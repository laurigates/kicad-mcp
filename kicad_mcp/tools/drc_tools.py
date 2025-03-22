"""
Design Rule Check (DRC) tools for KiCad PCB files.
"""
import os
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP, Context

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.drc_history import save_drc_result, get_drc_history, compare_with_previous
from kicad_mcp.utils.kicad_api_detection import get_best_api_approach

# Import implementations
from kicad_mcp.tools.drc_impl.cli_drc import run_drc_via_cli
from kicad_mcp.tools.drc_impl.ipc_drc import run_drc_with_ipc_api

def register_drc_tools(mcp: FastMCP) -> None:
    """Register DRC tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def get_drc_history_tool(project_path: str) -> Dict[str, Any]:
        """Get the DRC check history for a KiCad project.
        
        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            
        Returns:
            Dictionary with DRC history entries
        """
        print(f"Getting DRC history for project: {project_path}")
        
        if not os.path.exists(project_path):
            print(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}
        
        # Get history entries
        history_entries = get_drc_history(project_path)
        
        # Calculate trend information
        trend = None
        if len(history_entries) >= 2:
            first = history_entries[-1]  # Oldest entry
            last = history_entries[0]    # Newest entry
            
            first_violations = first.get("total_violations", 0)
            last_violations = last.get("total_violations", 0)
            
            if first_violations > last_violations:
                trend = "improving"
            elif first_violations < last_violations:
                trend = "degrading"
            else:
                trend = "stable"
        
        return {
            "success": True,
            "project_path": project_path,
            "history_entries": history_entries,
            "entry_count": len(history_entries),
            "trend": trend
        }
    
    @mcp.tool()
    async def run_drc_check(project_path: str, ctx: Context) -> Dict[str, Any]:
        """Run a Design Rule Check on a KiCad PCB file.
        
        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: MCP context for progress reporting
            
        Returns:
            Dictionary with DRC results and statistics
        """
        print(f"Running DRC check for project: {project_path}")
        
        if not os.path.exists(project_path):
            print(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}
        
        # Get PCB file from project
        files = get_project_files(project_path)
        if "pcb" not in files:
            print("PCB file not found in project")
            return {"success": False, "error": "PCB file not found in project"}
        
        pcb_file = files["pcb"]
        print(f"Found PCB file: {pcb_file}")
        
        # Report progress to user
        await ctx.report_progress(10, 100)
        ctx.info(f"Starting DRC check on {os.path.basename(pcb_file)}")
        
        # Get app context and determine which approach to use
        app_context = ctx.request_context.lifespan_context
        api_approach = getattr(app_context, 'api_approach', get_best_api_approach())
        
        # Run DRC using the appropriate approach
        drc_results = None
        
        if api_approach == "cli":
            # Use CLI approach (kicad-cli)
            print("Using kicad-cli for DRC")
            ctx.info("Using KiCad CLI for DRC check...")
            drc_results = await run_drc_via_cli(pcb_file, ctx)
        
        elif api_approach == "ipc":
            # Use IPC API approach (kicad-python)
            print("Using IPC API for DRC")
            ctx.info("Using KiCad IPC API for DRC check...")
            drc_results = await run_drc_with_ipc_api(pcb_file, ctx)
        
        else:
            # No API available
            print("No KiCad API available for DRC")
            return {
                "success": False,
                "error": "No KiCad API available for DRC. Please install KiCad 9.0 or later."
            }
        
        # Process and save results if successful
        if drc_results and drc_results.get("success", False):
            # Save results to history
            save_drc_result(project_path, drc_results)
            
            # Add comparison with previous run
            comparison = compare_with_previous(project_path, drc_results)
            if comparison:
                drc_results["comparison"] = comparison
                
                if comparison["change"] < 0:
                    ctx.info(f"Great progress! You've fixed {abs(comparison['change'])} DRC violations since the last check.")
                elif comparison["change"] > 0:
                    ctx.info(f"Found {comparison['change']} new DRC violations since the last check.")
                else:
                    ctx.info(f"No change in the number of DRC violations since the last check.")
        
        # Complete progress
        await ctx.report_progress(100, 100)
        
        return drc_results or {
            "success": False,
            "error": "DRC check failed with an unknown error"
        }

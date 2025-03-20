"""
Design Rule Check (DRC) tools for KiCad PCB files.
"""
import os
import json
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from mcp.server.fastmcp import FastMCP, Context

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.logger import Logger
from kicad_mcp.utils.drc_history import save_drc_result, get_drc_history, compare_with_previous
from kicad_mcp.config import KICAD_APP_PATH, system

# Create logger for this module
logger = Logger()

def register_drc_tools(mcp: FastMCP, kicad_modules_available: bool = False) -> None:
    """Register DRC tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
        kicad_modules_available: Whether KiCad Python modules are available
    """
    
    @mcp.tool()
    def get_drc_history_tool(project_path: str) -> Dict[str, Any]:
        """Get the DRC check history for a KiCad project.
        
        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            
        Returns:
            Dictionary with DRC history entries
        """
        logger.info(f"Getting DRC history for project: {project_path}")
        
        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
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
            
        Returns:
            Dictionary with DRC results and statistics
        """
        logger.info(f"Running DRC check for project: {project_path}")
        
        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}
        
        # Get PCB file from project
        files = get_project_files(project_path)
        if "pcb" not in files:
            logger.error("PCB file not found in project")
            return {"success": False, "error": "PCB file not found in project"}
        
        pcb_file = files["pcb"]
        logger.info(f"Found PCB file: {pcb_file}")
        
        # Report progress to user
        await ctx.report_progress(10, 100)
        ctx.info(f"Starting DRC check on {os.path.basename(pcb_file)}")
        
        # Try to use pcbnew if available
        if kicad_modules_available:
            try:
                drc_results = await run_drc_with_pcbnew(pcb_file, ctx)
                if drc_results["success"]:
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
                
                return drc_results
            except Exception as e:
                logger.error(f"Error running DRC with pcbnew: {str(e)}", exc_info=True)
                ctx.info(f"Error running DRC with pcbnew: {str(e)}")
                # Fall back to CLI method if pcbnew fails
        
        # Fall back to command line DRC check
        logger.info("Attempting DRC check via command line")
        await ctx.report_progress(30, 100)
        drc_results = run_drc_via_cli(pcb_file)
        
        if drc_results["success"]:
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
        
        return drc_results


async def run_drc_with_pcbnew(pcb_file: str, ctx: Context) -> Dict[str, Any]:
    """Run DRC using the pcbnew Python module.
    
    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting
        
    Returns:
        Dictionary with DRC results
    """
    try:
        import pcbnew
        logger.info("Successfully imported pcbnew module")
        
        # Load the board
        board = pcbnew.LoadBoard(pcb_file)
        if not board:
            logger.error("Failed to load PCB file")
            return {"success": False, "error": "Failed to load PCB file"}
        
        await ctx.report_progress(40, 100)
        ctx.info("PCB file loaded, running DRC checks...")
        
        # Create a DRC runner
        drc = pcbnew.DRC(board)
        drc.SetViolationHandler(pcbnew.DRC_ITEM_LIST())
        
        # Run the DRC
        drc.Run()
        await ctx.report_progress(70, 100)
        
        # Get the violations
        violations = drc.GetViolations()
        violation_count = violations.GetCount()
        
        logger.info(f"DRC completed with {violation_count} violations")
        ctx.info(f"DRC completed with {violation_count} violations")
        
        # Process the violations
        drc_errors = []
        for i in range(violation_count):
            violation = violations.GetItem(i)
            error_info = {
                "severity": violation.GetSeverity(),
                "message": violation.GetErrorMessage(),
                "location": {
                    "x": violation.GetPointA().x / 1000000.0,  # Convert to mm
                    "y": violation.GetPointA().y / 1000000.0
                }
            }
            drc_errors.append(error_info)
        
        await ctx.report_progress(90, 100)
        
        # Categorize violations by type
        error_types = {}
        for error in drc_errors:
            error_type = error["message"]
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
        
        # Create summary
        results = {
            "success": True,
            "method": "pcbnew",
            "pcb_file": pcb_file,
            "total_violations": violation_count,
            "violation_categories": error_types,
            "violations": drc_errors
        }
        
        return results
        
    except ImportError as e:
        logger.error(f"Failed to import pcbnew: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in pcbnew DRC: {str(e)}", exc_info=True)
        raise


def run_drc_via_cli(pcb_file: str) -> Dict[str, Any]:
    """Run DRC using KiCad command line tools.
    This is a fallback method when pcbnew Python module is not available.
    
    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        
    Returns:
        Dictionary with DRC results
    """
    results = {
        "success": False,
        "method": "cli",
        "pcb_file": pcb_file
    }
    
    try:
        # Create a temporary directory for the output
        with tempfile.TemporaryDirectory() as temp_dir:
            # The command to run DRC depends on the operating system
            if system == "Darwin":  # macOS
                # Path to KiCad command line tools on macOS
                pcbnew_cli = os.path.join(KICAD_APP_PATH, "Contents/MacOS/pcbnew_cli")
                
                # Check if the CLI tool exists
                if not os.path.exists(pcbnew_cli):
                    logger.error(f"pcbnew_cli not found at {pcbnew_cli}")
                    results["error"] = f"pcbnew_cli not found at {pcbnew_cli}"
                    return results
                
                # Output file for DRC report
                output_file = os.path.join(temp_dir, "drc_report.json")
                
                # Run the DRC command
                cmd = [
                    pcbnew_cli, 
                    "--run-drc",
                    "--output-json", output_file,
                    pcb_file
                ]
                
            elif system == "Windows":
                # Path to KiCad command line tools on Windows
                pcbnew_cli = os.path.join(KICAD_APP_PATH, "bin", "pcbnew_cli.exe")
                
                # Check if the CLI tool exists
                if not os.path.exists(pcbnew_cli):
                    logger.error(f"pcbnew_cli not found at {pcbnew_cli}")
                    results["error"] = f"pcbnew_cli not found at {pcbnew_cli}"
                    return results
                
                # Output file for DRC report
                output_file = os.path.join(temp_dir, "drc_report.json")
                
                # Run the DRC command
                cmd = [
                    pcbnew_cli, 
                    "--run-drc",
                    "--output-json", output_file,
                    pcb_file
                ]
                
            elif system == "Linux":
                # Path to KiCad command line tools on Linux
                pcbnew_cli = "pcbnew_cli"  # Assume it's in the PATH
                
                # Output file for DRC report
                output_file = os.path.join(temp_dir, "drc_report.json")
                
                # Run the DRC command
                cmd = [
                    pcbnew_cli, 
                    "--run-drc",
                    "--output-json", output_file,
                    pcb_file
                ]
            
            else:
                results["error"] = f"Unsupported operating system: {system}"
                return results
            
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the command was successful
            if process.returncode != 0:
                logger.error(f"DRC command failed with code {process.returncode}")
                logger.error(f"Error output: {process.stderr}")
                results["error"] = f"DRC command failed: {process.stderr}"
                return results
            
            # Check if the output file was created
            if not os.path.exists(output_file):
                logger.error("DRC report file not created")
                results["error"] = "DRC report file not created"
                return results
            
            # Read the DRC report
            with open(output_file, 'r') as f:
                try:
                    drc_report = json.load(f)
                except json.JSONDecodeError:
                    logger.error("Failed to parse DRC report JSON")
                    results["error"] = "Failed to parse DRC report JSON"
                    return results
            
            # Process the DRC report
            violation_count = len(drc_report.get("violations", []))
            logger.info(f"DRC completed with {violation_count} violations")
            
            # Extract violations
            violations = drc_report.get("violations", [])
            
            # Categorize violations by type
            error_types = {}
            for violation in violations:
                error_type = violation.get("message", "Unknown")
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
            
            # Create success response
            results = {
                "success": True,
                "method": "cli",
                "pcb_file": pcb_file,
                "total_violations": violation_count,
                "violation_categories": error_types,
                "violations": violations
            }
            
            return results
            
    except Exception as e:
        logger.error(f"Error in CLI DRC: {str(e)}", exc_info=True)
        results["error"] = f"Error in CLI DRC: {str(e)}"
        return results

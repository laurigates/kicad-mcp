"""
Design Rule Check (DRC) implementation using the KiCad IPC API.
"""
import os
from typing import Any, Dict

from mcp.server.fastmcp import Context

from kicad_mcp.utils.kicad_api_detection import check_ipc_api_environment

async def run_drc_with_ipc_api(pcb_file: str, ctx: Context) -> Dict[str, Any]:
    """Run DRC using the KiCad IPC API (kicad-python).
    This requires a running instance of KiCad with the IPC API enabled.
    
    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting
        
    Returns:
        Dictionary with DRC results
    """
    try:
        # Import the kicad-python modules
        import kipy
        from kipy.board_types import DrcExclusion, DrcSeverity
        print("Successfully imported kipy modules")
        
        # Check if we're running in a KiCad IPC plugin environment
        is_plugin, socket_path = check_ipc_api_environment()
        
        # Connect to KiCad
        await ctx.report_progress(20, 100)
        ctx.info("Connecting to KiCad...")
        
        if is_plugin:
            # When running as a plugin, let kipy use environment variables
            kicad = kipy.KiCad()
        else:
            # When running standalone, try to connect to KiCad
            if socket_path:
                kicad = kipy.KiCad(socket_path=socket_path)
            else:
                # Try with default socket path
                kicad = kipy.KiCad()
        
        # Get the currently open board
        await ctx.report_progress(30, 100)
        ctx.info("Getting board...")
        
        # Check which board to use
        current_boards = await kicad.get_open_documents("board")
        
        # If we have an open board, check if it's the one we want
        use_current_board = False
        board_doc = None
        
        if current_boards:
            for doc in current_boards:
                if doc.file_path and os.path.normpath(doc.file_path) == os.path.normpath(pcb_file):
                    board_doc = doc
                    use_current_board = True
                    break
        
        # If the board isn't open, see if we can open it
        if not use_current_board:
            ctx.info(f"Opening board file: {pcb_file}")
            try:
                # Try to open the board
                doc = await kicad.open_document(pcb_file)
                board_doc = doc
            except Exception as e:
                print(f"Error opening board: {str(e)}")
                return {
                    "success": False, 
                    "method": "ipc",
                    "error": f"Failed to open board file: {str(e)}"
                }
        
        # Get the board
        board = await kicad.board.get_board(board_doc.uuid)
        
        # Run DRC
        await ctx.report_progress(50, 100)
        ctx.info("Running DRC check...")
        
        # Define which severities to include
        severity_filter = DrcSeverity.ERROR | DrcSeverity.WARNING
        
        # Run DRC on the board
        drc_report = await kicad.board.run_drc(
            board.uuid, 
            severity_filter=severity_filter,
            exclusions=DrcExclusion.NONE  # Include all violations
        )
        
        # Process results
        await ctx.report_progress(70, 100)
        ctx.info("Processing DRC results...")
        
        # Get all violations
        violations = drc_report.violations
        violation_count = len(violations)
        
        print(f"DRC completed with {violation_count} violations")
        ctx.info(f"DRC completed with {violation_count} violations")
        
        # Process the violations
        drc_errors = []
        error_types = {}
        
        for violation in violations:
            # Get violation details
            severity = str(violation.severity)
            message = violation.message
            
            # Extract location
            location = {
                "x": violation.location.x if hasattr(violation, 'location') and violation.location else 0,
                "y": violation.location.y if hasattr(violation, 'location') and violation.location else 0
            }
            
            error_info = {
                "severity": severity,
                "message": message,
                "location": location
            }
            
            drc_errors.append(error_info)
            
            # Count by type
            if message not in error_types:
                error_types[message] = 0
            error_types[message] += 1
        
        # Create result
        results = {
            "success": True,
            "method": "ipc",
            "pcb_file": pcb_file,
            "total_violations": violation_count,
            "violation_categories": error_types,
            "violations": drc_errors
        }
        
        return results
        
    except ImportError as e:
        print(f"Failed to import kipy modules: {str(e)}")
        return {
            "success": False,
            "method": "ipc",
            "error": f"Failed to import kipy modules: {str(e)}"
        }
    except Exception as e:
        print(f"Error in IPC API DRC: {str(e)}", exc_info=True)
        return {
            "success": False,
            "method": "ipc",
            "error": f"Error in IPC API DRC: {str(e)}"
        }

"""
Analysis and validation tools for KiCad projects.
"""
import os
import tempfile
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context, Image

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.logger import Logger

# Create logger for this module
logger = Logger()

def register_analysis_tools(mcp: FastMCP, kicad_modules_available: bool = False) -> None:
    """Register analysis and validation tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
        kicad_modules_available: Whether KiCad Python modules are available
    """
    
    @mcp.tool()
    def validate_project(project_path: str) -> Dict[str, Any]:
        """Basic validation of a KiCad project."""
        logger.info(f"Validating project: {project_path}")
        
        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
            return {"valid": False, "error": f"Project not found: {project_path}"}
        
        issues = []
        files = get_project_files(project_path)
        
        # Check for essential files
        if "pcb" not in files:
            logger.warning("Missing PCB layout file")
            issues.append("Missing PCB layout file")
        
        if "schematic" not in files:
            logger.warning("Missing schematic file")
            issues.append("Missing schematic file")
        
        # Validate project file
        try:
            with open(project_path, 'r') as f:
                import json
                json.load(f)
                logger.debug("Project file validated successfully")
        except json.JSONDecodeError:
            logger.error("Invalid project file format (JSON parsing error)")
            issues.append("Invalid project file format (JSON parsing error)")
        except Exception as e:
            logger.error(f"Error reading project file: {str(e)}")
            issues.append(f"Error reading project file: {str(e)}")
        
        result = {
            "valid": len(issues) == 0,
            "path": project_path,
            "issues": issues if issues else None,
            "files_found": list(files.keys())
        }
        
        logger.info(f"Validation result: {'valid' if result['valid'] else 'invalid'}")
        return result

    @mcp.tool()
    async def generate_project_thumbnail(project_path: str, ctx: Context) -> Optional[Image]:
        """Generate a thumbnail of a KiCad project's PCB layout."""
        logger.info(f"Generating thumbnail for project: {project_path}")
        
        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
            ctx.info(f"Project not found: {project_path}")
            return None
        
        # Get PCB file
        files = get_project_files(project_path)
        if "pcb" not in files:
            logger.error("PCB file not found in project")
            ctx.info("PCB file not found in project")
            return None
        
        pcb_file = files["pcb"]
        logger.info(f"Found PCB file: {pcb_file}")
        
        if not kicad_modules_available:
            logger.warning("KiCad Python modules are not available - cannot generate thumbnail")
            ctx.info("KiCad Python modules are not available")
            return None
        
        try:
            # Try to import pcbnew
            import pcbnew
            logger.info("Successfully imported pcbnew module")
            
            # Load the PCB file
            logger.debug(f"Loading PCB file: {pcb_file}")
            board = pcbnew.LoadBoard(pcb_file)
            if not board:
                logger.error("Failed to load PCB file")
                ctx.info("Failed to load PCB file")
                return None
                
            # Get board dimensions
            board_box = board.GetBoardEdgesBoundingBox()
            width = board_box.GetWidth() / 1000000.0  # Convert to mm
            height = board_box.GetHeight() / 1000000.0
            
            logger.info(f"PCB dimensions: {width:.2f}mm x {height:.2f}mm")
            ctx.info(f"PCB dimensions: {width:.2f}mm x {height:.2f}mm")
            
            # Create temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"Created temporary directory: {temp_dir}")
                
                # Create PLOT_CONTROLLER for plotting
                pctl = pcbnew.PLOT_CONTROLLER(board)
                popt = pctl.GetPlotOptions()
                
                # Set plot options for PNG output
                popt.SetOutputDirectory(temp_dir)
                popt.SetPlotFrameRef(False)
                popt.SetPlotValue(True)
                popt.SetPlotReference(True)
                popt.SetPlotInvisibleText(False)
                popt.SetPlotViaOnMaskLayer(False)
                popt.SetColorMode(True)  # Color mode
                
                # Set color theme (if available in this version)
                if hasattr(popt, "SetColorTheme"):
                    popt.SetColorTheme("default")
                
                # Calculate a reasonable scale to fit in a thumbnail
                max_size = 800  # Max pixel dimension
                scale = min(max_size / width, max_size / height) * 0.8  # 80% to leave some margin
                
                # Set plot scale if the function exists
                if hasattr(popt, "SetScale"):
                    popt.SetScale(scale)
                
                # Determine output filename
                plot_basename = "thumbnail"
                output_filename = os.path.join(temp_dir, f"{plot_basename}.png")
                
                logger.debug(f"Plotting PCB to: {output_filename}")
                
                # Plot PNG
                pctl.OpenPlotfile(plot_basename, pcbnew.PLOT_FORMAT_PNG, "Thumbnail")
                pctl.PlotLayer()
                pctl.ClosePlot()
                
                # The plot controller creates files with predictable names
                plot_file = os.path.join(temp_dir, f"{plot_basename}.png")
                
                if not os.path.exists(plot_file):
                    logger.error(f"Expected plot file not found: {plot_file}")
                    ctx.info("Failed to generate PCB image")
                    return None
                
                # Read the image file
                with open(plot_file, 'rb') as f:
                    img_data = f.read()
                
                logger.info(f"Successfully generated thumbnail, size: {len(img_data)} bytes")
                return Image(data=img_data, format="png")
            
        except ImportError as e:
            logger.error(f"Failed to import pcbnew module: {str(e)}")
            ctx.info(f"Failed to import pcbnew module: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}", exc_info=True)
            ctx.info(f"Error generating thumbnail: {str(e)}")
            return None

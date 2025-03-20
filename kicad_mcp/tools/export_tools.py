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
    async def generate_pcb_thumbnail(project_path: str, ctx: Context) -> Optional[Image]:
        """Generate a thumbnail image of a KiCad PCB layout.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)

        Returns:
            Thumbnail image of the PCB or None if generation failed
        """
        logger.info(f"Generating thumbnail for project: {project_path}")

        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
            ctx.info(f"Project not found: {project_path}")
            return None

        # Get PCB file from project
        files = get_project_files(project_path)
        if "pcb" not in files:
            logger.error("PCB file not found in project")
            ctx.info("PCB file not found in project")
            return None

        pcb_file = files["pcb"]
        logger.info(f"Found PCB file: {pcb_file}")

        await ctx.report_progress(10, 100)
        ctx.info(f"Generating thumbnail for {os.path.basename(pcb_file)}")

        # Method 1: Try to use pcbnew Python module if available
        if kicad_modules_available:
            try:
                thumbnail = await generate_thumbnail_with_pcbnew(pcb_file, ctx)
                if thumbnail:
                    return thumbnail

                # If pcbnew method failed, log it but continue to try alternative method
                logger.warning("Failed to generate thumbnail with pcbnew, trying CLI method")
            except Exception as e:
                logger.error(f"Error using pcbnew for thumbnail: {str(e)}", exc_info=True)
                ctx.info(f"Error with pcbnew method, trying alternative approach")
        else:
            logger.info("KiCad Python modules not available, trying CLI method")

        # Method 2: Try to use command-line tools
        try:
            thumbnail = await generate_thumbnail_with_cli(pcb_file, ctx)
            if thumbnail:
                return thumbnail
        except Exception as e:
            logger.error(f"Error using CLI for thumbnail: {str(e)}", exc_info=True)
            ctx.info(f"Error generating thumbnail with CLI method")

        # If all methods fail, inform the user
        ctx.info("Could not generate thumbnail for PCB - all methods failed")
        return None

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

# Helper functions for thumbnail generation
async def generate_thumbnail_with_pcbnew(pcb_file: str, ctx: Context) -> Optional[Image]:
    """Generate PCB thumbnail using the pcbnew Python module.

    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting

    Returns:
        Image object containing the PCB thumbnail or None if generation failed
    """
    try:
        import pcbnew
        logger.info("Successfully imported pcbnew module")
        await ctx.report_progress(20, 100)

        # Load the PCB file
        logger.debug(f"Loading PCB file with pcbnew: {pcb_file}")
        board = pcbnew.LoadBoard(pcb_file)
        if not board:
            logger.error("Failed to load PCB file with pcbnew")
            return None

        # Report progress
        await ctx.report_progress(30, 100)
        ctx.info("PCB file loaded, generating image...")

        # Get board dimensions
        board_box = board.GetBoardEdgesBoundingBox()
        width_mm = board_box.GetWidth() / 1000000.0  # Convert to mm
        height_mm = board_box.GetHeight() / 1000000.0

        logger.info(f"PCB dimensions: {width_mm:.2f}mm x {height_mm:.2f}mm")

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

            # Set color mode (if available in this version)
            if hasattr(popt, "SetColorMode"):
                popt.SetColorMode(True)  # Color mode

            # Set color theme (if available in this version)
            if hasattr(popt, "SetColorTheme"):
                popt.SetColorTheme("default")

            # Calculate a reasonable scale to fit in a thumbnail
            max_pixels = 800  # Max pixel dimension
            scale = min(max_pixels / width_mm, max_pixels / height_mm) * 0.8  # 80% to leave margin

            # Set plot scale if the function exists
            if hasattr(popt, "SetScale"):
                popt.SetScale(scale)

            # Determine output filename
            plot_basename = "thumbnail"

            logger.debug(f"Plotting PCB to PNG")
            await ctx.report_progress(50, 100)

            # Plot PNG
            pctl.OpenPlotfile(plot_basename, pcbnew.PLOT_FORMAT_PNG, "Thumbnail")
            pctl.PlotLayer()
            pctl.ClosePlot()

            await ctx.report_progress(70, 100)

            # The plot controller creates files with predictable names
            plot_file = os.path.join(temp_dir, f"{plot_basename}.png")

            if not os.path.exists(plot_file):
                logger.error(f"Expected plot file not found: {plot_file}")
                return None

            # Read the image file
            with open(plot_file, 'rb') as f:
                img_data = f.read()

            logger.info(f"Successfully generated thumbnail, size: {len(img_data)} bytes")
            await ctx.report_progress(90, 100)
            return Image(data=img_data, format="png")

    except ImportError as e:
        logger.error(f"Failed to import pcbnew module: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail with pcbnew: {str(e)}", exc_info=True)
        return None

async def generate_thumbnail_with_cli(pcb_file: str, ctx: Context) -> Optional[Image]:
    """Generate PCB thumbnail using command line tools.
    This is a fallback method when pcbnew Python module is not available.

    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting

    Returns:
        Image object containing the PCB thumbnail or None if generation failed
    """
    import subprocess

    logger.info("Attempting to generate thumbnail using command line tools")
    await ctx.report_progress(20, 100)

    # Check for required command-line tools based on OS
    if system == "Darwin":  # macOS
        pcbnew_cli = os.path.join(KICAD_APP_PATH, "Contents/MacOS/pcbnew_cli")
        if not os.path.exists(pcbnew_cli) and shutil.which("pcbnew_cli") is not None:
            pcbnew_cli = "pcbnew_cli"  # Try to use from PATH
        elif not os.path.exists(pcbnew_cli):
            logger.error(f"pcbnew_cli not found at {pcbnew_cli} or in PATH")
            return None
    elif system == "Windows":
        pcbnew_cli = os.path.join(KICAD_APP_PATH, "bin", "pcbnew_cli.exe")
        if not os.path.exists(pcbnew_cli) and shutil.which("pcbnew_cli") is not None:
            pcbnew_cli = "pcbnew_cli"  # Try to use from PATH
        elif not os.path.exists(pcbnew_cli):
            logger.error(f"pcbnew_cli not found at {pcbnew_cli} or in PATH")
            return None
    elif system == "Linux":
        pcbnew_cli = shutil.which("pcbnew_cli")
        if not pcbnew_cli:
            logger.error("pcbnew_cli not found in PATH")
            return None
    else:
        logger.error(f"Unsupported operating system: {system}")
        return None

    await ctx.report_progress(30, 100)
    ctx.info("Using KiCad command line tools for thumbnail generation")

    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Output PNG file
        output_file = os.path.join(temp_dir, "thumbnail.png")

        # Build command for generating PNG from PCB
        cmd = [
            pcbnew_cli,
            "--export-png",
            output_file,
            "--page-size-inches", "8x6",  # Set a reasonable page size
            "--layers", "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",  # Important layers
            pcb_file
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")
        await ctx.report_progress(50, 100)

        # Run the command
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if process.returncode != 0:
                logger.error(f"Command failed with code {process.returncode}")
                logger.error(f"Error: {process.stderr}")
                return None

            await ctx.report_progress(70, 100)

            # Check if the output file was created
            if not os.path.exists(output_file):
                logger.error(f"Output file not created: {output_file}")
                return None

            # Read the image file
            with open(output_file, 'rb') as f:
                img_data = f.read()

            logger.info(f"Successfully generated thumbnail with CLI, size: {len(img_data)} bytes")
            await ctx.report_progress(90, 100)
            return Image(data=img_data, format="png")

        except subprocess.TimeoutExpired:
            logger.error("Command timed out after 30 seconds")
            return None
        except Exception as e:
            logger.error(f"Error running CLI command: {str(e)}", exc_info=True)
            return None

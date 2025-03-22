"""
Export tools for KiCad projects.
"""
import os
import tempfile
import subprocess
import shutil
import asyncio
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context, Image

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.config import KICAD_APP_PATH, system

def register_export_tools(mcp: FastMCP) -> None:
    """Register export tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def validate_project(project_path: str) -> Dict[str, Any]:
        """Basic validation of a KiCad project."""
        print(f"Validating project: {project_path}")
        
        if not os.path.exists(project_path):
            print(f"Project not found: {project_path}")
            return {"valid": False, "error": f"Project not found: {project_path}"}
        
        issues = []
        files = get_project_files(project_path)
        
        # Check for essential files
        if "pcb" not in files:
            print("Missing PCB layout file")
            issues.append("Missing PCB layout file")
        
        if "schematic" not in files:
            print("Missing schematic file")
            issues.append("Missing schematic file")
        
        # Validate project file
        try:
            with open(project_path, 'r') as f:
                import json
                json.load(f)
                print("Project file validated successfully")
        except json.JSONDecodeError:
            print("Invalid project file format (JSON parsing error)")
            issues.append("Invalid project file format (JSON parsing error)")
        except Exception as e:
            print(f"Error reading project file: {str(e)}")
            issues.append(f"Error reading project file: {str(e)}")
        
        result = {
            "valid": len(issues) == 0,
            "path": project_path,
            "issues": issues if issues else None,
            "files_found": list(files.keys())
        }
        
        print(f"Validation result: {'valid' if result['valid'] else 'invalid'}")
        return result

    @mcp.tool()
    async def generate_pcb_thumbnail(project_path: str, ctx: Context) -> Optional[Image]:
        """Generate a thumbnail image of a KiCad PCB layout.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: Context for MCP communication

        Returns:
            Thumbnail image of the PCB or None if generation failed
        """
        try:
            # Access the context
            app_context = ctx.request_context.lifespan_context
            kicad_modules_available = app_context.kicad_modules_available
            
            print(f"Generating thumbnail for project: {project_path}")

            if not os.path.exists(project_path):
                print(f"Project not found: {project_path}")
                ctx.info(f"Project not found: {project_path}")
                return None

            # Get PCB file from project
            files = get_project_files(project_path)
            if "pcb" not in files:
                print("PCB file not found in project")
                ctx.info("PCB file not found in project")
                return None

            pcb_file = files["pcb"]
            print(f"Found PCB file: {pcb_file}")

            # Check cache
            cache_key = f"thumbnail_{pcb_file}_{os.path.getmtime(pcb_file)}"
            if hasattr(app_context, 'cache') and cache_key in app_context.cache:
                print(f"Using cached thumbnail for {pcb_file}")
                return app_context.cache[cache_key]

            await ctx.report_progress(10, 100)
            ctx.info(f"Generating thumbnail for {os.path.basename(pcb_file)}")

            # Try to use command-line tools
            try:
                thumbnail = await generate_thumbnail_with_cli(pcb_file, ctx)
                if thumbnail:
                    # Cache the result if possible
                    if hasattr(app_context, 'cache'):
                        app_context.cache[cache_key] = thumbnail
                    return thumbnail
            except Exception as e:
                print(f"Error using CLI for thumbnail: {str(e)}", exc_info=True)
                ctx.info(f"Error generating thumbnail with CLI method")

            # If it fails, inform the user
            ctx.info("Could not generate thumbnail for PCB - all methods failed")
            return None
            
        except asyncio.CancelledError:
            print("Thumbnail generation cancelled")
            raise  # Re-raise to let MCP know the task was cancelled
        except Exception as e:
            print(f"Unexpected error in thumbnail generation: {str(e)}")
            ctx.info(f"Error: {str(e)}")
            return None

    @mcp.tool()
    async def generate_project_thumbnail(project_path: str, ctx: Context) -> Optional[Image]:
        """Generate a thumbnail of a KiCad project's PCB layout."""
        try:
            # Access the context
            app_context = ctx.request_context.lifespan_context
            kicad_modules_available = app_context.kicad_modules_available
            
            print(f"Generating thumbnail for project: {project_path}")
            
            if not os.path.exists(project_path):
                print(f"Project not found: {project_path}")
                ctx.info(f"Project not found: {project_path}")
                return None
            
            # Get PCB file
            files = get_project_files(project_path)
            if "pcb" not in files:
                print("PCB file not found in project")
                ctx.info("PCB file not found in project")
                return None
            
            pcb_file = files["pcb"]
            print(f"Found PCB file: {pcb_file}")
            
            if not kicad_modules_available:
                print("KiCad Python modules are not available - cannot generate thumbnail")
                ctx.info("KiCad Python modules are not available")
                return None
            
            # Check cache
            cache_key = f"project_thumbnail_{pcb_file}_{os.path.getmtime(pcb_file)}"
            if hasattr(app_context, 'cache') and cache_key in app_context.cache:
                print(f"Using cached project thumbnail for {pcb_file}")
                return app_context.cache[cache_key]
            
            try:
                # Try to import pcbnew
                import pcbnew
                print("Successfully imported pcbnew module")
                
                # Load the PCB file
                print(f"Loading PCB file: {pcb_file}")
                board = pcbnew.LoadBoard(pcb_file)
                if not board:
                    print("Failed to load PCB file")
                    ctx.info("Failed to load PCB file")
                    return None
                    
                # Get board dimensions
                board_box = board.GetBoardEdgesBoundingBox()
                width = board_box.GetWidth() / 1000000.0  # Convert to mm
                height = board_box.GetHeight() / 1000000.0
                
                print(f"PCB dimensions: {width:.2f}mm x {height:.2f}mm")
                ctx.info(f"PCB dimensions: {width:.2f}mm x {height:.2f}mm")
                
                # Create temporary directory for output
                with tempfile.TemporaryDirectory() as temp_dir:
                    print(f"Created temporary directory: {temp_dir}")
                    
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
                    
                    print(f"Plotting PCB to: {output_filename}")
                    
                    # Plot PNG
                    pctl.OpenPlotfile(plot_basename, pcbnew.PLOT_FORMAT_PNG, "Thumbnail")
                    pctl.PlotLayer()
                    pctl.ClosePlot()
                    
                    # The plot controller creates files with predictable names
                    plot_file = os.path.join(temp_dir, f"{plot_basename}.png")
                    
                    if not os.path.exists(plot_file):
                        print(f"Expected plot file not found: {plot_file}")
                        ctx.info("Failed to generate PCB image")
                        return None
                    
                    # Read the image file
                    with open(plot_file, 'rb') as f:
                        img_data = f.read()
                    
                    print(f"Successfully generated thumbnail, size: {len(img_data)} bytes")
                    
                    # Create and cache the image
                    thumbnail = Image(data=img_data, format="png")
                    if hasattr(app_context, 'cache'):
                        app_context.cache[cache_key] = thumbnail
                    
                    return thumbnail
                
            except ImportError as e:
                print(f"Failed to import pcbnew module: {str(e)}")
                ctx.info(f"Failed to import pcbnew module: {str(e)}")
                return None
            except Exception as e:
                print(f"Error generating thumbnail: {str(e)}", exc_info=True)
                ctx.info(f"Error generating thumbnail: {str(e)}")
                return None
                
        except asyncio.CancelledError:
            print("Project thumbnail generation cancelled")
            raise
        except Exception as e:
            print(f"Unexpected error in project thumbnail generation: {str(e)}", exc_info=True)
            ctx.info(f"Error: {str(e)}")
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
        print("Successfully imported pcbnew module")
        await ctx.report_progress(20, 100)

        # Load the PCB file
        print(f"Loading PCB file with pcbnew: {pcb_file}")
        board = pcbnew.LoadBoard(pcb_file)
        if not board:
            print("Failed to load PCB file with pcbnew")
            return None

        # Report progress
        await ctx.report_progress(30, 100)
        ctx.info("PCB file loaded, generating image...")

        # Get board dimensions
        board_box = board.GetBoardEdgesBoundingBox()
        width_mm = board_box.GetWidth() / 1000000.0  # Convert to mm
        height_mm = board_box.GetHeight() / 1000000.0

        print(f"PCB dimensions: {width_mm:.2f}mm x {height_mm:.2f}mm")

        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Created temporary directory: {temp_dir}")

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

            print(f"Plotting PCB to PNG")
            await ctx.report_progress(50, 100)

            # Plot PNG
            pctl.OpenPlotfile(plot_basename, pcbnew.PLOT_FORMAT_PNG, "Thumbnail")
            pctl.PlotLayer()
            pctl.ClosePlot()

            await ctx.report_progress(70, 100)

            # The plot controller creates files with predictable names
            plot_file = os.path.join(temp_dir, f"{plot_basename}.png")

            if not os.path.exists(plot_file):
                print(f"Expected plot file not found: {plot_file}")
                return None

            # Read the image file
            with open(plot_file, 'rb') as f:
                img_data = f.read()

            print(f"Successfully generated thumbnail, size: {len(img_data)} bytes")
            await ctx.report_progress(90, 100)
            return Image(data=img_data, format="png")

    except ImportError as e:
        print(f"Failed to import pcbnew module: {str(e)}")
        return None
    except Exception as e:
        print(f"Error generating thumbnail with pcbnew: {str(e)}", exc_info=True)
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
    try:
        print("Attempting to generate thumbnail using command line tools")
        await ctx.report_progress(20, 100)

        # Check for required command-line tools based on OS
        if system == "Darwin":  # macOS
            pcbnew_cli = os.path.join(KICAD_APP_PATH, "Contents/MacOS/pcbnew_cli")
            if not os.path.exists(pcbnew_cli) and shutil.which("pcbnew_cli") is not None:
                pcbnew_cli = "pcbnew_cli"  # Try to use from PATH
            elif not os.path.exists(pcbnew_cli):
                print(f"pcbnew_cli not found at {pcbnew_cli} or in PATH")
                return None
        elif system == "Windows":
            pcbnew_cli = os.path.join(KICAD_APP_PATH, "bin", "pcbnew_cli.exe")
            if not os.path.exists(pcbnew_cli) and shutil.which("pcbnew_cli") is not None:
                pcbnew_cli = "pcbnew_cli"  # Try to use from PATH
            elif not os.path.exists(pcbnew_cli):
                print(f"pcbnew_cli not found at {pcbnew_cli} or in PATH")
                return None
        elif system == "Linux":
            pcbnew_cli = shutil.which("pcbnew_cli")
            if not pcbnew_cli:
                print("pcbnew_cli not found in PATH")
                return None
        else:
            print(f"Unsupported operating system: {system}")
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

            print(f"Running command: {' '.join(cmd)}")
            await ctx.report_progress(50, 100)

            # Run the command
            try:
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if process.returncode != 0:
                    print(f"Command failed with code {process.returncode}")
                    print(f"Error: {process.stderr}")
                    return None

                await ctx.report_progress(70, 100)

                # Check if the output file was created
                if not os.path.exists(output_file):
                    print(f"Output file not created: {output_file}")
                    return None

                # Read the image file
                with open(output_file, 'rb') as f:
                    img_data = f.read()

                print(f"Successfully generated thumbnail with CLI, size: {len(img_data)} bytes")
                await ctx.report_progress(90, 100)
                return Image(data=img_data, format="png")

            except subprocess.TimeoutExpired:
                print("Command timed out after 30 seconds")
                return None
            except Exception as e:
                print(f"Error running CLI command: {str(e)}", exc_info=True)
                return None
                
    except asyncio.CancelledError:
        print("CLI thumbnail generation cancelled")
        raise
    except Exception as e:
        print(f"Unexpected error in CLI thumbnail generation: {str(e)}")
        return None

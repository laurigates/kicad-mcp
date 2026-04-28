"""
Export tools for KiCad projects.
"""
import os
import tempfile
import subprocess
import shutil
import asyncio
import logging
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context, Image

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.config import KICAD_APP_PATH, system

logger = logging.getLogger(__name__)


def register_export_tools(mcp: FastMCP) -> None:
    """Register export tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    async def generate_pcb_thumbnail(project_path: str, ctx: Context | None):
        """Generate a thumbnail image of a KiCad PCB layout using kicad-cli.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: Context for MCP communication

        Returns:
            Thumbnail image of the PCB or None if generation failed
        """
        try:
            # Access the context (with null check)
            app_context = None
            if ctx:
                app_context = ctx.request_context.lifespan_context
            # Removed check for kicad_modules_available as we now use CLI
            
            logger.info("Generating thumbnail via CLI for project: %s", project_path)

            if not os.path.exists(project_path):
                logger.warning("Project not found: %s", project_path)
                if ctx:
                    await ctx.info(f"Project not found: {project_path}")
                return None

            # Get PCB file from project
            files = get_project_files(project_path)
            if "pcb" not in files:
                logger.warning("PCB file not found in project")
                if ctx:
                    await ctx.info("PCB file not found in project")
                return None

            pcb_file = files["pcb"]
            logger.debug("Found PCB file: %s", pcb_file)

            # Check cache
            cache_key = f"thumbnail_cli_{pcb_file}_{os.path.getmtime(pcb_file)}"
            if app_context and hasattr(app_context, 'cache') and cache_key in app_context.cache:
                logger.debug("Using cached CLI thumbnail for %s", pcb_file)
                return app_context.cache[cache_key]

            if ctx:
                await ctx.report_progress(10, 100)
                await ctx.info(f"Generating thumbnail for {os.path.basename(pcb_file)} using kicad-cli")

            # Use command-line tools
            try:
                thumbnail = await generate_thumbnail_with_cli(pcb_file, ctx)
                if thumbnail:
                    # Cache the result if possible
                    if app_context and hasattr(app_context, 'cache'):
                        app_context.cache[cache_key] = thumbnail
                    logger.info("Thumbnail generated successfully via CLI.")
                    return thumbnail
                else:
                     logger.warning("generate_thumbnail_with_cli returned None")
                     if ctx:
                         await ctx.info("Failed to generate thumbnail using kicad-cli.")
                     return None
            except Exception as e:
                logger.error("Error calling generate_thumbnail_with_cli: %s", e, exc_info=True)
                if ctx:
                    await ctx.info(f"Error generating thumbnail with kicad-cli: {str(e)}")
                return None
            
        except asyncio.CancelledError:
            logger.info("Thumbnail generation cancelled")
            raise  # Re-raise to let MCP know the task was cancelled
        except Exception as e:
            logger.error("Unexpected error in thumbnail generation: %s", e)
            if ctx:
                await ctx.info(f"Error: {str(e)}")
            return None

    @mcp.tool()
    async def generate_project_thumbnail(project_path: str, ctx: Context | None):
        """Generate a thumbnail of a KiCad project's PCB layout (Alias for generate_pcb_thumbnail)."""
        # This function now just calls the main CLI-based thumbnail generator
        logger.debug("generate_project_thumbnail called, redirecting to generate_pcb_thumbnail for %s", project_path)
        return await generate_pcb_thumbnail(project_path, ctx)

# Helper functions for thumbnail generation
async def generate_thumbnail_with_cli(pcb_file: str, ctx: Context | None):
    """Generate PCB thumbnail using command line tools.
    This is a fallback method when the kicad Python module is not available or fails.

    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting

    Returns:
        Image object containing the PCB thumbnail or None if generation failed
    """
    try:
        logger.info("Attempting to generate thumbnail using KiCad CLI tools")
        if ctx:
            await ctx.report_progress(20, 100)

        # --- Determine Output Path --- 
        project_dir = os.path.dirname(pcb_file)
        project_name = os.path.splitext(os.path.basename(pcb_file))[0]
        output_file = os.path.join(project_dir, f"{project_name}_thumbnail.svg")
        # --------------------------- 

        # Check for required command-line tools based on OS
        kicad_cli = None
        if system == "Darwin":  # macOS
            kicad_cli_path = os.path.join(KICAD_APP_PATH, "Contents/MacOS/kicad-cli")
            if os.path.exists(kicad_cli_path):
                 kicad_cli = kicad_cli_path
            elif shutil.which("kicad-cli") is not None:
                kicad_cli = "kicad-cli"  # Try to use from PATH
            else:
                logger.warning("kicad-cli not found at %s or in PATH", kicad_cli_path)
                return None
        elif system == "Windows":
            kicad_cli_path = os.path.join(KICAD_APP_PATH, "bin", "kicad-cli.exe")
            if os.path.exists(kicad_cli_path):
                 kicad_cli = kicad_cli_path
            elif shutil.which("kicad-cli.exe") is not None:
                 kicad_cli = "kicad-cli.exe"
            elif shutil.which("kicad-cli") is not None:
                kicad_cli = "kicad-cli"  # Try to use from PATH (without .exe)
            else:
                logger.warning("kicad-cli not found at %s or in PATH", kicad_cli_path)
                return None
        elif system == "Linux":
            kicad_cli = shutil.which("kicad-cli")
            if not kicad_cli:
                logger.warning("kicad-cli not found in PATH")
                return None
        else:
            logger.error("Unsupported operating system: %s", system)
            return None

        if ctx:
            await ctx.report_progress(30, 100)
            await ctx.info("Using KiCad command line tools for thumbnail generation")        # Build command for generating SVG from PCB using kicad-cli (changed from PNG)
        cmd = [
            kicad_cli,
            "pcb",
            "export",
            "svg", # <-- Changed format to svg
            "--output", output_file,
            "--layers", "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",  # Keep relevant layers
            # Consider adding options like --black-and-white if needed
            pcb_file
        ]

        logger.debug("Running command: %s", " ".join(cmd))
        if ctx:
            await ctx.report_progress(50, 100)

        # Run the command
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            logger.debug("Command successful: %s", process.stdout)

            if ctx:
                await ctx.report_progress(70, 100)

            # Check if the output file was created
            if not os.path.exists(output_file):
                logger.error("Output file not created: %s", output_file)
                return None

            # Read the image file
            with open(output_file, 'rb') as f:
                img_data = f.read()

            logger.info("Successfully generated thumbnail with CLI, size: %d bytes", len(img_data))
            if ctx:
                await ctx.report_progress(90, 100)
                # Inform user about the saved file
                await ctx.info(f"Thumbnail saved to: {output_file}")
            return Image(data=img_data, format="svg") # <-- Changed format to svg

        except subprocess.CalledProcessError as e:
            logger.error("Command '%s' failed with code %d", " ".join(e.cmd), e.returncode)
            logger.error("Stderr: %s", e.stderr)
            logger.error("Stdout: %s", e.stdout)
            if ctx:
                await ctx.info(f"KiCad CLI command failed: {e.stderr or e.stdout}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Command timed out after 30 seconds: %s", " ".join(cmd))
            if ctx:
                await ctx.info("KiCad CLI command timed out")
            return None
        except Exception as e:
            logger.error("Error running CLI command: %s", e, exc_info=True)
            if ctx:
                await ctx.info(f"Error running KiCad CLI: {str(e)}")
            return None
                
    except asyncio.CancelledError:
        logger.info("CLI thumbnail generation cancelled")
        raise
    except Exception as e:
        logger.error("Unexpected error in CLI thumbnail generation: %s", e)
        if ctx:
            await ctx.info(f"Unexpected error: {str(e)}")
        return None

"""
Export tools for KiCad projects.
"""

import asyncio
import os

from fastmcp import Context, FastMCP
from fastmcp.utilities.types import Image

from kicad_mcp.config import PROGRESS_CONSTANTS, TIMEOUT_CONSTANTS
from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.path_validator import (
    PathValidationError,
    validate_directory,
    validate_kicad_file,
)
from kicad_mcp.utils.secure_subprocess import SecureSubprocessError, SecureSubprocessRunner


def register_export_tools(mcp: FastMCP) -> None:
    """Register export tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """

    @mcp.tool()
    async def generate_pcb_thumbnail(project_path: str, ctx: Context):
        """Generate a thumbnail image of a KiCad PCB layout using kicad-cli.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: Context for MCP communication

        Returns:
            Image object containing the PCB thumbnail or None if generation failed
        """
        try:
            # Access the context
            app_context = ctx.request_context.lifespan_context
            # Removed check for kicad_modules_available as we now use CLI

            print(f"Generating thumbnail via CLI for project: {project_path}")

            # Validate and sanitize project path
            try:
                validated_project_path = validate_kicad_file(
                    project_path, "project", must_exist=True
                )
            except PathValidationError as e:
                print(f"Invalid project path: {e}")
                await ctx.info(f"Invalid project path: {e}")
                return None

            # Get PCB file from project
            files = get_project_files(validated_project_path)
            if "pcb" not in files:
                print("PCB file not found in project")
                await ctx.info("PCB file not found in project")
                return None

            pcb_file = files["pcb"]
            print(f"Found PCB file: {pcb_file}")

            # Check cache
            cache_key = f"thumbnail_cli_{pcb_file}_{os.path.getmtime(pcb_file)}"
            if hasattr(app_context, "cache") and cache_key in app_context.cache:
                print(f"Using cached CLI thumbnail for {pcb_file}")
                return app_context.cache[cache_key]

            await ctx.report_progress(PROGRESS_CONSTANTS["start"], PROGRESS_CONSTANTS["complete"])
            await ctx.info(f"Generating thumbnail for {os.path.basename(pcb_file)} using kicad-cli")

            # Use command-line tools
            try:
                thumbnail = await generate_thumbnail_with_cli(pcb_file, ctx)
                if thumbnail:
                    # Cache the result if possible
                    if hasattr(app_context, "cache"):
                        app_context.cache[cache_key] = thumbnail
                    print("Thumbnail generated successfully via CLI.")
                    return thumbnail
                else:
                    print("generate_thumbnail_with_cli returned None")
                    await ctx.info("Failed to generate thumbnail using kicad-cli.")
                    return None
            except Exception as e:
                print(f"Error calling generate_thumbnail_with_cli: {str(e)}", exc_info=True)
                await ctx.info(f"Error generating thumbnail with kicad-cli: {str(e)}")
                return None

        except asyncio.CancelledError:
            print("Thumbnail generation cancelled")
            raise  # Re-raise to let MCP know the task was cancelled
        except Exception as e:
            print(f"Unexpected error in thumbnail generation: {str(e)}")
            await ctx.info(f"Error: {str(e)}")
            return None

    @mcp.tool()
    async def generate_project_thumbnail(project_path: str, ctx: Context):
        """Generate a thumbnail of a KiCad project's PCB layout (Alias for generate_pcb_thumbnail)."""
        # This function now just calls the main CLI-based thumbnail generator
        print(
            f"generate_project_thumbnail called, redirecting to generate_pcb_thumbnail for {project_path}"
        )
        return await generate_pcb_thumbnail(project_path, ctx)


# Helper functions for thumbnail generation
async def generate_thumbnail_with_cli(pcb_file: str, ctx: Context):
    """Generate PCB thumbnail using command line tools.
    This is a fallback method when the kicad Python module is not available or fails.

    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting

    Returns:
        Image object containing the PCB thumbnail or None if generation failed
    """
    try:
        print("Attempting to generate thumbnail using KiCad CLI tools")
        await ctx.report_progress(PROGRESS_CONSTANTS["detection"], PROGRESS_CONSTANTS["complete"])

        # Validate and sanitize PCB file path
        try:
            validated_pcb_file = validate_kicad_file(pcb_file, "pcb", must_exist=True)
        except PathValidationError as e:
            print(f"Invalid PCB file path: {e}")
            await ctx.info(f"Invalid PCB file path: {e}")
            return None

        # --- Determine Output Path ---
        project_dir = os.path.dirname(validated_pcb_file)
        try:
            validated_project_dir = validate_directory(project_dir, must_exist=True)
        except PathValidationError as e:
            print(f"Invalid project directory: {e}")
            await ctx.info(f"Invalid project directory: {e}")
            return None

        project_name = os.path.splitext(os.path.basename(validated_pcb_file))[0]
        output_file = os.path.join(validated_project_dir, f"{project_name}_thumbnail.svg")
        # ---------------------------

        await ctx.report_progress(PROGRESS_CONSTANTS["setup"], PROGRESS_CONSTANTS["complete"])
        await ctx.info("Using KiCad command line tools for thumbnail generation")

        # Create secure subprocess runner
        subprocess_runner = SecureSubprocessRunner()

        # Build command for generating SVG from PCB using kicad-cli
        command_args = [
            "pcb",
            "export",
            "svg",
            "--output",
            output_file,
            "--layers",
            "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",  # Keep relevant layers
            validated_pcb_file,
        ]

        print(f"Running KiCad CLI command: {' '.join(command_args)}")
        await ctx.report_progress(PROGRESS_CONSTANTS["processing"], PROGRESS_CONSTANTS["complete"])

        # Run the command using secure subprocess runner
        try:
            process = subprocess_runner.run_kicad_command(
                command_args,
                input_files=[validated_pcb_file],
                output_files=[output_file],
                working_dir=validated_project_dir,
                timeout=TIMEOUT_CONSTANTS["kicad_cli_export"],
            )

            if process.returncode != 0:
                print(f"Command failed with code {process.returncode}")
                print(f"Stderr: {process.stderr}")
                print(f"Stdout: {process.stdout}")
                await ctx.info(f"KiCad CLI command failed: {process.stderr or process.stdout}")
                return None

            print(f"Command successful: {process.stdout}")
            await ctx.report_progress(
                PROGRESS_CONSTANTS["finishing"], PROGRESS_CONSTANTS["complete"]
            )

            # Check if the output file was created
            if not os.path.exists(output_file):
                print(f"Output file not created: {output_file}")
                return None

            # Read the image file
            with open(output_file, "rb") as f:
                img_data = f.read()

            print(f"Successfully generated thumbnail with CLI, size: {len(img_data)} bytes")
            await ctx.report_progress(
                PROGRESS_CONSTANTS["validation"], PROGRESS_CONSTANTS["complete"]
            )
            # Inform user about the saved file
            await ctx.info(f"Thumbnail saved to: {output_file}")
            return Image(data=img_data, format="svg")

        except SecureSubprocessError as e:
            print(f"Secure subprocess error: {e}")
            await ctx.info(f"KiCad CLI command failed: {e}")
            return None
        except Exception as e:
            print(f"Error running CLI command: {str(e)}", exc_info=True)
            await ctx.info(f"Error running KiCad CLI: {str(e)}")
            return None

    except asyncio.CancelledError:
        print("CLI thumbnail generation cancelled")
        raise
    except Exception as e:
        print(f"Unexpected error in CLI thumbnail generation: {str(e)}")
        await ctx.info(f"Unexpected error: {str(e)}")
        return None

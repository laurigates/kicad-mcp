"""Design Rule Check (DRC) implementation using KiCad command-line interface.

Runs ``kicad-cli pcb drc`` and parses the JSON report.
"""

import json
import logging
import os
import tempfile
from typing import Any

from fastmcp import Context

from kicad_mcp.utils.kicad_cli import KiCadCLIError, find_kicad_cli
from kicad_mcp.utils.secure_subprocess import SecureSubprocessError, get_subprocess_runner

logger = logging.getLogger(__name__)


async def run_drc_via_cli(pcb_file: str, ctx: Context | None = None) -> dict[str, Any]:
    """Run DRC using KiCad command line tools.

    Args:
        pcb_file: Path to the PCB file (.kicad_pcb)
        ctx: MCP context for progress reporting

    Returns:
        Dictionary with DRC results
    """
    results = {"success": False, "method": "cli", "pcb_file": pcb_file}

    try:
        # Create a temporary directory for the output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Output file for DRC report
            output_file = os.path.join(temp_dir, "drc_report.json")

            # Find kicad-cli executable
            kicad_cli = find_kicad_cli()
            if not kicad_cli:
                logger.warning("kicad-cli not found in PATH or common installation locations")
                results["error"] = (
                    "kicad-cli not found. Please ensure KiCad 9.0+ is installed and kicad-cli is available."
                )
                return results

            # Report progress
            if ctx:
                await ctx.report_progress(50, 100)
                await ctx.info("Running DRC using KiCad CLI...")

            # Build the DRC command args (without kicad-cli executable)
            command_args = ["pcb", "drc", "--format", "json", "--output", output_file, pcb_file]

            logger.debug("Running DRC command via SecureSubprocessRunner")
            try:
                runner = get_subprocess_runner()
                process = runner.run_kicad_command(
                    command_args=command_args,
                    input_files=[pcb_file],
                    output_files=[output_file],
                )
            except (SecureSubprocessError, KiCadCLIError) as e:
                logger.error("DRC command failed: %s", e)
                results["error"] = f"DRC command failed: {e}"
                return results

            # Check if the command was successful
            if process.returncode != 0:
                logger.error("DRC command failed with code %d", process.returncode)
                logger.error("Error output: %s", process.stderr)
                results["error"] = f"DRC command failed: {process.stderr}"
                return results

            # Check if the output file was created
            if not os.path.exists(output_file):
                logger.error("DRC report file not created")
                results["error"] = "DRC report file not created"
                return results

            # Read the DRC report
            with open(output_file) as f:
                try:
                    drc_report = json.load(f)
                except json.JSONDecodeError:
                    logger.error("Failed to parse DRC report JSON")
                    results["error"] = "Failed to parse DRC report JSON"
                    return results

            # Process the DRC report
            violations = drc_report.get("violations", [])
            violation_count = len(violations)
            logger.info("DRC completed with %d violations", violation_count)
            if ctx:
                await ctx.report_progress(70, 100)
                await ctx.info(f"DRC completed with {violation_count} violations")

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
                "violations": violations,
            }

            if ctx:
                await ctx.report_progress(90, 100)
            return results

    except (OSError, json.JSONDecodeError, KeyError, SecureSubprocessError, KiCadCLIError) as e:
        logger.error("Error in CLI DRC: %s", e, exc_info=True)
        results["error"] = f"Error in CLI DRC: {str(e)}"
        return results

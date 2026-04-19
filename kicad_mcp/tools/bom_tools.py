"""Bill of Materials (BOM) processing tools for KiCad projects.

Registers MCP tools for analyzing and exporting BOMs, plus helper
functions for parsing CSV/XML/JSON BOM files.
"""

import csv
import json
import logging
import os
from typing import Any

from fastmcp import Context, FastMCP
import pandas as pd

from kicad_mcp.utils.file_utils import get_project_files

logger = logging.getLogger(__name__)


def register_bom_tools(mcp: FastMCP) -> None:
    """Register BOM-related tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """

    @mcp.tool()
    async def analyze_bom(project_path: str, ctx: Context) -> dict[str, Any]:
        """Analyze a KiCad project's Bill of Materials.

        This tool will look for BOM files related to a KiCad project and provide
        analysis including component counts, categories, and cost estimates if available.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: MCP context for progress reporting

        Returns:
            Dictionary with BOM analysis results
        """
        logger.info("Analyzing BOM for project: %s", project_path)

        if not os.path.exists(project_path):
            logger.warning("Project not found: %s", project_path)
            await ctx.info(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}

        # Report progress
        await ctx.report_progress(10, 100)
        await ctx.info(f"Looking for BOM files related to {os.path.basename(project_path)}")

        # Get all project files
        files = get_project_files(project_path)

        # Look for BOM files
        bom_files = {}
        for file_type, file_path in files.items():
            if "bom" in file_type.lower() or file_path.lower().endswith(".csv"):
                bom_files[file_type] = file_path
                logger.debug("Found potential BOM file: %s", file_path)

        if not bom_files:
            logger.info("No BOM files found for project")
            await ctx.info("No BOM files found for project")
            return {
                "success": False,
                "error": "No BOM files found. Export a BOM from KiCad first.",
                "project_path": project_path,
            }

        await ctx.report_progress(30, 100)

        # Analyze each BOM file
        results = {
            "success": True,
            "project_path": project_path,
            "bom_files": {},
            "component_summary": {},
        }

        total_unique_components = 0
        total_components = 0

        for file_type, file_path in bom_files.items():
            try:
                await ctx.info(f"Analyzing {os.path.basename(file_path)}")

                # Parse the BOM file
                bom_data, format_info = parse_bom_file(file_path)

                if not bom_data or len(bom_data) == 0:
                    logger.warning("Failed to parse BOM file: %s", file_path)
                    continue

                # Analyze the BOM data
                analysis = analyze_bom_data(bom_data, format_info)

                # Add to results
                results["bom_files"][file_type] = {
                    "path": file_path,
                    "format": format_info,
                    "analysis": analysis,
                }

                # Update totals
                total_unique_components += analysis["unique_component_count"]
                total_components += analysis["total_component_count"]

                logger.info("Successfully analyzed BOM file: %s", file_path)

            except (OSError, ValueError, KeyError) as e:
                logger.error("Error analyzing BOM file %s: %s", file_path, e, exc_info=True)
                results["bom_files"][file_type] = {"path": file_path, "error": str(e)}

        await ctx.report_progress(70, 100)

        # Generate overall component summary
        if total_components > 0:
            results["component_summary"] = {
                "total_unique_components": total_unique_components,
                "total_components": total_components,
            }

            # Calculate component categories across all BOMs
            all_categories = {}
            for _, file_info in results["bom_files"].items():
                if "analysis" in file_info and "categories" in file_info["analysis"]:
                    for category, count in file_info["analysis"]["categories"].items():
                        if category not in all_categories:
                            all_categories[category] = 0
                        all_categories[category] += count

            results["component_summary"]["categories"] = all_categories

            # Calculate total cost if available
            total_cost = 0.0
            cost_available = False
            for _, file_info in results["bom_files"].items():
                if (
                    "analysis" in file_info
                    and "total_cost" in file_info["analysis"]
                    and file_info["analysis"]["total_cost"] > 0
                ):
                    total_cost += file_info["analysis"]["total_cost"]
                    cost_available = True

            if cost_available:
                results["component_summary"]["total_cost"] = round(total_cost, 2)
                currency = next(
                    (
                        file_info["analysis"].get("currency", "USD")
                        for file_type, file_info in results["bom_files"].items()
                        if "analysis" in file_info and "currency" in file_info["analysis"]
                    ),
                    "USD",
                )
                results["component_summary"]["currency"] = currency

        await ctx.report_progress(100, 100)
        await ctx.info(f"BOM analysis complete: found {total_components} components")

        return results

    @mcp.tool()
    async def export_bom_csv(project_path: str, ctx: Context) -> dict[str, Any]:
        """Export a Bill of Materials for a KiCad project.

        This tool attempts to generate a CSV BOM file for a KiCad project.
        It requires KiCad to be installed with the appropriate command-line tools.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: MCP context for progress reporting

        Returns:
            Dictionary with export results
        """
        logger.info("Exporting BOM for project: %s", project_path)

        if not os.path.exists(project_path):
            logger.warning("Project not found: %s", project_path)
            await ctx.info(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}

        # Report progress
        await ctx.report_progress(10, 100)

        # Get all project files
        files = get_project_files(project_path)

        # We need the schematic file to generate a BOM
        if "schematic" not in files:
            logger.warning("Schematic file not found in project")
            await ctx.info("Schematic file not found in project")
            return {"success": False, "error": "Schematic file not found"}

        schematic_file = files["schematic"]
        project_dir = os.path.dirname(project_path)
        project_name = os.path.basename(project_path)[:-10]  # Remove .kicad_pro extension

        await ctx.report_progress(20, 100)
        await ctx.info(f"Found schematic file: {os.path.basename(schematic_file)}")

        # Export BOM using command-line tools
        export_result = {"success": False}
        try:
            await ctx.info("Attempting to export BOM using command-line tools...")
            export_result = await export_bom_with_cli(
                schematic_file, project_dir, project_name, ctx
            )
        except (OSError, ValueError) as e:
            logger.error("Error exporting BOM with CLI: %s", e, exc_info=True)
            await ctx.info(f"Error using command-line tools: {str(e)}")
            export_result = {"success": False, "error": str(e)}

        await ctx.report_progress(100, 100)

        if export_result.get("success", False):
            await ctx.info(
                f"BOM exported successfully to {export_result.get('output_file', 'unknown location')}"
            )
        else:
            await ctx.info(f"Failed to export BOM: {export_result.get('error', 'Unknown error')}")

        return export_result


# Helper functions for BOM processing


def parse_bom_file(file_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse a BOM file and detect its format.

    Args:
        file_path: Path to the BOM file

    Returns:
        Tuple containing:
            - List of component dictionaries
            - Dictionary with format information
    """
    logger.debug("Parsing BOM file: %s", file_path)

    # Check file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # Dictionary to store format detection info
    format_info: dict[str, Any] = {
        "file_type": ext,
        "detected_format": "unknown",
        "header_fields": [],
    }

    # Empty list to store component data
    components = []

    try:
        if ext == ".csv":
            # Try to parse as CSV
            with open(file_path, encoding="utf-8-sig") as f:
                # Read a few lines to analyze the format
                sample = "".join([f.readline() for _ in range(10)])
                f.seek(0)  # Reset file pointer

                # Try to detect the delimiter
                if "," in sample:
                    delimiter = ","
                elif ";" in sample:
                    delimiter = ";"
                elif "\t" in sample:
                    delimiter = "\t"
                else:
                    delimiter = ","  # Default

                format_info["delimiter"] = delimiter

                # Read CSV
                reader = csv.DictReader(f, delimiter=delimiter)
                format_info["header_fields"] = reader.fieldnames if reader.fieldnames else []

                # Detect BOM format based on header fields
                header_str = ",".join(format_info["header_fields"]).lower()

                if "reference" in header_str and "value" in header_str:
                    format_info["detected_format"] = "kicad"
                elif "designator" in header_str:
                    format_info["detected_format"] = "altium"
                elif "part number" in header_str or "manufacturer part" in header_str:
                    format_info["detected_format"] = "generic"

                # Read components
                for row in reader:
                    components.append(dict(row))

        elif ext == ".xml":
            # Basic XML parsing with security protection
            from defusedxml.ElementTree import parse as safe_parse

            tree = safe_parse(file_path)
            root = tree.getroot()

            format_info["detected_format"] = "xml"

            # Try to extract components based on common XML BOM formats
            component_elements = root.findall(".//component") or root.findall(".//Component")

            if component_elements:
                for elem in component_elements:
                    component = {}
                    for attr in elem.attrib:
                        component[attr] = elem.attrib[attr]
                    for child in elem:
                        component[child.tag] = child.text
                    components.append(component)

        elif ext == ".json":
            # Parse JSON
            with open(file_path) as f:
                data = json.load(f)

            format_info["detected_format"] = "json"

            # Try to find components array in common JSON formats
            if isinstance(data, list):
                components = data
            elif "components" in data:
                components = data["components"]
            elif "parts" in data:
                components = data["parts"]

        else:
            # Unknown format, try generic CSV parsing as fallback
            try:
                with open(file_path, encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    format_info["header_fields"] = reader.fieldnames if reader.fieldnames else []
                    format_info["detected_format"] = "unknown_csv"

                    for row in reader:
                        components.append(dict(row))
            except (OSError, csv.Error, UnicodeDecodeError):
                logger.warning("Failed to parse unknown file format: %s", file_path)
                return [], {"detected_format": "unsupported"}

    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as e:
        logger.error("Error parsing BOM file: %s", e, exc_info=True)
        return [], {"error": str(e)}

    # Check if we actually got components
    if not components:
        logger.warning("No components found in BOM file: %s", file_path)
    else:
        logger.debug("Successfully parsed %d components from %s", len(components), file_path)

        # Add a sample of the fields found
        if components:
            format_info["sample_fields"] = list(components[0].keys())

    return components, format_info


def analyze_bom_data(
    components: list[dict[str, Any]], format_info: dict[str, Any]
) -> dict[str, Any]:
    """Analyze component data from a BOM file.

    Args:
        components: List of component dictionaries
        format_info: Dictionary with format information

    Returns:
        Dictionary with analysis results
    """
    logger.debug("Analyzing %d components", len(components))

    # Initialize results
    results: dict[str, Any] = {
        "unique_component_count": 0,
        "total_component_count": 0,
        "categories": {},
        "has_cost_data": False,
    }

    if not components:
        return results

    # Try to convert to pandas DataFrame for easier analysis
    try:
        df = pd.DataFrame(components)

        # Clean up column names
        df.columns = [str(col).strip().lower() for col in df.columns]

        # Try to identify key columns based on format
        ref_col = None
        value_col = None
        quantity_col = None
        footprint_col = None
        cost_col = None
        category_col = None

        # Check for reference designator column
        for possible_col in [
            "reference",
            "designator",
            "references",
            "designators",
            "refdes",
            "ref",
        ]:
            if possible_col in df.columns:
                ref_col = possible_col
                break

        # Check for value column
        for possible_col in ["value", "component", "comp", "part", "component value", "comp value"]:
            if possible_col in df.columns:
                value_col = possible_col
                break

        # Check for quantity column
        for possible_col in ["quantity", "qty", "count", "amount"]:
            if possible_col in df.columns:
                quantity_col = possible_col
                break

        # Check for footprint column
        for possible_col in ["footprint", "package", "pattern", "pcb footprint"]:
            if possible_col in df.columns:
                footprint_col = possible_col
                break

        # Check for cost column
        for possible_col in ["cost", "price", "unit price", "unit cost", "cost each"]:
            if possible_col in df.columns:
                cost_col = possible_col
                break

        # Check for category column
        for possible_col in ["category", "type", "group", "component type", "lib"]:
            if possible_col in df.columns:
                category_col = possible_col
                break

        # Count total components
        if quantity_col:
            # Try to convert quantity to numeric
            df[quantity_col] = pd.to_numeric(df[quantity_col], errors="coerce").fillna(1)
            results["total_component_count"] = int(df[quantity_col].sum())
        else:
            # If no quantity column, assume each row is one component
            results["total_component_count"] = len(df)

        # Count unique components
        results["unique_component_count"] = len(df)

        # Calculate categories
        if category_col:
            # Use provided category column
            categories = df[category_col].value_counts().to_dict()
            results["categories"] = {str(k): int(v) for k, v in categories.items()}
        elif footprint_col:
            # Use footprint as category
            categories = df[footprint_col].value_counts().to_dict()
            results["categories"] = {str(k): int(v) for k, v in categories.items()}
        elif ref_col:
            # Try to extract categories from reference designators (R=resistor, C=capacitor, etc.)
            def extract_prefix(ref):
                if isinstance(ref, str):
                    import re

                    match = re.match(r"^([A-Za-z]+)", ref)
                    if match:
                        return match.group(1)
                return "Other"

            if isinstance(df[ref_col].iloc[0], str) and "," in df[ref_col].iloc[0]:
                # Multiple references in one cell
                all_refs = []
                for refs in df[ref_col]:
                    all_refs.extend([r.strip() for r in refs.split(",")])

                categories = {}
                for ref in all_refs:
                    prefix = extract_prefix(ref)
                    categories[prefix] = categories.get(prefix, 0) + 1

                results["categories"] = categories
            else:
                # Single reference per row
                categories = df[ref_col].apply(extract_prefix).value_counts().to_dict()
                results["categories"] = {str(k): int(v) for k, v in categories.items()}

        # Map common reference prefixes to component types
        category_mapping = {
            "R": "Resistors",
            "C": "Capacitors",
            "L": "Inductors",
            "D": "Diodes",
            "Q": "Transistors",
            "U": "ICs",
            "SW": "Switches",
            "J": "Connectors",
            "K": "Relays",
            "Y": "Crystals/Oscillators",
            "F": "Fuses",
            "T": "Transformers",
        }

        mapped_categories = {}
        for cat, count in results["categories"].items():
            if cat in category_mapping:
                mapped_name = category_mapping[cat]
                mapped_categories[mapped_name] = mapped_categories.get(mapped_name, 0) + count
            else:
                mapped_categories[cat] = count

        results["categories"] = mapped_categories

        # Calculate cost if available
        if cost_col:
            try:
                # Try to extract numeric values from cost field
                df[cost_col] = df[cost_col].astype(str).str.replace("$", "").str.replace(",", "")
                df[cost_col] = pd.to_numeric(df[cost_col], errors="coerce")

                # Remove NaN values
                df_with_cost = df.dropna(subset=[cost_col])

                if not df_with_cost.empty:
                    results["has_cost_data"] = True

                    if quantity_col:
                        total_cost = (df_with_cost[cost_col] * df_with_cost[quantity_col]).sum()
                    else:
                        total_cost = df_with_cost[cost_col].sum()

                    results["total_cost"] = round(float(total_cost), 2)

                    # Try to determine currency
                    # Check first row that has cost for currency symbols
                    for _, row in df.iterrows():
                        cost_str = str(row.get(cost_col, ""))
                        if "$" in cost_str:
                            results["currency"] = "USD"
                            break
                        elif "€" in cost_str:
                            results["currency"] = "EUR"
                            break
                        elif "£" in cost_str:
                            results["currency"] = "GBP"
                            break

                    if "currency" not in results:
                        results["currency"] = "USD"  # Default
            except (ValueError, TypeError, KeyError):
                logger.warning("Failed to parse cost data")

        # Add extra insights
        if ref_col and value_col:
            # Check for common components by value
            value_counts = df[value_col].value_counts()
            most_common = value_counts.head(5).to_dict()
            results["most_common_values"] = {str(k): int(v) for k, v in most_common.items()}

    except (ValueError, TypeError, KeyError) as e:
        logger.error("Error analyzing BOM data: %s", e, exc_info=True)
        # Fallback to basic analysis
        results["unique_component_count"] = len(components)
        results["total_component_count"] = len(components)

    return results


async def export_bom_with_cli(
    schematic_file: str, output_dir: str, project_name: str, ctx: Context
) -> dict[str, Any]:
    """Export a BOM using KiCad command-line tools.

    Args:
        schematic_file: Path to the schematic file
        output_dir: Directory to save the BOM
        project_name: Name of the project
        ctx: MCP context for progress reporting

    Returns:
        Dictionary with export results
    """
    from kicad_mcp.utils.kicad_cli import KiCadCLIError
    from kicad_mcp.utils.secure_subprocess import SecureSubprocessError, get_subprocess_runner

    logger.info("Exporting BOM using CLI tools via SecureSubprocessRunner")
    await ctx.report_progress(40, 100)

    # Output file path
    output_file = os.path.join(output_dir, f"{project_name}_bom.csv")

    # Command args (without kicad-cli executable - SecureSubprocessRunner resolves it)
    command_args = ["sch", "export", "bom", "--output", output_file, schematic_file]

    try:
        logger.info("Running BOM export command via SecureSubprocessRunner")
        await ctx.report_progress(60, 100)

        runner = get_subprocess_runner()
        process = runner.run_kicad_command(
            command_args=command_args,
            input_files=[schematic_file],
            output_files=[output_file],
        )

        # Check if the command was successful
        if process.returncode != 0:
            logger.error("BOM export command failed with code %d", process.returncode)
            logger.error("Error output: %s", process.stderr)

            return {
                "success": False,
                "error": f"BOM export command failed: {process.stderr}",
                "schematic_file": schematic_file,
            }

        # Check if the output file was created
        if not os.path.exists(output_file):
            return {
                "success": False,
                "error": "BOM file was not created",
                "schematic_file": schematic_file,
                "output_file": output_file,
            }

        await ctx.report_progress(80, 100)

        # Read the first few lines of the BOM to verify it's valid
        with open(output_file) as f:
            bom_content = f.read(1024)  # Read first 1KB

        if len(bom_content.strip()) == 0:
            return {
                "success": False,
                "error": "Generated BOM file is empty",
                "schematic_file": schematic_file,
                "output_file": output_file,
            }

        return {
            "success": True,
            "schematic_file": schematic_file,
            "output_file": output_file,
            "file_size": os.path.getsize(output_file),
            "message": "BOM exported successfully",
        }

    except (SecureSubprocessError, KiCadCLIError) as e:
        logger.error("BOM export command failed: %s", e)
        return {
            "success": False,
            "error": f"BOM export command failed: {e}",
            "schematic_file": schematic_file,
        }

    except OSError as e:
        logger.error("Error exporting BOM: %s", e, exc_info=True)
        return {
            "success": False,
            "error": f"Error exporting BOM: {str(e)}",
            "schematic_file": schematic_file,
        }

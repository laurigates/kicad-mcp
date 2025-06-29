"""
Circuit creation tools for KiCad projects.
"""
import os
import json
import shutil
import subprocess
import tempfile
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP, Context

from kicad_mcp.config import KICAD_APP_PATH, KICAD_EXTENSIONS, system
from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.sexpr_generator import SExpressionGenerator


def register_circuit_tools(mcp: FastMCP) -> None:
    """Register circuit creation tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    async def create_new_project(
        project_name: str,
        project_path: str,
        description: str = "",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Create a new KiCad project with basic files.

        Args:
            project_name: Name of the new project
            project_path: Directory path where the project will be created
            description: Optional project description
            ctx: Context for MCP communication

        Returns:
            Dictionary with project creation status and file paths
        """
        try:
            if ctx:
                await ctx.info(f"Creating new KiCad project: {project_name}")
                await ctx.report_progress(10, 100)

            # Ensure project directory exists
            os.makedirs(project_path, exist_ok=True)
            
            # Define file paths
            project_file = os.path.join(project_path, f"{project_name}.kicad_pro")
            schematic_file = os.path.join(project_path, f"{project_name}.kicad_sch")
            pcb_file = os.path.join(project_path, f"{project_name}.kicad_pcb")
            
            if ctx:
                await ctx.report_progress(30, 100)

            # Check if project already exists
            if os.path.exists(project_file):
                return {
                    "success": False,
                    "error": f"Project already exists at {project_file}"
                }

            # Create basic project file
            project_data = {
                "board": {
                    "3dviewports": [],
                    "design_settings": {
                        "defaults": {
                            "board_outline_line_width": 0.1,
                            "copper_line_width": 0.2
                        }
                    },
                    "layer_presets": [],
                    "viewports": []
                },
                "libraries": {
                    "pinned_footprint_libs": [],
                    "pinned_symbol_libs": []
                },
                "meta": {
                    "filename": f"{project_name}.kicad_pro",
                    "version": 1
                },
                "net_settings": {
                    "classes": [
                        {
                            "clearance": 0.2,
                            "diff_pair_gap": 0.25,
                            "diff_pair_via_gap": 0.25,
                            "diff_pair_width": 0.2,
                            "line_style": 0,
                            "microvia_diameter": 0.3,
                            "microvia_drill": 0.1,
                            "name": "Default",
                            "pcb_color": "rgba(0, 0, 0, 0.000)",
                            "schematic_color": "rgba(0, 0, 0, 0.000)",
                            "track_width": 0.25,
                            "via_diameter": 0.8,
                            "via_drill": 0.4,
                            "wire_width": 6
                        }
                    ],
                    "meta": {
                        "version": 3
                    }
                },
                "pcbnew": {
                    "last_paths": {
                        "gencad": "",
                        "idf": "",
                        "netlist": "",
                        "specctra_dsn": "",
                        "step": "",
                        "vrml": ""
                    },
                    "page_layout_descr_file": ""
                },
                "schematic": {
                    "annotate_start_num": 0,
                    "drawing": {
                        "dashed_lines_dash_length_ratio": 12.0,
                        "dashed_lines_gap_length_ratio": 3.0,
                        "default_line_thickness": 6.0,
                        "default_text_size": 50.0,
                        "field_names": [],
                        "intersheets_ref_own_page": False,
                        "intersheets_ref_prefix": "",
                        "intersheets_ref_short": False,
                        "intersheets_ref_show": False,
                        "intersheets_ref_suffix": "",
                        "junction_size_choice": 3,
                        "label_size_ratio": 0.375,
                        "pin_symbol_size": 25.0,
                        "text_offset_ratio": 0.15
                    },
                    "legacy_lib_dir": "",
                    "legacy_lib_list": [],
                    "meta": {
                        "version": 1
                    },
                    "net_format_name": "",
                    "page_layout_descr_file": "",
                    "plot_directory": "",
                    "spice_current_sheet_as_root": False,
                    "spice_external_command": "spice \"%I\"",
                    "spice_model_current_sheet_as_root": True,
                    "spice_save_all_currents": False,
                    "spice_save_all_voltages": False,
                    "subpart_first_id": 65,
                    "subpart_id_separator": 0
                },
                "sheets": [
                    [
                        "e63e39d7-6ac0-4ffd-8aa3-1841a4541b55",
                        ""
                    ]
                ],
                "text_variables": {}
            }

            if description:
                project_data["meta"]["description"] = description

            with open(project_file, 'w') as f:
                json.dump(project_data, f, indent=2)

            if ctx:
                await ctx.report_progress(60, 100)

            # Create basic schematic file using S-expression format
            generator = SExpressionGenerator()
            schematic_content = generator.generate_schematic(
                circuit_name=project_name,
                components=[],
                power_symbols=[],
                connections=[]
            )

            with open(schematic_file, 'w') as f:
                f.write(schematic_content)

            if ctx:
                await ctx.report_progress(80, 100)

            # Create basic PCB file
            pcb_data = {
                "version": 20230121,
                "generator": "kicad-mcp",
                "general": {
                    "thickness": 1.6
                },
                "paper": "A4",
                "title_block": {
                    "title": project_name,
                    "date": "",
                    "rev": "",
                    "company": "",
                    "comment": [
                        {
                            "number": 1,
                            "value": description if description else ""
                        }
                    ]
                },
                "layers": [
                    {
                        "ordinal": 0,
                        "name": "F.Cu",
                        "type": "signal"
                    },
                    {
                        "ordinal": 31,
                        "name": "B.Cu",
                        "type": "signal"
                    },
                    {
                        "ordinal": 32,
                        "name": "B.Adhes",
                        "type": "user"
                    },
                    {
                        "ordinal": 33,
                        "name": "F.Adhes",
                        "type": "user"
                    },
                    {
                        "ordinal": 34,
                        "name": "B.Paste",
                        "type": "user"
                    },
                    {
                        "ordinal": 35,
                        "name": "F.Paste",
                        "type": "user"
                    },
                    {
                        "ordinal": 36,
                        "name": "B.SilkS",
                        "type": "user"
                    },
                    {
                        "ordinal": 37,
                        "name": "F.SilkS",
                        "type": "user"
                    },
                    {
                        "ordinal": 38,
                        "name": "B.Mask",
                        "type": "user"
                    },
                    {
                        "ordinal": 39,
                        "name": "F.Mask",
                        "type": "user"
                    },
                    {
                        "ordinal": 44,
                        "name": "Edge.Cuts",
                        "type": "user"
                    },
                    {
                        "ordinal": 45,
                        "name": "Margin",
                        "type": "user"
                    },
                    {
                        "ordinal": 46,
                        "name": "B.CrtYd",
                        "type": "user"
                    },
                    {
                        "ordinal": 47,
                        "name": "F.CrtYd",
                        "type": "user"
                    },
                    {
                        "ordinal": 48,
                        "name": "B.Fab",
                        "type": "user"
                    },
                    {
                        "ordinal": 49,
                        "name": "F.Fab",
                        "type": "user"
                    }
                ],
                "setup": {
                    "pad_to_mask_clearance": 0,
                    "pcbplotparams": {
                        "layerselection": "0x00010fc_ffffffff",
                        "disableapertmacros": False,
                        "usegerberextensions": False,
                        "usegerberattributes": True,
                        "usegerberadvancedattributes": True,
                        "creategerberjobfile": True,
                        "svguseinch": False,
                        "svgprecision": 6,
                        "excludeedgelayer": True,
                        "plotframeref": False,
                        "viasonmask": False,
                        "mode": 1,
                        "useauxorigin": False,
                        "hpglpennumber": 1,
                        "hpglpenspeed": 20,
                        "hpglpendiameter": 15.0,
                        "dxfpolygonmode": True,
                        "dxfimperialunits": True,
                        "dxfusepcbnewfont": True,
                        "psnegative": False,
                        "psa4output": False,
                        "plotreference": True,
                        "plotvalue": True,
                        "plotinvisibletext": False,
                        "sketchpadsonfab": False,
                        "subtractmaskfromsilk": False,
                        "outputformat": 1,
                        "mirror": False,
                        "drillshape": 1,
                        "scaleselection": 1,
                        "outputdirectory": ""
                    }
                },
                "net": [
                    {
                        "code": 0,
                        "name": ""
                    }
                ],
                "footprint": [],
                "track": [],
                "via": [],
                "zone": [],
                "target": []
            }

            with open(pcb_file, 'w') as f:
                json.dump(pcb_data, f, indent=2)

            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info(f"Successfully created project at {project_file}")

            return {
                "success": True,
                "project_file": project_file,
                "schematic_file": schematic_file,
                "pcb_file": pcb_file,
                "project_path": project_path,
                "project_name": project_name
            }

        except Exception as e:
            if ctx:
                await ctx.info(f"Error creating project: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def add_component(
        project_path: str,
        component_reference: str,
        component_value: str,
        symbol_library: str,
        symbol_name: str,
        x_position: float,
        y_position: float,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Add a component to a KiCad schematic.
        
        WARNING: This tool modifies existing schematic files but may not preserve
        S-expression format if the file was created with proper KiCad tools.
        Prefer using create_kicad_schematic_from_text for new schematics.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            component_reference: Component reference designator (e.g., "R1", "C1")
            component_value: Component value (e.g., "10k", "100nF")
            symbol_library: Name of the symbol library
            symbol_name: Name of the symbol in the library
            x_position: X coordinate for component placement (in mm)
            y_position: Y coordinate for component placement (in mm)
            ctx: Context for MCP communication

        Returns:
            Dictionary with component addition status
        """
        try:
            if ctx:
                await ctx.info(f"Adding component {component_reference} to schematic")
                await ctx.report_progress(10, 100)

            # Get project files
            files = get_project_files(project_path)
            if "schematic" not in files:
                return {
                    "success": False,
                    "error": "No schematic file found in project"
                }

            schematic_file = files["schematic"]
            
            if ctx:
                await ctx.report_progress(30, 100)

            # Read existing schematic
            with open(schematic_file, 'r') as f:
                schematic_data = json.load(f)

            # Create component UUID
            component_uuid = str(uuid.uuid4())

            # Convert positions to KiCad internal units (0.1mm)
            x_pos_internal = int(x_position * 10)
            y_pos_internal = int(y_position * 10)

            if ctx:
                await ctx.report_progress(50, 100)

            # Create symbol entry
            symbol_entry = {
                "lib_id": f"{symbol_library}:{symbol_name}",
                "at": [x_pos_internal, y_pos_internal, 0],
                "uuid": component_uuid,
                "property": [
                    {
                        "name": "Reference",
                        "value": component_reference,
                        "at": [x_pos_internal, y_pos_internal - 254, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            }
                        }
                    },
                    {
                        "name": "Value",
                        "value": component_value,
                        "at": [x_pos_internal, y_pos_internal + 254, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            }
                        }
                    },
                    {
                        "name": "Footprint",
                        "value": "",
                        "at": [x_pos_internal, y_pos_internal, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            },
                            "hide": True
                        }
                    },
                    {
                        "name": "Datasheet",
                        "value": "",
                        "at": [x_pos_internal, y_pos_internal, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            },
                            "hide": True
                        }
                    }
                ],
                "pin": []
            }

            # Add symbol to schematic
            if "symbol" not in schematic_data:
                schematic_data["symbol"] = []
            
            schematic_data["symbol"].append(symbol_entry)

            if ctx:
                await ctx.report_progress(80, 100)

            # Write updated schematic
            with open(schematic_file, 'w') as f:
                json.dump(schematic_data, f, indent=2)

            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info(f"Successfully added component {component_reference}")

            return {
                "success": True,
                "component_reference": component_reference,
                "component_uuid": component_uuid,
                "position": [x_position, y_position]
            }

        except Exception as e:
            if ctx:
                await ctx.info(f"Error adding component: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def create_wire_connection(
        project_path: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Create a wire connection between two points in a schematic.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            start_x: Starting X coordinate (in mm)
            start_y: Starting Y coordinate (in mm)
            end_x: Ending X coordinate (in mm)
            end_y: Ending Y coordinate (in mm)
            ctx: Context for MCP communication

        Returns:
            Dictionary with wire creation status
        """
        try:
            if ctx:
                await ctx.info("Creating wire connection")
                await ctx.report_progress(10, 100)

            # Get project files
            files = get_project_files(project_path)
            if "schematic" not in files:
                return {
                    "success": False,
                    "error": "No schematic file found in project"
                }

            schematic_file = files["schematic"]
            
            if ctx:
                await ctx.report_progress(30, 100)

            # Read existing schematic
            with open(schematic_file, 'r') as f:
                schematic_data = json.load(f)

            # Convert positions to KiCad internal units
            start_x_internal = int(start_x * 10)
            start_y_internal = int(start_y * 10)
            end_x_internal = int(end_x * 10)
            end_y_internal = int(end_y * 10)

            if ctx:
                await ctx.report_progress(50, 100)

            # Create wire entry
            wire_entry = {
                "pts": [
                    [start_x_internal, start_y_internal],
                    [end_x_internal, end_y_internal]
                ],
                "stroke": {
                    "width": 0,
                    "type": "default"
                },
                "uuid": str(uuid.uuid4())
            }

            # Add wire to schematic
            if "wire" not in schematic_data:
                schematic_data["wire"] = []
            
            schematic_data["wire"].append(wire_entry)

            if ctx:
                await ctx.report_progress(80, 100)

            # Write updated schematic
            with open(schematic_file, 'w') as f:
                json.dump(schematic_data, f, indent=2)

            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info("Successfully created wire connection")

            return {
                "success": True,
                "start_position": [start_x, start_y],
                "end_position": [end_x, end_y],
                "wire_uuid": wire_entry["uuid"]
            }

        except Exception as e:
            if ctx:
                await ctx.info(f"Error creating wire: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def add_power_symbol(
        project_path: str,
        power_type: str,
        x_position: float,
        y_position: float,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Add a power symbol (VCC, GND, etc.) to the schematic.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            power_type: Type of power symbol ("VCC", "GND", "+5V", "+3V3", etc.)
            x_position: X coordinate for symbol placement (in mm)
            y_position: Y coordinate for symbol placement (in mm)
            ctx: Context for MCP communication

        Returns:
            Dictionary with power symbol addition status
        """
        try:
            if ctx:
                await ctx.info(f"Adding {power_type} power symbol")
                await ctx.report_progress(10, 100)

            # Map power types to KiCad symbols
            power_symbols = {
                "VCC": "power:VCC",
                "GND": "power:GND",
                "+5V": "power:+5V",
                "+3V3": "power:+3V3",
                "+12V": "power:+12V",
                "-12V": "power:-12V"
            }

            if power_type not in power_symbols:
                return {
                    "success": False,
                    "error": f"Unknown power type: {power_type}. Available types: {list(power_symbols.keys())}"
                }

            symbol_lib_id = power_symbols[power_type]

            # Manually create power symbol component
            # Get project files
            files = get_project_files(project_path)
            if "schematic" not in files:
                return {
                    "success": False,
                    "error": "No schematic file found in project"
                }

            schematic_file = files["schematic"]
            
            if ctx:
                await ctx.report_progress(30, 100)

            # Read existing schematic
            with open(schematic_file, 'r') as f:
                schematic_data = json.load(f)

            # Create component UUID
            component_uuid = str(uuid.uuid4())

            # Convert positions to KiCad internal units (0.1mm)
            x_pos_internal = int(x_position * 10)
            y_pos_internal = int(y_position * 10)

            # Generate power reference
            power_ref = f"#PWR0{len([s for s in schematic_data.get('symbol', []) if s.get('lib_id', '').startswith('power:')]) + 1:03d}"

            if ctx:
                await ctx.report_progress(50, 100)

            # Create symbol entry
            symbol_entry = {
                "lib_id": symbol_lib_id,
                "at": [x_pos_internal, y_pos_internal, 0],
                "uuid": component_uuid,
                "property": [
                    {
                        "name": "Reference",
                        "value": power_ref,
                        "at": [x_pos_internal, y_pos_internal - 254, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            }
                        }
                    },
                    {
                        "name": "Value",
                        "value": power_type,
                        "at": [x_pos_internal, y_pos_internal + 254, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            }
                        }
                    },
                    {
                        "name": "Footprint",
                        "value": "",
                        "at": [x_pos_internal, y_pos_internal, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            },
                            "hide": True
                        }
                    },
                    {
                        "name": "Datasheet",
                        "value": "",
                        "at": [x_pos_internal, y_pos_internal, 0],
                        "effects": {
                            "font": {
                                "size": [1.27, 1.27]
                            },
                            "hide": True
                        }
                    }
                ],
                "pin": []
            }

            # Add symbol to schematic
            if "symbol" not in schematic_data:
                schematic_data["symbol"] = []
            
            schematic_data["symbol"].append(symbol_entry)

            if ctx:
                await ctx.report_progress(80, 100)

            # Write updated schematic
            with open(schematic_file, 'w') as f:
                json.dump(schematic_data, f, indent=2)

            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info(f"Successfully added power symbol {power_ref}")

            result = {
                "success": True,
                "component_reference": power_ref,
                "component_uuid": component_uuid,
                "position": [x_position, y_position]
            }

            if result["success"]:
                result["power_type"] = power_type

            return result

        except Exception as e:
            if ctx:
                await ctx.info(f"Error adding power symbol: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def validate_schematic(
        project_path: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Validate a KiCad schematic for common issues.

        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: Context for MCP communication

        Returns:
            Dictionary with validation results
        """
        try:
            if ctx:
                await ctx.info("Validating schematic")
                await ctx.report_progress(10, 100)

            # Get project files
            files = get_project_files(project_path)
            if "schematic" not in files:
                return {
                    "success": False,
                    "error": "No schematic file found in project"
                }

            schematic_file = files["schematic"]
            
            if ctx:
                await ctx.report_progress(30, 100)

            # Read schematic
            with open(schematic_file, 'r') as f:
                schematic_data = json.load(f)

            validation_results = {
                "success": True,
                "issues": [],
                "warnings": [],
                "component_count": 0,
                "wire_count": 0,
                "unconnected_pins": []
            }

            # Count components and wires
            if "symbol" in schematic_data:
                validation_results["component_count"] = len(schematic_data["symbol"])

            if "wire" in schematic_data:
                validation_results["wire_count"] = len(schematic_data["wire"])

            if ctx:
                await ctx.report_progress(60, 100)

            # Check for components without values
            if "symbol" in schematic_data:
                for symbol in schematic_data["symbol"]:
                    ref = "Unknown"
                    value = "Unknown"
                    
                    if "property" in symbol:
                        for prop in symbol["property"]:
                            if prop["name"] == "Reference":
                                ref = prop["value"]
                            elif prop["name"] == "Value":
                                value = prop["value"]
                    
                    if not value or value == "Unknown" or value == "":
                        validation_results["warnings"].append(
                            f"Component {ref} has no value assigned"
                        )

            # Check for empty schematic
            if validation_results["component_count"] == 0:
                validation_results["warnings"].append("Schematic contains no components")

            # Check for isolated components (no wires)
            if validation_results["component_count"] > 0 and validation_results["wire_count"] == 0:
                validation_results["warnings"].append("Schematic has components but no wire connections")

            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info(f"Validation complete: {len(validation_results['issues'])} issues, {len(validation_results['warnings'])} warnings")

            return validation_results

        except Exception as e:
            if ctx:
                await ctx.info(f"Error validating schematic: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def get_kicad_cli_path() -> Optional[str]:
    """Get the path to kicad-cli executable based on the operating system.
    
    Returns:
        Path to kicad-cli executable or None if not found
    """
    if system == "Darwin":  # macOS
        kicad_cli_path = os.path.join(KICAD_APP_PATH, "Contents/MacOS/kicad-cli")
        if os.path.exists(kicad_cli_path):
            return kicad_cli_path
        elif shutil.which("kicad-cli") is not None:
            return "kicad-cli"
    elif system == "Windows":
        kicad_cli_path = os.path.join(KICAD_APP_PATH, "bin", "kicad-cli.exe")
        if os.path.exists(kicad_cli_path):
            return kicad_cli_path
        elif shutil.which("kicad-cli.exe") is not None:
            return "kicad-cli.exe"
        elif shutil.which("kicad-cli") is not None:
            return "kicad-cli"
    elif system == "Linux":
        kicad_cli = shutil.which("kicad-cli")
        if kicad_cli:
            return kicad_cli
    
    return None
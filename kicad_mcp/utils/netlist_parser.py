"""
KiCad schematic netlist extraction utilities.
"""

from collections import defaultdict
import logging
import math
import os
import re
from typing import Any
import uuid

import sexpdata

from kicad_mcp.utils.connectivity import ConnectivityEngine

logger = logging.getLogger(__name__)


class SchematicParser:
    """Parser for KiCad schematic files to extract netlist information."""

    def __init__(self, schematic_path: str):
        """Initialize the schematic parser.

        Args:
            schematic_path: Path to the KiCad schematic file (.kicad_sch)
        """
        self.schematic_path = schematic_path
        self.content = ""
        self.components = []
        self.labels = []
        self.wires = []
        self.junctions = []
        self.no_connects = []
        self.power_symbols = []
        self.hierarchical_labels = []
        self.global_labels = []

        # Netlist information
        self.nets = defaultdict(list)  # Net name -> connected pins
        self.component_pins = {}  # (component_ref, pin_num) -> net_name

        # Component information
        self.component_info = {}  # component_ref -> component details

        # Library symbol pin definitions: lib_id -> [{number, x, y}]
        self.lib_symbol_pins: dict[str, list[dict]] = {}

        # Load the file
        self._load_schematic()

    def _load_schematic(self) -> None:
        """Load the schematic file content."""
        if not os.path.exists(self.schematic_path):
            logger.error("Schematic file not found: %s", self.schematic_path)
            raise FileNotFoundError(f"Schematic file not found: {self.schematic_path}")

        try:
            with open(self.schematic_path) as f:
                self.content = f.read()
                logger.debug("Successfully loaded schematic: %s", self.schematic_path)
        except Exception as e:
            logger.error("Error reading schematic file: %s", e)
            raise

    def parse(self) -> dict[str, Any]:
        """Parse the schematic to extract netlist information.

        Returns:
            Dictionary with parsed netlist information
        """
        logger.info("Starting schematic parsing")

        # Extract symbols (components)
        self._extract_components()

        # Extract lib_symbol pin definitions
        self._extract_lib_symbol_pins()

        # Extract wires
        self.wires = self._extract_wires(self.content)

        # Extract junctions
        self.junctions = self._extract_junctions(self.content)

        # Extract labels
        self.labels, self.global_labels, self.hierarchical_labels = self._extract_labels(
            self.content
        )

        # Extract power symbols
        self._extract_power_symbols()

        # Extract no-connects
        self._extract_no_connects()

        # Build netlist
        self._build_netlist()

        # Create result
        result = {
            "components": self.component_info,
            "nets": dict(self.nets),
            "labels": self.labels,
            "wires": self.wires,
            "junctions": self.junctions,
            "power_symbols": self.power_symbols,
            "component_count": len(self.component_info),
            "net_count": len(self.nets),
        }

        logger.info(
            "Schematic parsing complete: found %d components and %d nets",
            len(self.component_info),
            len(self.nets),
        )
        return result

    def _extract_s_expressions(self, pattern: str) -> list[str]:
        """Extract all matching S-expressions from the schematic content.

        Args:
            pattern: Regex pattern to match the start of S-expressions

        Returns:
            List of matching S-expressions
        """
        matches = []
        positions = []

        # Find all starting positions of matches
        for match in re.finditer(pattern, self.content):
            positions.append(match.start())

        # Extract full S-expressions for each match
        for pos in positions:
            # Start from the matching position
            current_pos = pos
            depth = 0
            s_exp = ""

            # Extract the full S-expression by tracking parentheses
            while current_pos < len(self.content):
                char = self.content[current_pos]
                s_exp += char

                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        # Found the end of the S-expression
                        break

                current_pos += 1

            matches.append(s_exp)

        return matches

    def _extract_components(self) -> None:
        """Extract component information from schematic."""
        logger.debug("Extracting components")

        # Extract all symbol expressions (components)
        symbols = self._extract_s_expressions(r"\(symbol\s+")

        for symbol in symbols:
            # Skip library symbols
            if not re.search(r'\(in_bom\s+"?yes"?\)', symbol):
                continue
            component = self._parse_component(symbol)
            if component:
                self.components.append(component)

                # Add to component info dictionary
                ref = component.get("reference", "Unknown")
                self.component_info[ref] = component

        logger.debug("Extracted %d components", len(self.components))

    def _parse_component(self, symbol_expr: str) -> dict[str, Any]:
        """Parse a component from a symbol S-expression.

        Args:
            symbol_expr: Symbol S-expression

        Returns:
            Component information dictionary
        """
        try:
            component = {}
            parsed_symbol = sexpdata.loads(symbol_expr)

            for item in parsed_symbol:
                if not isinstance(item, list) or not item:
                    continue

                key = str(item[0])
                if key == "lib_id":
                    component["lib_id"] = item[1]
                elif key == "at":
                    component["position"] = {
                        "x": item[1],
                        "y": item[2],
                        "angle": item[3] if len(item) > 3 else 0,
                    }
                elif key == "uuid":
                    component["uuid"] = item[1]
                elif key == "property":
                    prop_name = item[1]
                    prop_value = item[2]
                    if prop_name == "Reference":
                        component["reference"] = prop_value
                    elif prop_name == "Value":
                        component["value"] = prop_value
                    elif prop_name == "Footprint":
                        component["footprint"] = prop_value
                    else:
                        if "properties" not in component:
                            component["properties"] = {}
                        component["properties"][prop_name] = prop_value
                elif key == "pin":
                    if "pins" not in component:
                        component["pins"] = []
                    pin_num = item[1]
                    pin_uuid_item = item[2]
                    if isinstance(pin_uuid_item, list) and pin_uuid_item[0] == sexpdata.Symbol(
                        "uuid"
                    ):
                        component["pins"].append({"num": pin_num, "uuid": pin_uuid_item[1]})

            return component
        except Exception as e:
            logger.warning(
                "Failed to parse component expression: %s\nExpression:\n%s", e, symbol_expr
            )
            return {}

    def _extract_wires(self, content: str) -> list[dict[str, Any]]:
        """Extract all wire expressions from the schematic content."""
        wires = []
        # A more robust regex to capture wire data including nested structures
        wire_matches = re.finditer(r"\(\s*wire\s+((?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)", content)
        for match in wire_matches:
            wire_data = match.group(1)
            pts_match = re.search(r"\(pts\s+((?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)", wire_data)
            if pts_match:
                pts_str = pts_match.group(1)
                coords = re.findall(r"\(xy\s+([\d\.-]+)\s+([\d\.-]+)\)", pts_str)
                if len(coords) >= 2:
                    # Generate a UUID for the wire
                    wire_uuid = str(uuid.uuid4())

                    # Use start/end format for compatibility with tests
                    wires.append(
                        {
                            "uuid": wire_uuid,
                            "start": {"x": float(coords[0][0]), "y": float(coords[0][1])},
                            "end": {"x": float(coords[-1][0]), "y": float(coords[-1][1])},
                        }
                    )
        return wires

    def _extract_junctions(self, content: str) -> list[dict[str, Any]]:
        """Extract all junction expressions from the schematic content."""
        junctions = []
        junction_matches = re.finditer(
            r"\(\s*junction\s+\(at\s+([\d\.-]+)\s+([\d\.-]+)\s*\)(?:.|\n)*?\)", content
        )
        for match in junction_matches:
            junctions.append({"x": float(match.group(1)), "y": float(match.group(2))})
        return junctions

    def _extract_labels(
        self, content: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract all label expressions from the schematic content."""
        labels = []
        global_labels = []
        hierarchical_labels = []

        # Find label starts and extract full S-expressions by tracking paren depth
        for match in re.finditer(r"\(\s*(label|global_label|hierarchical_label)\s", content):
            label_type = match.group(1)
            pos = match.start()
            depth = 0
            end = pos
            while end < len(content):
                if content[end] == "(":
                    depth += 1
                elif content[end] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                end += 1
            label_data = content[pos : end + 1]

            # Extract text, which is the first quoted string
            text_match = re.search(r'"([^"]*)"', label_data)
            text = text_match.group(1) if text_match else ""

            # Extract position
            pos_match = re.search(r"\(at\s+([\d\.-]+)\s+([\d\.-]+)\s+([\d\.-]+)\)", label_data)
            if pos_match:
                label_pos = {
                    "x": float(pos_match.group(1)),
                    "y": float(pos_match.group(2)),
                    "angle": float(pos_match.group(3)),
                }
            else:
                label_pos = {"x": 0, "y": 0, "angle": 0}

            label_info = {"text": text, "position": label_pos}

            if label_type == "label":
                labels.append(label_info)
            elif label_type == "global_label":
                global_labels.append(label_info)
            elif label_type == "hierarchical_label":
                hierarchical_labels.append(label_info)

        return labels, global_labels, hierarchical_labels

    def _extract_power_symbols(self) -> None:
        """Extract power symbol information from schematic."""
        logger.debug("Extracting power symbols")

        # Extract all power symbol expressions
        power_symbols = self._extract_s_expressions(r'\(symbol\s+\(lib_id\s+"power:')

        for symbol in power_symbols:
            # Extract power symbol type and position
            type_match = re.search(r'\(lib_id\s+"power:([^"]+)"\)', symbol)
            pos_match = re.search(r"\(at\s+([\d\.-]+)\s+([\d\.-]+)(\s+[\d\.-]+)?\)", symbol)

            if type_match and pos_match:
                self.power_symbols.append(
                    {
                        "type": type_match.group(1),
                        "position": {
                            "x": float(pos_match.group(1)),
                            "y": float(pos_match.group(2)),
                            "angle": float(pos_match.group(3).strip() if pos_match.group(3) else 0),
                        },
                    }
                )

        logger.debug("Extracted %d power symbols", len(self.power_symbols))

    def _extract_no_connects(self) -> None:
        """Extract no-connect information from schematic."""
        logger.debug("Extracting no-connects")

        # Extract all no-connect expressions
        no_connects = self._extract_s_expressions(r"\(no_connect\s+")

        for no_connect in no_connects:
            # Extract the no-connect coordinates
            xy_match = re.search(r"\(no_connect\s+\(at\s+([\d\.-]+)\s+([\d\.-]+)\)", no_connect)
            if xy_match:
                self.no_connects.append(
                    {"x": float(xy_match.group(1)), "y": float(xy_match.group(2))}
                )

        logger.debug("Extracted %d no-connects", len(self.no_connects))

    def _extract_lib_symbol_pins(self) -> None:
        """Extract pin positions from the lib_symbols section of the schematic.

        Populates self.lib_symbol_pins: {lib_id: [{number, x, y}]}
        Pin positions are in the symbol's local coordinate system.
        """
        # Find the lib_symbols section
        lib_match = re.search(r"\(lib_symbols\s*\n", self.content)
        if not lib_match:
            logger.debug("No lib_symbols section found")
            return

        # Extract the full lib_symbols block
        start = lib_match.start()
        depth = 0
        pos = start
        while pos < len(self.content):
            if self.content[pos] == "(":
                depth += 1
            elif self.content[pos] == ")":
                depth -= 1
                if depth == 0:
                    break
            pos += 1
        lib_section = self.content[start : pos + 1]

        # Find each top-level symbol definition in lib_symbols
        # Pattern: (symbol "Library:Name" ...)
        symbol_pattern = re.compile(r'\(symbol\s+"([^"]+)"')
        for sym_match in symbol_pattern.finditer(lib_section):
            lib_id = sym_match.group(1)
            # Skip sub-symbol names like "R_0_1" or "R_1_1" — they don't have ":"
            if ":" not in lib_id:
                continue

            # Extract the full symbol block
            sym_start = sym_match.start()
            sym_depth = 0
            sym_pos = sym_start
            while sym_pos < len(lib_section):
                if lib_section[sym_pos] == "(":
                    sym_depth += 1
                elif lib_section[sym_pos] == ")":
                    sym_depth -= 1
                    if sym_depth == 0:
                        break
                sym_pos += 1
            sym_block = lib_section[sym_start : sym_pos + 1]

            # Find all pin definitions within this symbol (including sub-symbols)
            pins = []
            pin_pattern = re.compile(
                r"\(pin\s+\w+\s+\w+\s+"
                r"\(at\s+([\d\.-]+)\s+([\d\.-]+)\s+([\d\.-]+)\)"
                r"\s+\(length\s+([\d\.-]+)\)"
                r".*?"
                r'\(number\s+"([^"]+)"',
                re.DOTALL,
            )
            for pin_match in pin_pattern.finditer(sym_block):
                pins.append(
                    {
                        "number": pin_match.group(5),
                        "x": float(pin_match.group(1)),
                        "y": float(pin_match.group(2)),
                        "angle": float(pin_match.group(3)),
                        "length": float(pin_match.group(4)),
                    }
                )

            if pins:
                self.lib_symbol_pins[lib_id] = pins

        logger.debug("Extracted lib_symbol pins for %d symbols", len(self.lib_symbol_pins))

    def _resolve_pin_positions(self) -> list[dict[str, Any]]:
        """Compute absolute pin connection points for all components.

        Uses lib_symbol pin definitions and component position/rotation
        to calculate where each pin's wire connection point is in schematic
        coordinates.

        Returns:
            List of {component, pin, x, y} dicts
        """
        resolved = []

        for component in self.components:
            ref = component.get("reference", "Unknown")
            lib_id = component.get("lib_id", "")
            pos = component.get("position", {})
            cx = pos.get("x", 0)
            cy = pos.get("y", 0)
            angle = pos.get("angle", 0)

            # Get pin definitions from lib_symbols
            lib_pins = self.lib_symbol_pins.get(lib_id)
            if not lib_pins:
                logger.debug(
                    "No lib_symbol pins for %s (%s), skipping pin resolution",
                    ref,
                    lib_id,
                )
                continue

            theta = math.radians(angle)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            for pin_def in lib_pins:
                px = pin_def["x"]
                py = pin_def["y"]

                # Transform from symbol-local coords to schematic coords
                # lib_symbols use Y-up, schematics use Y-down
                abs_x = cx + px * cos_t + py * sin_t
                abs_y = cy - (-px * sin_t + py * cos_t)

                resolved.append(
                    {
                        "component": ref,
                        "pin": pin_def["number"],
                        "x": abs_x,
                        "y": abs_y,
                    }
                )

        return resolved

    def _build_netlist(self) -> None:
        """Build the netlist using wire connectivity tracing."""
        logger.debug("Building netlist from schematic data")

        engine = ConnectivityEngine()

        # Add wires
        engine.add_wires(self.wires)

        # Add junctions
        engine.add_junctions(self.junctions)

        # Add labels
        engine.add_labels(self.labels, label_type="local")
        engine.add_labels(self.global_labels, label_type="global")
        engine.add_labels(self.hierarchical_labels, label_type="hierarchical")

        # Resolve and add pin positions
        resolved_pins = self._resolve_pin_positions()
        for pin in resolved_pins:
            engine.add_pin(pin["component"], pin["pin"], pin["x"], pin["y"])

        # Add power symbol pins (connect at power symbol position)
        for power in self.power_symbols:
            engine.add_pin(
                power["type"],
                "1",
                power["position"]["x"],
                power["position"]["y"],
            )

        # Build nets
        self.nets = defaultdict(list, engine.build_nets())

        # Populate component_pins reverse lookup
        for net_name, pins in self.nets.items():
            for pin in pins:
                self.component_pins[(pin["component"], pin["pin"])] = net_name

        logger.debug("Netlist built: %d nets from wire connectivity tracing", len(self.nets))


def extract_netlist(schematic_path: str) -> dict[str, Any]:
    """Extract netlist information from a KiCad schematic file.

    Args:
        schematic_path: Path to the KiCad schematic file (.kicad_sch)

    Returns:
        Dictionary with netlist information
    """
    try:
        if not os.path.exists(schematic_path) or os.path.getsize(schematic_path) == 0:
            return {
                "error": "Schematic file not found or is empty",
                "components": {},
                "nets": {},
                "component_count": 0,
                "net_count": 0,
            }

        with open(schematic_path) as f:
            content = f.read().strip()

        if not content:
            return {
                "error": "Schematic file is empty",
                "components": {},
                "nets": {},
                "component_count": 0,
                "net_count": 0,
            }

        # Try parsing as JSON first
        try:
            import json

            json_data = json.loads(content)
            # Check for JSON schematic format indicators
            if (
                "components" in json_data
                or "symbol" in json_data
                or ("version" in json_data and not content.startswith("("))
            ):
                logger.debug("Detected JSON format schematic: %s", schematic_path)
                return parse_json_schematic(json_data)
        except json.JSONDecodeError:
            # If it's not JSON, it should be an S-expression
            if not content.startswith("(kicad_sch"):
                return {
                    "error": "Invalid schematic format. Not a valid JSON or S-expression file.",
                    "components": {},
                    "nets": {},
                    "component_count": 0,
                    "net_count": 0,
                }

        # Fall back to S-expression parser
        logger.info("Using S-expression parser for: %s", schematic_path)
        parser = SchematicParser(schematic_path)
        return parser.parse()
    except Exception as e:
        logger.error("Error extracting netlist: %s", e)
        return {"error": str(e), "components": {}, "nets": {}, "component_count": 0, "net_count": 0}


def parse_json_schematic(json_data: dict[str, Any]) -> dict[str, Any]:
    """Parse a JSON format KiCad schematic (created by kicad-mcp).

    Args:
        json_data: Dictionary containing the JSON schematic data

    Returns:
        Dictionary with netlist information
    """
    components = {}
    nets = defaultdict(list)

    # Extract components/symbols (support both 'components' and 'symbol' keys)
    if "components" not in json_data and "symbol" not in json_data:
        raise KeyError("Schematic JSON must contain 'components' or 'symbol' key")
    symbols = json_data.get("components", json_data.get("symbol", []))
    for symbol in symbols:
        lib_id = symbol.get("lib_id", "")
        uuid = symbol.get("uuid", "")
        # Handle position format (can be dict or list)
        pos_data = symbol.get("position", symbol.get("at", [0, 0, 0]))
        if isinstance(pos_data, dict):
            position = [pos_data.get("x", 0), pos_data.get("y", 0), pos_data.get("angle", 0)]
        else:
            position = pos_data

        # Extract properties (handle both old and new formats)
        properties = symbol.get("properties", {})
        reference = symbol.get("reference", "Unknown")
        value = symbol.get("value", "")

        # If using old format with "property" array
        for prop in symbol.get("property", []):
            prop_name = prop.get("name", "")
            prop_value = prop.get("value", "")

            if prop_name == "Reference":
                reference = prop_value
            elif prop_name == "Value":
                value = prop_value
            elif prop_name == "Footprint":
                properties["footprint"] = prop_value
            elif prop_name == "Datasheet":
                properties["datasheet"] = prop_value
            else:
                properties[prop_name] = prop_value

        # Create component entry
        component = {
            "lib_id": lib_id,
            "reference": reference,
            "value": value,
            "uuid": uuid,
            "position": {
                "x": position[0] if len(position) > 0 else 0,
                "y": position[1] if len(position) > 1 else 0,
                "angle": position[2] if len(position) > 2 else 0,
            },
            "properties": properties,
            "pins": [],  # JSON format doesn't include detailed pin info
        }

        # Handle duplicate references by using UUID as backup key
        component_key = reference
        if component_key in components:
            component_key = f"{reference}_{uuid[:8]}"

        components[component_key] = component

        # For power symbols, create a net
        if lib_id.startswith("power:"):
            power_type = lib_id.split(":", 1)[1]
            nets[power_type].append(
                {
                    "component": component_key,  # Use the actual component key
                    "pin": "1",  # Assume pin 1 for power symbols
                    "uuid": uuid,
                }
            )

    # Extract wires with start/end format
    raw_wires = json_data.get("wire", json_data.get("wires", []))
    parsed_wires = []
    for i, wire in enumerate(raw_wires):
        wire_uuid = wire.get("uuid", f"wire_{i}")
        # Support both {start, end} and {pts} formats
        if "start" in wire and "end" in wire:
            parsed_wires.append(
                {
                    "uuid": wire_uuid,
                    "start": wire["start"],
                    "end": wire["end"],
                }
            )
        else:
            pts = wire.get("pts", [])
            if len(pts) >= 2:
                parsed_wires.append(
                    {
                        "uuid": wire_uuid,
                        "start": {"x": pts[0][0], "y": pts[0][1]},
                        "end": {"x": pts[-1][0], "y": pts[-1][1]},
                    }
                )

    # Extract labels from JSON
    labels = [
        {
            "text": label.get("text", ""),
            "position": label.get("position", {"x": 0, "y": 0, "angle": 0}),
        }
        for label in json_data.get("labels", [])
    ]

    # Extract junctions from JSON
    junctions = [
        {
            "x": j.get("x", j.get("position", {}).get("x", 0)),
            "y": j.get("y", j.get("position", {}).get("y", 0)),
        }
        for j in json_data.get("junctions", [])
    ]

    # Extract explicit nets from JSON
    for net in json_data.get("nets", []):
        nets[net["name"]] = net["connections"]

    # If no explicit nets provided but wires exist, use ConnectivityEngine
    explicit_nets_with_connections = {k: v for k, v in nets.items() if v}
    if not explicit_nets_with_connections and parsed_wires:
        engine = ConnectivityEngine()
        engine.add_wires(parsed_wires)
        engine.add_junctions(junctions)
        engine.add_labels(labels, label_type="local")

        # Add component pins at their positions (simplified — center of component)
        for comp in components.values():
            pos = comp.get("position", {})
            engine.add_pin(comp["reference"], "1", pos.get("x", 0), pos.get("y", 0))

        # Add power symbol pins
        for comp in components.values():
            if comp["lib_id"].startswith("power:"):
                pos = comp["position"]
                power_type = comp["lib_id"].split(":", 1)[1]
                engine.add_pin(power_type, "1", pos["x"], pos["y"])

        nets = defaultdict(list, engine.build_nets())

    power_symbols = [
        {
            "type": (
                comp["lib_id"].split(":", 1)[1]
                if comp["lib_id"].startswith("power:")
                else comp["lib_id"]
            ),
            "position": comp["position"],
        }
        for comp in components.values()
        if comp["lib_id"].startswith("power:")
    ]

    result = {
        "components": components,
        "nets": dict(nets),
        "labels": labels,
        "wires": [
            {"uuid": w.get("uuid", ""), "start": w["start"], "end": w["end"]} for w in parsed_wires
        ],
        "junctions": junctions,
        "power_symbols": power_symbols,
        "component_count": len(components),
        "net_count": len(nets),
    }

    logger.debug(
        "JSON schematic parsing complete: found %d components and %d nets",
        len(components),
        len(nets),
    )
    return result


def analyze_netlist(netlist_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze netlist data to provide insights.

    Args:
        netlist_data: Dictionary with netlist information

    Returns:
        Dictionary with analysis results
    """
    results = {
        "component_count": netlist_data.get("component_count", 0),
        "net_count": netlist_data.get("net_count", 0),
        "component_types": {},
        "net_connectivity": {},
        "component_summary": {
            "total_components": netlist_data.get("component_count", 0),
            "total_nets": netlist_data.get("net_count", 0),
        },
        "power_nets": [],
    }

    # Analyze component types from lib_id
    component_types = defaultdict(int)
    for _ref, component in netlist_data.get("components", {}).items():
        lib_id = component.get("lib_id", "")
        if lib_id:
            component_types[lib_id] += 1

    results["component_types"] = dict(component_types)

    # Analyze net connectivity
    net_connectivity = {}
    for net_name, connections in netlist_data.get("nets", {}).items():
        net_connectivity[net_name] = connections

    results["net_connectivity"] = net_connectivity

    # Identify power nets
    for net_name in netlist_data.get("nets", {}):
        if any(
            net_name.startswith(prefix) for prefix in ["VCC", "VDD", "GND", "+5V", "+3V3", "+12V"]
        ):
            results["power_nets"].append(net_name)

    # Count pin connections
    total_pins = sum(len(pins) for pins in netlist_data.get("nets", {}).values())
    results["total_pin_connections"] = total_pins

    return results

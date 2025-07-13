"""
KiCad schematic netlist extraction utilities.
"""

from collections import defaultdict
import os
import re
from typing import Any


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

        # Load the file
        self._load_schematic()

    def _load_schematic(self) -> None:
        """Load the schematic file content."""
        if not os.path.exists(self.schematic_path):
            print(f"Schematic file not found: {self.schematic_path}")
            raise FileNotFoundError(f"Schematic file not found: {self.schematic_path}")

        try:
            with open(self.schematic_path) as f:
                self.content = f.read()
                print(f"Successfully loaded schematic: {self.schematic_path}")
        except Exception as e:
            print(f"Error reading schematic file: {str(e)}")
            raise

    def parse(self) -> dict[str, Any]:
        """Parse the schematic to extract netlist information.

        Returns:
            Dictionary with parsed netlist information
        """
        print("Starting schematic parsing")

        # Extract symbols (components)
        self._extract_components()

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

        print(
            f"Schematic parsing complete: found {len(self.component_info)} components and {len(self.nets)} nets"
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
        print("Extracting components")

        # Extract all symbol expressions (components)
        symbols = self._extract_s_expressions(r"\(symbol\s+")

        for symbol in symbols:
            # Skip library symbols
            if "(in_bom yes)" not in symbol:
                continue
            component = self._parse_component(symbol)
            if component:
                self.components.append(component)

                # Add to component info dictionary
                ref = component.get("reference", "Unknown")
                self.component_info[ref] = component

        print(f"Extracted {len(self.components)} components")

    def _parse_component(self, symbol_expr: str) -> dict[str, Any]:
        """Parse a component from a symbol S-expression.

        Args:
            symbol_expr: Symbol S-expression

        Returns:
            Component information dictionary
        """
        component = {}

        # Extract library component ID
        lib_id_match = re.search(r'\(lib_id\s+"([^"]+)"\)', symbol_expr)
        if lib_id_match:
            component["lib_id"] = lib_id_match.group(1)

        # Extract reference (e.g., R1, C2)
        property_matches = re.finditer(r'\(property\s+"([^"]+)"\s+"([^"]+)"', symbol_expr)
        for match in property_matches:
            prop_name = match.group(1)
            prop_value = match.group(2)

            if prop_name == "Reference":
                component["reference"] = prop_value
            elif prop_name == "Value":
                component["value"] = prop_value
            elif prop_name == "Footprint":
                component["footprint"] = prop_value
            else:
                # Store other properties
                if "properties" not in component:
                    component["properties"] = {}
                component["properties"][prop_name] = prop_value

        # Extract uuid
        uuid_match = re.search(r"\(uuid\s+([^\s\)]+)\)", symbol_expr)
        if uuid_match:
            component["uuid"] = uuid_match.group(1).strip('"')

        # Extract position
        pos_match = re.search(r"\(at\s+([\d\.-]+)\s+([\d\.-]+)(\s+[\d\.-]+)?\)", symbol_expr)
        if pos_match:
            component["position"] = {
                "x": float(pos_match.group(1)),
                "y": float(pos_match.group(2)),
                "angle": float(pos_match.group(3).strip() if pos_match.group(3) else 0),
            }

        # Extract pins
        pins = []
        pin_matches = re.finditer(r'\(pin\s+"([^"]+)"\s+\(uuid\s+([^\s\)]+)\)\)', symbol_expr)
        for match in pin_matches:
            pin_num = match.group(1)
            pin_uuid = match.group(2).strip('"')
            pins.append({"num": pin_num, "uuid": pin_uuid})

        if pins:
            component["pins"] = pins

        return component

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
                    import uuid

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

        # Regex to find all types of labels
        label_matches = re.finditer(
            r"\(\s*(label|global_label|hierarchical_label)\s+((?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)",
            content,
        )

        for match in label_matches:
            label_type = match.group(1)
            label_data = match.group(2)

            # Extract text, which is the first quoted string
            text_match = re.search(r'"([^"]*)"', label_data)
            text = text_match.group(1) if text_match else ""

            # Extract position
            pos_match = re.search(r"\(at\s+([\d\.-]+)\s+([\d\.-]+)\s+([\d\.-]+)\)", label_data)
            if pos_match:
                pos = {
                    "x": float(pos_match.group(1)),
                    "y": float(pos_match.group(2)),
                    "angle": float(pos_match.group(3)),
                }
            else:
                pos = {"x": 0, "y": 0, "angle": 0}

            label_info = {"text": text, "position": pos}

            if label_type == "label":
                labels.append(label_info)
            elif label_type == "global_label":
                global_labels.append(label_info)
            elif label_type == "hierarchical_label":
                hierarchical_labels.append(label_info)

        return labels, global_labels, hierarchical_labels

    def _extract_power_symbols(self) -> None:
        """Extract power symbol information from schematic."""
        print("Extracting power symbols")

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

        print(f"Extracted {len(self.power_symbols)} power symbols")

    def _extract_no_connects(self) -> None:
        """Extract no-connect information from schematic."""
        print("Extracting no-connects")

        # Extract all no-connect expressions
        no_connects = self._extract_s_expressions(r"\(no_connect\s+")

        for no_connect in no_connects:
            # Extract the no-connect coordinates
            xy_match = re.search(r"\(no_connect\s+\(at\s+([\d\.-]+)\s+([\d\.-]+)\)", no_connect)
            if xy_match:
                self.no_connects.append(
                    {"x": float(xy_match.group(1)), "y": float(xy_match.group(2))}
                )

        print(f"Extracted {len(self.no_connects)} no-connects")

    def _build_netlist(self) -> None:
        """Build the netlist from extracted components and connections."""
        print("Building netlist from schematic data")

        # TODO: Implement netlist building algorithm
        # This is a complex task that involves:
        # 1. Tracking connections between components via wires
        # 2. Handling labels (local, global, hierarchical)
        # 3. Processing power symbols
        # 4. Resolving junctions

        # For now, we'll implement a basic version that creates a list of nets
        # based on component references and pin numbers

        # Process global labels as nets
        for label in self.global_labels:
            net_name = label["text"]
            self.nets[net_name] = []  # Initialize empty list for this net

        # Process power symbols as nets
        for power in self.power_symbols:
            net_name = power["type"]
            if net_name not in self.nets:
                self.nets[net_name] = []

        # In a full implementation, we would now trace connections between
        # components, but that requires a more complex algorithm to follow wires
        # and detect connected pins

        # For demonstration, we'll add a placeholder note
        print("Note: Full netlist building requires complex connectivity tracing")
        print(f"Found {len(self.nets)} potential nets from labels and power symbols")


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
                print(f"Detected JSON format schematic: {schematic_path}")
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
        print(f"Using S-expression parser for: {schematic_path}")
        parser = SchematicParser(schematic_path)
        return parser.parse()
    except Exception as e:
        print(f"Error extracting netlist: {str(e)}")
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

    # Extract wires and create connections
    wires = json_data.get("wire", [])

    # Extract nets
    for net in json_data.get("nets", []):
        nets[net["name"]] = net["connections"]

    # Create a basic net for each wire (this is simplified)
    for i, wire in enumerate(wires):
        wire_uuid = wire.get("uuid", f"wire_{i}")
        pts = wire.get("pts", [])
        if len(pts) >= 2:
            # Create a net for this wire connection
            net_name = f"Net-{wire_uuid[:8]}"
            nets[net_name] = []

            # In a real implementation, we would trace which component pins
            # are connected by this wire, but that requires geometric analysis

    # Build result
    result = {
        "components": components,
        "nets": dict(nets),
        "labels": [],  # TODO: Extract from JSON
        "wires": [{"uuid": w.get("uuid", "")} for w in wires],
        "junctions": [],  # TODO: Extract from JSON
        "power_symbols": [
            {
                "type": comp["lib_id"].split(":", 1)[1]
                if comp["lib_id"].startswith("power:")
                else comp["lib_id"],
                "position": comp["position"],
            }
            for comp in components.values()
            if comp["lib_id"].startswith("power:")
        ],
        "component_count": len(components),
        "net_count": len(nets),
    }

    print(
        f"JSON schematic parsing complete: found {len(components)} components and {len(nets)} nets"
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

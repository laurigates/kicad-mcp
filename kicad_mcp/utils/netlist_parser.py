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
        self._extract_wires()

        # Extract junctions
        self._extract_junctions()

        # Extract labels
        self._extract_labels()

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
        pin_matches = re.finditer(
            r'\(pin\s+\(num\s+"([^"]+)"\)\s+\(name\s+"([^"]+)"\)', symbol_expr
        )
        for match in pin_matches:
            pin_num = match.group(1)
            pin_name = match.group(2)
            pins.append({"num": pin_num, "name": pin_name})

        if pins:
            component["pins"] = pins

        return component

    def _extract_wires(self) -> None:
        """Extract wire information from schematic."""
        print("Extracting wires")

        # Extract all wire expressions
        wires = self._extract_s_expressions(r"\(wire\s+")

        for wire in wires:
            # Extract the wire coordinates
            pts_match = re.search(
                r"\(pts\s+\(xy\s+([\d\.-]+)\s+([\d\.-]+)\)\s+\(xy\s+([\d\.-]+)\s+([\d\.-]+)\)\)",
                wire,
            )
            if pts_match:
                self.wires.append(
                    {
                        "start": {"x": float(pts_match.group(1)), "y": float(pts_match.group(2))},
                        "end": {"x": float(pts_match.group(3)), "y": float(pts_match.group(4))},
                    }
                )

        print(f"Extracted {len(self.wires)} wires")

    def _extract_junctions(self) -> None:
        """Extract junction information from schematic."""
        print("Extracting junctions")

        # Extract all junction expressions
        junctions = self._extract_s_expressions(r"\(junction\s+")

        for junction in junctions:
            # Extract the junction coordinates
            xy_match = re.search(r"\(junction\s+\(xy\s+([\d\.-]+)\s+([\d\.-]+)\)\)", junction)
            if xy_match:
                self.junctions.append(
                    {"x": float(xy_match.group(1)), "y": float(xy_match.group(2))}
                )

        print(f"Extracted {len(self.junctions)} junctions")

    def _extract_labels(self) -> None:
        """Extract label information from schematic."""
        print("Extracting labels")

        # Extract local labels
        local_labels = self._extract_s_expressions(r"\(label\s+")

        for label in local_labels:
            # Extract label text and position
            label_match = re.search(
                r'\(label\s+"([^"]+)"\s+\(at\s+([\d\.-]+)\s+([\d\.-]+)(\s+[\d\.-]+)?\)', label
            )
            if label_match:
                self.labels.append(
                    {
                        "type": "local",
                        "text": label_match.group(1),
                        "position": {
                            "x": float(label_match.group(2)),
                            "y": float(label_match.group(3)),
                            "angle": float(
                                label_match.group(4).strip() if label_match.group(4) else 0
                            ),
                        },
                    }
                )

        # Extract global labels
        global_labels = self._extract_s_expressions(r"\(global_label\s+")

        for label in global_labels:
            # Extract global label text and position
            label_match = re.search(
                r'\(global_label\s+"([^"]+)"\s+\(shape\s+([^\s\)]+)\)\s+\(at\s+([\d\.-]+)\s+([\d\.-]+)(\s+[\d\.-]+)?\)',
                label,
            )
            if label_match:
                self.global_labels.append(
                    {
                        "type": "global",
                        "text": label_match.group(1),
                        "shape": label_match.group(2),
                        "position": {
                            "x": float(label_match.group(3)),
                            "y": float(label_match.group(4)),
                            "angle": float(
                                label_match.group(5).strip() if label_match.group(5) else 0
                            ),
                        },
                    }
                )

        # Extract hierarchical labels
        hierarchical_labels = self._extract_s_expressions(r"\(hierarchical_label\s+")

        for label in hierarchical_labels:
            # Extract hierarchical label text and position
            label_match = re.search(
                r'\(hierarchical_label\s+"([^"]+)"\s+\(shape\s+([^\s\)]+)\)\s+\(at\s+([\d\.-]+)\s+([\d\.-]+)(\s+[\d\.-]+)?\)',
                label,
            )
            if label_match:
                self.hierarchical_labels.append(
                    {
                        "type": "hierarchical",
                        "text": label_match.group(1),
                        "shape": label_match.group(2),
                        "position": {
                            "x": float(label_match.group(3)),
                            "y": float(label_match.group(4)),
                            "angle": float(
                                label_match.group(5).strip() if label_match.group(5) else 0
                            ),
                        },
                    }
                )

        print(
            f"Extracted {len(self.labels)} local labels, {len(self.global_labels)} global labels, and {len(self.hierarchical_labels)} hierarchical labels"
        )

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
        # First, try to detect if this is a JSON format file (created by kicad-mcp)
        with open(schematic_path) as f:
            content = f.read()

        # Try parsing as JSON first
        try:
            import json

            json_data = json.loads(content)
            # Check for JSON schematic format indicators
            if (
                "components" in json_data
                or "symbol" in json_data
                or ("version" in json_data and not content.strip().startswith("("))
            ):
                print(f"Detected JSON format schematic: {schematic_path}")
                return parse_json_schematic(json_data)
        except json.JSONDecodeError:
            pass

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
    len(wires)

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

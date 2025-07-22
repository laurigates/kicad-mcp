"""
S-expression handler using sexpdata library for KiCad format compatibility.

This module provides a wrapper around the sexpdata library to handle
KiCad-specific S-expression parsing and generation with proper formatting.
"""

from typing import Any
import uuid

import sexpdata

from kicad_mcp.utils.component_layout import ComponentLayoutManager
from kicad_mcp.utils.pin_mapper import ComponentPinMapper


class SExpressionHandler:
    """
    KiCad S-expression handler using sexpdata library.

    Provides a high-level interface for parsing and generating KiCad S-expressions
    while maintaining compatibility with the existing sexpr_generator.py API.
    """

    def __init__(self):
        """Initialize the S-expression handler."""
        self.symbol_libraries = {}
        self.component_uuid_map = {}
        self.layout_manager = ComponentLayoutManager()
        self.pin_mapper = ComponentPinMapper()

    def parse_schematic(self, content: str) -> dict[str, Any]:
        """
        Parse a KiCad schematic S-expression into a structured dictionary.

        Args:
            content: S-expression content as string

        Returns:
            Dictionary representation of the schematic
        """
        try:
            parsed = sexpdata.loads(content)
            return self._sexpr_to_dict(parsed)
        except Exception as e:
            raise ValueError(f"Failed to parse S-expression: {e}") from e

    def generate_schematic(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
        pretty_print: bool = True,
    ) -> str:
        """
        Generate a KiCad schematic S-expression from structured data.

        Args:
            circuit_name: Name of the circuit
            components: List of component dictionaries
            power_symbols: List of power symbol dictionaries
            connections: List of connection dictionaries
            pretty_print: Whether to format output for readability

        Returns:
            S-expression formatted schematic as string
        """
        # Clear previous layout and pin mappings
        self.layout_manager.clear_layout()
        self.pin_mapper.clear_mappings()

        # Validate and fix component positions using layout manager
        validated_components = self._validate_component_positions(components)
        validated_power_symbols = self._validate_power_positions(power_symbols)

        # Add components to pin mapper for accurate pin tracking
        self._map_component_pins(validated_components, validated_power_symbols)

        # Build the schematic structure
        schematic_data = self._build_schematic_structure(
            circuit_name, validated_components, validated_power_symbols, connections
        )

        # Convert to S-expression format
        try:
            if pretty_print:
                return self._pretty_dumps(schematic_data)
            else:
                return sexpdata.dumps(schematic_data)
        except Exception as e:
            raise ValueError(f"Failed to generate S-expression: {e}") from e

    def _build_schematic_structure(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
    ) -> list[Any]:
        """Build the internal S-expression structure for a schematic."""
        # Main schematic UUID
        main_uuid = str(uuid.uuid4())

        # Start with basic schematic structure
        schematic = [
            sexpdata.Symbol("kicad_sch"),
            [sexpdata.Symbol("version"), 20240618],
            [sexpdata.Symbol("generator"), sexpdata.Symbol("kicad-mcp")],
            [sexpdata.Symbol("uuid"), main_uuid],
            [sexpdata.Symbol("paper"), "A4"],
            [
                sexpdata.Symbol("title_block"),
                [sexpdata.Symbol("title"), circuit_name],
                [sexpdata.Symbol("date"), ""],
                [sexpdata.Symbol("rev"), ""],
                [sexpdata.Symbol("company"), ""],
            ],
        ]

        # Add library symbols (always include, even if empty)
        lib_symbols = self._build_lib_symbols(components, power_symbols)
        if lib_symbols:
            schematic.append(lib_symbols)
        else:
            # Always include empty lib_symbols section to match generator
            schematic.append([sexpdata.Symbol("lib_symbols")])

        # Add component symbols
        for component in components:
            schematic.append(self._build_component_symbol(component))

        # Add power symbols
        for power_symbol in power_symbols:
            schematic.append(self._build_power_symbol(power_symbol))

        # Add connections
        for connection in connections:
            wire_data = self._build_wire(connection)
            if wire_data:
                schematic.append(wire_data)

        # Add sheet instances (required)
        schematic.append(
            [
                sexpdata.Symbol("sheet_instances"),
                [sexpdata.Symbol("path"), "/", [sexpdata.Symbol("page"), "1"]],
            ]
        )

        return schematic

    def _build_lib_symbols(
        self, components: list[dict[str, Any]], power_symbols: list[dict[str, Any]]
    ) -> list[Any] | None:
        """Build the lib_symbols section."""
        symbols_needed = set()

        # Collect unique symbol libraries
        for component in components:
            lib_id = (
                f"{component.get('symbol_library', 'Device')}:{component.get('symbol_name', 'R')}"
            )
            symbols_needed.add(lib_id)

        for power_symbol in power_symbols:
            power_type = power_symbol.get("power_type", "VCC")
            lib_id = f"power:{power_type}"
            symbols_needed.add(lib_id)

        if not symbols_needed:
            return None

        lib_symbols = [sexpdata.Symbol("lib_symbols")]

        # Generate symbol definitions
        for lib_id in sorted(symbols_needed):
            library, symbol = lib_id.split(":")
            symbol_def = self._build_symbol_definition(library, symbol)
            lib_symbols.append(symbol_def)

        return lib_symbols

    def _build_symbol_definition(self, library: str, symbol: str) -> list[Any]:
        """Build a symbol definition in S-expression format."""
        if library == "Device":
            return self._build_device_symbol(symbol)
        elif library == "power":
            return self._build_power_symbol_definition(symbol)
        else:
            # Default to resistor-like symbol
            return self._build_device_symbol("R")

    def _build_device_symbol(self, symbol: str) -> list[Any]:
        """Build a device symbol definition."""
        # Route to specific symbol builders for accurate KiCad compatibility
        if symbol == "R":
            return self._build_resistor_symbol()
        elif symbol == "C":
            return self._build_capacitor_symbol()
        elif symbol == "L":
            return self._build_inductor_symbol()
        elif symbol == "LED":
            return self._build_led_symbol()
        elif symbol == "D":
            return self._build_diode_symbol()
        else:
            # For unknown components, create a generic symbol with the original name
            return self._build_generic_symbol(symbol)

    def _build_resistor_symbol(self) -> list[Any]:
        """Build resistor symbol definition matching the generator."""
        return [
            sexpdata.Symbol("symbol"),
            "Device:R",
            [sexpdata.Symbol("pin_numbers"), sexpdata.Symbol("hide")],
            [sexpdata.Symbol("pin_names"), [sexpdata.Symbol("offset"), 0]],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("property"), "Reference", "R", [sexpdata.Symbol("at"), 2.032, 0, 90]],
            [sexpdata.Symbol("property"), "Value", "R", [sexpdata.Symbol("at"), 0, 0, 90]],
            [sexpdata.Symbol("property"), "Footprint", "", [sexpdata.Symbol("at"), -1.778, 0, 90]],
            [sexpdata.Symbol("property"), "Datasheet", "~", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                "R_0_1",
                [
                    sexpdata.Symbol("rectangle"),
                    [sexpdata.Symbol("start"), -1.016, -2.54],
                    [sexpdata.Symbol("end"), 1.016, 2.54],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                "R_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, 3.81, 270],
                    [sexpdata.Symbol("length"), 1.27],
                    [
                        sexpdata.Symbol("name"),
                        "~",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, -3.81, 90],
                    [sexpdata.Symbol("length"), 1.27],
                    [
                        sexpdata.Symbol("name"),
                        "~",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_capacitor_symbol(self) -> list[Any]:
        """Build capacitor symbol definition matching the generator."""
        return [
            sexpdata.Symbol("symbol"),
            "Device:C",
            [sexpdata.Symbol("pin_numbers"), sexpdata.Symbol("hide")],
            [sexpdata.Symbol("pin_names"), [sexpdata.Symbol("offset"), 0.254]],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [
                sexpdata.Symbol("property"),
                "Reference",
                "C",
                [sexpdata.Symbol("at"), 0.635, 2.54, 0],
            ],
            [sexpdata.Symbol("property"), "Value", "C", [sexpdata.Symbol("at"), 0.635, -2.54, 0]],
            [
                sexpdata.Symbol("property"),
                "Footprint",
                "",
                [sexpdata.Symbol("at"), 0.9652, -3.81, 0],
            ],
            [sexpdata.Symbol("property"), "Datasheet", "~", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                "C_0_1",
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -2.032, -0.762],
                        [sexpdata.Symbol("xy"), 2.032, -0.762],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -2.032, 0.762],
                        [sexpdata.Symbol("xy"), 2.032, 0.762],
                    ],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                "C_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, 3.81, 270],
                    [sexpdata.Symbol("length"), 2.794],
                    [
                        sexpdata.Symbol("name"),
                        "~",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, -3.81, 90],
                    [sexpdata.Symbol("length"), 2.794],
                    [
                        sexpdata.Symbol("name"),
                        "~",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_led_symbol(self) -> list[Any]:
        """Build LED symbol definition matching the generator."""
        return [
            sexpdata.Symbol("symbol"),
            "Device:LED",
            [sexpdata.Symbol("pin_numbers"), sexpdata.Symbol("hide")],
            [
                sexpdata.Symbol("pin_names"),
                [sexpdata.Symbol("offset"), 1.016],
                sexpdata.Symbol("hide"),
            ],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("property"), "Reference", "D", [sexpdata.Symbol("at"), 0, 2.54, 0]],
            [sexpdata.Symbol("property"), "Value", "LED", [sexpdata.Symbol("at"), 0, -2.54, 0]],
            [sexpdata.Symbol("property"), "Footprint", "", [sexpdata.Symbol("at"), 0, 0, 0]],
            [sexpdata.Symbol("property"), "Datasheet", "~", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                "LED_0_1",
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -1.27, -1.27],
                        [sexpdata.Symbol("xy"), -1.27, 1.27],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -1.27, 0],
                        [sexpdata.Symbol("xy"), 1.27, 0],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), 1.27, -1.27],
                        [sexpdata.Symbol("xy"), 1.27, 1.27],
                        [sexpdata.Symbol("xy"), -1.27, 0],
                        [sexpdata.Symbol("xy"), 1.27, -1.27],
                    ],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                "LED_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), -3.81, 0, 0],
                    [sexpdata.Symbol("length"), 2.54],
                    [
                        sexpdata.Symbol("name"),
                        "K",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 3.81, 0, 180],
                    [sexpdata.Symbol("length"), 2.54],
                    [
                        sexpdata.Symbol("name"),
                        "A",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_inductor_symbol(self) -> list[Any]:
        """Build inductor symbol definition matching the generator."""
        return [
            sexpdata.Symbol("symbol"),
            "Device:L",
            [sexpdata.Symbol("pin_numbers"), sexpdata.Symbol("hide")],
            [
                sexpdata.Symbol("pin_names"),
                [sexpdata.Symbol("offset"), 1.016],
                sexpdata.Symbol("hide"),
            ],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("property"), "Reference", "L", [sexpdata.Symbol("at"), -1.27, 0, 90]],
            [sexpdata.Symbol("property"), "Value", "L", [sexpdata.Symbol("at"), 1.905, 0, 90]],
            [sexpdata.Symbol("property"), "Footprint", "", [sexpdata.Symbol("at"), 0, 0, 0]],
            [sexpdata.Symbol("property"), "Datasheet", "~", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                "L_0_1",
                [
                    sexpdata.Symbol("arc"),
                    [sexpdata.Symbol("start"), 0, -2.54],
                    [sexpdata.Symbol("mid"), 0.6323, -1.905],
                    [sexpdata.Symbol("end"), 0, -1.27],
                ],
                [
                    sexpdata.Symbol("arc"),
                    [sexpdata.Symbol("start"), 0, -1.27],
                    [sexpdata.Symbol("mid"), 0.6323, -0.635],
                    [sexpdata.Symbol("end"), 0, 0],
                ],
                [
                    sexpdata.Symbol("arc"),
                    [sexpdata.Symbol("start"), 0, 0],
                    [sexpdata.Symbol("mid"), 0.6323, 0.635],
                    [sexpdata.Symbol("end"), 0, 1.27],
                ],
                [
                    sexpdata.Symbol("arc"),
                    [sexpdata.Symbol("start"), 0, 1.27],
                    [sexpdata.Symbol("mid"), 0.6323, 1.905],
                    [sexpdata.Symbol("end"), 0, 2.54],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                "L_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, 3.81, 270],
                    [sexpdata.Symbol("length"), 1.27],
                    [
                        sexpdata.Symbol("name"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, -3.81, 90],
                    [sexpdata.Symbol("length"), 1.27],
                    [
                        sexpdata.Symbol("name"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_diode_symbol(self) -> list[Any]:
        """Build diode symbol definition matching the generator."""
        return [
            sexpdata.Symbol("symbol"),
            "Device:D",
            [sexpdata.Symbol("pin_numbers"), sexpdata.Symbol("hide")],
            [
                sexpdata.Symbol("pin_names"),
                [sexpdata.Symbol("offset"), 1.016],
                sexpdata.Symbol("hide"),
            ],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("property"), "Reference", "D", [sexpdata.Symbol("at"), 0, 2.54, 0]],
            [sexpdata.Symbol("property"), "Value", "D", [sexpdata.Symbol("at"), 0, -2.54, 0]],
            [sexpdata.Symbol("property"), "Footprint", "", [sexpdata.Symbol("at"), 0, 0, 0]],
            [sexpdata.Symbol("property"), "Datasheet", "~", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                "D_0_1",
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -1.27, -1.27],
                        [sexpdata.Symbol("xy"), -1.27, 1.27],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -1.27, 0],
                        [sexpdata.Symbol("xy"), 1.27, 0],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), 1.27, -1.27],
                        [sexpdata.Symbol("xy"), 1.27, 1.27],
                        [sexpdata.Symbol("xy"), -1.27, 0],
                        [sexpdata.Symbol("xy"), 1.27, -1.27],
                    ],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                "D_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), -3.81, 0, 0],
                    [sexpdata.Symbol("length"), 2.54],
                    [
                        sexpdata.Symbol("name"),
                        "K",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 3.81, 0, 180],
                    [sexpdata.Symbol("length"), 2.54],
                    [
                        sexpdata.Symbol("name"),
                        "A",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_generic_symbol(self, symbol: str) -> list[Any]:
        """Build a generic symbol definition for unknown component types."""
        return [
            sexpdata.Symbol("symbol"),
            f"Device:{symbol}",
            [sexpdata.Symbol("pin_numbers"), sexpdata.Symbol("hide")],
            [sexpdata.Symbol("pin_names"), [sexpdata.Symbol("offset"), 0]],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("property"), "Reference", "U", [sexpdata.Symbol("at"), 2.032, 0, 90]],
            [sexpdata.Symbol("property"), "Value", symbol, [sexpdata.Symbol("at"), 0, 0, 90]],
            [sexpdata.Symbol("property"), "Footprint", "", [sexpdata.Symbol("at"), -1.778, 0, 90]],
            [sexpdata.Symbol("property"), "Datasheet", "~", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                f"{symbol}_0_1",
                [
                    sexpdata.Symbol("rectangle"),
                    [sexpdata.Symbol("start"), -2.54, -2.54],
                    [sexpdata.Symbol("end"), 2.54, 2.54],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                f"{symbol}_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, 3.81, 270],
                    [sexpdata.Symbol("length"), 1.27],
                    [
                        sexpdata.Symbol("name"),
                        "~",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("passive"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, -3.81, 90],
                    [sexpdata.Symbol("length"), 1.27],
                    [
                        sexpdata.Symbol("name"),
                        "~",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "2",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_power_symbol_definition(self, power_type: str) -> list[Any]:
        """Build a power symbol definition."""
        symbol_name = f"power:{power_type}"

        return [
            sexpdata.Symbol("symbol"),
            symbol_name,
            [sexpdata.Symbol("power")],
            [sexpdata.Symbol("pin_names"), [sexpdata.Symbol("offset"), 0], sexpdata.Symbol("hide")],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [
                sexpdata.Symbol("property"),
                "Reference",
                "#PWR",
                [sexpdata.Symbol("at"), 0, -3.81, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Value",
                power_type,
                [sexpdata.Symbol("at"), 0, 3.556, 0],
            ],
            [sexpdata.Symbol("property"), "Footprint", "", [sexpdata.Symbol("at"), 0, 0, 0]],
            [sexpdata.Symbol("property"), "Datasheet", "", [sexpdata.Symbol("at"), 0, 0, 0]],
            [
                sexpdata.Symbol("symbol"),
                f"{power_type}_0_1",
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), -0.762, 1.27],
                        [sexpdata.Symbol("xy"), 0, 2.54],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), 0, 0],
                        [sexpdata.Symbol("xy"), 0, 2.54],
                    ],
                ],
                [
                    sexpdata.Symbol("polyline"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), 0, 2.54],
                        [sexpdata.Symbol("xy"), 0.762, 1.27],
                    ],
                ],
            ],
            [
                sexpdata.Symbol("symbol"),
                f"{power_type}_1_1",
                [
                    sexpdata.Symbol("pin"),
                    sexpdata.Symbol("power_in"),
                    sexpdata.Symbol("line"),
                    [sexpdata.Symbol("at"), 0, 0, 90],
                    [sexpdata.Symbol("length"), 0],
                    sexpdata.Symbol("hide"),
                    [
                        sexpdata.Symbol("name"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                    [
                        sexpdata.Symbol("number"),
                        "1",
                        [
                            sexpdata.Symbol("effects"),
                            [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]],
                        ],
                    ],
                ],
            ],
        ]

    def _build_component_symbol(self, component: dict[str, Any]) -> list[Any]:
        """Build a component symbol instance."""
        comp_uuid = str(uuid.uuid4())
        self.component_uuid_map[component["reference"]] = comp_uuid

        # Convert position from mm to KiCad internal units (0.1mm)
        position = component.get("position", (100, 100))
        x_pos = position[0] * 10
        y_pos = position[1] * 10

        lib_id = f"{component.get('symbol_library', 'Device')}:{component.get('symbol_name', 'R')}"
        # Register component with pin mapper
        # Register component with pin mapper using proper component type
        component_type = self._get_component_type(component)
        self.pin_mapper.add_component(
            component_ref=component["reference"], component_type=component_type, position=position
        )
        return [
            sexpdata.Symbol("symbol"),
            [sexpdata.Symbol("lib_id"), lib_id],
            [sexpdata.Symbol("at"), x_pos, y_pos, 0],
            [sexpdata.Symbol("unit"), 1],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("dnp"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("uuid"), comp_uuid],
            [
                sexpdata.Symbol("property"),
                "Reference",
                component["reference"],
                [sexpdata.Symbol("at"), x_pos + 25.4, y_pos - 12.7, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Value",
                component["value"],
                [sexpdata.Symbol("at"), x_pos + 25.4, y_pos + 12.7, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Footprint",
                "",
                [sexpdata.Symbol("at"), x_pos, y_pos, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Datasheet",
                "~",
                [sexpdata.Symbol("at"), x_pos, y_pos, 0],
            ],
            [sexpdata.Symbol("pin"), "1", [sexpdata.Symbol("uuid"), str(uuid.uuid4())]],
            [sexpdata.Symbol("pin"), "2", [sexpdata.Symbol("uuid"), str(uuid.uuid4())]],
        ]

    def _build_power_symbol(self, power_symbol: dict[str, Any]) -> list[Any]:
        """Build a power symbol instance."""
        power_uuid = str(uuid.uuid4())
        ref = power_symbol.get("reference", f"#PWR0{len(self.component_uuid_map) + 1:03d}")
        self.component_uuid_map[ref] = power_uuid

        # Convert position from mm to KiCad internal units
        position = power_symbol.get("position", (100, 100))
        x_pos = position[0] * 10
        y_pos = position[1] * 10

        power_type = power_symbol["power_type"]
        lib_id = f"power:{power_type}"
        return [
            sexpdata.Symbol("symbol"),
            [sexpdata.Symbol("lib_id"), lib_id],
            [sexpdata.Symbol("at"), x_pos, y_pos, 0],
            [sexpdata.Symbol("unit"), 1],
            [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("dnp"), sexpdata.Symbol("no")],
            [sexpdata.Symbol("uuid"), power_uuid],
            [
                sexpdata.Symbol("property"),
                "Reference",
                ref,
                [sexpdata.Symbol("at"), x_pos, y_pos - 25.4, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Value",
                power_type,
                [sexpdata.Symbol("at"), x_pos, y_pos + 35.56, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Footprint",
                "",
                [sexpdata.Symbol("at"), x_pos, y_pos, 0],
            ],
            [
                sexpdata.Symbol("property"),
                "Datasheet",
                "",
                [sexpdata.Symbol("at"), x_pos, y_pos, 0],
            ],
            [sexpdata.Symbol("pin"), "1", [sexpdata.Symbol("uuid"), str(uuid.uuid4())]],
        ]

    def _build_wire(self, connection: dict[str, Any]) -> list[Any] | None:
        """Build a wire connection."""
        wire_uuid = str(uuid.uuid4())

        # Handle coordinate-based connections
        if "start_x" in connection and "start_y" in connection:
            start_x = connection.get("start_x", 100) * 10
            start_y = connection.get("start_y", 100) * 10
            end_x = connection.get("end_x", 200) * 10
            end_y = connection.get("end_y", 100) * 10

            return [
                sexpdata.Symbol("wire"),
                [
                    sexpdata.Symbol("pts"),
                    [sexpdata.Symbol("xy"), start_x, start_y],
                    [sexpdata.Symbol("xy"), end_x, end_y],
                ],
                [
                    sexpdata.Symbol("stroke"),
                    [sexpdata.Symbol("width"), 0],
                    [sexpdata.Symbol("type"), sexpdata.Symbol("default")],
                ],
                [sexpdata.Symbol("uuid"), wire_uuid],
            ]

        # Handle pin-level connections
        if all(
            key in connection
            for key in ["start_component", "start_pin", "end_component", "end_pin"]
        ):
            # Get pin positions from pin mapper
            start_pos = self.pin_mapper.get_pin_connection_point(
                connection["start_component"], connection["start_pin"]
            )
            end_pos = self.pin_mapper.get_pin_connection_point(
                connection["end_component"], connection["end_pin"]
            )

            if start_pos and end_pos:
                # Track the connection in the pin mapper
                self.pin_mapper.add_connection(
                    connection["start_component"],
                    connection["start_pin"],
                    connection["end_component"],
                    connection["end_pin"],
                )

                return [
                    sexpdata.Symbol("wire"),
                    [
                        sexpdata.Symbol("pts"),
                        [sexpdata.Symbol("xy"), start_pos[0] * 10, start_pos[1] * 10],
                        [sexpdata.Symbol("xy"), end_pos[0] * 10, end_pos[1] * 10],
                    ],
                    [
                        sexpdata.Symbol("stroke"),
                        [sexpdata.Symbol("width"), 0],
                        [sexpdata.Symbol("type"), sexpdata.Symbol("default")],
                    ],
                    [sexpdata.Symbol("uuid"), wire_uuid],
                ]

        return None

    def generate_advanced_wire_routing(self, net_connections: list[dict]) -> list[str]:
        """Generate advanced wire routing for multi-pin nets."""
        wire_lines = []

        for net in net_connections:
            pins = net.get("pins", [])

            if len(pins) < 2:
                continue

            # Parse component.pin format
            parsed_pins = []
            for pin in pins:
                if "." in pin:
                    component, pin_num = pin.split(".", 1)
                    pos = self.pin_mapper.get_pin_connection_point(component, pin_num)
                    if pos:
                        parsed_pins.append((component, pin_num, pos))

            if len(parsed_pins) < 2:
                continue

            # Generate simple point-to-point connections for now
            # Connect each pin to the first pin (star topology)
            if len(parsed_pins) >= 2:
                hub_component, hub_pin, hub_pos = parsed_pins[0]

                for i in range(1, len(parsed_pins)):
                    component, pin_num, pos = parsed_pins[i]
                    # Track connections
                    self.pin_mapper.add_connection(hub_component, hub_pin, component, pin_num)

                    # Create wire route
                    route = [hub_pos, pos]
                    start_pos, end_pos = route
                    wire_uuid = str(uuid.uuid4())
                    wire_data = [
                        sexpdata.Symbol("wire"),
                        [
                            sexpdata.Symbol("pts"),
                            [sexpdata.Symbol("xy"), start_pos[0] * 10, start_pos[1] * 10],
                            [sexpdata.Symbol("xy"), end_pos[0] * 10, end_pos[1] * 10],
                        ],
                        [
                            sexpdata.Symbol("stroke"),
                            [sexpdata.Symbol("width"), 0],
                            [sexpdata.Symbol("type"), sexpdata.Symbol("default")],
                        ],
                        [sexpdata.Symbol("uuid"), wire_uuid],
                    ]
                    wire_lines.append(self._pretty_dumps(wire_data))

        return wire_lines

    def _pretty_dumps(self, data: Any, indent: int = 0) -> str:
        """
        Pretty-print S-expression data with proper indentation.

        Args:
            data: S-expression data structure
            indent: Current indentation level

        Returns:
            Formatted S-expression string
        """
        if isinstance(data, list):
            if not data:
                return "()"

            # Check if this is a simple list (no nested structures)
            if all(not isinstance(item, list) for item in data):
                return f"({' '.join(self._format_atom(item) for item in data)})"

            # Multi-line format for complex structures
            lines = ["("]
            for i, item in enumerate(data):
                if i == 0:
                    # First item (usually the symbol) on the same line
                    lines[0] += self._format_atom(item)
                else:
                    # Subsequent items on new lines with proper indentation
                    item_str = self._pretty_dumps(item, indent + 2)
                    lines.append("  " * (indent + 1) + item_str)
            lines.append("  " * indent + ")")
            return "\n".join(lines)
        else:
            return self._format_atom(data)

    def _format_atom(self, atom: Any) -> str:
        """Format a single atom (symbol, string, number) for output."""
        if isinstance(atom, sexpdata.Symbol):
            return str(atom)
        elif isinstance(atom, str):
            # Quote strings that contain spaces or special characters
            if " " in atom or '"' in atom or atom == "":
                return f'"{atom}"'
            return atom
        else:
            return str(atom)

    def _sexpr_to_dict(self, sexpr: Any) -> dict[str, Any]:
        """Convert S-expression to dictionary representation."""
        if isinstance(sexpr, list) and len(sexpr) > 0:
            key = str(sexpr[0])
            if key == "kicad_sch":
                return self._parse_schematic_dict(sexpr[1:])
            else:
                return {key: [self._sexpr_to_dict(item) for item in sexpr[1:]]}
        else:
            return str(sexpr) if sexpr is not None else ""

    def _parse_schematic_dict(self, items: list[Any]) -> dict[str, Any]:
        """Parse schematic items into a structured dictionary."""
        result = {}
        for item in items:
            if isinstance(item, list) and len(item) > 0:
                key = str(item[0])
                if key in result:
                    # Handle multiple items with same key (e.g., multiple symbols)
                    if not isinstance(result[key], list):
                        result[key] = [result[key]]
                    result[key].append(self._sexpr_to_dict(item))
                else:
                    result[key] = self._sexpr_to_dict(item)
        return result

    def _validate_component_positions(
        self, components: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate and fix component positions using the layout manager."""
        validated_components = []

        for component in components:
            # Get component type for sizing
            component_type = self._get_component_type(component)

            # Check if position is provided
            if "position" in component and component["position"]:
                position = component["position"]
                if isinstance(position, dict):
                    x, y = position["x"], position["y"]
                else:
                    x, y = position
                # Validate position is within bounds
                if self.layout_manager.validate_position(x, y, component_type):
                    # Position is valid, place component at exact location
                    final_x, final_y = self.layout_manager.place_component(
                        component["reference"], component_type, x, y
                    )
                else:
                    # Position is invalid, find a valid one
                    final_x, final_y = self.layout_manager.place_component(
                        component["reference"], component_type
                    )
            else:
                # No position provided, auto-place
                final_x, final_y = self.layout_manager.place_component(
                    component["reference"], component_type
                )

            # Update component with validated position
            validated_component = component.copy()
            validated_component["position"] = (final_x, final_y)
            validated_components.append(validated_component)

        return validated_components

    def _validate_power_positions(
        self, power_symbols: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate and fix power symbol positions using the layout manager."""
        validated_power_symbols = []

        for power_symbol in power_symbols:
            # Power symbols use 'power' component type
            component_type = "power"

            # Check if position is provided
            if "position" in power_symbol and power_symbol["position"]:
                position = power_symbol["position"]
                if isinstance(position, dict):
                    x, y = position["x"], position["y"]
                else:
                    x, y = position
                # Validate position is within bounds
                if self.layout_manager.validate_position(x, y, component_type):
                    # Position is valid, place power symbol at exact location
                    final_x, final_y = self.layout_manager.place_component(
                        power_symbol["reference"], component_type, x, y
                    )
                else:
                    # Position is invalid, find a valid one
                    final_x, final_y = self.layout_manager.place_component(
                        power_symbol["reference"], component_type
                    )
            else:
                # No position provided, auto-place
                final_x, final_y = self.layout_manager.place_component(
                    power_symbol["reference"], component_type
                )

            # Update power symbol with validated position
            validated_power_symbol = power_symbol.copy()
            validated_power_symbol["position"] = (final_x, final_y)
            validated_power_symbols.append(validated_power_symbol)

        return validated_power_symbols

    def _get_component_type(self, component: dict[str, Any]) -> str:
        """Determine component type from component dictionary."""
        # Check if component_type is explicitly provided
        if "component_type" in component:
            return component["component_type"]

        # Infer from symbol information
        symbol_name = component.get("symbol_name", "").lower()
        symbol_library = component.get("symbol_library", "").lower()

        # Map symbol names to component types
        if symbol_name in ["r", "resistor"]:
            return "resistor"
        elif symbol_name in ["c", "capacitor"]:
            return "capacitor"
        elif symbol_name in ["l", "inductor"]:
            return "inductor"
        elif symbol_name in ["led"]:
            return "led"
        elif symbol_name in ["d", "diode"]:
            return "diode"
        elif "transistor" in symbol_name:
            return "transistor"
        elif symbol_library == "switch":
            return "switch"
        elif symbol_library == "connector":
            return "connector"
        elif "ic" in symbol_name or "mcu" in symbol_name or "atmega" in symbol_name:
            return "ic"
        else:
            return "default"

    def _map_component_pins(
        self, components: list[dict[str, Any]], power_symbols: list[dict[str, Any]]
    ):
        """Map all components and power symbols to the pin mapper."""
        # Map regular components
        for component in components:
            component_type = self._get_component_type(component)
            self.pin_mapper.add_component(
                component_ref=component["reference"],
                component_type=component_type,
                position=component["position"],
                angle=0.0,  # Default angle, could be extended later
            )

        # Map power symbols
        for power_symbol in power_symbols:
            self.pin_mapper.add_component(
                component_ref=power_symbol["reference"],
                component_type="power",
                position=power_symbol["position"],
                angle=0.0,
            )

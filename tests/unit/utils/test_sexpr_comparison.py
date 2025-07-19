"""
Byte-for-byte comparison tests between SExpressionGenerator and SExpressionHandler.

These tests ensure the new sexpdata-based implementation produces identical output
to the existing string-concatenation implementation for full compatibility.
"""

import pytest
import sexpdata

from kicad_mcp.utils.sexpr_generator import SExpressionGenerator
from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class TestSExpressionComparison:
    """Compare outputs between SExpressionGenerator and SExpressionHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SExpressionGenerator()
        self.handler = SExpressionHandler()

        # Sample test data
        self.sample_component = {
            "reference": "R1",
            "value": "10k",
            "symbol_library": "Device",
            "symbol_name": "R",
            "position": (63.5, 87.63),
        }

        self.sample_power_symbol = {
            "reference": "#PWR001",
            "power_type": "VCC",
            "position": (63.5, 80.0),
        }

        self.sample_connection = {"start_x": 63.5, "start_y": 91.44, "end_x": 63.5, "end_y": 96.52}

    def test_empty_schematic_comparison(self):
        """Test that both implementations generate identical empty schematics."""
        circuit_name = "Empty Circuit"
        components = []
        power_symbols = []
        connections = []

        # Generate with existing implementation
        generator_output = self.generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        # Generate with new implementation (non-pretty to match old format)
        handler_output = self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print=False
        )

        # Parse both outputs to compare structure (UUIDs will be different)
        generator_parsed = sexpdata.loads(generator_output)
        handler_parsed = sexpdata.loads(handler_output)

        # Compare structure ignoring UUIDs
        self._compare_structures_ignore_uuids(generator_parsed, handler_parsed)

    def test_single_component_comparison(self):
        """Test single component schematic generation comparison."""
        circuit_name = "Single Component Test"
        components = [self.sample_component]
        power_symbols = []
        connections = []

        # Generate with both implementations
        generator_output = self.generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        handler_output = self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print=False
        )

        # Parse and compare structures
        generator_parsed = sexpdata.loads(generator_output)
        handler_parsed = sexpdata.loads(handler_output)

        self._compare_structures_ignore_uuids(generator_parsed, handler_parsed)

        # Verify component data is present
        self._verify_component_present(generator_parsed, "R1", "10k", "Device:R")
        self._verify_component_present(handler_parsed, "R1", "10k", "Device:R")

    def test_power_symbol_comparison(self):
        """Test power symbol generation comparison."""
        circuit_name = "Power Symbol Test"
        components = []
        power_symbols = [self.sample_power_symbol]
        connections = []

        # Generate with both implementations
        generator_output = self.generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        handler_output = self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print=False
        )

        # Parse and compare structures
        generator_parsed = sexpdata.loads(generator_output)
        handler_parsed = sexpdata.loads(handler_output)

        self._compare_structures_ignore_uuids(generator_parsed, handler_parsed)

        # Verify power symbol data is present
        self._verify_power_symbol_present(generator_parsed, "#PWR001", "VCC")
        self._verify_power_symbol_present(handler_parsed, "#PWR001", "VCC")

    def test_wire_connection_comparison(self):
        """Test wire connection generation comparison."""
        circuit_name = "Wire Connection Test"
        components = []
        power_symbols = []
        connections = [self.sample_connection]

        # Generate with both implementations
        generator_output = self.generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        handler_output = self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print=False
        )

        # Parse and compare structures
        generator_parsed = sexpdata.loads(generator_output)
        handler_parsed = sexpdata.loads(handler_output)

        self._compare_structures_ignore_uuids(generator_parsed, handler_parsed)

        # Verify wire is present
        self._verify_wire_present(generator_parsed)
        self._verify_wire_present(handler_parsed)

    def test_complex_schematic_comparison(self):
        """Test complex schematic with multiple components, power symbols, and connections."""
        circuit_name = "Complex Circuit Test"

        components = [
            {
                "reference": "R1",
                "value": "10k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (50.0, 50.0),
            },
            {
                "reference": "C1",
                "value": "100nF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (70.0, 50.0),
            },
            {
                "reference": "LED1",
                "value": "Red",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (90.0, 50.0),
            },
        ]

        power_symbols = [
            {"reference": "#PWR001", "power_type": "VCC", "position": (50.0, 30.0)},
            {"reference": "#PWR002", "power_type": "GND", "position": (90.0, 70.0)},
        ]

        connections = [
            {"start_x": 50.0, "start_y": 45.0, "end_x": 70.0, "end_y": 45.0},
            {"start_x": 70.0, "start_y": 55.0, "end_x": 90.0, "end_y": 55.0},
        ]

        # Generate with both implementations
        generator_output = self.generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        handler_output = self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print=False
        )

        # Parse and compare structures
        generator_parsed = sexpdata.loads(generator_output)
        handler_parsed = sexpdata.loads(handler_output)

        self._compare_structures_ignore_uuids(generator_parsed, handler_parsed)

        # Verify all components are present
        for component in components:
            lib_id = f"{component['symbol_library']}:{component['symbol_name']}"
            self._verify_component_present(
                generator_parsed, component["reference"], component["value"], lib_id
            )
            self._verify_component_present(
                handler_parsed, component["reference"], component["value"], lib_id
            )

        # Verify all power symbols are present
        for power_symbol in power_symbols:
            self._verify_power_symbol_present(
                generator_parsed, power_symbol["reference"], power_symbol["power_type"]
            )
            self._verify_power_symbol_present(
                handler_parsed, power_symbol["reference"], power_symbol["power_type"]
            )

    def test_symbol_library_generation_comparison(self):
        """Test that symbol library definitions are consistent."""
        circuit_name = "Symbol Library Test"

        # Test different component types
        components = [
            {
                "reference": "R1",
                "value": "1k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (10, 10),
            },
            {
                "reference": "C1",
                "value": "10uF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (20, 10),
            },
            {
                "reference": "L1",
                "value": "1mH",
                "symbol_library": "Device",
                "symbol_name": "L",
                "position": (30, 10),
            },
            {
                "reference": "D1",
                "value": "LED",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (40, 10),
            },
            {
                "reference": "D2",
                "value": "1N4148",
                "symbol_library": "Device",
                "symbol_name": "D",
                "position": (50, 10),
            },
        ]

        power_symbols = [
            {"reference": "#PWR001", "power_type": "VCC", "position": (10, 20)},
            {"reference": "#PWR002", "power_type": "GND", "position": (20, 20)},
        ]

        # Generate with both implementations
        generator_output = self.generator.generate_schematic(
            circuit_name, components, power_symbols, []
        )

        handler_output = self.handler.generate_schematic(
            circuit_name, components, power_symbols, [], pretty_print=False
        )

        # Parse and compare lib_symbols sections
        generator_parsed = sexpdata.loads(generator_output)
        handler_parsed = sexpdata.loads(handler_output)

        generator_lib_symbols = self._extract_lib_symbols(generator_parsed)
        handler_lib_symbols = self._extract_lib_symbols(handler_parsed)

        # Verify same number of symbol definitions
        assert len(generator_lib_symbols) == len(handler_lib_symbols), (
            f"Different number of lib symbols: {len(generator_lib_symbols)} vs {len(handler_lib_symbols)}"
        )

        # Verify symbol names match
        generator_symbol_names = {str(sym[1]) for sym in generator_lib_symbols if len(sym) > 1}
        handler_symbol_names = {str(sym[1]) for sym in handler_lib_symbols if len(sym) > 1}

        assert generator_symbol_names == handler_symbol_names, (
            f"Symbol names don't match: {generator_symbol_names} vs {handler_symbol_names}"
        )

    def test_position_conversion_consistency(self):
        """Test that position conversion from mm to KiCad units is consistent."""
        circuit_name = "Position Test"

        # Test various positions
        test_positions = [
            (0.0, 0.0),
            (10.0, 20.0),
            (63.5, 87.63),
            (100.0, 150.0),
            (25.4, 12.7),  # Exact inch conversions
        ]

        for i, position in enumerate(test_positions):
            component = {
                "reference": f"R{i + 1}",
                "value": "1k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": position,
            }

            # Generate with both implementations
            generator_output = self.generator.generate_schematic(circuit_name, [component], [], [])

            handler_output = self.handler.generate_schematic(
                circuit_name, [component], [], [], pretty_print=False
            )

            # Extract positions from both outputs
            generator_pos = self._extract_component_position(generator_output, f"R{i + 1}")
            handler_pos = self._extract_component_position(handler_output, f"R{i + 1}")

            # Positions should be identical (after boundary validation)
            assert generator_pos is not None, f"Generator position not found for R{i + 1}"
            assert handler_pos is not None, f"Handler position not found for R{i + 1}"

            # Both should produce the same final position
            assert generator_pos == handler_pos, (
                f"Position mismatch for R{i + 1}: {generator_pos} vs {handler_pos}"
            )

    def _compare_structures_ignore_uuids(self, struct1, struct2):
        """Compare S-expression structures while ignoring UUID differences."""
        # Remove UUIDs for comparison
        cleaned_struct1 = self._remove_uuids(struct1)
        cleaned_struct2 = self._remove_uuids(struct2)

        # Compare cleaned structures
        assert self._structures_equal(cleaned_struct1, cleaned_struct2), (
            f"Structures don't match:\n{cleaned_struct1}\nvs\n{cleaned_struct2}"
        )

    def _remove_uuids(self, structure):
        """Recursively remove UUID fields from S-expression structure."""
        if isinstance(structure, list):
            result = []
            skip_next = False
            for i, item in enumerate(structure):
                if skip_next:
                    skip_next = False
                    continue

                if isinstance(item, sexpdata.Symbol) and str(item) == "uuid":
                    skip_next = True  # Skip the UUID value
                    continue

                result.append(self._remove_uuids(item))
            return result
        else:
            return structure

    def _structures_equal(self, struct1, struct2):
        """Check if two S-expression structures are equal."""
        if type(struct1) != type(struct2):
            return False

        if isinstance(struct1, list):
            if len(struct1) != len(struct2):
                return False
            return all(self._structures_equal(a, b) for a, b in zip(struct1, struct2))
        else:
            return str(struct1) == str(struct2)

    def _verify_component_present(self, parsed_structure, reference, value, lib_id):
        """Verify that a component with given properties is present in the structure."""
        symbols = self._extract_symbols(parsed_structure)

        for symbol in symbols:
            if self._symbol_matches_component(symbol, reference, value, lib_id):
                return

        pytest.fail(f"Component {reference} with value {value} and lib_id {lib_id} not found")

    def _verify_power_symbol_present(self, parsed_structure, reference, power_type):
        """Verify that a power symbol is present in the structure."""
        symbols = self._extract_symbols(parsed_structure)

        for symbol in symbols:
            if self._symbol_matches_power(symbol, reference, power_type):
                return

        pytest.fail(f"Power symbol {reference} with type {power_type} not found")

    def _verify_wire_present(self, parsed_structure):
        """Verify that at least one wire is present in the structure."""
        wires = self._extract_wires(parsed_structure)
        assert len(wires) > 0, "No wires found in structure"

    def _extract_symbols(self, parsed_structure):
        """Extract all symbol entries from parsed structure."""
        symbols = []

        def extract_recursive(item):
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol) and str(item[0]) == "symbol":
                    symbols.append(item)
                else:
                    for subitem in item:
                        extract_recursive(subitem)

        extract_recursive(parsed_structure)
        return symbols

    def _extract_lib_symbols(self, parsed_structure):
        """Extract lib_symbols section from parsed structure."""
        lib_symbols = []

        def find_lib_symbols(item):
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol) and str(item[0]) == "lib_symbols":
                    for subitem in item[1:]:
                        if isinstance(subitem, list) and len(subitem) > 0:
                            if (
                                isinstance(subitem[0], sexpdata.Symbol)
                                and str(subitem[0]) == "symbol"
                            ):
                                lib_symbols.append(subitem)
                else:
                    for subitem in item:
                        find_lib_symbols(subitem)

        find_lib_symbols(parsed_structure)
        return lib_symbols

    def _extract_wires(self, parsed_structure):
        """Extract all wire entries from parsed structure."""
        wires = []

        def extract_recursive(item):
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol) and str(item[0]) == "wire":
                    wires.append(item)
                else:
                    for subitem in item:
                        extract_recursive(subitem)

        extract_recursive(parsed_structure)
        return wires

    def _symbol_matches_component(self, symbol, reference, value, lib_id):
        """Check if symbol matches component specifications."""
        # Extract properties from symbol
        properties = {}
        lib_id_found = None

        for item in symbol[1:]:
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol):
                    if str(item[0]) == "lib_id" and len(item) > 1:
                        lib_id_found = str(item[1])
                    elif str(item[0]) == "property" and len(item) >= 3:
                        prop_name = str(item[1])
                        prop_value = str(item[2])
                        properties[prop_name] = prop_value

        return (
            lib_id_found == lib_id
            and properties.get("Reference") == reference
            and properties.get("Value") == value
        )

    def _symbol_matches_power(self, symbol, reference, power_type):
        """Check if symbol matches power symbol specifications."""
        # Extract properties from symbol
        properties = {}
        lib_id_found = None

        for item in symbol[1:]:
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol):
                    if str(item[0]) == "lib_id" and len(item) > 1:
                        lib_id_found = str(item[1])
                    elif str(item[0]) == "property" and len(item) >= 3:
                        prop_name = str(item[1])
                        prop_value = str(item[2])
                        properties[prop_name] = prop_value

        expected_lib_id = f"power:{power_type}"
        return (
            lib_id_found == expected_lib_id
            and properties.get("Reference") == reference
            and properties.get("Value") == power_type
        )

    def _extract_component_position(self, sexpr_output, reference):
        """Extract component position from S-expression output."""
        parsed = sexpdata.loads(sexpr_output)
        symbols = self._extract_symbols(parsed)

        for symbol in symbols:
            # Check if this is the right component by reference
            ref_found = None
            position = None

            for item in symbol[1:]:
                if isinstance(item, list) and len(item) > 0:
                    if isinstance(item[0], sexpdata.Symbol):
                        if str(item[0]) == "property" and len(item) >= 3:
                            if str(item[1]) == "Reference":
                                ref_found = str(item[2])
                        elif str(item[0]) == "at" and len(item) >= 3:
                            position = (float(item[1]), float(item[2]))

            if ref_found == reference and position:
                return position

        return None


class TestSExpressionFormat:
    """Test S-expression format compliance and KiCad compatibility."""

    def test_handler_produces_valid_sexpr(self):
        """Test that handler output is valid S-expression format."""
        handler = SExpressionHandler()

        result = handler.generate_schematic(
            "Test Circuit",
            [
                {
                    "reference": "R1",
                    "value": "1k",
                    "symbol_library": "Device",
                    "symbol_name": "R",
                    "position": (10, 10),
                }
            ],
            [],
            [],
        )

        # Should parse without error
        parsed = sexpdata.loads(result)
        assert isinstance(parsed, list)
        assert str(parsed[0]) == "kicad_sch"

    def test_kicad_format_requirements(self):
        """Test that output meets KiCad format requirements."""
        handler = SExpressionHandler()

        result = handler.generate_schematic(
            "KiCad Format Test",
            [
                {
                    "reference": "R1",
                    "value": "1k",
                    "symbol_library": "Device",
                    "symbol_name": "R",
                    "position": (10, 10),
                }
            ],
            [{"reference": "#PWR001", "power_type": "VCC", "position": (20, 10)}],
            [{"start_x": 10, "start_y": 15, "end_x": 20, "end_y": 15}],
        )

        parsed = sexpdata.loads(result)

        # Check required top-level elements
        elements = [str(item[0]) if isinstance(item, list) else str(item) for item in parsed[1:]]
        required_elements = [
            "version",
            "generator",
            "uuid",
            "paper",
            "title_block",
            "sheet_instances",
        ]

        for element in required_elements:
            assert element in elements, f"Missing required element: {element}"

    def test_round_trip_compatibility(self):
        """Test that generated S-expressions can be parsed and regenerated."""
        handler = SExpressionHandler()

        original = handler.generate_schematic(
            "Round Trip Test",
            [
                {
                    "reference": "R1",
                    "value": "1k",
                    "symbol_library": "Device",
                    "symbol_name": "R",
                    "position": (10, 10),
                }
            ],
            [],
            [],
        )

        # Parse the generated S-expression
        parsed = handler.parse_schematic(original)

        # Should be valid structure
        assert isinstance(parsed, dict)
        assert "version" in parsed
        assert "generator" in parsed
        assert "uuid" in parsed

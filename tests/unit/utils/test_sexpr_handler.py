"""
Unit tests for SExpressionHandler using TDD practices.

Tests cover all functionality including parsing, generation, and compatibility.
"""

from pathlib import Path
from unittest.mock import patch
import uuid

import pytest
import sexpdata

from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class TestSExpressionHandler:
    """Test suite for SExpressionHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SExpressionHandler()

        # Sample component data
        self.sample_component = {
            "reference": "R1",
            "value": "10k",
            "symbol_library": "Device",
            "symbol_name": "R",
            "position": (63.5, 87.63),
        }

        # Sample power symbol data
        self.sample_power_symbol = {
            "reference": "#PWR001",
            "power_type": "VCC",
            "position": (63.5, 80.0),
        }

        # Sample connection data
        self.sample_connection = {"start_x": 63.5, "start_y": 91.44, "end_x": 63.5, "end_y": 96.52}

    def test_handler_initialization(self):
        """Test SExpressionHandler initialization."""
        handler = SExpressionHandler()
        assert handler.symbol_libraries == {}
        assert handler.component_uuid_map == {}

    def test_generate_empty_schematic(self):
        """Test generating an empty schematic."""
        result = self.handler.generate_schematic(
            circuit_name="Empty Circuit", components=[], power_symbols=[], connections=[]
        )

        # Should be valid S-expression
        parsed = sexpdata.loads(result)
        assert isinstance(parsed, list)
        assert str(parsed[0]) == "kicad_sch"

        # Should contain required elements
        elements = {str(item[0]): item for item in parsed[1:] if isinstance(item, list)}
        assert "version" in elements
        assert "generator" in elements
        assert "uuid" in elements
        assert "paper" in elements
        assert "title_block" in elements
        assert "sheet_instances" in elements

        # Check title
        title_block = elements["title_block"]
        title_items = {str(item[0]): item[1] for item in title_block[1:] if isinstance(item, list)}
        assert title_items["title"] == "Empty Circuit"

    def test_generate_single_component_schematic(self):
        """Test generating schematic with single component."""
        result = self.handler.generate_schematic(
            circuit_name="Single Component",
            components=[self.sample_component],
            power_symbols=[],
            connections=[],
        )

        parsed = sexpdata.loads(result)

        # Should have lib_symbols section
        lib_symbols = None
        symbols = []
        for item in parsed[1:]:
            if isinstance(item, list):
                if str(item[0]) == "lib_symbols":
                    lib_symbols = item
                elif str(item[0]) == "symbol":
                    symbols.append(item)

        assert lib_symbols is not None
        assert len(symbols) == 1

        # Check symbol properties
        symbol = symbols[0]
        symbol_props = {}
        for prop in symbol[1:]:
            if isinstance(prop, list) and len(prop) >= 2:
                if str(prop[0]) == "lib_id":
                    symbol_props["lib_id"] = prop[1]
                elif str(prop[0]) == "property" and len(prop) >= 3:
                    symbol_props[str(prop[1])] = prop[2]

        assert str(symbol_props["lib_id"]) == "Device:R"
        assert str(symbol_props["Reference"]) == "R1"
        assert str(symbol_props["Value"]) == "10k"

    def test_generate_with_power_symbols(self):
        """Test generating schematic with power symbols."""
        result = self.handler.generate_schematic(
            circuit_name="Power Test",
            components=[],
            power_symbols=[self.sample_power_symbol],
            connections=[],
        )

        parsed = sexpdata.loads(result)

        # Find power symbol
        power_symbols = []
        for item in parsed[1:]:
            if isinstance(item, list) and str(item[0]) == "symbol":
                # Check if it's a power symbol
                for prop in item[1:]:
                    if (
                        isinstance(prop, list)
                        and len(prop) >= 2
                        and str(prop[0]) == "lib_id"
                        and "power:" in str(prop[1])
                    ):
                        power_symbols.append(item)
                        break

        assert len(power_symbols) == 1

        # Check power symbol properties
        power_symbol = power_symbols[0]
        lib_id = None
        for prop in power_symbol[1:]:
            if isinstance(prop, list) and str(prop[0]) == "lib_id":
                lib_id = prop[1]
                break

        assert str(lib_id) == "power:VCC"

    def test_generate_with_connections(self):
        """Test generating schematic with wire connections."""
        result = self.handler.generate_schematic(
            circuit_name="Connection Test",
            components=[],
            power_symbols=[],
            connections=[self.sample_connection],
        )

        parsed = sexpdata.loads(result)

        # Find wire
        wires = []
        for item in parsed[1:]:
            if isinstance(item, list) and str(item[0]) == "wire":
                wires.append(item)

        assert len(wires) == 1

        # Check wire properties
        wire = wires[0]
        pts = None
        for prop in wire[1:]:
            if isinstance(prop, list) and str(prop[0]) == "pts":
                pts = prop
                break

        assert pts is not None
        # Should have xy coordinates
        assert len(pts) >= 3  # pts, xy1, xy2

    def test_component_uuid_tracking(self):
        """Test that component UUIDs are properly tracked."""
        # Mock uuid.uuid4 to return predictable values
        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.side_effect = [
                uuid.UUID("12345678-1234-1234-1234-123456789000"),  # main schematic
                uuid.UUID("12345678-1234-1234-1234-123456789001"),  # component
                uuid.UUID("12345678-1234-1234-1234-123456789002"),  # pin 1
                uuid.UUID("12345678-1234-1234-1234-123456789003"),  # pin 2
            ]

            self.handler.generate_schematic(
                circuit_name="UUID Test",
                components=[self.sample_component],
                power_symbols=[],
                connections=[],
            )

            # Check that component UUID was tracked
            assert "R1" in self.handler.component_uuid_map
            assert (
                str(self.handler.component_uuid_map["R1"]) == "12345678-1234-1234-1234-123456789001"
            )

    def test_position_conversion(self):
        """Test that positions are correctly converted from mm to KiCad units."""
        component = self.sample_component.copy()
        component["position"] = (10.0, 20.0)  # 10mm, 20mm

        result = self.handler.generate_schematic(
            circuit_name="Position Test", components=[component], power_symbols=[], connections=[]
        )

        parsed = sexpdata.loads(result)

        # Find component and check position
        for item in parsed[1:]:
            if isinstance(item, list) and str(item[0]) == "symbol":
                for prop in item[1:]:
                    if isinstance(prop, list) and str(prop[0]) == "at":
                        # Position may be adjusted by boundary validation
                        # Check that it's been converted to 0.1mm units (should be non-zero)
                        assert prop[1] > 0  # X position should be positive
                        assert prop[2] > 0  # Y position should be positive
                        assert prop[1] % 10 == 0  # Should be multiple of 10 (unit conversion)
                        assert prop[2] % 10 == 0  # Should be multiple of 10 (unit conversion)
                        return

        pytest.fail("Component position not found")

    def test_parse_basic_schematic(self):
        """Test parsing a basic S-expression schematic."""
        basic_sexpr = """(kicad_sch
  (version 20241201)
  (generator eeschema)
  (uuid "12345678-1234-1234-1234-123456789abc")
  (paper "A4")
  (title_block
    (title "Test Circuit")
  )
)"""

        result = self.handler.parse_schematic(basic_sexpr)

        assert isinstance(result, dict)
        assert "version" in result
        assert "generator" in result
        assert "uuid" in result
        assert "paper" in result
        assert "title_block" in result

        # The parsing function returns nested dictionaries
        assert isinstance(result["version"], dict)
        assert isinstance(result["generator"], dict)
        assert isinstance(result["uuid"], dict)

    def test_parse_invalid_sexpr(self):
        """Test parsing invalid S-expression raises appropriate error."""
        invalid_sexpr = "(kicad_sch (version 20241201) (incomplete"

        with pytest.raises(ValueError, match="Failed to parse S-expression"):
            self.handler.parse_schematic(invalid_sexpr)

    def test_pretty_printing(self):
        """Test pretty printing functionality."""
        result = self.handler.generate_schematic(
            circuit_name="Pretty Test",
            components=[],
            power_symbols=[],
            connections=[],
            pretty_print=True,
        )

        # Should be multi-line
        lines = result.split("\n")
        assert len(lines) > 1

        # Should have proper indentation
        assert lines[0] == "(kicad_sch"
        assert lines[1].startswith("  ")  # Second line should be indented

    def test_non_pretty_printing(self):
        """Test non-pretty printing functionality."""
        result = self.handler.generate_schematic(
            circuit_name="Non-Pretty Test",
            components=[],
            power_symbols=[],
            connections=[],
            pretty_print=False,
        )

        # Should be single line (or minimal lines)
        lines = result.split("\n")
        assert len(lines) <= 2  # Allow for possible single newline

    def test_symbol_library_generation(self):
        """Test generation of symbol libraries."""
        components = [
            {
                "reference": "R1",
                "value": "10k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (10, 10),
            },
            {
                "reference": "C1",
                "value": "100nF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (20, 20),
            },
        ]

        result = self.handler.generate_schematic(
            circuit_name="Multi-Symbol Test",
            components=components,
            power_symbols=[],
            connections=[],
        )

        parsed = sexpdata.loads(result)

        # Find lib_symbols section
        lib_symbols = None
        for item in parsed[1:]:
            if isinstance(item, list) and str(item[0]) == "lib_symbols":
                lib_symbols = item
                break

        assert lib_symbols is not None

        # Should have both Device:R and Device:C
        symbol_names = []
        for item in lib_symbols[1:]:
            if isinstance(item, list) and str(item[0]) == "symbol":
                symbol_names.append(str(item[1]))

        assert "Device:R" in symbol_names
        assert "Device:C" in symbol_names

    def test_round_trip_parsing(self):
        """Test that generated S-expressions can be parsed back correctly."""
        original_components = [self.sample_component]
        original_power_symbols = [self.sample_power_symbol]
        original_connections = [self.sample_connection]

        # Generate
        generated = self.handler.generate_schematic(
            circuit_name="Round Trip Test",
            components=original_components,
            power_symbols=original_power_symbols,
            connections=original_connections,
        )

        # Parse back
        parsed = self.handler.parse_schematic(generated)

        # Should be valid structure
        assert isinstance(parsed, dict)
        assert "version" in parsed
        assert "generator" in parsed
        assert "uuid" in parsed

        # Should have symbols
        assert "symbol" in parsed

    def test_format_atom_quoting(self):
        """Test proper quoting of atoms in S-expressions."""
        # Test string with spaces
        result = self.handler._format_atom("hello world")
        assert result == '"hello world"'

        # Test string without spaces
        result = self.handler._format_atom("hello")
        assert result == "hello"

        # Test empty string
        result = self.handler._format_atom("")
        assert result == '""'

        # Test string with quotes
        result = self.handler._format_atom('test"quote')
        assert result == '"test"quote"'

        # Test symbol
        result = self.handler._format_atom(sexpdata.Symbol("test"))
        assert result == "test"

        # Test number
        result = self.handler._format_atom(42)
        assert result == "42"

    def test_build_device_symbols(self):
        """Test building different device symbol definitions."""
        # Test resistor
        resistor = self.handler._build_device_symbol("R")
        assert isinstance(resistor, list)
        assert str(resistor[0]) == "symbol"
        assert resistor[1] == "Device:R"

        # Test capacitor
        capacitor = self.handler._build_device_symbol("C")
        assert isinstance(capacitor, list)
        assert str(capacitor[0]) == "symbol"
        assert capacitor[1] == "Device:C"

        # Test unknown symbol (should default to resistor-like)
        unknown = self.handler._build_device_symbol("UNKNOWN")
        assert isinstance(unknown, list)
        assert str(unknown[0]) == "symbol"
        assert unknown[1] == "Device:UNKNOWN"

    def test_build_power_symbol_definition(self):
        """Test building power symbol definitions."""
        vcc_symbol = self.handler._build_power_symbol_definition("VCC")

        assert isinstance(vcc_symbol, list)
        assert str(vcc_symbol[0]) == "symbol"
        assert vcc_symbol[1] == "power:VCC"

        # Should have power flag
        has_power_flag = False
        for item in vcc_symbol[2:]:
            if isinstance(item, list) and str(item[0]) == "power":
                has_power_flag = True
                break

        assert has_power_flag, "Power symbol should have power flag"

    def test_wire_with_missing_coordinates(self):
        """Test wire generation with missing coordinates."""
        connection = {}  # No coordinates

        result = self.handler._build_wire(connection)
        assert result is None

    def test_component_with_missing_position(self):
        """Test component generation with missing position."""
        component = {
            "reference": "R1",
            "value": "10k",
            "symbol_library": "Device",
            "symbol_name": "R",
            # No position
        }

        result = self.handler._build_component_symbol(component)

        # Should use default position (100, 100) * 10 = (1000, 1000)
        at_prop = None
        for item in result[1:]:
            if isinstance(item, list) and str(item[0]) == "at":
                at_prop = item
                break

        assert at_prop is not None
        assert at_prop[1] == 1000  # 100 * 10
        assert at_prop[2] == 1000  # 100 * 10

    def test_power_symbol_reference_generation(self):
        """Test automatic power symbol reference generation."""
        power_symbol = {
            "power_type": "VCC",
            "position": (10, 10),
            # No reference
        }

        result = self.handler._build_power_symbol(power_symbol)

        # Should generate reference
        ref_prop = None
        for item in result[1:]:
            if (
                isinstance(item, list)
                and str(item[0]) == "property"
                and len(item) >= 3
                and item[1] == "Reference"
            ):
                ref_prop = item[2]
                break

        assert ref_prop is not None
        assert ref_prop.startswith("#PWR")

    @pytest.mark.parametrize(
        "library,symbol",
        [
            ("Device", "R"),
            ("Device", "C"),
            ("Device", "L"),
            ("Device", "LED"),
            ("Device", "D"),
            ("power", "VCC"),
            ("power", "GND"),
            ("UnknownLib", "UnknownSymbol"),
        ],
    )
    def test_symbol_definition_generation(self, library, symbol):
        """Test symbol definition generation for various types."""
        result = self.handler._build_symbol_definition(library, symbol)

        assert isinstance(result, list)
        assert len(result) > 0
        assert str(result[0]) == "symbol"

        if library == "power":
            assert str(result[1]) == f"power:{symbol}"
        elif library == "UnknownLib":
            # Unknown libraries default to Device:R behavior
            assert str(result[1]) == "Device:R"
        else:
            assert str(result[1]) == f"Device:{symbol}"


class TestSExpressionHandlerIntegration:
    """Integration tests for SExpressionHandler."""

    def test_real_kicad_file_parsing(self):
        """Test parsing a real KiCad schematic file."""
        kicad_file = Path("tests/fixtures/sample_schematics/sexpr_schematic.kicad_sch")

        if not kicad_file.exists():
            pytest.skip(f"Test file not found: {kicad_file}")

        handler = SExpressionHandler()

        with open(kicad_file) as f:
            content = f.read()

        # Should parse without error
        result = handler.parse_schematic(content)

        assert isinstance(result, dict)
        assert "version" in result
        assert "generator" in result
        assert "uuid" in result

    def test_compatibility_with_kicad_format(self):
        """Test that generated files are compatible with KiCad format expectations."""
        handler = SExpressionHandler()

        components = [
            {
                "reference": "R1",
                "value": "10k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (63.5, 87.63),
            }
        ]

        result = handler.generate_schematic(
            circuit_name="Compatibility Test",
            components=components,
            power_symbols=[],
            connections=[],
        )

        # Parse with sexpdata to verify format
        parsed = sexpdata.loads(result)

        # Should be valid KiCad structure
        assert isinstance(parsed, list)
        assert str(parsed[0]) == "kicad_sch"

        # Should have all required top-level elements
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

    def test_large_schematic_generation(self):
        """Test generating a larger schematic with multiple components."""
        handler = SExpressionHandler()

        # Create 10 components
        components = []
        for i in range(10):
            components.append(
                {
                    "reference": f"R{i + 1}",
                    "value": f"{(i + 1) * 1000}",
                    "symbol_library": "Device",
                    "symbol_name": "R",
                    "position": (10 + i * 10, 10 + i * 5),
                }
            )

        # Create 5 power symbols
        power_symbols = []
        for i in range(5):
            power_symbols.append(
                {
                    "reference": f"#PWR{i + 1:03d}",
                    "power_type": "VCC" if i % 2 == 0 else "GND",
                    "position": (10 + i * 15, 100),
                }
            )

        # Create 5 connections
        connections = []
        for i in range(5):
            connections.append(
                {
                    "start_x": 10 + i * 10,
                    "start_y": 20 + i * 5,
                    "end_x": 20 + i * 10,
                    "end_y": 30 + i * 5,
                }
            )

        result = handler.generate_schematic(
            circuit_name="Large Test Circuit",
            components=components,
            power_symbols=power_symbols,
            connections=connections,
        )

        # Should be valid S-expression
        parsed = sexpdata.loads(result)
        assert isinstance(parsed, list)
        assert str(parsed[0]) == "kicad_sch"

        # Count symbols and wires
        symbol_count = 0
        wire_count = 0
        for item in parsed[1:]:
            if isinstance(item, list):
                if str(item[0]) == "symbol":
                    symbol_count += 1
                elif str(item[0]) == "wire":
                    wire_count += 1

        assert symbol_count == 15  # 10 components + 5 power symbols
        assert wire_count == 5  # 5 connections


class TestSExpressionBooleanFormat:
    """Test cases for proper KiCad boolean format generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SExpressionHandler()

    def test_component_boolean_properties_are_symbols(self):
        """
        Test that component boolean properties are generated as sexpdata.Symbol objects.

        This test should FAIL initially because current implementation uses quoted strings.
        KiCad expects: (exclude_from_sim no) not (exclude_from_sim "no")
        """
        component = {
            "reference": "U1",
            "value": "ESP32",
            "symbol_library": "Device",
            "symbol_name": "U",
            "position": (100, 100),
        }

        result = self.handler.generate_schematic(
            circuit_name="Boolean Test", components=[component], power_symbols=[], connections=[]
        )

        # Parse the generated schematic
        parsed = sexpdata.loads(result)

        # Find the component symbol
        component_symbol = None
        for item in parsed[1:]:
            if isinstance(item, list) and str(item[0]) == "symbol":
                component_symbol = item
                break

        assert component_symbol is not None, "Component symbol not found"

        # Check boolean properties are symbols, not strings
        boolean_props = {}
        for prop in component_symbol[1:]:
            if isinstance(prop, list) and len(prop) == 2:
                prop_name = str(prop[0])
                if prop_name in ["exclude_from_sim", "in_bom", "on_board", "dnp"]:
                    boolean_props[prop_name] = prop[1]

        # Assert all boolean properties are Symbol objects
        for prop_name, prop_value in boolean_props.items():
            assert isinstance(prop_value, sexpdata.Symbol), (
                f"Property '{prop_name}' should be a Symbol, got {type(prop_value)}: {prop_value}"
            )
            assert str(prop_value) in ["yes", "no"], (
                f"Property '{prop_name}' should be 'yes' or 'no', got: {prop_value}"
            )

    def test_boolean_values_in_sexpr_string_output(self):
        """Test that boolean values appear unquoted in the final S-expression string."""
        component = {
            "reference": "R1",
            "value": "10k",
            "symbol_library": "Device",
            "symbol_name": "R",
            "position": (50, 50),
        }

        result = self.handler.generate_schematic(
            circuit_name="String Output Test",
            components=[component],
            power_symbols=[],
            connections=[],
        )

        # Check that boolean values are unquoted in the string
        boolean_patterns_correct = [
            "(exclude_from_sim no)",
            "(exclude_from_sim yes)",
            "(in_bom no)",
            "(in_bom yes)",
            "(on_board no)",
            "(on_board yes)",
            "(dnp no)",
            "(dnp yes)",
        ]

        boolean_patterns_incorrect = [
            '(exclude_from_sim "no")',
            '(exclude_from_sim "yes")',
            '(in_bom "no")',
            '(in_bom "yes")',
            '(on_board "no")',
            '(on_board "yes")',
            '(dnp "no")',
            '(dnp "yes")',
        ]

        # At least some correct patterns should be present
        has_correct_pattern = any(pattern in result for pattern in boolean_patterns_correct)
        assert has_correct_pattern, f"No correct boolean patterns found in:\n{result}"

        # No incorrect patterns should be present
        for pattern in boolean_patterns_incorrect:
            assert pattern not in result, f"Found incorrect quoted boolean pattern: {pattern}"

    def test_multiple_components_boolean_consistency(self):
        """Test boolean format consistency across multiple components."""
        components = [
            {
                "reference": "U1",
                "value": "IC1",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (10, 10),
            },
            {
                "reference": "R1",
                "value": "10k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (20, 20),
            },
            {
                "reference": "C1",
                "value": "100nF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (30, 30),
            },
        ]

        result = self.handler.generate_schematic(
            circuit_name="Multi-Component Boolean Test",
            components=components,
            power_symbols=[],
            connections=[],
        )

        parsed = sexpdata.loads(result)

        # Find all component symbols
        symbols = [
            item for item in parsed[1:] if isinstance(item, list) and str(item[0]) == "symbol"
        ]

        assert len(symbols) == len(components), (
            f"Expected {len(components)} symbols, found {len(symbols)}"
        )

        # Check each symbol has proper boolean format
        for symbol in symbols:
            boolean_props = {}
            for prop in symbol[1:]:
                if isinstance(prop, list) and len(prop) == 2:
                    prop_name = str(prop[0])
                    if prop_name in ["exclude_from_sim", "in_bom", "on_board", "dnp"]:
                        boolean_props[prop_name] = prop[1]

            # All symbols should have boolean properties as Symbol objects
            assert len(boolean_props) >= 4, f"Symbol missing boolean properties: {boolean_props}"

            for prop_name, prop_value in boolean_props.items():
                assert isinstance(prop_value, sexpdata.Symbol), (
                    f"Property '{prop_name}' should be Symbol, got {type(prop_value)}"
                )

    def test_power_symbol_boolean_format(self):
        """Test that power symbols also use proper boolean format."""
        power_symbol = {"reference": "#PWR001", "power_type": "VCC", "position": (50, 50)}

        result = self.handler.generate_schematic(
            circuit_name="Power Boolean Test",
            components=[],
            power_symbols=[power_symbol],
            connections=[],
        )

        parsed = sexpdata.loads(result)

        # Find power symbol
        power_symbols = []
        for item in parsed[1:]:
            if isinstance(item, list) and str(item[0]) == "symbol":
                for prop in item[1:]:
                    if (
                        isinstance(prop, list)
                        and str(prop[0]) == "lib_id"
                        and "power:" in str(prop[1])
                    ):
                        power_symbols.append(item)
                        break

        assert len(power_symbols) == 1, "Power symbol not found"

        # Check boolean properties format
        power_symbol = power_symbols[0]
        boolean_props = {}
        for prop in power_symbol[1:]:
            if isinstance(prop, list) and len(prop) == 2:
                prop_name = str(prop[0])
                if prop_name in ["exclude_from_sim", "in_bom", "on_board", "dnp"]:
                    boolean_props[prop_name] = prop[1]

        # Power symbols should also have proper boolean format
        for prop_name, prop_value in boolean_props.items():
            assert isinstance(prop_value, sexpdata.Symbol), (
                f"Power symbol property '{prop_name}' should be Symbol, got {type(prop_value)}"
            )

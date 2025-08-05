"""
Tests for power symbol validation to prevent invalid KiCad symbol names.
"""

from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class TestPowerSymbolValidation:
    """Test power symbol generation to ensure valid KiCad format."""

    def test_valid_power_symbol_names(self):
        """Test that power symbols generate valid KiCad lib_id formats."""
        handler = SExpressionHandler()

        # Test power symbols that should work
        power_symbols = [
            {"reference": "VCC1", "power_type": "VCC", "position": (10, 10)},
            {"reference": "GND1", "power_type": "GND", "position": (10, 20)},
            {"reference": "PWR1", "power_type": "+5V", "position": (10, 30)},
            {"reference": "PWR2", "power_type": "+3V3", "position": (10, 40)},
            {"reference": "PWR3", "power_type": "+12V", "position": (10, 50)},
            {"reference": "PWR4", "power_type": "-12V", "position": (10, 60)},
        ]

        components = []

        # Generate schematic
        result = handler.generate_schematic(
            circuit_name="test_power_validation",
            components=components,
            power_symbols=power_symbols,
            connections=[],
            pretty_print=True,
        )

        # Verify that lib_symbols contains only valid power symbol names
        assert "power:VCC" in result
        assert "power:GND" in result
        assert "power:+5V" in result
        assert "power:+3V3" in result
        assert "power:+12V" in result
        assert "power:-12V" in result

        # Verify that invalid formats are not present
        invalid_patterns = [
            "VCC_5V:",
            "VCC_3V3:",
            "GND:",
            "+5V at",
            "+3V3 at",
            "GND at",
        ]

        for pattern in invalid_patterns:
            assert pattern not in result, (
                f"Found invalid pattern '{pattern}' in generated schematic"
            )

    def test_power_symbol_lib_id_format(self):
        """Test that power symbol lib_id uses correct format."""
        handler = SExpressionHandler()

        # Test lib_symbols generation specifically
        power_symbols = [
            {"reference": "VCC1", "power_type": "+5V", "position": (10, 10)},
        ]

        result = handler.generate_schematic(
            circuit_name="test_lib_id",
            components=[],
            power_symbols=power_symbols,
            connections=[],
            pretty_print=True,
        )

        # The lib_symbols section should contain the correct format
        lines = result.split("\n")
        lib_symbols_section = False

        for line in lines:
            if "lib_symbols" in line:
                lib_symbols_section = True
                continue
            if lib_symbols_section and "symbol" in line and "power:" in line:
                # Should be format: (symbol "power:+5V"
                assert '"power:+5V"' in line, f"Invalid power symbol format in line: {line}"
                # Should NOT contain invalid formats
                assert "VCC_5V:" not in line
                assert "+5V at" not in line
                break

    def test_prevent_concatenated_power_names(self):
        """Test that power symbol names are not incorrectly concatenated."""
        handler = SExpressionHandler()

        # Test case that could potentially cause concatenation issues
        power_symbols = [
            {"reference": "VCC_MAIN", "power_type": "+5V", "position": (10, 10)},
        ]

        result = handler.generate_schematic(
            circuit_name="test_concatenation",
            components=[],
            power_symbols=power_symbols,
            connections=[],
            pretty_print=True,
        )

        # Should use power_type for lib_id, not reference
        assert "power:+5V" in result
        # Should not concatenate reference with power_type
        assert "VCC_MAIN_5V" not in result
        assert "VCC_MAIN: +5V at" not in result

    def test_power_symbol_validation_in_build_symbol_definition(self):
        """Test the _build_symbol_definition method for power symbols."""
        handler = SExpressionHandler()

        # Test valid power symbol types
        valid_power_types = ["VCC", "GND", "+5V", "+3V3", "+12V", "-12V"]

        for power_type in valid_power_types:
            symbol_def = handler._build_symbol_definition("power", power_type)

            # Should be format: ['symbol', 'power:+5V', ['power']]
            assert str(symbol_def[0]) == "symbol"
            assert symbol_def[1] == f"power:{power_type}"
            assert len(symbol_def) == 3  # symbol, lib_id, power flag
            assert str(symbol_def[2][0]) == "power"

    def test_reject_invalid_power_symbol_formats(self):
        """Test that the system rejects clearly invalid power symbol formats."""
        handler = SExpressionHandler()

        # These should not appear in any generated S-expressions
        invalid_formats = [
            "power:VCC_5V: +5V at",
            "power:VCC_3V3: +3V3 at",
            "power:GND: GND at",
        ]

        power_symbols = [
            {"reference": "VCC1", "power_type": "+5V", "position": (10, 10)},
            {"reference": "VCC2", "power_type": "+3V3", "position": (10, 20)},
            {"reference": "GND1", "power_type": "GND", "position": (10, 30)},
        ]

        result = handler.generate_schematic(
            circuit_name="test_invalid_formats",
            components=[],
            power_symbols=power_symbols,
            connections=[],
            pretty_print=True,
        )

        for invalid_format in invalid_formats:
            assert invalid_format not in result, (
                f"Found invalid format '{invalid_format}' in generated schematic"
            )

"""
Test module for KiCad S-expression boolean format validation.

This module contains tests to ensure that boolean values in KiCad S-expressions
are generated as unquoted symbols (e.g., 'no', 'yes') rather than quoted strings
(e.g., "no", "yes"), which cause KiCad parser errors.

Following TDD methodology - these tests should FAIL initially until the fix is implemented.
"""

import pytest
import sexpdata

from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class TestBooleanFormatValidation:
    """Test cases for KiCad boolean format validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SExpressionHandler()
        self.test_component = {
            "reference": "U1",
            "value": "ESP32-WROOM-32",
            "lib_id": "Device:U",
            "position": {"x": 100, "y": 100, "angle": 0},
            "uuid": "test-uuid-1234",
        }

    def test_boolean_values_are_unquoted_symbols(self):
        """
        Test that boolean values in component symbols are generated as unquoted symbols.

        This test should FAIL initially because the current implementation uses quoted strings.
        KiCad expects: (exclude_from_sim no) not (exclude_from_sim "no")
        """
        # Generate symbol expression
        symbol_expr = self.handler._build_component_symbol(self.test_component)

        # Find boolean properties in the generated expression
        boolean_props = {}
        for item in symbol_expr:
            if isinstance(item, list) and len(item) == 2:
                prop_name = str(item[0])
                if prop_name in ["exclude_from_sim", "in_bom", "on_board", "dnp"]:
                    boolean_props[prop_name] = item[1]

        # Assert that boolean values are symbols, not strings
        for prop_name, prop_value in boolean_props.items():
            assert isinstance(prop_value, sexpdata.Symbol), (
                f"Property '{prop_name}' should be a Symbol, got {type(prop_value)} with value {prop_value}"
            )
            assert str(prop_value) in ["yes", "no"], (
                f"Property '{prop_name}' should be 'yes' or 'no', got '{prop_value}'"
            )

    def test_generated_schematic_parses_without_kicad_error(self):
        """
        Test that generated S-expressions don't trigger "Expecting 'yes or no'" error.

        This simulates the KiCad parser behavior that expects unquoted boolean values.
        """
        # Generate a complete symbol
        symbol_expr = self.handler._build_component_symbol(self.test_component)

        # Convert to S-expression string
        sexpr_string = sexpdata.dumps(symbol_expr)

        # Check that boolean values are not quoted in the string representation
        # This simulates what KiCad parser sees
        assert (
            "(exclude_from_sim no)" in sexpr_string or "(exclude_from_sim yes)" in sexpr_string
        ), "exclude_from_sim should have unquoted boolean value"
        assert "(in_bom no)" in sexpr_string or "(in_bom yes)" in sexpr_string, (
            "in_bom should have unquoted boolean value"
        )
        assert "(on_board no)" in sexpr_string or "(on_board yes)" in sexpr_string, (
            "on_board should have unquoted boolean value"
        )
        assert "(dnp no)" in sexpr_string or "(dnp yes)" in sexpr_string, (
            "dnp should have unquoted boolean value"
        )

        # Ensure NO quoted boolean values exist
        assert '(exclude_from_sim "no")' not in sexpr_string, (
            "exclude_from_sim should not have quoted boolean value"
        )
        assert '(exclude_from_sim "yes")' not in sexpr_string, (
            "exclude_from_sim should not have quoted boolean value"
        )

    def test_component_boolean_properties_format(self):
        """Test boolean properties format across different component types."""
        component_types = [
            {"reference": "U1", "value": "ESP32", "lib_id": "Device:U"},
            {"reference": "R1", "value": "10k", "lib_id": "Device:R"},
            {"reference": "C1", "value": "100nF", "lib_id": "Device:C"},
            {"reference": "LED1", "value": "Red", "lib_id": "Device:LED"},
        ]

        for comp_data in component_types:
            comp_data.update(
                {
                    "position": {"x": 100, "y": 100, "angle": 0},
                    "uuid": f"test-uuid-{comp_data['reference']}",
                }
            )

            symbol_expr = self.handler._build_component_symbol(comp_data)
            sexpr_string = sexpdata.dumps(symbol_expr)

            # Each component should have unquoted boolean values
            boolean_fields = ["exclude_from_sim", "in_bom", "on_board", "dnp"]
            for field in boolean_fields:
                # Should have unquoted values
                assert f"({field} no)" in sexpr_string or f"({field} yes)" in sexpr_string, (
                    f"Component {comp_data['reference']} should have unquoted {field} value"
                )
                # Should NOT have quoted values
                assert (
                    f'({field} "no")' not in sexpr_string and f'({field} "yes")' not in sexpr_string
                ), f"Component {comp_data['reference']} should not have quoted {field} value"

    def test_sexpdata_symbol_vs_string_output(self):
        """Test the difference between sexpdata.Symbol and string in final output."""
        # Create test expressions with both Symbol and string
        symbol_expr = [sexpdata.Symbol("exclude_from_sim"), sexpdata.Symbol("no")]
        string_expr = [sexpdata.Symbol("exclude_from_sim"), "no"]

        symbol_output = sexpdata.dumps(symbol_expr)
        string_output = sexpdata.dumps(string_expr)

        # The Symbol version should produce unquoted output
        assert symbol_output == "(exclude_from_sim no)", (
            f"Symbol should produce unquoted output, got: {symbol_output}"
        )

        # The string version should produce quoted output (which is wrong for KiCad)
        assert string_output == '(exclude_from_sim "no")', (
            f"String should produce quoted output, got: {string_output}"
        )

    def test_robocar_schematic_boolean_format_fix(self):
        """
        Specific test for the robocar schematic issue that triggered this fix.

        This test recreates the scenario that caused the original error.
        """
        # Create components similar to the robocar schematic
        robocar_components = [
            {"reference": "U1", "value": "ESP32-WROOM-32", "lib_id": "Device:U"},
            {"reference": "U2", "value": "ESP32-CAM", "lib_id": "Device:U"},
            {"reference": "U3", "value": "TB6612FNG", "lib_id": "Device:U"},
            {"reference": "U4", "value": "PCA9685", "lib_id": "Device:U"},
        ]

        for i, comp_data in enumerate(robocar_components):
            comp_data.update(
                {
                    "position": {"x": 500 + i * 1000, "y": 500, "angle": 0},
                    "uuid": f"robocar-uuid-{i}",
                }
            )

            symbol_expr = self.handler._build_component_symbol(comp_data)
            sexpr_string = sexpdata.dumps(symbol_expr)

            # This should not contain the problematic quoted boolean values
            # that caused "Expecting 'yes or no'" error in KiCad
            problematic_patterns = [
                '(exclude_from_sim "no")',
                '(exclude_from_sim "yes")',
                '(in_bom "no")',
                '(in_bom "yes")',
                '(on_board "no")',
                '(on_board "yes")',
                '(dnp "no")',
                '(dnp "yes")',
            ]

            for pattern in problematic_patterns:
                assert pattern not in sexpr_string, (
                    f"Component {comp_data['reference']} contains problematic pattern: {pattern}"
                )


class TestBooleanUtilityFunctions:
    """Test cases for boolean utility functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SExpressionHandler()

    def test_create_boolean_symbol_utility(self):
        """Test utility function for creating boolean symbols (to be implemented)."""
        # This test will guide the implementation of a utility function

        # Test that the utility function creates proper symbols
        try:
            yes_symbol = self.handler._create_boolean_symbol("yes")
            no_symbol = self.handler._create_boolean_symbol("no")

            assert isinstance(yes_symbol, sexpdata.Symbol)
            assert isinstance(no_symbol, sexpdata.Symbol)
            assert str(yes_symbol) == "yes"
            assert str(no_symbol) == "no"
        except AttributeError:
            # This should fail initially since the utility function doesn't exist yet
            pytest.fail(
                "_create_boolean_symbol method not implemented yet - this test should fail until GREEN phase"
            )

    def test_boolean_symbol_validation(self):
        """Test validation of boolean symbol values."""
        # This will also fail initially
        try:
            # Should accept valid boolean strings
            valid_values = ["yes", "no", "true", "false"]
            for value in valid_values[:2]:  # KiCad uses yes/no
                symbol = self.handler._create_boolean_symbol(value)
                assert isinstance(symbol, sexpdata.Symbol)

            # Should reject invalid boolean strings
            with pytest.raises(ValueError):
                self.handler._create_boolean_symbol("invalid")
        except AttributeError:
            pytest.fail(
                "_create_boolean_symbol method not implemented yet - this test should fail until GREEN phase"
            )


# Additional test to check the _create_symbol_from_component method exists
class TestSExprHandlerInterface:
    """Test the interface of SExpressionHandler."""

    def test_create_symbol_from_component_method_exists(self):
        """Test that the expected method exists (might need to be created)."""
        handler = SExpressionHandler()

        # This might fail if the method doesn't exist yet
        assert hasattr(handler, "_build_component_symbol"), (
            "_build_component_symbol method should exist"
        )

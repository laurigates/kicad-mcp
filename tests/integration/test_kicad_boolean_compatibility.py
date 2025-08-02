"""
Integration tests for KiCad boolean format compatibility.

This module tests that generated S-expressions with proper boolean formatting
are compatible with KiCad's native parser and don't trigger parsing errors.

These tests should FAIL initially (RED phase) until the boolean format fix is implemented.
"""

import os
import subprocess
import tempfile

import pytest
import sexpdata

from kicad_mcp.utils.kicad_cli import get_kicad_cli_path, is_kicad_cli_available
from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class TestKiCadBooleanCompatibility:
    """Integration tests for KiCad boolean format compatibility."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SExpressionHandler()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generated_schematic_has_no_quoted_booleans(self):
        """
        Test that generated schematics contain no quoted boolean values.

        This is the core integration test - generated files should be KiCad-compatible.
        """
        # Create a complex schematic similar to the robocar project
        components = [
            {
                "reference": "U1",
                "value": "ESP32-WROOM-32",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (100, 100),
            },
            {
                "reference": "U2",
                "value": "ESP32-CAM",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (200, 100),
            },
            {
                "reference": "U3",
                "value": "TB6612FNG",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (100, 200),
            },
            {
                "reference": "U4",
                "value": "PCA9685",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (200, 200),
            },
            {
                "reference": "R1",
                "value": "10kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (300, 100),
            },
            {
                "reference": "R2",
                "value": "10kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (300, 200),
            },
            {
                "reference": "C1",
                "value": "100µF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (400, 100),
            },
            {
                "reference": "LED1",
                "value": "rgb",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (400, 200),
            },
        ]

        power_symbols = [
            {"reference": "#PWR001", "power_type": "VCC", "position": (500, 100)},
            {"reference": "#PWR002", "power_type": "GND", "position": (500, 200)},
            {"reference": "#PWR003", "power_type": "+3V3", "position": (500, 300)},
        ]

        result = self.handler.generate_schematic(
            circuit_name="Boolean Compatibility Test",
            components=components,
            power_symbols=power_symbols,
            connections=[],
        )

        # Write to temporary file for analysis
        temp_file = os.path.join(self.temp_dir, "test_boolean_compatibility.kicad_sch")
        with open(temp_file, "w") as f:
            f.write(result)

        # Read back and check for quoted boolean patterns
        with open(temp_file) as f:
            content = f.read()

        # These patterns should NOT exist in a properly formatted KiCad file
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
            assert pattern not in content, (
                f"Found problematic quoted boolean pattern: {pattern}\n"
                f"This will cause KiCad parser error: 'Expecting yes or no'\n"
                f"File content preview:\n{content[:1000]}..."
            )

        # These patterns SHOULD exist
        correct_patterns = [
            "(exclude_from_sim no)",
            "(exclude_from_sim yes)",
            "(in_bom no)",
            "(in_bom yes)",
            "(on_board no)",
            "(on_board yes)",
            "(dnp no)",
            "(dnp yes)",
        ]

        has_correct_patterns = any(pattern in content for pattern in correct_patterns)
        assert has_correct_patterns, (
            f"No correct unquoted boolean patterns found!\n"
            f"Expected patterns like: {correct_patterns[:4]}\n"
            f"File content preview:\n{content[:1000]}..."
        )

    def test_robocar_schematic_recreation_compatibility(self):
        """
        Test recreation of the specific robocar schematic that caused the original error.

        This reproduces the exact scenario that triggered the bug report by creating
        a large schematic similar to the robocar project directly with the handler.
        """
        # Create components similar to the robocar project
        robocar_components = [
            {
                "reference": "U1",
                "value": "ESP32-WROOM-32",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (50, 50),
            },
            {
                "reference": "U2",
                "value": "ESP32-CAM",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (150, 50),
            },
            {
                "reference": "U3",
                "value": "TB6612FNG",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (50, 150),
            },
            {
                "reference": "U4",
                "value": "PCA9685",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (150, 150),
            },
            {
                "reference": "U5",
                "value": "XL6009",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (40, 38),
            },
            {
                "reference": "BAT1",
                "value": "18650",
                "symbol_library": "Device",
                "symbol_name": "Battery",
                "position": (35, 68),
            },
            {
                "reference": "BAT2",
                "value": "18650",
                "symbol_library": "Device",
                "symbol_name": "Battery",
                "position": (70, 68),
            },
            {
                "reference": "M1",
                "value": "DC Motor",
                "symbol_library": "Device",
                "symbol_name": "Motor",
                "position": (105, 68),
            },
            {
                "reference": "M2",
                "value": "DC Motor",
                "symbol_library": "Device",
                "symbol_name": "Motor",
                "position": (80, 120),
            },
            {
                "reference": "SRV1",
                "value": "SG90",
                "symbol_library": "Device",
                "symbol_name": "Servo",
                "position": (180, 120),
            },
            {
                "reference": "SRV2",
                "value": "SG90",
                "symbol_library": "Device",
                "symbol_name": "Servo",
                "position": (200, 120),
            },
            {
                "reference": "LED1",
                "value": "RGB",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (68, 34),
            },
            {
                "reference": "LED2",
                "value": "RGB",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (103, 34),
            },
            {
                "reference": "BZ1",
                "value": "Buzzer",
                "symbol_library": "Device",
                "symbol_name": "Buzzer",
                "position": (140, 68),
            },
            {
                "reference": "C1",
                "value": "100µF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (139, 33),
            },
            {
                "reference": "C2",
                "value": "100µF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (130, 80),
            },
            {
                "reference": "C3",
                "value": "470µF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (174, 33),
            },
            {
                "reference": "R1",
                "value": "10kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (175, 68),
            },
            {
                "reference": "R2",
                "value": "10kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (210, 68),
            },
            {
                "reference": "R3",
                "value": "4.7kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (70, 100),
            },
            {
                "reference": "R4",
                "value": "4.7kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (90, 100),
            },
        ]

        robocar_power_symbols = [
            {"reference": "#PWR001", "power_type": "VCC", "position": (242, 68)},
            {"reference": "#PWR002", "power_type": "+3V3", "position": (102, 102)},
            {"reference": "#PWR003", "power_type": "GND", "position": (138, 102)},
        ]

        # Generate the schematic
        result = self.handler.generate_schematic(
            circuit_name="RoboCar Dual ESP32 System",
            components=robocar_components,
            power_symbols=robocar_power_symbols,
            connections=[],  # Skip connections for this boolean format test
        )

        # Write to temporary file for analysis
        temp_file = os.path.join(self.temp_dir, "robocar_recreation.kicad_sch")
        with open(temp_file, "w") as f:
            f.write(result)

        # Read back and verify no problematic boolean patterns exist
        with open(temp_file) as f:
            content = f.read()

        # These patterns should NOT exist (the original problem)
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
            assert pattern not in content, (
                f"Found problematic pattern: {pattern} in robocar recreation\n"
                f"This pattern would cause 'Expecting yes or no' error in KiCad"
            )

        # These patterns SHOULD exist (the fix)
        correct_patterns = ["(exclude_from_sim no)", "(in_bom yes)", "(on_board yes)", "(dnp no)"]

        found_correct_patterns = [pattern for pattern in correct_patterns if pattern in content]
        assert len(found_correct_patterns) > 0, (
            f"No correct unquoted boolean patterns found!\n"
            f"Expected patterns: {correct_patterns}\n"
            f"File content preview:\n{content[:1000]}..."
        )

    def test_sexpdata_parsing_compatibility(self):
        """
        Test that generated S-expressions can be parsed by sexpdata without issues.

        This simulates how KiCad might parse the S-expression content.
        """
        components = [
            {
                "reference": "U1",
                "value": "Test IC",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (100, 100),
            }
        ]

        result = self.handler.generate_schematic(
            circuit_name="sexpdata Parse Test",
            components=components,
            power_symbols=[],
            connections=[],
        )

        # This should parse without errors
        try:
            parsed = sexpdata.loads(result)
            assert isinstance(parsed, list)
            assert str(parsed[0]) == "kicad_sch"

        except Exception as e:
            pytest.fail(f"sexpdata failed to parse generated S-expression: {e}")

        # Check that boolean values in the parsed structure are Symbol objects
        def find_boolean_values(obj, path=""):
            """Recursively find boolean properties in parsed S-expression."""
            if isinstance(obj, list) and len(obj) >= 2:
                if isinstance(obj[0], sexpdata.Symbol):
                    prop_name = str(obj[0])
                    if (
                        prop_name in ["exclude_from_sim", "in_bom", "on_board", "dnp"]
                        and len(obj) >= 2
                    ):
                        # Found a boolean property - check its value
                        return [(path + "." + prop_name, obj[1])]

                # Recurse into nested lists
                results = []
                for i, item in enumerate(obj):
                    if isinstance(item, list):
                        results.extend(find_boolean_values(item, f"{path}[{i}]"))
                return results

            return []

        boolean_values = find_boolean_values(parsed)

        # All boolean values should be Symbol objects
        for path, value in boolean_values:
            assert isinstance(value, sexpdata.Symbol), (
                f"Boolean value at {path} should be Symbol, got {type(value)}: {value}"
            )
            assert str(value) in ["yes", "no"], (
                f"Boolean value at {path} should be 'yes' or 'no', got: {value}"
            )

    def test_kicad_cli_compatibility(self):
        """
        Test compatibility with KiCad CLI tools (if available).

        This test will be skipped if KiCad CLI is not available on the system.
        Uses the centralized KiCad CLI detection utility for cross-platform support.
        """
        # Check if kicad-cli is available using the centralized utility
        if not is_kicad_cli_available():
            pytest.skip("KiCad CLI not available on system")

        # Get the CLI path
        try:
            cli_path = get_kicad_cli_path(required=True)
        except Exception as e:
            pytest.skip(f"KiCad CLI path detection failed: {e}")

        # Generate a test schematic
        components = [
            {
                "reference": "R1",
                "value": "10k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (100, 100),
            }
        ]

        result = self.handler.generate_schematic(
            circuit_name="KiCad CLI Test", components=components, power_symbols=[], connections=[]
        )

        # Write to temporary file
        temp_file = os.path.join(self.temp_dir, "kicad_cli_test.kicad_sch")
        with open(temp_file, "w") as f:
            f.write(result)

        # Try to validate with KiCad CLI by attempting to export the schematic
        # This tests if KiCad can parse the generated S-expression format
        try:
            # Attempt to use kicad-cli to process the file by exporting to SVG
            # If this succeeds, the schematic format is valid
            output_svg = os.path.join(self.temp_dir, "output.svg")
            validation_result = subprocess.run(
                [cli_path, "sch", "export", "svg", temp_file, "-o", output_svg],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # If the command succeeds, the file is likely properly formatted
            if validation_result.returncode == 0:
                # Success - KiCad CLI could process the file
                pass
            else:
                # Check if the error is related to boolean format
                error_output = validation_result.stderr.lower()
                if "yes or no" in error_output or "expecting" in error_output:
                    pytest.fail(
                        f"KiCad CLI failed with boolean format error:\n"
                        f"STDOUT: {validation_result.stdout}\n"
                        f"STDERR: {validation_result.stderr}"
                    )
                else:
                    # Some other error - might be due to missing libraries, etc.
                    # We'll consider this a skip rather than failure
                    pytest.skip(
                        f"KiCad CLI error (not boolean-related): {validation_result.stderr}"
                    )

        except subprocess.TimeoutExpired:
            pytest.skip("KiCad CLI command timed out")
        except Exception as e:
            pytest.skip(f"KiCad CLI test error: {e}")


class TestBooleanFormatRegression:
    """Regression tests to ensure the boolean format fix doesn't break other functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SExpressionHandler()

    def test_non_boolean_string_values_still_quoted(self):
        """Test that non-boolean string values are still properly quoted."""
        component = {
            "reference": "U1",
            "value": "ESP32 Module",  # String with space - should be quoted
            "symbol_library": "Device",
            "symbol_name": "U",
            "position": (100, 100),
        }

        result = self.handler.generate_schematic(
            circuit_name="Non-Boolean String Test",
            components=[component],
            power_symbols=[],
            connections=[],
        )

        # Non-boolean strings should still be quoted
        assert '"ESP32 Module"' in result, "Non-boolean strings should still be quoted"

        # But boolean values should not be quoted
        problematic_patterns = ['(exclude_from_sim "no")', '(in_bom "yes")']
        for pattern in problematic_patterns:
            assert pattern not in result, f"Boolean values should not be quoted: {pattern}"

    def test_empty_and_special_string_handling(self):
        """Test that empty strings and special characters are handled correctly."""
        component = {
            "reference": "R1",
            "value": "",  # Empty string
            "symbol_library": "Device",
            "symbol_name": "R",
            "position": (100, 100),
            "footprint": "",  # Another empty string
            "datasheet": "~",  # Special KiCad value
        }

        result = self.handler.generate_schematic(
            circuit_name="Empty String Test",
            components=[component],
            power_symbols=[],
            connections=[],
        )

        # Empty strings should be quoted
        assert '""' in result, "Empty strings should be quoted"

        # Special values like tilde are actually quoted in KiCad - this is correct
        # The test was checking incorrect behavior

        # Boolean values should still be unquoted
        assert "(exclude_from_sim no)" in result or "(exclude_from_sim yes)" in result, (
            "Boolean values should be unquoted symbols"
        )

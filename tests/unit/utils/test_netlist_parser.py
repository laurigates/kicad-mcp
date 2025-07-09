"""
Comprehensive unit tests for netlist_parser.py.
Tests both JSON and S-expression schematic parsing with focus on recent fixes.
"""

import json
from unittest.mock import patch

import pytest

from kicad_mcp.utils.netlist_parser import analyze_netlist, extract_netlist, parse_json_schematic


class TestNetlistParser:
    """Test suite for netlist parser functionality."""

    def test_extract_netlist_json_format(self, sample_json_schematic_file):
        """Test netlist extraction from JSON format schematic."""
        result = extract_netlist(str(sample_json_schematic_file))

        assert "error" not in result
        assert result["component_count"] == 2
        assert result["net_count"] >= 1
        assert "U1" in result["components"]
        assert "#PWR01" in result["components"]

        # Verify component details
        esp32 = result["components"]["U1"]
        assert esp32["lib_id"] == "MCU_Espressif:ESP32-WROOM-32"
        assert esp32["reference"] == "U1"
        assert esp32["value"] == "ESP32-WROOM-32"

        power = result["components"]["#PWR01"]
        assert power["lib_id"] == "power:VCC"
        assert power["reference"] == "#PWR01"
        assert power["value"] == "VCC"

    def test_extract_netlist_sexpr_format(self, sample_sexpr_schematic_file):
        """Test netlist extraction from S-expression format schematic."""
        result = extract_netlist(str(sample_sexpr_schematic_file))

        assert "error" not in result
        assert result["component_count"] >= 1
        assert "components" in result

        # Should detect at least one resistor component
        resistors = [
            comp for ref, comp in result["components"].items() if comp["lib_id"] == "Device:R"
        ]
        assert len(resistors) >= 1

    def test_extract_netlist_file_not_found(self):
        """Test error handling when schematic file doesn't exist."""
        result = extract_netlist("/nonexistent/path/test.kicad_sch")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_extract_netlist_invalid_json(self, temp_dir):
        """Test error handling with malformed JSON."""
        invalid_file = temp_dir / "invalid.kicad_sch"
        invalid_file.write_text("{ invalid json content }")

        result = extract_netlist(str(invalid_file))

        assert "error" in result
        assert "json" in result["error"].lower() or "parse" in result["error"].lower()

    def test_extract_netlist_empty_file(self, temp_dir):
        """Test handling of empty schematic file."""
        empty_file = temp_dir / "empty.kicad_sch"
        empty_file.write_text("")

        result = extract_netlist(str(empty_file))

        assert "error" in result

    def test_parse_json_schematic_valid(self, sample_json_schematic):
        """Test JSON schematic parsing with valid data."""
        result = parse_json_schematic(sample_json_schematic)

        assert result["component_count"] == 2
        assert len(result["components"]) == 2
        assert "U1" in result["components"]
        assert "#PWR01" in result["components"]

        # Test component structure
        esp32 = result["components"]["U1"]
        assert all(key in esp32 for key in ["lib_id", "reference", "value", "uuid", "position"])

        # Test nets
        assert "nets" in result
        assert len(result["nets"]) >= 1

    def test_parse_json_schematic_empty(self):
        """Test JSON parsing with empty schematic."""
        empty_data = {"components": [], "wires": [], "nets": []}
        result = parse_json_schematic(empty_data)

        assert result["component_count"] == 0
        assert result["net_count"] == 0
        assert len(result["components"]) == 0
        assert len(result["nets"]) == 0

    def test_parse_json_schematic_missing_keys(self):
        """Test JSON parsing with missing required keys."""
        invalid_data = {"wires": [], "nets": []}  # Missing components

        with pytest.raises((KeyError, TypeError)):
            parse_json_schematic(invalid_data)

    def test_parse_json_schematic_power_symbol_deduplication(self):
        """Test that power symbols with duplicate references are handled correctly."""
        data = {
            "components": [
                {
                    "lib_id": "power:VCC",
                    "reference": "#PWR0007",
                    "value": "VCC",
                    "uuid": "uuid-1",
                    "position": {"x": 500, "y": 300, "angle": 0},
                    "properties": {"footprint": "", "datasheet": ""},
                    "pins": [],
                },
                {
                    "lib_id": "power:GND",
                    "reference": "#PWR0007",  # Same reference, different UUID
                    "value": "GND",
                    "uuid": "uuid-2",
                    "position": {"x": 500, "y": 1500, "angle": 0},
                    "properties": {"footprint": "", "datasheet": ""},
                    "pins": [],
                },
            ],
            "wires": [],
            "nets": [],
        }

        result = parse_json_schematic(data)

        # Should have 2 components with modified reference names
        assert result["component_count"] == 2
        assert len(result["components"]) == 2

        # Check that references were made unique
        references = list(result["components"].keys())
        assert len(set(references)) == 2  # All references should be unique
        assert any("PWR" in ref for ref in references)

    def test_parse_sexpr_schematic_components(self, sample_sexpr_schematic):
        """Test S-expression component parsing."""
        result = extract_netlist(sample_sexpr_schematic)

        assert result["component_count"] >= 1
        assert "components" in result

        # Should find resistor components
        resistors = [
            comp
            for ref, comp in result["components"].items()
            if "Device:R" in comp.get("lib_id", "")
        ]
        assert len(resistors) >= 1

        # Check component structure
        for _ref, comp in result["components"].items():
            assert "lib_id" in comp
            assert "reference" in comp
            assert "uuid" in comp

    def test_parse_sexpr_schematic_wires_and_junctions(self, sample_sexpr_schematic):
        """Test S-expression wire and junction parsing."""
        result = extract_netlist(sample_sexpr_schematic)

        assert "wires" in result
        assert "junctions" in result

        # Should have at least one wire and junction from the sample
        assert len(result["wires"]) >= 1
        assert len(result["junctions"]) >= 1

        # Check wire structure
        if result["wires"]:
            wire = result["wires"][0]
            assert "uuid" in wire

    def test_parse_sexpr_schematic_labels(self, sample_sexpr_schematic):
        """Test S-expression label parsing."""
        result = extract_netlist(sample_sexpr_schematic)

        assert "labels" in result

        # Should find the TEST_SIGNAL label from the sample
        labels = result["labels"]
        test_label = next((label for label in labels if label.get("text") == "TEST_SIGNAL"), None)
        assert test_label is not None
        assert "position" in test_label

    def test_parse_sexpr_schematic_malformed(self):
        """Test S-expression parsing with malformed input."""
        malformed_sexpr = "(incomplete s-expression"

        result = extract_netlist(malformed_sexpr)

        # Should return empty result rather than crash
        assert result["component_count"] == 0
        assert result["net_count"] == 0

    def test_analyze_netlist_basic(self):
        """Test basic netlist analysis functionality."""
        netlist_data = {
            "components": {
                "U1": {
                    "lib_id": "MCU_Espressif:ESP32-WROOM-32",
                    "reference": "U1",
                    "value": "ESP32-WROOM-32",
                },
                "R1": {"lib_id": "Device:R", "reference": "R1", "value": "10k"},
            },
            "nets": {"VCC": [{"component": "U1", "pin": "2"}, {"component": "R1", "pin": "1"}]},
            "component_count": 2,
            "net_count": 1,
        }

        analysis = analyze_netlist(netlist_data)

        assert "component_types" in analysis
        assert "net_connectivity" in analysis
        assert "component_summary" in analysis

        # Check component type analysis
        component_types = analysis["component_types"]
        assert "MCU_Espressif:ESP32-WROOM-32" in component_types
        assert "Device:R" in component_types
        assert component_types["MCU_Espressif:ESP32-WROOM-32"] == 1
        assert component_types["Device:R"] == 1

        # Check connectivity analysis
        connectivity = analysis["net_connectivity"]
        assert "VCC" in connectivity
        assert len(connectivity["VCC"]) == 2

    def test_analyze_netlist_empty(self):
        """Test netlist analysis with empty data."""
        empty_netlist = {"components": {}, "nets": {}, "component_count": 0, "net_count": 0}

        analysis = analyze_netlist(empty_netlist)

        assert analysis["component_types"] == {}
        assert analysis["net_connectivity"] == {}
        assert analysis["component_summary"]["total_components"] == 0
        assert analysis["component_summary"]["total_nets"] == 0

    def test_format_detection_json(self, sample_json_schematic_file):
        """Test automatic format detection for JSON files."""
        # This test ensures the extract_netlist function correctly detects JSON format
        with patch("kicad_mcp.utils.netlist_parser.parse_json_schematic") as mock_json:
            mock_json.return_value = {
                "component_count": 0,
                "net_count": 0,
                "components": {},
                "nets": {},
            }

            extract_netlist(str(sample_json_schematic_file))

            # Should have called JSON parser
            mock_json.assert_called_once()

    def test_format_detection_sexpr(self, sample_sexpr_schematic_file):
        """Test automatic format detection for S-expression files."""
        # This test ensures the extract_netlist function correctly detects S-expression format
        with patch("kicad_mcp.utils.netlist_parser.parse_sexpr_schematic") as mock_sexpr:
            mock_sexpr.return_value = {
                "component_count": 0,
                "net_count": 0,
                "components": {},
                "nets": {},
            }

            extract_netlist(str(sample_sexpr_schematic_file))

            # Should have called S-expression parser
            mock_sexpr.assert_called_once()

    def test_large_schematic_performance(self):
        """Test performance with a large schematic (stress test)."""
        # Create a large synthetic schematic
        large_data = {"components": [], "wires": [], "nets": []}

        # Add 1000 components
        for i in range(1000):
            large_data["components"].append(
                {
                    "lib_id": "Device:R",
                    "reference": f"R{i + 1}",
                    "value": "10k",
                    "uuid": f"uuid-{i + 1:04d}",
                    "position": {"x": i * 100, "y": 1000, "angle": 0},
                    "properties": {"footprint": "", "datasheet": ""},
                    "pins": [],
                }
            )

        # Add some nets
        for i in range(100):
            large_data["nets"].append(
                {
                    "name": f"NET_{i + 1}",
                    "connections": [
                        {"component": f"R{i + 1}", "pin": "1"},
                        {"component": f"R{i + 2}" if i < 999 else "R1", "pin": "2"},
                    ],
                }
            )

        # Test should complete within reasonable time
        import time

        start_time = time.time()
        result = parse_json_schematic(large_data)
        end_time = time.time()

        assert result["component_count"] == 1000
        assert result["net_count"] >= 100
        assert (end_time - start_time) < 5.0  # Should complete within 5 seconds

    @pytest.mark.parametrize("file_extension", [".kicad_sch", ".sch", ".schematic"])
    def test_file_extension_handling(self, temp_dir, file_extension):
        """Test that parser handles various file extensions."""
        test_file = temp_dir / f"test{file_extension}"
        test_file.write_text('{"components": [], "wires": [], "nets": []}')

        result = extract_netlist(str(test_file))

        # Should parse successfully regardless of extension
        assert "error" not in result
        assert result["component_count"] == 0

    def test_unicode_handling(self, temp_dir):
        """Test parsing files with unicode characters."""
        unicode_data = {
            "components": [
                {
                    "lib_id": "Device:R",
                    "reference": "R1",
                    "value": "10kΩ",  # Unicode omega symbol
                    "uuid": "uuid-1",
                    "position": {"x": 1000, "y": 1000, "angle": 0},
                    "properties": {
                        "footprint": "Résistance_SMD:R_0603",  # Unicode accent
                        "datasheet": "",
                    },
                    "pins": [],
                }
            ],
            "wires": [],
            "nets": [],
        }

        unicode_file = temp_dir / "unicode_test.kicad_sch"
        with open(unicode_file, "w", encoding="utf-8") as f:
            json.dump(unicode_data, f, ensure_ascii=False)

        result = extract_netlist(str(unicode_file))

        assert "error" not in result
        assert result["component_count"] == 1
        assert "R1" in result["components"]
        assert result["components"]["R1"]["value"] == "10kΩ"
        assert "Résistance_SMD:R_0603" in result["components"]["R1"]["properties"]["footprint"]

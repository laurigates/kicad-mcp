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

        # Should detect at least one ESP32 component
        esp32_components = [
            comp
            for ref, comp in result["components"].items()
            if comp["lib_id"] == "MCU_Espressif:ESP32-WROOM-32"
        ]
        assert len(esp32_components) >= 1

    def test_extract_netlist_file_not_found(self):
        """Test error handling when schematic file doesn't exist."""
        result = extract_netlist("/nonexistent/path/test.kicad_sch")

        assert "error" in result
        assert "not found" in result["error"].lower() or "no such file" in result["error"].lower()

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

    def test_parse_sexpr_schematic_components(self, sample_sexpr_schematic_file):
        """Test S-expression component parsing."""
        result = extract_netlist(str(sample_sexpr_schematic_file))

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

    def test_parse_sexpr_schematic_wires_and_junctions(self, sample_sexpr_schematic_file):
        """Test S-expression wire and junction parsing."""
        result = extract_netlist(str(sample_sexpr_schematic_file))

        assert "wires" in result
        assert "junctions" in result

        # Should have at least one wire and junction from the sample
        assert len(result["wires"]) >= 1
        assert len(result["junctions"]) >= 1

        # Check wire structure
        if result["wires"]:
            wire = result["wires"][0]
            assert "uuid" in wire

    def test_parse_sexpr_schematic_labels(self, sample_sexpr_schematic_file):
        """Test S-expression label parsing."""
        result = extract_netlist(str(sample_sexpr_schematic_file))

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
        with patch("kicad_mcp.utils.netlist_parser.SchematicParser") as mock_parser:
            # Mock the parser instance and its parse method
            mock_instance = mock_parser.return_value
            mock_instance.parse.return_value = {
                "component_count": 0,
                "net_count": 0,
                "components": {},
                "nets": {},
            }

            extract_netlist(str(sample_sexpr_schematic_file))

            # Should have created a SchematicParser instance
            mock_parser.assert_called_once()
            mock_instance.parse.assert_called_once()

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


class TestBuildNetlist:
    """Tests for wire connectivity tracing in _build_netlist()."""

    @pytest.fixture
    def real_sexpr_fixture(self):
        """Path to the real S-expression fixture with lib_symbols and wires."""
        import pathlib

        return str(
            pathlib.Path(__file__).parent.parent.parent
            / "fixtures"
            / "sample_schematics"
            / "sexpr_schematic.kicad_sch"
        )

    def test_sexpr_netlist_wire_connectivity(self, real_sexpr_fixture):
        """R1.pin2 and R2.pin1 should be in the same net via wire chain."""
        result = extract_netlist(real_sexpr_fixture)

        assert "error" not in result
        nets = result["nets"]

        # Find which net contains R1 pin 2
        r1_pin2_net = None
        r2_pin1_net = None
        for net_name, connections in nets.items():
            for conn in connections:
                if conn["component"] == "R1" and conn["pin"] == "2":
                    r1_pin2_net = net_name
                if conn["component"] == "R2" and conn["pin"] == "1":
                    r2_pin1_net = net_name

        assert r1_pin2_net is not None, "R1.pin2 should be assigned to a net"
        assert r2_pin1_net is not None, "R2.pin1 should be assigned to a net"
        assert r1_pin2_net == r2_pin1_net, (
            f"R1.pin2 ({r1_pin2_net}) and R2.pin1 ({r2_pin1_net}) should be in same net"
        )

    def test_pin_position_from_lib_symbols(self, real_sexpr_fixture):
        """Verify pin positions are correctly resolved from lib_symbols section."""
        from kicad_mcp.utils.netlist_parser import SchematicParser

        parser = SchematicParser(real_sexpr_fixture)
        parser._extract_components()
        parser._extract_lib_symbol_pins()
        resolved = parser._resolve_pin_positions()

        # R1 at (63.5, 87.63) angle 0, lib_symbols pin 2 at local (0, -3.81)
        # absolute: (63.5, 87.63 - (-3.81)) = (63.5, 91.44)
        r1_pin2 = next((p for p in resolved if p["component"] == "R1" and p["pin"] == "2"), None)
        assert r1_pin2 is not None
        assert abs(r1_pin2["x"] - 63.5) < 0.01
        assert abs(r1_pin2["y"] - 91.44) < 0.01

        # R2 at (63.5, 100.33) angle 0, lib_symbols pin 1 at local (0, 3.81)
        # absolute: (63.5, 100.33 - 3.81) = (63.5, 96.52)
        r2_pin1 = next((p for p in resolved if p["component"] == "R2" and p["pin"] == "1"), None)
        assert r2_pin1 is not None
        assert abs(r2_pin1["x"] - 63.5) < 0.01
        assert abs(r2_pin1["y"] - 96.52) < 0.01

    @pytest.mark.parametrize(
        "angle,expected_pin2_offset",
        [
            (0, (0.0, 3.81)),  # pin2 local (0, -3.81) -> offset (0, +3.81)
            (90, (-3.81, 0.0)),  # 90 degree rotation
            (180, (0.0, -3.81)),  # 180 degree rotation
            (270, (3.81, 0.0)),  # 270 degree rotation
        ],
    )
    def test_rotated_component_pin_positions(self, angle, expected_pin2_offset, tmp_path):
        """Pin positions should rotate correctly with component angle."""
        from kicad_mcp.utils.netlist_parser import SchematicParser

        cx, cy = 100.0, 100.0
        schematic = f"""(kicad_sch
  (version 20241201)
  (generator eeschema)
  (uuid "test-uuid")
  (paper "A4")
  (lib_symbols
    (symbol "Device:R"
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 0 -3.81 90) (length 1.27)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
  )
  (symbol (lib_id "Device:R") (at {cx} {cy} {angle}) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "comp-uuid")
    (property "Reference" "R1" (at 0 0 0))
    (property "Value" "10k" (at 0 0 0))
    (pin "1" (uuid "pin1-uuid"))
    (pin "2" (uuid "pin2-uuid"))
  )
  (sheet_instances (path "/" (page "1")))
)"""
        sch_file = tmp_path / "rotation_test.kicad_sch"
        sch_file.write_text(schematic)

        parser = SchematicParser(str(sch_file))
        parser._extract_components()
        parser._extract_lib_symbol_pins()
        resolved = parser._resolve_pin_positions()

        r1_pin2 = next((p for p in resolved if p["component"] == "R1" and p["pin"] == "2"), None)
        assert r1_pin2 is not None
        expected_x = cx + expected_pin2_offset[0]
        expected_y = cy + expected_pin2_offset[1]
        assert abs(r1_pin2["x"] - expected_x) < 0.02, (
            f"angle={angle}: expected x={expected_x}, got {r1_pin2['x']}"
        )
        assert abs(r1_pin2["y"] - expected_y) < 0.02, (
            f"angle={angle}: expected y={expected_y}, got {r1_pin2['y']}"
        )

    def test_backward_compatible_output_format(self, real_sexpr_fixture):
        """Output format should preserve all existing keys."""
        result = extract_netlist(real_sexpr_fixture)

        assert "error" not in result
        assert "components" in result
        assert "nets" in result
        assert "labels" in result
        assert "wires" in result
        assert "junctions" in result
        assert "power_symbols" in result
        assert "component_count" in result
        assert "net_count" in result

        # Components with lib_id should have expected fields
        components_with_lib_id = [c for c in result["components"].values() if "lib_id" in c]
        assert len(components_with_lib_id) >= 2  # R1 and R2
        for comp in components_with_lib_id:
            assert "reference" in comp
            assert "position" in comp

    def test_large_schematic_performance(self, tmp_path):
        """Netlist building should handle 200+ components efficiently."""
        import time

        components = []
        wires = []
        for i in range(200):
            y_pos = i * 10.0
            components.append(
                f'  (symbol (lib_id "Device:R") (at 100 {y_pos} 0) (unit 1)\n'
                f"    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n"
                f'    (uuid "comp-{i}")\n'
                f'    (property "Reference" "R{i + 1}" (at 0 0 0))\n'
                f'    (property "Value" "10k" (at 0 0 0))\n'
                f'    (pin "1" (uuid "pin1-{i}"))\n'
                f'    (pin "2" (uuid "pin2-{i}"))\n'
                f"  )"
            )
            # Chain each component to the next via wire
            if i < 199:
                wire_y_start = y_pos + 3.81  # pin 2 of current
                wire_y_end = (i + 1) * 10.0 - 3.81  # pin 1 of next
                wires.append(
                    f"  (wire (pts (xy 100 {wire_y_start}) (xy 100 {wire_y_end}))"
                    f' (stroke (width 0) (type default)) (uuid "wire-{i}"))'
                )

        schematic = (
            "(kicad_sch\n"
            "  (version 20241201)\n"
            "  (generator eeschema)\n"
            '  (uuid "perf-test-uuid")\n'
            '  (paper "A4")\n'
            "  (lib_symbols\n"
            '    (symbol "Device:R"\n'
            '      (symbol "R_1_1"\n'
            "        (pin passive line (at 0 3.81 270) (length 1.27)\n"
            '          (name "~" (effects (font (size 1.27 1.27))))\n'
            '          (number "1" (effects (font (size 1.27 1.27))))\n'
            "        )\n"
            "        (pin passive line (at 0 -3.81 90) (length 1.27)\n"
            '          (name "~" (effects (font (size 1.27 1.27))))\n'
            '          (number "2" (effects (font (size 1.27 1.27))))\n'
            "        )\n"
            "      )\n"
            "    )\n"
            "  )\n" + "\n".join(components) + "\n" + "\n".join(wires) + "\n"
            '  (sheet_instances (path "/" (page "1")))\n'
            ")"
        )

        sch_file = tmp_path / "large_perf_test.kicad_sch"
        sch_file.write_text(schematic)

        start = time.monotonic()
        result = extract_netlist(str(sch_file))
        elapsed = time.monotonic() - start

        assert "error" not in result
        assert result["component_count"] == 200
        assert elapsed < 2.0, f"Netlist building took {elapsed:.2f}s (limit: 2s)"

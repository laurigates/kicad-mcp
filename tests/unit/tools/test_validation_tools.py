"""
Tests for validation tools.
"""

import json
import os
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from kicad_mcp.tools.validation_tools import (
    _extract_components_from_json,
    _extract_components_from_sexpr,
    _get_component_type_from_lib_id,
    generate_validation_report,
    validate_project_boundaries,
)


class TestValidationTools:
    """Test cases for validation tools."""

    @pytest.fixture
    def mock_project_files(self):
        """Mock project files structure."""
        return {"schematic": "/path/to/test.kicad_sch", "project": "/path/to/test.kicad_pro"}

    @pytest.fixture
    def sample_json_schematic(self):
        """Sample JSON schematic data."""
        return {
            "symbol": [
                {
                    "lib_id": "Device:R",
                    "at": [500, 500, 0],  # 50mm, 50mm in internal units
                    "property": [
                        {"name": "Reference", "value": "R1"},
                        {"name": "Value", "value": "10k"},
                    ],
                },
                {
                    "lib_id": "Device:C",
                    "at": [3500, 2500, 0],  # 350mm, 250mm - out of bounds
                    "property": [
                        {"name": "Reference", "value": "C1"},
                        {"name": "Value", "value": "100nF"},
                    ],
                },
            ]
        }

    @pytest.fixture
    def sample_sexpr_schematic(self):
        """Sample S-expression schematic content."""
        return """(kicad_sch (version 20241201) (generator eeschema)
            (symbol (lib_id "Device:R") (at 50.0 50.0 0) (uuid "abc123")
                (property "Reference" "R1" (at 50.0 48.0 0))
                (property "Value" "10k" (at 50.0 52.0 0))
            )
            (symbol (lib_id "Device:C") (at 350.0 250.0 0) (uuid "def456")
                (property "Reference" "C1" (at 350.0 248.0 0))
                (property "Value" "100nF" (at 350.0 252.0 0))
            )
        )"""

    @pytest.mark.asyncio
    async def test_validate_project_boundaries_json_format(
        self, mock_project_files, sample_json_schematic
    ):
        """Test validation of JSON format schematic."""
        with (
            patch(
                "kicad_mcp.tools.validation_tools.get_project_files",
                return_value=mock_project_files,
            ),
            patch("builtins.open", mock_open(read_data=json.dumps(sample_json_schematic))),
        ):
            ctx = Mock()
            ctx.info = AsyncMock()
            ctx.report_progress = AsyncMock()

            result = await validate_project_boundaries("/path/to/test.kicad_pro", ctx)

            assert result["success"] is False
            assert result["total_components"] == 2
            assert result["out_of_bounds_count"] == 1
            assert "C1" in result["corrected_positions"]
            assert result["has_errors"] is True

            # Check that info was called with report
            ctx.info.assert_called()
            ctx.report_progress.assert_called()

    @pytest.mark.asyncio
    async def test_validate_project_boundaries_sexpr_format(
        self, mock_project_files, sample_sexpr_schematic
    ):
        """Test validation of S-expression format schematic."""
        with (
            patch(
                "kicad_mcp.tools.validation_tools.get_project_files",
                return_value=mock_project_files,
            ),
            patch("builtins.open", mock_open(read_data=sample_sexpr_schematic)),
        ):
            ctx = Mock()
            ctx.info = AsyncMock()
            ctx.report_progress = AsyncMock()

            result = await validate_project_boundaries("/path/to/test.kicad_pro", ctx)

            assert result["success"] is False
            assert result["total_components"] == 2
            assert result["out_of_bounds_count"] == 1
            assert "C1" in result["corrected_positions"]

    @pytest.mark.asyncio
    async def test_validate_project_boundaries_no_schematic(self):
        """Test validation when no schematic file exists."""
        with patch("kicad_mcp.tools.validation_tools.get_project_files", return_value={}):
            result = await validate_project_boundaries("/path/to/test.kicad_pro")

            assert result["success"] is False
            assert "No schematic file found" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_project_boundaries_invalid_format(self, mock_project_files):
        """Test validation with invalid file format."""
        with (
            patch(
                "kicad_mcp.tools.validation_tools.get_project_files",
                return_value=mock_project_files,
            ),
            patch("builtins.open", mock_open(read_data="invalid content")),
        ):
            result = await validate_project_boundaries("/path/to/test.kicad_pro")

            assert result["success"] is False
            assert "neither valid S-expression nor JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_validation_report_success(
        self, mock_project_files, sample_json_schematic, tmp_path
    ):
        """Test successful validation report generation."""
        # Use a more targeted mock that only mocks reading the schematic file
        real_open = open

        def mock_open_func(filename, mode="r", *args, **kwargs):
            if "test.kicad_sch" in filename and "r" in mode:
                return mock_open(read_data=json.dumps(sample_json_schematic))()
            else:
                # Use real open for other files (like writing the report)
                return real_open(filename, mode, *args, **kwargs)

        with (
            patch(
                "kicad_mcp.tools.validation_tools.get_project_files",
                return_value=mock_project_files,
            ),
            patch("builtins.open", side_effect=mock_open_func),
        ):
            ctx = Mock()
            ctx.info = AsyncMock()
            ctx.report_progress = AsyncMock()

            output_path = str(tmp_path / "report.json")
            result = await generate_validation_report("/path/to/test.kicad_pro", output_path, ctx)

            assert result["success"] is True
            assert result["report_path"] == output_path
            assert result["summary"]["total_components"] == 2
            assert result["summary"]["out_of_bounds_count"] == 1

            # Check report file was created
            assert os.path.exists(output_path)

            # Check report content
            with open(output_path) as f:
                report_data = json.load(f)

            assert report_data["project_path"] == "/path/to/test.kicad_pro"
            assert "validation_timestamp" in report_data
            assert report_data["summary"]["total_components"] == 2
            assert len(report_data["issues"]) == 2

    @pytest.mark.asyncio
    async def test_generate_validation_report_default_path(
        self, mock_project_files, sample_json_schematic, tmp_path
    ):
        """Test validation report generation with default output path."""
        project_path = str(tmp_path / "test_project.kicad_pro")

        with (
            patch(
                "kicad_mcp.tools.validation_tools.get_project_files",
                return_value=mock_project_files,
            ),
            patch("builtins.open", mock_open(read_data=json.dumps(sample_json_schematic))),
        ):
            result = await generate_validation_report(project_path)

            assert result["success"] is True
            expected_path = str(tmp_path / "test_project_validation_report.json")
            assert result["report_path"] == expected_path

    def test_extract_components_from_json_valid(self, sample_json_schematic):
        """Test extracting components from valid JSON schematic."""
        components = _extract_components_from_json(sample_json_schematic)

        assert len(components) == 2

        # Check first component
        assert components[0]["reference"] == "R1"
        assert components[0]["position"] == (50.0, 50.0)
        assert components[0]["component_type"] == "resistor"
        assert components[0]["lib_id"] == "Device:R"

        # Check second component
        assert components[1]["reference"] == "C1"
        assert components[1]["position"] == (350.0, 250.0)
        assert components[1]["component_type"] == "capacitor"
        assert components[1]["lib_id"] == "Device:C"

    def test_extract_components_from_json_empty(self):
        """Test extracting components from empty JSON schematic."""
        components = _extract_components_from_json({})

        assert len(components) == 0

    def test_extract_components_from_json_no_properties(self):
        """Test extracting components from JSON with no properties."""
        schematic_data = {
            "symbol": [
                {
                    "lib_id": "Device:R",
                    "at": [500, 500, 0],
                    # No properties
                }
            ]
        }

        components = _extract_components_from_json(schematic_data)

        assert len(components) == 1
        assert components[0]["reference"] == "Unknown"
        assert components[0]["position"] == (50.0, 50.0)
        assert components[0]["component_type"] == "resistor"

    def test_extract_components_from_sexpr_valid(self, sample_sexpr_schematic):
        """Test extracting components from valid S-expression schematic."""
        components = _extract_components_from_sexpr(sample_sexpr_schematic)

        assert len(components) == 2

        # Check first component
        assert components[0]["reference"] == "R1"
        assert components[0]["position"] == (50.0, 50.0)
        assert components[0]["component_type"] == "resistor"
        assert components[0]["lib_id"] == "Device:R"

        # Check second component
        assert components[1]["reference"] == "C1"
        assert components[1]["position"] == (350.0, 250.0)
        assert components[1]["component_type"] == "capacitor"
        assert components[1]["lib_id"] == "Device:C"

    def test_extract_components_from_sexpr_empty(self):
        """Test extracting components from empty S-expression schematic."""
        components = _extract_components_from_sexpr("(kicad_sch)")

        assert len(components) == 0

    def test_get_component_type_from_lib_id_resistor(self):
        """Test component type detection for resistors."""
        assert _get_component_type_from_lib_id("Device:R") == "resistor"
        assert _get_component_type_from_lib_id("Device:Resistor") == "resistor"
        assert _get_component_type_from_lib_id("Custom:R_1206") == "resistor"

    def test_get_component_type_from_lib_id_capacitor(self):
        """Test component type detection for capacitors."""
        assert _get_component_type_from_lib_id("Device:C") == "capacitor"
        assert _get_component_type_from_lib_id("Device:Capacitor") == "capacitor"
        assert _get_component_type_from_lib_id("Custom:C_0805") == "capacitor"

    def test_get_component_type_from_lib_id_inductor(self):
        """Test component type detection for inductors."""
        assert _get_component_type_from_lib_id("Device:L") == "inductor"
        assert _get_component_type_from_lib_id("Device:Inductor") == "inductor"

    def test_get_component_type_from_lib_id_led(self):
        """Test component type detection for LEDs."""
        assert _get_component_type_from_lib_id("Device:LED") == "led"
        assert _get_component_type_from_lib_id("Custom:LED_5mm") == "led"

    def test_get_component_type_from_lib_id_diode(self):
        """Test component type detection for diodes."""
        assert _get_component_type_from_lib_id("Device:D") == "diode"
        assert _get_component_type_from_lib_id("Device:Diode") == "diode"

    def test_get_component_type_from_lib_id_transistor(self):
        """Test component type detection for transistors."""
        assert _get_component_type_from_lib_id("Device:Q_NPN_CBE") == "transistor"
        assert _get_component_type_from_lib_id("Device:Q_PNP_CBE") == "transistor"
        assert _get_component_type_from_lib_id("Custom:Transistor_NPN") == "transistor"

    def test_get_component_type_from_lib_id_power(self):
        """Test component type detection for power symbols."""
        assert _get_component_type_from_lib_id("power:VCC") == "power"
        assert _get_component_type_from_lib_id("power:GND") == "power"
        assert _get_component_type_from_lib_id("power:+5V") == "power"

    def test_get_component_type_from_lib_id_switch(self):
        """Test component type detection for switches."""
        assert _get_component_type_from_lib_id("Switch:SW_Push") == "switch"
        assert _get_component_type_from_lib_id("Custom:Switch_SPDT") == "switch"

    def test_get_component_type_from_lib_id_connector(self):
        """Test component type detection for connectors."""
        assert _get_component_type_from_lib_id("Connector:Conn_01x02") == "connector"
        assert _get_component_type_from_lib_id("Custom:Connector_USB") == "connector"

    def test_get_component_type_from_lib_id_ic(self):
        """Test component type detection for ICs."""
        assert _get_component_type_from_lib_id("Device:U") == "ic"
        assert _get_component_type_from_lib_id("MCU:ESP32") == "ic"
        assert _get_component_type_from_lib_id("Custom:IC_OpAmp") == "ic"

    def test_get_component_type_from_lib_id_default(self):
        """Test component type detection for unknown types."""
        assert _get_component_type_from_lib_id("Unknown:Component") == "default"
        assert _get_component_type_from_lib_id("Custom:Mystery") == "default"
        assert _get_component_type_from_lib_id("") == "default"


class TestValidationToolsIntegration:
    """Integration tests for validation tools."""

    @pytest.mark.asyncio
    async def test_validation_workflow_complete(self, tmp_path):
        """Test complete validation workflow from project to report."""
        # Create test project structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        project_file = project_dir / "test.kicad_pro"
        schematic_file = project_dir / "test.kicad_sch"

        # Create project file
        project_file.write_text('{"meta": {"filename": "test.kicad_pro"}}')

        # Create schematic with out-of-bounds components
        schematic_data = {
            "symbol": [
                {
                    "lib_id": "Device:R",
                    "at": [500, 500, 0],  # Valid position
                    "property": [
                        {"name": "Reference", "value": "R1"},
                        {"name": "Value", "value": "10k"},
                    ],
                },
                {
                    "lib_id": "Device:C",
                    "at": [3500, 2500, 0],  # Out of bounds
                    "property": [
                        {"name": "Reference", "value": "C1"},
                        {"name": "Value", "value": "100nF"},
                    ],
                },
            ]
        }

        schematic_file.write_text(json.dumps(schematic_data))

        # Run validation
        result = await validate_project_boundaries(str(project_file))

        assert result["success"] is False
        assert result["total_components"] == 2
        assert result["out_of_bounds_count"] == 1
        assert "C1" in result["corrected_positions"]

        # Generate report
        report_result = await generate_validation_report(str(project_file))

        assert report_result["success"] is True
        assert os.path.exists(report_result["report_path"])

        # Check report content
        with open(report_result["report_path"]) as f:
            report_data = json.load(f)

        assert report_data["summary"]["total_components"] == 2
        assert report_data["summary"]["out_of_bounds_count"] == 1
        assert len(report_data["issues"]) == 2
        assert any(issue["severity"] == "error" for issue in report_data["issues"])


if __name__ == "__main__":
    pytest.main([__file__])

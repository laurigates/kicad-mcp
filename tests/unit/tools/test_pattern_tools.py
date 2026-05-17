"""Unit tests for pattern_tools.py circuit pattern MCP wrappers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kicad_mcp.tools.pattern_tools import register_pattern_tools


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.tools[kwargs.get("name", func.__name__)] = func
            return func

        return decorator


@pytest.fixture
def mcp_with_pattern_tools():
    mcp = ToolRegistry()
    register_pattern_tools(mcp)
    return mcp


@pytest.fixture
def mock_context():
    context = Mock()
    context.info = AsyncMock()
    context.report_progress = AsyncMock()
    return context


def write_pattern_schematic(path: Path) -> Path:
    """Write a small JSON schematic with a regulator and ESP32."""
    path.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "lib_id": "Regulator_Linear:AMS1117-3.3",
                        "reference": "U1",
                        "value": "AMS1117-3.3",
                        "uuid": "11111111-1111-1111-1111-111111111111",
                        "position": {"x": 10, "y": 10, "angle": 0},
                    },
                    {
                        "lib_id": "MCU_Espressif:ESP32-WROOM-32",
                        "reference": "U2",
                        "value": "ESP32-WROOM-32",
                        "uuid": "22222222-2222-2222-2222-222222222222",
                        "position": {"x": 20, "y": 20, "angle": 0},
                    },
                ],
                "nets": [
                    {
                        "name": "VIN",
                        "connections": [
                            {"component": "U1", "pin": "3"},
                        ],
                    },
                    {
                        "name": "3V3",
                        "connections": [
                            {"component": "U1", "pin": "2"},
                            {"component": "U2", "pin": "2"},
                        ],
                    },
                ],
            }
        )
    )
    return path


class TestPatternToolRegistration:
    def test_registers_expected_tools(self, mcp_with_pattern_tools):
        tools = set(mcp_with_pattern_tools.tools)

        assert {"identify_circuit_patterns", "analyze_project_circuit_patterns"} <= tools


class TestIdentifyCircuitPatterns:
    @pytest.mark.asyncio
    async def test_identifies_patterns_with_mocked_recognizers(
        self, mcp_with_pattern_tools, mock_context, tmp_path
    ):
        schematic = tmp_path / "demo.kicad_sch"
        schematic.write_text("{}")
        identify = mcp_with_pattern_tools.tools["identify_circuit_patterns"]
        netlist = {
            "components": {"U1": {"value": "AMS1117"}, "U2": {"value": "ESP32-WROOM-32"}},
            "nets": {"3V3": [{"component": "U1", "pin": "2"}]},
            "component_count": 2,
        }

        with (
            patch("kicad_mcp.tools.pattern_tools.extract_netlist", return_value=netlist),
            patch(
                "kicad_mcp.tools.pattern_tools.identify_power_supplies",
                return_value=[{"type": "linear_regulator", "main_component": "U1"}],
            ) as power_mock,
            patch("kicad_mcp.tools.pattern_tools.identify_amplifiers", return_value=[]),
            patch("kicad_mcp.tools.pattern_tools.identify_filters", return_value=[]),
            patch("kicad_mcp.tools.pattern_tools.identify_oscillators", return_value=[]),
            patch("kicad_mcp.tools.pattern_tools.identify_digital_interfaces", return_value=[]),
            patch(
                "kicad_mcp.tools.pattern_tools.identify_microcontrollers",
                return_value=[{"type": "microcontroller", "component": "U2"}],
            ) as mcu_mock,
            patch("kicad_mcp.tools.pattern_tools.identify_sensor_interfaces", return_value=[]),
        ):
            result = await identify(schematic_path=str(schematic), ctx=mock_context)

        assert result["success"] is True
        assert result["component_count"] == 2
        assert result["total_patterns_found"] == 2
        assert result["identified_patterns"]["power_supply_circuits"][0]["main_component"] == "U1"
        assert result["identified_patterns"]["microcontroller_circuits"][0]["component"] == "U2"
        power_mock.assert_called_once_with(netlist["components"], netlist["nets"])
        mcu_mock.assert_called_once_with(netlist["components"])
        mock_context.report_progress.assert_any_await(100, 100)

    @pytest.mark.asyncio
    async def test_missing_schematic_returns_error(self, mcp_with_pattern_tools, mock_context):
        identify = mcp_with_pattern_tools.tools["identify_circuit_patterns"]

        result = await identify(schematic_path="/no/such/file.kicad_sch", ctx=mock_context)

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        mock_context.info.assert_awaited()

    @pytest.mark.asyncio
    async def test_malformed_schematic_returns_parse_error(
        self, mcp_with_pattern_tools, mock_context, tmp_path
    ):
        schematic = tmp_path / "bad.kicad_sch"
        schematic.write_text("not a schematic")
        identify = mcp_with_pattern_tools.tools["identify_circuit_patterns"]

        result = await identify(schematic_path=str(schematic), ctx=mock_context)

        assert result["success"] is False
        assert "invalid schematic format" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_real_recognizers_identify_power_supply_and_microcontroller(
        self, mcp_with_pattern_tools, mock_context, tmp_path
    ):
        schematic = write_pattern_schematic(tmp_path / "patterns.kicad_sch")
        identify = mcp_with_pattern_tools.tools["identify_circuit_patterns"]

        result = await identify(schematic_path=str(schematic), ctx=mock_context)

        assert result["success"] is True
        assert result["identified_patterns"]["power_supply_circuits"]
        assert result["identified_patterns"]["microcontroller_circuits"]

    @pytest.mark.asyncio
    async def test_real_recognizers_handle_complex_fixture(
        self, mcp_with_pattern_tools, mock_context
    ):
        schematic = Path("tests/fixtures/sample_schematics/complex_schematic.kicad_sch")
        identify = mcp_with_pattern_tools.tools["identify_circuit_patterns"]

        result = await identify(schematic_path=str(schematic), ctx=mock_context)

        assert result["success"] is True
        assert result["component_count"] > 0
        assert result["total_patterns_found"] > 0


class TestAnalyzeProjectCircuitPatterns:
    @pytest.mark.asyncio
    async def test_resolves_schematic_from_project_path(
        self, mcp_with_pattern_tools, mock_context, tmp_path
    ):
        project = tmp_path / "demo.kicad_pro"
        project.write_text("{}")
        write_pattern_schematic(tmp_path / "demo.kicad_sch")
        analyze = mcp_with_pattern_tools.tools["analyze_project_circuit_patterns"]

        result = await analyze(project_path=str(project), ctx=mock_context)

        assert result["success"] is True
        assert result["project_path"] == str(project)
        assert result["schematic_path"] == str(tmp_path / "demo.kicad_sch")

    @pytest.mark.asyncio
    async def test_project_without_schematic_returns_error(
        self, mcp_with_pattern_tools, mock_context, tmp_path
    ):
        project = tmp_path / "missing_schematic.kicad_pro"
        project.write_text("{}")
        analyze = mcp_with_pattern_tools.tools["analyze_project_circuit_patterns"]

        result = await analyze(project_path=str(project), ctx=mock_context)

        assert result["success"] is False
        assert "schematic" in result["error"].lower()

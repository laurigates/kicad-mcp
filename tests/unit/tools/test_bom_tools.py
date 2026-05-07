"""Unit tests for bom_tools.py - BOM analysis and CSV export.

Backs user stories M1 (export_bom_csv) and M2 (analyze_bom) from
docs/USER_STORIES.md.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import FastMCP
import pytest

from kicad_mcp.tools.bom_tools import (
    analyze_bom_data,
    parse_bom_file,
    register_bom_tools,
)


def _get_tool(mcp: FastMCP, name: str):
    return mcp._tool_manager._tools[name].fn


@pytest.fixture
def mcp_with_bom_tools():
    mcp = FastMCP("test")
    register_bom_tools(mcp)
    return mcp


class TestRegistration:
    def test_registers_expected_tools(self, mcp_with_bom_tools):
        tools = set(mcp_with_bom_tools._tool_manager._tools)
        assert {"analyze_bom", "export_bom_csv"} <= tools


class TestParseBomFile:
    """parse_bom_file is the core helper for analyze_bom; verify formats."""

    def test_parses_kicad_csv(self, tmp_path):
        f = tmp_path / "bom.csv"
        f.write_text(
            "Reference,Value,Footprint,Quantity\nR1,10k,0805,1\nC1,100nF,0603,1\nU1,ESP32,QFN48,1\n"
        )
        components, info = parse_bom_file(str(f))

        assert len(components) == 3
        assert info["detected_format"] == "kicad"
        assert info["delimiter"] == ","
        assert components[0]["Reference"] == "R1"

    def test_parses_semicolon_csv(self, tmp_path):
        f = tmp_path / "euro.csv"
        f.write_text("Reference;Value\nR1;10k\nR2;1k\n")
        components, info = parse_bom_file(str(f))

        assert len(components) == 2
        assert info["delimiter"] == ";"

    def test_parses_json_list_format(self, tmp_path):
        f = tmp_path / "bom.json"
        f.write_text('[{"reference": "R1", "value": "10k"}]')
        components, info = parse_bom_file(str(f))

        assert components == [{"reference": "R1", "value": "10k"}]
        assert info["detected_format"] == "json"

    def test_parses_json_components_key(self, tmp_path):
        f = tmp_path / "bom.json"
        f.write_text('{"components": [{"reference": "C1", "value": "100nF"}]}')
        components, _ = parse_bom_file(str(f))

        assert len(components) == 1
        assert components[0]["reference"] == "C1"

    def test_unknown_extension_falls_back_to_csv(self, tmp_path):
        f = tmp_path / "weird.txt"
        f.write_text("Reference,Value\nR1,10k\n")
        components, info = parse_bom_file(str(f))

        assert len(components) == 1
        assert info["detected_format"] == "unknown_csv"


class TestAnalyzeBomData:
    """analyze_bom_data turns parsed rows into the summary the user sees."""

    def test_categorizes_by_reference_prefix(self):
        rows = [
            {"reference": "R1", "value": "10k"},
            {"reference": "R2", "value": "1k"},
            {"reference": "C1", "value": "100nF"},
            {"reference": "U1", "value": "ESP32"},
        ]
        result = analyze_bom_data(rows, {"detected_format": "kicad"})

        assert result["unique_component_count"] == 4
        assert result["total_component_count"] == 4
        # Prefixes are mapped to friendly category names
        assert result["categories"].get("Resistors") == 2
        assert result["categories"].get("Capacitors") == 1
        assert result["categories"].get("ICs") == 1

    def test_quantity_column_is_summed(self):
        rows = [
            {"reference": "R1", "value": "10k", "quantity": "5"},
            {"reference": "C1", "value": "100nF", "quantity": "3"},
        ]
        result = analyze_bom_data(rows, {})

        assert result["total_component_count"] == 8
        assert result["unique_component_count"] == 2

    def test_cost_column_is_summed_with_currency(self):
        rows = [
            {"reference": "R1", "value": "10k", "quantity": "2", "cost": "$0.10"},
            {"reference": "C1", "value": "100nF", "quantity": "4", "cost": "$0.05"},
        ]
        result = analyze_bom_data(rows, {})

        assert result["has_cost_data"] is True
        # 2 * 0.10 + 4 * 0.05 = 0.40
        assert result["total_cost"] == pytest.approx(0.40)
        assert result["currency"] == "USD"

    def test_empty_input_returns_zero_counts(self):
        result = analyze_bom_data([], {})

        assert result["unique_component_count"] == 0
        assert result["total_component_count"] == 0


class TestAnalyzeBom:
    """Story M2: end-to-end BOM analysis tool."""

    @pytest.mark.asyncio
    async def test_missing_project_returns_error(self, mcp_with_bom_tools, mock_context):
        analyze_bom = _get_tool(mcp_with_bom_tools, "analyze_bom")

        result = await analyze_bom(project_path="/no/such.kicad_pro", ctx=mock_context)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_no_bom_files_returns_helpful_error(
        self, mcp_with_bom_tools, mock_context, sample_kicad_project
    ):
        analyze_bom = _get_tool(mcp_with_bom_tools, "analyze_bom")

        result = await analyze_bom(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is False
        assert "bom" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_analyzes_csv_bom_next_to_project(
        self, mcp_with_bom_tools, mock_context, sample_kicad_project
    ):
        # Drop a sibling BOM that get_project_files will discover.
        from pathlib import Path

        project_dir = Path(sample_kicad_project["directory"])
        project_name = sample_kicad_project["name"]
        bom_file = project_dir / f"{project_name}-bom.csv"
        bom_file.write_text("Reference,Value,Quantity\nR1,10k,2\nC1,100nF,4\nU1,ESP32,1\n")

        analyze_bom = _get_tool(mcp_with_bom_tools, "analyze_bom")
        result = await analyze_bom(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is True
        assert result["component_summary"]["total_components"] == 7
        assert result["component_summary"]["total_unique_components"] == 3
        # Progress was reported
        mock_context.report_progress.assert_called()


class TestExportBomCsv:
    """Story M1: export a CSV BOM via kicad-cli."""

    @pytest.mark.asyncio
    async def test_missing_project_returns_error(self, mcp_with_bom_tools, mock_context):
        export = _get_tool(mcp_with_bom_tools, "export_bom_csv")

        result = await export(project_path="/no/such.kicad_pro", ctx=mock_context)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_schematic_returns_error(
        self, mcp_with_bom_tools, mock_context, tmp_path
    ):
        # Project file exists, but there is no sibling .kicad_sch
        pro = tmp_path / "noSch.kicad_pro"
        pro.write_text("{}")

        export = _get_tool(mcp_with_bom_tools, "export_bom_csv")
        result = await export(project_path=str(pro), ctx=mock_context)

        assert result["success"] is False
        assert "schematic" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_export_via_cli(
        self, mcp_with_bom_tools, mock_context, sample_kicad_project
    ):
        export = _get_tool(mcp_with_bom_tools, "export_bom_csv")

        async def fake_export(schematic_file, output_dir, project_name, ctx):
            output_file = f"{output_dir}/{project_name}_bom.csv"
            # Simulate kicad-cli writing the file
            with open(output_file, "w") as f:
                f.write("Reference,Value\nR1,10k\n")
            return {
                "success": True,
                "output_file": output_file,
                "schematic_file": schematic_file,
                "file_size": 24,
                "message": "BOM exported successfully",
            }

        with patch(
            "kicad_mcp.tools.bom_tools.export_bom_with_cli", side_effect=fake_export
        ) as mock_export:
            result = await export(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is True
        assert result["output_file"].endswith("_bom.csv")
        mock_export.assert_called_once()

    @pytest.mark.asyncio
    async def test_cli_failure_is_propagated(
        self, mcp_with_bom_tools, mock_context, sample_kicad_project
    ):
        export = _get_tool(mcp_with_bom_tools, "export_bom_csv")

        with patch(
            "kicad_mcp.tools.bom_tools.export_bom_with_cli",
            new=AsyncMock(return_value={"success": False, "error": "kicad-cli not found"}),
        ):
            result = await export(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is False
        assert "kicad-cli" in result["error"]

    @pytest.mark.asyncio
    async def test_cli_exception_is_caught(
        self, mcp_with_bom_tools, mock_context, sample_kicad_project
    ):
        """If export_bom_with_cli raises, the tool should still return a dict, not crash."""
        export = _get_tool(mcp_with_bom_tools, "export_bom_csv")

        with patch(
            "kicad_mcp.tools.bom_tools.export_bom_with_cli",
            new=AsyncMock(side_effect=OSError("disk full")),
        ):
            result = await export(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is False
        assert "disk full" in result["error"]


class TestExportBomWithCli:
    """The lower-level CLI wrapper - verify it shells out via the secure runner."""

    @pytest.mark.asyncio
    async def test_runs_kicad_command_and_returns_success(self, tmp_path, mock_context):
        from kicad_mcp.tools.bom_tools import export_bom_with_cli

        schematic = tmp_path / "p.kicad_sch"
        schematic.write_text("(kicad_sch)")
        output_path = tmp_path / "p_bom.csv"

        fake_proc = MagicMock(returncode=0, stdout="ok", stderr="")
        fake_runner = MagicMock()
        fake_runner.run_kicad_command.return_value = fake_proc

        def write_output(*args, **kwargs):
            output_path.write_text("Reference,Value\nR1,10k\n")
            return fake_proc

        fake_runner.run_kicad_command.side_effect = write_output

        with patch(
            "kicad_mcp.utils.secure_subprocess.get_subprocess_runner",
            return_value=fake_runner,
        ):
            result = await export_bom_with_cli(str(schematic), str(tmp_path), "p", mock_context)

        assert result["success"] is True
        assert result["output_file"] == str(output_path)
        assert result["file_size"] > 0
        fake_runner.run_kicad_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_nonzero_return_code_is_failure(self, tmp_path, mock_context):
        from kicad_mcp.tools.bom_tools import export_bom_with_cli

        schematic = tmp_path / "p.kicad_sch"
        schematic.write_text("(kicad_sch)")

        fake_runner = MagicMock()
        fake_runner.run_kicad_command.return_value = MagicMock(
            returncode=1, stdout="", stderr="boom"
        )

        with patch(
            "kicad_mcp.utils.secure_subprocess.get_subprocess_runner",
            return_value=fake_runner,
        ):
            result = await export_bom_with_cli(str(schematic), str(tmp_path), "p", mock_context)

        assert result["success"] is False
        assert "boom" in result["error"]

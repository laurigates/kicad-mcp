"""Unit tests for drc_tools.py - DRC execution and history.

Backs user stories R1 (run_drc_check) and R2 (get_drc_history_tool)
from docs/USER_STORIES.md.
"""

from unittest.mock import AsyncMock, patch

from fastmcp import FastMCP
import pytest

from kicad_mcp.tools.drc_tools import register_drc_tools


def _get_tool(mcp: FastMCP, name: str):
    return mcp._tool_manager._tools[name].fn


@pytest.fixture
def mcp_with_drc_tools():
    mcp = FastMCP("test")
    register_drc_tools(mcp)
    return mcp


class TestRegistration:
    def test_registers_expected_tools(self, mcp_with_drc_tools):
        tools = set(mcp_with_drc_tools._tool_manager._tools)
        assert {"run_drc_check", "get_drc_history_tool"} <= tools


class TestGetDrcHistoryTool:
    """Story R2: surface DRC trend over time."""

    def test_missing_project_returns_error(self, mcp_with_drc_tools):
        get_history = _get_tool(mcp_with_drc_tools, "get_drc_history_tool")

        result = get_history(project_path="/no/such.kicad_pro")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_no_history_returns_empty_list_with_no_trend(
        self, mcp_with_drc_tools, sample_kicad_project
    ):
        get_history = _get_tool(mcp_with_drc_tools, "get_drc_history_tool")

        with patch("kicad_mcp.tools.drc_tools.get_drc_history", return_value=[]):
            result = get_history(project_path=sample_kicad_project["path"])

        assert result["success"] is True
        assert result["entry_count"] == 0
        assert result["trend"] is None
        assert result["history_entries"] == []

    def test_single_entry_has_no_trend(self, mcp_with_drc_tools, sample_kicad_project):
        get_history = _get_tool(mcp_with_drc_tools, "get_drc_history_tool")
        entries = [{"timestamp": 100.0, "datetime": "2026-05-01 00:00:00", "total_violations": 5}]

        with patch("kicad_mcp.tools.drc_tools.get_drc_history", return_value=entries):
            result = get_history(project_path=sample_kicad_project["path"])

        assert result["entry_count"] == 1
        assert result["trend"] is None

    def test_improving_trend_when_violations_decrease(
        self, mcp_with_drc_tools, sample_kicad_project
    ):
        # Entries are returned newest-first by get_drc_history, so the tool
        # treats history[0] as "latest" and history[-1] as "earliest".
        entries = [
            {"timestamp": 200.0, "total_violations": 2},  # newest
            {"timestamp": 150.0, "total_violations": 5},
            {"timestamp": 100.0, "total_violations": 10},  # oldest
        ]
        get_history = _get_tool(mcp_with_drc_tools, "get_drc_history_tool")

        with patch("kicad_mcp.tools.drc_tools.get_drc_history", return_value=entries):
            result = get_history(project_path=sample_kicad_project["path"])

        assert result["trend"] == "improving"
        assert result["entry_count"] == 3

    def test_degrading_trend_when_violations_increase(
        self, mcp_with_drc_tools, sample_kicad_project
    ):
        entries = [
            {"timestamp": 200.0, "total_violations": 12},  # newest
            {"timestamp": 100.0, "total_violations": 3},  # oldest
        ]
        get_history = _get_tool(mcp_with_drc_tools, "get_drc_history_tool")

        with patch("kicad_mcp.tools.drc_tools.get_drc_history", return_value=entries):
            result = get_history(project_path=sample_kicad_project["path"])

        assert result["trend"] == "degrading"

    def test_stable_trend_when_violations_unchanged(self, mcp_with_drc_tools, sample_kicad_project):
        entries = [
            {"timestamp": 200.0, "total_violations": 4},
            {"timestamp": 100.0, "total_violations": 4},
        ]
        get_history = _get_tool(mcp_with_drc_tools, "get_drc_history_tool")

        with patch("kicad_mcp.tools.drc_tools.get_drc_history", return_value=entries):
            result = get_history(project_path=sample_kicad_project["path"])

        assert result["trend"] == "stable"


class TestRunDrcCheck:
    """Story R1: run DRC and surface violations."""

    @pytest.mark.asyncio
    async def test_missing_project_returns_error(self, mcp_with_drc_tools, mock_context):
        run_drc = _get_tool(mcp_with_drc_tools, "run_drc_check")

        result = await run_drc(project_path="/no/such.kicad_pro", ctx=mock_context)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_pcb_returns_error(self, mcp_with_drc_tools, mock_context, tmp_path):
        # Project file with no sibling .kicad_pcb
        pro = tmp_path / "noPcb.kicad_pro"
        pro.write_text("{}")

        run_drc = _get_tool(mcp_with_drc_tools, "run_drc_check")
        result = await run_drc(project_path=str(pro), ctx=mock_context)

        assert result["success"] is False
        assert "pcb" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_run_saves_history_and_reports_progress(
        self, mcp_with_drc_tools, mock_context, sample_kicad_project
    ):
        run_drc = _get_tool(mcp_with_drc_tools, "run_drc_check")
        drc_payload = {
            "success": True,
            "total_violations": 0,
            "violation_categories": {},
            "violations": [],
        }

        with (
            patch(
                "kicad_mcp.tools.drc_tools.run_drc_via_cli",
                new=AsyncMock(return_value=drc_payload),
            ) as mock_cli,
            patch("kicad_mcp.tools.drc_tools.save_drc_result") as mock_save,
            patch("kicad_mcp.tools.drc_tools.compare_with_previous", return_value=None),
        ):
            result = await run_drc(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is True
        assert result["total_violations"] == 0
        # Underlying CLI was invoked with the discovered PCB path
        mock_cli.assert_awaited_once()
        called_pcb_arg = mock_cli.await_args.args[0]
        assert called_pcb_arg == sample_kicad_project["pcb"]
        # Successful runs are persisted to history
        mock_save.assert_called_once()
        # Progress reported at start and end
        assert mock_context.report_progress.call_count >= 2

    @pytest.mark.asyncio
    async def test_comparison_with_previous_run_is_attached(
        self, mcp_with_drc_tools, mock_context, sample_kicad_project
    ):
        run_drc = _get_tool(mcp_with_drc_tools, "run_drc_check")
        comparison = {
            "current_violations": 1,
            "previous_violations": 3,
            "change": -2,
            "previous_datetime": "2026-05-01 00:00:00",
            "new_categories": {},
            "resolved_categories": {"clearance": 2},
            "changed_categories": {},
        }

        with (
            patch(
                "kicad_mcp.tools.drc_tools.run_drc_via_cli",
                new=AsyncMock(
                    return_value={
                        "success": True,
                        "total_violations": 1,
                        "violation_categories": {"clearance": 1},
                    }
                ),
            ),
            patch("kicad_mcp.tools.drc_tools.save_drc_result"),
            patch(
                "kicad_mcp.tools.drc_tools.compare_with_previous",
                return_value=comparison,
            ),
        ):
            result = await run_drc(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["comparison"] == comparison
        # The tool should send a user-facing message celebrating the improvement
        info_calls = [c.args[0] for c in mock_context.info.call_args_list if c.args]
        assert any("fixed" in msg.lower() for msg in info_calls)

    @pytest.mark.asyncio
    async def test_failed_drc_does_not_save_history(
        self, mcp_with_drc_tools, mock_context, sample_kicad_project
    ):
        run_drc = _get_tool(mcp_with_drc_tools, "run_drc_check")
        failure = {"success": False, "error": "kicad-cli not found"}

        with (
            patch(
                "kicad_mcp.tools.drc_tools.run_drc_via_cli",
                new=AsyncMock(return_value=failure),
            ),
            patch("kicad_mcp.tools.drc_tools.save_drc_result") as mock_save,
        ):
            result = await run_drc(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result == failure
        mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_result_falls_back_to_generic_failure(
        self, mcp_with_drc_tools, mock_context, sample_kicad_project
    ):
        run_drc = _get_tool(mcp_with_drc_tools, "run_drc_check")

        with patch(
            "kicad_mcp.tools.drc_tools.run_drc_via_cli",
            new=AsyncMock(return_value=None),
        ):
            result = await run_drc(project_path=sample_kicad_project["path"], ctx=mock_context)

        assert result["success"] is False
        assert "unknown" in result["error"].lower()

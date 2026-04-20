"""Tests for kicad_mcp.utils.drc_history."""

import os

import pytest

from kicad_mcp.utils.drc_history import (
    compare_with_previous,
    ensure_history_dir,
    get_drc_history,
    get_project_history_path,
    save_drc_result,
)


class TestEnsureHistoryDir:
    """Tests for ensure_history_dir."""

    def test_creates_directory(self, tmp_path, monkeypatch) -> None:
        target = str(tmp_path / "drc_hist")
        monkeypatch.setattr("kicad_mcp.utils.drc_history.DRC_HISTORY_DIR", target)
        ensure_history_dir()
        assert os.path.isdir(target)

    def test_idempotent(self, tmp_path, monkeypatch) -> None:
        target = str(tmp_path / "drc_hist")
        monkeypatch.setattr("kicad_mcp.utils.drc_history.DRC_HISTORY_DIR", target)
        ensure_history_dir()
        ensure_history_dir()  # should not raise


class TestGetProjectHistoryPath:
    """Tests for get_project_history_path."""

    def test_returns_path_in_history_dir(self, monkeypatch) -> None:
        monkeypatch.setattr("kicad_mcp.utils.drc_history.DRC_HISTORY_DIR", "/tmp/drc")
        path = get_project_history_path("/home/user/project.kicad_pro")
        assert path.startswith("/tmp/drc/")
        assert "project.kicad_pro" in path
        assert path.endswith("_drc_history.json")

    def test_different_projects_different_paths(self, monkeypatch) -> None:
        monkeypatch.setattr("kicad_mcp.utils.drc_history.DRC_HISTORY_DIR", "/tmp/drc")
        p1 = get_project_history_path("/a/project1.kicad_pro")
        p2 = get_project_history_path("/b/project2.kicad_pro")
        assert p1 != p2


class TestSaveAndGetDrcHistory:
    """Integration tests for save_drc_result and get_drc_history."""

    @pytest.fixture()
    def history_dir(self, tmp_path, monkeypatch):
        target = str(tmp_path / "drc_hist")
        monkeypatch.setattr("kicad_mcp.utils.drc_history.DRC_HISTORY_DIR", target)
        return target

    def test_save_and_retrieve(self, history_dir) -> None:
        project = "/fake/project.kicad_pro"
        drc_result = {"total_violations": 3, "violation_categories": {"clearance": 2, "width": 1}}
        save_drc_result(project, drc_result)
        history = get_drc_history(project)
        assert len(history) == 1
        assert history[0]["total_violations"] == 3

    def test_history_sorted_newest_first(self, history_dir) -> None:
        project = "/fake/project.kicad_pro"
        save_drc_result(project, {"total_violations": 1, "violation_categories": {}})
        save_drc_result(project, {"total_violations": 5, "violation_categories": {}})
        history = get_drc_history(project)
        assert len(history) == 2
        # Newest first
        assert history[0]["timestamp"] >= history[1]["timestamp"]

    def test_no_history_returns_empty(self, history_dir) -> None:
        history = get_drc_history("/nonexistent/project.kicad_pro")
        assert history == []

    def test_corrupt_file_returns_empty(self, history_dir) -> None:
        project = "/fake/project.kicad_pro"
        # Write corrupt JSON
        ensure_history_dir()
        path = get_project_history_path(project)
        with open(path, "w") as f:
            f.write("not valid json{{{")
        history = get_drc_history(project)
        assert history == []

    def test_max_entries_capped(self, history_dir) -> None:
        project = "/fake/project.kicad_pro"
        for i in range(15):
            save_drc_result(project, {"total_violations": i, "violation_categories": {}})
        history = get_drc_history(project)
        assert len(history) <= 10


class TestCompareWithPrevious:
    """Tests for compare_with_previous."""

    @pytest.fixture()
    def history_dir(self, tmp_path, monkeypatch):
        target = str(tmp_path / "drc_hist")
        monkeypatch.setattr("kicad_mcp.utils.drc_history.DRC_HISTORY_DIR", target)
        return target

    def test_no_history_returns_none(self, history_dir) -> None:
        result = compare_with_previous(
            "/fake/project.kicad_pro",
            {"total_violations": 1, "violation_categories": {}},
        )
        assert result is None

    def test_single_entry_returns_none(self, history_dir) -> None:
        project = "/fake/project.kicad_pro"
        save_drc_result(project, {"total_violations": 3, "violation_categories": {}})
        result = compare_with_previous(project, {"total_violations": 1, "violation_categories": {}})
        assert result is None

    def test_comparison_with_two_entries(self, history_dir) -> None:
        project = "/fake/project.kicad_pro"
        save_drc_result(project, {"total_violations": 5, "violation_categories": {"a": 3, "b": 2}})
        save_drc_result(project, {"total_violations": 3, "violation_categories": {"a": 2, "c": 1}})

        current = {"total_violations": 2, "violation_categories": {"a": 1, "d": 1}}
        result = compare_with_previous(project, current)
        assert result is not None
        assert result["current_violations"] == 2
        assert "change" in result
        assert "new_categories" in result
        assert "resolved_categories" in result
        assert "changed_categories" in result

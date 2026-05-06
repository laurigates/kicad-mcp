"""Unit tests for project_tools.py - project discovery, structure, and open.

Backs user stories P1 (list_projects), P2 (get_project_structure),
H6 (open_project), and P3 (validate_project) from docs/USER_STORIES.md.
"""

from unittest.mock import patch

from fastmcp import FastMCP
import pytest

from kicad_mcp.tools.analysis_tools import register_analysis_tools
from kicad_mcp.tools.project_tools import register_project_tools


def _get_tool(mcp: FastMCP, name: str):
    """Pull a registered tool's underlying function out of FastMCP."""
    return mcp._tool_manager._tools[name].fn


class TestRegistration:
    def test_register_project_tools_registers_expected_names(self):
        mcp = FastMCP("test")
        register_project_tools(mcp)

        tools = set(mcp._tool_manager._tools)
        assert {"list_projects", "get_project_structure", "open_project"} <= tools


class TestListProjects:
    """Story P1: list every KiCad project under one or more search dirs."""

    def test_default_search_uses_find_kicad_projects(self):
        mcp = FastMCP("test")
        register_project_tools(mcp)
        list_projects = _get_tool(mcp, "list_projects")

        sample = [{"name": "alpha", "path": "/a/alpha.kicad_pro"}]
        with (
            patch(
                "kicad_mcp.tools.project_tools.find_kicad_projects", return_value=sample
            ) as mock_default,
            patch("kicad_mcp.tools.project_tools.find_kicad_projects_in_dirs") as mock_dirs,
        ):
            result = list_projects(search_directories=None)

        assert result == sample
        mock_default.assert_called_once_with()
        mock_dirs.assert_not_called()

    def test_custom_search_directories_are_forwarded(self):
        mcp = FastMCP("test")
        register_project_tools(mcp)
        list_projects = _get_tool(mcp, "list_projects")

        dirs = ["/tmp/projects", "/opt/work"]
        sample = [
            {"name": "beta", "path": "/tmp/projects/beta.kicad_pro"},
            {"name": "gamma", "path": "/opt/work/gamma.kicad_pro"},
        ]
        with (
            patch(
                "kicad_mcp.tools.project_tools.find_kicad_projects_in_dirs",
                return_value=sample,
            ) as mock_dirs,
            patch("kicad_mcp.tools.project_tools.find_kicad_projects") as mock_default,
        ):
            result = list_projects(search_directories=dirs)

        assert result == sample
        mock_dirs.assert_called_once_with(dirs)
        mock_default.assert_not_called()

    def test_empty_directory_list_falls_through_to_default(self):
        """An empty list is falsy, so the tool should fall back to defaults."""
        mcp = FastMCP("test")
        register_project_tools(mcp)
        list_projects = _get_tool(mcp, "list_projects")

        with (
            patch(
                "kicad_mcp.tools.project_tools.find_kicad_projects", return_value=[]
            ) as mock_default,
            patch("kicad_mcp.tools.project_tools.find_kicad_projects_in_dirs") as mock_dirs,
        ):
            result = list_projects(search_directories=[])

        assert result == []
        mock_default.assert_called_once()
        mock_dirs.assert_not_called()


class TestGetProjectStructure:
    """Story P2: inspect the file structure and metadata of a project."""

    @pytest.mark.asyncio
    async def test_returns_full_structure_for_existing_project(self, sample_kicad_project):
        mcp = FastMCP("test")
        register_project_tools(mcp)
        get_structure = _get_tool(mcp, "get_project_structure")

        result = get_structure(project_path=sample_kicad_project["path"])

        assert result["name"] == sample_kicad_project["name"]
        assert result["path"] == sample_kicad_project["path"]
        assert result["directory"] == sample_kicad_project["directory"]
        assert "files" in result
        # The fixture creates schematic + pcb + project files
        assert "project" in result["files"]
        assert "schematic" in result["files"]
        assert "pcb" in result["files"]
        # Metadata is optional in the fixture (pyproject doesn't write a `metadata` block),
        # so just assert the key exists
        assert "metadata" in result

    def test_returns_error_for_nonexistent_path(self):
        mcp = FastMCP("test")
        register_project_tools(mcp)
        get_structure = _get_tool(mcp, "get_project_structure")

        result = get_structure(project_path="/no/such/place.kicad_pro")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_metadata_is_extracted_when_present(self, tmp_path):
        """If the .kicad_pro contains a metadata block, it should be surfaced."""
        import json

        project_dir = tmp_path / "with_meta"
        project_dir.mkdir()
        pro = project_dir / "with_meta.kicad_pro"
        pro.write_text(json.dumps({"metadata": {"author": "test", "revision": "A"}, "meta": {}}))
        # Empty schematic + pcb so file discovery has something to find
        (project_dir / "with_meta.kicad_sch").write_text("(kicad_sch)")
        (project_dir / "with_meta.kicad_pcb").write_text("(kicad_pcb)")

        mcp = FastMCP("test")
        register_project_tools(mcp)
        get_structure = _get_tool(mcp, "get_project_structure")

        result = get_structure(project_path=str(pro))

        assert result["metadata"] == {"author": "test", "revision": "A"}


class TestOpenProject:
    """Story H6: open a generated project in KiCad."""

    def test_delegates_to_open_kicad_project(self):
        mcp = FastMCP("test")
        register_project_tools(mcp)
        open_project = _get_tool(mcp, "open_project")

        expected = {"success": True, "message": "Opened in KiCad"}
        with patch(
            "kicad_mcp.tools.project_tools.open_kicad_project", return_value=expected
        ) as mock_open:
            result = open_project(project_path="/some/project.kicad_pro")

        assert result == expected
        mock_open.assert_called_once_with("/some/project.kicad_pro")

    def test_propagates_failure_dict(self):
        mcp = FastMCP("test")
        register_project_tools(mcp)
        open_project = _get_tool(mcp, "open_project")

        failure = {"success": False, "error": "KiCad not installed"}
        with patch("kicad_mcp.tools.project_tools.open_kicad_project", return_value=failure):
            result = open_project(project_path="/some/project.kicad_pro")

        assert result == failure


class TestValidateProject:
    """Story P3: validate that a project has the essential KiCad files."""

    def test_valid_project_has_no_issues(self, sample_kicad_project):
        mcp = FastMCP("test")
        register_analysis_tools(mcp)
        validate = _get_tool(mcp, "validate_project")

        result = validate(project_path=sample_kicad_project["path"])

        assert result["valid"] is True
        assert result["issues"] is None
        assert "schematic" in result["files_found"]
        assert "pcb" in result["files_found"]

    def test_missing_path_returns_error(self):
        mcp = FastMCP("test")
        register_analysis_tools(mcp)
        validate = _get_tool(mcp, "validate_project")

        result = validate(project_path="/does/not/exist.kicad_pro")

        assert result["valid"] is False
        assert "error" in result

    def test_missing_pcb_and_schematic_are_reported(self, tmp_path):
        """A .kicad_pro file alone (no .kicad_sch / .kicad_pcb) should fail validation."""
        pro = tmp_path / "lonely.kicad_pro"
        pro.write_text("{}")  # Valid JSON but no siblings

        mcp = FastMCP("test")
        register_analysis_tools(mcp)
        validate = _get_tool(mcp, "validate_project")

        result = validate(project_path=str(pro))

        assert result["valid"] is False
        issues = result["issues"]
        assert any("schematic" in issue.lower() for issue in issues)
        assert any("pcb" in issue.lower() for issue in issues)

    def test_invalid_json_is_reported(self, tmp_path):
        pro = tmp_path / "bad.kicad_pro"
        pro.write_text("{ this is not valid json")
        # Sibling files so PCB/schematic checks pass
        (tmp_path / "bad.kicad_sch").write_text("(kicad_sch)")
        (tmp_path / "bad.kicad_pcb").write_text("(kicad_pcb)")

        mcp = FastMCP("test")
        register_analysis_tools(mcp)
        validate = _get_tool(mcp, "validate_project")

        result = validate(project_path=str(pro))

        assert result["valid"] is False
        assert any("json" in issue.lower() for issue in result["issues"])

"""Tools and resources that delegate to a sibling tool/resource, exercised through MCP.

``@mcp.tool()`` and ``@mcp.resource()`` replace the decorated function with a
non-callable ``FunctionTool`` / ``FunctionResourceTemplate``. A project-level
tool that ``await``s a decorated sibling therefore fails with
``'FunctionTool' object is not callable`` — but only when registered on a real
``FastMCP``. These tests go through ``fastmcp.Client`` in memory so the real
registration path is what runs; a fake registry that returns the bare function
cannot detect the bug.
"""

from pathlib import Path
import shutil
from urllib.parse import quote

from fastmcp import Client, FastMCP
import pytest

from kicad_mcp.resources.netlist_resources import register_netlist_resources
from kicad_mcp.resources.pattern_resources import register_pattern_resources
from kicad_mcp.tools.export_tools import register_export_tools
from kicad_mcp.tools.netlist_tools import register_netlist_tools
from kicad_mcp.tools.pattern_tools import register_pattern_tools
from kicad_mcp.tools.text_to_schematic import register_text_to_schematic_tools
from kicad_mcp.tools.visualization_tools import register_visualization_tools

FIXTURE_SCHEMATIC = (
    Path(__file__).parent.parent / "fixtures" / "sample_schematics" / "sexpr_schematic.kicad_sch"
)

NOT_CALLABLE = "object is not callable"


@pytest.fixture
def mcp() -> FastMCP:
    server = FastMCP("sibling-call-test")
    register_netlist_tools(server)
    register_pattern_tools(server)
    register_export_tools(server)
    register_visualization_tools(server)
    register_text_to_schematic_tools(server)
    register_netlist_resources(server)
    register_pattern_resources(server)
    return server


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project directory with a .kicad_pro and a real S-expression schematic."""
    project_file = tmp_path / "demo.kicad_pro"
    project_file.write_text("{}")
    shutil.copy(FIXTURE_SCHEMATIC, tmp_path / "demo.kicad_sch")
    return project_file


def resource_uri(prefix: str, path: Path) -> str:
    """Build a resource URI; the path is percent-encoded so it fills one template segment."""
    return f"{prefix}{quote(str(path), safe='')}"


class TestProjectLevelToolsViaMcp:
    async def test_extract_project_netlist(self, mcp, project):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "extract_project_netlist", {"project_path": str(project)}
            )

        assert result.data["success"] is True
        assert result.data["project_path"] == str(project)
        assert result.data["component_count"] > 0

    async def test_analyze_project_circuit_patterns(self, mcp, project):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "analyze_project_circuit_patterns", {"project_path": str(project)}
            )

        assert result.data["success"] is True
        assert result.data["project_path"] == str(project)

    async def test_generate_project_thumbnail_without_pcb(self, mcp, project):
        # No .kicad_pcb in the project: the delegated generator returns None.
        async with Client(mcp) as client:
            result = await client.call_tool(
                "generate_project_thumbnail", {"project_path": str(project)}
            )

        assert result.is_error is False

    async def test_capture_schematic_screenshot_missing_project(self, mcp, tmp_path):
        # export_schematic_svg reports the missing project; the screenshot is None.
        async with Client(mcp) as client:
            result = await client.call_tool(
                "capture_schematic_screenshot",
                {"project_path": str(tmp_path / "missing.kicad_pro")},
            )

        assert result.is_error is False

    async def test_create_visual_comparison_missing_projects(self, mcp, tmp_path):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "create_visual_comparison",
                {
                    "before_project": str(tmp_path / "before.kicad_pro"),
                    "after_project": str(tmp_path / "after.kicad_pro"),
                },
            )

        assert result.data["success"] is False
        assert result.data["error"] == "Failed to capture one or both screenshots"

    async def test_create_kicad_schematic_from_text_json_output(self, mcp, project):
        # output_format="json" delegates to the create_circuit_from_text tool.
        description = "circuit 'Divider':\n  components:\n    - R1: resistor 10k at (10, 20)\n"

        async with Client(mcp) as client:
            result = await client.call_tool(
                "create_kicad_schematic_from_text",
                {
                    "project_path": str(project),
                    "circuit_description": description,
                    "format_type": "simple",
                    "output_format": "json",
                },
                raise_on_error=False,
            )

        assert result.is_error is False, result.content
        assert result.data["output_format"] == "JSON"


class TestProjectLevelResourcesViaMcp:
    async def test_project_netlist_resource(self, mcp, project):
        async with Client(mcp) as client:
            contents = await client.read_resource(resource_uri("kicad://project_netlist/", project))

        text = contents[0].text
        assert NOT_CALLABLE not in text
        assert text.startswith("# Netlist Analysis")

    async def test_project_patterns_resource(self, mcp, project):
        async with Client(mcp) as client:
            contents = await client.read_resource(
                resource_uri("kicad://patterns/project/", project)
            )

        text = contents[0].text
        assert NOT_CALLABLE not in text
        assert text.startswith("# Circuit Pattern Analysis")

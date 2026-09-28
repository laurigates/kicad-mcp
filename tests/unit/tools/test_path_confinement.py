"""Path-confinement tests for every path-taking MCP tool and resource.

Every tool/resource that accepts a filesystem path must confine it to the
``PathValidator`` trusted roots. These tests go through the MCP layer
(``fastmcp.Client`` in-memory) so they exercise exactly what a client can reach:
the registered callable, argument parsing, and the tool's own error shape.

See https://github.com/lamaalrajih/kicad-mcp/issues/57 for the reported class.
"""

from collections.abc import Callable
import inspect
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.parse import quote

from fastmcp import Client, FastMCP
import pytest

from kicad_mcp import config
from kicad_mcp.resources.bom_resources import register_bom_resources
from kicad_mcp.resources.drc_resources import register_drc_resources
from kicad_mcp.resources.files import register_file_resources
from kicad_mcp.resources.netlist_resources import register_netlist_resources
from kicad_mcp.resources.pattern_resources import register_pattern_resources
from kicad_mcp.resources.projects import register_project_resources
from kicad_mcp.tools.analysis_tools import register_analysis_tools
from kicad_mcp.tools.bom_tools import register_bom_tools
from kicad_mcp.tools.circuit_tools import register_circuit_tools
from kicad_mcp.tools.drc_impl import cli_drc
from kicad_mcp.tools.drc_tools import register_drc_tools
from kicad_mcp.tools.export_tools import register_export_tools
from kicad_mcp.tools.netlist_tools import register_netlist_tools
from kicad_mcp.tools.pattern_tools import register_pattern_tools
from kicad_mcp.tools.project_tools import register_project_tools
from kicad_mcp.tools.text_to_schematic import register_text_to_schematic_tools
from kicad_mcp.tools.validation_tools import register_validation_tools
from kicad_mcp.tools.visualization_tools import register_visualization_tools
from kicad_mcp.utils import path_validator, secure_subprocess
from kicad_mcp.utils.path_validator import PathValidator

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
REJECTION = "outside trusted directories"
SIMPLE_CIRCUIT = 'circuit "Probe":\n  components:\n    - R1: resistor 1k at (10, 20)\n'


def _build_server() -> FastMCP:
    mcp = FastMCP("path-confinement-test")
    for register in (
        register_project_resources,
        register_file_resources,
        register_drc_resources,
        register_bom_resources,
        register_netlist_resources,
        register_pattern_resources,
        register_project_tools,
        register_analysis_tools,
        register_export_tools,
        register_drc_tools,
        register_bom_tools,
        register_netlist_tools,
        register_pattern_tools,
        register_circuit_tools,
        register_text_to_schematic_tools,
        register_validation_tools,
        register_visualization_tools,
    ):
        register(mcp)
    return mcp


def _make_project(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    project = directory / f"{name}.kicad_pro"
    shutil.copy(FIXTURES / "sample_projects" / "test_project.kicad_pro", project)
    shutil.copy(
        FIXTURES / "sample_schematics" / "sexpr_schematic.kicad_sch",
        directory / f"{name}.kicad_sch",
    )
    (directory / f"{name}.kicad_pcb").write_text('(kicad_pcb (version 20241229) (generator "t"))')
    (directory / f"{name}.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    return project


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Map every path under root to (size, mtime_ns) so any write is detectable."""
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for entry in dirnames + filenames:
            full = os.path.join(dirpath, entry)
            st = os.lstat(full)
            snap[full] = (st.st_size, st.st_mtime_ns)
    return snap


@pytest.fixture
def layout(tmp_path, monkeypatch):
    """A trusted root with a legit project, an outside project, and escape vectors."""
    trusted = tmp_path / "trusted"
    outside = tmp_path / "outside"
    legit = _make_project(trusted / "legit", "legit")
    secret = _make_project(outside / "secret", "secret")
    # A symlinked directory inside the trusted root that points outside it.
    (trusted / "escape").symlink_to(outside / "secret", target_is_directory=True)

    monkeypatch.setattr(path_validator, "_default_validator", PathValidator({str(trusted)}))
    return {
        "trusted": trusted,
        "outside": outside,
        "legit": legit,
        "secret": secret,
        "legit_sch": legit.with_suffix(".kicad_sch"),
        "secret_sch": secret.with_suffix(".kicad_sch"),
        "legit_svg": legit.with_suffix(".svg"),
        "secret_svg": secret.with_suffix(".svg"),
    }


def _escape_paths(layout: dict[str, Path], key: str) -> dict[str, str]:
    """The three escape vectors for a given outside target."""
    target = layout[key]
    rel_from_trusted = os.path.relpath(target, layout["trusted"])
    return {
        "outside": str(target),
        "traversal": f"{layout['trusted']}/legit/../{rel_from_trusted}",
        "symlink": str(layout["trusted"] / "escape" / target.name),
    }


# (tool name, path kind in layout, builder(path, layout) -> arguments)
ToolCase = tuple[str, str, Callable[[str, dict[str, Path]], dict[str, Any]]]

TOOL_CASES: list[ToolCase] = [
    ("validate_project", "secret", lambda p, _: {"project_path": p}),
    ("get_project_structure", "secret", lambda p, _: {"project_path": p}),
    ("open_project", "secret", lambda p, _: {"project_path": p}),
    ("analyze_bom", "secret", lambda p, _: {"project_path": p}),
    ("export_bom_csv", "secret", lambda p, _: {"project_path": p}),
    ("get_drc_history_tool", "secret", lambda p, _: {"project_path": p}),
    ("run_drc_check", "secret", lambda p, _: {"project_path": p}),
    ("generate_pcb_thumbnail", "secret", lambda p, _: {"project_path": p}),
    ("generate_project_thumbnail", "secret", lambda p, _: {"project_path": p}),
    ("extract_schematic_netlist", "secret_sch", lambda p, _: {"schematic_path": p}),
    ("extract_project_netlist", "secret", lambda p, _: {"project_path": p}),
    ("analyze_schematic_connections", "secret_sch", lambda p, _: {"schematic_path": p}),
    (
        "find_component_connections",
        "secret",
        lambda p, _: {"project_path": p, "component_ref": "R1"},
    ),
    ("identify_circuit_patterns", "secret_sch", lambda p, _: {"schematic_path": p}),
    ("analyze_project_circuit_patterns", "secret", lambda p, _: {"project_path": p}),
    (
        "create_new_project",
        "outside",
        lambda p, _: {"project_name": "planted", "project_path": p},
    ),
    (
        "add_component",
        "secret",
        lambda p, _: {
            "project_path": p,
            "component_reference": "R9",
            "component_value": "1k",
            "symbol_library": "Device",
            "symbol_name": "R",
            "x_position": 10.0,
            "y_position": 10.0,
        },
    ),
    (
        "create_wire_connection",
        "secret",
        lambda p, _: {"project_path": p, "start_x": 0, "start_y": 0, "end_x": 5, "end_y": 5},
    ),
    (
        "add_power_symbol",
        "secret",
        lambda p, _: {"project_path": p, "power_type": "GND", "x_position": 1, "y_position": 1},
    ),
    ("validate_schematic", "secret", lambda p, _: {"project_path": p}),
    ("validate_project_boundaries", "secret", lambda p, _: {"project_path": p}),
    ("generate_validation_report", "secret", lambda p, _: {"project_path": p}),
    (
        "generate_validation_report",
        "outside",
        lambda p, lay: {
            "project_path": str(lay["legit"]),
            "output_path": os.path.join(p, "planted_report.json"),
        },
    ),
    (
        "create_circuit_from_text",
        "secret",
        lambda p, _: {"project_path": p, "circuit_description": SIMPLE_CIRCUIT},
    ),
    (
        "create_kicad_schematic_from_text",
        "secret",
        lambda p, _: {"project_path": p, "circuit_description": SIMPLE_CIRCUIT},
    ),
    ("export_schematic_svg", "secret", lambda p, _: {"project_path": p}),
    ("convert_svg_to_png", "secret_svg", lambda p, _: {"svg_path": p}),
    ("capture_schematic_screenshot", "secret", lambda p, _: {"project_path": p}),
    (
        "create_visual_comparison",
        "secret",
        lambda p, lay: {"before_project": p, "after_project": str(lay["legit"])},
    ),
    (
        "create_visual_comparison",
        "secret",
        lambda p, lay: {"before_project": str(lay["legit"]), "after_project": p},
    ),
]

RESOURCE_CASES: list[tuple[str, str]] = [
    ("kicad://project/{p}", "secret"),
    ("kicad://schematic/{p}", "secret_sch"),
    ("kicad://drc/history/{p}", "secret"),
    ("kicad://drc/{p}", "secret"),
    ("kicad://bom/{p}", "secret"),
    ("kicad://bom/{p}/csv", "secret"),
    ("kicad://bom/{p}/json", "secret"),
    ("kicad://netlist/{p}", "secret_sch"),
    ("kicad://project_netlist/{p}", "secret"),
    ("kicad://component/{p}/R1", "secret_sch"),
    ("kicad://patterns/{p}", "secret_sch"),
    ("kicad://patterns/project/{p}", "secret"),
]

VECTORS = ["outside", "traversal", "symlink"]


def _result_text(result) -> str:
    parts = [getattr(block, "text", "") or "" for block in result.content]
    if result.structuredContent:
        parts.append(json.dumps(result.structuredContent))
    return "\n".join(parts)


@pytest.mark.parametrize("vector", VECTORS)
@pytest.mark.parametrize(
    ("tool", "kind", "build"),
    TOOL_CASES,
    ids=[f"{name}-{i}" for i, (name, _, _) in enumerate(TOOL_CASES)],
)
async def test_tool_rejects_path_escaping_trusted_roots(layout, caplog, tool, kind, build, vector):
    """A path outside the trusted roots is refused before the tool touches it."""
    escape = _escape_paths(layout, kind)[vector]
    before = _snapshot(layout["outside"])

    caplog.set_level(logging.WARNING)
    async with Client(_build_server()) as client:
        result = await client.call_tool_mcp(tool, build(escape, layout))

    text = _result_text(result)
    assert REJECTION in text or REJECTION in caplog.text, (
        f"{tool} did not reject {vector} path {escape!r}: {text[:300]}"
    )
    assert _snapshot(layout["outside"]) == before, f"{tool} wrote outside the trusted roots"


@pytest.mark.parametrize("vector", VECTORS)
@pytest.mark.parametrize(("template", "kind"), RESOURCE_CASES)
async def test_resource_rejects_path_escaping_trusted_roots(layout, template, kind, vector):
    """Resource templates take paths via URL-encoded URI segments; confine them too."""
    escape = _escape_paths(layout, kind)[vector]
    uri = template.format(p=quote(escape, safe=""))

    async with Client(_build_server()) as client:
        contents = await client.read_resource(uri)

    text = "\n".join(getattr(c, "text", "") or "" for c in contents)
    assert REJECTION in text, f"{uri} did not reject {vector} path: {text[:300]}"


async def test_create_new_project_rejects_name_traversal(layout):
    """project_name is joined onto project_path; '..' in it must not escape."""
    async with Client(_build_server()) as client:
        result = await client.call_tool_mcp(
            "create_new_project",
            {
                "project_name": "../../outside/planted",
                "project_path": str(layout["trusted"] / "new"),
            },
        )

    assert REJECTION in _result_text(result)
    assert not (layout["outside"] / "planted.kicad_pro").exists()


# --- Controls: legitimate paths under a trusted root keep working ----------------


async def test_legit_project_still_validates(layout):
    async with Client(_build_server()) as client:
        result = await client.call_tool_mcp(
            "validate_project", {"project_path": str(layout["legit"])}
        )

    data = result.structuredContent
    assert data["valid"] is True, data
    assert set(data["files_found"]) >= {"pcb", "schematic"}


async def test_legit_project_structure_and_netlist(layout):
    async with Client(_build_server()) as client:
        structure = await client.call_tool_mcp(
            "get_project_structure", {"project_path": str(layout["legit"])}
        )
        netlist = await client.call_tool_mcp(
            "extract_schematic_netlist", {"schematic_path": str(layout["legit_sch"])}
        )

    assert structure.structuredContent["name"] == "legit"
    assert "schematic" in structure.structuredContent["files"]
    assert netlist.structuredContent["success"] is True, netlist.structuredContent


async def test_legit_writes_land_inside_trusted_root(layout):
    async with Client(_build_server()) as client:
        created = await client.call_tool_mcp(
            "create_new_project",
            {"project_name": "fresh", "project_path": str(layout["trusted"] / "fresh")},
        )
        report = await client.call_tool_mcp(
            "generate_validation_report", {"project_path": str(layout["legit"])}
        )

    assert created.structuredContent["success"] is True, created.structuredContent
    assert (layout["trusted"] / "fresh" / "fresh.kicad_pro").exists()
    assert report.structuredContent["success"] is True, report.structuredContent
    assert Path(report.structuredContent["report_path"]).is_relative_to(layout["trusted"].resolve())


async def test_legit_resource_still_reads(layout):
    async with Client(_build_server()) as client:
        contents = await client.read_resource(
            f"kicad://project/{quote(str(layout['legit']), safe='')}"
        )
    assert "# Project: legit" in contents[0].text


# --- Default trusted roots come from the configured search locations -------------


@pytest.fixture
def configured_roots(tmp_path, monkeypatch):
    """Point KICAD_USER_DIR / search paths at tmp dirs and reset the default validator."""
    user_dir = tmp_path / "kicad_user"
    extra = tmp_path / "extra_search"
    _make_project(user_dir / "alpha", "alpha")
    _make_project(extra / "beta", "beta")
    monkeypatch.setattr(config, "KICAD_USER_DIR", str(user_dir))
    monkeypatch.setattr(config, "ADDITIONAL_SEARCH_PATHS", [str(extra)])
    monkeypatch.setattr(path_validator, "_default_validator", None)
    # Run from a directory that is neither a search path nor an ancestor of one.
    cwd = tmp_path / "server_cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    return user_dir, extra


def test_default_roots_are_configured_search_paths(configured_roots):
    user_dir, extra = configured_roots
    roots = path_validator.get_default_validator().trusted_roots
    assert roots == {os.path.realpath(user_dir), os.path.realpath(extra)}
    assert os.path.realpath(os.getcwd()) not in roots


async def test_list_projects_paths_are_accepted_by_other_tools(configured_roots):
    """Every path list_projects returns must pass the same tools' validation."""
    async with Client(_build_server()) as client:
        listed = await client.call_tool_mcp("list_projects", {})
        projects = listed.structuredContent["result"]
        assert {p["name"] for p in projects} == {"alpha", "beta"}

        for project in projects:
            result = await client.call_tool_mcp(
                "validate_project", {"project_path": project["path"]}
            )
            assert result.structuredContent["valid"] is True, result.structuredContent


# --- Regression pin: no path-taking tool/resource is registered unguarded --------

PATH_PARAMS = {
    "project_path",
    "schematic_path",
    "svg_path",
    "output_path",
    "before_project",
    "after_project",
    "search_directories",
}
# list_projects validates each search directory inside find_kicad_projects_in_dirs.
EXEMPT = {("list_projects", "search_directories")}


def test_every_path_parameter_is_guarded():
    mcp = _build_server()
    callables = {name: tool.fn for name, tool in mcp._tool_manager._tools.items()}
    callables.update({uri: tmpl.fn for uri, tmpl in mcp._resource_manager._templates.items()})

    unguarded = []
    for name, fn in callables.items():
        guarded = getattr(fn, "__trusted_path_params__", {})
        for param in PATH_PARAMS & set(inspect.signature(fn).parameters):
            if (name, param) not in EXEMPT and param not in guarded:
                unguarded.append(f"{name}.{param}")

    assert not unguarded, f"unguarded path parameters: {sorted(unguarded)}"


# --- Outputs the server writes itself must still validate ------------------------


async def test_run_drc_check_temp_report_dir_is_accepted(layout, monkeypatch):
    """DRC writes its JSON report to a private temp dir outside the search paths.

    Confinement must not reject the server's own scratch output: the run succeeds
    while the default validator trusts only the project's root.
    """

    def fake_kicad_cli(self, command, **_kwargs):
        report = command[command.index("--output") + 1]
        Path(report).write_text(json.dumps({"violations": [{"message": "clearance"}]}))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(secure_subprocess, "_subprocess_runner", None)
    monkeypatch.setattr(secure_subprocess, "get_kicad_cli_path", lambda **_: "/fake/kicad-cli")
    monkeypatch.setattr(cli_drc, "find_kicad_cli", lambda *a, **k: "/fake/kicad-cli")
    monkeypatch.setattr(secure_subprocess.SecureSubprocessRunner, "_run_subprocess", fake_kicad_cli)
    monkeypatch.setattr("kicad_mcp.tools.drc_tools.save_drc_result", lambda *a, **k: None)
    monkeypatch.setattr("kicad_mcp.tools.drc_tools.compare_with_previous", lambda *a, **k: None)

    async with Client(_build_server()) as client:
        result = await client.call_tool_mcp("run_drc_check", {"project_path": str(layout["legit"])})

    data = result.structuredContent
    assert data["success"] is True, data
    assert data["total_violations"] == 1

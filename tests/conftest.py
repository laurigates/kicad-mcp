"""
Pytest configuration and shared fixtures for KiCad MCP tests.
"""

from collections.abc import Generator
import json
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

# Try to import MCP dependencies, but make it optional for unit tests
try:
    from fastmcp import Context

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create a mock Context class for when MCP is not available
    Context = Mock

# Import version constant
from kicad_mcp.utils.version import KICAD_FILE_FORMAT_VERSION


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_context() -> Context:
    """Create a mock MCP Context for testing."""
    context = Mock(spec=Context)
    context.info = AsyncMock()
    context.report_progress = AsyncMock()
    context.emit_log = AsyncMock()
    return context


@pytest.fixture
def sample_json_schematic() -> dict[str, Any]:
    """Sample JSON format schematic data for testing."""
    return {
        "components": [
            {
                "lib_id": "MCU_Espressif:ESP32-WROOM-32",
                "reference": "U1",
                "value": "ESP32-WROOM-32",
                "uuid": "12345678-1234-1234-1234-123456789abc",
                "position": {"x": 1000, "y": 1000, "angle": 0},
                "properties": {"footprint": "", "datasheet": ""},
                "pins": [],
            },
            {
                "lib_id": "power:VCC",
                "reference": "#PWR01",
                "value": "VCC",
                "uuid": "87654321-4321-4321-4321-cba987654321",
                "position": {"x": 500, "y": 300, "angle": 0},
                "properties": {"footprint": "", "datasheet": ""},
                "pins": [],
            },
        ],
        "wires": [
            {
                "uuid": "wire-1234-5678-90ab-cdef",
                "start": {"x": 500, "y": 400},
                "end": {"x": 1000, "y": 400},
            }
        ],
        "nets": [{"name": "VCC", "connections": [{"component": "#PWR01", "pin": "1"}]}],
    }


@pytest.fixture
def sample_sexpr_schematic() -> str:
    """Sample S-expression format schematic content for testing."""
    return f"""(kicad_sch
    (version {KICAD_FILE_FORMAT_VERSION})
    (generator eeschema)
    (uuid "12345678-1234-1234-1234-123456789abc")
    (paper "A4")
    (lib_symbols)
    (symbol
        (lib_id "MCU_Espressif:ESP32-WROOM-32")
        (at 127 83.82 0)
        (unit 1)
        (exclude_from_sim no)
        (in_bom yes)
        (on_board yes)
        (dnp no)
        (fields_autoplaced yes)
        (uuid "component-uuid-1234")
        (property "Reference" "U1" (at 127 76.2 0))
        (property "Value" "ESP32-WROOM-32" (at 127 78.74 0))
        (property "Footprint" "" (at 127 83.82 0))
        (property "Datasheet" "" (at 127 83.82 0))
    )
    (symbol
        (lib_id "Device:R")
        (at 100 50 0)
        (unit 1)
        (exclude_from_sim no)
        (in_bom yes)
        (on_board yes)
        (dnp no)
        (uuid "resistor-uuid-5678")
        (property "Reference" "R1" (at 100 45 0))
        (property "Value" "10k" (at 100 55 0))
        (property "Footprint" "" (at 100 50 0))
        (property "Datasheet" "" (at 100 50 0))
    )
    (wire (pts (xy 90 50) (xy 100 50)))
    (wire (pts (xy 100 50) (xy 110 50)))
    (junction (at 100 50))
    (label "TEST_SIGNAL" (at 95 50 0))
    (sheet_instances
        (path "/" (page "1"))
    )
)"""


@pytest.fixture
def sample_kicad_project(temp_dir: Path) -> dict[str, Any]:
    """Create a sample KiCad project structure for testing."""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()

    # Create .kicad_pro file
    pro_file = project_dir / "test_project.kicad_pro"
    pro_content = {
        "board": {"3dviewports": [], "design_settings": {}, "layer_presets": [], "viewports": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {
            "erc_exclusions": [],
            "meta": {"version": 0},
            "pin_map": [
                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2],
                [0, 2, 0, 1, 0, 0, 1, 0, 2, 2, 2, 2],
                [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 2],
                [0, 1, 0, 0, 0, 0, 1, 1, 2, 1, 1, 2],
                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
                [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 2],
                [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2],
                [0, 2, 1, 2, 0, 0, 1, 0, 2, 2, 2, 2],
                [0, 2, 0, 1, 0, 0, 1, 0, 2, 0, 0, 2],
                [0, 2, 1, 1, 0, 0, 1, 0, 2, 0, 0, 2],
                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            ],
            "rule_severities": {
                "bus_definition_conflict": "error",
                "bus_entry_needed": "error",
                "bus_to_behavior_mismatch": "error",
                "bus_to_bus_conflict": "error",
                "conflicting_netclasses": "error",
                "different_unit_footprint": "error",
                "different_unit_net": "error",
                "duplicate_reference": "error",
                "duplicate_sheet_names": "error",
                "endpoint_off_grid": "warning",
                "extra_units": "error",
                "global_label_dangling": "warning",
                "hier_label_mismatch": "error",
                "label_dangling": "error",
                "lib_symbol_issues": "warning",
                "missing_bidi_pin": "warning",
                "missing_input_pin": "warning",
                "missing_power_pin": "error",
                "missing_unit": "warning",
                "multiple_net_names": "warning",
                "net_not_bus_member": "warning",
                "no_connect_connected": "warning",
                "no_connect_dangling": "warning",
                "pin_not_connected": "error",
                "pin_not_driven": "error",
                "power_pin_not_driven": "error",
                "similar_labels": "warning",
                "simulation_model_issue": "ignore",
                "unannotated": "error",
                "unit_value_mismatch": "error",
                "unresolved_variable": "error",
                "wire_dangling": "error",
            },
        },
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "test_project.kicad_pro", "version": 1},
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": 0.2,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.25,
                    "via_diameter": 0.8,
                    "via_drill": 0.4,
                    "wire_width": 6,
                }
            ],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [],
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "specctra_dsn": "",
                "step": "",
                "vrml": "",
            },
            "page_layout_descr_file": "",
        },
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {
                "dashed_lines_dash_length_ratio": 12.0,
                "dashed_lines_gap_length_ratio": 3.0,
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "field_names": [],
                "intersheets_ref_own_page": False,
                "intersheets_ref_prefix": "",
                "intersheets_ref_short": False,
                "intersheets_ref_show": False,
                "intersheets_ref_suffix": "",
                "junction_size_choice": 3,
                "label_size_ratio": 0.375,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15,
            },
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "meta": {"version": 1},
            "net_format_name": "",
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_current_sheet_as_root": False,
            "spice_external_command": 'spice "%I"',
            "spice_model_current_sheet_as_root": True,
            "spice_save_all_currents": False,
            "spice_save_all_voltages": False,
            "subpart_first_id": 65,
            "subpart_id_separator": 0,
        },
        "sheets": [["root", ""]],
        "text_variables": {},
    }

    with open(pro_file, "w") as f:
        json.dump(pro_content, f, indent=2)

    # Create empty .kicad_sch file
    sch_file = project_dir / "test_project.kicad_sch"
    sch_file.write_text(f"(kicad_sch (version {KICAD_FILE_FORMAT_VERSION}) (generator eeschema))")
    # Create empty .kicad_pcb file
    pcb_file = project_dir / "test_project.kicad_pcb"
    pcb_file.write_text("(kicad_pcb (version 20221018) (generator pcbnew))")

    return {
        "name": "test_project",
        "path": str(pro_file),
        "directory": str(project_dir),
        "schematic": str(sch_file),
        "pcb": str(pcb_file),
    }


@pytest.fixture
def sample_json_schematic_file(temp_dir: Path, sample_json_schematic: dict[str, Any]) -> Path:
    """Create a sample JSON schematic file for testing."""
    sch_file = temp_dir / "test_schematic.kicad_sch"
    with open(sch_file, "w") as f:
        json.dump(sample_json_schematic, f, indent=2)
    return sch_file


@pytest.fixture
def sample_sexpr_schematic_file(temp_dir: Path, sample_sexpr_schematic: str) -> Path:
    """Create a sample S-expression schematic file for testing."""
    sch_file = temp_dir / "test_schematic_sexpr.kicad_sch"
    sch_file.write_text(sample_sexpr_schematic)
    return sch_file


@pytest.fixture
def mock_kicad_cli():
    """Mock KiCad CLI subprocess calls."""
    from unittest.mock import MagicMock, patch

    def mock_run(*args, **kwargs):
        """Mock subprocess.run behavior."""
        result = MagicMock()
        result.returncode = 0
        result.stdout = "KiCad CLI operation successful"
        result.stderr = ""
        return result

    with patch("subprocess.run", side_effect=mock_run) as mock:
        yield mock


@pytest.fixture
def mock_temp_dir():
    """Mock temporary directory creation."""
    from unittest.mock import MagicMock, patch

    def mock_temp_dir(*args, **kwargs):
        """Mock TempDirManager behavior."""
        temp_manager = MagicMock()
        temp_manager.path = "/tmp/mock_temp_dir"
        temp_manager.__enter__ = MagicMock(return_value=temp_manager)
        temp_manager.__exit__ = MagicMock(return_value=None)
        return temp_manager

    with patch(
        "kicad_mcp.utils.temp_dir_manager.TempDirManager", side_effect=mock_temp_dir
    ) as mock:
        yield mock


# Configure pytest-asyncio
pytest_asyncio.asyncio_mode = "auto"

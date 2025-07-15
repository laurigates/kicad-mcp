"""
Unit tests for file_utils.py - KiCad project file handling utilities.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kicad_mcp.utils.file_utils import get_project_files, load_project_json


class TestFileUtils:
    """Test suite for file utilities."""

    def test_get_project_files_complete_project(self, temp_dir):
        """Test getting files for a complete KiCad project."""
        project_name = "complete_project"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create all standard KiCad files
        files_to_create = {
            f"{project_name}.kicad_pro": "{}",
            f"{project_name}.kicad_sch": "(kicad_sch)",
            f"{project_name}.kicad_pcb": "(kicad_pcb)",
            f"{project_name}.kicad_dru": "",
            f"{project_name}.kicad_wks": "",
            f"{project_name}-bom.csv": "Reference,Value\n",
            f"{project_name}-gerbers.zip": "",
            f"{project_name}.net": "netlist content",
        }

        for filename, content in files_to_create.items():
            (project_dir / filename).write_text(content)

        project_path = str(project_dir / f"{project_name}.kicad_pro")

        # Test function
        result = get_project_files(project_path)

        # Verify all files are found
        assert "project" in result
        assert "schematic" in result
        assert "pcb" in result
        assert result["project"] == project_path
        assert result["schematic"].endswith(".kicad_sch")
        assert result["pcb"].endswith(".kicad_pcb")

        # Check data files
        assert any("bom" in key for key in result)
        assert any("net" in key or "netlist" in key for key in result)

    def test_get_project_files_minimal_project(self, temp_dir):
        """Test getting files for a minimal project (only .kicad_pro file)."""
        project_name = "minimal_project"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create only the project file
        pro_file = project_dir / f"{project_name}.kicad_pro"
        pro_file.write_text("{}")

        project_path = str(pro_file)

        result = get_project_files(project_path)

        # Should only find the project file
        assert len(result) == 1
        assert "project" in result
        assert result["project"] == project_path

    def test_get_project_files_with_schematic_only(self, temp_dir):
        """Test project with only project and schematic files."""
        project_name = "schematic_only"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create project and schematic files
        pro_file = project_dir / f"{project_name}.kicad_pro"
        sch_file = project_dir / f"{project_name}.kicad_sch"

        pro_file.write_text("{}")
        sch_file.write_text("(kicad_sch)")

        project_path = str(pro_file)

        result = get_project_files(project_path)

        assert len(result) == 2
        assert "project" in result
        assert "schematic" in result
        assert result["schematic"] == str(sch_file)

    def test_get_project_files_nonexistent_directory(self):
        """Test error handling for nonexistent project directory."""
        nonexistent_path = "/nonexistent/directory/project.kicad_pro"

        # Should not crash, might return empty or handle gracefully
        result = get_project_files(nonexistent_path)

        # At minimum should include the project file path
        assert "project" in result
        assert result["project"] == nonexistent_path

    def test_get_project_files_data_extensions(self, temp_dir):
        """Test detection of various data file extensions."""
        project_name = "data_project"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create project file
        pro_file = project_dir / f"{project_name}.kicad_pro"
        pro_file.write_text("{}")

        # Create various data files
        data_files = [
            f"{project_name}-bom.csv",
            f"{project_name}-positions.csv",
            f"{project_name}_gerbers.zip",
            f"{project_name}.net",
            f"{project_name}-drc.txt",
            f"{project_name}_fabrication.pdf",
        ]

        for filename in data_files:
            (project_dir / filename).write_text("content")

        project_path = str(pro_file)

        result = get_project_files(project_path)

        # Should find project file plus data files
        assert "project" in result
        assert len(result) > 1

        # Check that data files are categorized
        found_extensions = set()
        for file_path in result.values():
            if file_path != project_path:
                found_extensions.add(Path(file_path).suffix)

        expected_extensions = {".csv", ".zip", ".net", ".txt", ".pdf"}
        assert found_extensions.intersection(expected_extensions)

    def test_get_project_files_with_prefix_variations(self, temp_dir):
        """Test handling of files with different prefix patterns."""
        project_name = "prefix_test"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create project file
        pro_file = project_dir / f"{project_name}.kicad_pro"
        pro_file.write_text("{}")

        # Create files with different prefix patterns
        files = [
            f"{project_name}-bom.csv",  # dash separator
            f"{project_name}_pos.csv",  # underscore separator
            f"{project_name}gerbers.zip",  # no separator
            f"{project_name}.drl",  # direct extension
        ]

        for filename in files:
            (project_dir / filename).write_text("content")

        project_path = str(pro_file)

        result = get_project_files(project_path)

        # Should detect files with various prefix patterns
        assert len(result) > 1

        # Verify specific files are found
        file_paths = list(result.values())
        assert any("bom.csv" in path for path in file_paths)
        assert any("pos.csv" in path for path in file_paths)
        assert any("gerbers.zip" in path for path in file_paths)
        assert any(".drl" in path for path in file_paths)

    def test_load_project_json_valid_file(self, temp_dir):
        """Test loading a valid KiCad project JSON file."""
        project_data = {
            "board": {"design_settings": {}},
            "meta": {"filename": "test.kicad_pro", "version": 1},
            "schematic": {"annotate_start_num": 0},
        }

        project_file = temp_dir / "test.kicad_pro"
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        result = load_project_json(str(project_file))

        assert result is not None
        assert isinstance(result, dict)
        assert result["meta"]["filename"] == "test.kicad_pro"
        assert result["meta"]["version"] == 1
        assert "board" in result
        assert "schematic" in result

    def test_load_project_json_file_not_found(self):
        """Test error handling when project file doesn't exist."""
        result = load_project_json("/nonexistent/project.kicad_pro")

        assert result is None

    def test_load_project_json_invalid_json(self, temp_dir):
        """Test error handling with malformed JSON."""
        project_file = temp_dir / "invalid.kicad_pro"
        project_file.write_text("{ invalid json content }")

        result = load_project_json(str(project_file))

        assert result is None

    def test_load_project_json_empty_file(self, temp_dir):
        """Test handling of empty project file."""
        project_file = temp_dir / "empty.kicad_pro"
        project_file.write_text("")

        result = load_project_json(str(project_file))

        assert result is None

    def test_load_project_json_permission_error(self, temp_dir):
        """Test handling of permission errors."""
        project_file = temp_dir / "restricted.kicad_pro"
        project_file.write_text("{}")

        # Mock permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = load_project_json(str(project_file))

            assert result is None

    @patch("kicad_mcp.utils.file_utils.get_project_name_from_path")
    def test_get_project_files_name_extraction(self, mock_get_name, temp_dir):
        """Test that project name extraction is called correctly."""
        mock_get_name.return_value = "extracted_name"

        project_path = str(temp_dir / "test.kicad_pro")

        # Create a basic project file
        Path(project_path).write_text("{}")

        result = get_project_files(project_path)

        # Verify the name extraction function was called
        mock_get_name.assert_called_once_with(project_path)
        assert "project" in result

    def test_get_project_files_case_sensitivity(self, temp_dir):
        """Test handling of different case patterns in filenames."""
        project_name = "CaseTest"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create project file
        pro_file = project_dir / f"{project_name}.kicad_pro"
        pro_file.write_text("{}")

        # Create files with different cases
        files = [
            f"{project_name}.KICAD_SCH",  # uppercase extension
            f"{project_name.lower()}.kicad_pcb",  # lowercase name
            f"{project_name}-BOM.CSV",  # mixed case
        ]

        for filename in files:
            (project_dir / filename).write_text("content")

        project_path = str(pro_file)

        result = get_project_files(project_path)

        # Should find the project file at minimum
        assert "project" in result
        # Note: Case sensitivity behavior depends on filesystem

    def test_get_project_files_symlinks(self, temp_dir):
        """Test handling of symbolic links in project directory."""
        project_name = "symlink_test"
        project_dir = temp_dir / project_name
        project_dir.mkdir()

        # Create project file
        pro_file = project_dir / f"{project_name}.kicad_pro"
        pro_file.write_text("{}")

        # Create a real file and a symlink to it
        real_file = project_dir / "real_schematic.kicad_sch"
        real_file.write_text("(kicad_sch)")

        symlink_file = project_dir / f"{project_name}.kicad_sch"
        try:
            symlink_file.symlink_to(real_file)
        except OSError:
            # Skip test if symlinks aren't supported
            pytest.skip("Symbolic links not supported on this system")

        project_path = str(pro_file)

        result = get_project_files(project_path)

        assert "project" in result
        assert "schematic" in result
        assert result["schematic"] == str(symlink_file)

    def test_load_project_json_with_unicode(self, temp_dir):
        """Test loading project files with unicode characters."""
        project_data = {
            "meta": {
                "filename": "tëst_ünïcødé.kicad_pro",
                "version": 1,
                "description": "Prøject with ünïcødé characters",
            }
        }

        project_file = temp_dir / "unicode_test.kicad_pro"
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False)

        result = load_project_json(str(project_file))

        assert result is not None
        assert result["meta"]["filename"] == "tëst_ünïcødé.kicad_pro"
        assert "ünïcødé" in result["meta"]["description"]

    @patch("os.listdir")
    @patch("os.path.exists")
    def test_get_project_files_os_error_handling(self, mock_exists, mock_listdir):
        """Test handling of OS errors during file discovery."""
        mock_exists.side_effect = lambda path: path.endswith(".kicad_pro")
        mock_listdir.side_effect = OSError("Permission denied")

        # Should handle the error gracefully
        result = get_project_files("/test/project.kicad_pro")

        # Should at least return the project file
        assert "project" in result
        assert result["project"] == "/test/project.kicad_pro"

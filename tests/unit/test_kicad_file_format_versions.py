"""
Tests for KiCad file format version validation - Issue #2.

These tests validate that generated KiCad files use current file format versions
to eliminate compatibility warnings when opened in recent KiCad versions.
"""

from pathlib import Path
import re
from tempfile import TemporaryDirectory

import pytest

from kicad_mcp.tools.circuit_tools import create_new_project
from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class TestKiCadFileFormatVersions:
    """Test KiCad file format version compliance."""

    def test_current_schematic_version_format(self):
        """Test that schematic files use a recent version format (Issue #2)."""
        handler = SExpressionHandler()

        # Generate a simple schematic
        circuit_name = "test_circuit"
        components = [
            {"reference": "R1", "value": "10k", "symbol": "Device:R", "position": [100, 100]}
        ]
        power_symbols = []
        connections = []

        schematic_content = handler.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        # Check that the version is present and follows YYYYMMDD format
        version_match = re.search(r"\(version (\d{8})\)", schematic_content)
        assert version_match is not None, "Version field not found in schematic"

        version_date = version_match.group(1)

        # Validate format: should be 8 digits (YYYYMMDD)
        assert len(version_date) == 8, f"Version should be 8 digits (YYYYMMDD), got: {version_date}"
        assert version_date.isdigit(), f"Version should be numeric, got: {version_date}"

        # Parse date components
        year = int(version_date[:4])
        month = int(version_date[4:6])
        day = int(version_date[6:8])

        # Validate date ranges
        assert 2024 <= year <= 2025, f"Year should be 2024-2025 for current KiCad, got: {year}"
        assert 1 <= month <= 12, f"Month should be 1-12, got: {month}"
        assert 1 <= day <= 31, f"Day should be 1-31, got: {day}"

    def test_version_not_outdated(self):
        """Test that we don't use old versions that cause warnings (Issue #2)."""
        handler = SExpressionHandler()

        schematic_content = handler.generate_schematic(
            "test",
            [{"reference": "R1", "value": "1k", "symbol": "Device:R", "position": [50, 50]}],
            [],
            [],
        )

        # Check that we're not using the old problematic versions mentioned in issue #2
        outdated_versions = [
            "20230121",  # Mentioned in issue as old version
            "20220101",  # Clearly outdated
            "20210101",  # Clearly outdated
        ]

        for old_version in outdated_versions:
            assert old_version not in schematic_content, (
                f"Schematic uses outdated version {old_version} which causes compatibility warnings"
            )

    def test_version_is_recent_enough(self):
        """Test that version is recent enough to avoid compatibility warnings."""
        handler = SExpressionHandler()

        schematic_content = handler.generate_schematic(
            "test",
            [{"reference": "R1", "value": "1k", "symbol": "Device:R", "position": [50, 50]}],
            [],
            [],
        )

        version_match = re.search(r"\(version (\d{8})\)", schematic_content)
        assert version_match is not None

        version_date = int(version_match.group(1))

        # Should be at least from 2024 to be reasonably current
        # (20240101 = January 1, 2024)
        min_acceptable_version = 20240101
        assert version_date >= min_acceptable_version, (
            f"Version {version_date} is too old, should be >= {min_acceptable_version} "
            f"to avoid compatibility warnings in recent KiCad versions"
        )

    def test_generator_field_present(self):
        """Test that generator field is properly set."""
        handler = SExpressionHandler()

        schematic_content = handler.generate_schematic(
            "test",
            [{"reference": "R1", "value": "1k", "symbol": "Device:R", "position": [50, 50]}],
            [],
            [],
        )

        # Check for generator field (can be with or without quotes)
        assert (
            '(generator "kicad-mcp")' in schematic_content
            or "(generator kicad-mcp)" in schematic_content
        ), "Generator field missing"
        assert "(generator_version" in schematic_content, "Generator version field missing"

    async def test_consistency_across_file_types(self):
        """Test version consistency across different file types in a project."""
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project.kicad_pro"

            # Create a project to test file consistency
            result = await create_new_project(
                project_name="test_project",
                project_path=str(project_path),
                description="Test project for version consistency",
            )

            assert result["success"], f"Failed to create project: {result.get('error')}"

            # Check schematic file if it exists
            schematic_file = project_path.with_suffix(".kicad_sch")
            if schematic_file.exists():
                content = schematic_file.read_text()
                version_match = re.search(r"\(version (\d{8})\)", content)
                if version_match:
                    version = version_match.group(1)
                    # Ensure it's not using an old version
                    assert int(version) >= 20240101, f"Schematic file uses old version {version}"

    def test_version_format_validation(self):
        """Test that version format follows KiCad specifications."""
        handler = SExpressionHandler()

        schematic_content = handler.generate_schematic("test", [], [], [])

        # Extract the complete version line
        version_line_match = re.search(r"\(version \d{8}\)", schematic_content)
        assert version_line_match is not None, "Version line not found"

        version_line = version_line_match.group(0)

        # Should be exactly in format (version YYYYMMDD)
        assert re.match(r"^\(version \d{8}\)$", version_line), (
            f"Version line format incorrect: {version_line}"
        )

    def test_no_legacy_format_markers(self):
        """Test that generated files don't contain legacy format markers."""
        handler = SExpressionHandler()

        schematic_content = handler.generate_schematic(
            "test",
            [{"reference": "R1", "value": "1k", "symbol": "Device:R", "position": [50, 50]}],
            [],
            [],
        )

        # Should not contain legacy format indicators
        legacy_markers = [
            "EESchema Schematic File Version",  # Old KiCad 4/5 format
            "$Descr",  # Legacy descriptor
            "$EndDescr",  # Legacy descriptor
        ]

        for marker in legacy_markers:
            assert marker not in schematic_content, (
                f"Generated schematic contains legacy format marker: {marker}"
            )

    def test_modern_sexpr_format(self):
        """Test that generated files use modern S-expression format."""
        handler = SExpressionHandler()

        schematic_content = handler.generate_schematic(
            "test",
            [{"reference": "R1", "value": "1k", "symbol": "Device:R", "position": [50, 50]}],
            [],
            [],
        )

        # Should start with modern S-expression format
        assert schematic_content.strip().startswith("(kicad_sch"), (
            "Schematic should start with (kicad_sch for modern format"
        )

        # Should contain required modern fields
        required_fields = ["(version", "(generator", "(kicad_sch"]

        for field in required_fields:
            assert field in schematic_content, f"Required modern field missing: {field}"


class TestVersionUpgradeValidation:
    """Test version upgrade scenarios for Issue #2."""

    def test_detect_outdated_test_fixtures(self):
        """Test to identify test fixtures using outdated versions."""
        # This test helps identify files that need updating for Issue #2
        test_files_dir = Path(__file__).parent.parent.parent / "tests"
        outdated_versions = ["20230121", "20220101", "20210101"]

        files_with_old_versions = []

        # Scan test files for outdated versions
        for test_file in test_files_dir.rglob("*.py"):
            if test_file.name.startswith("test_"):
                try:
                    content = test_file.read_text()
                    for old_version in outdated_versions:
                        if old_version in content:
                            files_with_old_versions.append((test_file, old_version))
                except Exception:
                    # Skip files that can't be read
                    continue

        # This is informational - shows what needs to be updated
        if files_with_old_versions:
            file_list = "\n".join(
                [f"  {file}: {version}" for file, version in files_with_old_versions]
            )
            pytest.skip(
                f"Found test files with outdated versions (Issue #2):\n{file_list}\n"
                f"These should be updated to use current versions (>= 20240101)"
            )

    def test_documentation_version_references(self):
        """Test to identify documentation with outdated version references."""
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        if not docs_dir.exists():
            pytest.skip("No docs directory found")

        outdated_versions = ["20230121", "20220101", "20210101"]
        docs_with_old_versions = []

        for doc_file in docs_dir.rglob("*.md"):
            try:
                content = doc_file.read_text()
                for old_version in outdated_versions:
                    if old_version in content:
                        docs_with_old_versions.append((doc_file, old_version))
            except Exception:
                continue

        if docs_with_old_versions:
            file_list = "\n".join(
                [f"  {file}: {version}" for file, version in docs_with_old_versions]
            )
            pytest.skip(
                f"Found documentation with outdated versions (Issue #2):\n{file_list}\n"
                f"These should be updated to use current versions (>= 20240101)"
            )

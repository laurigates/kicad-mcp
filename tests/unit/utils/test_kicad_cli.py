"""
Tests for KiCad CLI detection utility.
"""

import os
import platform
from unittest.mock import MagicMock, patch

import pytest

from kicad_mcp.utils.kicad_cli import (
    KiCadCLIError,
    KiCadCLIManager,
    find_kicad_cli,
    get_kicad_cli_path,
    get_kicad_version,
    is_kicad_cli_available,
)


class TestKiCadCLIManager:
    """Test cases for KiCadCLIManager class."""

    def test_init(self):
        """Test CLI manager initialization."""
        manager = KiCadCLIManager()
        assert manager._cached_cli_path is None
        assert manager._cache_validated is False
        assert manager._system == platform.system()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_find_kicad_cli_in_path(self, mock_run, mock_which):
        """Test finding KiCad CLI in system PATH."""
        mock_which.return_value = "/usr/bin/kicad-cli"
        mock_run.return_value = MagicMock(returncode=0, stdout="KiCad CLI")

        manager = KiCadCLIManager()
        result = manager.find_kicad_cli()

        assert result == "/usr/bin/kicad-cli"
        assert manager._cached_cli_path == "/usr/bin/kicad-cli"
        assert manager._cache_validated is True

    @patch.dict(os.environ, {"KICAD_CLI_PATH": "/custom/kicad-cli"})
    @patch("os.path.isfile")
    @patch("os.access")
    @patch("subprocess.run")
    def test_find_kicad_cli_from_env(self, mock_run, mock_access, mock_isfile):
        """Test finding KiCad CLI from environment variable."""
        mock_isfile.return_value = True
        mock_access.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="KiCad CLI")

        manager = KiCadCLIManager()
        result = manager.find_kicad_cli()

        assert result == "/custom/kicad-cli"

    @patch("os.path.isfile")
    @patch("os.access")
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_find_kicad_cli_common_location(self, mock_which, mock_run, mock_access, mock_isfile):
        """Test finding KiCad CLI in common installation location."""
        mock_which.return_value = None  # Not in PATH
        mock_isfile.return_value = True
        mock_access.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="KiCad CLI")

        manager = KiCadCLIManager()

        # Mock platform-specific behavior
        with patch.object(manager, "_system", "Linux"):
            result = manager.find_kicad_cli()
            assert result == "/usr/bin/kicad-cli"

    @patch("shutil.which")
    @patch("os.path.isfile")
    def test_find_kicad_cli_not_found(self, mock_isfile, mock_which):
        """Test CLI not found."""
        mock_which.return_value = None
        mock_isfile.return_value = False

        manager = KiCadCLIManager()
        result = manager.find_kicad_cli()

        assert result is None
        assert manager._cached_cli_path is None
        assert manager._cache_validated is False

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_find_kicad_cli_validation_fails(self, mock_run, mock_which):
        """Test CLI found but validation fails."""
        mock_which.return_value = "/usr/bin/kicad-cli"
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        manager = KiCadCLIManager()
        result = manager.find_kicad_cli()

        assert result is None

    def test_find_kicad_cli_caching(self):
        """Test CLI path caching."""
        manager = KiCadCLIManager()
        manager._cached_cli_path = "/cached/kicad-cli"
        manager._cache_validated = True

        # Should return cached path without detection
        result = manager.find_kicad_cli()
        assert result == "/cached/kicad-cli"

    def test_find_kicad_cli_force_refresh(self):
        """Test force refresh bypasses cache."""
        manager = KiCadCLIManager()
        manager._cached_cli_path = "/cached/kicad-cli"
        manager._cache_validated = True

        with patch.object(manager, "_detect_cli_path", return_value=None):
            result = manager.find_kicad_cli(force_refresh=True)
            assert result is None
            assert manager._cached_cli_path is None

    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_get_cli_path_success(self, mock_find):
        """Test successful CLI path retrieval."""
        mock_find.return_value = "/usr/bin/kicad-cli"

        manager = KiCadCLIManager()
        result = manager.get_cli_path()

        assert result == "/usr/bin/kicad-cli"

    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_get_cli_path_required_not_found(self, mock_find):
        """Test CLI path retrieval when required but not found."""
        mock_find.return_value = None

        manager = KiCadCLIManager()

        with pytest.raises(KiCadCLIError, match="KiCad CLI not found"):
            manager.get_cli_path(required=True)

    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_get_cli_path_not_required_not_found(self, mock_find):
        """Test CLI path retrieval when not required and not found."""
        mock_find.return_value = None

        manager = KiCadCLIManager()
        result = manager.get_cli_path(required=False)

        assert result is None

    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_is_available(self, mock_find):
        """Test availability check."""
        mock_find.return_value = "/usr/bin/kicad-cli"

        manager = KiCadCLIManager()
        assert manager.is_available() is True

        mock_find.return_value = None
        assert manager.is_available() is False

    @patch("subprocess.run")
    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_get_version_success(self, mock_find, mock_run):
        """Test successful version retrieval."""
        mock_find.return_value = "/usr/bin/kicad-cli"
        mock_run.return_value = MagicMock(returncode=0, stdout="KiCad CLI 6.0.0")

        manager = KiCadCLIManager()
        version = manager.get_version()

        assert version == "KiCad CLI 6.0.0"

    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_get_version_cli_not_found(self, mock_find):
        """Test version retrieval when CLI not found."""
        mock_find.return_value = None

        manager = KiCadCLIManager()
        version = manager.get_version()

        assert version is None

    @patch("subprocess.run")
    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_get_version_command_fails(self, mock_find, mock_run):
        """Test version retrieval when command fails."""
        mock_find.return_value = "/usr/bin/kicad-cli"
        mock_run.side_effect = OSError("Command failed")

        manager = KiCadCLIManager()
        version = manager.get_version()

        assert version is None

    def test_get_cli_executable_name_windows(self):
        """Test CLI executable name on Windows."""
        manager = KiCadCLIManager()
        manager._system = "Windows"

        assert manager._get_cli_executable_name() == "kicad-cli.exe"

    def test_get_cli_executable_name_unix(self):
        """Test CLI executable name on Unix-like systems."""
        manager = KiCadCLIManager()
        manager._system = "Linux"

        assert manager._get_cli_executable_name() == "kicad-cli"

    def test_get_common_installation_paths_macos(self):
        """Test common installation paths on macOS."""
        manager = KiCadCLIManager()
        manager._system = "Darwin"

        paths = manager._get_common_installation_paths()
        assert "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli" in paths

    def test_get_common_installation_paths_windows(self):
        """Test common installation paths on Windows."""
        manager = KiCadCLIManager()
        manager._system = "Windows"

        paths = manager._get_common_installation_paths()
        assert r"C:\Program Files\KiCad\bin\kicad-cli.exe" in paths

    def test_get_common_installation_paths_linux(self):
        """Test common installation paths on Linux."""
        manager = KiCadCLIManager()
        manager._system = "Linux"

        paths = manager._get_common_installation_paths()
        assert "/usr/bin/kicad-cli" in paths


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch.object(KiCadCLIManager, "find_kicad_cli")
    def test_find_kicad_cli_convenience(self, mock_find):
        """Test find_kicad_cli convenience function."""
        mock_find.return_value = "/usr/bin/kicad-cli"

        result = find_kicad_cli()
        assert result == "/usr/bin/kicad-cli"

    @patch.object(KiCadCLIManager, "get_cli_path")
    def test_get_kicad_cli_path_convenience(self, mock_get_path):
        """Test get_kicad_cli_path convenience function."""
        mock_get_path.return_value = "/usr/bin/kicad-cli"

        result = get_kicad_cli_path()
        assert result == "/usr/bin/kicad-cli"

    @patch.object(KiCadCLIManager, "is_available")
    def test_is_kicad_cli_available_convenience(self, mock_available):
        """Test is_kicad_cli_available convenience function."""
        mock_available.return_value = True

        result = is_kicad_cli_available()
        assert result is True

    @patch.object(KiCadCLIManager, "get_version")
    def test_get_kicad_version_convenience(self, mock_version):
        """Test get_kicad_version convenience function."""
        mock_version.return_value = "KiCad CLI 6.0.0"

        result = get_kicad_version()
        assert result == "KiCad CLI 6.0.0"

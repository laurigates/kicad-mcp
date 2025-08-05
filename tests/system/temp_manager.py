"""
Temporary directory management for HTTP tests.

Provides test isolation through temporary directories with automatic cleanup.
"""

from contextlib import suppress
import os
from pathlib import Path
import shutil
import signal
import tempfile
from typing import Any


class TempDirectoryManager:
    """Manages temporary directories for test isolation."""

    def __init__(self):
        """Initialize temporary directory manager."""
        self._temp_dirs: list[str] = []
        self._cleanup_registered = False

    def create_temp_dir(self, prefix: str = "kicad_mcp_test_") -> str:
        """Create a new temporary directory.

        Args:
            prefix: Prefix for the temporary directory name

        Returns:
            Path to the created temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self._temp_dirs.append(temp_dir)

        # Register cleanup handlers on first use
        if not self._cleanup_registered:
            self._register_cleanup_handlers()
            self._cleanup_registered = True

        return temp_dir

    def substitute_templates(self, text: str, temp_dir: str) -> str:
        """Substitute template variables in text.

        Args:
            text: Text containing template variables
            temp_dir: Temporary directory path for substitution

        Returns:
            Text with variables substituted
        """
        return text.replace("{temp_dir}", temp_dir)

    def substitute_dict_templates(self, data: dict[str, Any], temp_dir: str) -> dict[str, Any]:
        """Recursively substitute template variables in dictionary.

        Args:
            data: Dictionary containing template variables
            temp_dir: Temporary directory path for substitution

        Returns:
            Dictionary with variables substituted
        """
        if isinstance(data, dict):
            return {
                key: self.substitute_dict_templates(value, temp_dir) for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self.substitute_dict_templates(item, temp_dir) for item in data]
        elif isinstance(data, str):
            return self.substitute_templates(data, temp_dir)
        else:
            return data

    def cleanup_temp_dirs(self) -> None:
        """Clean up all tracked temporary directories."""
        for temp_dir in self._temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Error cleaning up {temp_dir}: {e}")

        self._temp_dirs.clear()

    def _register_cleanup_handlers(self) -> None:
        """Register signal handlers for cleanup on interruption."""

        def signal_handler(signum: int, frame: Any) -> None:
            """Handle signals by cleaning up and exiting."""
            print(f"\nReceived signal {signum}, cleaning up...")
            self.cleanup_temp_dirs()
            exit(1)

        # Register for common termination signals
        for sig in (signal.SIGINT, signal.SIGTERM):
            with suppress(ValueError, AttributeError):
                # Some signals may not be available on all platforms
                signal.signal(sig, signal_handler)

    def __enter__(self) -> "TempDirectoryManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        self.cleanup_temp_dirs()


def validate_project_structure(project_path: str) -> dict[str, bool]:
    """Validate basic KiCad project file structure.

    Args:
        project_path: Path to project directory

    Returns:
        Dictionary mapping file types to existence status
    """
    project_dir = Path(project_path)
    project_name = project_dir.stem

    expected_files = {
        "kicad_pro": project_dir / f"{project_name}.kicad_pro",
        "kicad_sch": project_dir / f"{project_name}.kicad_sch",
        "kicad_pcb": project_dir / f"{project_name}.kicad_pcb",
    }

    return {file_type: file_path.exists() for file_type, file_path in expected_files.items()}


def ensure_directory_exists(path: str) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists
    """
    Path(path).mkdir(parents=True, exist_ok=True)

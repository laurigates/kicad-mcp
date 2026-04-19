"""Utility functions for detecting and selecting available KiCad API approaches.

Checks for a working ``kicad-cli`` binary in PATH or common install locations.
"""

import logging
import os
import shutil

from kicad_mcp.config import system
from kicad_mcp.utils.secure_subprocess import SecureSubprocessError, get_subprocess_runner

logger = logging.getLogger(__name__)


def check_for_cli_api() -> bool:
    """Check if KiCad CLI API is available.

    Returns:
        True if KiCad CLI is available, False otherwise
    """
    try:
        # Check if kicad-cli is in PATH
        if system == "Windows":
            # On Windows, check for kicad-cli.exe
            kicad_cli = shutil.which("kicad-cli.exe")
        else:
            # On Unix-like systems
            kicad_cli = shutil.which("kicad-cli")

        if kicad_cli:
            # Verify it's a working kicad-cli
            try:
                runner = get_subprocess_runner()
                result = runner.run_safe_command(
                    [kicad_cli, "--version"],
                    allowed_commands=[kicad_cli],
                )
                if result.returncode == 0:
                    logger.info("Found working kicad-cli: %s", kicad_cli)
                    return True
            except SecureSubprocessError:
                pass

        # Check common installation locations if not found in PATH
        if system == "Windows":
            # Common Windows installation paths
            potential_paths = [
                r"C:\Program Files\KiCad\bin\kicad-cli.exe",
                r"C:\Program Files (x86)\KiCad\bin\kicad-cli.exe",
            ]
        elif system == "Darwin":  # macOS
            # Common macOS installation paths
            potential_paths = [
                "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
                "/Applications/KiCad/kicad-cli",
            ]
        else:  # Linux
            # Common Linux installation paths
            potential_paths = [
                "/usr/bin/kicad-cli",
                "/usr/local/bin/kicad-cli",
                "/opt/kicad/bin/kicad-cli",
            ]

        # Check each potential path
        for path in potential_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                logger.info("Found kicad-cli at common location: %s", path)
                return True

        logger.info("KiCad CLI API is not available")
        return False

    except OSError as e:
        logger.error("Error checking for KiCad CLI API: %s", e)
        return False

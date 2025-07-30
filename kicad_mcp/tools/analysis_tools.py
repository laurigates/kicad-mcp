"""
Analysis and validation tools for KiCad projects.

This module provides utility functions that can be registered with the FastMCP
server to analyze and validate the structure and contents of KiCad projects.

Functions:
    - register_analysis_tools: Registers analysis functions like project validation.

Usage:
    This module is intended to be used by the MCP server via tool registration.
"""

import os
from typing import Any

from fastmcp import FastMCP

from kicad_mcp.utils.file_utils import get_project_files


def register_analysis_tools(mcp: FastMCP) -> None:
    """
    Register analysis and validation tools with the MCP server.

    Args:
        mcp (FastMCP): The FastMCP server instance.

    Returns:
        None
    """

    @mcp.tool()
    def validate_project(project_path: str) -> dict[str, Any]:
        """
        Perform basic validation of a KiCad project directory.

        This tool checks whether the provided project directory exists,
        and whether it contains expected KiCad files like PCB and schematic.

        It also attempts to open and parse the main project file to ensure
        it's in valid JSON format.

        Args:
            project_path (str): Path to the KiCad project file (usually `.kicad_pro`).

        Returns:
            dict[str, Any]: A dictionary containing:
                - valid (bool): Whether the project is considered valid.
                - path (str): The path of the project.
                - issues (list[str] | None): List of issues found, or None if valid.
                - files_found (list[str]): Keys of detected project files.

        Raises:
            This function handles exceptions internally and does not raise errors.

        Time Complexity:
            O(n) where n is the number of files in the project directory.
        """
        if not os.path.exists(project_path):
            return {"valid": False, "error": f"Project not found: {project_path}"}

        issues = []
        files = get_project_files(project_path)

        # Check for essential files
        if "pcb" not in files:
            issues.append("Missing PCB layout file")

        if "schematic" not in files:
            issues.append("Missing schematic file")

        # Validate project file format
        try:
            with open(project_path) as f:
                import json

                json.load(f)
        except json.JSONDecodeError:
            issues.append("Invalid project file format (JSON parsing error)")
        except Exception as e:
            issues.append(f"Error reading project file: {str(e)}")

        return {
            "valid": len(issues) == 0,
            "path": project_path,
            "issues": issues if issues else None,
            "files_found": list(files.keys()),
        }

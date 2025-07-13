"""
Project management tools for KiCad.
"""

import logging
import os
from typing import Any

from fastmcp import FastMCP

from kicad_mcp.utils.file_utils import get_project_files, load_project_json
from kicad_mcp.utils.kicad_utils import (
    find_kicad_projects,
    find_kicad_projects_in_dirs,
    open_kicad_project,
)

# Get PID for logging
# _PID = os.getpid()


def register_project_tools(mcp: FastMCP) -> None:
    """Register project management tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """

    @mcp.tool()
    def list_projects(search_directories: list[str] = None) -> list[dict[str, Any]]:
        """Find and list all KiCad projects on this system.

        Args:
            search_directories: Optional list of directories to search. If None, uses default system directories.
        """
        logging.info("Executing list_projects tool...")
        if search_directories:
            projects = find_kicad_projects_in_dirs(search_directories)
        else:
            projects = find_kicad_projects()
        logging.info(f"list_projects tool returning {len(projects)} projects.")
        return projects

    @mcp.tool()
    def get_project_structure(project_path: str) -> dict[str, Any]:
        """Get the structure and files of a KiCad project."""
        if not os.path.exists(project_path):
            return {"error": f"Project not found: {project_path}"}

        project_dir = os.path.dirname(project_path)
        project_name = os.path.basename(project_path)[:-10]  # Remove .kicad_pro extension

        # Get related files
        files = get_project_files(project_path)

        # Get project metadata
        metadata = {}
        project_data = load_project_json(project_path)
        if project_data and "metadata" in project_data:
            metadata = project_data["metadata"]

        return {
            "name": project_name,
            "path": project_path,
            "directory": project_dir,
            "files": files,
            "metadata": metadata,
        }

    @mcp.tool()
    def open_project(project_path: str) -> dict[str, Any]:
        """Open a KiCad project in KiCad."""
        return open_kicad_project(project_path)

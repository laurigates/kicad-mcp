"""
Project management tools for KiCad.
"""
import os
import logging
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP

from kicad_mcp.utils.kicad_utils import find_kicad_projects, open_kicad_project
from kicad_mcp.utils.file_utils import get_project_files, load_project_json

# Get PID for logging
# _PID = os.getpid()

def register_project_tools(mcp: FastMCP) -> None:
    """Register project management tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def list_projects() -> List[Dict[str, Any]]:
        """Find and list all KiCad projects on this system."""
        logging.info(f"Executing list_projects tool...")
        projects = find_kicad_projects()
        logging.info(f"list_projects tool returning {len(projects)} projects.")
        return projects

    @mcp.tool()
    def get_project_structure(project_path: str) -> Dict[str, Any]:
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
            "metadata": metadata
        }

    @mcp.tool()
    def open_project(project_path: str) -> Dict[str, Any]:
        """Open a KiCad project in KiCad."""
        return open_kicad_project(project_path)

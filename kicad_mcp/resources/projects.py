"""
Project listing and information resources.
"""
import os
from mcp.server.fastmcp import FastMCP

from kicad_mcp.utils.kicad_utils import find_kicad_projects
from kicad_mcp.utils.file_utils import get_project_files, load_project_json


def register_project_resources(mcp: FastMCP) -> None:
    """Register project-related resources with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.resource("kicad://projects")
    def list_projects_resource() -> str:
        """List all KiCad projects as a formatted resource."""
        projects = find_kicad_projects()
        
        if not projects:
            return "No KiCad projects found in your Documents/KiCad directory."
        
        result = "# KiCad Projects\n\n"
        for project in sorted(projects, key=lambda p: p["modified"], reverse=True):
            result += f"## {project['name']}\n"
            result += f"- **Path**: {project['path']}\n"
            result += f"- **Last Modified**: {os.path.getmtime(project['path'])}\n\n"
        
        return result

    @mcp.resource("kicad://project/{project_path}")
    def get_project_details(project_path: str) -> str:
        """Get details about a specific KiCad project."""
        if not os.path.exists(project_path):
            return f"Project not found: {project_path}"
        
        try:
            # Load project file
            project_data = load_project_json(project_path)
            if not project_data:
                return f"Error reading project file: {project_path}"
            
            # Get related files
            files = get_project_files(project_path)
            
            # Format project details
            result = f"# Project: {os.path.basename(project_path)[:-10]}\n\n"
            
            result += "## Project Files\n"
            for file_type, file_path in files.items():
                result += f"- **{file_type}**: {file_path}\n"
            
            result += "\n## Project Settings\n"
            
            # Extract metadata
            if "metadata" in project_data:
                metadata = project_data["metadata"]
                for key, value in metadata.items():
                    result += f"- **{key}**: {value}\n"
            
            return result
        
        except Exception as e:
            return f"Error reading project file: {str(e)}"

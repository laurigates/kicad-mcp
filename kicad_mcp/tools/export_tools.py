"""
Export and file generation tools for KiCad projects.
"""
import os
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.kicad_utils import get_project_name_from_path


def register_export_tools(mcp: FastMCP) -> None:
    """Register export and file generation tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    def extract_bom(project_path: str) -> Dict[str, Any]:
        """Extract a Bill of Materials (BOM) from a KiCad project."""
        if not os.path.exists(project_path):
            return {"success": False, "error": f"Project not found: {project_path}"}
        
        project_dir = os.path.dirname(project_path)
        project_name = get_project_name_from_path(project_path)
        
        # Look for existing BOM files
        bom_files = []
        for file in os.listdir(project_dir):
            if file.startswith(project_name) and file.endswith('.csv') and 'bom' in file.lower():
                bom_files.append(os.path.join(project_dir, file))
        
        if not bom_files:
            return {
                "success": False, 
                "error": "No BOM files found. You need to generate a BOM using KiCad first."
            }
        
        try:
            # Read the first BOM file
            bom_path = bom_files[0]
            with open(bom_path, 'r') as f:
                bom_content = f.read()
            
            # Parse CSV (simplified)
            lines = bom_content.strip().split('\n')
            headers = lines[0].split(',')
            
            components = []
            for line in lines[1:]:
                values = line.split(',')
                if len(values) >= len(headers):
                    component = {}
                    for i, header in enumerate(headers):
                        component[header.strip()] = values[i].strip()
                    components.append(component)
            
            return {
                "success": True,
                "bom_file": bom_path,
                "headers": headers,
                "component_count": len(components),
                "components": components
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}

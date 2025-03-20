#!/usr/bin/env python3
"""
KiCad MCP Server - A Model Context Protocol server for KiCad on macOS.
This server allows Claude and other MCP clients to interact with KiCad projects.
"""
from typing import Dict, List, Any, Tuple, Optional
import os
import json
import subprocess
import asyncio
from pathlib import Path
from mcp.server.fastmcp import FastMCP, Context, Image

# Initialize FastMCP server
mcp = FastMCP("KiCad")

# Constants
KICAD_USER_DIR = os.path.expanduser("~/Documents/KiCad")
KICAD_APP_PATH = "/Applications/KiCad/KiCad.app"

# Helper functions
def find_kicad_projects() -> List[Dict[str, Any]]:
    """Find KiCad projects in the user's directory."""
    projects = []
    
    for root, _, files in os.walk(KICAD_USER_DIR):
        for file in files:
            if file.endswith(".kicad_pro"):
                project_path = os.path.join(root, file)
                rel_path = os.path.relpath(project_path, KICAD_USER_DIR)
                project_name = file[:-10]  # Remove .kicad_pro extension
                
                projects.append({
                    "name": project_name,
                    "path": project_path,
                    "relative_path": rel_path,
                    "modified": os.path.getmtime(project_path)
                })
    
    return projects

def get_project_files(project_path: str) -> Dict[str, str]:
    """Get all files related to a KiCad project."""
    project_dir = os.path.dirname(project_path)
    project_name = os.path.basename(project_path)[:-10]  # Remove .kicad_pro
    
    files = {}
    extensions = [
        ".kicad_pcb",      # PCB layout
        ".kicad_sch",      # Schematic
        ".kicad_dru",      # Design rules
        ".kibot.yaml",     # KiBot configuration
        ".kicad_wks",      # Worksheet template
        ".kicad_mod",      # Footprint module
        "_netlist.net",    # Netlist
        ".csv",            # BOM or other data
        ".pos",            # Component position file
    ]
    
    for ext in extensions:
        file_path = os.path.join(project_dir, f"{project_name}{ext}")
        if os.path.exists(file_path):
            files[ext[1:]] = file_path  # Remove leading dot from extension
    
    return files

# Resources
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
        with open(project_path, 'r') as f:
            project_data = json.load(f)
        
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

@mcp.resource("kicad://schematic/{schematic_path}")
def get_schematic_info(schematic_path: str) -> str:
    """Extract information from a KiCad schematic file."""
    if not os.path.exists(schematic_path):
        return f"Schematic file not found: {schematic_path}"
    
    # KiCad schematic files are in S-expression format (not JSON)
    # This is a basic extraction of text-based information
    try:
        with open(schematic_path, 'r') as f:
            content = f.read()
        
        # Basic extraction of components
        components = []
        for line in content.split('\n'):
            if '(symbol ' in line and 'lib_id' in line:
                components.append(line.strip())
        
        result = f"# Schematic: {os.path.basename(schematic_path)}\n\n"
        result += f"## Components (Estimated Count: {len(components)})\n\n"
        
        # Extract a sample of components
        for i, comp in enumerate(components[:10]):
            result += f"{comp}\n"
        
        if len(components) > 10:
            result += f"\n... and {len(components) - 10} more components\n"
        
        return result
    
    except Exception as e:
        return f"Error reading schematic file: {str(e)}"

# Tools
@mcp.tool()
def find_projects() -> List[Dict[str, Any]]:
    """Find all KiCad projects on this system."""
    return find_kicad_projects()

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
    try:
        with open(project_path, 'r') as f:
            project_data = json.load(f)
            if "metadata" in project_data:
                metadata = project_data["metadata"]
    except Exception as e:
        metadata = {"error": str(e)}
    
    return {
        "name": project_name,
        "path": project_path,
        "directory": project_dir,
        "files": files,
        "metadata": metadata
    }

@mcp.tool()
def open_kicad_project(project_path: str) -> Dict[str, Any]:
    """Open a KiCad project in KiCad."""
    if not os.path.exists(project_path):
        return {"success": False, "error": f"Project not found: {project_path}"}
    
    try:
        # On MacOS, use the 'open' command to open the project in KiCad
        cmd = ["open", "-a", KICAD_APP_PATH, project_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "command": " ".join(cmd),
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def extract_bom(project_path: str) -> Dict[str, Any]:
    """Extract a Bill of Materials (BOM) from a KiCad project."""
    if not os.path.exists(project_path):
        return {"success": False, "error": f"Project not found: {project_path}"}
    
    project_dir = os.path.dirname(project_path)
    project_name = os.path.basename(project_path)[:-10]
    
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

@mcp.tool()
def validate_project(project_path: str) -> Dict[str, Any]:
    """Basic validation of a KiCad project."""
    if not os.path.exists(project_path):
        return {"valid": False, "error": f"Project not found: {project_path}"}
    
    issues = []
    files = get_project_files(project_path)
    
    # Check for essential files
    if "kicad_pcb" not in files:
        issues.append("Missing PCB layout file")
    
    if "kicad_sch" not in files:
        issues.append("Missing schematic file")
    
    # Validate project file
    try:
        with open(project_path, 'r') as f:
            project_data = json.load(f)
    except json.JSONDecodeError:
        issues.append("Invalid project file format (JSON parsing error)")
    except Exception as e:
        issues.append(f"Error reading project file: {str(e)}")
    
    return {
        "valid": len(issues) == 0,
        "path": project_path,
        "issues": issues if issues else None,
        "files_found": list(files.keys())
    }

@mcp.tool()
async def generate_project_thumbnail(project_path: str, ctx: Context) -> Optional[Image]:
    """Generate a thumbnail of a KiCad project's PCB layout."""
    # This would normally use KiCad's Python API (pcbnew) to render a PCB image
    # However, since this is a simulation, we'll return a message instead
    
    if not os.path.exists(project_path):
        ctx.info(f"Project not found: {project_path}")
        return None
    
    # Get PCB file
    files = get_project_files(project_path)
    if "kicad_pcb" not in files:
        ctx.info("PCB file not found in project")
        return None
    
    ctx.info("In a real implementation, this would generate a PCB thumbnail image")
    ctx.info("This requires pcbnew Python module from KiCad to render PCB layouts")
    
    # Placeholder for actual implementation
    # In a real implementation, you would:
    # 1. Load the PCB file using pcbnew
    # 2. Render it to an image
    # 3. Return the image
    
    return None

# Prompts
@mcp.prompt()
def create_new_component() -> str:
    """Prompt for creating a new KiCad component."""
    return """
I want to create a new component in KiCad for my PCB design. I need help with:

1. Deciding on the correct component package/footprint
2. Creating the schematic symbol
3. Connecting the schematic symbol to the footprint
4. Adding the component to my design

Please provide step-by-step instructions on how to create a new component in KiCad.
"""

@mcp.prompt()
def debug_pcb_issues() -> str:
    """Prompt for debugging common PCB issues."""
    return """
I'm having issues with my KiCad PCB design. Can you help me troubleshoot the following problems:

1. Design rule check (DRC) errors
2. Electrical rule check (ERC) errors
3. Footprint mismatches
4. Routing challenges

Please provide a systematic approach to identifying and fixing these issues in KiCad.
"""

# Run the server
if __name__ == "__main__":
    mcp.run(transport='stdio')

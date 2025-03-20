"""
MCP server creation and configuration.
"""
from mcp.server.fastmcp import FastMCP

# Import resource handlers
from kicad_mcp.resources.projects import register_project_resources
from kicad_mcp.resources.files import register_file_resources

# Import tool handlers
from kicad_mcp.tools.project_tools import register_project_tools
from kicad_mcp.tools.analysis_tools import register_analysis_tools
from kicad_mcp.tools.export_tools import register_export_tools

# Import prompt handlers
from kicad_mcp.prompts.templates import register_prompts

def create_server() -> FastMCP:
    """Create and configure the KiCad MCP server."""
    # Initialize FastMCP server
    mcp = FastMCP("KiCad")
    
    # Register resources
    register_project_resources(mcp)
    register_file_resources(mcp)
    
    # Register tools
    register_project_tools(mcp)
    register_analysis_tools(mcp)
    register_export_tools(mcp)
    
    # Register prompts
    register_prompts(mcp)
    
    return mcp

"""
MCP server creation and configuration.
"""
from mcp.server.fastmcp import FastMCP

# Import resource handlers
from kicad_mcp.resources.projects import register_project_resources
from kicad_mcp.resources.files import register_file_resources
from kicad_mcp.resources.drc_resources import register_drc_resources
from kicad_mcp.resources.bom_resources import register_bom_resources

# Import tool handlers
from kicad_mcp.tools.project_tools import register_project_tools
from kicad_mcp.tools.analysis_tools import register_analysis_tools
from kicad_mcp.tools.export_tools import register_export_tools
from kicad_mcp.tools.drc_tools import register_drc_tools
from kicad_mcp.tools.bom_tools import register_bom_tools

# Import prompt handlers
from kicad_mcp.prompts.templates import register_prompts
from kicad_mcp.prompts.drc_prompt import register_drc_prompts
from kicad_mcp.prompts.bom_prompts import register_bom_prompts

# Import utils
from kicad_mcp.utils.logger import Logger
from kicad_mcp.utils.python_path import setup_kicad_python_path

# Import context management
from kicad_mcp.context import kicad_lifespan

# Create logger for this module
logger = Logger()

def create_server() -> FastMCP:
    """Create and configure the KiCad MCP server."""
    logger.info("Initializing KiCad MCP server")

    # Try to set up KiCad Python path
    kicad_modules_available = setup_kicad_python_path()

    if kicad_modules_available:
        logger.info("KiCad Python modules successfully configured")
    else:
        logger.warning("KiCad Python modules not available - some features will be disabled")

    # Initialize FastMCP server
    mcp = FastMCP("KiCad", lifespan=kicad_lifespan)
    logger.info("Created FastMCP server instance with lifespan management")
    
    # Register resources
    logger.debug("Registering resources...")
    register_project_resources(mcp)
    register_file_resources(mcp)
    register_drc_resources(mcp)
    register_bom_resources(mcp)
    
    # Register tools
    logger.debug("Registering tools...")
    register_project_tools(mcp)
    register_analysis_tools(mcp)
    register_export_tools(mcp)
    register_drc_tools(mcp)
    register_bom_tools(mcp)
    
    # Register prompts
    logger.debug("Registering prompts...")
    register_prompts(mcp)
    register_drc_prompts(mcp)
    register_bom_prompts(mcp)
    
    logger.info("Server initialization complete")
    return mcp

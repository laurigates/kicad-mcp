"""
MCP server creation and configuration.
"""
import atexit
import os
import signal
from typing import Callable
from mcp.server.fastmcp import FastMCP

# Import resource handlers
from kicad_mcp.resources.projects import register_project_resources
from kicad_mcp.resources.files import register_file_resources
from kicad_mcp.resources.drc_resources import register_drc_resources
from kicad_mcp.resources.bom_resources import register_bom_resources
from kicad_mcp.resources.netlist_resources import register_netlist_resources
from kicad_mcp.resources.pattern_resources import register_pattern_resources


# Import tool handlers
from kicad_mcp.tools.project_tools import register_project_tools
from kicad_mcp.tools.analysis_tools import register_analysis_tools
from kicad_mcp.tools.export_tools import register_export_tools
from kicad_mcp.tools.drc_tools import register_drc_tools
from kicad_mcp.tools.bom_tools import register_bom_tools
from kicad_mcp.tools.netlist_tools import register_netlist_tools
from kicad_mcp.tools.pattern_tools import register_pattern_tools

# Import prompt handlers
from kicad_mcp.prompts.templates import register_prompts
from kicad_mcp.prompts.drc_prompt import register_drc_prompts
from kicad_mcp.prompts.bom_prompts import register_bom_prompts
from kicad_mcp.prompts.pattern_prompts import register_pattern_prompts

# Import utils
from kicad_mcp.utils.python_path import setup_kicad_python_path

# Import context management
from kicad_mcp.context import kicad_lifespan

# Track cleanup handlers
cleanup_handlers = []

# Flag to track whether we're already in shutdown process
_shutting_down = False

# Store server instance for clean shutdown
_server_instance = None

def add_cleanup_handler(handler: Callable) -> None:
    """Register a function to be called during cleanup.
    
    Args:
        handler: Function to call during cleanup
    """
    cleanup_handlers.append(handler)

def run_cleanup_handlers() -> None:
    """Run all registered cleanup handlers."""
    print("Running cleanup handlers...")

    global _shutting_down
    
    # Prevent running cleanup handlers multiple times
    if _shutting_down:
        return

    _shutting_down = True
    print("Running cleanup handlers...")
    
    for handler in cleanup_handlers:
        try:
            handler()
            print(f"Cleanup handler {handler.__name__} completed successfully")
        except Exception as e:
            print(f"Error in cleanup handler {handler.__name__}: {str(e)}", exc_info=True)

def shutdown_server():
    """Properly shutdown the server if it exists."""
    global _server_instance
    
    if _server_instance:
        try:
            print("Shutting down KiCad MCP server")
            # The server should handle its own shutdown through its lifespan context
            # This is mostly a placeholder for any additional server shutdown code
            _server_instance = None
            print("KiCad MCP server shutdown complete")
        except Exception as e:
            print(f"Error shutting down server: {str(e)}", exc_info=True)


def register_signal_handlers(server: FastMCP) -> None:
    """Register handlers for system signals to ensure clean shutdown.
    
    Args:
        server: The FastMCP server instance
    """
    def handle_exit_signal(signum, frame):
        print(f"Received signal {signum}, initiating shutdown...")
        
        # Run cleanup first
        run_cleanup_handlers()
        
        # Then shutdown server
        shutdown_server()
        
        # Exit without waiting for stdio processes which might be blocking
        os._exit(0)
    
    # Register for common termination signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_exit_signal)
            print(f"Registered handler for signal {sig}")
        except (ValueError, AttributeError) as e:
            # Some signals may not be available on all platforms
            print(f"Could not register handler for signal {sig}: {str(e)}")


def create_server() -> FastMCP:
    """Create and configure the KiCad MCP server."""
    print("Initializing KiCad MCP server")

    # Try to set up KiCad Python path
    kicad_modules_available = setup_kicad_python_path()

    if kicad_modules_available:
        print("KiCad Python modules successfully configured")
    else:
        print("KiCad Python modules not available - some features will be disabled")

    # Initialize FastMCP server
    mcp = FastMCP("KiCad", lifespan=kicad_lifespan)
    print("Created FastMCP server instance with lifespan management")
    
    # Register resources
    print("Registering resources...")
    register_project_resources(mcp)
    register_file_resources(mcp)
    register_drc_resources(mcp)
    register_bom_resources(mcp)
    register_netlist_resources(mcp)
    register_pattern_resources(mcp)
    
    # Register tools
    print("Registering tools...")
    register_project_tools(mcp)
    register_analysis_tools(mcp)
    register_export_tools(mcp)
    register_drc_tools(mcp)
    register_bom_tools(mcp)
    register_netlist_tools(mcp)
    register_pattern_tools(mcp)
    
    # Register prompts
    print("Registering prompts...")
    register_prompts(mcp)
    register_drc_prompts(mcp)
    register_bom_prompts(mcp)
    register_pattern_prompts(mcp)

    # Register signal handlers and cleanup
    register_signal_handlers(mcp)
    atexit.register(run_cleanup_handlers)
    
    # Add specific cleanup handlers
    add_cleanup_handler(lambda: print("KiCad MCP server shutdown complete"))

    # Add temp directory cleanup
    def cleanup_temp_dirs():
        """Clean up any temporary directories created by the server."""
        import shutil
        from kicad_mcp.utils.temp_dir_manager import get_temp_dirs
        
        temp_dirs = get_temp_dirs()
        print(f"Cleaning up {len(temp_dirs)} temporary directories")
        
        for temp_dir in temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")
    
    add_cleanup_handler(cleanup_temp_dirs)
    
    print("Server initialization complete")
    return mcp

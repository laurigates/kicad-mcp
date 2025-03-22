"""
Lifespan context management for KiCad MCP Server.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Any

from mcp.server.fastmcp import FastMCP

from kicad_mcp.utils.python_path import setup_kicad_python_path

@dataclass
class KiCadAppContext:
    """Type-safe context for KiCad MCP server."""
    kicad_modules_available: bool
    
    # Optional cache for expensive operations
    cache: Dict[str, Any]

@asynccontextmanager
async def kicad_lifespan(server: FastMCP) -> AsyncIterator[KiCadAppContext]:
    """Manage KiCad MCP server lifecycle with type-safe context.
    
    This function handles:
    1. Initializing shared resources when the server starts
    2. Providing a typed context object to all request handlers
    3. Properly cleaning up resources when the server shuts down
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        KiCadAppContext: A typed context object shared across all handlers
    """
    print("Starting KiCad MCP server initialization")
    
    # Initialize resources on startup
    print("Setting up KiCad Python modules")
    kicad_modules_available = setup_kicad_python_path()
    print(f"KiCad Python modules available: {kicad_modules_available}")
    
    # Create in-memory cache for expensive operations
    cache: Dict[str, Any] = {}
    
    # Initialize any other resources that need cleanup later
    created_temp_dirs = []
    
    try:
        # Import any KiCad modules that should be preloaded
        if kicad_modules_available:
            try:
                print("Preloading KiCad Python modules")
                
                # Core PCB module used in multiple tools
                import pcbnew
                print(f"Successfully preloaded pcbnew module: {getattr(pcbnew, 'GetBuildVersion', lambda: 'unknown')()}")
                cache["pcbnew_version"] = getattr(pcbnew, "GetBuildVersion", lambda: "unknown")()
            except ImportError as e:
                print(f"Failed to preload some KiCad modules: {str(e)}")

        # Yield the context to the server - server runs during this time
        print("KiCad MCP server initialization complete")
        yield KiCadAppContext(
            kicad_modules_available=kicad_modules_available,
            cache=cache
        )
    finally:
        # Clean up resources when server shuts down
        print("Shutting down KiCad MCP server")
        
        # Clear the cache
        if cache:
            print(f"Clearing cache with {len(cache)} entries")
            cache.clear()
        
        # Clean up any temporary directories
        import shutil
        for temp_dir in created_temp_dirs:
            try:
                print(f"Removing temporary directory: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")
        
        print("KiCad MCP server shutdown complete")

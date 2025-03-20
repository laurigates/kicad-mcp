"""
Lifespan context management for KiCad MCP Server.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

from kicad_mcp.utils.logger import Logger
from kicad_mcp.utils.python_path import setup_kicad_python_path

# Create logger for this module
logger = Logger()

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
    logger.info("Starting KiCad MCP server initialization")
    
    # Initialize resources on startup
    logger.info("Setting up KiCad Python modules")
    kicad_modules_available = setup_kicad_python_path()
    logger.info(f"KiCad Python modules available: {kicad_modules_available}")
    
    # Create in-memory cache for expensive operations
    cache: Dict[str, Any] = {}
    
    # Initialize any other resources that need cleanup later
    created_temp_dirs = []
    
    try:
        # Import any KiCad modules that should be preloaded
        if kicad_modules_available:
            try:
                logger.info("Preloading KiCad Python modules")
                
                # Core PCB module used in multiple tools
                import pcbnew
                logger.info(f"Successfully preloaded pcbnew module: {getattr(pcbnew, 'GetBuildVersion', lambda: 'unknown')()}")
                cache["pcbnew_version"] = getattr(pcbnew, "GetBuildVersion", lambda: "unknown")()
            except ImportError as e:
                logger.warning(f"Failed to preload some KiCad modules: {str(e)}")

        # Yield the context to the server - server runs during this time
        logger.info("KiCad MCP server initialization complete")
        yield KiCadAppContext(
            kicad_modules_available=kicad_modules_available,
            cache=cache
        )
    finally:
        # Clean up resources when server shuts down
        logger.info("Shutting down KiCad MCP server")
        
        # Clear the cache
        if cache:
            logger.debug(f"Clearing cache with {len(cache)} entries")
            cache.clear()
        
        # Clean up any temporary directories
        import shutil
        for temp_dir in created_temp_dirs:
            try:
                logger.debug(f"Removing temporary directory: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")
        
        logger.info("KiCad MCP server shutdown complete")

#!/usr/bin/env python3
"""
KiCad MCP Server - A Model Context Protocol server for KiCad on macOS.
This server allows Claude and other MCP clients to interact with KiCad projects.
"""
import os
import sys

from kicad_mcp.config import KICAD_USER_DIR, ADDITIONAL_SEARCH_PATHS
from kicad_mcp.server import create_server
from kicad_mcp.utils.env import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

if __name__ == "__main__":
    try:
        print("Starting KiCad MCP server")

        # Log search paths from config
        print(f"Using KiCad user directory: {KICAD_USER_DIR}")
        if ADDITIONAL_SEARCH_PATHS:
            print(f"Additional search paths: {', '.join(ADDITIONAL_SEARCH_PATHS)}")
        else:
            print("No additional search paths configured")

        # Create and run server
        server = create_server()
        print("Running server with stdio transport")
        server.run(transport='stdio')
    except Exception as e:
        print(f"Unhandled exception: {str(e)}")
        raise

#!/usr/bin/env python3
"""
KiCad MCP Server - A Model Context Protocol server for KiCad on macOS.
This server allows Claude and other MCP clients to interact with KiCad projects.
"""
from kicad_mcp.server import create_server
from kicad_mcp.utils.logger import Logger

logger = Logger()

if __name__ == "__main__":
    try:
        logger.info("Starting KiCad MCP server")
        server = create_server()
        logger.info("Running server with stdio transport")
        server.run(transport='stdio')
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        raise

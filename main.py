#!/usr/bin/env python3
"""
KiCad MCP Server - A Model Context Protocol server for KiCad on macOS.
This server allows Claude and other MCP clients to interact with KiCad projects.
"""
from kicad_mcp.server import create_server

if __name__ == "__main__":
    server = create_server()
    server.run(transport='stdio')

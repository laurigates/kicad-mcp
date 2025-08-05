#!/usr/bin/env python3
"""
Server startup script for HTTP testing.

Provides a simple entry point to start the KiCad-MCP server for HTTP testing.
"""

import argparse
import sys

import uvicorn

from kicad_mcp.server import create_server


def main() -> None:
    """Main entry point for starting the test server."""
    parser = argparse.ArgumentParser(description="Start KiCad-MCP server for HTTP testing")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Log level (default: info)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    try:
        # Create the FastMCP server
        print("Creating KiCad-MCP server...")
        server = create_server()

        # Get the HTTP app (uses StreamableHTTP by default for MCP protocol support)
        print("Configuring HTTP transport...")
        app = server.http_app()

        print(f"Starting server on http://{args.host}:{args.port}")
        print(f"Log level: {args.log_level}")

        # Start the server
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            reload=args.reload,
        )

    except KeyboardInterrupt:
        print("\nServer interrupted!")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

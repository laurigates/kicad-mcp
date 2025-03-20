# KiCad MCP Server

> ⚠️ **WARNING**: This project was quickly hacked together and is largely untested. Expect things to break. Use at your own risk. I plan on improving it over time, but if you find bugs, please open an issue or submit a pull request to fix them (see Contributing section below).

This guide will help you set up a Model Context Protocol (MCP) server for KiCad on macOS, allowing you to interact with KiCad projects through Claude Desktop or other MCP-compatible clients.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Installation Steps](#installation-steps)
  - [1. Set Up Your Python Environment](#1-set-up-your-python-environment)
  - [2. Run the Server](#2-run-the-server)
  - [3. Configure Claude Desktop](#3-configure-claude-desktop)
  - [4. Restart Claude Desktop](#4-restart-claude-desktop)
- [Understanding MCP Components](#understanding-mcp-components)
- [Available Features](#available-features)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Future Development Ideas](#future-development-ideas)
- [License](#license)

## Prerequisites

- macOS with KiCad installed
- Python 3.10 or higher
- Claude Desktop (or another MCP client)
- Basic familiarity with the terminal

## Project Structure

The KiCad MCP Server is organized into a modular structure for better maintainability:

```
kicad-mcp/
├── README.md                       # Project documentation
├── main.py                         # Entry point that runs the server
├── config.py                       # Configuration constants and settings
├── requirements.txt                # Python dependencies
├── kicad_mcp/                      # Main package directory
│   ├── __init__.py                 # Package initialization
│   ├── server.py                   # MCP server setup
│   ├── resources/                  # Resource handlers
│   ├── tools/                      # Tool handlers
│   ├── prompts/                    # Prompt templates
│   └── utils/                      # Utility functions
└── tests/                          # Unit tests
```

## Installation Steps

### 1. Set Up Your Python Environment

First, let's install `pip` and set up our environment:

```bash
# Create a new directory for our project
mkdir -p ~/Projects/kicad-mcp
cd ~/Projects/kicad-mcp

# Create a virtual environment and activate it
python3 -m venv venv
source venv/bin/activate

# Install the MCP SDK and other dependencies
pip install -r requirements.txt
```

### 2. Run the Server

Once the environment is set up, you can run the server:

```bash
# Run in development mode
python -m mcp.dev main.py

# Or run directly
python main.py
```

### 3. Configure Claude Desktop

Now, let's configure Claude Desktop to use our MCP server:

1. Create or edit the Claude Desktop configuration file:

```bash
# Create the directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude

# Edit the configuration file (or create it if it doesn't exist)
vim ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. Add the KiCad MCP server to the configuration:

```json
{
    "mcpServers": {
        "kicad": {
            "command": "/ABSOLUTE/PATH/TO/YOUR/PROJECT/kicad-mcp/venv/bin/python",
            "args": [
                "/ABSOLUTE/PATH/TO/YOUR/PROJECT/kicad-mcp/main.py"
            ]
        }
    }
}
```

Replace `/ABSOLUTE/PATH/TO/YOUR/PROJECT/kicad-mcp` with the actual path to your project directory (e.g., `/Users/yourusername/Projects/kicad-mcp`).

3. Save the file and exit the editor.

### 4. Restart Claude Desktop

Close and reopen Claude Desktop to load the new configuration.

## Understanding MCP Components

The Model Context Protocol (MCP) defines three primary ways to provide capabilities:

### Resources vs Tools vs Prompts

**Resources** are read-only data sources that LLMs can reference:
- Similar to GET endpoints in REST APIs
- Provide data without performing significant computation
- Used when the LLM needs to read information
- Typically accessed programmatically by the client application
- Example: `kicad://projects` returns a list of all KiCad projects

**Tools** are functions that perform actions or computations:
- Similar to POST/PUT endpoints in REST APIs
- Can have side effects (like opening applications or generating files)
- Used when the LLM needs to perform actions in the world
- Typically invoked directly by the LLM (with user approval)
- Example: `open_project()` launches KiCad with a specific project

**Prompts** are reusable templates for common interactions:
- Pre-defined conversation starters or instructions
- Help users articulate common questions or tasks
- Invoked by user choice (typically from a menu)
- Example: The `debug_pcb_issues` prompt helps users troubleshoot PCB problems

## Available Features

The KiCad MCP Server provides several capabilities:

### Resources
- `kicad://projects` - List all KiCad projects
- `kicad://project/{path}` - Get details about a specific project
- `kicad://schematic/{path}` - Extract information from a schematic file
- `kicad://drc/{path}` - Get a detailed Design Rule Check report for a PCB
- `kicad://drc/history/{path}` - Get DRC history report with trend analysis

### Tools
- Project management tools (find projects, get structure, open in KiCad)
- Analysis tools (validate projects, generate thumbnails)
- Export tools (extract bill of materials)
- Design Rule Check tools (run DRC checks, get detailed violation reports, track DRC history and improvements over time)

### Prompts
- Create new component guide
- Debug PCB issues guide
- PCB manufacturing checklist

## Development Guide

### Adding New Features

To add new features to the KiCad MCP Server, follow these steps:

1. Identify the category for your feature (resource, tool, or prompt)
2. Add your implementation to the appropriate module
3. Register your feature in the corresponding register function
4. Test your changes with the development tools

Example for adding a new tool:

```python
# kicad_mcp/tools/analysis_tools.py

@mcp.tool()
def new_analysis_tool(project_path: str) -> Dict[str, Any]:
    """Description of your new tool."""
    # Implementation goes here
    return {"result": "success"}
```

### Running Tests

This project uses pytest for testing:

```bash
# Install development dependencies
pip install pytest

# Run tests
pytest
```

## Troubleshooting

If you encounter issues:

1. **Server Not Appearing in Claude Desktop:**
   - Check your `claude_desktop_config.json` file for errors
   - Make sure the path to your project and Python interpreter is correct
   - Ensure Python can access the `mcp` package

2. **Server Errors:**
   - Check the terminal output when running the server in development mode
   - Make sure all required Python packages are installed
   - Verify that your KiCad installation is in the standard location

## Contributing

Want to contribute to the KiCad MCP Server? Here's how you can help improve this project:

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

## Future Development Ideas

Interested in contributing? Here are some ideas for future development:

1. Implement 3D model visualization tools
2. Create PCB review tools with annotations
3. Add support for generating manufacturing files
4. Implement component search tools
5. Add tests!

## License

This project is open source under the MIT license.

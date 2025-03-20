# KiCad MCP Server

> ⚠️ **WARNING**: This project was quickly hacked together and is largely untested. Expect things to break. Use at your own risk. I plan on improving it over time, but if you find bugs, please open an issue or submit a pull request to fix them (see Contributing section below).

> **WARNING**: This project is optimized for Mac. While there exists some basic support for Windows and Linux, not all functionality is guaranteed to work.

This guide will help you set up a Model Context Protocol (MCP) server for KiCad. While the examples in this guide often reference Claude Desktop, the server is compatible with **any MCP-compliant client**. You can use it with Claude Desktop, your own custom MCP clients, or any other application that implements the Model Context Protocol.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Installation Steps](#installation-steps)
  - [1. Set Up Your Python Environment](#1-set-up-your-python-environment)
  - [2. Run the Server](#2-run-the-server)
  - [3. Configure Claude Desktop](#3-configure-claude-desktop)
  - [4. Restart Claude Desktop](#4-restart-claude-desktop)
- [Understanding MCP Components](#understanding-mcp-components)
- [Features and Usage Guide](#features-and-usage-guide)
  - [Project Management](#project-management)
  - [PCB Design Analysis](#pcb-design-analysis)
  - [Design Rule Checking (DRC)](#design-rule-checking-drc)
  - [PCB Visualization](#pcb-visualization)
  - [Templates and Prompts](#templates-and-prompts)
- [Usage Examples](#usage-examples)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Future Development Ideas](#future-development-ideas)
- [License](#license)

## Prerequisites

- macOS, Windows, or Linux with KiCad installed
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
│   ├── context.py                  # Lifespan management and shared context
│   ├── resources/                  # Resource handlers
│   ├── tools/                      # Tool handlers
│   ├── prompts/                    # Prompt templates
│   └── utils/                      # Utility functions
├── docs/                           # Documentation
│   ├── drc_guide.md                # Design Rule Check guide
│   └── thumbnail_guide.md          # PCB Thumbnail feature guide
└── tests/                          # Unit tests
```

## Installation Steps

### 1. Set Up Your Python Environment

First, let's install dependencies and set up our environment:

```bash
# Create a new directory for our project
mkdir -p ~/Projects/kicad-mcp
cd ~/Projects/kicad-mcp

# Clone the repository
git clone https://github.com/lamaalrajih/kicad-mcp.git .

# Create a virtual environment and activate it
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

### 3. Configure an MCP Client

The server can be used with any MCP-compatible client. Here's how to set it up with Claude Desktop as an example:

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

#### Windows Configuration

On Windows, the configuration would look like:

```json
{
    "mcpServers": {
        "kicad": {
            "command": "C:\\Path\\To\\Your\\Project\\kicad-mcp\\venv\\Scripts\\python.exe",
            "args": [
                "C:\\Path\\To\\Your\\Project\\kicad-mcp\\main.py"
            ]
        }
    }
}
```

The configuration should be stored in `%APPDATA%\Claude\claude_desktop_config.json`.

### 4. Restart Your MCP Client

Close and reopen your MCP client (e.g., Claude Desktop) to load the new configuration. The KiCad server should appear in the tools dropdown menu or equivalent interface in your client.

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

## Features and Usage Guide

Here's how to use each of the key features of the KiCad MCP Server through any MCP-compatible client (examples show prompts for Claude Desktop, but the concepts apply to any MCP client):

### Project Management

#### Listing Projects

To see all KiCad projects available on your system:

```
Could you list all my KiCad projects?
```

Claude will use the `kicad://projects` resource to display a formatted list of your KiCad projects, including their paths and last modified dates.

#### Project Details

To get details about a specific project:

```
Show me details about my KiCad project at /path/to/your/project.kicad_pro
```

Claude will display project information including available files, settings, and metadata.

#### Opening Projects

To open a KiCad project:

```
Can you open my KiCad project at /path/to/your/project.kicad_pro?
```

This will launch KiCad with the specified project open. Note that this requires KiCad to be properly installed.

### PCB Design Analysis

#### Validating Projects

To validate a KiCad project for issues:

```
Validate my KiCad project at /path/to/your/project.kicad_pro
```

Claude will check for missing files, incorrect formats, and other common issues.

#### Schematic Information

To extract information from a schematic:

```
What components are in my schematic at /path/to/your/project.kicad_sch?
```

This will display component information extracted from the schematic file.

### Design Rule Checking (DRC)

#### Running DRC Checks

To check your PCB layout for design rule violations:

```
Run a DRC check on my KiCad project at /path/to/your/project.kicad_pro
```

Claude will analyze your PCB layout for violations of design rules and provide a detailed report.

#### Viewing DRC History

To see how DRC violations have changed over time:

```
Show me the DRC history for my KiCad project at /path/to/your/project.kicad_pro
```

This displays a trend of violations over time, helping you track your progress as you fix issues.

DRC history is persistently stored on your filesystem at `~/.kicad_mcp/drc_history/` and is preserved across sessions. Each project's history is saved in a JSON file with a format like `projectname_[hash]_drc_history.json`. The system keeps track of up to 10 most recent DRC checks per project, allowing you to monitor your progress in fixing design rule violations over time.

#### Getting Help with DRC Violations

For help with fixing DRC issues, use the Fix DRC Violations prompt:

```
I need help fixing DRC violations in my KiCad project at /path/to/your/project.kicad_pro
```

Claude will guide you through understanding and resolving each type of violation.

### PCB Visualization

#### Generating PCB Thumbnails

To visualize your PCB layout:

```
Generate a thumbnail for my KiCad PCB at /path/to/your/project.kicad_pro
```

Claude will create a visual representation of your PCB board, showing layers, traces, and components.

### Templates and Prompts

#### Using Prompt Templates

Claude Desktop provides several specialized prompts for common KiCad workflows. Access these by clicking the "Prompt Templates" button in Claude Desktop, then selecting one of the KiCad templates:

- **Create New Component** - Guides you through creating a new KiCad component
- **Debug PCB Issues** - Helps troubleshoot common PCB design problems
- **PCB Manufacturing Checklist** - Prepares your design for manufacturing
- **Fix DRC Violations** - Assists with resolving design rule violations
- **Custom Design Rules** - Helps create specialized design rules for your project

## Usage Examples

Here are some complete examples of how to interact with the KiCad MCP Server through Claude Desktop:

### Example 1: Basic Project Workflow

```
Claude, I've just started a new KiCad project but I need some guidance. Can you list my existing KiCad projects first so I can see what I've already worked on?
```

Claude will list your KiCad projects. Then you might ask:

```
Great, can you show me details about the project at /Users/me/Documents/KiCad/amplifier/amplifier.kicad_pro?
```

Claude will display information about that specific project. Then you could continue:

```
I need to check if there are any design rule violations. Can you run a DRC check on that project?
```

### Example 2: Getting PCB Design Help

```
I'm having trouble with my PCB design in KiCad. I keep getting clearance errors between traces. Can you help me understand how to fix this?
```

Claude will explain clearance errors and suggest solutions. You could continue:

```
Can you show me a thumbnail of my PCB layout at /Users/me/Documents/KiCad/amplifier/amplifier.kicad_pro so I can see the problematic areas?
```

Claude will generate and display a thumbnail of your PCB. Then you might ask:

```
Let's run a full DRC check on this project to identify all the issues I need to fix.
```

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

1. **Server Not Appearing in MCP Client:**
   - Check your client's configuration file for errors (e.g., `claude_desktop_config.json` for Claude Desktop)
   - Make sure the path to your project and Python interpreter is correct
   - Ensure Python can access the `mcp` package
   - Check if your KiCad installation is detected

2. **Server Errors:**
   - Check the terminal output when running the server in development mode
   - Look for errors in the logs at `~/.kicad_mcp/logs` or `logs/` directory
   - Make sure all required Python packages are installed
   - Verify that your KiCad installation is in the standard location

3. **KiCad Python Modules Not Found:**
   - This is a common issue. The server will still work but with limited functionality
   - Ensure KiCad is installed properly
   - Check if the right paths are set in `config.py`
   
4. **DRC History Not Saving:**
   - Check if the `~/.kicad_mcp/drc_history/` directory exists and is writable
   - Verify that the project path used is consistent between runs
   - Check for errors in the logs related to DRC history saving

## Contributing

Want to contribute to the KiCad MCP Server? Here's how you can help improve this project:

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

Key areas that need work:
- Improving cross-platform compatibility
- Adding more comprehensive tests
- Enhancing error handling
- Adding support for more KiCad features

## Future Development Ideas

Interested in contributing? Here are some ideas for future development:

1. Implement 3D model visualization tools
2. Create PCB review tools with annotations
3. Add support for generating manufacturing files
4. Implement component search tools
5. Enhance BOM capabilities with supplier integration
6. Add support for interactive design checks
7. Implement a simple web UI for configuration and monitoring
8. Add automated circuit analysis features
9. Add tests!

## License

This project is open source under the MIT license.

# KiCad MCP Server - Setup Guide

This guide will help you set up a Model Context Protocol (MCP) server for KiCad on macOS, allowing you to interact with KiCad projects through Claude Desktop or other MCP-compatible clients.

## Prerequisites

- macOS with KiCad installed
- Python 3.10 or higher
- Claude Desktop (or another MCP client)
- Basic familiarity with the terminal

## Installation Steps

### 1. Set Up Your Python Environment

First, let's install `uv` (a fast Python package installer) and set up our environment:

```bash
# Create a new directory for our project
mkdir -p ~/Projects/kicad-mcp
cd ~/Projects/kicad-mcp

# Create a virtual environment and activate it
python3 -m venv venv
source venv/bin/activate

# Install the MCP SDK
pip install "mcp[cli]"
```

### 2. Save the KiCad MCP Server Script

Create a new file called `kicad_mcp.py` in your project directory and paste the contents of the KiCad MCP Server script.

```bash
# Make the file executable (optional, but helpful)
chmod +x kicad_mcp.py

# Run the server in development mode
python -m mcp.dev kicad_mcp.py
```

### 3. Test Your Server

Let's make sure your server works correctly before integrating it with Claude Desktop:

```bash
# Check if the file exists and has content
cat kicad_mcp.py | head -n 5
```

You should see the server start up and display information about the available tools and resources.

### 4. Configure Claude Desktop

Now, let's configure Claude Desktop to use our MCP server:

1. Create or edit the Claude Desktop configuration file:

```bash
# Create the directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude

# Edit the configuration file (or create it if it doesn't exist)
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. Add the KiCad MCP server to the configuration:

```json
{
    "mcpServers": {
        "kicad": {
            "command": "/ABSOLUTE/PATH/TO/YOUR/PROJECT/kicad-mcp/venv/bin/python",
            "args": [
                "/ABSOLUTE/PATH/TO/YOUR/PROJECT/kicad-mcp/kicad_mcp.py"
            ]
        }
    }
}
```

Replace `/ABSOLUTE/PATH/TO/YOUR/PROJECT/kicad-mcp` with the actual path to your project directory (e.g., `/Users/yourusername/Projects/kicad-mcp`).

3. Save the file and exit the editor.

### 5. Restart Claude Desktop

Close and reopen Claude Desktop to load the new configuration.

## Usage

Once the server is properly configured, you can interact with KiCad through Claude Desktop:

1. Open Claude Desktop
2. Look for the tools icon (hammer symbol) in the Claude interface
3. You should see the KiCad MCP tools available in the menu

Here are some example prompts you can use:

- "What KiCad projects do I have on my Mac?"
- "Can you help me open my latest KiCad project?"
- "Extract the bill of materials from my project at [path]"
- "Validate my KiCad project at [path]"

## Troubleshooting

If you encounter issues:

1. **Server Not Appearing in Claude Desktop:**
   - Check your `claude_desktop_config.json` file for errors
   - Make sure the path to your project and Python interpreter is correct
   - Ensure Python can access the `mcp` package (check by running `python -c "import mcp; print(mcp.__version__)"` in your venv)

2. **Server Errors:**
   - Check the terminal output when running the server in development mode
   - Make sure all required Python packages are installed
   - Verify that your KiCad installation is in the standard location
   - Run `pip install -U "mcp[cli]"` to ensure you have the latest version

3. **Permission Issues:**
   - Make sure the script is executable (`chmod +x kicad_mcp.py`)
   - Check if Claude Desktop has permission to run the script
   - If you get permission errors, try using the full path to your Python interpreter in the configuration

## Extending the Server

The provided MCP server implements basic KiCad functionality. To extend it:

1. Add new tools using the `@mcp.tool()` decorator
2. Add new resources using the `@mcp.resource()` decorator
3. Add new prompts using the `@mcp.prompt()` decorator

The MCP SDK provides a command-line interface for development and deployment. With your virtual environment activated, you can use commands like:

```bash
# Test your server in development mode
python -m mcp.dev kicad_mcp.py

# Install your server for use with Claude Desktop
python -m mcp.install kicad_mcp.py --name "KiCad"
```

## Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io/introduction)
- [KiCad Python API Documentation](https://docs.kicad.org/doxygen-python/namespacepcbnew.html)

## Contributing

Want to contribute to the KiCad MCP Server? Here's how you can help improve this project:

### Getting Started

The project currently consists of just two files:

- kicad_mcp.py - The main MCP server implementation

- This setup guide

If you want to make improvements:

1. Set up your environment as described in the installation steps

2. Make your changes to the kicad_mcp.py file

3. Test your changes with Claude Desktop

### How to Contribute

#### Improving the Existing Server

You can improve the existing server by:

- Adding more tools and resources for KiCad

- Fixing bugs in the current implementation

- Improving error handling and user experience

- Adding support for more KiCad features

#### Testing Your Changes

Before sharing your changes, test them thoroughly:

```bash

# Run the server in development mode to check for errors

python -m mcp.dev kicad_mcp.py

# Test your changes with Claude Desktop

```

### Future Development Ideas

If you're looking for ways to improve the server, consider:

1. Adding support for KiCad's Python API (`pcbnew`) for deeper integration

2. Creating more specialized tools for PCB design review

3. Adding visualization capabilities for schematics and layouts

4. Improving project organization as the codebase grows

### Best Practices

- Keep the code simple and focused

- Document your functions with clear docstrings

- Handle errors gracefully with informative messages

- Test with different KiCad project structures

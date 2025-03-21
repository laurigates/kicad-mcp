# KiCad Project Management Guide

This guide explains how to use the project management features in the KiCad MCP Server.

## Overview

The project management functionality allows you to:

1. List all KiCad projects on your system
2. View detailed information about specific projects
3. Open projects directly in KiCad
4. Validate project files for completeness and correctness

## Quick Reference

| Task | Example Prompt |
|------|---------------|
| List all projects | `List all my KiCad projects` |
| View project details | `Show details for my KiCad project at /path/to/project.kicad_pro` |
| Open a project | `Open my KiCad project at /path/to/project.kicad_pro` |
| Validate a project | `Validate my KiCad project at /path/to/project.kicad_pro` |

## Using Project Management Features

### Listing Projects

To see all KiCad projects available on your system:

```
Could you list all my KiCad projects?
```

This will:
- Search your KiCad user directory (typically `~/Documents/KiCad`)
- Search any additional directories specified in your configuration
- Display a formatted list of projects with:
  - Project names
  - File paths
  - Last modified dates

The listing is sorted by last modified date, with most recently modified projects first.

#### How Project Discovery Works

Projects are discovered by:
1. Looking in the standard KiCad user directory
2. Searching directories specified in the `KICAD_SEARCH_PATHS` environment variable
3. Looking in common project directories (automatically detected)

### Viewing Project Details

To get detailed information about a specific project:

```
Show me details about my KiCad project at /path/to/your/project.kicad_pro
```

This will display:
- Basic project information
- Associated files (schematic, PCB, etc.)
- Project settings
- Metadata

Example output:
```
# Project: my_project

## Project Files
- **project**: /path/to/my_project.kicad_pro
- **schematic**: /path/to/my_project.kicad_sch
- **pcb**: /path/to/my_project.kicad_pcb
- **netlist**: /path/to/my_project_netlist.net

## Project Settings
- **version**: 20210606
- **generator**: pcbnew
- **board_thickness**: 1.6
```

### Opening Projects

To open a KiCad project:

```
Can you open my KiCad project at /path/to/your/project.kicad_pro?
```

This will:
- Launch KiCad with the specified project
- Return confirmation and status information

Note that this requires KiCad to be properly installed in the standard location for your operating system. The server detects KiCad's location automatically based on your platform.

### Validating Projects

To validate a KiCad project for issues:

```
Validate my KiCad project at /path/to/your/project.kicad_pro
```

The validation will check for:
- Missing or corrupt project files
- Required components (schematic, PCB)
- Valid project structure
- Proper JSON formatting

This is useful for identifying issues with project files before attempting to open them in KiCad.

## Project Resources

The server provides several resources for accessing project information:

- `kicad://projects` - List of all projects
- `kicad://project/{project_path}` - Details about a specific project

These resources can be accessed programmatically by other MCP clients or directly referenced in conversations.

## Tips for Project Management

### Best Practices

For smooth project management:

1. **Use consistent naming**: Keep project filenames consistent and meaningful
2. **Organize by functionality**: Group related projects in themed directories
3. **Include documentation**: Add README files or documentation in project directories
4. **Back up regularly**: Create backups of important projects
5. **Use version control**: Consider using git for tracking project changes

### Path Handling

When specifying project paths:

- Use absolute paths for reliability
- Ensure paths are properly escaped if they contain spaces
- On Windows, use forward slashes (/) instead of backslashes (\\)

## Troubleshooting

### Projects Not Found

If your projects aren't being discovered:

1. Check your `.env` file to ensure search paths are correctly specified
2. Verify that projects have the `.kicad_pro` extension
3. Check if you have read permissions for the specified directories
4. Try using absolute paths instead of relative paths
5. Restart the server after changing configuration

### Can't Open Projects

If you can't open projects:

1. Verify that KiCad is installed correctly
2. Check the `KICAD_APP_PATH` configuration if KiCad is in a non-standard location
3. Ensure the project path is correctly specified and accessible
4. Check if you have permissions to launch applications
5. Look for errors in the server logs

## Advanced Usage

### Custom Project Queries

You can ask more specific questions about your projects:

```
Which of my KiCad projects were modified in the last week?
```

```
Show me all KiCad projects in my ~/Electronics directory that have a PCB file
```

### Project Statistics

For insights across multiple projects:

```
What's the average board size across all my KiCad projects?
```

```
Which components are most commonly used across my KiCad projects?
```

# KiCad BOM Management Guide

This guide explains how to use the Bill of Materials (BOM) features in the KiCad MCP Server.

## Overview

The BOM functionality allows you to:

1. Analyze component usage in your KiCad projects
2. Export BOMs from your schematics
3. Estimate project costs
4. View BOM data in various formats (Markdown, CSV, JSON)
5. Get assistance with component sourcing and optimization

## Quick Reference

| Task | Example Prompt |
|------|---------------|
| Analyze components | `Analyze the BOM for my KiCad project at /path/to/project.kicad_pro` |
| Export a BOM | `Export a BOM for my KiCad project at /path/to/project.kicad_pro` |
| View formatted report | `Show me the BOM report for /path/to/project.kicad_pro` |
| Get raw CSV data | `Show me the CSV BOM data for /path/to/project.kicad_pro` |
| Get JSON data | `Show me the JSON BOM data for /path/to/project.kicad_pro` |

## Using BOM Features

### Analyzing an Existing BOM

To analyze a BOM that already exists in your project:

1. In your MCP client, request analysis of your project's BOM:

```
Please analyze the BOM for my KiCad project at /Users/username/Documents/KiCad/my_project/my_project.kicad_pro
```

The `analyze_bom` tool will:
- Search for BOM files in your project directory
- Parse and analyze the component data
- Generate a comprehensive report with component counts, categories, and cost estimates (if available)
- Provide insights into your component usage

### Exporting a New BOM

If you don't have a BOM yet, you can export one directly:

```
Can you export a BOM for my KiCad project at /Users/username/Documents/KiCad/my_project/my_project.kicad_pro?
```

The `export_bom_csv` tool will:
- Find the schematic file in your project
- Use KiCad's command-line tools to generate a new BOM
- Save the BOM in your project directory
- Provide a path to the generated file

### Viewing BOM Information

There are several ways to view your BOM data:

#### Formatted BOM Report

For a well-formatted report with component analysis:

```
Show me the BOM report for /Users/username/Documents/KiCad/my_project/my_project.kicad_pro
```

This will load the `kicad://bom/project_path` resource, showing:
- Total component count
- Breakdown by component type
- Cost estimates (if available)
- A table of components
- Suggestions for optimization

#### Raw BOM Data

To get the raw BOM data in CSV format:

```
Can I see the raw CSV BOM data for /Users/username/Documents/KiCad/my_project/my_project.kicad_pro?
```

This will load the `kicad://bom/project_path/csv` resource, providing:
- The raw CSV data from your BOM file
- Ideal for importing into spreadsheets or other tools

#### JSON Data

For structured data access:

```
Show me the JSON BOM data for /Users/username/Documents/KiCad/my_project/my_project.kicad_pro
```

This will load the `kicad://bom/project_path/json` resource, providing:
- Structured JSON representation of all BOM data
- Component analysis in machine-readable format
- Useful for programmatic processing

### Getting Help with BOM Tasks

The KiCad MCP Server provides several prompt templates for BOM-related tasks:

1. **Analyze Components** - Help with analyzing your component usage
2. **Cost Estimation** - Assistance with estimating project costs
3. **BOM Export Help** - Guidance on exporting BOMs from KiCad
4. **Component Sourcing** - Help with finding and sourcing components
5. **BOM Comparison** - Compare BOMs between different project versions

To use these prompts, click on the prompt templates button in your MCP client, then select the desired BOM template.

## Understanding BOM Results

### Component Categories

The BOM analysis provides a breakdown of component categories, such as:

| Category | Description | Example Components |
|----------|-------------|-------------------|
| Resistors | Current-limiting or voltage-dividing components | R1, R2, R3 |
| Capacitors | Energy storage and filtering components | C1, C2, C3 |
| ICs | Integrated circuits | U1, U2, U3 |
| Connectors | Board-to-board or board-to-wire connectors | J1, J2, J3 |
| Transistors | Switching or amplifying components | Q1, Q2, Q3 |
| Diodes | Unidirectional current flow components | D1, D2, D3 |

### Cost Information

The BOM analysis will attempt to extract cost information if it's available in your BOM file. This includes:

- Individual component costs
- Total project cost
- Breakdown of cost by component type

To include cost information in your BOM, add a "Cost" or "Price" column to your KiCad component fields, or include this information when exporting your BOM.

## Tips for Better BOM Management

### Structure Your BOM Export

When exporting a BOM from KiCad:

1. Use descriptive component values
2. Add meaningful component descriptions
3. Group components logically
4. Include footprint information
5. Add supplier part numbers where possible
6. Include cost information for better estimates

### Optimize Your Component Selection

Based on BOM analysis, consider:

- Standardizing component values (e.g., using the same resistor values across the design)
- Reducing the variety of footprints
- Selecting commonly available components
- Using components from the same supplier where possible
- Finding alternatives for expensive or hard-to-find components

### Keep BOM Files Updated

When making changes to your schematic:

1. Re-export your BOM after significant changes
2. Compare with previous versions to identify changes
3. Verify that all components are still available
4. Update cost estimates regularly

## Troubleshooting

### BOM Analysis Fails

If BOM analysis fails:

1. Ensure your BOM file is in a supported format (CSV, XML, or JSON)
2. Check that the file is not corrupted or empty
3. Verify that the BOM file is in your project directory
4. Try exporting a new BOM from KiCad
5. Check for unusual characters or formatting in your BOM

### BOM Export Fails

If BOM export fails:

1. Make sure KiCad is properly installed on your system
2. Verify that your schematic file exists and is valid
3. Check that you have write permissions in your project directory
4. Look for KiCad command-line tools in your KiCad installation
5. Try exporting manually from KiCad to see if there are specific errors

## Advanced Usage

### Custom BOM Analysis

For deeper analysis of your BOM, you can ask specific questions about:

1. Component distribution
2. Cost optimization
3. Footprint standardization
4. Supply chain considerations
5. Design for manufacturing improvements

Simply ask with your specific query, referencing your BOM:

```
Looking at the BOM for my project at /path/to/project.kicad_pro, can you suggest ways to reduce the variety of resistor values while maintaining the same functionality?
```

### Comparing Multiple Projects

To compare BOMs across different projects or revisions:

```
Can you compare the BOMs between my projects at /path/to/project_v1.kicad_pro and /path/to/project_v2.kicad_pro?
```

This allows you to see how component selection evolves across design iterations.

---
id: PRD-001
title: KiCad MCP Server Product Requirements
status: accepted
created: 2026-03-05
---

# PRD-001: KiCad MCP Server

## Problem Statement

Electronic engineers using AI assistants lack a standardized way to query, analyze, and manipulate KiCad EDA projects through natural language. KiCad files use complex binary-adjacent formats (S-expressions for schematics and PCB layouts, JSON for project files) that AI assistants cannot directly parse or reason about. Engineers must manually extract information — component lists, netlist connections, design rule violations — and paste it into chat contexts, breaking their workflow.

The Model Context Protocol (MCP) defines a standard interface for giving AI assistants structured access to external tools and data sources. A KiCad MCP server bridges the gap between AI assistants and KiCad project files, enabling natural language interaction with EDA workflows without leaving the design environment.

## Goals

- Provide MCP-compliant tools, resources, and prompts that expose KiCad project data to any MCP client.
- Support all major KiCad file formats: `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.net`.
- Enable AI assistants to perform read-heavy analysis tasks (BOM, netlist, DRC results, PCB metrics) without modifying source files.
- Allow AI assistants to create and modify KiCad projects through well-defined tools with appropriate safeguards.
- Run on macOS, Windows, and Linux with Python 3.10 or higher.

## Non-Goals

- This server does not replace the KiCad GUI application.
- This server does not implement a KiCad renderer or a design rule engine from scratch; it delegates to `kicad-cli` where feasible.
- This server does not provide a web interface or REST API.
- SPICE simulation and third-party format import (Eagle, Altium) are out of scope for the initial release.

## Requirements

### Functional Requirements

#### FR-1: Project Management

- The server must discover KiCad projects in user-configured search paths (`KICAD_SEARCH_PATHS` environment variable).
- The server must list all discovered projects sorted by modification date.
- The server must expose per-project metadata: name, path, last modified, file inventory.
- The server must support opening a project in the KiCad GUI application.

#### FR-2: PCB Design Analysis

- The server must parse `.kicad_pcb` files and report component count, board dimensions, and layer stack.
- The server must compute component density metrics and spatial distribution.
- The server must generate thumbnail previews of PCB layouts as image data.

#### FR-3: Netlist Extraction

- The server must extract component-to-net connectivity from `.kicad_sch` schematic files.
- The server must support both S-expression and JSON netlist formats.
- The server must report all nets connected to a named component or pin.

#### FR-4: Bill of Materials

- The server must aggregate component references, values, and footprints into a BOM.
- The server must export BOMs in CSV format.
- The server must support filtering and grouping by value or footprint.

#### FR-5: Design Rule Checking

- The server must invoke `kicad-cli` to run DRC on a PCB file.
- The server must parse and structure DRC output into typed violation records.
- The server must persist DRC history to allow tracking progress over time.
- The server must compare the current DRC result against a prior baseline.

#### FR-6: Circuit Pattern Recognition

- The server must identify common analog and digital circuit topologies within schematics.
- Supported patterns must include: voltage regulators (linear, buck, boost), decoupling networks, pull-up/pull-down resistors, protection diodes, and oscillator circuits.
- The server must report the confidence level and matched component references for each identified pattern.

#### FR-7: Prompt Templates

- The server must expose reusable prompt templates for common EDA tasks: PCB review, BOM analysis, DRC debugging, component selection, and schematic review.

#### FR-8: Text-to-Schematic

- The server must provide tools to create new KiCad schematic files from structured text descriptions.
- Generated schematics must be compatible with KiCad 9.0 or higher.
- Component placement, wiring, and property assignment must be supported.

### Non-Functional Requirements

#### NFR-1: Compatibility

- Python 3.10, 3.11, 3.12, and 3.13 must all be supported.
- The server must be compatible with any MCP-compliant client, not only Claude Desktop.
- KiCad 9.0 or higher must be supported.

#### NFR-2: Security

- All file path inputs must be validated against configured search paths to prevent path traversal.
- All `kicad-cli` subprocess invocations must use argument lists (not shell strings) to prevent command injection.
- XML parsing must use `defusedxml` to prevent XML entity expansion attacks.
- Temporary files must be cleaned up on server shutdown.

#### NFR-3: Reliability

- All MCP tool functions must be `async` and must not block the event loop during file I/O or subprocess calls.
- Errors in individual tools must not crash the server process; tools must return structured error responses.
- Graceful shutdown must clean up all temporary directories and registered cleanup handlers.

#### NFR-4: Testability

- All new functionality must be developed following Test-Driven Development (TDD): write a failing test before implementing.
- The test suite must be runnable with `uv run pytest tests/ -v`.
- Coverage must not fall below 30% (enforced by CI); the target coverage is 80%+.
- Tests must be organized into `tests/unit/`, `tests/integration/`, and `tests/fixtures/`.

#### NFR-5: Configuration

- Server behavior must be configurable via environment variables and `.env` files.
- Key variables: `KICAD_SEARCH_PATHS`, `KICAD_USER_DIR`, `KICAD_APP_PATH`.
- Sensible platform-specific defaults must be provided for macOS, Windows, and Linux.

## MCP Component Inventory

### Resources (read-only data)

| URI Pattern | Description |
|---|---|
| `kicad://projects` | List of all discovered KiCad projects |
| `kicad://projects/{project_id}` | Metadata for a specific project |
| `kicad://files/{project_id}` | File inventory for a project |
| `kicad://drc/{project_id}` | Latest DRC results for a project |
| `kicad://bom/{project_id}` | Bill of materials for a project |
| `kicad://netlist/{project_id}` | Netlist data for a project |
| `kicad://patterns/{project_id}` | Recognized circuit patterns for a project |

### Tools (actions and computations)

| Tool Module | Key Tools |
|---|---|
| `project_tools` | list_projects, get_project, open_project |
| `analysis_tools` | analyze_pcb, get_board_stats |
| `bom_tools` | generate_bom, export_bom_csv |
| `netlist_tools` | extract_netlist, get_component_connections |
| `drc_tools` | run_drc, get_drc_history, compare_drc |
| `pattern_tools` | identify_patterns, list_known_patterns |
| `circuit_tools` | create_circuit, add_component, connect_components |
| `text_to_schematic` | create_schematic_from_text |
| `visualization_tools` | generate_pcb_thumbnail |
| `export_tools` | export_gerber, export_pdf |
| `validation_tools` | validate_schematic, validate_pcb |

### Prompts (reusable templates)

| Prompt | Purpose |
|---|---|
| `review_pcb` | Guide a full PCB design review |
| `debug_pcb_issues` | Help troubleshoot DRC violations |
| `analyze_bom` | Assist with BOM analysis and sourcing |
| `identify_patterns` | Walk through circuit pattern recognition |
| `design_circuit` | Step-by-step circuit design assistance |

## Future Development

The following capabilities are out of scope for the current release but are tracked as future work:

1. 3D model visualization (STEP/VRML export and rendering)
2. PCB review annotation features
3. Manufacturing file generation (Gerber, drill, pick-and-place)
4. Component library search across KiCad symbol and footprint libraries
5. BOM supplier integration for component sourcing and pricing
6. Hierarchical schematic support
7. Third-party format import (Eagle, Altium, LTSpice)
8. SPICE simulation integration
9. Web interface for configuration and monitoring
10. KiCad Python scripting API integration

# CLAUDE.md

This file provides guidance to Claude Code when working with the KiCad MCP project.

## Project Overview

KiCad MCP is a Model Context Protocol (MCP) server that provides tools for working with KiCad electronic design automation (EDA) files. It enables AI assistants to interact with KiCad projects, schematics, PCBs, and related files through a standardized interface.

## Key Architecture Components

### MCP Server Structure
- **FastMCP Framework**: Uses the FastMCP framework for implementing MCP tools
- **Tool Modules**: Organized into separate modules (project, circuit, netlist, export, DRC, BOM, etc.)
- **Resource Handlers**: Provide access to KiCad project files and data
- **Utility Libraries**: Common functionality for file parsing, temp directory management, etc.

### KiCad File Format Support

Based on the KiCad source documentation, this project should handle:

#### S-Expression Format (.kicad_sch, .kicad_pcb, .kicad_pro)
- **Lexer/Parser**: KiCad uses generated lexers from `.keywords` files for parsing S-expressions
- **Schematic Files**: Use `TSCHEMATIC_T` token types for schematic parsing
- **PCB Files**: Use `PCB_KEYS_T` token types for PCB parsing  
- **Netlist Files**: Use `NL_T` token types for netlist parsing

#### File Types to Support
- `.kicad_pro` - Project files (JSON format)
- `.kicad_sch` - Schematic files (S-expression format)
- `.kicad_pcb` - PCB layout files (S-expression format)
- `.net` - Netlist files
- BOM exports (CSV, HTML, etc.)
- Gerber files and drill files
- 3D model files

### Current Implementation Status

#### Working Components
- **Project Discovery**: Listing and finding KiCad projects
- **JSON Schematic Parsing**: Custom JSON format for schematic representation
- **Netlist Extraction**: Both JSON and S-expression format support
- **Circuit Creation**: Tools for creating new circuits and adding components
- **Basic Export**: Some export functionality

#### Areas for Improvement
- **S-Expression Parsing**: Should align with KiCad's native parsing approach
- **Component Libraries**: Integration with KiCad component libraries
- **Pin-Level Connectivity**: More detailed component pin analysis
- **Native File Format**: Generate files compatible with KiCad application

## Development Guidelines

### File Format Compatibility
- **Primary Goal**: Generate files readable by KiCad application
- **S-Expression Standard**: Follow KiCad's S-expression format specification
- **JSON Support**: Maintain JSON format for internal processing but convert to S-expression for KiCad compatibility

### Code Organization
- **Tool Modules**: Each major functionality area has its own tool module
- **Async Operations**: All MCP tools are async functions
- **Error Handling**: Graceful error handling with informative messages
- **Testing**: Comprehensive unit and integration tests

### Key Files and Directories
- `kicad_mcp/server.py` - Main MCP server implementation
- `kicad_mcp/tools/` - Individual tool modules
- `kicad_mcp/utils/` - Utility functions for file parsing, etc.
- `kicad_mcp/resources/` - MCP resource handlers
- `tests/` - Comprehensive test suite

### Testing Strategy

#### Test-Driven Development (TDD) - MANDATORY
**ALL new features and bug fixes MUST follow TDD principles:**

1. **RED Phase**: Write a failing test that describes the desired behavior
2. **GREEN Phase**: Write minimal code to make the test pass
3. **REFACTOR Phase**: Clean up code while keeping tests green

**TDD Implementation Rules:**
- Write tests BEFORE implementing functionality
- Each test should focus on a single behavior
- Tests must be automated and repeatable
- All tests must pass before code is committed
- Coverage should be comprehensive but not excessive

**Test Categories:**
- **Unit Tests**: Individual function and class testing
- **Integration Tests**: End-to-end workflow testing
- **Fixtures**: Sample KiCad files for testing
- **Performance Tests**: Large project handling
- **Format Compatibility**: Ensure generated files work with KiCad

**Test Commands:**
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v           # Unit tests only
python -m pytest tests/integration/ -v   # Integration tests only

# Run with coverage
python -m pytest tests/ --cov=kicad_mcp --cov-report=html

# Run tests for specific module
python -m pytest tests/unit/utils/test_component_layout.py -v
```

**Test Structure:**
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for complete workflows
- `tests/fixtures/` - Sample KiCad files and test data
- `tests/conftest.py` - Shared test configuration and fixtures

## KiCad Integration Details

### Schematic I/O
Based on KiCad source, schematic I/O supports:
- **KiCad S-Expression**: Native format (`sch_io_kicad_sexpr`)
- **Legacy Format**: Older KiCad format (`sch_io_kicad_legacy`)  
- **Third-Party Formats**: Eagle, Altium, Cadstar, LTSpice, EasyEDA

### Netlist Processing
- **Netlist Reader**: `board_netlist_updater.cpp`, `netlist.cpp`
- **Format Support**: Standard netlist formats, SPICE export
- **Component Connectivity**: Pin-to-pin connections, net analysis

### Component Libraries
- **Symbol Libraries**: `.kicad_sym` files
- **Footprint Libraries**: `.pretty` directories with `.kicad_mod` files
- **Library Tables**: `sym-lib-table`, `fp-lib-table` for library management

### Export Capabilities
- **Gerber Generation**: Manufacturing files
- **BOM Export**: Bill of materials in various formats
- **3D Export**: STEP, VRML formats
- **PDF Export**: Schematic and PCB documentation

## Technical Implementation Notes

### Parser Generation
KiCad uses CMake's `make_lexer` function to generate parsers from keyword files:
```cmake
make_lexer(
    target
    keywords_file.keywords
    output_lexer.h
    output_keywords.cpp
    TOKEN_TYPE
)
```

### S-Expression Structure
KiCad S-expressions follow Lisp-like syntax:
```
(kicad_sch (version 20230121) (generator eeschema)
  (symbol (lib_id "Device:R") (at 63.5 87.63 0)
    (property "Reference" "R1")
    (property "Value" "10k")
  )
)
```

### Key Token Types
- `TSCHEMATIC_T` - Schematic file tokens
- `PCB_KEYS_T` - PCB file tokens  
- `NL_T` - Netlist tokens
- `DRCRULE_T` - Design rule check tokens

## Development Priorities

### High Priority
1. **S-Expression Compatibility**: Ensure generated files are KiCad-compatible
2. **Component Pin Analysis**: Implement proper pin-to-pin connectivity
3. **Library Integration**: Support for component and footprint libraries
4. **Test Coverage**: Comprehensive testing of all file formats

### Medium Priority
1. **Advanced Export**: Gerber, drill, pick-and-place files
2. **Design Rule Checking**: DRC integration
3. **3D Model Support**: Component 3D models and visualization
4. **Hierarchical Sheets**: Support for hierarchical schematic design

### Lower Priority
1. **Third-Party Import**: Eagle, Altium file import
2. **Advanced Simulation**: SPICE integration
3. **Python Scripting**: KiCad Python API integration
4. **Web Interface**: Browser-based project management

## Security Considerations
- **File Access**: Limit access to designated project directories
- **Command Injection**: Sanitize all KiCad CLI commands
- **Temp Files**: Proper cleanup of temporary files
- **Path Traversal**: Validate all file paths for security

## Performance Guidelines
- **Large Projects**: Handle projects with thousands of components
- **Memory Usage**: Efficient parsing of large schematic files
- **Async Operations**: Non-blocking file operations
- **Caching**: Cache parsed project data when appropriate
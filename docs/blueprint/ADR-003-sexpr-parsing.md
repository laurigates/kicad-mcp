---
id: ADR-003
title: S-Expression Parsing Approach for KiCad File Formats
status: accepted
created: 2026-03-05
---

# ADR-003: S-Expression Parsing Approach for KiCad File Formats

## Status

Accepted

## Context

KiCad stores schematic files (`.kicad_sch`) and PCB layout files (`.kicad_pcb`) in an S-expression format derived from Lisp syntax. A minimal example:

```
(kicad_sch (version 20230121) (generator eeschema)
  (symbol (lib_id "Device:R") (at 63.5 87.63 0)
    (property "Reference" "R1")
    (property "Value" "10k")
  )
)
```

The server needs to read, traverse, and in some cases generate this format to:
1. Extract component references, values, and footprints for BOM generation.
2. Parse netlist connectivity for the netlist extraction feature.
3. Read DRC rule files and PCB constraint layers.
4. Generate `.kicad_sch` files for the text-to-schematic feature.

Several approaches were evaluated:

### Option A: Write a Custom S-expression Parser

Implement a recursive-descent or regex-based parser from scratch. Full control over the AST structure, error messages, and round-trip formatting.

### Option B: Use the `sexpdata` Library

`sexpdata` is a pure-Python S-expression parser that parses S-expressions into nested Python lists and `Symbol` objects. It handles quoted strings, numbers, and nested lists. It does not require a grammar definition.

### Option C: Use the KiCad Python API (`pcbnew`)

KiCad ships a Python scripting module (`pcbnew`) that exposes the full KiCad object model. The MCP server could use this for all file access, delegating parsing to KiCad itself.

### Option D: Call `kicad-cli` for All File Operations

Delegate all parsing to `kicad-cli` subprocesses. Export data in JSON or CSV and parse those well-supported formats instead.

## Decision

The project uses a **layered approach**:

1. **`sexpdata` for direct S-expression parsing** (`kicad_mcp/utils/sexpr_handler.py`, `kicad_mcp/utils/sexpr_service.py`): Used for reading `.kicad_sch` and `.kicad_pcb` files where in-process parsing is required for performance or when `kicad-cli` output is insufficient. `sexpdata` handles the tokenization and nesting; the server's utility layer provides domain-specific traversal helpers on top.

2. **`kicad-cli` subprocess delegation** (`kicad_mcp/utils/kicad_cli.py`): Used for DRC execution, where `kicad-cli drc` produces structured JSON output. Subprocess calls use argument list form (not shell strings) through `kicad_mcp/utils/secure_subprocess.py` to prevent command injection.

3. **JSON format for internal representation**: Project files (`.kicad_pro`) are already JSON and are parsed with the standard library `json` module. Internally, netlist data and component graphs are kept as Python dicts and dataclasses to decouple internal logic from the S-expression wire format.

The KiCad Python API (`pcbnew`) and full `kicad-cli` delegation for all operations were both rejected as primary approaches (see Consequences).

## Consequences

### Positive

- `sexpdata` is a lightweight, pure-Python dependency with no C extensions, making it easy to install across all supported platforms and Python versions without binary wheel concerns.
- The layered approach means that features not requiring S-expression manipulation (BOM, project listing) avoid parsing overhead entirely.
- Delegating DRC to `kicad-cli` ensures DRC results are authoritative — produced by the same engine that KiCad's GUI uses — without requiring KiCad's Python API.
- Internal JSON/dataclass representation isolates the rest of the codebase from S-expression parsing details, making it easier to test business logic without real KiCad files.

### Negative

- `sexpdata` does not produce a typed AST aligned with KiCad's internal token types (`TSCHEMATIC_T`, `PCB_KEYS_T`). Traversal code in `sexpr_handler.py` must use list indexing and symbol comparisons rather than a structured grammar, making it fragile to KiCad format version changes.
- Writing new `.kicad_sch` files (text-to-schematic feature) requires constructing S-expression trees manually from Python lists, which is tedious and must be validated against KiCad's format spec by loading the output in KiCad.
- `kicad-cli` subprocess calls introduce a runtime dependency on KiCad being installed, which is unavailable in CI environments without special setup. Tests that require `kicad-cli` must be marked `@pytest.mark.requires_kicad` and skipped in standard CI runs.
- Pin-level connectivity analysis is incomplete because `sexpdata` parsing does not yet fully model all schematic primitives (bus entries, hierarchical labels). This is noted as a high-priority improvement area in CLAUDE.md.

### Neutral

- `defusedxml` is used for any XML parsing (some older KiCad export formats use XML) to guard against XML entity expansion attacks, consistent with the project's security guidelines.
- The version management utility (`kicad_mcp/utils/version.py`) centralizes the KiCad file format version constants so that generated files declare the correct version token regardless of which tool module produces them.

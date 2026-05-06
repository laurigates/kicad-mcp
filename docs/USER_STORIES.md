# KiCad MCP — User Stories & Test Coverage Map

This document captures the user stories the KiCad MCP server is intended to
support, mapped to the tools/resources that back them and the tests that
verify them. It exists to:

1. Make the *intended* behavior of each MCP tool reviewable as text.
2. Highlight blind spots in test coverage so gaps can be triaged.
3. Provide a stable target when adding new features or refactoring tools.

When you add or change a tool, update the relevant story row(s) in the same
PR. When you add a test that fills a gap, flip the coverage column.

## Personas

- **Hobbyist Designer** — bootstrapping small projects (LED drivers, MCU
  boards) with low KiCad expertise; relies on the AI to generate scaffolding.
- **Professional EE** — uses the AI to accelerate review, refactoring, and
  documentation of existing designs; cares deeply about correctness.
- **Educator / Learner** — explores designs, asks "what does this do?", and
  builds tutorials.
- **Manufacturing / Procurement** — needs BOMs, sourcing data, pre-fab
  checks, and Gerber-style outputs.
- **Hardware Reviewer / Auditor** — runs DRC, validates structure, and tracks
  regressions across revisions.

## Coverage legend

- ✅ — direct test exercises the MCP tool entry point
- ⚠️ — only an underlying utility is tested, not the tool itself
- ❌ — no test coverage
- — — not applicable (e.g. prompt-only flow)

## Hobbyist Designer

| ID | Story | Tools | Coverage |
|----|-------|-------|----------|
| H1 | Create a new KiCad project from a name + description | `create_new_project` | ✅ `tests/unit/tools/test_circuit_tools.py` |
| H2 | Describe a circuit in YAML/Mermaid-style text and get a working schematic | `create_kicad_schematic_from_text` | ⚠️ parser only (`test_text_to_schematic_parsers.py`); no end-to-end |
| H3 | Add a component (R, C, MCU…) at given coordinates | `add_component` | ✅ |
| H4 | Add a power symbol (VCC/GND/+5V/+3V3) | `add_power_symbol` | ✅ |
| H5 | Connect two points with a wire | `create_wire_connection` | ⚠️ minimal |
| H6 | Open the generated project in KiCad | `open_project` | ❌ |
| H7 | See a thumbnail of the schematic / PCB | `capture_schematic_screenshot`, `capture_pcb_screenshot`, `generate_pcb_thumbnail` | ❌ |

## Professional EE

| ID | Story | Tools | Coverage |
|----|-------|-------|----------|
| P1 | List every KiCad project under one or more search directories | `list_projects` | ❌ |
| P2 | Inspect the file structure and metadata of a project | `get_project_structure` | ❌ |
| P3 | Validate a project has the essential KiCad files | `validate_project` | ❌ |
| P4 | Validate a schematic for missing values, unconnected pins, etc. | `validate_schematic` | ✅ |
| P5 | Validate component placement against board boundaries | `validate_project_boundaries` | ✅ `test_validation_tools.py` |
| P6 | Extract a netlist with component and net counts | `extract_schematic_netlist`, `extract_project_netlist` | ⚠️ parser only |
| P7 | Find every connection touching a single component (e.g. U3) | `find_component_connections` | ❌ |
| P8 | Categorize nets (power vs signal) and surface floating nets | `analyze_schematic_connections` | ❌ |
| P9 | Export the schematic as SVG/PNG for documentation | `export_schematic_svg`, `convert_svg_to_png` | ❌ |

## Educator / Learner

| ID | Story | Tools / Prompts | Coverage |
|----|-------|-----------------|----------|
| L1 | Identify the major circuit blocks in a schematic (power, amp, filter, MCU…) | `identify_circuit_patterns`, `analyze_project_circuit_patterns` | ⚠️ recognizers tested, tool wrapper not |
| L2 | Get a plain-language explanation of what a circuit does | `explain_circuit_function` prompt | — |
| L3 | Compare two schematics side by side | `compare_circuit_patterns` prompt, `bom_comparison` prompt | — |

## Manufacturing / Procurement

| ID | Story | Tools / Prompts | Coverage |
|----|-------|-----------------|----------|
| M1 | Export a CSV BOM for a contract manufacturer | `export_bom_csv` | ❌ |
| M2 | Analyze an existing BOM (counts, categories, cost) | `analyze_bom` | ❌ |
| M3 | Generate a PCB thumbnail image for documentation | `generate_pcb_thumbnail`, `generate_project_thumbnail` | ❌ |
| M4 | Walk through a pre-manufacturing checklist | `pcb_manufacturing_checklist` prompt | — |
| M5 | Export Gerber and drill files | **— missing tool —** | gap |

## Hardware Reviewer / Auditor

| ID | Story | Tools | Coverage |
|----|-------|-------|----------|
| R1 | Run DRC on a PCB and surface violations | `run_drc_check` | ❌ |
| R2 | View DRC trend over time (improving / degrading / stable) | `get_drc_history_tool` | ⚠️ history util tested, tool not |
| R3 | Confirm generated files actually round-trip through `kicad-cli` | (implicit) | ⚠️ partial in `test_kicad_compatibility` |

## Cross-cutting / Non-functional

| ID | Story | Coverage |
|----|-------|----------|
| N1 | Path-traversal protection on all `*_path` parameters | ✅ `test_path_validator` |
| N2 | `kicad-cli` subprocess execution is sandboxed | ✅ `test_secure_subprocess` |
| N3 | Concurrent tool calls do not corrupt shared temp dirs | ⚠️ one integration test |
| N4 | Generated S-expression files are byte-compatible with KiCad | ✅ `test_kicad_boolean_compatibility`, version freshness tests |

## Top blind spots (ranked by user impact × likelihood of breaking)

1. **DRC tool itself** (R1) — the headline auditor feature has zero behavior tests.
2. **BOM export & analysis** (M1, M2) — manufacturing workflow is completely untested.
3. **Project discovery** (P1, P2, P3) — first thing every persona does, no tests.
4. **Pattern recognition tool wrappers** (L1) — recognizers tested, MCP tool not.
5. **Netlist tool wrappers** (P6, P7, P8) — same shape: util tested, tool not.
6. **Visualization pipeline** (H7, P9, M3) — SVG → PNG → Image return path untested end-to-end.
7. **Text-to-schematic happy path** (H2) — parser tested, but "text in → openable .kicad_sch out" round-trip is missing.
8. **Missing capability**: Gerber/drill export (M5) — listed as medium priority in `CLAUDE.md` but no tool exists yet.

## How to update this file

- Adding a new tool → add a row under the persona it primarily serves.
- Adding a test that closes a gap → flip the coverage cell from ❌/⚠️ to ✅.
- Removing a tool → strike through the row rather than delete, so the
  history of intent is preserved in `git log`.
- New personas should be rare; prefer reusing the five above.

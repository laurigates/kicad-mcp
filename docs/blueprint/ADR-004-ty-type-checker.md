---
id: ADR-004
title: Replace mypy with ty for Python Type Checking
status: accepted
created: 2026-04-24
supersedes: "ADR-002 (type checker selection only)"
---

# ADR-004: Replace mypy with ty for Python Type Checking

## Status

Accepted

## Context

ADR-002 included mypy in the `dev` dependency group as an optional static type checker. Type checking was not enforced in CI, so mypy saw limited use. Two developments since then prompted reconsideration:

1. Astral — the maintainer of `uv` and `ruff`, both already adopted by this project — released **`ty`**, a Rust-based Python type checker intended as a faster, more ergonomic alternative to mypy.
2. The project accumulated enough typed surface area (async tool functions, dataclasses, typed dicts for netlist and DRC results) that running a checker regularly became valuable, and mypy's per-run cost on a cold cache was noticeable.

The options considered were:

- **Keep mypy** and invest in tuning its configuration and cache behavior.
- **Switch to pyright** (Microsoft), which is fast and has broad editor integration but is a Node.js tool, adding a non-Python runtime dependency.
- **Switch to `ty`** (Astral), which is Rust-based, distributes as a Python wheel, and shares the same maintainer as the existing `uv` + `ruff` stack.

`ty` is still pre-1.0 (`0.0.1a*` release line at time of adoption). This is a known risk.

## Decision

The project uses **`ty`** as its Python type checker, replacing `mypy`. The `dev` dependency group declares `ty>=0.0.1a6,<0.1` and `mypy` is removed. A minimal `[tool.ty]` table is present in `pyproject.toml` to reserve configuration scope; project-wide strictness tuning is deferred until `ty` stabilises.

As with mypy, type checking is not yet a blocking gate in CI. It is run locally by contributors and expected to be promoted to a required CI job once `ty` reaches a stable release.

## Consequences

### Positive

- `ty` runs in a fraction of the time mypy took on the same codebase, making it practical to run on every save during development.
- Aligning on a single maintainer (Astral) for `uv`, `ruff`, and `ty` reduces the number of tool ecosystems contributors must track.
- Distribution as a Python wheel keeps installation inside the `uv sync --group dev` flow with no extra runtimes required.
- A focused cleanup pass (PR #80) resolved the set of real type errors `ty` surfaced, improving the codebase's actual type correctness independent of the tool choice.

### Negative

- `ty` is pre-1.0. Its CLI flags, error codes, and configuration schema are expected to change before a stable release. Configuration in `pyproject.toml` may need updates tracking upstream releases.
- Error messages and rule coverage are not yet fully at parity with mypy. Edge cases (complex generics, protocol conformance) may be diagnosed differently or not at all.
- Editor integrations for `ty` are less mature than for mypy or pyright. Contributors using non-Astral-aware editors may need to fall back to running `ty` from the shell.

### Neutral

- The type-checker switch does not change the type annotation style in the codebase. Existing annotations compatible with mypy continue to work under `ty`.
- ADR-002's decision to use `ruff` for lint/format and `pytest` for testing is unaffected; only the mypy row of that ADR's decision table is superseded by this one.

---
id: ADR-001
title: Use FastMCP as the MCP Framework
status: accepted
created: 2026-03-05
---

# ADR-001: Use FastMCP as the MCP Framework

## Status

Accepted

## Context

The Model Context Protocol (MCP) is a specification for exposing tools, resources, and prompt templates to AI assistants. Implementing an MCP server requires handling the JSON-RPC wire protocol, capability negotiation, tool schema generation, and request routing. Doing this from scratch against the raw `mcp` SDK is verbose and error-prone.

At the time this project was initiated, two primary options existed for building Python MCP servers:

1. **Raw `mcp[cli]` SDK**: The official Anthropic-maintained Python SDK. Requires manual registration of tools, resources, and prompts using lower-level primitives. Provides complete control but demands significant boilerplate.

2. **FastMCP**: A higher-level framework built on top of the `mcp` SDK, inspired by FastAPI's decorator-driven design. Tools are registered by decorating ordinary async Python functions with `@mcp.tool()`. Schemas are derived from function signatures and docstrings via Python type hints, reducing boilerplate substantially.

The project needs to expose a large surface area: over a dozen tool modules, six resource endpoints, and five prompt templates. The team prioritized developer velocity and readability of tool definitions.

## Decision

The project uses **FastMCP** as the primary framework for implementing the MCP server. The raw `mcp[cli]` SDK is retained as a direct dependency because FastMCP depends on it internally, and it is needed to satisfy type constraints in some integration contexts.

The server is instantiated once at startup as `FastMCP("KiCad")` in `kicad_mcp/server.py`. Each feature area registers its tools, resources, and prompts by accepting the `FastMCP` instance and calling the appropriate registration helpers.

## Consequences

### Positive

- Tool definitions are concise: a decorated async function with typed parameters and a docstring is sufficient to expose an MCP tool with a complete JSON schema.
- New tools can be added by writing a single function and registering it in the appropriate module; no manual schema authoring is required.
- FastMCP handles transport negotiation (stdio, SSE) and capability advertisement automatically.
- The decorator pattern is familiar to developers who have used Flask or FastAPI, reducing onboarding time.

### Negative

- FastMCP is a third-party dependency that is not maintained by Anthropic. Breaking changes in FastMCP could require updates across all tool modules.
- The abstraction hides some low-level MCP protocol details, which can make debugging protocol-level issues harder.
- FastMCP's release cadence and long-term maintenance are less certain than the official `mcp` SDK.

### Neutral

- The `mcp[cli]` SDK must be pinned alongside FastMCP. Version conflicts between the two packages need to be managed in `pyproject.toml`.
- Tests that exercise MCP protocol behavior (tool listing, resource resolution) must account for FastMCP's internal routing rather than raw SDK behavior.

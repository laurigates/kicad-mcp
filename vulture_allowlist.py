"""Vulture allowlist for intentional "unused" names.

Vulture reports anything it cannot prove is referenced. Several idioms in this
codebase produce false positives — MCP tool/resource registrations referenced
only by decorators, FastMCP parameters introspected at runtime, and dataclass
fields consumed via serialization. List them here so `uv run vulture` stays
signal-heavy.

Any name added here should include a short comment explaining why it's needed.
Prefer fixing real dead code over adding allowlist entries.
"""

# FastMCP-registered handler functions are only referenced via the @mcp.tool /
# @mcp.resource / @mcp.prompt decorators, which vulture doesn't follow into the
# runtime registry. The `ignore_decorators` config in pyproject.toml covers
# most of these; anything leaking through goes here.

# pytest fixtures and hooks — referenced by name via dependency injection
_unused_pytest_fixtures = (
    "pytest_collection_modifyitems",
    "pytest_configure",
)

# Public API re-exports from __init__ modules — may appear unused within the
# package but are part of the external surface.
_unused_public_api: tuple[str, ...] = ()

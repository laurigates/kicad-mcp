---
id: ADR-002
title: Python Toolchain Choices (uv, ruff, pytest, hatchling)
status: accepted
created: 2026-03-05
---

# ADR-002: Python Toolchain Choices (uv, ruff, pytest, hatchling)

## Status

Accepted

## Context

The project needed to settle on a consistent set of tools for dependency management, linting, formatting, testing, and packaging. The Python ecosystem offers many options in each category. The team evaluated alternatives with a focus on speed, modern standards compliance, and low maintenance overhead.

### Dependency and Environment Management

The two primary modern options were **uv** (Astral) and **Poetry**. Traditional `pip` with `venv` was also considered but rejected early due to lack of lockfile support and slower resolution.

### Linting and Formatting

The dominant options were:
- **ruff** (Astral): A single Rust-based tool that replaces flake8, isort, pyupgrade, and black.
- **flake8 + isort + black**: The previous generation standard; requires coordinating multiple tools with overlapping concerns.
- **pylint**: Thorough but significantly slower and noisier in CI.

### Testing

**pytest** is the de facto standard for Python testing. The team also evaluated `unittest` (too verbose) and `ward` (too niche). pytest was selected with the following plugins:
- `pytest-asyncio` for testing async MCP tool functions.
- `pytest-cov` for coverage measurement.
- `pytest-xdist` for parallel test execution.
- `pytest-mock` for mocking KiCad CLI calls and file system operations.

### Build Backend

The two modern options were:
- **hatchling**: The build backend for the Hatch project management tool. Minimal configuration, PEP 517/518 compliant.
- **setuptools**: Mature but requires more configuration for modern projects.
- **flit**: Lightweight but limited for projects needing complex build customization.

## Decision

| Concern | Tool | Alternative Rejected |
|---|---|---|
| Dependency management | **uv** | Poetry, pip+venv |
| Linting | **ruff** | flake8 + isort |
| Formatting | **ruff format** | black |
| Testing | **pytest** | unittest |
| Build backend | **hatchling** | setuptools, flit |

Dependency groups are declared in `pyproject.toml` under `[dependency-groups]` using uv's native format, replacing `[project.optional-dependencies]`. The `dev` group includes pytest, ruff, mypy, pre-commit, and bandit. Additional groups (`docs`, `security`, `performance`, `visualization`) are available for optional capabilities.

The ruff configuration (`[tool.ruff]`) selects rule sets E, W, F, I, B, C4, UP, and SIM, targeting Python 3.11. `E501` (line too long) is ignored in favour of `ruff format`'s auto line wrapping at 100 characters.

pytest is configured via `[tool.pytest.ini_options]` with strict markers, async mode set to `auto`, and a coverage minimum of 30%.

## Consequences

### Positive

- **uv** resolves and installs dependencies in milliseconds compared to seconds or minutes with pip/Poetry. CI pipelines benefit noticeably.
- **ruff** replaces five separate tools with one binary that runs in under a second even on large codebases. Pre-commit hooks complete quickly, reducing friction.
- **hatchling** requires minimal configuration: a `[build-system]` table pointing to hatchling is sufficient for a standard Python package layout.
- All tool configurations live in `pyproject.toml`, keeping the repository root clean.
- `asyncio_mode = "auto"` in pytest means async test functions do not need `@pytest.mark.asyncio` decorators, reducing boilerplate across the large async tool surface.

### Negative

- **uv** is newer than Poetry and pip; its `[dependency-groups]` format is not yet universally supported by all tooling (e.g., some CI templates expect `[project.optional-dependencies]`).
- **ruff** does not yet cover every rule category that pylint or flake8-bugbear plugins provide. Some nuanced code quality checks require mypy or additional configuration.
- Developers unfamiliar with uv may need to install it separately (`curl -LsSf https://astral.sh/uv/install.sh | sh`) before they can contribute.

### Neutral

- mypy is included in the `dev` dependency group for optional static type checking. It is not enforced in CI at this time but is available for local use.
- bandit is included for security linting and is run in CI as a separate job (`security-scan`).
- The pre-commit configuration wires ruff, conventional commits validation (commitlint), trufflehog secret scanning, and actionlint for GitHub Actions workflow validation.

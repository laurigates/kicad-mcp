# Contributing to KiCad MCP

Thank you for your interest in contributing to KiCad MCP! This guide covers everything you need to get started.

## Getting Started

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/<your-username>/kicad-mcp.git
   cd kicad-mcp
   ```

2. Install dependencies (requires [uv](https://docs.astral.sh/uv/)):

   ```bash
   uv sync --group dev
   ```

3. Set up pre-commit hooks:

   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# With coverage report
uv run pytest tests/ --cov=kicad_mcp --cov-report=html
```

## Code Quality

Linting and formatting are enforced via pre-commit hooks and CI. You can run them manually:

```bash
# Lint
uv run ruff check kicad_mcp/

# Format
uv run ruff format kicad_mcp/

# Security checks
uv run bandit -c pyproject.toml -r kicad_mcp/
```

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/).

**Format:** `type(scope): description`

| Type       | Usage                              |
|------------|------------------------------------|
| `feat`     | New feature                        |
| `fix`      | Bug fix                            |
| `docs`     | Documentation changes              |
| `chore`    | Maintenance, dependencies, config  |
| `refactor` | Code restructuring (no behavior change) |
| `test`     | Adding or updating tests           |
| `ci`       | CI/CD pipeline changes             |

**Examples:**

```
feat(tools): add footprint library browser
fix(parser): handle empty S-expression nodes
docs: update installation instructions
test(bom): add coverage for multi-unit components
```

## Pull Request Process

1. Create a feature branch from `main`:

   ```bash
   git checkout -b feat/your-feature main
   ```

2. Make your changes following the conventions above.

3. Ensure all checks pass:

   ```bash
   uv run pytest tests/ -v
   uv run ruff check kicad_mcp/
   uv run ruff format --check kicad_mcp/
   ```

4. Push and open a pull request against `main`.

5. In your PR description, include:
   - A summary of the changes
   - A test plan describing how the changes were verified
   - References to any related issues (e.g., `Closes #123`)

## Project Structure

| Path | Description |
|------|-------------|
| `kicad_mcp/server.py` | Main MCP server |
| `kicad_mcp/tools/` | Tool modules (project, circuit, BOM, DRC, etc.) |
| `kicad_mcp/utils/` | Shared utilities and parsers |
| `kicad_mcp/resources/` | MCP resource handlers |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Integration tests |
| `tests/fixtures/` | Sample KiCad files for testing |

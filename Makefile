# KiCad MCP Makefile
# Provides common development tasks using uv

.PHONY: help install test test-unit test-integration coverage lint format clean dev run

# Default target
help:
	@echo "KiCad MCP Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install     - Install dependencies and sync environment"
	@echo "  dev         - Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test        - Run all tests"
	@echo "  test-unit   - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  coverage    - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code"
	@echo ""
	@echo "Development:"
	@echo "  run         - Run the MCP server"
	@echo "  clean       - Clean up temporary files"
	@echo ""
	@echo "Dependencies:"
	@echo "  lock        - Update lockfile"

# Install dependencies
install:
	uv sync

# Install development dependencies
dev:
	uv sync --dev

# Run all tests (matches CI command)
test:
	uv run python -m pytest tests/ -v --cov=kicad_mcp --cov-report=xml

# Run unit tests only
test-unit:
	uv run pytest tests/unit/ -v

# Run integration tests only
test-integration:
	uv run pytest tests/integration/ -v

# Run tests with coverage
coverage:
	uv run pytest tests/ --cov=kicad_mcp --cov-report=html --cov-report=term

# Run linting
lint:
	uv run ruff check .
	uv run mypy kicad_mcp/

# Format code
format:
	uv run ruff format .
	uv run ruff check --fix .

# Run the MCP server
run:
	uv run python -m kicad_mcp.server

# Update lockfile
lock:
	uv lock

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

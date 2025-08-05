"""
Test configuration parser for HTTP-based KiCad-MCP tests.

Handles JSON test configuration format with template substitution and validation.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class MCPCallConfig(BaseModel):
    """Configuration for a single MCP tool call."""

    tool: str = Field(..., description="Name of the MCP tool to call")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool call")


class ValidationConfig(BaseModel):
    """Configuration for a single validation step."""

    type: str = Field(..., description="Type of validation to perform")
    path: str = Field(..., description="File path to validate")
    expected: Any = Field(None, description="Expected value for validation")
    format: str = Field(None, description="Expected file format")


class TestConfig(BaseModel):
    """Complete test configuration."""

    test_name: str = Field(..., description="Unique name for the test")
    description: str = Field(..., description="Human-readable test description")
    mcp_calls: list[MCPCallConfig] = Field(
        default_factory=list, description="List of MCP tool calls to execute"
    )
    validations: list[ValidationConfig] = Field(
        default_factory=list, description="List of validation steps to perform"
    )
    timeout: int = Field(default=60, description="Test timeout in seconds")
    skip_cleanup: bool = Field(default=False, description="Skip cleanup for debugging")


class TestConfigLoader:
    """Loads and validates test configurations from JSON files."""

    def __init__(self):
        """Initialize test config loader."""
        self.loaded_configs: dict[str, TestConfig] = {}

    def load_config_file(self, config_path: str | Path) -> TestConfig:
        """Load test configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            Parsed and validated test configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If JSON is invalid
            ValidationError: If configuration is invalid
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with config_path.open("r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {config_path}: {e.msg}", e.doc, e.pos
            ) from e

        try:
            config = TestConfig(**config_data)
            self.loaded_configs[config.test_name] = config
            return config
        except ValidationError as e:
            raise ValidationError(f"Invalid configuration in {config_path}: {e}") from e

    def load_config_directory(self, config_dir: str | Path) -> dict[str, TestConfig]:
        """Load all test configurations from a directory.

        Args:
            config_dir: Directory containing JSON configuration files

        Returns:
            Dictionary mapping test names to configurations

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        config_dir = Path(config_dir)

        if not config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

        configs = {}
        for config_file in config_dir.glob("*.json"):
            try:
                config = self.load_config_file(config_file)
                configs[config.test_name] = config
            except Exception as e:
                print(f"Warning: Failed to load {config_file}: {e}")

        return configs

    def validate_config(self, config: TestConfig) -> list[str]:
        """Validate a test configuration for common issues.

        Args:
            config: Configuration to validate

        Returns:
            List of validation warnings/errors
        """
        issues = []

        # Check for duplicate tool calls
        tool_names = [call.tool for call in config.mcp_calls]
        if len(tool_names) != len(set(tool_names)):
            issues.append("Duplicate tool calls detected")

        # Check for missing required validations
        if not config.validations:
            issues.append("No validations specified")

        # Check validation paths contain template variables
        for validation in config.validations:
            if "{temp_dir}" not in validation.path:
                issues.append(
                    f"Validation path '{validation.path}' should use {{temp_dir}} template"
                )

        # Check for reasonable timeout
        if config.timeout < 5:
            issues.append("Timeout may be too short (< 5 seconds)")
        elif config.timeout > 300:
            issues.append("Timeout may be too long (> 5 minutes)")

        return issues

    def get_config(self, test_name: str) -> TestConfig | None:
        """Get a loaded configuration by name.

        Args:
            test_name: Name of the test configuration

        Returns:
            Test configuration or None if not found
        """
        return self.loaded_configs.get(test_name)

    def list_loaded_configs(self) -> list[str]:
        """Get list of loaded configuration names.

        Returns:
            List of test configuration names
        """
        return list(self.loaded_configs.keys())


def create_sample_config() -> dict[str, Any]:
    """Create a sample test configuration for reference.

    Returns:
        Sample configuration dictionary
    """
    return {
        "test_name": "basic_led_circuit",
        "description": "Create basic LED circuit with resistor",
        "mcp_calls": [
            {
                "tool": "create_new_project",
                "params": {
                    "project_name": "led_test",
                    "project_path": "{temp_dir}/led_test",
                },
            },
            {
                "tool": "create_kicad_schematic_from_text",
                "params": {
                    "project_path": "{temp_dir}/led_test/led_test.kicad_pro",
                    "circuit_description": (
                        'circuit "LED":\n'
                        "  components:\n"
                        "    - R1: resistor 220Ω at (50, 50)\n"
                        "    - LED1: led red at (100, 50)\n"
                        "  power:\n"
                        "    - VCC: +5V at (30, 30)\n"
                        "    - GND: GND at (30, 70)"
                    ),
                },
            },
        ],
        "validations": [
            {
                "type": "file_exists",
                "path": "{temp_dir}/led_test/led_test.kicad_pro",
            },
            {
                "type": "file_format",
                "path": "{temp_dir}/led_test/led_test.kicad_sch",
                "format": "sexpr",
            },
            {
                "type": "kicad_cli_validate",
                "path": "{temp_dir}/led_test/led_test.kicad_sch",
            },
            {
                "type": "component_count",
                "path": "{temp_dir}/led_test/led_test.kicad_sch",
                "expected": 2,
            },
            {
                "type": "power_symbol_count",
                "path": "{temp_dir}/led_test/led_test.kicad_sch",
                "expected": 2,
            },
        ],
        "timeout": 60,
        "skip_cleanup": False,
    }


def save_sample_config(output_path: str | Path) -> None:
    """Save a sample configuration to a file for reference.

    Args:
        output_path: Path where to save the sample configuration
    """
    config = create_sample_config()
    output_path = Path(output_path)

    with output_path.open("w") as f:
        json.dump(config, f, indent=2)

    print(f"Sample configuration saved to: {output_path}")

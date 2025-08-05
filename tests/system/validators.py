"""
File validation framework for HTTP-based KiCad-MCP tests.

Provides validators for different aspects of generated KiCad files.
"""

from abc import ABC, abstractmethod
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from kicad_mcp.utils.kicad_cli import get_kicad_cli_path, is_kicad_cli_available


class ValidationResult:
    """Result of a validation operation."""

    def __init__(
        self,
        success: bool,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        """Initialize validation result.

        Args:
            success: Whether validation passed
            message: Human-readable result message
            details: Optional additional details
        """
        self.success = success
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """String representation of result."""
        status = "PASS" if self.success else "FAIL"
        return f"[{status}] {self.message}"

    def __bool__(self) -> bool:
        """Boolean representation (True if validation passed)."""
        return self.success


class Validator(ABC):
    """Abstract base class for file validators."""

    @abstractmethod
    def validate(self, path: str, **kwargs: Any) -> ValidationResult:
        """Validate a file or aspect.

        Args:
            path: File path to validate
            **kwargs: Additional validation parameters

        Returns:
            Validation result
        """
        pass


class FileExistsValidator(Validator):
    """Validates that a file exists."""

    def validate(self, path: str, **kwargs: Any) -> ValidationResult:
        """Check if file exists."""
        file_path = Path(path)
        if file_path.exists():
            return ValidationResult(True, f"File exists: {path}")
        else:
            return ValidationResult(False, f"File not found: {path}")


class FormatValidator(Validator):
    """Validates file format (JSON or S-expression)."""

    def validate(self, path: str, format: str = "json", **kwargs: Any) -> ValidationResult:
        """Validate file format.

        Args:
            path: File path to validate
            format: Expected format ('json' or 'sexpr')
            **kwargs: Additional parameters

        Returns:
            Validation result
        """
        file_path = Path(path)

        if not file_path.exists():
            return ValidationResult(False, f"File not found: {path}")

        try:
            content = file_path.read_text()
        except Exception as e:
            return ValidationResult(False, f"Could not read file {path}: {e}")

        if format.lower() == "json":
            return self._validate_json(content, path)
        elif format.lower() in ("sexpr", "s-expression"):
            return self._validate_sexpr(content, path)
        else:
            return ValidationResult(False, f"Unknown format: {format}")

    def _validate_json(self, content: str, path: str) -> ValidationResult:
        """Validate JSON format."""
        try:
            json.loads(content)
            return ValidationResult(True, f"Valid JSON format: {path}")
        except json.JSONDecodeError as e:
            return ValidationResult(False, f"Invalid JSON in {path}: {e.msg} at line {e.lineno}")

    def _validate_sexpr(self, content: str, path: str) -> ValidationResult:
        """Validate S-expression format."""
        # Basic S-expression validation - check balanced parentheses
        paren_count = 0
        line_num = 1

        for _i, char in enumerate(content):
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
                if paren_count < 0:
                    return ValidationResult(
                        False,
                        f"Unmatched closing parenthesis in {path} at line {line_num}",
                    )
            elif char == "\n":
                line_num += 1

        if paren_count != 0:
            return ValidationResult(
                False, f"Unbalanced parentheses in {path} (missing {paren_count} closing)"
            )

        # Check for basic KiCad S-expression structure
        if not content.strip().startswith("("):
            return ValidationResult(False, f"S-expression must start with '(' in {path}")

        return ValidationResult(True, f"Valid S-expression format: {path}")


class KiCadCLIValidator(Validator):
    """Validates files using KiCad CLI tools."""

    def validate(self, path: str, **kwargs: Any) -> ValidationResult:
        """Validate file using KiCad CLI.

        Args:
            path: File path to validate
            **kwargs: Additional parameters

        Returns:
            Validation result
        """
        if not is_kicad_cli_available():
            return ValidationResult(False, "KiCad CLI not available for validation")

        file_path = Path(path)
        if not file_path.exists():
            return ValidationResult(False, f"File not found: {path}")

        try:
            cli_path = get_kicad_cli_path(required=True)
        except Exception as e:
            return ValidationResult(False, f"Could not get KiCad CLI path: {e}")

        # Determine validation command based on file extension
        if file_path.suffix == ".kicad_sch":
            return self._validate_schematic(cli_path, path)
        elif file_path.suffix == ".kicad_pcb":
            return self._validate_pcb(cli_path, path)
        elif file_path.suffix == ".kicad_pro":
            return self._validate_project(cli_path, path)
        else:
            return ValidationResult(False, f"Unknown KiCad file type: {file_path.suffix}")

    def _validate_schematic(self, cli_path: str, path: str) -> ValidationResult:
        """Validate schematic file."""
        try:
            # Try to export schematic to SVG as validation
            result = subprocess.run(
                [
                    cli_path,
                    "sch",
                    "export",
                    "svg",
                    "--output",
                    "/tmp/test_validation.svg",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return ValidationResult(True, f"KiCad CLI validation passed: {path}")
            else:
                return ValidationResult(
                    False,
                    f"KiCad CLI validation failed: {result.stderr}",
                    {"stdout": result.stdout, "stderr": result.stderr},
                )
        except subprocess.TimeoutExpired:
            return ValidationResult(False, f"KiCad CLI validation timeout: {path}")
        except Exception as e:
            return ValidationResult(False, f"KiCad CLI validation error: {e}")

    def _validate_pcb(self, cli_path: str, path: str) -> ValidationResult:
        """Validate PCB file."""
        try:
            # Try to export PCB info as validation
            result = subprocess.run(
                [cli_path, "pcb", "export", "gerbers", "--dry-run", path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return ValidationResult(True, f"KiCad CLI validation passed: {path}")
            else:
                return ValidationResult(
                    False,
                    f"KiCad CLI validation failed: {result.stderr}",
                    {"stdout": result.stdout, "stderr": result.stderr},
                )
        except subprocess.TimeoutExpired:
            return ValidationResult(False, f"KiCad CLI validation timeout: {path}")
        except Exception as e:
            return ValidationResult(False, f"KiCad CLI validation error: {e}")

    def _validate_project(self, cli_path: str, path: str) -> ValidationResult:
        """Validate project file."""
        # Project files are JSON, so validate JSON format
        format_validator = FormatValidator()
        return format_validator.validate(path, format="json")


class ComponentCountValidator(Validator):
    """Validates number of components in a schematic."""

    def validate(self, path: str, expected: int, **kwargs: Any) -> ValidationResult:
        """Count components in schematic file.

        Args:
            path: Schematic file path
            expected: Expected number of components
            **kwargs: Additional parameters

        Returns:
            Validation result
        """
        file_path = Path(path)
        if not file_path.exists():
            return ValidationResult(False, f"File not found: {path}")

        try:
            content = file_path.read_text()
        except Exception as e:
            return ValidationResult(False, f"Could not read file {path}: {e}")

        # Count symbol declarations in S-expression format
        symbol_count = len(re.findall(r"\(symbol\s+", content))

        if symbol_count == expected:
            return ValidationResult(
                True,
                f"Component count correct: {symbol_count} (expected {expected})",
                {"actual": symbol_count, "expected": expected},
            )
        else:
            return ValidationResult(
                False,
                f"Component count mismatch: {symbol_count} (expected {expected})",
                {"actual": symbol_count, "expected": expected},
            )


class PowerSymbolValidator(Validator):
    """Validates number of power symbols in a schematic."""

    def validate(self, path: str, expected: int, **kwargs: Any) -> ValidationResult:
        """Count power symbols in schematic file.

        Args:
            path: Schematic file path
            expected: Expected number of power symbols
            **kwargs: Additional parameters

        Returns:
            Validation result
        """
        file_path = Path(path)
        if not file_path.exists():
            return ValidationResult(False, f"File not found: {path}")

        try:
            content = file_path.read_text()
        except Exception as e:
            return ValidationResult(False, f"Could not read file {path}: {e}")

        # Count power symbols (VCC, GND, etc.)
        power_patterns = [
            r"\(lib_id\s+\"power:",  # Power library symbols
            r"\"VCC\"",
            r"\"GND\"",
            r"\+5V",
            r"\+3V3",
        ]

        power_count = 0
        for pattern in power_patterns:
            power_count += len(re.findall(pattern, content, re.IGNORECASE))

        if power_count == expected:
            return ValidationResult(
                True,
                f"Power symbol count correct: {power_count} (expected {expected})",
                {"actual": power_count, "expected": expected},
            )
        else:
            return ValidationResult(
                False,
                f"Power symbol count mismatch: {power_count} (expected {expected})",
                {"actual": power_count, "expected": expected},
            )


class ValidationRunner:
    """Runs multiple validators and collects results."""

    def __init__(self):
        """Initialize validation runner."""
        self.validators = {
            "file_exists": FileExistsValidator(),
            "file_format": FormatValidator(),
            "kicad_cli_validate": KiCadCLIValidator(),
            "component_count": ComponentCountValidator(),
            "power_symbol_count": PowerSymbolValidator(),
        }

    def run_validation(self, validation_type: str, path: str, **params: Any) -> ValidationResult:
        """Run a single validation.

        Args:
            validation_type: Type of validation to run
            path: File path to validate
            **params: Additional validation parameters

        Returns:
            Validation result
        """
        if validation_type not in self.validators:
            return ValidationResult(False, f"Unknown validation type: {validation_type}")

        validator = self.validators[validation_type]
        return validator.validate(path, **params)

    def run_all_validations(self, validations: list[dict[str, Any]]) -> list[ValidationResult]:
        """Run multiple validations.

        Args:
            validations: List of validation configurations

        Returns:
            List of validation results
        """
        results = []
        for validation in validations:
            validation_type = validation.get("type")
            path = validation.get("path")

            if not validation_type or not path:
                results.append(
                    ValidationResult(
                        False, "Invalid validation configuration: missing type or path"
                    )
                )
                continue

            # Extract additional parameters
            params = {k: v for k, v in validation.items() if k not in ("type", "path")}

            result = self.run_validation(validation_type, path, **params)
            results.append(result)

        return results

"""
Tests for the boundary validation system.
"""

import pytest

from kicad_mcp.utils.boundary_validator import (
    BoundaryValidator,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from kicad_mcp.utils.component_layout import SchematicBounds


class TestBoundaryValidator:
    """Test cases for the BoundaryValidator class."""

    def test_init_default_bounds(self):
        """Test initialization with default A4 bounds."""
        validator = BoundaryValidator()

        assert validator.bounds.width == 297.0
        assert validator.bounds.height == 210.0
        assert validator.bounds.margin == 20.0

    def test_init_custom_bounds(self):
        """Test initialization with custom bounds."""
        custom_bounds = SchematicBounds(width=200.0, height=150.0, margin=10.0)
        validator = BoundaryValidator(custom_bounds)

        assert validator.bounds.width == 200.0
        assert validator.bounds.height == 150.0
        assert validator.bounds.margin == 10.0

    def test_validate_component_position_valid(self):
        """Test validation of a valid component position."""
        validator = BoundaryValidator()

        # Position within usable area
        issue = validator.validate_component_position("R1", 50.0, 50.0, "resistor")

        assert issue.severity == ValidationSeverity.INFO
        assert issue.component_ref == "R1"
        assert issue.position == (50.0, 50.0)
        assert issue.suggested_position is None
        assert "valid" in issue.message.lower()

    def test_validate_component_position_outside_bounds(self):
        """Test validation of component position outside A4 bounds."""
        validator = BoundaryValidator()

        # Position outside A4 bounds
        issue = validator.validate_component_position("R1", 350.0, 250.0, "resistor")

        assert issue.severity == ValidationSeverity.ERROR
        assert issue.component_ref == "R1"
        assert issue.position == (350.0, 250.0)
        assert issue.suggested_position is not None
        assert "outside A4 bounds" in issue.message

    def test_validate_component_position_outside_usable_area(self):
        """Test validation of component position outside usable area but within bounds."""
        validator = BoundaryValidator()

        # Position within absolute bounds but outside usable area (too close to edge)
        issue = validator.validate_component_position("R1", 5.0, 5.0, "resistor")

        assert issue.severity == ValidationSeverity.WARNING
        assert issue.component_ref == "R1"
        assert issue.position == (5.0, 5.0)
        assert "outside usable area" in issue.message

    def test_validate_circuit_components_empty(self):
        """Test validation of empty component list."""
        validator = BoundaryValidator()

        report = validator.validate_circuit_components([])

        assert report.success is True
        assert report.total_components == 0
        assert report.out_of_bounds_count == 0
        assert len(report.issues) == 0

    def test_validate_circuit_components_valid(self):
        """Test validation of valid circuit components."""
        validator = BoundaryValidator()

        components = [
            {"reference": "R1", "position": (50.0, 50.0), "component_type": "resistor"},
            {"reference": "C1", "position": (100.0, 100.0), "component_type": "capacitor"},
        ]

        report = validator.validate_circuit_components(components)

        assert report.success is True
        assert report.total_components == 2
        assert report.out_of_bounds_count == 0
        assert len(report.issues) == 2
        assert all(issue.severity == ValidationSeverity.INFO for issue in report.issues)

    def test_validate_circuit_components_out_of_bounds(self):
        """Test validation of components with out-of-bounds positions."""
        validator = BoundaryValidator()

        components = [
            {"reference": "R1", "position": (50.0, 50.0), "component_type": "resistor"},
            {"reference": "R2", "position": (350.0, 250.0), "component_type": "resistor"},
        ]

        report = validator.validate_circuit_components(components)

        assert report.success is False
        assert report.total_components == 2
        assert report.out_of_bounds_count == 1
        assert len(report.issues) == 2
        assert "R2" in report.corrected_positions

    def test_validate_circuit_components_missing_position(self):
        """Test validation of components without position."""
        validator = BoundaryValidator()

        components = [
            {"reference": "R1", "component_type": "resistor"}  # No position
        ]

        report = validator.validate_circuit_components(components)

        assert report.success is True  # No out of bounds, just missing position
        assert report.total_components == 1
        assert report.validated_components == 0
        assert len(report.issues) == 1
        assert report.issues[0].severity == ValidationSeverity.INFO
        assert "no position specified" in report.issues[0].message

    def test_validate_circuit_components_invalid_position_format(self):
        """Test validation of components with invalid position format."""
        validator = BoundaryValidator()

        components = [{"reference": "R1", "position": "invalid", "component_type": "resistor"}]

        report = validator.validate_circuit_components(components)

        assert report.success is True  # No out of bounds, just invalid format
        assert report.total_components == 1
        assert len(report.issues) == 1
        assert report.issues[0].severity == ValidationSeverity.ERROR
        assert "invalid position format" in report.issues[0].message

    def test_validate_wire_connection_valid(self):
        """Test validation of valid wire connection."""
        validator = BoundaryValidator()

        issues = validator.validate_wire_connection(50.0, 50.0, 100.0, 100.0)

        assert len(issues) == 0

    def test_validate_wire_connection_invalid_start(self):
        """Test validation of wire connection with invalid start point."""
        validator = BoundaryValidator()

        issues = validator.validate_wire_connection(350.0, 50.0, 100.0, 100.0)

        assert len(issues) == 1
        assert issues[0].component_ref == "WIRE_START"
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "outside bounds" in issues[0].message

    def test_validate_wire_connection_invalid_end(self):
        """Test validation of wire connection with invalid end point."""
        validator = BoundaryValidator()

        issues = validator.validate_wire_connection(50.0, 50.0, 350.0, 250.0)

        assert len(issues) == 1
        assert issues[0].component_ref == "WIRE_END"
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "outside bounds" in issues[0].message

    def test_validate_wire_connection_both_invalid(self):
        """Test validation of wire connection with both invalid endpoints."""
        validator = BoundaryValidator()

        issues = validator.validate_wire_connection(350.0, 250.0, 400.0, 300.0)

        assert len(issues) == 2
        assert any(issue.component_ref == "WIRE_START" for issue in issues)
        assert any(issue.component_ref == "WIRE_END" for issue in issues)

    def test_auto_correct_positions(self):
        """Test automatic position correction."""
        validator = BoundaryValidator()

        components = [
            {"reference": "R1", "position": (50.0, 50.0), "component_type": "resistor"},
            {"reference": "R2", "position": (350.0, 250.0), "component_type": "resistor"},
        ]

        corrected_components, validation_report = validator.auto_correct_positions(components)

        assert len(corrected_components) == 2
        assert corrected_components[0]["position"] == (50.0, 50.0)  # No change
        assert corrected_components[1]["position"] != (350.0, 250.0)  # Changed
        assert validation_report.out_of_bounds_count == 1
        assert "R2" in validation_report.corrected_positions

    def test_generate_validation_report_text(self):
        """Test generation of text validation report."""
        validator = BoundaryValidator()

        # Create a validation report with issues
        components = [
            {"reference": "R1", "position": (50.0, 50.0), "component_type": "resistor"},
            {"reference": "R2", "position": (350.0, 250.0), "component_type": "resistor"},
            {"reference": "R3", "position": (5.0, 5.0), "component_type": "resistor"},
        ]

        report = validator.validate_circuit_components(components)
        report_text = validator.generate_validation_report_text(report)

        assert "BOUNDARY VALIDATION REPORT" in report_text
        assert "Total Components: 3" in report_text
        assert "Out of Bounds: 2" in report_text
        assert "ERRORS:" in report_text
        assert "WARNINGS:" in report_text
        assert "R2" in report_text
        assert "R3" in report_text

    def test_export_validation_report(self, tmp_path):
        """Test exporting validation report to JSON file."""
        validator = BoundaryValidator()

        components = [{"reference": "R1", "position": (350.0, 250.0), "component_type": "resistor"}]

        report = validator.validate_circuit_components(components)

        # Export to temporary file
        export_path = tmp_path / "validation_report.json"
        validator.export_validation_report(report, str(export_path))

        # Check file exists and has content
        assert export_path.exists()

        import json

        with open(export_path) as f:
            exported_data = json.load(f)

        assert exported_data["success"] is False
        assert exported_data["total_components"] == 1
        assert exported_data["out_of_bounds_count"] == 1
        assert len(exported_data["issues"]) == 1
        assert exported_data["issues"][0]["severity"] == "error"


class TestValidationReport:
    """Test cases for the ValidationReport class."""

    def test_has_errors_true(self):
        """Test has_errors returns True when errors exist."""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "R1", "Error message", (0, 0)),
            ValidationIssue(ValidationSeverity.WARNING, "R2", "Warning message", (0, 0)),
        ]

        report = ValidationReport(
            success=False,
            issues=issues,
            total_components=2,
            validated_components=2,
            out_of_bounds_count=1,
            corrected_positions={},
        )

        assert report.has_errors() is True

    def test_has_errors_false(self):
        """Test has_errors returns False when no errors exist."""
        issues = [
            ValidationIssue(ValidationSeverity.WARNING, "R1", "Warning message", (0, 0)),
            ValidationIssue(ValidationSeverity.INFO, "R2", "Info message", (0, 0)),
        ]

        report = ValidationReport(
            success=True,
            issues=issues,
            total_components=2,
            validated_components=2,
            out_of_bounds_count=0,
            corrected_positions={},
        )

        assert report.has_errors() is False

    def test_has_warnings_true(self):
        """Test has_warnings returns True when warnings exist."""
        issues = [
            ValidationIssue(ValidationSeverity.WARNING, "R1", "Warning message", (0, 0)),
            ValidationIssue(ValidationSeverity.INFO, "R2", "Info message", (0, 0)),
        ]

        report = ValidationReport(
            success=True,
            issues=issues,
            total_components=2,
            validated_components=2,
            out_of_bounds_count=0,
            corrected_positions={},
        )

        assert report.has_warnings() is True

    def test_has_warnings_false(self):
        """Test has_warnings returns False when no warnings exist."""
        issues = [
            ValidationIssue(ValidationSeverity.INFO, "R1", "Info message", (0, 0)),
            ValidationIssue(ValidationSeverity.INFO, "R2", "Info message", (0, 0)),
        ]

        report = ValidationReport(
            success=True,
            issues=issues,
            total_components=2,
            validated_components=2,
            out_of_bounds_count=0,
            corrected_positions={},
        )

        assert report.has_warnings() is False

    def test_get_issues_by_severity(self):
        """Test getting issues filtered by severity."""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "R1", "Error message", (0, 0)),
            ValidationIssue(ValidationSeverity.WARNING, "R2", "Warning message", (0, 0)),
            ValidationIssue(ValidationSeverity.INFO, "R3", "Info message", (0, 0)),
            ValidationIssue(ValidationSeverity.ERROR, "R4", "Another error", (0, 0)),
        ]

        report = ValidationReport(
            success=False,
            issues=issues,
            total_components=4,
            validated_components=4,
            out_of_bounds_count=2,
            corrected_positions={},
        )

        errors = report.get_issues_by_severity(ValidationSeverity.ERROR)
        warnings = report.get_issues_by_severity(ValidationSeverity.WARNING)
        info = report.get_issues_by_severity(ValidationSeverity.INFO)

        assert len(errors) == 2
        assert len(warnings) == 1
        assert len(info) == 1
        assert all(issue.severity == ValidationSeverity.ERROR for issue in errors)
        assert all(issue.severity == ValidationSeverity.WARNING for issue in warnings)
        assert all(issue.severity == ValidationSeverity.INFO for issue in info)


class TestValidationIssue:
    """Test cases for the ValidationIssue class."""

    def test_create_validation_issue(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            component_ref="R1",
            message="Test error message",
            position=(50.0, 50.0),
            suggested_position=(60.0, 60.0),
            component_type="resistor",
        )

        assert issue.severity == ValidationSeverity.ERROR
        assert issue.component_ref == "R1"
        assert issue.message == "Test error message"
        assert issue.position == (50.0, 50.0)
        assert issue.suggested_position == (60.0, 60.0)
        assert issue.component_type == "resistor"

    def test_create_validation_issue_minimal(self):
        """Test creating a validation issue with minimal parameters."""
        issue = ValidationIssue(
            severity=ValidationSeverity.INFO,
            component_ref="C1",
            message="Test info message",
            position=(100.0, 100.0),
        )

        assert issue.severity == ValidationSeverity.INFO
        assert issue.component_ref == "C1"
        assert issue.message == "Test info message"
        assert issue.position == (100.0, 100.0)
        assert issue.suggested_position is None
        assert issue.component_type == "default"


if __name__ == "__main__":
    pytest.main([__file__])

"""
Integration tests for boundary validation system.

Tests the complete boundary validation workflow from circuit generation
to validation reporting.
"""

import json
import os
from unittest.mock import AsyncMock, Mock

import pytest

from kicad_mcp.tools.text_to_schematic import TextToSchematicParser
from kicad_mcp.tools.validation_tools import generate_validation_report, validate_project_boundaries
from kicad_mcp.utils.boundary_validator import BoundaryValidator


class TestBoundaryValidationIntegration:
    """Integration tests for boundary validation system."""

    @pytest.fixture
    def sample_circuit_yaml(self):
        """Sample circuit YAML with out-of-bounds components."""
        return """
circuit "test_circuit":
  components:
    - reference: R1
      type: resistor
      value: 10k
      position: [50, 50]
    - reference: R2
      type: resistor
      value: 1k
      position: [350, 250]  # Out of bounds
    - reference: C1
      type: capacitor
      value: 100nF
      position: [5, 5]      # Outside usable area
    - reference: LED1
      type: led
      value: RED
      position: [100, 100]  # Valid position

  power_symbols:
    - reference: "#PWR001"
      type: VCC
      position: [75, 25]
    - reference: "#PWR002"
      type: GND
      position: [75, 175]

  connections:
    - from: R1.1
      to: R2.1
    - from: C1.1
      to: LED1.1
"""

    @pytest.fixture
    def valid_circuit_yaml(self):
        """Sample circuit YAML with all valid positions."""
        return """
circuit "valid_circuit":
  components:
    - reference: R1
      type: resistor
      value: 10k
      position: [50, 50]
    - reference: R2
      type: resistor
      value: 1k
      position: [150, 50]
    - reference: C1
      type: capacitor
      value: 100nF
      position: [100, 100]

  power_symbols:
    - reference: "#PWR001"
      type: VCC
      position: [75, 25]
    - reference: "#PWR002"
      type: GND
      position: [75, 175]
"""

    def test_parser_boundary_validation_integration(self, sample_circuit_yaml):
        """Test integration between circuit parser and boundary validation."""
        parser = TextToSchematicParser()
        circuit = parser.parse_yaml_circuit(sample_circuit_yaml)

        # Validate parsed circuit
        validator = BoundaryValidator()

        # Prepare components for validation
        components_for_validation = []
        for comp in circuit.components:
            components_for_validation.append(
                {
                    "reference": comp.reference,
                    "position": comp.position,
                    "component_type": comp.component_type,
                }
            )

        # Run validation
        validation_report = validator.validate_circuit_components(components_for_validation)

        # Check validation results
        assert validation_report.total_components == 4
        assert (
            validation_report.out_of_bounds_count == 2
        )  # R2 is out of bounds, C1 is outside usable area
        assert validation_report.has_errors() is True
        assert validation_report.has_warnings() is True  # C1 is outside usable area
        assert "R2" in validation_report.corrected_positions
        assert "C1" in validation_report.corrected_positions  # C1 now also gets corrected

        # Test auto-correction
        corrected_components, _ = validator.auto_correct_positions(components_for_validation)

        # Check that out-of-bounds component was corrected
        r2_component = next(comp for comp in corrected_components if comp["reference"] == "R2")
        assert r2_component["position"] != (350, 250)  # Position should be changed
        assert r2_component["position"][0] < 297.0  # Should be within A4 width
        assert r2_component["position"][1] < 210.0  # Should be within A4 height

    def test_valid_circuit_validation(self, valid_circuit_yaml):
        """Test validation of a circuit with all valid positions."""
        parser = TextToSchematicParser()
        circuit = parser.parse_yaml_circuit(valid_circuit_yaml)

        validator = BoundaryValidator()

        # Prepare components for validation
        components_for_validation = []
        for comp in circuit.components:
            components_for_validation.append(
                {
                    "reference": comp.reference,
                    "position": comp.position,
                    "component_type": comp.component_type,
                }
            )

        # Run validation
        validation_report = validator.validate_circuit_components(components_for_validation)

        # Check validation results
        assert validation_report.total_components == 3
        assert validation_report.out_of_bounds_count == 0
        assert validation_report.has_errors() is False
        assert validation_report.success is True
        assert len(validation_report.corrected_positions) == 0

    @pytest.mark.asyncio
    async def test_project_validation_workflow(self, tmp_path, sample_circuit_yaml):
        """Test complete project validation workflow."""
        # Create temporary project
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        project_file = project_dir / "test.kicad_pro"
        schematic_file = project_dir / "test.kicad_sch"

        # Create project file
        project_data = {
            "meta": {"filename": "test.kicad_pro", "version": 1},
            "sheets": [["test-sheet-id", ""]],
        }
        project_file.write_text(json.dumps(project_data))

        # Parse circuit and create schematic
        parser = TextToSchematicParser()
        circuit = parser.parse_yaml_circuit(sample_circuit_yaml)

        # Create schematic data with out-of-bounds components
        schematic_data = {"symbol": []}

        for comp in circuit.components:
            symbol_entry = {
                "lib_id": f"Device:{comp.component_type.upper()}",
                "at": [
                    comp.position[0] * 10,
                    comp.position[1] * 10,
                    0,
                ],  # Convert to internal units
                "property": [
                    {"name": "Reference", "value": comp.reference},
                    {"name": "Value", "value": comp.value},
                ],
            }
            schematic_data["symbol"].append(symbol_entry)

        schematic_file.write_text(json.dumps(schematic_data))

        # Run project validation
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.report_progress = AsyncMock()

        validation_result = await validate_project_boundaries(str(project_file), ctx)

        assert validation_result["success"] is False
        assert validation_result["total_components"] == 4
        assert validation_result["out_of_bounds_count"] == 2
        assert "R2" in validation_result["corrected_positions"]
        assert "C1" in validation_result["corrected_positions"]

        # Generate validation report
        report_result = await generate_validation_report(str(project_file), ctx=ctx)

        assert report_result["success"] is True
        assert os.path.exists(report_result["report_path"])

        # Check report contents
        with open(report_result["report_path"]) as f:
            report_data = json.load(f)

        assert report_data["summary"]["total_components"] == 4
        assert report_data["summary"]["out_of_bounds_count"] == 2
        assert report_data["summary"]["has_errors"] is True
        assert report_data["summary"]["has_warnings"] is True

        # Check issues
        issues = report_data["issues"]
        error_issues = [issue for issue in issues if issue["severity"] == "error"]
        warning_issues = [issue for issue in issues if issue["severity"] == "warning"]

        assert len(error_issues) == 1
        assert error_issues[0]["component_ref"] == "R2"
        assert len(warning_issues) == 1
        assert warning_issues[0]["component_ref"] == "C1"

    def test_boundary_validation_different_component_types(self):
        """Test boundary validation with different component types."""
        validator = BoundaryValidator()

        # Test different component types with various positions
        test_cases = [
            ("resistor", (50, 50), True),  # Valid position
            ("capacitor", (350, 250), False),  # Out of bounds
            ("ic", (20, 20), True),  # Valid but large component
            ("led", (10, 10), True),  # Too close to edge (outside usable area) - should be warning
            ("transistor", (200, 100), True),  # Valid position
            ("power", (280, 190), True),  # Valid position near edge
            ("connector", (300, 200), False),  # Out of bounds
        ]

        for component_type, position, should_be_valid in test_cases:
            issue = validator.validate_component_position(
                f"TEST_{component_type.upper()}", position[0], position[1], component_type
            )

            if should_be_valid:
                assert issue.severity.value in ["info", "warning"], (
                    f"Expected {component_type} at {position} to be valid or warning"
                )
            else:
                assert issue.severity.value == "error", (
                    f"Expected {component_type} at {position} to be error"
                )

    def test_validation_report_text_generation(self):
        """Test generation of human-readable validation reports."""
        validator = BoundaryValidator()

        # Create components with various issues
        components = [
            {"reference": "R1", "position": (50, 50), "component_type": "resistor"},  # Valid
            {
                "reference": "R2",
                "position": (350, 250),
                "component_type": "resistor",
            },  # Out of bounds
            {
                "reference": "C1",
                "position": (5, 5),
                "component_type": "capacitor",
            },  # Outside usable area
            {"reference": "LED1", "position": (100, 100), "component_type": "led"},  # Valid
            {"reference": "U1", "position": (400, 300), "component_type": "ic"},  # Out of bounds
        ]

        validation_report = validator.validate_circuit_components(components)
        report_text = validator.generate_validation_report_text(validation_report)

        # Check report structure
        assert "BOUNDARY VALIDATION REPORT" in report_text
        assert "Total Components: 5" in report_text
        assert "Out of Bounds: 3" in report_text
        assert "ERRORS:" in report_text
        assert "WARNINGS:" in report_text
        assert "INFO:" in report_text

        # Check specific components are mentioned
        assert "R2" in report_text
        assert "U1" in report_text
        assert "C1" in report_text

        # Check corrected positions are shown
        assert "CORRECTED POSITIONS:" in report_text
        assert len(validation_report.corrected_positions) == 3

    def test_validation_with_missing_positions(self):
        """Test validation handling of components with missing positions."""
        validator = BoundaryValidator()

        components = [
            {"reference": "R1", "position": (50, 50), "component_type": "resistor"},
            {"reference": "R2", "component_type": "resistor"},  # Missing position
            {"reference": "C1", "position": None, "component_type": "capacitor"},  # None position
        ]

        validation_report = validator.validate_circuit_components(components)

        assert validation_report.total_components == 3
        assert validation_report.validated_components == 1  # Only R1 has valid position
        assert validation_report.out_of_bounds_count == 0
        assert validation_report.success is True  # No out-of-bounds, just missing positions

        # Check issues
        assert (
            len([issue for issue in validation_report.issues if "no position" in issue.message])
            == 2
        )

    def test_wire_validation_integration(self):
        """Test wire connection validation integration."""
        validator = BoundaryValidator()

        # Test various wire connections
        test_cases = [
            # (start_x, start_y, end_x, end_y, expected_issue_count)
            (50, 50, 100, 100, 0),  # Valid wire
            (350, 250, 100, 100, 1),  # Invalid start
            (50, 50, 350, 250, 1),  # Invalid end
            (350, 250, 400, 300, 2),  # Both invalid
            (20, 20, 30, 30, 0),  # Valid within bounds
        ]

        for start_x, start_y, end_x, end_y, expected_issues in test_cases:
            issues = validator.validate_wire_connection(start_x, start_y, end_x, end_y)
            assert len(issues) == expected_issues, (
                f"Wire ({start_x},{start_y}) to ({end_x},{end_y}) expected {expected_issues} issues, got {len(issues)}"
            )

    def test_performance_with_large_circuit(self):
        """Test validation performance with large number of components."""
        validator = BoundaryValidator()

        # Create a large circuit with 100 components
        large_components = []
        for i in range(100):
            # Mix of valid and invalid positions
            if i % 10 == 0:  # Every 10th component is out of bounds
                x, y = 350 + i, 250 + i
            else:
                x, y = 50 + (i % 10) * 20, 50 + (i // 10) * 15

            large_components.append(
                {"reference": f"R{i + 1}", "position": (x, y), "component_type": "resistor"}
            )

        # Run validation
        validation_report = validator.validate_circuit_components(large_components)

        assert validation_report.total_components == 100
        assert validation_report.out_of_bounds_count == 10
        assert len(validation_report.corrected_positions) == 10
        assert validation_report.success is False

        # Check that all errors are captured
        error_count = len(
            [issue for issue in validation_report.issues if issue.severity.value == "error"]
        )
        assert error_count == 10


if __name__ == "__main__":
    pytest.main([__file__])

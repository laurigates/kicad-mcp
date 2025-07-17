"""
Visual validation tests for schematic generation.

These tests validate that generated schematics look correct and meet visual standards.
"""

import os
import tempfile

import pytest

from kicad_mcp.utils.boundary_validator import BoundaryValidator
from kicad_mcp.utils.component_layout import ComponentLayoutManager
from kicad_mcp.utils.coordinate_converter import CoordinateConverter
from kicad_mcp.utils.sexpr_generator import SExpressionGenerator


class TestVisualValidation:
    """Test visual aspects of schematic generation."""

    @pytest.fixture
    def coordinate_converter(self):
        """Provide coordinate converter instance."""
        return CoordinateConverter()

    @pytest.fixture
    def layout_manager(self):
        """Provide layout manager instance."""
        return ComponentLayoutManager()

    @pytest.fixture
    def boundary_validator(self):
        """Provide boundary validator instance."""
        return BoundaryValidator()

    @pytest.fixture
    def sexpr_generator(self):
        """Provide S-expression generator instance."""
        return SExpressionGenerator()

    def test_coordinate_system_validation(self, coordinate_converter):
        """Test coordinate validation within A4 bounds."""
        # Test valid coordinates within A4
        assert coordinate_converter.validate_layout_coordinates(50.0, 100.0)
        assert coordinate_converter.validate_layout_coordinates(297.0, 210.0)
        assert coordinate_converter.validate_layout_coordinates(0.0, 0.0)

        # Test invalid coordinates outside A4
        assert not coordinate_converter.validate_layout_coordinates(-10.0, 100.0)
        assert not coordinate_converter.validate_layout_coordinates(300.0, 100.0)
        assert not coordinate_converter.validate_layout_coordinates(100.0, 220.0)

        # Test usable area validation (with margins)
        assert coordinate_converter.validate_layout_usable_area(30.0, 30.0)
        assert coordinate_converter.validate_layout_usable_area(250.0, 150.0)

        # Test margin violations
        assert not coordinate_converter.validate_layout_usable_area(10.0, 30.0)  # Left margin
        assert not coordinate_converter.validate_layout_usable_area(290.0, 30.0)  # Right margin
        assert not coordinate_converter.validate_layout_usable_area(30.0, 10.0)  # Top margin
        assert not coordinate_converter.validate_layout_usable_area(30.0, 200.0)  # Bottom margin

    def test_component_layout_strategies(self, layout_manager):
        """Test different component layout strategies produce valid positions."""
        # Test components for layout
        test_components = [
            {"reference": "R1", "component_type": "resistor", "value": "10k"},
            {"reference": "R2", "component_type": "resistor", "value": "1k"},
            {"reference": "LED1", "component_type": "led", "value": "Red"},
            {"reference": "C1", "component_type": "capacitor", "value": "100nF"},
        ]

        # Clear any existing layout
        layout_manager.clear_layout()

        # Place all components
        positions = []
        for component in test_components:
            x, y = layout_manager.place_component(
                component["reference"], component["component_type"]
            )
            positions.append((x, y))

            # Verify position is within A4 bounds
            assert 0 <= x <= 297.0, f"X position {x} out of A4 bounds for {component['reference']}"
            assert 0 <= y <= 210.0, f"Y position {y} out of A4 bounds for {component['reference']}"

        # Verify no overlapping positions (within reasonable tolerance)
        min_distance = 10.0  # Minimum distance between components in mm
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i + 1 :], i + 1):
                distance = ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
                assert distance >= min_distance, (
                    f"Components too close: {test_components[i]['reference']} and {test_components[j]['reference']}"
                )

    def test_boundary_validation_visual_feedback(self, boundary_validator):
        """Test that boundary validation provides useful visual feedback."""
        # Test components with various position issues
        test_components = [
            {"reference": "R1", "position": (50.0, 100.0), "component_type": "resistor"},  # Valid
            {
                "reference": "R2",
                "position": (350.0, 100.0),
                "component_type": "resistor",
            },  # Out of bounds
            {
                "reference": "C1",
                "position": (10.0, 10.0),
                "component_type": "capacitor",
            },  # Margin violation
            {"reference": "LED1", "component_type": "led"},  # No position
        ]

        # Run validation
        validation_report = boundary_validator.validate_circuit_components(test_components)

        # Check that validation identifies issues correctly
        assert validation_report.total_components == 4
        assert validation_report.validated_components == 1  # Only R1 is fully valid
        assert validation_report.out_of_bounds_count == 2  # R2 and C1
        assert not validation_report.success

        # Check that auto-correction produces valid positions
        corrected_components, correction_report = boundary_validator.auto_correct_positions(
            test_components
        )

        # All corrected components should have valid positions
        for component in corrected_components:
            if "position" in component:
                x, y = component["position"]
                assert 20.0 <= x <= 277.0, f"Corrected X position {x} not in usable area"
                assert 20.0 <= y <= 190.0, f"Corrected Y position {y} not in usable area"

    def test_sexpr_visual_output_structure(self, sexpr_generator):
        """Test that generated S-expression has proper visual structure."""
        # Simple test circuit
        circuit_name = "Visual Test Circuit"
        components = [
            {
                "reference": "R1",
                "value": "10k",
                "position": (50.0, 50.0),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
            {
                "reference": "LED1",
                "value": "Red",
                "position": (100.0, 50.0),
                "symbol_library": "Device",
                "symbol_name": "LED",
            },
        ]
        power_symbols = [
            {"reference": "#PWR001", "power_type": "VCC", "position": (30.0, 30.0)},
            {"reference": "#PWR002", "power_type": "GND", "position": (30.0, 80.0)},
        ]
        connections = [
            {"start_component": "VCC", "start_pin": "1", "end_component": "R1", "end_pin": "1"},
            {"start_component": "R1", "start_pin": "2", "end_component": "LED1", "end_pin": "1"},
            {"start_component": "LED1", "start_pin": "2", "end_component": "GND", "end_pin": "1"},
        ]

        # Generate S-expression
        sexpr_content = sexpr_generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

        # Verify basic structure
        assert sexpr_content.startswith("(kicad_sch")
        assert sexpr_content.endswith(")")
        assert "A4" in sexpr_content  # Paper size
        assert circuit_name in sexpr_content
        assert "R1" in sexpr_content
        assert "LED1" in sexpr_content
        assert "VCC" in sexpr_content
        assert "GND" in sexpr_content

        # Check for lib_symbols section
        assert "(lib_symbols" in sexpr_content
        assert "Device:R" in sexpr_content
        assert "Device:LED" in sexpr_content
        assert "power:VCC" in sexpr_content
        assert "power:GND" in sexpr_content

        # Check for wire connections
        assert "(wire" in sexpr_content

        # Test that it can be written to a file without errors
        with tempfile.NamedTemporaryFile(mode="w", suffix=".kicad_sch", delete=False) as f:
            f.write(sexpr_content)
            temp_file = f.name

        try:
            # Verify file was created and has content
            assert os.path.exists(temp_file)
            assert os.path.getsize(temp_file) > 0

            # Read back and verify basic structure is preserved
            with open(temp_file) as f:
                file_content = f.read()
            assert file_content == sexpr_content

        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_visual_layout_consistency(self, layout_manager, boundary_validator):
        """Test that layout and validation produce consistent visual results."""
        # Large set of components to test layout distribution
        components = []
        for i in range(20):
            components.append(
                {
                    "reference": f"R{i + 1}",
                    "component_type": "resistor",
                    "value": f"{(i + 1) * 100}Ω",
                }
            )

        # Place components using layout manager
        layout_manager.clear_layout()
        placed_components = []
        for component in components:
            x, y = layout_manager.place_component(
                component["reference"], component["component_type"]
            )
            placed_component = component.copy()
            placed_component["position"] = (x, y)
            placed_components.append(placed_component)

        # Validate all placed components
        validation_report = boundary_validator.validate_circuit_components(placed_components)

        # All components should be valid (layout manager should place correctly)
        assert validation_report.success, "Layout manager should place all components within bounds"
        assert validation_report.out_of_bounds_count == 0
        assert validation_report.validated_components == len(components)

        # Check visual distribution - components shouldn't all be clustered in one area
        x_positions = [comp["position"][0] for comp in placed_components]
        y_positions = [comp["position"][1] for comp in placed_components]

        # Check spread across A4 page (should use reasonable portion of available space)
        x_range = max(x_positions) - min(x_positions)
        y_range = max(y_positions) - min(y_positions)

        # Expect at least 50mm spread in both directions for 20 components
        assert x_range >= 50.0, f"X spread too small: {x_range}mm"
        assert y_range >= 50.0, f"Y spread too small: {y_range}mm"

        # Components should be within usable area (with margins)
        for component in placed_components:
            x, y = component["position"]
            assert 20.0 <= x <= 277.0, f"Component {component['reference']} X outside usable area"
            assert 20.0 <= y <= 190.0, f"Component {component['reference']} Y outside usable area"

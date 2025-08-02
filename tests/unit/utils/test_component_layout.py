"""
Tests for ComponentLayoutManager functionality.
"""

from kicad_mcp.utils.component_layout import (
    ComponentBounds,
    ComponentLayoutManager,
    LayoutStrategy,
    SchematicBounds,
)


class TestSchematicBounds:
    """Test SchematicBounds class."""

    def test_default_bounds(self):
        """Test default A4 schematic bounds."""
        bounds = SchematicBounds()
        assert bounds.width == 297.0  # A4 width
        assert bounds.height == 210.0  # A4 height
        assert bounds.margin == 30.0

    def test_usable_area(self):
        """Test usable area calculations."""
        bounds = SchematicBounds()
        assert bounds.usable_width == 237.0  # 297 - 2*30
        assert bounds.usable_height == 150.0  # 210 - 2*30

    def test_boundary_coordinates(self):
        """Test boundary coordinate properties."""
        bounds = SchematicBounds()
        assert bounds.min_x == 30.0
        assert bounds.max_x == 267.0  # 297 - 30
        assert bounds.min_y == 30.0
        assert bounds.max_y == 180.0  # 210 - 30

    def test_enhanced_boundary_validation_issue3(self):
        """Test enhanced boundary validation addresses Issue #3.

        This test verifies that components are placed with conservative
        margins that provide better visibility in KiCad by using a 30mm
        margin instead of the previous 20mm margin.
        """
        bounds = SchematicBounds()
        manager = ComponentLayoutManager(bounds)

        # Test coordinates from Issue #3
        # Default component size is (10.0, 8.0) mm, so we need to account for half-size margins
        test_cases = [
            # Coordinates that were valid with 20mm margin but caused visibility issues
            {
                "pos": (127.0, 76.2),
                "expected": True,
                "description": "Previously valid, now with better margins",
            },
            {
                "pos": (203.2, 76.2),
                "expected": True,
                "description": "Previously valid, now with better margins",
            },
            # Coordinates that were invalid and should remain invalid
            {
                "pos": (355.6, 76.2),
                "expected": False,
                "description": "Outside bounds (x too large)",
            },
            # Edge cases with new 30mm margins (considering component half-sizes: 5.0 x 4.0)
            {
                "pos": (35.0, 34.0),
                "expected": True,
                "description": "Valid with component size at min boundary",
            },
            {
                "pos": (262.0, 176.0),
                "expected": True,
                "description": "Valid with component size at max boundary",
            },
            {
                "pos": (34.9, 76.2),
                "expected": False,
                "description": "Just outside min x (considering component width)",
            },
            {
                "pos": (127.0, 33.9),
                "expected": False,
                "description": "Just outside min y (considering component height)",
            },
            {
                "pos": (262.1, 76.2),
                "expected": False,
                "description": "Just outside max x (considering component width)",
            },
            {
                "pos": (127.0, 176.1),
                "expected": False,
                "description": "Just outside max y (considering component height)",
            },
        ]

        for case in test_cases:
            x, y = case["pos"]
            expected = case["expected"]
            description = case["description"]

            result = manager.validate_position(x, y)
            assert result == expected, f"Position ({x}, {y}) validation failed: {description}"


class TestComponentBounds:
    """Test ComponentBounds class."""

    def test_component_bounds_properties(self):
        """Test component bounds calculations."""
        comp = ComponentBounds("R1", 50.0, 50.0, 10.0, 5.0)

        assert comp.left == 45.0  # 50 - 10/2
        assert comp.right == 55.0  # 50 + 10/2
        assert comp.top == 47.5  # 50 - 5/2
        assert comp.bottom == 52.5  # 50 + 5/2

    def test_overlap_detection(self):
        """Test component overlap detection."""
        comp1 = ComponentBounds("R1", 50.0, 50.0, 10.0, 5.0)
        comp2 = ComponentBounds("R2", 55.0, 50.0, 10.0, 5.0)  # Overlapping
        comp3 = ComponentBounds("R3", 70.0, 50.0, 10.0, 5.0)  # Not overlapping

        assert comp1.overlaps_with(comp2)
        assert not comp1.overlaps_with(comp3)


class TestComponentLayoutManager:
    """Test ComponentLayoutManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.layout_manager = ComponentLayoutManager()

    def test_initialization(self):
        """Test layout manager initialization."""
        assert self.layout_manager.bounds.width == 297.0
        assert self.layout_manager.grid_spacing == 1.0
        assert len(self.layout_manager.placed_components) == 0

    def test_position_validation(self):
        """Test position validation."""
        # Valid positions
        assert self.layout_manager.validate_position(100, 100, "resistor")
        assert self.layout_manager.validate_position(50, 50, "resistor")

        # Invalid positions (outside bounds)
        assert not self.layout_manager.validate_position(10, 10, "resistor")  # Too close to edge
        assert not self.layout_manager.validate_position(400, 400, "resistor")  # Outside bounds
        assert not self.layout_manager.validate_position(
            290, 100, "resistor"
        )  # Too close to right edge

    def test_grid_snapping(self):
        """Test grid snapping functionality."""
        # Test various coordinates
        x, y = self.layout_manager.snap_to_grid(51.2, 49.8)
        assert x == 51.0  # 51.2 rounds to 51*1.0 = 51.0
        assert y == 50.0  # 49.8 rounds to 50*1.0 = 50.0

        x, y = self.layout_manager.snap_to_grid(25.0, 25.0)
        assert x == 25.0  # Already on grid point
        assert y == 25.0

    def test_component_placement(self):
        """Test component placement."""
        # Place a component at valid position
        x, y = self.layout_manager.place_component("R1", "resistor", 50, 50)

        assert x == 50.0  # Snapped to grid
        assert y == 50.0
        assert len(self.layout_manager.placed_components) == 1

        # Place another component at invalid position (should auto-correct)
        x, y = self.layout_manager.place_component("R2", "resistor", 400, 400)

        # Should be placed at valid position
        assert self.layout_manager.validate_position(x, y, "resistor")
        assert len(self.layout_manager.placed_components) == 2

    def test_collision_avoidance(self):
        """Test collision avoidance."""
        # Place first component
        x1, y1 = self.layout_manager.place_component("R1", "resistor", 50, 50)

        # Try to place second component at same location
        x2, y2 = self.layout_manager.place_component("R2", "resistor", 50, 50)

        # Should be placed at different location
        assert (x2, y2) != (x1, y1)
        assert len(self.layout_manager.placed_components) == 2

    def test_auto_layout_grid(self):
        """Test grid auto-layout."""
        components = [
            {"reference": "R1", "component_type": "resistor"},
            {"reference": "R2", "component_type": "resistor"},
            {"reference": "R3", "component_type": "resistor"},
            {"reference": "R4", "component_type": "resistor"},
        ]

        laid_out = self.layout_manager.auto_layout_components(components, LayoutStrategy.GRID)

        assert len(laid_out) == 4
        for comp in laid_out:
            assert "position" in comp
            assert len(comp["position"]) == 2
            # All positions should be valid
            assert self.layout_manager.validate_position(
                comp["position"][0], comp["position"][1], comp.get("component_type", "default")
            )

    def test_auto_layout_row(self):
        """Test row auto-layout."""
        components = [
            {"reference": "R1", "component_type": "resistor"},
            {"reference": "R2", "component_type": "resistor"},
            {"reference": "R3", "component_type": "resistor"},
        ]

        laid_out = self.layout_manager.auto_layout_components(components, LayoutStrategy.ROW)

        assert len(laid_out) == 3
        # All components should have same Y coordinate (in a row)
        y_coords = [comp["position"][1] for comp in laid_out]
        assert len(set(y_coords)) == 1  # All Y coordinates are the same

    def test_auto_layout_column(self):
        """Test column auto-layout."""
        components = [
            {"reference": "R1", "component_type": "resistor"},
            {"reference": "R2", "component_type": "resistor"},
            {"reference": "R3", "component_type": "resistor"},
        ]

        laid_out = self.layout_manager.auto_layout_components(components, LayoutStrategy.COLUMN)

        assert len(laid_out) == 3
        # All components should have same X coordinate (in a column)
        x_coords = [comp["position"][0] for comp in laid_out]
        assert len(set(x_coords)) == 1  # All X coordinates are the same

    def test_layout_statistics(self):
        """Test layout statistics."""
        # Initially empty
        stats = self.layout_manager.get_layout_statistics()
        assert stats["total_components"] == 0
        assert stats["area_utilization"] == 0.0
        assert stats["bounds_violations"] == 0

        # Place some components
        self.layout_manager.place_component("R1", "resistor", 50, 50)
        self.layout_manager.place_component("R2", "resistor", 100, 100)

        stats = self.layout_manager.get_layout_statistics()
        assert stats["total_components"] == 2
        assert stats["area_utilization"] > 0
        assert stats["bounds_violations"] == 0

    def test_clear_layout(self):
        """Test layout clearing."""
        # Place some components
        self.layout_manager.place_component("R1", "resistor", 50, 50)
        self.layout_manager.place_component("R2", "resistor", 100, 100)

        assert len(self.layout_manager.placed_components) == 2

        # Clear layout
        self.layout_manager.clear_layout()

        assert len(self.layout_manager.placed_components) == 0

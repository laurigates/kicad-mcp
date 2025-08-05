"""
Tests for WireRouter functionality.
"""

from kicad_mcp.utils.component_layout import SchematicBounds
from kicad_mcp.utils.pin_mapper import ComponentPin, PinDirection, PinInfo, PinType
from kicad_mcp.utils.wire_router import (
    RouteStrategy,
    RoutingObstacle,
    WireRoute,
    WireRouter,
    WireSegment,
    WireSegmentType,
)


class TestWireSegment:
    """Test WireSegment class."""

    def test_segment_creation(self):
        """Test wire segment creation."""
        segment = WireSegment(
            start=(10.0, 20.0), end=(30.0, 20.0), segment_type=WireSegmentType.HORIZONTAL
        )

        assert segment.start == (10.0, 20.0)
        assert segment.end == (30.0, 20.0)
        assert segment.segment_type == WireSegmentType.HORIZONTAL
        assert segment.width == 0.15  # Default width

    def test_segment_length_calculation(self):
        """Test segment length calculation."""
        # Horizontal segment
        h_segment = WireSegment(
            start=(0.0, 0.0), end=(10.0, 0.0), segment_type=WireSegmentType.HORIZONTAL
        )
        assert abs(h_segment.length - 10.0) < 0.01

        # Vertical segment
        v_segment = WireSegment(
            start=(0.0, 0.0), end=(0.0, 5.0), segment_type=WireSegmentType.VERTICAL
        )
        assert abs(v_segment.length - 5.0) < 0.01

        # Diagonal segment
        d_segment = WireSegment(
            start=(0.0, 0.0), end=(3.0, 4.0), segment_type=WireSegmentType.HORIZONTAL
        )
        assert abs(d_segment.length - 5.0) < 0.01  # 3-4-5 triangle

    def test_segment_midpoint_calculation(self):
        """Test segment midpoint calculation."""
        segment = WireSegment(
            start=(10.0, 20.0), end=(30.0, 40.0), segment_type=WireSegmentType.HORIZONTAL
        )

        midpoint = segment.midpoint
        assert midpoint == (20.0, 30.0)


class TestWireRoute:
    """Test WireRoute class."""

    def test_route_creation(self):
        """Test wire route creation."""
        pin1 = self._create_test_pin("R1", (10.0, 10.0))
        pin2 = self._create_test_pin("R2", (20.0, 10.0))

        segments = [WireSegment((10.0, 10.0), (20.0, 10.0), WireSegmentType.HORIZONTAL)]

        route = WireRoute(
            net_name="NET1", segments=segments, connected_pins=[pin1, pin2], priority=2
        )

        assert route.net_name == "NET1"
        assert len(route.segments) == 1
        assert len(route.connected_pins) == 2
        assert route.priority == 2

    def test_route_total_length(self):
        """Test route total length calculation."""
        segments = [
            WireSegment((0.0, 0.0), (10.0, 0.0), WireSegmentType.HORIZONTAL),
            WireSegment((10.0, 0.0), (10.0, 5.0), WireSegmentType.VERTICAL),
        ]

        route = WireRoute(net_name="NET1", segments=segments, connected_pins=[], priority=1)

        expected_length = 10.0 + 5.0  # 15.0 total
        assert abs(route.total_length - expected_length) < 0.01

    def test_route_endpoints(self):
        """Test route start and end point properties."""
        segments = [
            WireSegment((5.0, 10.0), (15.0, 10.0), WireSegmentType.HORIZONTAL),
            WireSegment((15.0, 10.0), (15.0, 20.0), WireSegmentType.VERTICAL),
        ]

        route = WireRoute(net_name="NET1", segments=segments, connected_pins=[], priority=1)

        assert route.start_point == (5.0, 10.0)
        assert route.end_point == (15.0, 20.0)

    def _create_test_pin(self, component_ref: str, position: tuple[float, float]) -> ComponentPin:
        """Create a test pin for testing."""
        pin_info = PinInfo(
            number="1",
            name="test",
            direction=PinDirection.PASSIVE,
            pin_type=PinType.ELECTRICAL,
            position=(0.0, 0.0),
        )

        return ComponentPin(
            component_ref=component_ref, pin_info=pin_info, component_position=position
        )


class TestRoutingObstacle:
    """Test RoutingObstacle class."""

    def test_obstacle_creation(self):
        """Test obstacle creation."""
        obstacle = RoutingObstacle(
            bounds=(10.0, 10.0, 20.0, 20.0), obstacle_type="component", reference="R1"
        )

        assert obstacle.bounds == (10.0, 10.0, 20.0, 20.0)
        assert obstacle.obstacle_type == "component"
        assert obstacle.reference == "R1"

    def test_obstacle_intersection_detection(self):
        """Test obstacle intersection with wire segments."""
        obstacle = RoutingObstacle(
            bounds=(10.0, 10.0, 20.0, 20.0), obstacle_type="component", reference="R1"
        )

        # Segment that intersects obstacle
        intersecting_segment = WireSegment(
            start=(5.0, 15.0), end=(25.0, 15.0), segment_type=WireSegmentType.HORIZONTAL
        )
        assert obstacle.intersects_segment(intersecting_segment)

        # Segment that doesn't intersect obstacle
        non_intersecting_segment = WireSegment(
            start=(5.0, 5.0), end=(25.0, 5.0), segment_type=WireSegmentType.HORIZONTAL
        )
        assert not obstacle.intersects_segment(non_intersecting_segment)


class TestWireRouter:
    """Test WireRouter class."""

    def test_router_initialization(self):
        """Test wire router initialization."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        assert router.bounds == bounds
        assert len(router.obstacles) == 0
        assert len(router.routes) == 0
        assert router.grid_spacing == 2.54
        assert router.min_wire_spacing == 2.54

    def test_obstacle_management(self):
        """Test adding and clearing obstacles."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        obstacle = RoutingObstacle(
            bounds=(10.0, 10.0, 20.0, 20.0), obstacle_type="component", reference="R1"
        )

        router.add_obstacle(obstacle)
        assert len(router.obstacles) == 1
        assert router.obstacles[0] == obstacle

        router.clear_obstacles()
        assert len(router.obstacles) == 0

    def test_route_management(self):
        """Test route management."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        pin1 = self._create_test_pin("R1", (10.0, 10.0))
        pin2 = self._create_test_pin("R2", (20.0, 10.0))

        route = router.route_connection(pin1, pin2, "NET1")

        assert len(router.routes) == 1
        assert route.net_name == "NET1"
        assert len(route.connected_pins) == 2

        router.clear_routes()
        assert len(router.routes) == 0

    def test_manhattan_routing_horizontal(self):
        """Test Manhattan routing for horizontal connections."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        pin1 = self._create_test_pin("R1", (10.0, 10.0))
        pin2 = self._create_test_pin("R2", (20.0, 10.0))

        route = router.route_connection(pin1, pin2, "NET1", RouteStrategy.MANHATTAN)

        # Should create a single horizontal segment
        assert len(route.segments) == 1
        assert route.segments[0].segment_type == WireSegmentType.HORIZONTAL
        assert route.segments[0].start == pin1.connection_point
        assert route.segments[0].end == pin2.connection_point

    def test_manhattan_routing_vertical(self):
        """Test Manhattan routing for vertical connections."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        pin1 = self._create_test_pin("R1", (10.0, 10.0))
        pin2 = self._create_test_pin("R2", (10.0, 20.0))

        route = router.route_connection(pin1, pin2, "NET1", RouteStrategy.MANHATTAN)

        # Should create a single vertical segment
        assert len(route.segments) == 1
        assert route.segments[0].segment_type == WireSegmentType.VERTICAL
        assert route.segments[0].start == pin1.connection_point
        assert route.segments[0].end == pin2.connection_point

    def test_manhattan_routing_l_shaped(self):
        """Test Manhattan routing for L-shaped connections."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        pin1 = self._create_test_pin("R1", (10.0, 10.0))
        pin2 = self._create_test_pin("R2", (20.0, 15.0))

        route = router.route_connection(pin1, pin2, "NET1", RouteStrategy.MANHATTAN)

        # Should create horizontal then vertical segments
        assert len(route.segments) == 2
        assert route.segments[0].segment_type == WireSegmentType.HORIZONTAL
        assert route.segments[1].segment_type == WireSegmentType.VERTICAL

        # Check segment connections
        assert route.segments[0].start == pin1.connection_point
        assert route.segments[0].end == route.segments[1].start
        assert route.segments[1].end == pin2.connection_point

    def test_direct_routing(self):
        """Test direct routing strategy."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        pin1 = self._create_test_pin("R1", (10.0, 10.0))
        pin2 = self._create_test_pin("R2", (20.0, 15.0))

        route = router.route_connection(pin1, pin2, "NET1", RouteStrategy.DIRECT)

        # Should create a single direct segment
        assert len(route.segments) == 1
        assert route.segments[0].start == pin1.connection_point
        assert route.segments[0].end == pin2.connection_point

    def test_multi_point_net_routing(self):
        """Test multi-point net routing (star topology)."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        pins = [
            self._create_test_pin("VCC", (10.0, 10.0)),  # Hub
            self._create_test_pin("R1", (20.0, 10.0)),
            self._create_test_pin("R2", (30.0, 15.0)),
            self._create_test_pin("R3", (15.0, 20.0)),
        ]

        routes = router.route_multi_point_net(pins, "VCC_NET", RouteStrategy.MANHATTAN)

        # Should create 3 routes (hub to each other pin)
        assert len(routes) == 3
        assert all(route.net_name == "VCC_NET" for route in routes)

        # All routes should connect to the hub pin
        for route in routes:
            assert pins[0] in route.connected_pins

    def test_grid_snapping(self):
        """Test grid snapping functionality."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        # Test snapping to 2.54mm grid
        point = (10.3, 15.7)
        snapped = router.snap_to_grid(point)

        expected = (10.16, 15.24)  # Nearest 2.54mm grid points
        assert abs(snapped[0] - expected[0]) < 0.01
        assert abs(snapped[1] - expected[1]) < 0.01

    def test_routing_statistics(self):
        """Test routing statistics generation."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        # Empty router statistics
        stats = router.get_routing_statistics()
        assert stats["total_routes"] == 0
        assert stats["total_length"] == 0.0
        assert stats["average_length"] == 0.0

        # Add some routes
        pin1 = self._create_test_pin("R1", (0.0, 0.0))
        pin2 = self._create_test_pin("R2", (10.0, 0.0))
        pin3 = self._create_test_pin("R3", (0.0, 10.0))

        router.route_connection(pin1, pin2, "NET1", priority=1)
        router.route_connection(pin1, pin3, "NET2", priority=2)

        stats = router.get_routing_statistics()
        assert stats["total_routes"] == 2
        assert stats["total_length"] > 0
        assert stats["average_length"] > 0
        assert stats["routes_by_priority"] == {1: 1, 2: 1}

    def test_segment_merging_optimization(self):
        """Test segment merging during optimization."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        # Create segments that can be merged (collinear horizontal segments)
        segments = [
            WireSegment((0.0, 10.0), (10.0, 10.0), WireSegmentType.HORIZONTAL),
            WireSegment((10.0, 10.0), (20.0, 10.0), WireSegmentType.HORIZONTAL),
        ]

        optimized = router._optimize_route_segments(segments)

        # Should merge into single segment
        assert len(optimized) == 1
        assert optimized[0].start == (0.0, 10.0)
        assert optimized[0].end == (20.0, 10.0)
        assert optimized[0].segment_type == WireSegmentType.HORIZONTAL

    def test_segment_merging_different_types(self):
        """Test that segments of different types don't merge."""
        bounds = SchematicBounds()
        router = WireRouter(bounds)

        # Create segments that cannot be merged (different types)
        segments = [
            WireSegment((0.0, 10.0), (10.0, 10.0), WireSegmentType.HORIZONTAL),
            WireSegment((10.0, 10.0), (10.0, 20.0), WireSegmentType.VERTICAL),
        ]

        optimized = router._optimize_route_segments(segments)

        # Should not merge - different segment types
        assert len(optimized) == 2
        assert optimized[0].segment_type == WireSegmentType.HORIZONTAL
        assert optimized[1].segment_type == WireSegmentType.VERTICAL

    def _create_test_pin(self, component_ref: str, position: tuple[float, float]) -> ComponentPin:
        """Create a test pin for testing."""
        pin_info = PinInfo(
            number="1",
            name="test",
            direction=PinDirection.PASSIVE,
            pin_type=PinType.ELECTRICAL,
            position=(0.0, 0.0),
        )

        return ComponentPin(
            component_ref=component_ref, pin_info=pin_info, component_position=position
        )

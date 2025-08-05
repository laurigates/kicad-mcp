"""
Intelligent wire routing algorithms for KiCad schematic generation.

This module provides algorithms for routing wires between component pins,
including Manhattan routing, obstacle avoidance, and path optimization.
Designed to generate clean, readable schematic layouts.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from kicad_mcp.utils.component_layout import SchematicBounds
from kicad_mcp.utils.pin_mapper import ComponentPin


class RouteStrategy(Enum):
    """Wire routing strategies."""

    MANHATTAN = "manhattan"  # Right-angle connections only
    DIRECT = "direct"  # Straight lines when possible
    OPTIMIZED = "optimized"  # Smart combination of strategies


class WireSegmentType(Enum):
    """Types of wire segments."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    JUNCTION = "junction"  # Connection point for multiple wires


@dataclass
class WireSegment:
    """A single wire segment in a route."""

    start: tuple[float, float]
    end: tuple[float, float]
    segment_type: WireSegmentType
    width: float = 0.15  # Default wire width in mm

    @property
    def length(self) -> float:
        """Calculate segment length."""
        return math.sqrt((self.end[0] - self.start[0]) ** 2 + (self.end[1] - self.start[1]) ** 2)

    @property
    def midpoint(self) -> tuple[float, float]:
        """Calculate segment midpoint."""
        return ((self.start[0] + self.end[0]) / 2, (self.start[1] + self.end[1]) / 2)


@dataclass
class WireRoute:
    """A complete wire route between pins."""

    net_name: str
    segments: list[WireSegment]
    connected_pins: list[ComponentPin]
    priority: int = 1  # Higher numbers get priority in routing

    @property
    def total_length(self) -> float:
        """Calculate total route length."""
        return sum(segment.length for segment in self.segments)

    @property
    def start_point(self) -> tuple[float, float]:
        """Get route start point."""
        return self.segments[0].start if self.segments else (0, 0)

    @property
    def end_point(self) -> tuple[float, float]:
        """Get route end point."""
        return self.segments[-1].end if self.segments else (0, 0)


@dataclass
class RoutingObstacle:
    """An obstacle that wires must route around."""

    bounds: tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    obstacle_type: str
    reference: str  # Component reference or identifier

    def intersects_segment(self, segment: WireSegment) -> bool:
        """Check if this obstacle intersects with a wire segment."""
        min_x, min_y, max_x, max_y = self.bounds

        # Simple bounding box intersection check
        seg_min_x = min(segment.start[0], segment.end[0])
        seg_max_x = max(segment.start[0], segment.end[0])
        seg_min_y = min(segment.start[1], segment.end[1])
        seg_max_y = max(segment.start[1], segment.end[1])

        return not (
            seg_max_x < min_x or seg_min_x > max_x or seg_max_y < min_y or seg_min_y > max_y
        )


class WireRouter:
    """
    Intelligent wire routing engine for KiCad schematics.

    Features:
    - Manhattan routing with right-angle connections
    - Obstacle avoidance for clean layouts
    - Multi-point net routing (power, ground buses)
    - Path length optimization
    - Wire priority handling
    """

    def __init__(self, bounds: SchematicBounds):
        """Initialize the wire router."""
        self.bounds = bounds
        self.obstacles: list[RoutingObstacle] = []
        self.routes: list[WireRoute] = []
        self.grid_spacing = 2.54  # Standard KiCad grid spacing in mm
        self.min_wire_spacing = 2.54  # Minimum spacing between parallel wires

    def add_obstacle(self, obstacle: RoutingObstacle) -> None:
        """Add a routing obstacle (typically a component)."""
        self.obstacles.append(obstacle)

    def clear_obstacles(self) -> None:
        """Clear all routing obstacles."""
        self.obstacles.clear()

    def clear_routes(self) -> None:
        """Clear all existing routes."""
        self.routes.clear()

    def route_connection(
        self,
        pin1: ComponentPin,
        pin2: ComponentPin,
        net_name: str,
        strategy: RouteStrategy = RouteStrategy.MANHATTAN,
        priority: int = 1,
    ) -> WireRoute:
        """
        Route a connection between two pins.

        Args:
            pin1: Source pin
            pin2: Destination pin
            net_name: Name of the electrical net
            strategy: Routing strategy to use
            priority: Route priority (higher = more important)

        Returns:
            WireRoute object containing the routing segments
        """
        start_point = pin1.connection_point
        end_point = pin2.connection_point

        if strategy == RouteStrategy.MANHATTAN:
            segments = self._route_manhattan(start_point, end_point)
        elif strategy == RouteStrategy.DIRECT:
            segments = self._route_direct(start_point, end_point)
        else:  # OPTIMIZED
            segments = self._route_optimized(start_point, end_point)

        route = WireRoute(
            net_name=net_name, segments=segments, connected_pins=[pin1, pin2], priority=priority
        )

        self.routes.append(route)
        return route

    def route_multi_point_net(
        self,
        pins: list[ComponentPin],
        net_name: str,
        strategy: RouteStrategy = RouteStrategy.MANHATTAN,
        priority: int = 1,
    ) -> list[WireRoute]:
        """
        Route a multi-point net (e.g., power or ground connections).

        Uses minimum spanning tree approach to minimize total wire length
        while ensuring all pins are connected.

        Args:
            pins: List of pins to connect
            net_name: Name of the electrical net
            strategy: Routing strategy
            priority: Route priority

        Returns:
            List of WireRoute objects forming the complete net
        """
        if len(pins) < 2:
            return []

        routes = []

        # Simple star topology for power/ground nets
        # Connect all pins to the first pin (typically power source)
        hub_pin = pins[0]

        for i in range(1, len(pins)):
            route = self.route_connection(hub_pin, pins[i], net_name, strategy, priority)
            routes.append(route)

        return routes

    def _route_manhattan(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> list[WireSegment]:
        """Route using Manhattan (right-angle) routing."""
        start_x, start_y = start
        end_x, end_y = end

        # Simple L-shaped routing
        # Go horizontal first, then vertical
        segments = []

        if abs(end_x - start_x) > 0.1:  # Horizontal segment needed
            mid_point = (end_x, start_y)
            segments.append(
                WireSegment(start=start, end=mid_point, segment_type=WireSegmentType.HORIZONTAL)
            )

            if abs(end_y - start_y) > 0.1:  # Vertical segment needed
                segments.append(
                    WireSegment(start=mid_point, end=end, segment_type=WireSegmentType.VERTICAL)
                )

        elif abs(end_y - start_y) > 0.1:  # Only vertical segment needed
            segments.append(
                WireSegment(start=start, end=end, segment_type=WireSegmentType.VERTICAL)
            )

        return segments

    def _route_direct(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> list[WireSegment]:
        """Route using direct line routing."""
        return [
            WireSegment(
                start=start,
                end=end,
                segment_type=WireSegmentType.HORIZONTAL,  # Classification for direct routes
            )
        ]

    def _route_optimized(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> list[WireSegment]:
        """Route using optimized strategy with obstacle avoidance."""
        # For now, use Manhattan routing as base
        # Future enhancement: add A* pathfinding with obstacle avoidance
        segments = self._route_manhattan(start, end)

        # Check for obstacles and reroute if necessary
        for obstacle in self.obstacles:
            segments = self._avoid_obstacle(segments, obstacle)

        return segments

    def _avoid_obstacle(
        self, segments: list[WireSegment], obstacle: RoutingObstacle
    ) -> list[WireSegment]:
        """Modify route segments to avoid an obstacle."""
        # Simple obstacle avoidance: if any segment intersects,
        # try to route around the obstacle
        modified_segments = []

        for segment in segments:
            if obstacle.intersects_segment(segment):
                # Route around obstacle by adding detour
                detour_segments = self._create_detour(segment, obstacle)
                modified_segments.extend(detour_segments)
            else:
                modified_segments.append(segment)

        return modified_segments

    def _create_detour(self, segment: WireSegment, obstacle: RoutingObstacle) -> list[WireSegment]:
        """Create a detour around an obstacle."""
        min_x, min_y, max_x, max_y = obstacle.bounds
        start_x, start_y = segment.start
        end_x, end_y = segment.end

        # Simple detour: go around the obstacle
        # Choose the shorter path (above/below or left/right)
        detour_segments = []

        if segment.segment_type == WireSegmentType.HORIZONTAL:
            # Route above or below the obstacle
            clearance = 2.54  # 2.54mm clearance
            # Route above or below obstacle
            detour_y = min_y - clearance if start_y < min_y else max_y + clearance

            detour_segments = [
                WireSegment((start_x, start_y), (start_x, detour_y), WireSegmentType.VERTICAL),
                WireSegment((start_x, detour_y), (end_x, detour_y), WireSegmentType.HORIZONTAL),
                WireSegment((end_x, detour_y), (end_x, end_y), WireSegmentType.VERTICAL),
            ]

        else:  # VERTICAL
            # Route left or right of obstacle
            clearance = 2.54
            # Route left or right of obstacle
            detour_x = min_x - clearance if start_x < min_x else max_x + clearance

            detour_segments = [
                WireSegment((start_x, start_y), (detour_x, start_y), WireSegmentType.HORIZONTAL),
                WireSegment((detour_x, start_y), (detour_x, end_y), WireSegmentType.VERTICAL),
                WireSegment((detour_x, end_y), (end_x, end_y), WireSegmentType.HORIZONTAL),
            ]

        return detour_segments

    def snap_to_grid(self, point: tuple[float, float]) -> tuple[float, float]:
        """Snap a point to the routing grid."""
        x, y = point
        grid = self.grid_spacing
        return (round(x / grid) * grid, round(y / grid) * grid)

    def optimize_routes(self) -> None:
        """Optimize all routes for better layout and shorter paths."""
        # Sort routes by priority (higher priority routes get better paths)
        self.routes.sort(key=lambda route: route.priority, reverse=True)

        # Apply optimizations
        for route in self.routes:
            route.segments = self._optimize_route_segments(route.segments)

    def _optimize_route_segments(self, segments: list[WireSegment]) -> list[WireSegment]:
        """Optimize individual route segments."""
        if len(segments) <= 1:
            return segments

        optimized = []
        i = 0

        while i < len(segments):
            current = segments[i]

            # Try to merge with next segment if they're collinear
            if i + 1 < len(segments):
                next_segment = segments[i + 1]
                merged = self._try_merge_segments(current, next_segment)
                if merged:
                    optimized.append(merged)
                    i += 2  # Skip next segment since we merged
                    continue

            optimized.append(current)
            i += 1

        return optimized

    def _try_merge_segments(self, seg1: WireSegment, seg2: WireSegment) -> WireSegment | None:
        """Try to merge two segments if they're collinear."""
        # Check if segments are connected and collinear
        if seg1.end != seg2.start:
            return None

        # Check if both segments are horizontal or both vertical
        if seg1.segment_type != seg2.segment_type:
            return None

        # Check collinearity
        if seg1.segment_type == WireSegmentType.HORIZONTAL:
            if abs(seg1.start[1] - seg2.end[1]) < 0.1:  # Same Y coordinate
                return WireSegment(
                    start=seg1.start, end=seg2.end, segment_type=WireSegmentType.HORIZONTAL
                )
        elif (
            seg1.segment_type == WireSegmentType.VERTICAL and abs(seg1.start[0] - seg2.end[0]) < 0.1
        ):  # Same X coordinate
            return WireSegment(
                start=seg1.start, end=seg2.end, segment_type=WireSegmentType.VERTICAL
            )

        return None

    def get_routing_statistics(self) -> dict[str, Any]:
        """Get statistics about the current routing solution."""
        if not self.routes:
            return {"total_routes": 0, "total_length": 0.0, "average_length": 0.0}

        total_length = sum(route.total_length for route in self.routes)
        return {
            "total_routes": len(self.routes),
            "total_length": total_length,
            "average_length": total_length / len(self.routes),
            "total_segments": sum(len(route.segments) for route in self.routes),
            "routes_by_priority": self._get_priority_distribution(),
        }

    def _get_priority_distribution(self) -> dict[int, int]:
        """Get distribution of routes by priority level."""
        distribution = {}
        for route in self.routes:
            distribution[route.priority] = distribution.get(route.priority, 0) + 1
        return distribution

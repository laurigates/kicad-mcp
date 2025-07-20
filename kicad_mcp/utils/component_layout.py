"""Component layout manager for KiCad schematics.

This module provides functionalities for intelligent positioning,
boundary validation, and automatic layout capabilities for components
within KiCad schematics. It integrates with configuration settings
from `kicad_mcp.config` and utilizes standard Python libraries for
mathematical operations and data structuring.

Features:
- Intelligent positioning
- Boundary validation
- Automatic layout generation
- Collision detection
- Support for various layout strategies (Grid, Row, Column, Circular, Hierarchical)
- Statistical analysis of component layouts

Dependencies:
    - dataclasses
    - enum
    - math
    - kicad_mcp.config (for CIRCUIT_DEFAULTS)
"""

from dataclasses import dataclass
from enum import Enum
import math

from kicad_mcp.config import CIRCUIT_DEFAULTS


class LayoutStrategy(Enum):
    """Layout strategies for automatic component placement.

    Attributes:
        GRID: Places components in a grid pattern.
        ROW: Places components in a single horizontal row.
        COLUMN: Places components in a single vertical column.
        CIRCULAR: Arranges components in a circular formation.
        HIERARCHICAL: Organizes components based on their type in a hierarchical
            structure.
    """
    # ...

    GRID = "grid"
    ROW = "row"
    COLUMN = "column"
    CIRCULAR = "circular"
    HIERARCHICAL = "hierarchical"


@dataclass
class ComponentBounds:
    """Represents the bounding box and position of a component.

    This dataclass stores geometric information about a component,
    including its reference designator, central coordinates (x, y),
    and dimensions (width, height), enabling calculations for
    layout and collision detection.

    Attributes:
        reference: The reference designator of the component (e.g., 'R1', 'C10').
        x: The central X-coordinate of the component in millimeters.
        y: The central Y-coordinate of the component in millimeters.
        width: The width of the component bounding box in millimeters.
        height: The height of the component bounding box in millimeters.
    """

    reference: str
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        """Calculates the left edge coordinate of the component bounding box."""
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        """Calculates the right edge coordinate of the component bounding box."""
        return self.x + self.width / 2

    @property
    def top(self) -> float:
        """Calculates the top edge coordinate of the component bounding box."""
        return self.y - self.height / 2

    @property
    def bottom(self) -> float:
        """Calculates the bottom edge coordinate of the component bounding box."""
        return self.y + self.height / 2

    def overlaps_with(self, other: "ComponentBounds") -> bool:
        """Checks if this component's bounding box overlaps with another's.

        Args:
            other:
                The other component bounding box to check against.

        Returns:
            True if the bounding boxes overlap, False otherwise.

        Examples:
            >>> b1 = ComponentBounds("R1", 10, 10, 5, 5)
            >>> b2 = ComponentBounds("C1", 12, 12, 5, 5)
            >>> b1.overlaps_with(b2)
            True
            >>> b3 = ComponentBounds("D1", 20, 20, 5, 5)
            >>> b1.overlaps_with(b3)
            False
        """
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bottom < other.top
            or self.top > other.bottom
        )


@dataclass
class SchematicBounds:
    """Represents the boundaries of a KiCad schematic sheet.

    This dataclass defines the dimensions and margins of the schematic sheet,
    providing properties to easily calculate usable areas and coordinate limits.
    It defaults to A4 dimensions with a standard margin.

    Attributes:
        width: The total width of the schematic sheet in millimeters
            (default: 297.0 for A4).
        height: The total height of the schematic sheet in millimeters
            (default: 210.0 for A4).
        margin: The margin from the edges of the sheet in millimeters
            (default: 20.0).
    """

    width: float = 297.0  # A4 width in mm
    height: float = 210.0  # A4 height in mm
    margin: float = 20.0  # Margin from edges in mm

    @property
    def usable_width(self) -> float:
        """Calculates the usable width of the schematic area, considering margins."""
        return self.width - 2 * self.margin

    @property
    def usable_height(self) -> float:
        """Calculates the usable height of the schematic area, considering margins."""
        return self.height - 2 * self.margin

    @property
    def min_x(self) -> float:
        """Returns the minimum X-coordinate for component placement."""
        return self.margin

    @property
    def max_x(self) -> float:
        """Returns the maximum X-coordinate for component placement."""
        return self.width - self.margin

    @property
    def min_y(self) -> float:
        """Returns the minimum Y-coordinate for component placement."""
        return self.margin

    @property
    def max_y(self) -> float:
        """Returns the maximum Y-coordinate for component placement."""
        return self.height - self.margin


class ComponentLayoutManager:
    """Manages component layout and positioning for KiCad schematics.

    This class provides robust functionalities for automatically placing components,
    validating their positions within schematic boundaries, and detecting/avoiding
    collisions. It supports various automated layout strategies and offers
    tools for analyzing the resulting component arrangements.
    """

    COMPONENT_SIZES = {
        "resistor": (10.0, 5.0),
        "capacitor": (8.0, 6.0),
        "inductor": (12.0, 8.0),
        "led": (6.0, 8.0),
        "diode": (8.0, 6.0),
        "ic": (20.0, 15.0),
        "transistor": (10.0, 12.0),
        "switch": (12.0, 8.0),
        "connector": (15.0, 10.0),
        "power": (5.0, 5.0),
        "default": (10.0, 8.0),
    }

    def __init__(self, bounds: SchematicBounds | None = None):
        """Initializes the layout manager.

        Args:
            bounds:
                Schematic boundaries to use for layout. If None, defaults to
                A4 dimensions.

        Attributes:
            bounds: The schematic boundaries being used.
            grid_spacing: The spacing for grid snapping, loaded from config.
            component_spacing: Minimum spacing between components, from config.
            placed_components: List to store placed components.
        """
        self.bounds = bounds or SchematicBounds()
        self.grid_spacing = CIRCUIT_DEFAULTS["grid_spacing"]
        self.component_spacing = CIRCUIT_DEFAULTS["component_spacing"]
        self.placed_components: list[ComponentBounds] = []

    def validate_position(self, x: float, y: float, component_type: str = "default") -> bool:
        """Validates that a component fits within the defined schematic boundaries.

        This method checks if a component, based on its center coordinates (x, y)
        and type (for size lookup), fits entirely within the usable area of
        the schematic.

        Args:
            x: The central X-coordinate of the component in millimeters.
            y: The central Y-coordinate of the component in millimeters.
            component_type: The type of component (e.g., "resistor", "ic") used
                to determine its dimensions. Defaults to "default".

        Returns:
            True if the component's bounding box is entirely within the
            schematic's usable boundaries, False otherwise.

        Examples:
            >>> manager = ComponentLayoutManager(SchematicBounds(width=100, height=100, margin=10))
            >>> manager.validate_position(50, 50, "resistor")
            True
            >>> manager.validate_position(5, 5, "default")
            False
        """
        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])

        if x - width / 2 < self.bounds.min_x:
            return False
        if x + width / 2 > self.bounds.max_x:
            return False
        if y - height / 2 < self.bounds.min_y:
            return False
        return not y + height / 2 > self.bounds.max_y

    def snap_to_grid(self, x: float, y: float) -> tuple[float, float]:
        """Snaps coordinates to the nearest grid point.

        This function takes a given (x, y) coordinate and adjusts it to align
        with the nearest grid intersection point, ensuring components are
        placed neatly on the schematic.

        Args:
            x: The X coordinate in millimeters.
            y: The Y coordinate in millimeters.

        Returns:
            A tuple containing the snapped (snapped_x, snapped_y)
            coordinates in millimeters.

        Examples:
            >>> manager = ComponentLayoutManager()
            >>> manager.grid_spacing = 10.0
            >>> manager.snap_to_grid(12.3, 27.8)
            (10.0, 30.0)
            >>> manager.snap_to_grid(5.1, 4.9)
            (10.0, 0.0)
        """
        snapped_x = round(x / self.grid_spacing) * self.grid_spacing
        snapped_y = round(y / self.grid_spacing) * self.grid_spacing
        return snapped_x, snapped_y

    def find_valid_position(
        self,
        component_ref: str,
        component_type: str = "default",
        preferred_x: float | None = None,
        preferred_y: float | None = None,
    ) -> tuple[float, float]:
        """Finds a valid position for a component, avoiding collisions.

        If preferred coordinates are provided and valid, they are used.
        Otherwise, it falls back to a grid-based search for the next
        available position.

        Complexity:
            O(1) if preferred position is valid. O(N*M) in the worst-case for
            grid search, where N and M are the number of grid points.

        Args:
            component_ref: Component reference (e.g., 'R1', 'U2').
            component_type: Type of component (e.g., "resistor", "ic").
            preferred_x: Optional preferred X-coordinate in mm.
            preferred_y: Optional preferred Y-coordinate in mm.

        Returns:
            A tuple of (x, y) coordinates for the found valid position.
        """
        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])

        if preferred_x is not None and preferred_y is not None:
            x, y = self.snap_to_grid(preferred_x, preferred_y)
            if self.validate_position(x, y, component_type):
                candidate = ComponentBounds(component_ref, x, y, width, height)
                if not self._has_collision(candidate):
                    return x, y

        return self._find_next_grid_position(component_ref, component_type)

    def _find_next_grid_position(
        self, component_ref: str, component_type: str
    ) -> tuple[float, float]:
        """Finds the next available grid position within the schematic bounds.

        This private helper performs a systematic grid search starting from the
        top-left corner of the usable area, considering component size and
        avoiding collisions.

        Complexity:
            O(W * H / S^2) in the worst case, where W and H are usable
            width/height and S is grid_spacing.

        Args:
            component_ref: Component reference (e.g., 'R1').
            component_type: Type of component (e.g., "resistor").

        Returns:
            A tuple of (x, y) coordinates for the found position.
        """
        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])

        start_x = self.bounds.min_x + width / 2
        start_y = self.bounds.min_y + height / 2

        current_y = start_y
        while current_y + height / 2 <= self.bounds.max_y:
            current_x = start_x
            while current_x + width / 2 <= self.bounds.max_x:
                x, y = self.snap_to_grid(current_x, current_y)

                if self.validate_position(x, y, component_type):
                    candidate = ComponentBounds(component_ref, x, y, width, height)
                    if not self._has_collision(candidate):
                        return x, y

                current_x += self.component_spacing

            current_y += self.component_spacing

        return self.snap_to_grid(self.bounds.min_x + width / 2, self.bounds.min_y + height / 2)

    def _has_collision(self, candidate: ComponentBounds) -> bool:
        """Checks if a component's bounding box collides with placed components.

        Complexity:
            O(N), where N is the number of `placed_components`.

        Args:
            candidate: The component to check for collisions.

        Returns:
            True if the candidate component overlaps with any placed component.

        Examples:
            >>> manager = ComponentLayoutManager()
            >>> manager.place_component("R1", "resistor", 10, 10)
            (10.0, 10.0)
            >>> candidate_overlap = ComponentBounds("C1", 12, 12, 5, 5)
            >>> manager._has_collision(candidate_overlap)
            True
        """
        return any(candidate.overlaps_with(placed) for placed in self.placed_components)

    def place_component(
        self,
        component_ref: str,
        component_type: str = "default",
        x: float | None = None,
        y: float | None = None,
    ) -> tuple[float, float]:
        """Places a component on the schematic and records its position.

        This method finds a valid position for the component, using explicit
        coordinates if provided, otherwise finding an available spot. The
        component's bounds are then added to the list of placed components.

        Args:
            component_ref: The reference designator of the component.
            component_type: The type of component for size lookup.
            x: Optional preferred X-coordinate in mm.
            y: Optional preferred Y-coordinate in mm.

        Returns:
            A tuple of the final (x, y) coordinates where the component
            was placed.
        """
        final_x, final_y = self.find_valid_position(component_ref, component_type, x, y)

        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])
        component_bounds = ComponentBounds(component_ref, final_x, final_y, width, height)
        self.placed_components.append(component_bounds)

        return final_x, final_y

    def auto_layout_components(
        self, components: list[dict], strategy: LayoutStrategy = LayoutStrategy.GRID
    ) -> list[dict]:
        """Automatically layouts components based on a specified strategy.

        This method dispatches the layout task to a specific private function
        based on the chosen `LayoutStrategy`.

        Complexity:
            Varies by strategy. Generally at least O(N).

        Args:
            components: A list of component dictionaries, each containing at
                least a "reference".
            strategy: The layout strategy to apply.

        Returns:
            A list of the component dictionaries with their "position" updated.
        """
        updated_components = []
        self.clear_layout()

        if strategy == LayoutStrategy.GRID:
            updated_components = self._layout_grid(components)
        elif strategy == LayoutStrategy.ROW:
            updated_components = self._layout_row(components)
        elif strategy == LayoutStrategy.COLUMN:
            updated_components = self._layout_column(components)
        elif strategy == LayoutStrategy.CIRCULAR:
            updated_components = self._layout_circular(components)
        elif strategy == LayoutStrategy.HIERARCHICAL:
            updated_components = self._layout_hierarchical(components)
        else:
            for component in components:
                x, y = self.place_component(
                    component["reference"], component.get("component_type", "default")
                )
                component_copy = component.copy()
                component_copy["position"] = (x, y)
                updated_components.append(component_copy)

        return updated_components

    def _layout_grid(self, components: list[dict]) -> list[dict]:
        """Layouts components in a grid pattern.

        Components are placed row by row, snapping to the grid and attempting
        to fit within schematic bounds.

        Args:
            components: List of component dictionaries to layout.

        Returns:
            List of components with updated positions.
        """
        updated_components = []
        num_components = len(components)
        cols = math.ceil(math.sqrt(num_components))
        
        available_width = self.bounds.usable_width
        available_height = self.bounds.usable_height
        
        col_spacing = available_width / max(1, cols - 1) if cols > 1 else available_width / 2
        row_spacing = available_height / max(1, math.ceil(num_components / cols) - 1) if num_components > cols else available_height / 2

        col_spacing = max(col_spacing, self.component_spacing)
        row_spacing = max(row_spacing, self.component_spacing)

        for i, component in enumerate(components):
            row = i // cols
            col = i % cols
            x = self.bounds.min_x + col * col_spacing
            y = self.bounds.min_y + row * row_spacing
            x, y = self.snap_to_grid(x, y)
            
            component_type = component.get("component_type", "default")
            final_x, final_y = self.place_component(component["reference"], component_type, x, y)
            
            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_row(self, components: list[dict]) -> list[dict]:
        """Layouts components in a single horizontal row.

        Components are evenly spaced across the usable width of the schematic.

        Args:
            components: List of component dictionaries to layout.

        Returns:
            List of components with updated positions.
        """
        updated_components = []
        y = self.bounds.min_y + self.bounds.usable_height / 2
        available_width = self.bounds.usable_width
        
        spacing = available_width / max(1, len(components) - 1) if len(components) > 1 else 0
        spacing = max(spacing, self.component_spacing)
        
        for i, component in enumerate(components):
            x = self.bounds.min_x + i * spacing
            x, y_snapped = self.snap_to_grid(x, y)
            
            component_type = component.get("component_type", "default")
            final_x, final_y = self.place_component(component["reference"], component_type, x, y_snapped)
            
            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_column(self, components: list[dict]) -> list[dict]:
        """Layouts components in a single vertical column.

        Components are evenly spaced along the usable height of the schematic.

        Args:
            components: List of component dictionaries to layout.

        Returns:
            List of components with updated positions.
        """
        updated_components = []
        x = self.bounds.min_x + self.bounds.usable_width / 2
        available_height = self.bounds.usable_height
        
        max_h = max(
            (self.COMPONENT_SIZES.get(c.get("component_type", "default"), self.COMPONENT_SIZES["default"])[1] for c in components),
            default=0
        )
        min_spacing = max(self.component_spacing, max_h + 5.0)
        
        spacing = max(available_height / max(1, len(components) - 1), min_spacing) if len(components) > 1 else min_spacing

        column_x, _ = self.snap_to_grid(x, 0)
        
        for i, component in enumerate(components):
            y = self.bounds.min_y + i * spacing
            _, snapped_y = self.snap_to_grid(0, y)
            
            component_type = component.get("component_type", "default")
            final_x, final_y = self.place_component(component["reference"], component_type, column_x, snapped_y)
            
            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_circular(self, components: list[dict]) -> list[dict]:
        """Layouts components in a circular pattern.

        Components are distributed evenly along the circumference of a circle
        within the usable schematic area.

        Args:
            components: List of component dictionaries to layout.

        Returns:
            List of components with updated positions.
        """
        updated_components = []
        center_x = self.bounds.min_x + self.bounds.usable_width / 2
        center_y = self.bounds.min_y + self.bounds.usable_height / 2
        max_radius = min(self.bounds.usable_width, self.bounds.usable_height) / 3
        
        num_components = len(components)
        angle_step = 2 * math.pi / num_components if num_components > 0 else 0
        
        for i, component in enumerate(components):
            angle = i * angle_step
            x = center_x + max_radius * math.cos(angle)
            y = center_y + max_radius * math.sin(angle)
            
            x, y = self.snap_to_grid(x, y)
            component_type = component.get("component_type", "default")
            final_x, final_y = self.place_component(component["reference"], component_type, x, y)
            
            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)
            
        return updated_components

    def _layout_hierarchical(self, components: list[dict]) -> list[dict]:
        """Layouts components in a hierarchical pattern based on type.

        Components are grouped by their type, and each group is then laid out
        within its own dedicated zone on the schematic.

        Args:
            components: List of component dictionaries to layout.

        Returns:
            List of components with updated positions.
        """
        updated_components = []
        type_groups = {}
        for component in components:
            comp_type = component.get("component_type", "default")
            type_groups.setdefault(comp_type, []).append(component)
        
        num_groups = len(type_groups)
        if not num_groups:
            return []

        cols = math.ceil(math.sqrt(num_groups))
        rows = math.ceil(num_groups / cols)
        zone_width = self.bounds.usable_width / cols
        zone_height = self.bounds.usable_height / rows
        
        for i, (comp_type, group_components) in enumerate(type_groups.items()):
            zone_row, zone_col = divmod(i, cols)
            zone_x_offset = self.bounds.min_x + zone_col * zone_width
            zone_y_offset = self.bounds.min_y + zone_row * zone_height
            
            zone_bounds = SchematicBounds(width=zone_width, height=zone_height, margin=5.0)
            zone_manager = ComponentLayoutManager(zone_bounds)
            
            for component in group_components:
                local_x, local_y = zone_manager.place_component(component["reference"], comp_type)
                global_x = zone_x_offset + local_x
                global_y = zone_y_offset + local_y
                
                updated_component = component.copy()
                updated_component["position"] = (global_x, global_y)
                updated_components.append(updated_component)
                
        return updated_components

    def get_layout_statistics(self) -> dict:
        """Gets statistics about the current component layout.

        Provides insights into the density and arrangement of placed components.

        Complexity:
            O(N^2) due to the nested loop for calculating average spacing.

        Returns:
            A dictionary containing layout statistics:
                - total_components: The number of components placed.
                - area_utilization: The percentage of usable area covered.
                - average_spacing: The average Euclidean distance between pairs.
                - bounds_violations: The number of components outside bounds.
        """
        if not self.placed_components:
            return {
                "total_components": 0,
                "area_utilization": 0.0,
                "average_spacing": 0.0,
                "bounds_violations": 0,
            }

        total_area = sum(c.width * c.height for c in self.placed_components)
        schematic_area = self.bounds.usable_width * self.bounds.usable_height
        area_utilization = total_area / schematic_area if schematic_area > 0 else 0

        total_distance, distance_count = 0, 0
        for i, comp1 in enumerate(self.placed_components):
            for comp2 in self.placed_components[i + 1:]:
                distance = math.hypot(comp1.x - comp2.x, comp1.y - comp2.y)
                total_distance += distance
                distance_count += 1
        average_spacing = total_distance / distance_count if distance_count > 0 else 0

        bounds_violations = sum(1 for c in self.placed_components if 
            c.left < self.bounds.min_x or c.right > self.bounds.max_x or
            c.top < self.bounds.min_y or c.bottom > self.bounds.max_y)

        return {
            "total_components": len(self.placed_components),
            "area_utilization": area_utilization,
            "average_spacing": average_spacing,
            "bounds_violations": bounds_violations,
        }

    def clear_layout(self):
        """Clears all currently placed components from the layout manager.

        Resets the `placed_components` list to an empty state.

        Complexity:
            O(1).
        """
        self.placed_components.clear()
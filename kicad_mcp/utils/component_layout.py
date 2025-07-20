"""
Component layout manager for KiCad schematics.

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
        GRID (str): Places components in a grid pattern.
        ROW (str): Places components in a single horizontal row.
        COLUMN (str): Places components in a single vertical column.
        CIRCULAR (str): Arranges components in a circular formation.
        HIERARCHICAL (str): Organizes components based on their type in a hierarchical structure.
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
        reference (str): The reference designator of the component (e.g., 'R1', 'C10').
        x (float): The central X-coordinate of the component in millimeters.
        y (float): The central Y-coordinate of the component in millimeters.
        width (float): The width of the component bounding box in millimeters.
        height (float): The height of the component bounding box in millimeters.
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
        """Checks if this component's bounding box overlaps with another component's.

        Args:
            other (ComponentBounds): The other component bounding box to check against.

        Returns:
            bool: True if the bounding boxes overlap, False otherwise.

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
        width (float): The total width of the schematic sheet in millimeters (default: 297.0 for A4).
        height (float): The total height of the schematic sheet in millimeters (default: 210.0 for A4).
        margin (float): The margin from the edges of the sheet in millimeters (default: 20.0).
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
        """Returns the minimum X-coordinate for component placement (left boundary of usable area)."""
        return self.margin

    @property
    def max_x(self) -> float:
        """Returns the maximum X-coordinate for component placement (right boundary of usable area)."""
        return self.width - self.margin

    @property
    def min_y(self) -> float:
        """Returns the minimum Y-coordinate for component placement (top boundary of usable area)."""
        return self.margin

    @property
    def max_y(self) -> float:
        """Returns the maximum Y-coordinate for component placement (bottom boundary of usable area)."""
        return self.height - self.margin


class ComponentLayoutManager:
    """Manages component layout and positioning for KiCad schematics.

    This class provides robust functionalities for automatically placing components,
    validating their positions within schematic boundaries, and detecting/avoiding
    collisions. It supports various automated layout strategies and offers
    tools for analyzing the resulting component arrangements.

    Features:
    - Boundary validation for component positions.
    - Automatic layout generation when positions are not specified.
    - Grid-based positioning with configurable spacing.
    - Collision detection and avoidance among placed components.
    - Support for different component types and sizes using predefined dimensions.
    - Multiple automated layout strategies: Grid, Row, Column, Circular, and Hierarchical.
    - Statistical analysis of the current component layout.
    """

    # Default component sizes (width, height) in mm. These are used for layout
    # calculations when a specific component type's size is not provided.
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
            bounds (SchematicBounds | None): Schematic boundaries to use for layout.
                                             If None, defaults to A4 dimensions.

        Attributes:
            bounds (SchematicBounds): The schematic boundaries being used.
            grid_spacing (float): The spacing for grid snapping, loaded from config.
            component_spacing (float): Minimum spacing between components, from config.
            placed_components (list[ComponentBounds]): List to store placed components.
        """
        self.bounds = bounds or SchematicBounds()
        self.grid_spacing = CIRCUIT_DEFAULTS["grid_spacing"]
        self.component_spacing = CIRCUIT_DEFAULTS["component_spacing"]
        self.placed_components: list[ComponentBounds] = []

    def validate_position(self, x: float, y: float, component_type: str = "default") -> bool:
        """Validates that a component position is within the defined schematic boundaries.

        This method checks if a component, based on its center coordinates (x, y)
        and type (for size lookup), fits entirely within the usable area of the schematic.

        Args:
            x (float): The central X-coordinate of the component in millimeters.
            y (float): The central Y-coordinate of the component in millimeters.
            component_type (str): The type of component (e.g., "resistor", "ic")
                                  used to determine its dimensions. Defaults to "default".

        Returns:
            bool: True if the component's bounding box is entirely within the
                  schematic's usable boundaries, False otherwise.

        Examples:
            >>> manager = ComponentLayoutManager(SchematicBounds(width=100, height=100, margin=10))
            >>> manager.validate_position(50, 50, "resistor") # Center of a 100x100 sheet with 10mm margin
            True
            >>> manager.validate_position(5, 5, "default") # Too close to margin
            False
        """
        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])

        # Check boundaries including component size
        if x - width / 2 < self.bounds.min_x:
            return False
        if x + width / 2 > self.bounds.max_x:
            return False
        if y - height / 2 < self.bounds.min_y:
            return False
        return not y + height / 2 > self.bounds.max_y

    def snap_to_grid(self, x: float, y: float) -> tuple[float, float]:
        """Snaps coordinates to the nearest grid point defined by `self.grid_spacing`.

        This function takes a given (x, y) coordinate and adjusts it to align
        with the nearest grid intersection point, ensuring components are
        placed neatly on the schematic.

        Args:
            x (float): The X coordinate in millimeters.
            y (float): The Y coordinate in millimeters.

        Returns:
            tuple[float, float]: A tuple containing the snapped (snapped_x, snapped_y)
                                 coordinates in millimeters.

        Examples:
            If grid_spacing is 10.0:
            >>> manager = ComponentLayoutManager() # Assuming default grid_spacing
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
        """Finds a valid position for a component, prioritizing preferred coordinates
        and avoiding collisions.

        If preferred coordinates are provided and valid (within bounds and no collision),
        they are used. Otherwise, it falls back to finding the next available position
        on a grid-based search.

        Complexity:
            O(1) if preferred position is valid and no collision.
            O(N * M) in worst-case for grid search if no preferred position
            is valid, where N and M are the number of grid points in x and y
            directions within the schematic bounds. In typical use cases, this
            is practical as N*M is not excessively large.

        Args:
            component_ref (str): Component reference (e.g., 'R1', 'U2').
            component_type (str): Type of component (e.g., "resistor", "ic").
            preferred_x (float | None): Preferred X-coordinate in mm (optional).
            preferred_y (float | None): Preferred Y-coordinate in mm (optional).

        Returns:
            tuple[float, float]: A tuple of (x, y) coordinates representing the
                                 found valid position in millimeters.
        """
        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])

        # If preferred position is provided and valid, try to use it
        if preferred_x is not None and preferred_y is not None:
            x, y = self.snap_to_grid(preferred_x, preferred_y)
            if self.validate_position(x, y, component_type):
                candidate = ComponentBounds(component_ref, x, y, width, height)
                if not self._has_collision(candidate):
                    return x, y

        # Fallback: Find next available position using grid search
        return self._find_next_grid_position(component_ref, component_type)

    def _find_next_grid_position(
        self, component_ref: str, component_type: str
    ) -> tuple[float, float]:
        """Finds the next available grid position within the schematic bounds.

        This is a private helper method that performs a systematic grid search
        starting from the top-left corner of the usable schematic area.
        It considers component size, boundary validation, and collision avoidance.

        Complexity:
            O(W * H / S^2) in worst case, where W and H are usable width/height
            and S is grid_spacing. This represents iterating through all possible
            grid points. In practical terms, it's efficient for typical schematic sizes.

        Args:
            component_ref (str): Component reference (e.g., 'R1').
            component_type (str): Type of component (e.g., "resistor").

        Returns:
            tuple[float, float]: A tuple of (x, y) coordinates for the found position.
                                 If no valid position is found, returns a default
                                 position at the top-left of the usable area.
        """
        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])

        # Start from top-left of usable area, adjusting for component's center
        start_x = self.bounds.min_x + width / 2
        start_y = self.bounds.min_y + height / 2

        # Search in rows, then columns (row-major order)
        current_y = start_y
        while current_y + height / 2 <= self.bounds.max_y:
            current_x = start_x
            while current_x + width / 2 <= self.bounds.max_x:
                x, y = self.snap_to_grid(current_x, current_y)

                # Validate position after grid snapping and check for collisions
                if self.validate_position(x, y, component_type):
                    candidate = ComponentBounds(component_ref, x, y, width, height)
                    if not self._has_collision(candidate):
                        return x, y

                current_x += self.component_spacing # Move to next column position

            current_y += self.component_spacing # Move to next row position

        # If no position found (e.g., schematic is full), place at default origin
        # This acts as a fallback to ensure a position is always returned.
        return self.snap_to_grid(self.bounds.min_x + width / 2, self.bounds.min_y + height / 2)

    def _has_collision(self, candidate: ComponentBounds) -> bool:
        """Checks if a candidate component's bounding box collides with any
        already placed components.

        This is a private helper method used to ensure components do not overlap.

        Complexity:
            O(N), where N is the number of already `placed_components`.
            It iterates through all placed components to check for overlaps.

        Args:
            candidate (ComponentBounds): The bounding box of the component to check for collisions.

        Returns:
            bool: True if the candidate component overlaps with any existing
                  placed component, False otherwise.

        Examples:
            >>> manager = ComponentLayoutManager()
            >>> manager.place_component("R1", "resistor", 10, 10)
            (10.0, 10.0)
            >>> candidate_overlap = ComponentBounds("C1", 12, 12, 5, 5)
            >>> manager._has_collision(candidate_overlap)
            True
            >>> candidate_no_overlap = ComponentBounds("C2", 30, 30, 5, 5)
            >>> manager._has_collision(candidate_no_overlap)
            False
        """
        return any(candidate.overlaps_with(placed) for placed in self.placed_components)

    def place_component(
        self,
        component_ref: str,
        component_type: str = "default",
        x: float | None = None,
        y: float | None = None,
    ) -> tuple[float, float]:
        """Places a component on the schematic and records its final position.

        This method first attempts to find a valid position for the component.
        If explicit (x, y) coordinates are provided, it tries to use them;
        otherwise, it automatically finds an available spot. Once a valid
        position is determined, the component's bounding box is added to the
        list of `placed_components`.

        Args:
            component_ref (str): The reference designator of the component (e.g., 'R1').
            component_type (str): The type of component for size lookup (e.g., "resistor").
                                  Defaults to "default".
            x (float | None): Preferred X-coordinate in mm. If None, auto-placement is used.
            y (float | None): Preferred Y-coordinate in mm. If None, auto-placement is used.

        Returns:
            tuple[float, float]: A tuple of the final (x, y) coordinates where the
                                 component was placed in millimeters.
        """
        final_x, final_y = self.find_valid_position(component_ref, component_type, x, y)

        width, height = self.COMPONENT_SIZES.get(component_type, self.COMPONENT_SIZES["default"])
        component_bounds = ComponentBounds(component_ref, final_x, final_y, width, height)
        self.placed_components.append(component_bounds)

        return final_x, final_y

    def auto_layout_components(
        self, components: list[dict], strategy: LayoutStrategy = LayoutStrategy.GRID
    ) -> list[dict]:
        """Automatically layouts a list of components based on a specified strategy.

        This method dispatches the layout task to various private layout
        functions depending on the chosen `LayoutStrategy`. If a strategy is
        not explicitly handled, it falls back to placing components individually.

        Complexity:
            Varies depending on the chosen strategy:
            - O(N) for ROW, COLUMN, CIRCULAR layouts.
            - O(N) or O(sqrt(N) * max_components_per_zone * M) for GRID (where M is grid search).
            - O(N * (Number of Groups)) for HIERARCHICAL.
            Generally, at least O(N) due to iterating through components.

        Args:
            components (list[dict]): A list of component dictionaries. Each dictionary
                                     should contain at least "reference" and optionally
                                     "component_type".
            strategy (LayoutStrategy): The layout strategy to apply (e.g., `LayoutStrategy.GRID`).
                                       Defaults to `LayoutStrategy.GRID`.

        Returns:
            list[dict]: A list of the original component dictionaries, with their
                        "position" updated to the newly calculated (x, y) coordinates.
        """
        updated_components = []

        # Clear existing components to avoid collision detection issues from previous layouts
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
            # Default to individual placement if strategy is not recognized
            for component in components:
                x, y = self.place_component(
                    component["reference"], component.get("component_type", "default")
                )
                component_copy = component.copy() # Avoid modifying original dict
                component_copy["position"] = (x, y)
                updated_components.append(component_copy)

        return updated_components

    def _layout_grid(self, components: list[dict]) -> list[dict]:
        """Layouts components in a grid pattern.

        Components are placed row by row, and column by column,
        snapping to the grid and attempting to fit within schematic bounds.
        If a position is invalid or causes a collision, it falls back to
        `place_component` which finds the next available spot.

        Complexity:
            O(N * (W * H / S^2)) in worst-case, where N is the number of
            components, W/H are usable width/height, and S is grid spacing.
            This is because each component might trigger a grid search.
            However, for a well-behaved grid, it approximates O(N).

        Args:
            components (list[dict]): List of component dictionaries to layout.

        Returns:
            list[dict]: List of components with updated positions.
        """
        updated_components = []

        num_components = len(components)
        # Calculate grid dimensions: aiming for roughly square grid
        cols = math.ceil(math.sqrt(num_components))
        rows = math.ceil(num_components / cols)

        # Calculate initial spacing based on available area
        available_width = self.bounds.usable_width
        available_height = self.bounds.usable_height

        col_spacing = available_width / max(1, cols - 1) if cols > 1 else available_width / 2
        row_spacing = available_height / max(1, rows - 1) if rows > 1 else available_height / 2

        # Ensure minimum spacing between components
        col_spacing = max(col_spacing, self.component_spacing)
        row_spacing = max(row_spacing, self.component_spacing)

        # Place components iteratively in the grid
        for i, component in enumerate(components):
            row = i // cols
            col = i % cols

            # Calculate ideal position based on grid cell
            x = self.bounds.min_x + col * col_spacing
            y = self.bounds.min_y + row * row_spacing

            # Snap to grid and validate, then place component
            x, y = self.snap_to_grid(x, y)
            component_type = component.get("component_type", "default")

            # Try to place at calculated grid position. If not valid/collision, place_component will find next.
            # This handles cases where the calculated position might be out of bounds or overlap.
            final_x, final_y = self.place_component(component["reference"], component_type, x, y)

            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_row(self, components: list[dict]) -> list[dict]:
        """Layouts components in a single horizontal row.

        Components are evenly spaced across the usable width of the schematic,
        snapping to the grid.

        Complexity:
            O(N), where N is the number of components. Each component is
            processed once for placement.

        Args:
            components (list[dict]): List of component dictionaries to layout.

        Returns:
            list[dict]: List of components with updated positions.
        """
        updated_components = []

        # Fix Y coordinate to the center of the usable height for a single row
        y = self.bounds.min_y + self.bounds.usable_height / 2
        available_width = self.bounds.usable_width

        # Calculate spacing for components in the row
        spacing = available_width / max(1, len(components) - 1) if len(components) > 1 else 0
        spacing = max(spacing, self.component_spacing) # Ensure minimum spacing

        for i, component in enumerate(components):
            x = self.bounds.min_x + i * spacing
            x, y_snapped = self.snap_to_grid(x, y) # Snap X to grid, Y uses the fixed snapped_y

            component_type = component.get("component_type", "default")
            # Place component at the calculated (x,y)
            final_x, final_y = self.place_component(component["reference"], component_type, x, y_snapped)

            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_column(self, components: list[dict]) -> list[dict]:
        """Layouts components in a single vertical column.

        Components are evenly spaced along the usable height of the schematic,
        snapping to the grid.

        Complexity:
            O(N), where N is the number of components. Each component is
            processed once for placement.

        Args:
            components (list[dict]): List of component dictionaries to layout.

        Returns:
            list[dict]: List of components with updated positions.
        """
        updated_components = []

        # Fix X coordinate to the center of the usable width for a single column
        x = self.bounds.min_x + self.bounds.usable_width / 2
        available_height = self.bounds.usable_height

        # Calculate proper spacing considering component heights
        # This ensures components don't overlap vertically even with their dimensions
        max_component_height = 0
        if components: # Avoid error for empty list
            max_component_height = max(
                self.COMPONENT_SIZES.get(
                    comp.get("component_type", "default"), self.COMPONENT_SIZES["default"]
                )[1]
                for comp in components
            )
        min_spacing = max(self.component_spacing, max_component_height + 5.0)  # Add 5mm buffer

        # Use either calculated spacing or minimum spacing, whichever is larger
        if len(components) > 1:
            calculated_spacing = available_height / (len(components) - 1)
            spacing = max(calculated_spacing, min_spacing)
        else:
            spacing = min_spacing # For single component or no components

        # Snap the fixed X coordinate for the column to the grid
        column_x, _ = self.snap_to_grid(x, 0) # Y can be 0 as it's just for X snapping

        for i, component in enumerate(components):
            y = self.bounds.min_y + i * spacing
            _, snapped_y = self.snap_to_grid(0, y) # Snap Y to grid, X uses the fixed column_x

            component_type = component.get("component_type", "default")

            # Place component at the calculated (x,y)
            final_x, final_y = self.place_component(component["reference"], component_type, column_x, snapped_y)

            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_circular(self, components: list[dict]) -> list[dict]:
        """Layouts components in a circular pattern.

        Components are distributed evenly along the circumference of a circle
        within the usable schematic area.

        Complexity:
            O(N), where N is the number of components. Each component's position
            is calculated once.

        Args:
            components (list[dict]): List of component dictionaries to layout.

        Returns:
            list[dict]: List of components with updated positions.
        """
        updated_components = []

        # Calculate center of the usable schematic area
        center_x = self.bounds.min_x + self.bounds.usable_width / 2
        center_y = self.bounds.min_y + self.bounds.usable_height / 2

        # Calculate maximum radius to fit components comfortably within bounds
        # (Using 1/3 of min dimension as a heuristic to avoid crowding edges)
        max_radius = min(self.bounds.usable_width, self.bounds.usable_height) / 3

        num_components = len(components)
        # Calculate angle step for even distribution around the circle
        angle_step = 2 * math.pi / num_components if num_components > 0 else 0

        for i, component in enumerate(components):
            angle = i * angle_step
            # Calculate (x, y) coordinates on the circle
            x = center_x + max_radius * math.cos(angle)
            y = center_y + max_radius * math.sin(angle)

            x, y = self.snap_to_grid(x, y) # Snap to grid
            component_type = component.get("component_type", "default")

            # Place component at the calculated (x,y)
            final_x, final_y = self.place_component(component["reference"], component_type, x, y)

            updated_component = component.copy()
            updated_component["position"] = (final_x, final_y)
            updated_components.append(updated_component)

        return updated_components

    def _layout_hierarchical(self, components: list[dict]) -> list[dict]:
        """Layouts components in a hierarchical pattern based on component types.

        Components are grouped by their type, and each group is then laid out
        within its own dedicated zone on the schematic. This provides a structured
        and organized appearance.

        Complexity:
            O(N + G * (W_zone * H_zone / S^2)), where N is total components,
            G is the number of unique component types (groups), and
            (W_zone * H_zone / S^2) represents the cost of placing components
            within a zone (potentially a grid search).
            In a practical sense, it's more complex than simple linear layouts.

        Args:
            components (list[dict]): List of component dictionaries to layout.

        Returns:
            list[dict]: List of components with updated positions.
        """
        updated_components = []

        # Group components by type
        type_groups = {}
        for component in components:
            comp_type = component.get("component_type", "default")
            if comp_type not in type_groups:
                type_groups[comp_type] = []
            type_groups[comp_type].append(component)

        num_groups = len(type_groups)
        if num_groups == 0:
            return updated_components

        # Divide schematic into zones (grid of zones)
        cols = math.ceil(math.sqrt(num_groups))
        rows = math.ceil(num_groups / cols)

        zone_width = self.bounds.usable_width / cols
        zone_height = self.bounds.usable_height / rows

        for group_index, (comp_type, group_components) in enumerate(type_groups.items()):
            zone_row = group_index // cols
            zone_col = group_index % cols

            # Calculate the top-left origin of the current zone
            zone_x_offset = self.bounds.min_x + zone_col * zone_width
            zone_y_offset = self.bounds.min_y + zone_row * zone_height

            # Create temporary layout manager for this specific zone
            # This allows each group to be laid out independently within its zone
            zone_bounds = SchematicBounds(width=zone_width, height=zone_height, margin=5.0) # Small margin for zone
            zone_manager = ComponentLayoutManager(zone_bounds)

            # Layout components within this zone (e.g., using default grid layout within the zone)
            # The inner layout could be customized here too, but defaulting to grid for simplicity
            for component in group_components:
                # Place component within its zone's local coordinates
                local_x, local_y = zone_manager.place_component(component["reference"], comp_type)
                
                # Adjust coordinates to global schematic space
                global_x = zone_x_offset + local_x
                global_y = zone_y_offset + local_y

                updated_component = component.copy()
                updated_component["position"] = (global_x, global_y)
                updated_components.append(updated_component)

        return updated_components

    def get_layout_statistics(self) -> dict:
        """Gets statistics about the current component layout.

        Provides insights into the density and arrangement of placed components,
        including total count, area utilization, average spacing, and boundary violations.

        Complexity:
            O(N^2) in worst-case, where N is the number of `placed_components`.
            This is due to the nested loop used for calculating `average_spacing`.
            Other calculations are O(N).

        Returns:
            dict: A dictionary containing layout statistics:
                  - "total_components" (int): The number of components currently placed.
                  - "area_utilization" (float): The percentage of the usable schematic
                                                area covered by components (0.0 to 1.0).
                  - "average_spacing" (float): The average Euclidean distance between
                                               all unique pairs of placed components.
                  - "bounds_violations" (int): The number of components that extend
                                               beyond the schematic's usable boundaries.
        """
        if not self.placed_components:
            return {
                "total_components": 0,
                "area_utilization": 0.0,
                "average_spacing": 0.0,
                "bounds_violations": 0,
            }

        total_area = sum(comp.width * comp.height for comp in self.placed_components)
        schematic_area = self.bounds.usable_width * self.bounds.usable_height
        area_utilization = total_area / schematic_area if schematic_area > 0 else 0

        # Calculate average spacing between components
        total_distance = 0
        distance_count = 0
        for i, comp1 in enumerate(self.placed_components):
            for comp2 in self.placed_components[i + 1 :]: # Nested loop for unique pairs
                distance = math.sqrt((comp1.x - comp2.x) ** 2 + (comp1.y - comp2.y) ** 2)
                total_distance += distance
                distance_count += 1

        average_spacing = total_distance / distance_count if distance_count > 0 else 0

        # Check for bounds violations (components extending outside boundaries)
        bounds_violations = 0
        for comp in self.placed_components:
            if (
                comp.left < self.bounds.min_x
                or comp.right > self.bounds.max_x
                or comp.top < self.bounds.min_y
                or comp.bottom > self.bounds.max_y
            ):
                bounds_violations += 1

        return {
            "total_components": len(self.placed_components),
            "area_utilization": area_utilization,
            "average_spacing": average_spacing,
            "bounds_violations": bounds_violations,
        }

    def clear_layout(self):
        """Clears all currently placed components from the layout manager.

        Resets the `placed_components` list, effectively emptying the schematic
        of all previously placed items.

        Complexity:
            O(1) as it directly clears a list.
        """
        self.placed_components.clear()
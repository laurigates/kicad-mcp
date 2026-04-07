"""Wire connectivity tracing engine for KiCad schematic netlist extraction.

Uses Union-Find to group connected wire segments, pins, and labels into nets.
"""

import logging

logger = logging.getLogger(__name__)

COORDINATE_TOLERANCE = 0.01  # mm


class UnionFind:
    """Disjoint Set Union with path compression and union by rank."""

    def __init__(self) -> None:
        self._parent: dict[int, int] = {}
        self._rank: dict[int, int] = {}

    def find(self, x: int) -> int:
        """Find the root representative of x's set."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: int, y: int) -> None:
        """Merge the sets containing x and y."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

    def groups(self) -> dict[int, list[int]]:
        """Return all disjoint sets as {root: [members]}."""
        result: dict[int, list[int]] = {}
        for x in self._parent:
            root = self.find(x)
            result.setdefault(root, []).append(x)
        return result


def quantize_point(x: float, y: float, tolerance: float = COORDINATE_TOLERANCE) -> tuple[int, int]:
    """Quantize a coordinate pair to integer grid for exact hashing.

    Points within `tolerance` of each other map to the same bucket.
    """
    return (round(x / tolerance), round(y / tolerance))


class ConnectivityEngine:
    """Traces wire connectivity to build a netlist from schematic geometry.

    Takes pre-parsed schematic elements (wires, pins, junctions, labels)
    and produces net groupings.
    """

    def __init__(self, tolerance: float = COORDINATE_TOLERANCE) -> None:
        self.tolerance = tolerance
        self._uf = UnionFind()
        self._point_to_id: dict[tuple[int, int], int] = {}
        self._next_id: int = 0
        self._pins: list[tuple[str, str, int]] = []  # (comp_ref, pin_num, point_id)
        self._label_points: list[tuple[str, str, int]] = []  # (text, label_type, point_id)

    def _get_point_id(self, x: float, y: float) -> int:
        """Get or create a unique ID for a quantized point."""
        key = quantize_point(x, y, self.tolerance)
        if key not in self._point_to_id:
            pid = self._next_id
            self._next_id += 1
            self._point_to_id[key] = pid
            # Ensure the point exists in union-find
            self._uf.find(pid)
        return self._point_to_id[key]

    def add_wires(self, wires: list[dict]) -> None:
        """Register wire segments. Each wire's start and end are unioned."""
        for wire in wires:
            start = wire["start"]
            end = wire["end"]
            sid = self._get_point_id(start["x"], start["y"])
            eid = self._get_point_id(end["x"], end["y"])
            self._uf.union(sid, eid)

    def add_junctions(self, junctions: list[dict]) -> None:
        """Register junctions. Ensures junction points exist in the graph.

        KiCad breaks wires at junctions, so the junction coordinate
        already matches wire endpoints and will be merged via quantization.
        """
        for junction in junctions:
            self._get_point_id(junction["x"], junction["y"])

    def add_labels(self, labels: list[dict], label_type: str = "local") -> None:
        """Register labels. Labels with the same text create named net groups."""
        for label in labels:
            pos = label["position"]
            pid = self._get_point_id(pos["x"], pos["y"])
            self._label_points.append((label["text"], label_type, pid))

    def add_pin(self, component_ref: str, pin_num: str, x: float, y: float) -> None:
        """Register a component pin at its wire connection point."""
        pid = self._get_point_id(x, y)
        self._pins.append((component_ref, pin_num, pid))

    def build_nets(self) -> dict[str, list[dict]]:
        """Run the connectivity algorithm and return the net dictionary.

        Returns:
            {"net_name": [{"component": "R1", "pin": "1"}, ...]}
        """
        # Phase 1: Merge label groups — labels with same text are same net
        label_text_to_pids: dict[str, list[int]] = {}
        for text, _label_type, pid in self._label_points:
            label_text_to_pids.setdefault(text, []).append(pid)

        for pids in label_text_to_pids.values():
            for i in range(1, len(pids)):
                self._uf.union(pids[0], pids[i])

        # Phase 2: Collect pins by their group root
        root_to_pins: dict[int, list[tuple[str, str]]] = {}
        for comp_ref, pin_num, pid in self._pins:
            root = self._uf.find(pid)
            root_to_pins.setdefault(root, []).append((comp_ref, pin_num))

        # Phase 3: Collect label info by group root
        root_to_labels: dict[int, list[tuple[str, str]]] = {}
        for text, label_type, pid in self._label_points:
            root = self._uf.find(pid)
            root_to_labels.setdefault(root, []).append((text, label_type))

        # Phase 4: Build nets — only groups with pins
        nets: dict[str, list[dict]] = {}
        for root, pins in root_to_pins.items():
            if not pins:
                continue

            # Determine net name
            net_name = self._pick_net_name(root, pins, root_to_labels)

            # Deduplicate pins (same component+pin registered multiple times)
            seen = set()
            connections = []
            for comp_ref, pin_num in pins:
                key = (comp_ref, pin_num)
                if key not in seen:
                    seen.add(key)
                    connections.append({"component": comp_ref, "pin": pin_num})

            if connections:
                nets[net_name] = connections

        return nets

    def _pick_net_name(
        self,
        root: int,
        pins: list[tuple[str, str]],
        root_to_labels: dict[int, list[tuple[str, str]]],
    ) -> str:
        """Choose a net name: prefer global labels, then local, then synthetic."""
        labels = root_to_labels.get(root, [])
        # Prefer global labels over local
        global_labels = [text for text, ltype in labels if ltype == "global"]
        if global_labels:
            return global_labels[0]
        local_labels = [text for text, ltype in labels if ltype == "local"]
        if local_labels:
            return local_labels[0]
        hierarchical_labels = [text for text, ltype in labels if ltype == "hierarchical"]
        if hierarchical_labels:
            return hierarchical_labels[0]
        # Synthetic name from first pin
        comp, pin = pins[0]
        return f"Net-({comp}-{pin})"

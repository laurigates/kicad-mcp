"""Tests for the connectivity engine (Union-Find based netlist builder)."""

import pytest

from kicad_mcp.utils.connectivity import ConnectivityEngine, UnionFind, quantize_point


class TestUnionFind:
    """Tests for the Union-Find data structure."""

    def test_initial_find_returns_self(self):
        uf = UnionFind()
        assert uf.find(0) == 0
        assert uf.find(5) == 5

    def test_union_merges_sets(self):
        uf = UnionFind()
        uf.union(0, 1)
        assert uf.find(0) == uf.find(1)

    def test_transitive_union(self):
        uf = UnionFind()
        uf.union(0, 1)
        uf.union(1, 2)
        assert uf.find(0) == uf.find(2)

    def test_separate_sets_remain_separate(self):
        uf = UnionFind()
        uf.union(0, 1)
        uf.union(2, 3)
        assert uf.find(0) != uf.find(2)

    def test_groups_returns_all_sets(self):
        uf = UnionFind()
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(3, 4)
        groups = uf.groups()
        # Should have 2 groups: {0,1,2} and {3,4}
        group_sets = [set(members) for members in groups.values()]
        assert {0, 1, 2} in group_sets
        assert {3, 4} in group_sets

    def test_groups_singletons_included(self):
        uf = UnionFind()
        # Access elements to register them
        uf.find(0)
        uf.find(1)
        groups = uf.groups()
        assert len(groups) == 2

    def test_union_idempotent(self):
        uf = UnionFind()
        uf.union(0, 1)
        uf.union(0, 1)
        groups = uf.groups()
        group_sets = [set(members) for members in groups.values()]
        assert {0, 1} in group_sets


class TestQuantizePoint:
    """Tests for coordinate quantization."""

    def test_exact_coordinates(self):
        assert quantize_point(63.5, 91.44) == quantize_point(63.5, 91.44)

    def test_within_tolerance_same_bucket(self):
        # Default tolerance is 0.01mm
        p1 = quantize_point(63.5, 91.44)
        p2 = quantize_point(63.504, 91.444)
        assert p1 == p2

    def test_beyond_tolerance_different_bucket(self):
        p1 = quantize_point(63.5, 91.44)
        p2 = quantize_point(63.52, 91.44)
        assert p1 != p2

    def test_custom_tolerance(self):
        p1 = quantize_point(63.5, 91.44, tolerance=0.1)
        p2 = quantize_point(63.54, 91.44, tolerance=0.1)
        assert p1 == p2

    def test_negative_coordinates(self):
        p1 = quantize_point(-10.0, -20.0)
        p2 = quantize_point(-10.0, -20.0)
        assert p1 == p2

    def test_returns_tuple(self):
        result = quantize_point(1.0, 2.0)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestConnectivityEngineWires:
    """Tests for wire handling in ConnectivityEngine."""

    def test_single_wire_creates_connected_endpoints(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}])
        engine.add_pin("R1", "1", 0, 0)
        engine.add_pin("R2", "1", 10, 0)
        nets = engine.build_nets()
        # Both pins should be in the same net
        _assert_pins_in_same_net(nets, "R1", "1", "R2", "1")

    def test_chained_wires_same_net(self):
        engine = ConnectivityEngine()
        engine.add_wires(
            [
                {"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}},
                {"start": {"x": 5, "y": 0}, "end": {"x": 10, "y": 0}},
            ]
        )
        engine.add_pin("R1", "1", 0, 0)
        engine.add_pin("R2", "1", 10, 0)
        nets = engine.build_nets()
        _assert_pins_in_same_net(nets, "R1", "1", "R2", "1")

    def test_disconnected_wires_separate_nets(self):
        engine = ConnectivityEngine()
        engine.add_wires(
            [
                {"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}},
                {"start": {"x": 20, "y": 0}, "end": {"x": 25, "y": 0}},
            ]
        )
        engine.add_pin("R1", "1", 0, 0)
        engine.add_pin("R2", "1", 25, 0)
        nets = engine.build_nets()
        _assert_pins_in_different_nets(nets, "R1", "1", "R2", "1")

    def test_empty_wires(self):
        engine = ConnectivityEngine()
        engine.add_wires([])
        nets = engine.build_nets()
        assert nets == {}


class TestConnectivityEngineJunctions:
    """Tests for junction handling."""

    def test_junction_at_wire_meeting_point(self):
        engine = ConnectivityEngine()
        # T-junction: KiCad breaks wires at junctions, so the horizontal wire
        # becomes two segments meeting the vertical wire at (5, 0)
        engine.add_wires(
            [
                {"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}},
                {"start": {"x": 5, "y": 0}, "end": {"x": 10, "y": 0}},
                {"start": {"x": 5, "y": -5}, "end": {"x": 5, "y": 0}},
            ]
        )
        engine.add_junctions([{"x": 5, "y": 0}])
        engine.add_pin("R1", "1", 0, 0)
        engine.add_pin("R2", "1", 10, 0)
        engine.add_pin("R3", "1", 5, -5)
        nets = engine.build_nets()
        # All three should be in the same net
        _assert_pins_in_same_net(nets, "R1", "1", "R2", "1")
        _assert_pins_in_same_net(nets, "R1", "1", "R3", "1")


class TestConnectivityEngineLabels:
    """Tests for label-based connectivity."""

    def test_same_label_merges_nets(self):
        engine = ConnectivityEngine()
        # Two separate wires, each with a label "SIG_A"
        engine.add_wires(
            [
                {"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}},
                {"start": {"x": 20, "y": 0}, "end": {"x": 25, "y": 0}},
            ]
        )
        engine.add_labels(
            [
                {"text": "SIG_A", "position": {"x": 5, "y": 0}},
                {"text": "SIG_A", "position": {"x": 20, "y": 0}},
            ],
            label_type="local",
        )
        engine.add_pin("R1", "1", 0, 0)
        engine.add_pin("R2", "1", 25, 0)
        nets = engine.build_nets()
        _assert_pins_in_same_net(nets, "R1", "1", "R2", "1")
        # Net should be named SIG_A
        net_name = _find_net_containing(nets, "R1", "1")
        assert net_name == "SIG_A"

    def test_different_labels_separate_nets(self):
        engine = ConnectivityEngine()
        engine.add_wires(
            [
                {"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}},
                {"start": {"x": 20, "y": 0}, "end": {"x": 25, "y": 0}},
            ]
        )
        engine.add_labels(
            [
                {"text": "SIG_A", "position": {"x": 5, "y": 0}},
                {"text": "SIG_B", "position": {"x": 20, "y": 0}},
            ],
            label_type="local",
        )
        engine.add_pin("R1", "1", 0, 0)
        engine.add_pin("R2", "1", 25, 0)
        nets = engine.build_nets()
        _assert_pins_in_different_nets(nets, "R1", "1", "R2", "1")

    def test_global_label_names_net(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}}])
        engine.add_labels(
            [{"text": "RESET", "position": {"x": 5, "y": 0}}],
            label_type="global",
        )
        engine.add_pin("U1", "3", 0, 0)
        nets = engine.build_nets()
        assert "RESET" in nets

    def test_global_label_preferred_over_local(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}}])
        engine.add_labels(
            [{"text": "local_sig", "position": {"x": 0, "y": 0}}],
            label_type="local",
        )
        engine.add_labels(
            [{"text": "GLOBAL_SIG", "position": {"x": 5, "y": 0}}],
            label_type="global",
        )
        engine.add_pin("R1", "1", 0, 0)
        nets = engine.build_nets()
        net_name = _find_net_containing(nets, "R1", "1")
        assert net_name == "GLOBAL_SIG"


class TestConnectivityEnginePins:
    """Tests for pin registration and net output format."""

    def test_pin_at_wire_endpoint_joins_net(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}])
        engine.add_pin("R1", "2", 0, 0)
        nets = engine.build_nets()
        found = False
        for connections in nets.values():
            for conn in connections:
                if conn["component"] == "R1" and conn["pin"] == "2":
                    found = True
        assert found, "Pin R1.2 should appear in a net"

    def test_pin_not_at_any_wire_excluded(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}])
        engine.add_pin("R1", "1", 100, 100)  # Far from any wire
        nets = engine.build_nets()
        # Pin at (100, 100) is not near any wire — should not appear in any net
        # (or appear in a singleton net with just itself, which is acceptable)
        for connections in nets.values():
            if len(connections) > 1:
                refs = {(c["component"], c["pin"]) for c in connections}
                assert ("R1", "1") not in refs

    def test_output_format(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}])
        engine.add_pin("R1", "2", 0, 0)
        engine.add_pin("R2", "1", 10, 0)
        nets = engine.build_nets()
        # Verify output format: dict of net_name -> list of {component, pin}
        assert isinstance(nets, dict)
        for net_name, connections in nets.items():
            assert isinstance(net_name, str)
            assert isinstance(connections, list)
            for conn in connections:
                assert "component" in conn
                assert "pin" in conn

    def test_synthetic_net_name_when_no_label(self):
        engine = ConnectivityEngine()
        engine.add_wires([{"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}])
        engine.add_pin("R1", "2", 0, 0)
        engine.add_pin("R2", "1", 10, 0)
        nets = engine.build_nets()
        # Should have exactly one net with a synthetic name
        assert len(nets) == 1
        net_name = list(nets.keys())[0]
        assert net_name.startswith("Net-(")


# --- Test helpers ---


def _assert_pins_in_same_net(nets: dict, comp1: str, pin1: str, comp2: str, pin2: str):
    """Assert two pins are in the same net."""
    for _net_name, connections in nets.items():
        refs = {(c["component"], c["pin"]) for c in connections}
        if (comp1, pin1) in refs and (comp2, pin2) in refs:
            return
    pytest.fail(f"{comp1}.{pin1} and {comp2}.{pin2} not found in same net. Nets: {nets}")


def _assert_pins_in_different_nets(nets: dict, comp1: str, pin1: str, comp2: str, pin2: str):
    """Assert two pins are NOT in the same net."""
    for net_name, connections in nets.items():
        refs = {(c["component"], c["pin"]) for c in connections}
        if (comp1, pin1) in refs and (comp2, pin2) in refs:
            pytest.fail(
                f"{comp1}.{pin1} and {comp2}.{pin2} should be in different nets "
                f"but both found in '{net_name}'"
            )


def _find_net_containing(nets: dict, comp: str, pin: str) -> str | None:
    """Find the net name containing a specific pin."""
    for net_name, connections in nets.items():
        for conn in connections:
            if conn["component"] == comp and conn["pin"] == pin:
                return net_name
    return None

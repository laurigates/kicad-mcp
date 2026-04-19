"""Integration tests covering wire emission when parsed connections omit pin numbers.

Regression coverage for issue #57: shorthand references like ``VCC -> R1.1`` emit
connections with ``start_pin=None``/``end_pin=None``. The S-expression handler
previously dropped these silently, yielding schematics with no wires at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kicad_mcp.tools.text_to_schematic import TextToSchematicParser
from kicad_mcp.utils.netlist_parser import extract_netlist
from kicad_mcp.utils.sexpr_service import get_sexpr_service

VOLTAGE_DIVIDER = """
circuit: Voltage Divider

components:
  R1 resistor 10k (100, 60)
  R2 resistor 10k (100, 100)

power:
  VCC +5V (60, 40)
  GND GND (60, 120)

connections:
  VCC -> R1.1
  R1.2 -> R2.1
  R2.2 -> GND
"""


def _generate_divider_sexpr() -> str:
    parser = TextToSchematicParser()
    circuit = parser.parse_simple_text(VOLTAGE_DIVIDER)

    assert circuit.components, "expected components parsed from voltage divider fixture"
    assert circuit.power_symbols, "expected power symbols parsed from voltage divider fixture"
    assert len(circuit.connections) == 3

    # At least one connection must carry pin=None to exercise the regression path.
    assert any(c.start_pin is None or c.end_pin is None for c in circuit.connections)

    components = [
        {
            "reference": c.reference,
            "value": c.value,
            "position": c.position,
            "symbol_library": c.symbol_library,
            "symbol_name": c.symbol_name,
        }
        for c in circuit.components
    ]
    power_symbols = [
        {"reference": p.reference, "power_type": p.power_type, "position": p.position}
        for p in circuit.power_symbols
    ]
    connections = [
        {
            "start_component": c.start_component,
            "start_pin": c.start_pin,
            "end_component": c.end_component,
            "end_pin": c.end_pin,
        }
        for c in circuit.connections
    ]

    service = get_sexpr_service()
    return service.generate_schematic(circuit.name, components, power_symbols, connections)


def test_shorthand_connections_emit_wires() -> None:
    """`VCC -> R1.1` style connections must produce wires, not be silently dropped."""
    sexpr = _generate_divider_sexpr()
    # KiCad emits wires with either "(wire " or "(wire\n" depending on pretty-print.
    wire_count = sexpr.count("(wire\n") + sexpr.count("(wire ")
    assert wire_count >= 3, (
        f"expected at least 3 wires for the voltage divider; got {wire_count}:\n{sexpr}"
    )


def test_shorthand_connections_round_trip_through_netlist(tmp_path: Path) -> None:
    """Wires emitted for shorthand connections must be visible to the netlist parser."""
    sexpr = _generate_divider_sexpr()
    schematic_path = tmp_path / "voltage_divider.kicad_sch"
    schematic_path.write_text(sexpr)

    netlist = extract_netlist(str(schematic_path))

    assert "error" not in netlist, f"netlist extraction reported error: {netlist.get('error')}"
    assert netlist.get("component_count", 0) >= 2
    assert netlist.get("net_count", 0) >= 2, (
        f"expected at least two nets (VCC and GND rails) from shorthand connections; got {netlist}"
    )


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    pytest.main([__file__, "-v"])

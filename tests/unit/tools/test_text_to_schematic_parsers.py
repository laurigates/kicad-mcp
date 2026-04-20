"""Regression tests for text_to_schematic parser bugs (#19, #20, #74)."""

import logging

import pytest

from kicad_mcp.tools.text_to_schematic import TextToSchematicParser


class TestSimpleFormatParser:
    """Issue #20: 'simple' format docs use ``- R1: type value at (x, y)``."""

    def test_yaml_bullet_prefix_is_stripped(self):
        """Lines starting with ``- `` are parsed the same as bare lines."""
        parser = TextToSchematicParser()
        text = """circuit "demo":
  components:
    - R1: resistor 330 at (10, 20)
  power:
    - VCC: 3.3V at (5, 5)
  connections:
    - R1.1 -> VCC"""
        circuit = parser.parse_simple_text(text)

        assert circuit.name == "demo"
        assert len(circuit.components) == 1
        comp = circuit.components[0]
        assert comp.reference == "R1"
        assert comp.component_type == "resistor"
        assert comp.value == "330"
        assert comp.position == (10.0, 20.0)

        assert len(circuit.power_symbols) == 1
        assert circuit.power_symbols[0].reference == "VCC"
        assert circuit.power_symbols[0].power_type == "3.3V"

        assert len(circuit.connections) == 1
        conn = circuit.connections[0]
        assert conn.start_component == "R1"
        assert conn.start_pin == "1"
        assert conn.end_component == "VCC"

    def test_full_issue_20_input_parses(self):
        """Exact input from issue #20 must parse without raising."""
        parser = TextToSchematicParser()
        text = """circuit "ESP32 with LED and Button":
  components:
    - U1: ic ESP32-DevKitC at (100, 100)
    - R1: resistor 330 at (160, 80)
    - D1: led LED at (160, 120)
    - SW1: switch SW_Push at (40, 80)
    - R2: resistor 10k at (40, 120)
  power:
    - VCC: 3.3V at (40, 150)
    - GND: GND at (160, 150)
  connections:
    - U1.GPIO2 -> R1.1
    - R1.2 -> D1.A
    - D1.K -> GND
    - U1.GPIO4 -> SW1.1
    - SW1.2 -> R2.1
    - R2.2 -> VCC
    - U1.GND -> GND
    - U1.3V3 -> VCC"""
        circuit = parser.parse_simple_text(text)

        assert circuit.name == "ESP32 with LED and Button"
        assert len(circuit.components) == 5
        assert {c.reference for c in circuit.components} == {"U1", "R1", "D1", "SW1", "R2"}
        assert len(circuit.power_symbols) == 2
        assert len(circuit.connections) == 8


class TestYamlFormatParser:
    """Issue #19: flat YAML with list-of-lists connections."""

    def test_flat_yaml_without_circuit_wrapper(self):
        """Top-level components/power/connections keys are accepted."""
        parser = TextToSchematicParser()
        text = """components:
  - reference: U1
    type: ic
    value: ESP32-DevKitC
    position: [100, 100]
connections:
  - - U1:GPIO2
    - R1:1
power:
  - net: 3V3
    type: VCC
    position: [50, 150]"""
        circuit = parser.parse_yaml_circuit(text)

        assert len(circuit.components) == 1
        comp = circuit.components[0]
        assert comp.reference == "U1"
        assert comp.component_type == "ic"
        assert comp.position == (100.0, 100.0)

        assert len(circuit.power_symbols) == 1
        assert circuit.power_symbols[0].reference == "3V3"
        assert circuit.power_symbols[0].power_type == "VCC"

        assert len(circuit.connections) == 1
        conn = circuit.connections[0]
        assert conn.start_component == "U1"
        assert conn.start_pin == "GPIO2"
        assert conn.end_component == "R1"
        assert conn.end_pin == "1"

    def test_list_of_lists_connections(self):
        """``[[a, b], [c, d]]`` connection format from issue #19."""
        parser = TextToSchematicParser()
        text = """components:
  - reference: A
    type: resistor
    value: "1k"
    position: [0, 0]
connections:
  - - A:1
    - B:2
  - - B:3
    - C:4"""
        circuit = parser.parse_yaml_circuit(text)

        assert len(circuit.connections) == 2
        assert circuit.connections[0].start_component == "A"
        assert circuit.connections[0].end_component == "B"
        assert circuit.connections[1].start_component == "B"
        assert circuit.connections[1].end_component == "C"

    def test_colon_pin_separator(self):
        """``U1:GPIO2`` (YAML-friendly) parses same as ``U1.GPIO2``."""
        parser = TextToSchematicParser()
        dot = parser._parse_connection("U1.GPIO2 -> R1.1")
        colon = parser._parse_connection("U1:GPIO2 -> R1:1")
        assert dot is not None and colon is not None
        assert (dot.start_component, dot.start_pin) == (colon.start_component, colon.start_pin)
        assert (dot.end_component, dot.end_pin) == (colon.end_component, colon.end_pin)


class TestEdgeCases:
    """Issue #74: parser edge cases."""

    def setup_method(self):
        self.parser = TextToSchematicParser()

    # -- Edge case 1: flat-YAML false positive on single key overlap ----------

    def test_flat_yaml_false_positive_single_key(self):
        """A YAML dict sharing only one section key should NOT be treated as flat.

        ``{"components": "some_value", "name": "foo"}`` has one overlap
        with the section keys but the value is not a list, so it should
        fall through to the circuit-wrapper branch (and error there since
        the body is not a mapping).
        """
        yaml_text = """
components: not-a-list
name: foo
"""
        with pytest.raises(ValueError, match="must be a mapping"):
            self.parser.parse_yaml_circuit(yaml_text)

    def test_flat_yaml_true_positive_two_keys(self):
        """Two or more section keys with list/None values IS flat format."""
        yaml_text = """
components:
  - reference: R1
    type: resistor
    value: "1k"
    position: [0, 0]
connections:
  - R1.1 -> R1.2
"""
        circuit = self.parser.parse_yaml_circuit(yaml_text)
        assert circuit.name == "Untitled Circuit"
        assert len(circuit.components) == 1

    # -- Edge case 2: _split_endpoint splits 3.3V on '.' -------------------

    def test_split_endpoint_voltage_with_dot(self):
        """``3.3V`` must NOT be split into component='3' pin='3V'."""
        comp, pin = TextToSchematicParser._split_endpoint("3.3V")
        assert comp == "3.3V"
        assert pin is None

    def test_split_endpoint_normal_pin(self):
        """``R1.1`` should still split normally."""
        comp, pin = TextToSchematicParser._split_endpoint("R1.1")
        assert comp == "R1"
        assert pin == "1"

    def test_connection_with_voltage_endpoint(self):
        """``3.3V -> R1.1`` should parse correctly via public API."""
        circuit = self.parser.parse_yaml_circuit("""
components:
  - reference: R1
    type: resistor
    value: "1k"
    position: [0, 0]
connections:
  - "3.3V -> R1.1"
""")
        conn = circuit.connections[0]
        assert conn.start_component == "3.3V"
        assert conn.start_pin is None
        assert conn.end_component == "R1"
        assert conn.end_pin == "1"

    # -- Edge case 3: circuit names with ':' truncated ----------------------

    def test_circuit_name_with_colon_simple_text(self):
        """``circuit "My Circuit: v2":`` must preserve the full quoted name."""
        text = """circuit "My Circuit: v2":
components:
connections:
"""
        circuit = self.parser.parse_simple_text(text)
        assert circuit.name == "My Circuit: v2"

    def test_circuit_name_with_colon_yaml(self):
        """YAML keys with colons require proper quoting to survive yaml.safe_load.

        When the YAML key is properly quoted, the parser should extract the name.
        """
        yaml_text = """'circuit "My Circuit - v2"':
  components: []
  connections: []
"""
        circuit = self.parser.parse_yaml_circuit(yaml_text)
        assert circuit.name == "My Circuit - v2"

    # -- Edge case 4: 3-element list connection silently dropped -------------

    def test_three_element_list_connection_warns(self, caplog):
        """A 3-element list connection should log a warning."""
        yaml_text = """
components:
  - reference: A
    type: resistor
    value: "1k"
    position: [0, 0]
connections:
  - [A:1, B:2, C:3]
"""
        with caplog.at_level(logging.WARNING):
            circuit = self.parser.parse_yaml_circuit(yaml_text)

        assert len(circuit.connections) == 0
        assert any("3" in r.message and "element" in r.message.lower() for r in caplog.records)

    # -- Edge case 5: private-method tests via public API -------------------

    def test_parse_connection_via_public_api(self):
        """Connection parsing should be testable through parse_yaml_circuit."""
        yaml_text = """
components:
  - reference: U1
    type: ic
    value: ESP32
    position: [0, 0]
connections:
  - "U1.GPIO2 -> R1.1"
  - - U1:GPIO2
    - R1:1
"""
        circuit = self.parser.parse_yaml_circuit(yaml_text)
        assert len(circuit.connections) == 2

        # String format
        conn0 = circuit.connections[0]
        assert conn0.start_component == "U1"
        assert conn0.start_pin == "GPIO2"
        assert conn0.end_component == "R1"
        assert conn0.end_pin == "1"

        # List format
        conn1 = circuit.connections[1]
        assert conn1.start_component == "U1"
        assert conn1.start_pin == "GPIO2"
        assert conn1.end_component == "R1"
        assert conn1.end_pin == "1"

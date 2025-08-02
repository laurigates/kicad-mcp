"""
Tests for enhanced ComponentPinMapper circuit logic functionality.
"""

from kicad_mcp.utils.pin_mapper import ComponentPinMapper


class TestComponentPinMapperCircuitLogic:
    """Test enhanced circuit logic functionality."""

    def test_parse_explicit_connections(self):
        """Test parsing explicit connections from circuit description."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
            ],
            "connections": [
                {
                    "net": "LED_NET",
                    "from": {"component": "R1", "pin": "2"},
                    "to": {"component": "LED1", "pin": "2"},
                    "type": "signal",
                }
            ],
        }

        connections = mapper.parse_circuit_connections(circuit_description)

        assert len(connections) == 1
        conn = connections[0]
        assert conn["net_name"] == "LED_NET"
        assert conn["source_component"] == "R1"
        assert conn["source_pin"] == "2"
        assert conn["target_component"] == "LED1"
        assert conn["target_pin"] == "2"
        assert conn["connection_type"] == "signal"

    def test_detect_power_connections(self):
        """Test auto-detection of power connections."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "BAT1", "type": "battery"},
                {"reference": "IC1", "type": "ic"},
                {"reference": "IC2", "type": "microcontroller"},
            ]
        }

        connections = mapper.parse_circuit_connections(circuit_description)

        # Should detect power connections from battery to ICs
        power_connections = [c for c in connections if c["connection_type"] == "power"]
        ground_connections = [c for c in connections if c["connection_type"] == "ground"]

        assert len(power_connections) == 2  # BAT1 -> IC1, BAT1 -> IC2
        assert len(ground_connections) == 2  # BAT1 -> IC1, BAT1 -> IC2

        # Verify power connection details
        power_conn = power_connections[0]
        assert power_conn["net_name"] == "VCC"
        assert power_conn["source_component"] == "BAT1"
        assert power_conn["source_pin"] == "1"  # Battery positive

        # Verify ground connection details
        ground_conn = ground_connections[0]
        assert ground_conn["net_name"] == "GND"
        assert ground_conn["source_component"] == "BAT1"
        assert ground_conn["source_pin"] == "2"  # Battery negative

    def test_detect_led_circuits(self):
        """Test auto-detection of LED circuit patterns."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "R1", "type": "resistor"},
                {"reference": "R2", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
                {"reference": "LED2", "type": "led"},
            ]
        }

        connections = mapper.parse_circuit_connections(circuit_description)

        # Should detect LED circuit connections (resistor to LED)
        led_connections = [c for c in connections if "LED_NET" in c["net_name"]]

        assert len(led_connections) == 2  # R1 -> LED1, R2 -> LED2

        # Verify LED connection details
        led_conn = led_connections[0]
        assert led_conn["source_pin"] == "2"  # Resistor output
        assert led_conn["target_pin"] == "2"  # LED anode
        assert led_conn["connection_type"] == "signal"

    def test_detect_amplifier_circuits(self):
        """Test auto-detection of amplifier circuit patterns."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "CONN1", "type": "connector"},
                {"reference": "AMP1", "type": "amplifier"},
                {"reference": "SPK1", "type": "speaker"},
            ]
        }

        connections = mapper.parse_circuit_connections(circuit_description)

        # Should detect amplifier connections
        audio_connections = [c for c in connections if "AUDIO" in c["net_name"]]

        assert len(audio_connections) == 2  # Input -> Amp, Amp -> Output

        # Verify input connection
        input_conn = next(c for c in audio_connections if c["net_name"] == "AUDIO_IN")
        assert input_conn["source_component"] == "CONN1"
        assert input_conn["target_component"] == "AMP1"

        # Verify output connection
        output_conn = next(c for c in audio_connections if c["net_name"] == "AUDIO_OUT")
        assert output_conn["source_component"] == "AMP1"
        assert output_conn["target_component"] == "SPK1"

    def test_generate_connection_list(self):
        """Test generation of connection list tuples."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
            ],
            "connections": [
                {
                    "net": "LED_NET",
                    "from": {"component": "R1", "pin": "2"},
                    "to": {"component": "LED1", "pin": "2"},
                }
            ],
        }

        connection_list = mapper.generate_connection_list(circuit_description)

        assert len(connection_list) == 1
        conn_tuple = connection_list[0]
        assert conn_tuple == ("LED_NET", "R1", "2", "LED1", "2")

    def test_validate_circuit_connectivity_valid(self):
        """Test circuit connectivity validation for valid circuit."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "BAT1", "type": "battery"},
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
            ],
            "connections": [
                {"from": {"component": "R1", "pin": "2"}, "to": {"component": "LED1", "pin": "2"}}
            ],
        }

        validation = mapper.validate_circuit_connectivity(circuit_description)

        assert validation["is_valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["stats"]["total_components"] == 3
        assert validation["stats"]["connected_components"] == 2  # R1 and LED1

    def test_validate_circuit_connectivity_isolated_components(self):
        """Test detection of isolated components."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "R1", "type": "resistor"},
                {"reference": "R2", "type": "resistor"},  # Isolated
                {"reference": "LED1", "type": "led"},
            ],
            "connections": [
                {"from": {"component": "R1", "pin": "2"}, "to": {"component": "LED1", "pin": "2"}}
            ],
        }

        validation = mapper.validate_circuit_connectivity(circuit_description)

        assert len(validation["warnings"]) == 1
        assert "R2" in validation["warnings"][0]
        assert validation["stats"]["isolated_components"] == 1

    def test_validate_circuit_connectivity_missing_power(self):
        """Test detection of missing power connections."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "IC1", "type": "ic"}  # Requires power
            ]
        }

        validation = mapper.validate_circuit_connectivity(circuit_description)

        assert validation["is_valid"] is False
        assert any("power" in issue.lower() for issue in validation["issues"])
        assert any("ground" in issue.lower() for issue in validation["issues"])

    def test_power_pin_mappings(self):
        """Test power pin mapping for different component types."""
        mapper = ComponentPinMapper()

        # Test battery pins
        assert mapper._get_power_pin("battery", "positive") == "1"
        assert mapper._get_power_pin("battery", "negative") == "2"

        # Test IC pins
        assert mapper._get_power_pin("ic", "vcc") == "3"
        assert mapper._get_power_pin("ic", "gnd") == "4"

        # Test microcontroller pins
        assert mapper._get_power_pin("microcontroller", "vcc") == "VCC"
        assert mapper._get_power_pin("microcontroller", "gnd") == "GND"

        # Test unknown component
        assert mapper._get_power_pin("unknown", "vcc") == ""

    def test_connection_validation(self):
        """Test connection specification validation."""
        mapper = ComponentPinMapper()

        # Valid connection
        valid_conn = {
            "from": {"component": "R1", "pin": "1"},
            "to": {"component": "LED1", "pin": "2"},
        }
        assert mapper._is_valid_connection_spec(valid_conn) is True

        # Invalid connection - missing 'to'
        invalid_conn1 = {"from": {"component": "R1", "pin": "1"}}
        assert mapper._is_valid_connection_spec(invalid_conn1) is False

        # Invalid connection - missing component in 'from'
        invalid_conn2 = {"from": {"pin": "1"}, "to": {"component": "LED1", "pin": "2"}}
        assert mapper._is_valid_connection_spec(invalid_conn2) is False

    def test_complex_circuit_parsing(self):
        """Test parsing a complex circuit with multiple connection types."""
        mapper = ComponentPinMapper()

        circuit_description = {
            "components": [
                {"reference": "BAT1", "type": "battery"},
                {"reference": "IC1", "type": "ic"},
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
                {"reference": "CONN1", "type": "connector"},
            ],
            "connections": [
                {
                    "net": "CONTROL",
                    "from": {"component": "IC1", "pin": "1"},
                    "to": {"component": "R1", "pin": "1"},
                    "type": "signal",
                }
            ],
        }

        connections = mapper.parse_circuit_connections(circuit_description)

        # Should have explicit connection plus auto-detected power/ground/LED connections
        connection_types = {c["connection_type"] for c in connections}
        assert "signal" in connection_types  # Explicit connection
        assert "power" in connection_types  # Auto-detected power
        assert "ground" in connection_types  # Auto-detected ground

        # Should NOT auto-detect LED circuits since explicit connections exist
        led_connections = [c for c in connections if "LED_NET" in c["net_name"]]
        assert len(led_connections) == 0  # No auto-detection with explicit connections

    def test_empty_circuit_description(self):
        """Test handling of empty circuit descriptions."""
        mapper = ComponentPinMapper()

        # Empty description
        empty_circuit = {}
        connections = mapper.parse_circuit_connections(empty_circuit)
        assert len(connections) == 0

        # Description with empty components
        empty_components = {"components": []}
        connections = mapper.parse_circuit_connections(empty_components)
        assert len(connections) == 0

        # Validation of empty circuit
        validation = mapper.validate_circuit_connectivity(empty_circuit)
        assert validation["is_valid"] is True
        assert validation["stats"]["total_components"] == 0

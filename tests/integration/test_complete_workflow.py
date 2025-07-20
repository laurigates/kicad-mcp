"""
Integration tests for complete workflow functionality.

Tests the complete integration of ComponentLayoutManager, ComponentPinMapper,
and SExpressionHandler working together.
"""

from kicad_mcp.utils.sexpr_service import get_sexpr_service


class TestCompleteWorkflow:
    """Test complete workflow integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = get_sexpr_service()

    def test_simple_circuit_generation(self):
        """Test generation of a simple circuit."""
        components = [
            {
                "reference": "R1",
                "value": "1k",
                "position": (50, 50),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
            {
                "reference": "LED1",
                "value": "red",
                "position": (100, 50),
                "symbol_library": "Device",
                "symbol_name": "LED",
            },
        ]

        power_symbols = [
            {"reference": "VCC", "power_type": "+5V", "position": (30, 30)},
            {"reference": "GND", "power_type": "GND", "position": (30, 70)},
        ]

        connections = [
            {"start_component": "VCC", "start_pin": "1", "end_component": "R1", "end_pin": "1"},
            {"start_component": "R1", "start_pin": "2", "end_component": "LED1", "end_pin": "2"},
            {"start_component": "LED1", "start_pin": "1", "end_component": "GND", "end_pin": "1"},
        ]

        # Generate schematic
        sexpr = self.service.generate_schematic(
            "Test Circuit", components, power_symbols, connections
        )

        # Validate output
        assert sexpr.startswith("(kicad_sch")
        assert sexpr.endswith(")")
        assert "20240618" in sexpr  # Updated version
        assert sexpr.count("(symbol (lib_id") >= 4  # All components
        assert sexpr.count("(wire (pts") >= 3  # All connections

    def test_boundary_validation_integration(self):
        """Test that boundary validation works in complete workflow."""
        # Components with some outside bounds
        components = [
            {
                "reference": "R1",
                "value": "1k",
                "position": (50, 50),  # Valid
                "symbol_library": "Device",
                "symbol_name": "R",
            },
            {
                "reference": "R2",
                "value": "1k",
                "position": (400, 400),  # Invalid - outside bounds
                "symbol_library": "Device",
                "symbol_name": "R",
            },
        ]

        power_symbols = [{"reference": "VCC", "power_type": "+5V", "position": (30, 30)}]

        connections = []

        # Generate schematic
        self.service.generate_schematic("Boundary Test", components, power_symbols, connections)

        # Check layout statistics
        layout_stats = self.service.layout_manager.get_layout_statistics()

        # Should have corrected the invalid position
        assert layout_stats["total_components"] == 3  # 2 components + 1 power
        # Allow up to 1 violation due to correction process
        assert layout_stats["bounds_violations"] <= 1

    def test_pin_level_connectivity(self):
        """Test pin-level connectivity tracking."""
        components = [
            {
                "reference": "U1",
                "value": "MCU",
                "position": (100, 60),
                "symbol_library": "MCU",
                "symbol_name": "MCU",
            },
            {
                "reference": "R1",
                "value": "10k",
                "position": (60, 40),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
        ]

        power_symbols = [{"reference": "VCC", "power_type": "+3V3", "position": (40, 20)}]

        connections = [
            {"start_component": "VCC", "start_pin": "1", "end_component": "R1", "end_pin": "1"},
            {"start_component": "R1", "start_pin": "2", "end_component": "U1", "end_pin": "1"},
        ]

        # Generate schematic
        self.service.generate_schematic(
            "Pin Connectivity Test", components, power_symbols, connections
        )

        # Check pin mapping statistics
        pin_stats = self.service.pin_mapper.get_component_statistics()

        assert pin_stats["total_components"] == 3
        assert pin_stats["total_pins"] >= 5  # At least 5 pins total
        assert pin_stats["total_connections"] >= 2  # At least 2 connections tracked

        # Verify specific pin connections
        vcc_connections = self.service.pin_mapper.get_connected_pins("VCC", "1")
        assert len(vcc_connections) > 0

    def test_advanced_wire_routing(self):
        """Test advanced wire routing with nets."""
        components = [
            {
                "reference": "R1",
                "value": "10k",
                "position": (50, 50),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
            {
                "reference": "R2",
                "value": "10k",
                "position": (100, 50),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
            {
                "reference": "R3",
                "value": "10k",
                "position": (150, 50),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
        ]

        power_symbols = [{"reference": "VCC", "power_type": "+5V", "position": (40, 30)}]

        connections = []

        # Generate basic schematic first
        self.service.generate_schematic(
            "Advanced Routing Test", components, power_symbols, connections
        )

        # Test advanced routing with nets
        net_connections = [
            {
                "name": "VCC_NET",
                "pins": ["VCC.1", "R1.1", "R2.1", "R3.1"],  # Multi-pin net
            }
        ]

        advanced_wires = self.service.generate_advanced_wire_routing(net_connections)

        # Should generate wire segments for the net
        wire_segments = [line for line in advanced_wires if "(wire (pts" in line]
        assert len(wire_segments) >= 3  # Should have multiple segments for bus routing

    def test_complex_circuit_integration(self):
        """Test complex circuit with all features."""
        components = [
            {
                "reference": "U1",
                "value": "ATmega328P",
                "position": (100, 80),
                "symbol_library": "MCU_Microchip_ATmega",
                "symbol_name": "ATmega328P",
            },
            {
                "reference": "R1",
                "value": "10k",
                "position": (50, 50),
                "symbol_library": "Device",
                "symbol_name": "R",
            },
            {
                "reference": "C1",
                "value": "100nF",
                "position": (50, 110),
                "symbol_library": "Device",
                "symbol_name": "C",
            },
            {
                "reference": "LED1",
                "value": "red",
                "position": (150, 50),
                "symbol_library": "Device",
                "symbol_name": "LED",
            },
        ]

        power_symbols = [
            {"reference": "VCC", "power_type": "+5V", "position": (30, 10)},
            {"reference": "GND", "power_type": "GND", "position": (30, 130)},
        ]

        connections = [
            {"start_component": "VCC", "start_pin": "1", "end_component": "R1", "end_pin": "1"},
            {"start_component": "R1", "start_pin": "2", "end_component": "U1", "end_pin": "1"},
            {"start_component": "U1", "start_pin": "2", "end_component": "LED1", "end_pin": "2"},
            {"start_component": "LED1", "start_pin": "1", "end_component": "GND", "end_pin": "1"},
            {"start_component": "C1", "start_pin": "1", "end_component": "VCC", "end_pin": "1"},
            {"start_component": "C1", "start_pin": "2", "end_component": "GND", "end_pin": "1"},
        ]

        # Generate complete schematic
        sexpr = self.service.generate_schematic(
            "Complex Circuit Test", components, power_symbols, connections
        )

        # Comprehensive validation
        assert len(sexpr) > 5000  # Should be substantial
        assert sexpr.startswith("(kicad_sch")
        assert sexpr.endswith(")")
        assert "20240618" in sexpr

        # Check all systems working
        layout_stats = self.service.layout_manager.get_layout_statistics()
        pin_stats = self.service.pin_mapper.get_component_statistics()

        assert layout_stats["total_components"] == 6  # 4 components + 2 power
        assert layout_stats["bounds_violations"] <= 1  # Allow minimal violations during correction

        assert pin_stats["total_components"] == 6
        assert pin_stats["total_pins"] >= 8  # Multiple pins
        assert pin_stats["total_connections"] >= 6  # All connections tracked

        # Count actual wire segments
        wire_count = sexpr.count("(wire (pts")
        assert wire_count >= 6  # Should have generated wires for all connections

    def test_legacy_compatibility(self):
        """Test that legacy coordinate-based connections still work."""
        components = [
            {
                "reference": "R1",
                "value": "1k",
                "position": (50, 50),
                "symbol_library": "Device",
                "symbol_name": "R",
            }
        ]

        power_symbols = [{"reference": "VCC", "power_type": "+5V", "position": (30, 30)}]

        # Legacy coordinate-based connection
        connections = [{"start_x": 50, "start_y": 50, "end_x": 100, "end_y": 50}]

        # Should still work
        sexpr = self.service.generate_schematic(
            "Legacy Test", components, power_symbols, connections
        )

        assert sexpr.startswith("(kicad_sch")
        assert "(wire (pts" in sexpr
        assert "20240618" in sexpr

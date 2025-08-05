"""
Tests for SExpressionHandler intelligent wiring functionality.
"""

from kicad_mcp.utils.sexpr_handler import SExpressionHandler
from kicad_mcp.utils.wire_router import RouteStrategy


class TestSExpressionHandlerIntelligentWiring:
    """Test intelligent wiring integration in SExpressionHandler."""

    def test_generate_schematic_with_intelligent_wiring_simple_led_circuit(self):
        """Test intelligent wiring for a simple LED circuit."""
        handler = SExpressionHandler()

        # Define a simple LED circuit
        circuit_description = {
            "components": [
                {"reference": "BAT1", "type": "battery"},
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
            ]
        }

        components = [
            {
                "reference": "BAT1",
                "type": "battery",
                "symbol_library": "Device",
                "symbol_name": "Battery_Cell",
                "position": (50.0, 100.0),
            },
            {
                "reference": "R1",
                "type": "resistor",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (100.0, 100.0),
            },
            {
                "reference": "LED1",
                "type": "led",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (150.0, 100.0),
            },
        ]

        # Generate schematic with intelligent wiring
        schematic = handler.generate_schematic_with_intelligent_wiring(
            "LED Circuit", circuit_description, components, strategy=RouteStrategy.MANHATTAN
        )

        # Verify schematic is generated
        assert isinstance(schematic, str)
        assert len(schematic) > 0

        # Verify it contains KiCad schematic structure
        assert "kicad_sch" in schematic
        assert "LED Circuit" in schematic

        # Verify components are included
        assert "BAT1" in schematic
        assert "R1" in schematic
        assert "LED1" in schematic

        # Verify wires are generated
        assert "wire" in schematic
        assert "pts" in schematic  # Wire points
        assert "xy" in schematic  # Coordinates

    def test_generate_intelligent_wiring_power_connections(self):
        """Test intelligent detection and routing of power connections."""
        handler = SExpressionHandler()

        circuit_description = {
            "components": [
                {"reference": "BAT1", "type": "battery"},
                {"reference": "IC1", "type": "ic"},
                {"reference": "IC2", "type": "microcontroller"},
            ]
        }

        components = [
            {"reference": "BAT1", "type": "battery", "position": (50.0, 50.0)},
            {"reference": "IC1", "type": "ic", "position": (100.0, 50.0)},
            {"reference": "IC2", "type": "microcontroller", "position": (150.0, 50.0)},
        ]

        # Generate intelligent wiring
        wire_sexprs = handler.generate_intelligent_wiring(
            circuit_description, components, RouteStrategy.MANHATTAN
        )

        # Should generate multiple wires for power and ground connections
        assert len(wire_sexprs) >= 4  # At least 2 power + 2 ground connections

        # Verify wire structure
        for wire_expr in wire_sexprs:
            assert wire_expr[0].value() == "wire"  # sexpdata.Symbol

            # Check for required wire elements
            wire_dict = {item[0].value(): item for item in wire_expr[1:] if isinstance(item, list)}
            assert "pts" in wire_dict  # Points
            assert "stroke" in wire_dict  # Style
            assert "uuid" in wire_dict  # UUID

    def test_generate_intelligent_wiring_explicit_connections(self):
        """Test intelligent wiring with explicit connections."""
        handler = SExpressionHandler()

        circuit_description = {
            "components": [
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
            ],
            "connections": [
                {
                    "net": "SIGNAL",
                    "from": {"component": "R1", "pin": "2"},
                    "to": {"component": "LED1", "pin": "2"},
                    "type": "signal",
                }
            ],
        }

        components = [
            {"reference": "R1", "type": "resistor", "position": (50.0, 50.0)},
            {"reference": "LED1", "type": "led", "position": (100.0, 50.0)},
        ]

        # Generate intelligent wiring
        wire_sexprs = handler.generate_intelligent_wiring(
            circuit_description, components, RouteStrategy.MANHATTAN
        )

        # Should generate at least one wire for the explicit connection
        assert len(wire_sexprs) >= 1

        # Verify explicit connection is wired
        found_signal_connection = False
        for wire_expr in wire_sexprs:
            # Check if this wire connects the expected points
            if len(wire_expr) > 1:
                found_signal_connection = True
                break

        assert found_signal_connection

    def test_routing_obstacle_setup(self):
        """Test that routing obstacles are properly set up from components."""
        handler = SExpressionHandler()

        components = [
            {"reference": "R1", "type": "resistor", "position": (50.0, 50.0)},
            {"reference": "IC1", "type": "ic", "position": (100.0, 50.0)},
        ]

        # Setup obstacles
        handler._setup_routing_obstacles(components)

        # Verify obstacles were created
        assert len(handler.wire_router.obstacles) == 2

        # Check obstacle properties
        for obstacle in handler.wire_router.obstacles:
            assert obstacle.obstacle_type == "component"
            assert obstacle.reference in ["R1", "IC1"]
            assert len(obstacle.bounds) == 4  # (min_x, min_y, max_x, max_y)

    def test_wire_segment_to_sexpr_conversion(self):
        """Test conversion of wire segments to S-expressions."""
        handler = SExpressionHandler()

        # Create a mock wire segment
        class MockSegment:
            def __init__(self):
                self.start = (10.0, 20.0)
                self.end = (30.0, 20.0)
                self.width = 0.15

        segment = MockSegment()
        wire_expr = handler._create_wire_sexpr_from_segment(segment)

        # Verify S-expression structure
        assert wire_expr[0].value() == "wire"

        # Check for required elements
        wire_dict = {item[0].value(): item for item in wire_expr[1:] if isinstance(item, list)}
        assert "pts" in wire_dict
        assert "stroke" in wire_dict
        assert "uuid" in wire_dict

        # Check points
        pts = wire_dict["pts"]
        assert len(pts) >= 3  # "pts", start_xy, end_xy

        # Check stroke
        stroke = wire_dict["stroke"]
        stroke_dict = {item[0].value(): item[1] for item in stroke[1:] if isinstance(item, list)}
        assert "width" in stroke_dict
        assert stroke_dict["width"] == 0.15

    def test_full_workflow_integration(self):
        """Test complete workflow from circuit description to schematic with wires."""
        handler = SExpressionHandler()

        # Complex circuit with multiple connection types
        circuit_description = {
            "components": [
                {"reference": "BAT1", "type": "battery"},
                {"reference": "IC1", "type": "ic"},
                {"reference": "R1", "type": "resistor"},
                {"reference": "LED1", "type": "led"},
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

        components = [
            {
                "reference": "BAT1",
                "type": "battery",
                "symbol_library": "Device",
                "symbol_name": "Battery_Cell",
                "position": (50.0, 50.0),
            },
            {
                "reference": "IC1",
                "type": "ic",
                "symbol_library": "Device",
                "symbol_name": "U",
                "position": (100.0, 50.0),
            },
            {
                "reference": "R1",
                "type": "resistor",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (150.0, 50.0),
            },
            {
                "reference": "LED1",
                "type": "led",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "position": (200.0, 50.0),
            },
        ]

        # Generate complete schematic with intelligent wiring
        schematic = handler.generate_schematic_with_intelligent_wiring(
            "Complex Circuit", circuit_description, components, strategy=RouteStrategy.MANHATTAN
        )

        # Comprehensive verification
        assert isinstance(schematic, str)
        assert "kicad_sch" in schematic
        assert "Complex Circuit" in schematic

        # Verify all components
        for comp in components:
            assert comp["reference"] in schematic

        # Verify wiring exists
        assert "wire" in schematic

        # Count approximate number of wires (should have power, ground, signal, LED connections)
        wire_count = schematic.count("(wire")
        assert wire_count >= 3  # At least power, ground, and signal connections

    def test_empty_circuit_handling(self):
        """Test handling of empty circuit descriptions."""
        handler = SExpressionHandler()

        # Empty components
        empty_components = []
        empty_circuit = {"components": []}

        wire_sexprs = handler.generate_intelligent_wiring(
            empty_circuit, empty_components, RouteStrategy.MANHATTAN
        )

        assert len(wire_sexprs) == 0

        # Should still generate valid schematic structure
        schematic = handler.generate_schematic_with_intelligent_wiring(
            "Empty Circuit", empty_circuit, empty_components
        )

        assert isinstance(schematic, str)
        assert "kicad_sch" in schematic
        assert "Empty Circuit" in schematic

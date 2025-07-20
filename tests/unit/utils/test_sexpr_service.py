"""
Tests for the S-expression service.

This module tests the simplified S-expression service that uses
SExpressionHandler for all operations.
"""

from kicad_mcp.utils.sexpr_service import (
    SExpressionService,
    get_sexpr_service,
    reset_sexpr_service,
)


class TestSExpressionService:
    """Test suite for SExpressionService class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global service for clean tests
        reset_sexpr_service()

        # Sample test data
        self.sample_components = [
            {
                "reference": "R1",
                "value": "10k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (63.5, 87.63),
            }
        ]
        self.sample_power_symbols = [
            {
                "reference": "#PWR001",
                "power_type": "VCC",
                "position": (50.0, 50.0),
            }
        ]
        self.sample_connections = [
            {
                "start_component": "R1",
                "start_pin": "1",
                "end_component": "#PWR001",
                "end_pin": "1",
            }
        ]

    def test_service_initialization(self):
        """Test that the service initializes correctly."""
        service = SExpressionService()
        assert service.handler is not None
        assert service.logger is not None

    def test_generate_schematic_basic(self):
        """Test basic schematic generation."""
        service = SExpressionService()

        result = service.generate_schematic(
            circuit_name="Test Circuit",
            components=self.sample_components,
            power_symbols=self.sample_power_symbols,
            connections=self.sample_connections,
        )

        assert isinstance(result, str)
        assert "kicad_sch" in result
        assert "Test Circuit" in result
        assert "R1" in result
        assert "10k" in result

    def test_generate_schematic_pretty_print(self):
        """Test schematic generation with pretty printing."""
        service = SExpressionService()

        result = service.generate_schematic(
            circuit_name="Test Circuit",
            components=self.sample_components,
            power_symbols=self.sample_power_symbols,
            connections=self.sample_connections,
            pretty_print=True,
        )

        assert isinstance(result, str)
        assert "kicad_sch" in result

    def test_parse_schematic(self):
        """Test schematic parsing functionality."""
        service = SExpressionService()

        # Generate a schematic first
        sexpr_content = service.generate_schematic(
            circuit_name="Test Circuit",
            components=self.sample_components,
            power_symbols=self.sample_power_symbols,
            connections=self.sample_connections,
        )

        # Then parse it
        parsed = service.parse_schematic(sexpr_content)

        assert isinstance(parsed, dict)
        assert "type" in parsed
        assert parsed["type"] == "kicad_sch"

    def test_layout_manager_access(self):
        """Test access to layout manager."""
        service = SExpressionService()
        layout_manager = service.layout_manager

        assert layout_manager is not None
        assert hasattr(layout_manager, "place_component")

    def test_pin_mapper_access(self):
        """Test access to pin mapper."""
        service = SExpressionService()
        pin_mapper = service.pin_mapper

        assert pin_mapper is not None
        assert hasattr(pin_mapper, "add_component")

    def test_global_service_instance(self):
        """Test global service instance management."""
        # Reset to ensure clean state
        reset_sexpr_service()

        # Get service instances
        service1 = get_sexpr_service()
        service2 = get_sexpr_service()

        # Should be the same instance
        assert service1 is service2

        # Reset and get new instance
        reset_sexpr_service()
        service3 = get_sexpr_service()

        # Should be different from the first ones
        assert service3 is not service1

    def test_generate_advanced_wire_routing(self):
        """Test advanced wire routing functionality."""
        service = SExpressionService()

        net_connections = [
            {
                "name": "VCC",
                "pins": ["R1.1", "#PWR001.1"],
            }
        ]

        result = service.generate_advanced_wire_routing(net_connections)

        assert isinstance(result, list)

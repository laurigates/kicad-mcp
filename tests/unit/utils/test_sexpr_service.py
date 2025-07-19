"""
Unit tests for SExpressionService with feature flags and migration support.

Tests the unified S-expression service that provides feature flag control,
fallback mechanisms, and gradual rollout capabilities.
"""

import os
from unittest.mock import patch

import pytest

from kicad_mcp.utils.sexpr_service import (
    SExpressionService,
    SExprImplementation,
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
        self.sample_component = {
            "reference": "R1",
            "value": "10k",
            "symbol_library": "Device",
            "symbol_name": "R",
            "position": (63.5, 87.63),
        }

        self.sample_power_symbol = {
            "reference": "#PWR001",
            "power_type": "VCC",
            "position": (63.5, 80.0),
        }

        self.sample_connection = {"start_x": 63.5, "start_y": 91.44, "end_x": 63.5, "end_y": 96.52}

    def test_service_initialization_default(self):
        """Test service initialization with default configuration."""
        service = SExpressionService()

        assert service.primary_implementation == SExprImplementation.GENERATOR
        assert not service.enable_handler
        assert service.enable_fallback
        assert not service.enable_comparison
        assert not service.enable_performance_logging
        assert service.rollout_percentage == 0
        assert not service.validate_output
        assert not service.strict_validation

    @patch.dict(
        os.environ,
        {
            "KICAD_MCP_SEXPR_IMPLEMENTATION": "handler",
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
            "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "false",
            "KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": "50",
            "KICAD_MCP_ENABLE_SEXPR_COMPARISON": "true",
            "KICAD_MCP_ENABLE_PERFORMANCE_LOGGING": "true",
            "KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true",
            "KICAD_MCP_STRICT_SEXPR_VALIDATION": "true",
        },
    )
    def test_service_initialization_with_env_vars(self):
        """Test service initialization with environment variable configuration."""
        service = SExpressionService()

        assert service.primary_implementation == SExprImplementation.HANDLER
        assert service.enable_handler
        assert not service.enable_fallback
        assert service.rollout_percentage == 50
        assert service.enable_comparison
        assert service.enable_performance_logging
        assert service.validate_output
        assert service.strict_validation

    @patch.dict(os.environ, {"KICAD_MCP_SEXPR_IMPLEMENTATION": "invalid"})
    def test_service_initialization_invalid_implementation(self):
        """Test service initialization with invalid implementation."""
        service = SExpressionService()
        assert service.primary_implementation == SExprImplementation.GENERATOR

    def test_generate_schematic_with_generator(self):
        """Test schematic generation using the generator implementation."""
        service = SExpressionService()

        result = service.generate_schematic(
            "Test Circuit",
            [self.sample_component],
            [self.sample_power_symbol],
            [self.sample_connection],
        )

        assert isinstance(result, str)
        assert "kicad_sch" in result
        assert "Test Circuit" in result
        assert "R1" in result
        assert "#PWR001" in result

    @patch.dict(
        os.environ,
        {"KICAD_MCP_SEXPR_IMPLEMENTATION": "handler", "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true"},
    )
    def test_generate_schematic_with_handler(self):
        """Test schematic generation using the handler implementation."""
        service = SExpressionService()

        result = service.generate_schematic(
            "Test Circuit",
            [self.sample_component],
            [self.sample_power_symbol],
            [self.sample_connection],
        )

        assert isinstance(result, str)
        assert "kicad_sch" in result
        assert "Test Circuit" in result
        assert "R1" in result
        assert "#PWR001" in result

    def test_force_implementation_override(self):
        """Test forcing a specific implementation."""
        service = SExpressionService()

        # Force handler implementation even though default is generator
        result = service.generate_schematic(
            "Test Circuit",
            [self.sample_component],
            [],
            [],
            force_implementation=SExprImplementation.HANDLER,
        )

        assert isinstance(result, str)
        assert "kicad_sch" in result

    @patch.dict(
        os.environ,
        {"KICAD_MCP_ENABLE_SEXPR_HANDLER": "true", "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "true"},
    )
    def test_fallback_mechanism(self):
        """Test fallback from handler to generator on error."""
        service = SExpressionService()

        # Mock handler to raise an exception
        with patch.object(
            service.handler, "generate_schematic", side_effect=Exception("Handler error")
        ):
            result = service.generate_schematic(
                "Test Circuit",
                [self.sample_component],
                [],
                [],
                force_implementation=SExprImplementation.HANDLER,
            )

            # Should still get a result from fallback
            assert isinstance(result, str)
            assert "kicad_sch" in result
            assert service.performance_stats["fallbacks"] == 1

    @patch.dict(
        os.environ,
        {"KICAD_MCP_ENABLE_SEXPR_HANDLER": "true", "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "false"},
    )
    def test_no_fallback_on_error(self):
        """Test behavior when fallback is disabled."""
        service = SExpressionService()

        # Mock handler to raise an exception
        with patch.object(
            service.handler, "generate_schematic", side_effect=Exception("Handler error")
        ):
            with pytest.raises(Exception, match="Handler error"):
                service.generate_schematic(
                    "Test Circuit",
                    [self.sample_component],
                    [],
                    [],
                    force_implementation=SExprImplementation.HANDLER,
                )

    @patch.dict(
        os.environ,
        {
            "KICAD_MCP_SEXPR_IMPLEMENTATION": "auto",
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
            "KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": "100",
        },
    )
    def test_auto_implementation_selection_100_percent(self):
        """Test automatic implementation selection with 100% rollout."""
        service = SExpressionService()

        # Should select handler with 100% rollout
        selected = service._select_implementation()
        assert selected == SExprImplementation.HANDLER

    @patch.dict(
        os.environ,
        {
            "KICAD_MCP_SEXPR_IMPLEMENTATION": "auto",
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
            "KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": "0",
        },
    )
    def test_auto_implementation_selection_0_percent(self):
        """Test automatic implementation selection with 0% rollout."""
        service = SExpressionService()

        # Should select generator with 0% rollout
        selected = service._select_implementation()
        assert selected == SExprImplementation.GENERATOR

    @patch.dict(
        os.environ,
        {"KICAD_MCP_SEXPR_IMPLEMENTATION": "handler", "KICAD_MCP_ENABLE_SEXPR_HANDLER": "false"},
    )
    def test_handler_requested_but_disabled(self):
        """Test behavior when handler is requested but disabled."""
        service = SExpressionService()

        # Should fall back to generator
        selected = service._select_implementation()
        assert selected == SExprImplementation.GENERATOR

    @patch.dict(os.environ, {"KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true"})
    def test_output_validation_success(self):
        """Test successful output validation."""
        service = SExpressionService()

        result = service.generate_schematic("Test Circuit", [self.sample_component], [], [])

        # Should not raise any validation errors
        assert isinstance(result, str)
        assert "kicad_sch" in result

    @patch.dict(
        os.environ,
        {"KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true", "KICAD_MCP_STRICT_SEXPR_VALIDATION": "true"},
    )
    def test_strict_validation_success(self):
        """Test successful strict validation."""
        service = SExpressionService()

        result = service.generate_schematic("Test Circuit", [self.sample_component], [], [])

        # Should pass strict validation
        assert isinstance(result, str)
        assert "kicad_sch" in result

    @patch.dict(os.environ, {"KICAD_MCP_ENABLE_PERFORMANCE_LOGGING": "true"})
    def test_performance_tracking(self):
        """Test performance statistics tracking."""
        service = SExpressionService()

        # Generate a few schematics
        for i in range(3):
            service.generate_schematic(f"Test Circuit {i}", [], [], [])

        stats = service.get_performance_stats()

        assert stats["generator"]["count"] == 3
        assert stats["generator"]["total_time"] > 0
        assert stats["generator"]["avg_time"] > 0
        assert stats["generator"]["error_rate"] == 0
        assert stats["handler"]["count"] == 0  # Should be 0 since using generator

    @patch.dict(os.environ, {"KICAD_MCP_ENABLE_SEXPR_COMPARISON": "true"})
    def test_implementation_comparison(self):
        """Test A/B comparison between implementations."""
        service = SExpressionService()

        # Mock the comparison method to avoid issues
        with patch.object(service, "_compare_implementations") as mock_compare:
            service.generate_schematic("Test Circuit", [self.sample_component], [], [])

            # Should have called comparison
            mock_compare.assert_called_once()

    def test_parse_schematic(self):
        """Test schematic parsing functionality."""
        service = SExpressionService()

        # Generate a schematic first
        schematic = service.generate_schematic("Test Circuit", [self.sample_component], [], [])

        # Parse it back
        parsed = service.parse_schematic(schematic)

        assert isinstance(parsed, dict)
        assert "version" in parsed
        assert "generator" in parsed
        assert "uuid" in parsed

    def test_get_config_info(self):
        """Test configuration information retrieval."""
        service = SExpressionService()

        config = service.get_config_info()

        assert "primary_implementation" in config
        assert "handler_enabled" in config
        assert "fallback_enabled" in config
        assert "rollout_percentage" in config
        assert config["primary_implementation"] == "generator"

    def test_uuid_removal_for_comparison(self):
        """Test UUID removal functionality for output comparison."""
        service = SExpressionService()

        # Test structure with UUIDs
        test_structure = [
            "kicad_sch",
            ["uuid", "12345-67890"],
            ["version", 20240618],
            ["symbol", ["uuid", "abcdef"], ["property", "Reference", "R1"]],
        ]

        cleaned = service._remove_uuids(test_structure)

        # UUIDs should be removed
        assert "12345-67890" not in str(cleaned)
        assert "abcdef" not in str(cleaned)
        assert "kicad_sch" in str(cleaned)
        assert "Reference" in str(cleaned)

    def test_structures_equal(self):
        """Test structure equality comparison."""
        service = SExpressionService()

        struct1 = ["kicad_sch", ["version", 20240618], ["title", "Test"]]
        struct2 = ["kicad_sch", ["version", 20240618], ["title", "Test"]]
        struct3 = ["kicad_sch", ["version", 20240618], ["title", "Different"]]

        assert service._structures_equal(struct1, struct2)
        assert not service._structures_equal(struct1, struct3)

    def test_rollout_percentage_logic(self):
        """Test rollout percentage logic."""
        service = SExpressionService()

        # Test 0% rollout
        service.rollout_percentage = 0
        assert not service._should_use_rollout()

        # Test 100% rollout
        service.rollout_percentage = 100
        assert service._should_use_rollout()


class TestSExpressionServiceGlobal:
    """Test global service instance management."""

    def setup_method(self):
        """Reset global service for clean tests."""
        reset_sexpr_service()

    def test_get_global_service_singleton(self):
        """Test that get_sexpr_service returns the same instance."""
        service1 = get_sexpr_service()
        service2 = get_sexpr_service()

        assert service1 is service2
        assert isinstance(service1, SExpressionService)

    def test_reset_global_service(self):
        """Test resetting the global service instance."""
        service1 = get_sexpr_service()
        reset_sexpr_service()
        service2 = get_sexpr_service()

        assert service1 is not service2
        assert isinstance(service2, SExpressionService)


class TestSExpressionServiceIntegration:
    """Integration tests for SExpressionService."""

    def setup_method(self):
        """Reset global service for clean tests."""
        reset_sexpr_service()

    @patch.dict(
        os.environ,
        {
            "KICAD_MCP_SEXPR_IMPLEMENTATION": "handler",
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
            "KICAD_MCP_ENABLE_SEXPR_COMPARISON": "true",
            "KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true",
            "KICAD_MCP_ENABLE_PERFORMANCE_LOGGING": "true",
        },
    )
    def test_full_feature_integration(self):
        """Test service with all features enabled."""
        service = SExpressionService()

        components = [
            {
                "reference": "R1",
                "value": "1k",
                "symbol_library": "Device",
                "symbol_name": "R",
                "position": (10, 10),
            },
            {
                "reference": "C1",
                "value": "10uF",
                "symbol_library": "Device",
                "symbol_name": "C",
                "position": (20, 10),
            },
        ]

        power_symbols = [
            {"reference": "#PWR001", "power_type": "VCC", "position": (10, 20)},
            {"reference": "#PWR002", "power_type": "GND", "position": (20, 20)},
        ]

        connections = [{"start_x": 10, "start_y": 15, "end_x": 20, "end_y": 15}]

        result = service.generate_schematic(
            "Integration Test Circuit", components, power_symbols, connections
        )

        # Should generate valid output
        assert isinstance(result, str)
        assert "kicad_sch" in result
        assert "Integration Test Circuit" in result

        # Should have performance stats
        stats = service.get_performance_stats()
        assert stats["handler"]["count"] == 1

        # Should be able to parse the result
        parsed = service.parse_schematic(result)
        assert isinstance(parsed, dict)
        assert "version" in parsed

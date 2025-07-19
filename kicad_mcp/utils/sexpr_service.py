"""
S-expression service with feature flag support for gradual migration.

This service provides a unified interface for S-expression generation with
feature flags to control which implementation is used (SExpressionGenerator
vs SExpressionHandler) and fallback mechanisms for safe deployment.
"""

from enum import Enum
import logging
import os
from typing import Any

from kicad_mcp.utils.sexpr_generator import SExpressionGenerator
from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class SExprImplementation(Enum):
    """Available S-expression implementations."""

    GENERATOR = "generator"  # Original string-based implementation
    HANDLER = "handler"  # New sexpdata-based implementation
    AUTO = "auto"  # Automatic selection based on configuration


class SExpressionService:
    """
    Unified S-expression service with feature flags and fallback support.

    This service manages the transition between the original SExpressionGenerator
    and the new SExpressionHandler, providing:
    - Feature flag control via environment variables
    - Graceful fallback on errors
    - Performance monitoring and comparison
    - Gradual rollout capabilities
    """

    def __init__(self):
        """Initialize the S-expression service."""
        self.logger = logging.getLogger(__name__)

        # Initialize both implementations
        self.generator = SExpressionGenerator()
        self.handler = SExpressionHandler()

        # Load configuration
        self._load_config()

        # Performance tracking
        self.performance_stats = {
            "generator": {"count": 0, "total_time": 0.0, "errors": 0},
            "handler": {"count": 0, "total_time": 0.0, "errors": 0},
            "fallbacks": 0,
        }

    def _load_config(self):
        """Load feature flag configuration from environment variables."""
        # Primary feature flag - which implementation to use
        impl_str = os.environ.get("KICAD_MCP_SEXPR_IMPLEMENTATION", "generator").lower()
        try:
            self.primary_implementation = SExprImplementation(impl_str)
        except ValueError:
            self.logger.warning(
                f"Invalid SEXPR implementation '{impl_str}', defaulting to generator"
            )
            self.primary_implementation = SExprImplementation.GENERATOR

        # Feature flags
        self.enable_handler = (
            os.environ.get("KICAD_MCP_ENABLE_SEXPR_HANDLER", "false").lower() == "true"
        )
        self.enable_fallback = (
            os.environ.get("KICAD_MCP_ENABLE_SEXPR_FALLBACK", "true").lower() == "true"
        )
        self.enable_comparison = (
            os.environ.get("KICAD_MCP_ENABLE_SEXPR_COMPARISON", "false").lower() == "true"
        )
        self.enable_performance_logging = (
            os.environ.get("KICAD_MCP_ENABLE_PERFORMANCE_LOGGING", "false").lower() == "true"
        )

        # Rollout percentage (0-100) for gradual deployment
        self.rollout_percentage = int(os.environ.get("KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE", "0"))

        # Validation settings
        self.validate_output = (
            os.environ.get("KICAD_MCP_VALIDATE_SEXPR_OUTPUT", "false").lower() == "true"
        )
        self.strict_validation = (
            os.environ.get("KICAD_MCP_STRICT_SEXPR_VALIDATION", "false").lower() == "true"
        )

        self.logger.info(
            f"S-expression service configured: implementation={self.primary_implementation.value}, "
            f"handler_enabled={self.enable_handler}, fallback_enabled={self.enable_fallback}, "
            f"rollout_percentage={self.rollout_percentage}%"
        )

    def generate_schematic(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
        pretty_print: bool = True,
        force_implementation: SExprImplementation | None = None,
    ) -> str:
        """
        Generate a KiCad schematic S-expression.

        Args:
            circuit_name: Name of the circuit
            components: List of component dictionaries
            power_symbols: List of power symbol dictionaries
            connections: List of connection dictionaries
            pretty_print: Whether to format output for readability (handler only)
            force_implementation: Force specific implementation for testing

        Returns:
            S-expression formatted schematic as string

        Raises:
            ValueError: If generation fails and fallback is disabled
        """
        import time

        # Determine which implementation to use
        implementation = force_implementation or self._select_implementation()

        start_time = time.time()

        try:
            if implementation == SExprImplementation.HANDLER:
                result = self._generate_with_handler(
                    circuit_name, components, power_symbols, connections, pretty_print
                )
                self._record_performance("handler", time.time() - start_time, True)
            else:
                result = self._generate_with_generator(
                    circuit_name, components, power_symbols, connections
                )
                self._record_performance("generator", time.time() - start_time, True)

            # Optional output validation
            if self.validate_output:
                self._validate_output(result, implementation)

            # Optional comparison for testing
            if self.enable_comparison and not force_implementation:
                self._compare_implementations(circuit_name, components, power_symbols, connections)

            return result

        except Exception as e:
            self.logger.error(f"S-expression generation failed with {implementation.value}: {e}")

            if implementation == SExprImplementation.HANDLER:
                self._record_performance("handler", time.time() - start_time, False)
            else:
                self._record_performance("generator", time.time() - start_time, False)

            # Attempt fallback if enabled
            if self.enable_fallback and implementation != SExprImplementation.GENERATOR:
                return self._fallback_to_generator(
                    circuit_name, components, power_symbols, connections
                )

            raise

    def _select_implementation(self) -> SExprImplementation:
        """Select which implementation to use based on configuration."""
        if self.primary_implementation == SExprImplementation.AUTO:
            # Auto-selection logic based on feature flags and rollout
            if self.enable_handler and self._should_use_rollout():
                return SExprImplementation.HANDLER
            return SExprImplementation.GENERATOR
        elif self.primary_implementation == SExprImplementation.HANDLER:
            if self.enable_handler:
                return SExprImplementation.HANDLER
            else:
                self.logger.warning("Handler requested but not enabled, falling back to generator")
                return SExprImplementation.GENERATOR
        else:
            return SExprImplementation.GENERATOR

    def _should_use_rollout(self) -> bool:
        """Determine if this request should use the new implementation based on rollout percentage."""
        if self.rollout_percentage <= 0:
            return False
        if self.rollout_percentage >= 100:
            return True

        # Use deterministic rollout based on process ID and time
        import os
        import time

        seed = hash(f"{os.getpid()}{int(time.time() / 3600)}")  # Changes hourly
        return (seed % 100) < self.rollout_percentage

    def _generate_with_handler(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
        pretty_print: bool,
    ) -> str:
        """Generate using the new SExpressionHandler."""
        return self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print
        )

    def _generate_with_generator(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
    ) -> str:
        """Generate using the original SExpressionGenerator."""
        return self.generator.generate_schematic(
            circuit_name, components, power_symbols, connections
        )

    def _fallback_to_generator(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
    ) -> str:
        """Fallback to the original generator implementation."""
        import time

        self.performance_stats["fallbacks"] += 1
        self.logger.warning("Falling back to SExpressionGenerator due to handler failure")

        try:
            start_time = time.time()
            result = self._generate_with_generator(
                circuit_name, components, power_symbols, connections
            )
            self._record_performance("generator", time.time() - start_time, True)
            return result
        except Exception as e:
            self.logger.error(f"Fallback to generator also failed: {e}")
            raise ValueError(
                f"Both S-expression implementations failed. Handler error was handled, generator error: {e}"
            ) from e

    def _validate_output(self, output: str, implementation: SExprImplementation):
        """Validate the generated S-expression output."""
        try:
            import sexpdata

            parsed = sexpdata.loads(output)

            # Basic structure validation
            if not isinstance(parsed, list) or len(parsed) == 0:
                raise ValueError("Invalid S-expression structure")

            if str(parsed[0]) != "kicad_sch":
                raise ValueError("Not a valid KiCad schematic S-expression")

            # Additional validation for strict mode
            if self.strict_validation:
                required_elements = [
                    "version",
                    "generator",
                    "uuid",
                    "paper",
                    "title_block",
                    "sheet_instances",
                ]
                elements = [
                    str(item[0]) if isinstance(item, list) else str(item) for item in parsed[1:]
                ]

                for required in required_elements:
                    if required not in elements:
                        raise ValueError(f"Missing required element: {required}")

            self.logger.debug(f"Output validation passed for {implementation.value}")

        except Exception as e:
            self.logger.error(f"Output validation failed for {implementation.value}: {e}")
            if self.strict_validation:
                raise

    def _compare_implementations(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
    ):
        """Compare outputs from both implementations for testing."""
        try:
            import sexpdata

            # Generate with both implementations
            generator_output = self._generate_with_generator(
                circuit_name, components, power_symbols, connections
            )
            handler_output = self._generate_with_handler(
                circuit_name, components, power_symbols, connections, False
            )

            # Parse and compare structures (ignoring UUIDs)
            generator_parsed = sexpdata.loads(generator_output)
            handler_parsed = sexpdata.loads(handler_output)

            # Remove UUIDs for comparison
            generator_clean = self._remove_uuids(generator_parsed)
            handler_clean = self._remove_uuids(handler_parsed)

            # Compare structures
            if self._structures_equal(generator_clean, handler_clean):
                self.logger.debug("Implementation outputs are structurally identical")
            else:
                self.logger.warning("Implementation outputs differ structurally")

        except Exception as e:
            self.logger.error(f"Implementation comparison failed: {e}")

    def _remove_uuids(self, structure):
        """Remove UUID fields from S-expression structure for comparison."""
        if isinstance(structure, list):
            result = []
            skip_next = False
            for _i, item in enumerate(structure):
                if skip_next:
                    skip_next = False
                    continue

                # Check for sexpdata Symbol objects or regular string "uuid"
                if (
                    hasattr(item, "__class__")
                    and hasattr(item.__class__, "__name__")
                    and item.__class__.__name__ == "Symbol"
                    and str(item) == "uuid"
                ) or (isinstance(item, str) and item == "uuid"):
                    skip_next = True  # Skip the UUID value
                    continue

                result.append(self._remove_uuids(item))
            return result
        else:
            return structure

    def _structures_equal(self, struct1, struct2) -> bool:
        """Check if two S-expression structures are equal."""
        if type(struct1) is not type(struct2):
            return False

        if isinstance(struct1, list):
            if len(struct1) != len(struct2):
                return False
            return all(self._structures_equal(a, b) for a, b in zip(struct1, struct2))
        else:
            return str(struct1) == str(struct2)

    def _record_performance(self, implementation: str, duration: float, success: bool):
        """Record performance statistics."""
        stats = self.performance_stats[implementation]
        stats["count"] += 1
        stats["total_time"] += duration

        if not success:
            stats["errors"] += 1

        if self.enable_performance_logging:
            avg_time = stats["total_time"] / stats["count"]
            self.logger.info(
                f"Performance [{implementation}]: {duration:.3f}s (avg: {avg_time:.3f}s, "
                f"count: {stats['count']}, errors: {stats['errors']})"
            )

    def get_performance_stats(self) -> dict[str, Any]:
        """Get current performance statistics."""
        stats = self.performance_stats.copy()

        # Calculate averages
        for impl in ["generator", "handler"]:
            if stats[impl]["count"] > 0:
                stats[impl]["avg_time"] = stats[impl]["total_time"] / stats[impl]["count"]
                stats[impl]["error_rate"] = stats[impl]["errors"] / stats[impl]["count"]
            else:
                stats[impl]["avg_time"] = 0.0
                stats[impl]["error_rate"] = 0.0

        return stats

    def get_config_info(self) -> dict[str, Any]:
        """Get current configuration information."""
        return {
            "primary_implementation": self.primary_implementation.value,
            "handler_enabled": self.enable_handler,
            "fallback_enabled": self.enable_fallback,
            "comparison_enabled": self.enable_comparison,
            "performance_logging_enabled": self.enable_performance_logging,
            "rollout_percentage": self.rollout_percentage,
            "validate_output": self.validate_output,
            "strict_validation": self.strict_validation,
        }

    def parse_schematic(self, content: str) -> dict[str, Any]:
        """Parse a KiCad schematic S-expression into a structured dictionary."""
        # Always use the handler for parsing since it has robust parsing capabilities
        return self.handler.parse_schematic(content)


# Global service instance for easy access
_service_instance: SExpressionService | None = None


def get_sexpr_service() -> SExpressionService:
    """Get the global S-expression service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SExpressionService()
    return _service_instance


def reset_sexpr_service():
    """Reset the global service instance (mainly for testing)."""
    global _service_instance
    _service_instance = None

"""
S-expression service using SExpressionHandler.

This service provides a unified interface for S-expression generation
using the production-ready SExpressionHandler implementation.
"""

import logging
from typing import Any

from kicad_mcp.utils.sexpr_handler import SExpressionHandler


class SExpressionService:
    """
    S-expression service using SExpressionHandler.

    This service provides a unified interface for S-expression generation
    using the production-ready SExpressionHandler implementation.
    """

    def __init__(self):
        """Initialize the S-expression service."""
        self.logger = logging.getLogger(__name__)
        self.handler = SExpressionHandler()

    def generate_schematic(
        self,
        circuit_name: str,
        components: list[dict[str, Any]],
        power_symbols: list[dict[str, Any]],
        connections: list[dict[str, Any]],
        pretty_print: bool = True,
    ) -> str:
        """
        Generate a KiCad schematic S-expression.

        Args:
            circuit_name: Name of the circuit
            components: List of component dictionaries
            power_symbols: List of power symbol dictionaries
            connections: List of connection dictionaries
            pretty_print: Whether to format output for readability

        Returns:
            S-expression formatted schematic as string
        """
        return self.handler.generate_schematic(
            circuit_name, components, power_symbols, connections, pretty_print
        )

    def parse_schematic(self, content: str) -> dict[str, Any]:
        """Parse a KiCad schematic S-expression into a structured dictionary."""
        return self.handler.parse_schematic(content)

    @property
    def layout_manager(self):
        """Access to the layout manager for compatibility."""
        return self.handler.layout_manager

    @property
    def pin_mapper(self):
        """Access to the pin mapper for compatibility."""
        return self.handler.pin_mapper

    def generate_advanced_wire_routing(self, net_connections: list[dict]) -> list[str]:
        """Generate advanced wire routing for compatibility."""
        return self.handler.generate_advanced_wire_routing(net_connections)


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

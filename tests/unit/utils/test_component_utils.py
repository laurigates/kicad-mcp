"""Tests for kicad_mcp.utils.component_utils.

Focus: regression coverage for MCU / IC detection in
:func:`get_component_type_from_symbol`. Prior to the fix, the consolidated
detector only matched ``"ic"``, ``"mcu"``, and ``"esp32"`` substrings,
silently downgrading AVR / PIC / STM32 parts to the ``"default"`` placement
type.
"""

import pytest

from kicad_mcp.utils.component_utils import (
    _MCU_FAMILY_PREFIXES,
    _REFERENCE_PREFIX_TO_TYPE,
    get_component_type_from_symbol,
)


class TestMcuFamilyDetection:
    """Symbol-name based MCU detection regression tests."""

    @pytest.mark.parametrize(
        "symbol_name",
        [
            "ATmega328P-PU",
            "STM32F103C8T6",
            "ATtiny85-20PU",
            "PIC18F4550",
        ],
    )
    def test_mcu_parts_classified_as_ic(self, symbol_name: str) -> None:
        """AVR/STM32/PIC parts must resolve to ``"ic"`` regardless of library."""
        assert get_component_type_from_symbol("MCU_Custom", symbol_name) == "ic"

    def test_esp32_still_matches(self) -> None:
        """Pre-existing ESP32 match must not regress."""
        assert get_component_type_from_symbol("RF_Module", "ESP32-WROOM-32") == "ic"

    def test_generic_ic_still_matches(self) -> None:
        """The plain ``ic`` substring still classifies as IC."""
        assert get_component_type_from_symbol("Custom", "MyIC_Part") == "ic"

    def test_non_mcu_symbol_not_classified_as_ic(self) -> None:
        """A plain resistor symbol name should not be an IC."""
        assert get_component_type_from_symbol("Device", "R") == "resistor"


class TestModuleLevelConstants:
    """The MCU prefix tuple and reference map are module-level singletons."""

    def test_mcu_family_prefixes_contains_expected_families(self) -> None:
        for family in ("atmega", "attiny", "stm32", "esp32", "ic", "mcu"):
            assert family in _MCU_FAMILY_PREFIXES

    def test_reference_prefix_map_hoisted_to_module_scope(self) -> None:
        """Sanity-check that the dict is built once, at import."""
        assert _REFERENCE_PREFIX_TO_TYPE["U"] == "ic"
        assert _REFERENCE_PREFIX_TO_TYPE["R"] == "resistor"

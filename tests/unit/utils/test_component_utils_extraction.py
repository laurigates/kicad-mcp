"""Tests for component value extraction functions in kicad_mcp.utils.component_utils.

Covers: extract_voltage_from_regulator, extract_frequency_from_value,
extract_resistance_value, extract_capacitance_value, extract_inductance_value,
format_value, normalize_component_value, get_component_type,
get_component_type_from_reference, is_power_component.
"""

import pytest

from kicad_mcp.utils.component_utils import (
    extract_capacitance_value,
    extract_frequency_from_value,
    extract_inductance_value,
    extract_resistance_value,
    extract_voltage_from_regulator,
    format_value,
    get_component_type,
    get_component_type_from_reference,
    is_power_component,
    normalize_component_value,
)


class TestExtractVoltageFromRegulator:
    """Tests for extract_voltage_from_regulator."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("LM7805CT", "5V"),
            ("LM7812", "12V"),
            ("LM7905", "5V"),
            ("LM7912", "12V"),
            ("AMS1117-3.3", "3.3V"),
            ("LM1117-3.3", "3.3V"),
            ("LM1117-5", "5V"),
            ("LM317", "Adjustable"),
            ("LM337", "Adjustable (Negative)"),
            ("MCP1700-3.3", "3.3V"),
            ("L7805", "5V"),
            ("Some LDO 5V", "5V"),
            ("3.3V regulator", "3.3V"),
        ],
    )
    def test_known_regulators(self, value: str, expected: str) -> None:
        assert extract_voltage_from_regulator(value) == expected

    def test_unknown_returns_unknown(self) -> None:
        assert extract_voltage_from_regulator("MYSTERY_PART") == "unknown"

    def test_79xx_negative_regulator(self) -> None:
        # 79xx series pattern
        result = extract_voltage_from_regulator("LM7909")
        assert result == "9V"


class TestExtractFrequencyFromValue:
    """Tests for extract_frequency_from_value."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Crystal 16MHz", "16.000MHz"),
            ("32.768kHz", "32.768kHz"),
            ("8MHz", "8.000MHz"),
            ("16M", "16.000MHz"),
            ("32.768k", "32.768kHz"),
            ("2.4GHz", "2.400GHz"),
            ("32768", "32.768kHz"),  # special case
        ],
    )
    def test_known_frequencies(self, value: str, expected: str) -> None:
        assert extract_frequency_from_value(value) == expected

    def test_unknown_returns_unknown(self) -> None:
        assert extract_frequency_from_value("no_freq_here") == "unknown"

    def test_bare_hz_value(self) -> None:
        result = extract_frequency_from_value("100Hz")
        assert result == "100.000Hz"


class TestExtractResistanceValue:
    """Tests for extract_resistance_value."""

    @pytest.mark.parametrize(
        ("value", "expected_val", "expected_unit"),
        [
            ("10k", 10.0, "kΩ"),
            ("4R7", 4.7, "Ω"),
            ("4k7", 4.7, "kΩ"),
            ("1M", 1.0, "MΩ"),
            ("100", 100.0, "Ω"),
            ("2.2k", 2.2, "kΩ"),
            ("100R", 100.0, "Ω"),
        ],
    )
    def test_resistance_values(self, value: str, expected_val: float, expected_unit: str) -> None:
        num, unit = extract_resistance_value(value)
        assert num == pytest.approx(expected_val)
        assert unit == expected_unit

    def test_empty_string(self) -> None:
        assert extract_resistance_value("") == (None, None)


class TestExtractCapacitanceValue:
    """Tests for extract_capacitance_value."""

    @pytest.mark.parametrize(
        ("value", "expected_val", "expected_unit"),
        [
            ("10uF", 10.0, "μF"),
            ("100nF", 100.0, "nF"),
            ("22pF", 22.0, "pF"),
            ("4n7", 4.7, "nF"),
            ("10u", 10.0, "μF"),
        ],
    )
    def test_capacitance_values(self, value: str, expected_val: float, expected_unit: str) -> None:
        num, unit = extract_capacitance_value(value)
        assert num == pytest.approx(expected_val)
        assert unit == expected_unit

    def test_empty_string(self) -> None:
        assert extract_capacitance_value("") == (None, None)


class TestExtractInductanceValue:
    """Tests for extract_inductance_value."""

    @pytest.mark.parametrize(
        ("value", "expected_val", "expected_unit"),
        [
            ("10uH", 10.0, "μH"),
            ("100mH", 100.0, "mH"),
            ("4u7", 4.7, "μH"),
            ("10nH", 10.0, "nH"),
        ],
    )
    def test_inductance_values(self, value: str, expected_val: float, expected_unit: str) -> None:
        num, unit = extract_inductance_value(value)
        assert num == pytest.approx(expected_val)
        assert unit == expected_unit

    def test_empty_string(self) -> None:
        assert extract_inductance_value("") == (None, None)


class TestFormatValue:
    """Tests for format_value."""

    def test_integer_value(self) -> None:
        assert format_value(10.0, "kΩ") == "10kΩ"

    def test_float_value(self) -> None:
        assert format_value(4.7, "kΩ") == "4.7kΩ"

    def test_zero(self) -> None:
        assert format_value(0.0, "Ω") == "0Ω"


class TestNormalizeComponentValue:
    """Tests for normalize_component_value."""

    def test_resistor(self) -> None:
        assert normalize_component_value("10k", "R") == "10kΩ"

    def test_capacitor(self) -> None:
        assert normalize_component_value("100nF", "C") == "100nF"

    def test_inductor(self) -> None:
        assert normalize_component_value("10uH", "L") == "10μH"

    def test_voltage_regulator(self) -> None:
        assert normalize_component_value("LM7805", "U") == "5V"

    def test_unknown_type_returns_original(self) -> None:
        assert normalize_component_value("XYZ", "Q") == "XYZ"

    def test_regulator_unknown_returns_original(self) -> None:
        assert normalize_component_value("MYSTERY", "U") == "MYSTERY"


class TestGetComponentType:
    """Tests for get_component_type."""

    @pytest.mark.parametrize(
        ("lib_id", "expected"),
        [
            ("Device:R", "resistor"),
            ("Device:C", "capacitor"),
            ("Device:L", "inductor"),
            ("Device:LED", "led"),
            ("Device:D", "diode"),
            ("power:GND", "power"),
            ("power:VCC", "power"),
            ("Connector:Conn_01x02", "connector"),
            ("Switch:SW_Push", "switch"),
            ("MCU_Microchip:ATmega328P", "ic"),
        ],
    )
    def test_lib_id_detection(self, lib_id: str, expected: str) -> None:
        assert get_component_type(lib_id) == expected

    def test_reference_fallback(self) -> None:
        assert get_component_type("", "R1") == "resistor"
        assert get_component_type("", "C5") == "capacitor"
        assert get_component_type("", "U3") == "ic"

    def test_unknown(self) -> None:
        assert get_component_type("") == "unknown"

    def test_transistor_npn(self) -> None:
        assert get_component_type("Transistor_BJT:NPN_EBC") == "transistor"

    def test_resistor_variants(self) -> None:
        assert get_component_type("Device:R_Small") == "resistor"

    def test_capacitor_variants(self) -> None:
        assert get_component_type("Device:C_Polarized") == "capacitor"

    def test_inductor_variants(self) -> None:
        assert get_component_type("Device:L_Core_Ferrite") == "inductor"


class TestGetComponentTypeFromReference:
    """Tests for get_component_type_from_reference."""

    @pytest.mark.parametrize(
        ("ref", "expected"),
        [
            ("R1", "R"),
            ("C22", "C"),
            ("U10", "U"),
            ("LED3", "LED"),
            ("SW_SPDT2", "SW_SPDT"),
        ],
    )
    def test_reference_prefix(self, ref: str, expected: str) -> None:
        assert get_component_type_from_reference(ref) == expected

    def test_empty_string(self) -> None:
        assert get_component_type_from_reference("") == ""

    def test_numeric_only(self) -> None:
        assert get_component_type_from_reference("123") == ""


class TestIsPowerComponent:
    """Tests for is_power_component."""

    def test_power_reference_prefix(self) -> None:
        assert is_power_component({"reference": "VR1", "value": "", "lib_id": ""}) is True
        assert is_power_component({"reference": "PS1", "value": "", "lib_id": ""}) is True
        assert is_power_component({"reference": "REG1", "value": "", "lib_id": ""}) is True

    def test_power_keywords_in_value(self) -> None:
        assert is_power_component({"reference": "U1", "value": "VCC", "lib_id": ""}) is True
        assert (
            is_power_component({"reference": "U1", "value": "LDO REGULATOR", "lib_id": ""}) is True
        )

    def test_power_keywords_in_lib_id(self) -> None:
        assert is_power_component({"reference": "U1", "value": "", "lib_id": "power:GND"}) is True

    def test_regulator_part_numbers(self) -> None:
        assert is_power_component({"reference": "U1", "value": "LM7805", "lib_id": ""}) is True
        assert is_power_component({"reference": "U1", "value": "AMS1117", "lib_id": ""}) is True

    def test_non_power_component(self) -> None:
        assert (
            is_power_component({"reference": "R1", "value": "10k", "lib_id": "Device:R"}) is False
        )

    def test_missing_keys_defaults(self) -> None:
        assert is_power_component({}) is False

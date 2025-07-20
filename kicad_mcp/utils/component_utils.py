"""
Utilities for parsing, normalizing, and identifying KiCad component properties.

This module provides a collection of helper functions designed to work with
component data commonly found in KiCad projects. It uses regular expressions
and lookup tables to extract meaningful information—such as voltage, frequency,
resistance, capacitance, and inductance—from raw value strings. It also includes
functions to normalize these values into a standard format and identify
component types from their reference designators.
"""

import re
from typing import Any


def extract_voltage_from_regulator(value: str) -> str:
    """Extracts the output voltage from a voltage regulator's part number.

    This function attempts to find the voltage by sequentially applying
    several strategies:
    1.  Looks for classic `78xx`/`79xx` series patterns.
    2.  Searches for explicit voltage values (e.g., "3.3V", "-5V").
    3.  Checks against a dictionary of common regulator part numbers.

    If no voltage can be determined, it returns "unknown" or "Adjustable".

    Args:
        value (str): The component value string, typically the regulator's part number
                     or a description (e.g., "LM7805", "LM1117-3.3", "5V LDO").

    Returns:
        str: The extracted voltage as a formatted string (e.g., "5V", "3.3V", "-12V")
             or a status string ("unknown", "Adjustable").

    Examples:
        >>> extract_voltage_from_regulator("LM7805CT")
        '5V'
        >>> extract_voltage_from_regulator("AMS1117-3.3")
        '3.3V'
        >>> extract_voltage_from_regulator("Some LDO 5V")
        '5V'
        >>> extract_voltage_from_regulator("7912")
        '12V'
        >>> extract_voltage_from_regulator("LM317T")
        'Adjustable'
        >>> extract_voltage_from_regulator("Some random part")
        'unknown'
    """
    # Strategy 1: 78xx/79xx series
    match = re.search(r"78(\d{2})|79(\d{2})", value, re.IGNORECASE)
    if match:
        group = match.group(1) or match.group(2)
        try:
            voltage = int(group)
            if voltage < 50:  # Sanity check
                return f"{voltage}V"
        except ValueError:
            pass

    # Strategy 2: Common voltage indicators
    voltage_patterns = [
        r"(\d+\.?\d*)\s*V",    # "3.3V", "5V"
        r"-(\d+\.?\d*)\s*V",   # "-5V", "-12V"
        r"[_-](\d+\.?\d+)",  # "LM1117-3.3"
    ]
    for pattern in voltage_patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            try:
                voltage = float(match.group(1))
                if 0 < voltage < 50:  # Sanity check
                    return f"{int(voltage)}V" if voltage.is_integer() else f"{voltage}V"
            except (ValueError, IndexError):
                pass

    # Strategy 3: Dictionary of known regulators
    regulators = {
        "LM7805": "5V", "LM7809": "9V", "LM7812": "12V",
        "LM7905": "-5V", "LM7912": "-12V",
        "LM1117-3.3": "3.3V", "LM1117-5": "5V",
        "LM317": "Adjustable", "LM337": "Adjustable (Negative)",
        "AMS1117-3.3": "3.3V", "L7805": "5V", "MCP1700-3.3": "3.3V",
    }
    for reg, volt in regulators.items():
        if re.search(re.escape(reg), value, re.IGNORECASE):
            return volt

    return "unknown"


def extract_frequency_from_value(value: str) -> str:
    """Extracts frequency information from a component value string.

    Searches for numeric values followed by frequency units (Hz, kHz, MHz, GHz)
    or common abbreviations (k, M, G). It attempts to normalize the output
    to a standard format.

    Args:
        value (str): The component value or description (e.g., "16MHz", "Crystal 8M").

    Returns:
        str: The formatted frequency string (e.g., "16.000MHz", "32.768kHz")
             or "unknown" if parsing fails.

    Examples:
        >>> extract_frequency_from_value("Crystal 16MHz")
        '16.000MHz'
        >>> extract_frequency_from_value("32.768k")
        '32.768kHz'
        >>> extract_frequency_from_value("OSC 4000000")
        '4.000MHz'
        >>> extract_frequency_from_value("32768")
        '32.768kHz'
    """
    # Patterns with explicit units
    match = re.search(r"(\d+\.?\d*)\s*([kKmMgG])?[hH][zZ]", value, re.IGNORECASE)
    if not match:
        # Patterns with implicit units (e.g., "16M")
        match = re.search(r"(\d+\.?\d*)\s*([kKmMgG])", value, re.IGNORECASE)

    if match:
        try:
            freq = float(match.group(1))
            unit = match.group(2).upper() if match.group(2) else ""
            if freq > 0:
                if unit == "K": return f"{freq:.3f}kHz"
                if unit == "M": return f"{freq:.3f}MHz"
                if unit == "G": return f"{freq:.3f}GHz"
                # If no unit, infer from magnitude
                if freq < 1000: return f"{freq:.3f}Hz"
                if freq < 1_000_000: return f"{freq / 1000:.3f}kHz"
                return f"{freq / 1_000_000:.3f}MHz"
        except (ValueError, IndexError):
            pass

    # Fallback for common crystal values without clear units
    if "32.768" in value or "32768" in value:
        return "32.768kHz"

    return "unknown"


def extract_resistance_value(value: str) -> tuple[float | None, str | None]:
    """Extracts a numeric resistance and its unit from a string.

    Handles standard notations like "10k", "4.7M", "100R", "100" and
    inline notations like "4k7" (4.7k).

    Args:
        value (str): The resistance value string to parse.

    Returns:
        A tuple containing the numeric value (float) and the base unit
        (str, e.g., 'Ω', 'kΩ', 'MΩ'), or (None, None) if parsing fails.

    Examples:
        >>> extract_resistance_value("10k")
        (10.0, 'kΩ')
        >>> extract_resistance_value("4R7")
        (4.7, 'Ω')
        >>> extract_resistance_value("100")
        (100.0, 'Ω')
        >>> extract_resistance_value("invalid")
        (None, None)
    """
    # Handle "4k7" -> 4.7k
    match = re.search(r"(\d+)([kKmMrR])(\d+)", value, re.IGNORECASE)
    if match:
        try:
            val_str = f"{match.group(1)}.{match.group(3)}"
            unit_char = match.group(2).upper()
            unit_map = {"R": "Ω", "K": "kΩ", "M": "MΩ"}
            return float(val_str), unit_map.get(unit_char, "Ω")
        except ValueError:
            pass

    # Handle "10k", "100", "100R"
    match = re.search(r"(\d+\.?\d*)\s*([kKmMrRΩ]?)", value, re.IGNORECASE)
    if match:
        try:
            num_val = float(match.group(1))
            unit_char = match.group(2).upper()
            if unit_char in ("R", "Ω", ""): return num_val, "Ω"
            if unit_char == "K": return num_val, "kΩ"
            if unit_char == "M": return num_val, "MΩ"
        except (ValueError, IndexError):
            pass

    return None, None


def extract_capacitance_value(value: str) -> tuple[float | None, str | None]:
    """Extracts a numeric capacitance and its unit from a string.

    Handles standard notations like "10uF", "100n", and inline "4n7".

    Args:
        value (str): The capacitance value string to parse.

    Returns:
        A tuple containing the numeric value (float) and the unit (str),
        or (None, None) if parsing fails.

    Examples:
        >>> extract_capacitance_value("10uF")
        (10.0, 'μF')
        >>> extract_capacitance_value("100n")
        (100.0, 'nF')
        >>> extract_capacitance_value("4n7")
        (4.7, 'nF')
    """
    # Handle "4n7" -> 4.7nF
    match = re.search(r"(\d+)([pPnNuUμ])(\d+)", value, re.IGNORECASE)
    if match:
        try:
            val_str = f"{match.group(1)}.{match.group(3)}"
            unit_char = match.group(2).lower()
            if unit_char == 'p': return float(val_str), "pF"
            if unit_char == 'n': return float(val_str), "nF"
            if unit_char in ('u', 'μ'): return float(val_str), "μF"
        except ValueError:
            pass
    
    # Handle "10uF", "100n", etc.
    match = re.search(r"(\d+\.?\d*)\s*([pPnNuUμ]*[fF]?)", value, re.IGNORECASE)
    if match:
        try:
            num_val = float(match.group(1))
            unit_str = match.group(2).lower()
            if 'p' in unit_str: return num_val, "pF"
            if 'n' in unit_str: return num_val, "nF"
            if 'u' in unit_str or 'μ' in unit_str: return num_val, "μF"
            if 'f' in unit_str: return num_val, "F" # Assumes base unit if only 'F'
        except (ValueError, IndexError):
            pass

    return None, None


def extract_inductance_value(value: str) -> tuple[float | None, str | None]:
    """Extracts a numeric inductance and its unit from a string.

    Handles standard notations like "10uH", "100m", and inline "4u7".

    Args:
        value (str): The inductance value string to parse.

    Returns:
        A tuple containing the numeric value (float) and the unit (str),
        or (None, None) if parsing fails.
    
    Examples:
        >>> extract_inductance_value("10uH")
        (10.0, 'μH')
        >>> extract_inductance_value("4u7")
        (4.7, 'μH')
    """
    # Handle "4u7" -> 4.7uH
    match = re.search(r"(\d+)([pPnNuUμmM])(\d+)", value, re.IGNORECASE)
    if match:
        try:
            val_str = f"{match.group(1)}.{match.group(3)}"
            unit_char = match.group(2).lower()
            if unit_char == 'n': return float(val_str), "nH"
            if unit_char in ('u', 'μ'): return float(val_str), "μH"
            if unit_char == 'm': return float(val_str), "mH"
        except ValueError:
            pass

    # Handle "10uH", "100mH", etc.
    match = re.search(r"(\d+\.?\d*)\s*([pPnNuUμmM]?[hH]?)", value, re.IGNORECASE)
    if match:
        try:
            num_val = float(match.group(1))
            unit_str = match.group(2).lower()
            if 'n' in unit_str: return num_val, "nH"
            if 'u' in unit_str or 'μ' in unit_str: return num_val, "μH"
            if 'm' in unit_str: return num_val, "mH"
            if 'h' in unit_str: return num_val, "H"
        except (ValueError, IndexError):
            pass
            
    return None, None


def format_value(value: float, unit: str) -> str:
    """Formats a numeric value and unit into a clean string.

    Removes trailing ".0" for integer values.

    Args:
        value (float): The numeric value.
        unit (str): The unit string (e.g., "kΩ", "μF", "MHz").

    Returns:
        str: A nicely formatted string.
    """
    if value.is_integer():
        return f"{int(value)}{unit}"
    return f"{value}{unit}"


def normalize_component_value(value: str, component_type: str) -> str:
    """Parses and normalizes a component value string based on its type.

    This acts as a high-level wrapper around the various `extract_*` and
    `format_*` functions. If parsing is successful, it returns a standardized
    string; otherwise, it returns the original value.

    Args:
        value (str): The raw component value string from KiCad.
        component_type (str): The component type identifier (e.g., "R", "C", "L", "U").

    Returns:
        str: A normalized and formatted value string, or the original value on failure.
    """
    type_map = {
        "R": extract_resistance_value,
        "C": extract_capacitance_value,
        "L": extract_inductance_value,
    }

    if component_type in type_map:
        num_val, unit = type_map[component_type](value)
        if num_val is not None and unit is not None:
            return format_value(num_val, unit)
    
    if component_type.startswith("U"): # ICs, Regulators, etc.
        voltage = extract_voltage_from_regulator(value)
        if voltage != "unknown":
            return voltage

    return value


def get_component_type_from_reference(reference: str) -> str:
    """Determines the component type letter(s) from its reference designator.

    Args:
        reference (str): The component reference (e.g., "R1", "C22", "JP3", "U10").

    Returns:
        str: The alphabetic prefix of the reference (e.g., "R", "C", "JP", "U"),
             or an empty string if no prefix is found.
    
    Examples:
        >>> get_component_type_from_reference("R101")
        'R'
        >>> get_component_type_from_reference("SW_SPDT2")
        'SW_SPDT'
    """
    match = re.match(r"^([A-Za-z_]+)", reference)
    return match.group(1).upper() if match else ""


def is_power_component(component: dict[str, Any]) -> bool:
    """Checks if a component is likely power-related using a set of heuristics.

    This function inspects the component's reference, value, and library ID for
    common power-related prefixes, keywords, and part numbers.

    Args:
        component (dict): A dictionary containing component data. Expected keys are
                          'reference', 'value', and 'lib_id'.
                          e.g., {'reference': 'U1', 'value': 'LM7805', 'lib_id': 'Regulator_Linear'}

    Returns:
        bool: True if the component is likely power-related, False otherwise.
    """
    ref = component.get("reference", "").upper()
    value = component.get("value", "").upper()
    lib_id = component.get("lib_id", "").upper()

    # Heuristic 1: Check reference designator prefixes
    if ref.startswith(("VR", "PS", "REG", "V")):
        return True

    # Heuristic 2: Check for keywords in value or library ID
    power_terms = ["VCC", "VDD", "GND", "POWER", "PWR", "SUPPLY", "REGULATOR", "LDO"]
    if any(term in value or term in lib_id for term in power_terms):
        return True

    # Heuristic 3: Check for common regulator part number patterns
    regulator_patterns = [r"78\d{2}", r"79\d{2}", r"LM\d{3,4}", r"AMS\d{4}", r"MCP\d{4}"]
    if any(re.search(pattern, value) for pattern in regulator_patterns):
        return True

    return False
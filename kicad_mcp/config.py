"""
Configuration settings for the KiCad MCP server.
"""

import os
import platform

# Determine operating system
system = platform.system()

# KiCad paths based on operating system
if system == "Darwin":  # macOS
    KICAD_USER_DIR = os.path.expanduser("~/Documents/KiCad")
    KICAD_APP_PATH = "/Applications/KiCad/KiCad.app"
elif system == "Windows":
    KICAD_USER_DIR = os.path.expanduser("~/Documents/KiCad")
    KICAD_APP_PATH = r"C:\Program Files\KiCad"
elif system == "Linux":
    KICAD_USER_DIR = os.path.expanduser("~/KiCad")
    KICAD_APP_PATH = "/usr/share/kicad"
else:
    # Default to macOS paths if system is unknown
    KICAD_USER_DIR = os.path.expanduser("~/Documents/KiCad")
    KICAD_APP_PATH = "/Applications/KiCad/KiCad.app"

# Additional search paths from environment variable
ADDITIONAL_SEARCH_PATHS = []
env_search_paths = os.environ.get("KICAD_SEARCH_PATHS", "")
if env_search_paths:
    for path in env_search_paths.split(","):
        expanded_path = os.path.expanduser(path.strip())
        if os.path.exists(expanded_path):
            ADDITIONAL_SEARCH_PATHS.append(expanded_path)

# Try to auto-detect common project locations if not specified
DEFAULT_PROJECT_LOCATIONS = [
    "~/Documents/PCB",
    "~/PCB",
    "~/Electronics",
    "~/Projects/Electronics",
    "~/Projects/PCB",
    "~/Projects/KiCad",
]

for location in DEFAULT_PROJECT_LOCATIONS:
    expanded_path = os.path.expanduser(location)
    if os.path.exists(expanded_path) and expanded_path not in ADDITIONAL_SEARCH_PATHS:
        ADDITIONAL_SEARCH_PATHS.append(expanded_path)

# Base path to KiCad's Python framework
if system == "Darwin":  # macOS
    KICAD_PYTHON_BASE = os.path.join(
        KICAD_APP_PATH, "Contents/Frameworks/Python.framework/Versions"
    )
else:
    KICAD_PYTHON_BASE = ""  # Will be determined dynamically in python_path.py


# File extensions
KICAD_EXTENSIONS = {
    "project": ".kicad_pro",
    "pcb": ".kicad_pcb",
    "schematic": ".kicad_sch",
    "design_rules": ".kicad_dru",
    "worksheet": ".kicad_wks",
    "footprint": ".kicad_mod",
    "netlist": "_netlist.net",
    "kibot_config": ".kibot.yaml",
}

# Recognized data files
DATA_EXTENSIONS = [
    ".csv",  # BOM or other data
    ".pos",  # Component position file
    ".net",  # Netlist files
    ".zip",  # Gerber files and other archives
    ".drl",  # Drill files
]

# Circuit creation constants
CIRCUIT_DEFAULTS = {
    "grid_spacing": 1.0,  # Default grid spacing in mm for user coordinates
    "component_spacing": 10.16,  # Default component spacing in mm
    "wire_width": 6,  # Default wire width in KiCad units (0.006 inch)
    "text_size": [1.27, 1.27],  # Default text size in mm
    "pin_length": 2.54,  # Default pin length in mm
}

# Common component libraries
COMMON_LIBRARIES = {
    "basic": {
        "resistor": {"library": "Device", "symbol": "R"},
        "capacitor": {"library": "Device", "symbol": "C"},
        "inductor": {"library": "Device", "symbol": "L"},
        "led": {"library": "Device", "symbol": "LED"},
        "diode": {"library": "Device", "symbol": "D"},
    },
    "power": {
        "vcc": {"library": "power", "symbol": "VCC"},
        "gnd": {"library": "power", "symbol": "GND"},
        "+5v": {"library": "power", "symbol": "+5V"},
        "+3v3": {"library": "power", "symbol": "+3V3"},
        "+12v": {"library": "power", "symbol": "+12V"},
        "-12v": {"library": "power", "symbol": "-12V"},
    },
    "connectors": {
        "conn_2pin": {"library": "Connector", "symbol": "Conn_01x02_Male"},
        "conn_4pin": {"library": "Connector_Generic", "symbol": "Conn_01x04"},
        "conn_8pin": {"library": "Connector_Generic", "symbol": "Conn_01x08"},
    },
}

# Default footprint suggestions
DEFAULT_FOOTPRINTS = {
    "R": [
        "Resistor_SMD:R_0805_2012Metric",
        "Resistor_SMD:R_0603_1608Metric",
        "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    ],
    "C": [
        "Capacitor_SMD:C_0805_2012Metric",
        "Capacitor_SMD:C_0603_1608Metric",
        "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    ],
    "LED": ["LED_SMD:LED_0805_2012Metric", "LED_THT:LED_D5.0mm"],
    "D": ["Diode_SMD:D_SOD-123", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"],
}

# Timeout constants (in seconds)
TIMEOUT_CONSTANTS = {
    "kicad_cli_version_check": 10.0,  # Timeout for KiCad CLI version checks
    "kicad_cli_export": 30.0,  # Timeout for KiCad CLI export operations
    "application_open": 10.0,  # Timeout for opening applications (e.g., KiCad)
    "subprocess_default": 30.0,  # Default timeout for subprocess operations
}

# Progress reporting constants
PROGRESS_CONSTANTS = {
    "start": 10,  # Initial progress percentage
    "detection": 20,  # Progress after CLI detection
    "setup": 30,  # Progress after setup complete
    "processing": 50,  # Progress during processing
    "finishing": 70,  # Progress when finishing up
    "validation": 90,  # Progress during validation
    "complete": 100,  # Progress when complete
}

# Display constants
DISPLAY_CONSTANTS = {
    "bom_preview_limit": 20,  # Maximum number of BOM items to show in preview
}

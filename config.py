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
    KICAD_USER_DIR = os.path.expanduser("~/kicad")
    KICAD_APP_PATH = "/usr/share/kicad"
else:
    # Default to macOS paths if system is unknown
    KICAD_USER_DIR = os.path.expanduser("~/Documents/KiCad")
    KICAD_APP_PATH = "/Applications/KiCad/KiCad.app"

# Base path to KiCad's Python framework
KICAD_PYTHON_BASE = os.path.join(KICAD_APP_PATH, "Contents/Frameworks/Python.framework/Versions")

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
]

"""
Configuration settings for the KiCad MCP server.
"""
import os

# KiCad paths
KICAD_USER_DIR = os.path.expanduser("~/Documents/KiCad")
KICAD_APP_PATH = "/Applications/KiCad/KiCad.app"

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

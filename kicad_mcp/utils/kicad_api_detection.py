"""
Utility functions for detecting and selecting available KiCad API approaches.
"""
import os
import subprocess
import shutil
from typing import Tuple, Optional, Literal

from kicad_mcp.config import system

def check_for_cli_api() -> bool:
    """Check if KiCad CLI API is available.
    
    Returns:
        True if KiCad CLI is available, False otherwise
    """
    try:
        # Check if kicad-cli is in PATH
        if system == "Windows":
            # On Windows, check for kicad-cli.exe
            kicad_cli = shutil.which("kicad-cli.exe")
        else:
            # On Unix-like systems
            kicad_cli = shutil.which("kicad-cli")
        
        if kicad_cli:
            # Verify it's a working kicad-cli
            if system == "Windows":
                cmd = [kicad_cli, "--version"]
            else:
                cmd = [kicad_cli, "--version"]
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Found working kicad-cli: {kicad_cli}")
                return True
        
        # Check common installation locations if not found in PATH
        if system == "Windows":
            # Common Windows installation paths
            potential_paths = [
                r"C:\Program Files\KiCad\bin\kicad-cli.exe",
                r"C:\Program Files (x86)\KiCad\bin\kicad-cli.exe"
            ]
        elif system == "Darwin":  # macOS
            # Common macOS installation paths
            potential_paths = [
                "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
                "/Applications/KiCad/kicad-cli"
            ]
        else:  # Linux
            # Common Linux installation paths
            potential_paths = [
                "/usr/bin/kicad-cli",
                "/usr/local/bin/kicad-cli",
                "/opt/kicad/bin/kicad-cli"
            ]
        
        # Check each potential path
        for path in potential_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                print(f"Found kicad-cli at common location: {path}")
                return True
        
        print("KiCad CLI API is not available")
        return False
        
    except Exception as e:
        print(f"Error checking for KiCad CLI API: {str(e)}")
        return False


def check_for_ipc_api() -> bool:
    """Check if KiCad IPC API (kicad-python) is available.
    
    Returns:
        True if KiCad IPC API is available, False otherwise
    """
    try:
        # Try to import the kipy module
        import kipy
        print("KiCad IPC API (kicad-python) is available")
        return True
    except ImportError:
        print("KiCad IPC API (kicad-python) is not available")
        return False
    except Exception as e:
        print(f"Error checking for KiCad IPC API: {str(e)}")
        return False


def check_ipc_api_environment() -> Tuple[bool, Optional[str]]:
    """Check if we're running in a KiCad IPC plugin environment.
    
    Returns:
        Tuple of (is_plugin, socket_path)
    """
    # Check for environment variables that would indicate we're a plugin
    is_plugin = os.environ.get("KICAD_PLUGIN_ENV") is not None
    
    # Check for socket path in environment
    socket_path = os.environ.get("KICAD_SOCKET_PATH")
    
    if is_plugin:
        print("Running as a KiCad plugin")
    elif socket_path:
        print(f"KiCad IPC socket path found: {socket_path}")
    
    return (is_plugin, socket_path)


def get_best_api_approach() -> Literal["cli", "ipc", "none"]:
    """Determine the best available KiCad API approach.
    
    Returns:
        String indicating which API approach to use:
        - "cli": Use KiCad command-line interface
        - "ipc": Use KiCad IPC API (kicad-python)
        - "none": No API available
    """
    # Check for IPC API first (preferred if available)
    if check_for_ipc_api():
        return "ipc"
    
    # Check for CLI API next
    if check_for_cli_api():
        return "cli"
    
    # No API available
    print("No KiCad API available")
    return "none"

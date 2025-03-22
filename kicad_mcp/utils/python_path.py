"""
Python path handling for KiCad modules.
"""
import os
import sys
import glob
import platform

def setup_kicad_python_path():
    """
    Add KiCad Python modules to the Python path by detecting the appropriate version.
    
    Returns:
        bool: True if successful, False otherwise
    """
    system = platform.system()
    print(f"Setting up KiCad Python path for {system}")
    
    # Define search paths based on operating system
    if system == "Darwin":  # macOS
        from kicad_mcp.config import KICAD_APP_PATH
        
        if not os.path.exists(KICAD_APP_PATH):
            print(f"KiCad application not found at {KICAD_APP_PATH}")
            return False
            
        # Base path to Python framework
        python_base = os.path.join(KICAD_APP_PATH, "Contents/Frameworks/Python.framework/Versions")
        
        # First try 'Current' symlink
        current_path = os.path.join(python_base, "Current/lib/python*/site-packages")
        site_packages = glob.glob(current_path)
        
        # If 'Current' symlink doesn't work, find all available Python versions
        if not site_packages:
            print("'Current' symlink not found, searching for numbered versions")
            # Look for numbered versions like 3.9, 3.10, etc.
            version_dirs = glob.glob(os.path.join(python_base, "[0-9]*"))
            for version_dir in version_dirs:
                potential_path = os.path.join(version_dir, "lib/python*/site-packages")
                site_packages.extend(glob.glob(potential_path))
    
    elif system == "Windows":
        # Windows path - typically in Program Files
        kicad_app_path = r"C:\Program Files\KiCad"
        python_dirs = glob.glob(os.path.join(kicad_app_path, "lib", "python*"))
        site_packages = []
        
        for python_dir in python_dirs:
            potential_path = os.path.join(python_dir, "site-packages")
            if os.path.exists(potential_path):
                site_packages.append(potential_path)
    
    elif system == "Linux":
        # Common Linux installation paths
        site_packages = [
            "/usr/lib/python3/dist-packages",  # Debian/Ubuntu
            "/usr/lib/python3.*/site-packages",  # Red Hat/Fedora
            "/usr/local/lib/python3.*/site-packages"  # Source install
        ]
        
        # Expand glob patterns
        expanded_packages = []
        for pattern in site_packages:
            if "*" in pattern:
                expanded_packages.extend(glob.glob(pattern))
            else:
                expanded_packages.append(pattern)
        
        site_packages = expanded_packages
    
    else:
        print(f"Unsupported operating system: {system}")
        return False
    
    # Pick the first valid path found
    for path in site_packages:
        if os.path.exists(path):
            # Check if pcbnew module exists in this path
            pcbnew_path = os.path.join(path, "pcbnew.so")
            if not os.path.exists(pcbnew_path):
                # On Windows it might be pcbnew.pyd instead
                pcbnew_path = os.path.join(path, "pcbnew.pyd")
            
            if os.path.exists(pcbnew_path):
                if path not in sys.path:
                    sys.path.append(path)
                    print(f"Added KiCad Python path: {path}")
                    print(f"Found pcbnew module at: {pcbnew_path}")
                    
                    # Try to actually import it to verify compatibility
                    try:
                        import pcbnew
                        print(f"Successfully imported pcbnew module version: {getattr(pcbnew, 'GetBuildVersion', lambda: 'unknown')()}")
                        return True
                    except ImportError as e:
                        print(f"Found pcbnew but failed to import: {str(e)}")
                        # Remove from path as it's not usable
                        sys.path.remove(path)
            else:
                print(f"Found site-packages at {path} but no pcbnew module")
    
    print("Could not find a valid KiCad Python site-packages directory with pcbnew module")
    return False

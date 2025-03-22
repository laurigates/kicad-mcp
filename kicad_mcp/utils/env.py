"""
Environment variable handling for KiCad MCP Server.
"""
import os
from typing import Dict, Optional

def load_dotenv(env_file: str = ".env") -> Dict[str, str]:
    """Load environment variables from .env file.
    
    Args:
        env_file: Path to the .env file
        
    Returns:
        Dictionary of loaded environment variables
    """
    env_vars = {}
    
    # Try to find .env file in the current directory or parent directories
    env_path = find_env_file(env_file)
    
    if not env_path:
        # No .env file found, return empty dict
        return env_vars
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key-value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Expand ~ to user's home directory
                    if '~' in value:
                        value = os.path.expanduser(value)
                    
                    # Set environment variable
                    os.environ[key] = value
                    env_vars[key] = value
    
    except Exception as e:
        print(f"Error loading .env file: {str(e)}")
    
    return env_vars

def find_env_file(filename: str = ".env") -> Optional[str]:
    """Find a .env file in the current directory or parent directories.
    
    Args:
        filename: Name of the env file to find
        
    Returns:
        Path to the env file if found, None otherwise
    """
    current_dir = os.getcwd()
    max_levels = 3  # Limit how far up to search
    
    for _ in range(max_levels):
        env_path = os.path.join(current_dir, filename)
        if os.path.exists(env_path):
            return env_path
        
        # Move up one directory
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # We've reached the root
            break
        current_dir = parent_dir
    
    return None

def get_env_list(env_var: str, default: str = "") -> list:
    """Get a list from a comma-separated environment variable.
    
    Args:
        env_var: Name of the environment variable
        default: Default value if environment variable is not set
        
    Returns:
        List of values
    """
    value = os.environ.get(env_var, default)
    if not value:
        return []
    
    # Split by comma and strip whitespace
    items = [item.strip() for item in value.split(",")]
    
    # Filter out empty items
    return [item for item in items if item]

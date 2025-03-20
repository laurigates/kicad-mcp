"""
Simple logger with automatic function-level context tracking for KiCad MCP Server.

Usage examples:
# Creates logs in the "logs" directory by default
logger = Logger()

# To disable file logging completely
logger = Logger(log_dir=None)

# Or to specify a custom logs directory
logger = Logger(log_dir="custom_logs")
"""
import os
import sys
import logging
import inspect
from datetime import datetime
from pathlib import Path


class Logger:
    """
    Simple logger that automatically tracks function-level context.
    """
    def __init__(self, name=None, log_dir="logs", console_level=logging.INFO, file_level=logging.DEBUG):
        """
        Initialize a logger with automatic function-level context.
        
        Args:
            name: Logger name (defaults to calling module name)
            log_dir: Directory to store log files (default: "logs" directory)
                     Set to None to disable file logging
            console_level: Logging level for console output
            file_level: Logging level for file output
        """
        # If no name provided, try to determine it from the calling module
        if name is None:
            frame = inspect.currentframe().f_back
            module = inspect.getmodule(frame)
            self.name = module.__name__ if module else "kicad_mcp"
        else:
            self.name = name
            
        # Initialize Python's logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels, filtering at handler level
        
        # Only configure if not already configured
        if not self.logger.handlers and not logging.getLogger().handlers:
            # Create formatter with detailed context
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(pathname)s:%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Set up console output
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # Set up file output by default unless explicitly disabled
            if log_dir is not None:
                log_dir_path = Path(log_dir)
                log_dir_path.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                log_file = log_dir_path / f"kicad_mcp_{timestamp}.log"
                
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(file_level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                
                self.info(f"Logging session started, log file: {log_file}")

    def _get_caller_info(self):
        """Get information about the function that called the logger."""
        # Skip this function, the log method, and get to the actual caller
        frame = inspect.currentframe().f_back.f_back
        return frame
                
    def debug(self, message):
        """Log a debug message with caller context."""
        self.logger.debug(message)
        
    def info(self, message):
        """Log an info message with caller context."""
        self.logger.info(message)
        
    def warning(self, message):
        """Log a warning message with caller context."""
        self.logger.warning(message)
        
    def error(self, message):
        """Log an error message with caller context."""
        self.logger.error(message)
        
    def critical(self, message):
        """Log a critical message with caller context."""
        self.logger.critical(message)
        
    def exception(self, message):
        """Log an exception message with caller context and traceback."""
        self.logger.exception(message)

"""
Logging Configuration for Oraban Traffic Signal Control Project.

Provides centralized logging configuration with:
- Console output with colored formatting
- File output with rotation
- Configurable log levels per module
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


# ANSI color codes for console output
class LogColors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    LEVEL_COLORS = {
        logging.DEBUG: LogColors.GRAY,
        logging.INFO: LogColors.GREEN,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.MAGENTA,
    }
    
    def __init__(self, fmt: str, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = self.LEVEL_COLORS.get(record.levelno, LogColors.RESET)
            record.levelname = f"{color}{record.levelname}{LogColors.RESET}"
            record.name = f"{LogColors.CYAN}{record.name}{LogColors.RESET}"
        return super().format(record)


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    use_colors: bool = True
) -> logging.Logger:
    """
    Set up logging for the entire application.
    
    Args:
        log_dir: Directory for log files
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        max_file_size_mb: Maximum size of each log file in MB
        backup_count: Number of backup log files to keep
        use_colors: Whether to use colored output in console
        
    Returns:
        Root logger configured with handlers
    """
    # Create log directory if needed
    if log_to_file:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        console_formatter = ColoredFormatter(console_format, datefmt="%H:%M:%S", use_colors=use_colors)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        log_file = Path(log_dir) / "oraban.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Module-level loggers for easy import
environment_logger = get_logger("oraban.environment")
observation_logger = get_logger("oraban.observation")
reward_logger = get_logger("oraban.reward")
training_logger = get_logger("oraban.training")
agent_logger = get_logger("oraban.agent")


# Initialize logging when module is imported (can be reconfigured later)
_initialized = False

def init_logging(**kwargs):
    """Initialize logging with custom configuration."""
    global _initialized
    if not _initialized:
        setup_logging(**kwargs)
        _initialized = True


def get_training_logger():
    """Get the training logger for use in training scripts."""
    return training_logger


def get_environment_logger():
    """Get the environment logger."""
    return environment_logger

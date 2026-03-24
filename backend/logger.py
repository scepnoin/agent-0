"""
Agent-0 Logger
Simple logging to console + file.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(log_file_path: str = None) -> logging.Logger:
    """Set up Agent-0 logger with console + file output."""
    logger = logging.getLogger("agent0")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter("  [%(name)s] %(message)s")
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # File handler
    if log_file_path:
        log_file = Path(log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger


# Module-level loggers
def get_logger(name: str) -> logging.Logger:
    """Get a child logger."""
    return logging.getLogger(f"agent0.{name}")

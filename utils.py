"""Generic, reusable utility helpers.

Includes helpers for filename sanitization, logging configuration, and
timestamp generation. These are intentionally kept free of any
business-specific logic so they can be reused across modules.
"""

import logging
import re
from datetime import datetime

_INVALID_FILENAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]+")


def sanitize_filename(value: str) -> str:
    """Convert an arbitrary string into a safe, filesystem-friendly filename.

    Spaces and invalid characters are replaced with underscores, and the
    result is lowercased for consistency.

    Args:
        value: The raw string to sanitize (e.g. a business type or query).

    Returns:
        A sanitized string safe to use as part of a filename.

    Example:
        >>> sanitize_filename("Coffee Shops in Karachi!")
        'coffee_shops_in_karachi'
    """
    normalized = value.strip().lower().replace(" ", "_")
    sanitized = _INVALID_FILENAME_CHARS.sub("", normalized)
    return sanitized.strip("_")


def generate_timestamp() -> str:
    """Generate a timestamp string suitable for filenames.

    Returns:
        A timestamp string in the format 'YYYYMMDD_HHMMSS'.

    Example:
        >>> generate_timestamp()
        '20260726_143000'
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger for the application.

    Sets up a basic console handler with a consistent format. Safe to call
    multiple times; will not add duplicate handlers.

    Args:
        level: The logging level to use (default: logging.INFO).

    Returns:
        A configured Logger instance named 'lead_generation_agent'.
    """
    logger = logging.getLogger("lead_generation_agent")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
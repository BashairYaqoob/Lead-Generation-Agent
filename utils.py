"""Generic, reusable utility helpers.

Includes helpers for filename sanitization, logging configuration,
timestamp generation, and a generic retry wrapper. These are intentionally
kept free of any business-specific logic so they can be reused across
modules.
"""

import logging
import re
import time
from datetime import datetime
from typing import Callable, TypeVar

_INVALID_FILENAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]+")

T = TypeVar("T")


def sanitize_filename(value: str) -> str:
    """Convert an arbitrary string into a safe, filesystem-friendly filename.

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
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger for the application.

    Safe to call multiple times; will not add duplicate handlers.

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


def retry(
    operation: Callable[[], T],
    attempts: int = 3,
    wait_ms: int = 800,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Run `operation` and retry it on failure up to `attempts` times.

    Args:
        operation: A zero-argument callable to execute.
        attempts: Maximum number of attempts (including the first one).
        wait_ms: Milliseconds to wait between attempts.
        exceptions: Exception types that should trigger a retry.
        on_retry: Optional callback invoked as `on_retry(attempt_number, exc)`
            after a failed attempt (but before waiting/retrying).

    Returns:
        The return value of `operation` on its first successful attempt.

    Raises:
        The last exception raised by `operation`, if all attempts fail.
    """
    last_exception: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except exceptions as exc:  # noqa: BLE001 - intentional broad retry boundary
            last_exception = exc
            if on_retry is not None:
                on_retry(attempt, exc)
            if attempt < attempts:
                time.sleep(wait_ms / 1000)

    assert last_exception is not None  # for type-checkers; loop always sets it on failure
    raise last_exception
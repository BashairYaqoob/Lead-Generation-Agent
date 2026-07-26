"""Application configuration loaded from environment variables.

Uses python-dotenv to load a .env file (if present) and exposes typed
constants for the rest of the application to import. This centralizes
configuration so no other module needs to call `os.getenv` directly.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(env_var: str, default: bool) -> bool:
    """Parse an environment variable as a boolean.

    Args:
        env_var: Name of the environment variable to read.
        default: Value to use if the variable is unset.

    Returns:
        The parsed boolean value.
    """
    raw_value = os.getenv(env_var)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(env_var: str, default: int) -> int:
    """Parse an environment variable as an integer.

    Args:
        env_var: Name of the environment variable to read.
        default: Value to use if the variable is unset or invalid.

    Returns:
        The parsed integer value.
    """
    raw_value = os.getenv(env_var)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


# LLM configuration (used in a later stage for prompt parsing / extraction).
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none")
API_KEY: str = os.getenv("API_KEY", "")
MODEL: str = os.getenv("MODEL", "")

# Browser automation configuration.
HEADLESS: bool = _get_bool("HEADLESS", True)

# Maximum time (in milliseconds) to wait for browser actions/selectors
# before treating the operation as failed/timed out.
SEARCH_TIMEOUT: int = _get_int("SEARCH_TIMEOUT", 15000)

# Lead collection configuration.
MAX_LEADS: int = _get_int("MAX_LEADS", 20)

# Output configuration.
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")
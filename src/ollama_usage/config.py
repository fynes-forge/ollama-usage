"""Configuration module."""

from typing import Dict


def load_config() -> Dict[str, str]:
    """Load configuration from environment variables."""
    config = {}
    if "APP_ENV" in os.environ:
        config["APP_ENV"] = os.environ["APP_ENV"]
    return config

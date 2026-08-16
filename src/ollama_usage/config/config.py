import os


def load_config() -> dict[str, str]:
    """Load configuration from environment variables."""
    config = {}
    if "APP_ENV" in os.environ:
        config["APP_ENV"] = os.environ["APP_ENV"]
    return config

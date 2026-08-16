from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ollama-usage")
except PackageNotFoundError:
    # Running from source without an install (e.g. `python -m ollama_usage`
    # inside the repo) — there's no installed metadata to read yet.
    __version__ = "0.0.0+unknown"

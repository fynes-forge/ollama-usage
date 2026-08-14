"""Log token usage from local Ollama calls to a JSONL file.

Every non-streamed response from Ollama's /api/generate already includes
prompt/output token counts and durations — this module just makes sure
that data lands somewhere instead of vanishing after each request.

build_entry() and append_entry() are split out from call_and_log() so
the proxy (proxy.py) can log usage from traffic it merely forwards,
without having made the request itself.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_LOG_PATH = Path("~/ollama-usage.jsonl").expanduser()
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"


def build_entry(
    data: dict[str, Any],
    tag: str = "untagged",
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Turn a completed Ollama response (streamed or not) into a log entry."""
    eval_duration = data.get("eval_duration", 0) or 1  # avoid div-by-zero
    return {
        "timestamp": timestamp if timestamp is not None else time.time(),
        "tag": tag,
        "model": data.get("model", ""),
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "output_tokens": data.get("eval_count", 0),
        "eval_duration_s": data.get("eval_duration", 0) / 1e9,
        "tokens_per_second": data.get("eval_count", 0) / (eval_duration / 1e9),
    }


def append_entry(entry: dict[str, Any], log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Append one log entry as a line of JSON."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def call_and_log(
    model: str,
    prompt: str,
    tag: str = "untagged",
    log_path: Path = DEFAULT_LOG_PATH,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> dict[str, Any]:
    """Call Ollama directly, log the resulting token usage, and return the response.

    This is for scripts that call Ollama themselves (the CLI's `log` command,
    a batch job, etc.). If you're using an agent like Cline that talks to
    Ollama on its own, this function never runs — see proxy.py instead.

    Args:
        model: The Ollama model tag to call, e.g. "qwen2.5-coder-agent".
        prompt: The prompt to send.
        tag: A short label for the task this call belongs to (e.g.
            "dependabot-review"). This is what makes the log queryable
            later — tag every call, not just the interesting ones.
        log_path: Where to append the JSONL entry. Defaults to
            ~/ollama-usage.jsonl.
        ollama_url: The Ollama generate endpoint.

    Returns:
        The parsed JSON response from Ollama, unmodified.
    """
    start = time.time()
    resp = requests.post(
        ollama_url,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()

    entry = build_entry(data, tag=tag, timestamp=start)
    append_entry(entry, log_path)

    return data
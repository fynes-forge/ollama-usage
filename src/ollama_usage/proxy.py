from __future__ import annotations

import json
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, request

from ollama_usage.logger import DEFAULT_LOG_PATH, append_entry, build_entry

DEFAULT_TARGET = "http://localhost:11434"

_HOP_BY_HOP_HEADERS = {
    "content-length",
    "transfer-encoding",
    "connection",
    "content-encoding",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ollama_proxy")


def _normalize_openai_chunk(chunk: dict[str, Any]) -> dict[str, Any] | None:
    """Converts OpenAI-style completion usage stats into Ollama format."""
    usage = chunk.get("usage")
    if not usage:
        return None

    return {
        "model": chunk.get("model", "unknown"),
        "done": True,
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": usage.get("completion_tokens", 0),
        "total_duration": chunk.get("total_duration", 0),
        "eval_duration": chunk.get("eval_duration", 0),
    }


def create_app(
    target: str = DEFAULT_TARGET,
    log_path: Path = DEFAULT_LOG_PATH,
    tag: str = "cline",
) -> Flask:
    app = Flask(__name__)

    # Ensure log destination parent folder exists
    log_path = Path(log_path).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    @app.route(
        "/",
        defaults={"path": ""},
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    )
    @app.route(
        "/<path:path>",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    )
    def proxy(path: str) -> Response:
        logger.info(f"Incoming request: {request.method} /{path}")

        try:
            upstream = requests.request(
                method=request.method,
                url=f"{target}/{path}",
                headers={k: v for k, v in request.headers if k.lower() != "host"},
                data=request.get_data(),
                params=request.args,
                stream=True,
                timeout=600,
            )
        except requests.RequestException as err:
            logger.error(f"Failed to connect to target Ollama server ({target}): {err}")
            return Response(f"Proxy upstream error: {err}", status=502)

        def relay() -> Generator[bytes, None, None]:
            accumulated_body = []

            try:
                for line in upstream.iter_lines():
                    if not line:
                        continue

                    yield line + b"\n"
                    accumulated_body.append(line)

                    clean_line = line.decode("utf-8", errors="ignore").strip()
                    if clean_line.startswith("data: "):
                        clean_line = clean_line[6:].strip()

                    if clean_line == "[DONE]":
                        continue

                    try:
                        chunk = json.loads(clean_line)
                    except json.JSONDecodeError:
                        continue

                    # Native Ollama endpoint check
                    if isinstance(chunk, dict) and chunk.get("done") is True:
                        _log_safely(chunk)

                    # OpenAI-compatible /v1/ endpoint check
                    elif isinstance(chunk, dict) and "usage" in chunk:
                        normalized = _normalize_openai_chunk(chunk)
                        if normalized:
                            _log_safely(normalized)

                # Fallback for non-streaming requests
                if accumulated_body and not upstream.headers.get(
                    "content-type", ""
                ).startswith("text/event-stream"):
                    try:
                        full_payload = json.loads(b"".join(accumulated_body))
                        if isinstance(full_payload, dict):
                            if full_payload.get("done") is True:
                                _log_safely(full_payload)
                            elif "usage" in full_payload:
                                normalized = _normalize_openai_chunk(full_payload)
                                if normalized:
                                    _log_safely(normalized)
                    except json.JSONDecodeError:
                        pass

            except Exception as stream_err:  # noqa: BLE001
                logger.error(f"Error during response relay stream: {stream_err}")

        def _log_safely(payload: dict[str, Any]) -> None:
            try:
                entry = build_entry(payload, tag=tag)
                append_entry(entry, log_path)
                logger.info(f"Successfully appended entry to JSONL: {log_path}")
            except Exception:
                logger.exception(f"Failed to append entry to {log_path}")

        headers = [
            (k, v)
            for k, v in upstream.headers.items()
            if k.lower() not in _HOP_BY_HOP_HEADERS
        ]
        return Response(relay(), status=upstream.status_code, headers=headers)

    return app


def run_proxy(
    target: str = DEFAULT_TARGET,
    log_path: Path = DEFAULT_LOG_PATH,
    tag: str = "cline",
    host: str = "0.0.0.0",
    port: int = 11435,
) -> None:
    app = create_app(target=target, log_path=log_path, tag=tag)
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    run_proxy()

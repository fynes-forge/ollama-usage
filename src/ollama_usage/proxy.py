"""A transparent reverse proxy that sits in front of Ollama.

This exists because tools like Cline talk to Ollama's API directly —
they never go through call_and_log(). The only way to capture that
traffic without modifying Cline is to sit between it and Ollama, so
every request passes through this proxy on its way to the real server.

Point the client (Cline's "Ollama Base URL" setting, for example) at
this proxy's address instead of Ollama's. Every response is streamed
back to the client unmodified; usage is logged on the side once each
request completes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, request

from ollama_usage.logger import DEFAULT_LOG_PATH, append_entry, build_entry

DEFAULT_TARGET = "http://localhost:11434"

# Response headers that must not be copied straight through — the proxy's
# own response has different framing (chunked, no upstream content-length).
_HOP_BY_HOP_HEADERS = {
    "content-length",
    "transfer-encoding",
    "connection",
    "content-encoding",
}


def create_app(target: str = DEFAULT_TARGET, log_path: Path = DEFAULT_LOG_PATH, tag: str = "cline") -> Flask:
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def proxy(path: str) -> Response:
        upstream = requests.request(
            method=request.method,
            url=f"{target}/{path}",
            headers={k: v for k, v in request.headers if k.lower() != "host"},
            data=request.get_data(),
            params=request.args,
            stream=True,
            timeout=600,
        )

        def relay() -> Any:
            for line in upstream.iter_lines():
                if not line:
                    continue
                yield line + b"\n"
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("done"):
                    entry = build_entry(chunk, tag=tag)
                    append_entry(entry, log_path)

        headers = [
            (k, v) for k, v in upstream.headers.items()
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
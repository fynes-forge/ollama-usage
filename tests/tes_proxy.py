import json
from unittest.mock import MagicMock, patch

from ollama_usage.proxy import create_app


def _fake_upstream(chunks: list[dict], status: int = 200) -> MagicMock:
    """Build a fake requests.Response-like object streaming NDJSON chunks,
    the same shape Ollama's real streaming API returns."""
    mock_response = MagicMock()
    mock_response.status_code = status
    mock_response.headers = {"Content-Type": "application/x-ndjson"}
    mock_response.iter_lines.return_value = [
        json.dumps(chunk).encode() for chunk in chunks
    ]
    return mock_response


@patch("ollama_usage.proxy.requests.request")
def test_proxy_forwards_response_unchanged(mock_request, tmp_path):
    chunks = [
        {"model": "m", "response": "Hello", "done": False},
        {"model": "m", "response": " world", "done": False},
        {
            "model": "m",
            "response": "",
            "done": True,
            "prompt_eval_count": 42,
            "eval_count": 128,
            "eval_duration": 2_000_000_000,
        },
    ]
    mock_request.return_value = _fake_upstream(chunks)

    log_path = tmp_path / "usage.jsonl"
    app = create_app(target="http://fake-ollama:11434", log_path=log_path, tag="cline")
    client = app.test_client()

    resp = client.post(
        "/api/generate", json={"model": "m", "prompt": "hi", "stream": True}
    )

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Every chunk the fake upstream sent should appear in what the client received.
    for chunk in chunks:
        assert json.dumps(chunk) in body


@patch("ollama_usage.proxy.requests.request")
def test_proxy_logs_exactly_once_per_completed_request(mock_request, tmp_path):
    chunks = [
        {"model": "m", "response": "hi", "done": False},
        {
            "model": "m",
            "response": "",
            "done": True,
            "prompt_eval_count": 42,
            "eval_count": 128,
            "eval_duration": 2_000_000_000,
        },
    ]
    mock_request.return_value = _fake_upstream(chunks)

    log_path = tmp_path / "usage.jsonl"
    app = create_app(target="http://fake-ollama:11434", log_path=log_path, tag="cline")
    client = app.test_client()

    resp = client.post("/api/generate", json={"model": "m", "prompt": "hi"})
    resp.get_data()  # force full consumption of the streamed generator —
    # Flask's test client is lazy and won't otherwise drain it, which is a
    # test-client quirk, not something a real streaming client does.

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tag"] == "cline"
    assert entry["prompt_tokens"] == 42
    assert entry["output_tokens"] == 128


@patch("ollama_usage.proxy.requests.request")
def test_proxy_logs_one_line_per_request_across_a_session(mock_request, tmp_path):
    def make_chunk():
        return {
            "model": "m",
            "response": "",
            "done": True,
            "prompt_eval_count": 1,
            "eval_count": 1,
            "eval_duration": 1_000_000_000,
        }

    log_path = tmp_path / "usage.jsonl"
    app = create_app(target="http://fake-ollama:11434", log_path=log_path, tag="cline")
    client = app.test_client()

    mock_request.return_value = _fake_upstream([make_chunk()])
    client.post("/api/generate", json={"model": "m", "prompt": "first"}).get_data()

    # A fresh mock response per call — iter_lines() on the first mock is
    # already exhausted after being consumed once.
    mock_request.return_value = _fake_upstream([make_chunk()])
    client.post("/api/generate", json={"model": "m", "prompt": "second"}).get_data()

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


@patch("ollama_usage.proxy.requests.request")
def test_proxy_passes_through_non_generate_paths(mock_request, tmp_path):
    # Simulate a GET /api/tags call (Cline listing available models) —
    # no "done" chunk, nothing should be logged, but it should still pass through.
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.iter_lines.return_value = [b'{"models": []}']
    mock_request.return_value = mock_response

    log_path = tmp_path / "usage.jsonl"
    app = create_app(target="http://fake-ollama:11434", log_path=log_path, tag="cline")
    client = app.test_client()

    resp = client.get("/api/tags")
    resp.get_data()

    assert resp.status_code == 200
    assert not log_path.exists()


@patch("ollama_usage.proxy.requests.request")
def test_proxy_forwards_method_and_target_url(mock_request, tmp_path):
    mock_request.return_value = _fake_upstream([{"done": True}])

    log_path = tmp_path / "usage.jsonl"
    app = create_app(target="http://fake-ollama:11434", log_path=log_path, tag="cline")
    client = app.test_client()

    client.post("/api/generate", json={"model": "m"}).get_data()

    mock_request.assert_called_once()
    _, kwargs = mock_request.call_args
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "http://fake-ollama:11434/api/generate"

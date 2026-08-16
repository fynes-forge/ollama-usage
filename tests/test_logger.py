import json
from unittest.mock import MagicMock, patch

import pytest

from ollama_usage.logger import append_entry, build_entry, call_and_log


def test_build_entry_computes_tokens_per_second():
    data = {
        "model": "qwen2.5-coder-agent",
        "prompt_eval_count": 26,
        "eval_count": 290,
        "eval_duration": 4_709_213_000,  # nanoseconds
    }
    entry = build_entry(data, tag="dependabot-review", timestamp=1000.0)

    assert entry["tag"] == "dependabot-review"
    assert entry["model"] == "qwen2.5-coder-agent"
    assert entry["prompt_tokens"] == 26
    assert entry["output_tokens"] == 290
    assert entry["timestamp"] == 1000.0
    assert entry["eval_duration_s"] == pytest.approx(4.709213)
    assert entry["tokens_per_second"] == pytest.approx(290 / 4.709213, rel=1e-3)


def test_build_entry_defaults_timestamp_to_now():
    entry = build_entry({"eval_count": 1, "eval_duration": 1_000_000_000}, tag="x")
    assert isinstance(entry["timestamp"], float)


def test_build_entry_handles_zero_eval_duration_without_crashing():
    # A real Ollama response should never have eval_duration=0, but the
    # fallback (`or 1`) exists specifically so a malformed one can't crash
    # the caller with a ZeroDivisionError.
    entry = build_entry({"eval_duration": 0, "eval_count": 5}, tag="x")
    assert entry["tokens_per_second"] > 0


def test_append_entry_writes_one_jsonl_line_per_call(tmp_path):
    log_path = tmp_path / "usage.jsonl"
    entry = {"tag": "test", "output_tokens": 10}

    append_entry(entry, log_path=log_path)
    append_entry(entry, log_path=log_path)

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == entry


def test_append_entry_creates_parent_directories(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "usage.jsonl"
    append_entry({"a": 1}, log_path=log_path)
    assert log_path.exists()


@patch("ollama_usage.logger.requests.post")
def test_call_and_log_sends_stream_false_and_returns_response(mock_post, tmp_path):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "model": "qwen2.5-coder-agent",
        "response": "hello",
        "prompt_eval_count": 10,
        "eval_count": 20,
        "eval_duration": 1_000_000_000,
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    log_path = tmp_path / "usage.jsonl"
    data = call_and_log(model="m", prompt="p", tag="t", log_path=log_path)

    assert data["response"] == "hello"

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"model": "m", "prompt": "p", "stream": False}

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tag"] == "t"
    assert entry["output_tokens"] == 20


@patch("ollama_usage.logger.requests.post")
def test_call_and_log_raises_on_http_error(mock_post, tmp_path):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")
    mock_post.return_value = mock_response

    log_path = tmp_path / "usage.jsonl"
    with pytest.raises(Exception, match="HTTP 500"):
        call_and_log(model="m", prompt="p", log_path=log_path)

    # A failed call should not produce a log entry.
    assert not log_path.exists()

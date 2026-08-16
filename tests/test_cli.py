import json
from unittest.mock import MagicMock, patch

import pytest

from ollama_usage.cli import app

typer_testing = pytest.importorskip("typer.testing")


runner = typer_testing.CliRunner()


def test_version_flag_prints_version_and_exits_cleanly():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ollama-usage" in result.stdout


def test_log_command_writes_entry_and_prints_response(tmp_path):
    log_path = tmp_path / "usage.jsonl"
    fake_response = {
        "model": "m",
        "response": "hello",
        "prompt_eval_count": 5,
        "eval_count": 10,
        "eval_duration": 1_000_000_000,
    }
    with patch("ollama_usage.logger.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = runner.invoke(
            app,
            [
                "--log-path",
                str(log_path),
                "log",
                "--model",
                "m",
                "--prompt",
                "hi",
                "--tag",
                "test",
            ],
        )

    assert result.exit_code == 0
    assert "hello" in result.stdout

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tag"] == "test"


def test_log_command_warns_when_context_budget_is_tight(tmp_path):
    log_path = tmp_path / "usage.jsonl"
    fake_response = {
        "model": "m",
        "response": "hello",
        "prompt_eval_count": 9500,
        "eval_count": 10,
        "eval_duration": 1_000_000_000,
    }
    with patch("ollama_usage.logger.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = runner.invoke(
            app,
            [
                "--log-path",
                str(log_path),
                "log",
                "--model",
                "m",
                "--prompt",
                "hi",
                "--num-ctx",
                "10000",
            ],
        )

    assert "Context at" in result.stdout


def test_report_command_runs_without_error_on_a_populated_log(tmp_path):
    log_path = tmp_path / "usage.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "timestamp": 1,
                "tag": "a",
                "model": "m",
                "prompt_tokens": 1,
                "output_tokens": 1,
                "eval_duration_s": 0.1,
                "tokens_per_second": 10.0,
            }
        )
        + "\n"
    )
    result = runner.invoke(app, ["--log-path", str(log_path), "report"])
    assert result.exit_code == 0

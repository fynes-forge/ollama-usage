import json

import pytest

from ollama_usage.report import summary

duckdb = pytest.importorskip("duckdb")


def _write_log(tmp_path, entries):
    log_path = tmp_path / "usage.jsonl"
    with log_path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return log_path


def test_summary_groups_by_tag_and_sums_tokens(tmp_path):
    entries = [
        {
            "timestamp": 1,
            "tag": "a",
            "model": "m",
            "prompt_tokens": 10,
            "output_tokens": 20,
            "eval_duration_s": 1.0,
            "tokens_per_second": 20.0,
        },
        {
            "timestamp": 2,
            "tag": "a",
            "model": "m",
            "prompt_tokens": 5,
            "output_tokens": 5,
            "eval_duration_s": 0.5,
            "tokens_per_second": 10.0,
        },
        {
            "timestamp": 3,
            "tag": "b",
            "model": "m",
            "prompt_tokens": 1,
            "output_tokens": 1,
            "eval_duration_s": 0.1,
            "tokens_per_second": 10.0,
        },
    ]
    log_path = _write_log(tmp_path, entries)

    result = summary(log_path=log_path).df()

    row_a = result[result["tag"] == "a"].iloc[0]
    assert row_a["calls"] == 2
    assert row_a["total_tokens"] == 40  # (10+20) + (5+5)
    assert row_a["avg_tps"] == pytest.approx(15.0)

    row_b = result[result["tag"] == "b"].iloc[0]
    assert row_b["calls"] == 1
    assert row_b["total_tokens"] == 2


def test_summary_sorts_by_total_tokens_descending(tmp_path):
    entries = [
        {
            "timestamp": 1,
            "tag": "small",
            "model": "m",
            "prompt_tokens": 1,
            "output_tokens": 1,
            "eval_duration_s": 0.1,
            "tokens_per_second": 10.0,
        },
        {
            "timestamp": 2,
            "tag": "big",
            "model": "m",
            "prompt_tokens": 1000,
            "output_tokens": 2000,
            "eval_duration_s": 10.0,
            "tokens_per_second": 200.0,
        },
    ]
    log_path = _write_log(tmp_path, entries)

    result = summary(log_path=log_path).df()

    assert result.iloc[0]["tag"] == "big"
    assert result.iloc[-1]["tag"] == "small"

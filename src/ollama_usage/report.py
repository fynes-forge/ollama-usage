from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from ollama_usage.logger import DEFAULT_LOG_PATH


def summary(log_path: Path = DEFAULT_LOG_PATH) -> duckdb.DuckDBPyRelation:
    """Return a per-tag summary: call count, total tokens, average tok/s."""
    return duckdb.sql(f"""
        SELECT
            tag,
            count(*) AS calls,
            sum(prompt_tokens + output_tokens) AS total_tokens,
            round(avg(tokens_per_second), 1) AS avg_tps
        FROM read_json_auto('{log_path}')
        GROUP BY tag
        ORDER BY total_tokens DESC
    """)


def plot_report(
    log_path: Path = DEFAULT_LOG_PATH, show: bool = True
) -> Any:
    """Plot tokens-per-second over time, to spot thermal throttling."""
    import matplotlib.pyplot as plt

    df = duckdb.sql(f"""
        SELECT to_timestamp(timestamp) AS ts, tokens_per_second
        FROM read_json_auto('{log_path}')
        ORDER BY ts
    """).df()

    ax = df.plot(
        x="ts", y="tokens_per_second", title="Generation speed over time"
    )
    ax.set_xlabel("Time")
    ax.set_ylabel("Tokens / second")
    if show:
        plt.show()
    return ax

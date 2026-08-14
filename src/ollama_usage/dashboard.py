"""Streamlit dashboard for ollama-usage.

Run directly:
    uv run streamlit run src/ollama_usage/dashboard.py

Or via the CLI wrapper, which also binds it to 0.0.0.0 so other devices
on your network can reach it:
    uv run ollama-usage dashboard
"""

from __future__ import annotations

import duckdb
import pandas as pd
import streamlit as st

from ollama_usage.logger import DEFAULT_LOG_PATH

st.set_page_config(page_title="Ollama Usage", page_icon="🦙", layout="wide")
st.title("🦙 Ollama Usage Dashboard")

log_path = st.sidebar.text_input("Log file", str(DEFAULT_LOG_PATH))
st.sidebar.caption("Reload the page after logging new calls — this reads the file fresh each run.")

try:
    df = duckdb.sql(f"SELECT * FROM read_json_auto('{log_path}')").df()
except Exception:
    st.warning(f"No usage data found yet at `{log_path}`. Run `ollama-usage log` first.")
    st.stop()

if df.empty:
    st.info("Log file exists but has no entries yet.")
    st.stop()

df["ts"] = pd.to_datetime(df["timestamp"], unit="s")

# ── Top-line metrics ─────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total requests", len(df))
col2.metric("Total tokens", int((df["prompt_tokens"] + df["output_tokens"]).sum()))
col3.metric("Avg tokens/sec", round(df["tokens_per_second"].mean(), 1))
col4.metric("Distinct tags", df["tag"].nunique())

# ── Usage by tag ──────────────────────────────────────────────────────────────
st.subheader("Usage by tag")
df["total_tokens"] = df["prompt_tokens"] + df["output_tokens"]
by_tag = (
    df.groupby("tag")
    .agg(
        calls=("tag", "count"),
        total_tokens=("total_tokens", "sum"),
        avg_tps=("tokens_per_second", "mean"),
    )
    .sort_values("total_tokens", ascending=False)
)
by_tag["avg_tps"] = by_tag["avg_tps"].round(1)
st.dataframe(by_tag, use_container_width=True)

# ── Time series ───────────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Tokens/sec over time")
    st.line_chart(df.set_index("ts")["tokens_per_second"])

with right:
    st.subheader("Requests per day")
    per_day = df.set_index("ts").resample("D").size()
    st.bar_chart(per_day)

st.subheader("Raw log")
st.dataframe(df.sort_values("ts", ascending=False), use_container_width=True)
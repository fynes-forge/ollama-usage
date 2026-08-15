"""Streamlit dashboard for ollama-usage, styled to the Fynes Forge brand.

Run directly:
    uv run streamlit run src/ollama_usage/dashboard.py

Or via the CLI wrapper, which also binds it to 0.0.0.0 so other devices
on your network can reach it:
    uv run ollama-usage dashboard
"""

from __future__ import annotations

from datetime import datetime

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ollama_usage.branding import (
    BG,
    BG_DEEP,
    CYAN,
    DEEP_LAVENDER,
    DEEP_PINK,
    GOLD,
    LAVENDER,
    PINK,
    STEEL_BLUE,
)
from ollama_usage.logger import DEFAULT_LOG_PATH

FONT_DISPLAY = "'Cinzel', serif"
FONT_BODY = "'Rajdhani', sans-serif"
FONT_MONO = "'JetBrains Mono', monospace"

# Tag pill colours, cycled deterministically per tag name.
_TAG_PALETTE = [
    (f"rgba(221,117,150,0.18)", DEEP_PINK),   # t-pink
    (f"rgba(99,197,234,0.12)", CYAN),          # t-cyan
    (f"rgba(236,218,144,0.12)", GOLD),         # t-gold
    (f"rgba(159,126,190,0.18)", DEEP_LAVENDER),  # t-lav
]

# The Fynes Forge mark, straight from the brand pack — scaled down for the header.
_LOGO_SVG = """
<svg viewBox="0 0 86 86" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:34px;height:34px">
  <rect x="8" y="8" width="70" height="70" rx="4" fill="#1C2329"/>
  <rect x="18" y="18" width="9" height="50" fill="#B7C3F3"/>
  <rect x="18" y="18" width="50" height="9" fill="#B7C3F3"/>
  <rect x="18" y="38" width="37" height="7" fill="#ECDA90"/>
  <polygon points="59,18 68,18 68,27" fill="#DD7596"/>
  <polygon points="59,18 68,27 59,27" fill="#1C2329"/>
  <rect x="18" y="68" width="50" height="2" fill="#63C5EA" opacity="0.55"/>
  <rect x="66" y="29" width="2" height="39" fill="#9F7EBE" opacity="0.45"/>
  <rect x="8"  y="8"  width="7" height="2" fill="#ECDA90"/>
  <rect x="8"  y="8"  width="2" height="7" fill="#ECDA90"/>
  <rect x="71" y="76" width="7" height="2" fill="#DD7596"/>
  <rect x="75" y="72" width="2" height="6" fill="#DD7596"/>
</svg>
"""


def _clean_html(html: str) -> str:
    """Strip leading whitespace from every line so Markdown won't treat indented HTML as code blocks."""
    return "\n".join(line.strip() for line in html.splitlines())


def _inject_css() -> None:
    st.markdown(
        _clean_html(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;700&display=swap');

        html, body, [class*="css"] {{
            font-family: {FONT_BODY};
        }}

        [data-testid="stAppViewContainer"] {{
            background: {BG};
        }}
        [data-testid="stHeader"] {{
            background: transparent;
        }}
        [data-testid="stSidebar"] {{
            background: {BG_DEEP};
            border-right: 1px solid rgba(79,98,114,0.25);
        }}
        #MainMenu, footer {{ visibility: hidden; }}

        h1, h2, h3 {{
            font-family: {FONT_DISPLAY} !important;
            letter-spacing: 0.04em;
            color: {LAVENDER} !important;
        }}

        /* ── Header bar ── */
        .ff-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 0 28px;
            border-bottom: 1px solid rgba(79,98,114,0.25);
            margin-bottom: 36px;
        }}
        .ff-header-left {{ display: flex; align-items: center; gap: 14px; }}
        .ff-title {{
            font-family: {FONT_DISPLAY};
            font-weight: 700;
            font-size: 20px;
            letter-spacing: 0.12em;
            color: {LAVENDER};
        }}
        .ff-title span {{ color: {GOLD}; }}
        .ff-badge {{
            font-family: {FONT_MONO};
            font-size: 10px;
            letter-spacing: 0.15em;
            color: {GOLD};
            border: 1px solid rgba(236,218,144,0.4);
            padding: 4px 12px 4px 10px;
            clip-path: polygon(6px 0%, 100% 0%, calc(100% - 6px) 100%, 0% 100%);
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .ff-dot {{
            width: 6px; height: 6px; border-radius: 50%;
            background: {CYAN};
            box-shadow: 0 0 6px {CYAN};
        }}
        .ff-timestamp {{
            font-family: {FONT_MONO};
            font-size: 10px;
            color: {STEEL_BLUE};
            letter-spacing: 0.1em;
        }}

        /* ── Section labels ── */
        .ff-section-label {{
            font-family: {FONT_MONO};
            font-size: 10px;
            letter-spacing: 0.35em;
            text-transform: uppercase;
            color: {STEEL_BLUE};
            display: flex;
            align-items: center;
            gap: 16px;
            margin: 40px 0 20px;
        }}
        .ff-section-label::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(79,98,114,0.3);
        }}

        /* ── KPI cards ── */
        .ff-kpi-row {{ display: flex; gap: 10px; }}
        .ff-kpi {{
            flex: 1;
            background: {BG_DEEP};
            border-radius: 3px;
            padding: 20px 22px;
            border-left: 3px solid var(--accent);
        }}
        .ff-kpi-label {{
            font-family: {FONT_MONO};
            font-size: 9px;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            color: {STEEL_BLUE};
            margin-bottom: 10px;
        }}
        .ff-kpi-value {{
            font-family: {FONT_DISPLAY};
            font-weight: 700;
            font-size: 32px;
            color: var(--accent);
            line-height: 1;
        }}

        /* ── Tag table ── */
        .ff-table {{ width: 100%; border-collapse: collapse; font-family: {FONT_MONO}; font-size: 12.5px; }}
        .ff-table th {{
            text-align: left;
            font-family: {FONT_MONO};
            font-size: 9px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: {STEEL_BLUE};
            padding: 0 16px 10px 0;
            border-bottom: 1px solid rgba(79,98,114,0.35);
        }}
        .ff-table td {{
            padding: 12px 16px 12px 0;
            border-bottom: 1px solid rgba(79,98,114,0.15);
            color: {LAVENDER};
        }}
        .ff-tag-pill {{
            font-family: {FONT_BODY};
            font-weight: 600;
            font-size: 11px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 1px;
        }}

        .ff-footer {{
            margin-top: 48px;
            padding-top: 20px;
            border-top: 1px solid rgba(79,98,114,0.25);
            font-family: {FONT_MONO};
            font-size: 10px;
            color: {STEEL_BLUE};
            letter-spacing: 0.12em;
        }}
        </style>
        """),
        unsafe_allow_html=True,
    )


def _tag_style(tag: str) -> tuple[str, str]:
    idx = sum(ord(c) for c in tag) % len(_TAG_PALETTE)
    return _TAG_PALETTE[idx]


def _kpi_card(label: str, value: str, accent: str) -> str:
    return _clean_html(f"""
        <div class="ff-kpi" style="--accent: {accent}">
            <div class="ff-kpi-label">{label}</div>
            <div class="ff-kpi-value">{value}</div>
        </div>
    """)


def _table_html(by_tag: pd.DataFrame) -> str:
    rows = ""
    for tag, row in by_tag.iterrows():
        bg, fg = _tag_style(str(tag))
        rows += f"""
            <tr>
                <td><span class="ff-tag-pill" style="background:{bg}; color:{fg}">{tag}</span></td>
                <td>{int(row['calls'])}</td>
                <td>{int(row['total_tokens']):,}</td>
                <td>{row['avg_tps']:.1f}</td>
            </tr>
        """
    return _clean_html(f"""
        <table class="ff-table">
            <thead>
                <tr><th>Tag</th><th>Calls</th><th>Total Tokens</th><th>Avg Tok/s</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    """)


def _themed_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(
            family=FONT_MONO, size=12, color=STEEL_BLUE)),
        plot_bgcolor=BG_DEEP,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_MONO, color=LAVENDER, size=11),
        margin=dict(l=40, r=20, t=40, b=30),
        xaxis=dict(gridcolor="rgba(79,98,114,0.15)",
                   linecolor=STEEL_BLUE, zeroline=False),
        yaxis=dict(gridcolor="rgba(79,98,114,0.15)",
                   linecolor=STEEL_BLUE, zeroline=False),
        showlegend=False,
        height=320,
    )
    return fig


def _tps_line_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["tokens_per_second"],
            mode="lines+markers",
            line=dict(color=GOLD, width=2),
            marker=dict(color=CYAN, size=5),
            fill="tozeroy",
            fillcolor="rgba(236,218,144,0.08)",
        )
    )
    return _themed_layout(fig, "TOKENS / SECOND OVER TIME")


def _requests_bar_chart(per_day: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=per_day.index,
            y=per_day.values,
            marker=dict(color=LAVENDER, line=dict(
                color=DEEP_LAVENDER, width=1)),
        )
    )
    return _themed_layout(fig, "REQUESTS PER DAY")


def main() -> None:
    st.set_page_config(page_title="Ollama Usage — Fynes Forge",
                       page_icon="🔥", layout="wide")
    _inject_css()

    st.markdown(
        _clean_html(f"""
            <div class="ff-header">
                <div class="ff-header-left">
                    {_LOGO_SVG}
                    <div class="ff-title">FYNES FORGE <span>· OLLAMA USAGE</span></div>
                </div>
                <div style="display:flex; align-items:center; gap:16px;">
                    <span class="ff-timestamp">LOADED {datetime.now().strftime('%H:%M:%S')}</span>
                    <span class="ff-badge"><span class="ff-dot"></span>LOCAL · NO CLOUD</span>
                </div>
            </div>
        """),
        unsafe_allow_html=True,
    )

    log_path = st.sidebar.text_input("Log file", str(DEFAULT_LOG_PATH))
    st.sidebar.caption(
        "Reload the page after logging new calls — this reads the file fresh each run.")

    try:
        df = duckdb.sql(f"SELECT * FROM read_json_auto('{log_path}')").df()
    except Exception:
        st.warning(
            f"No usage data found yet at `{log_path}`. Run `ollama-usage log` first.")
        st.stop()

    if df.empty:
        st.info("Log file exists but has no entries yet.")
        st.stop()

    df["ts"] = pd.to_datetime(df["timestamp"], unit="s")
    df["total_tokens"] = df["prompt_tokens"] + df["output_tokens"]

    # ── 01 Overview ──────────────────────────────────────────────────────
    st.markdown('<div class="ff-section-label">01 — OVERVIEW</div>',
                unsafe_allow_html=True)
    cards = "".join([
        _kpi_card("Total Requests", f"{len(df):,}", CYAN),
        _kpi_card("Total Tokens", f"{int(df['total_tokens'].sum()):,}", GOLD),
        _kpi_card("Avg Tokens/Sec",
                  f"{df['tokens_per_second'].mean():.1f}", PINK),
        _kpi_card("Distinct Tags", f"{df['tag'].nunique()}", DEEP_LAVENDER),
    ])
    st.markdown(
        _clean_html(f'<div class="ff-kpi-row">{cards}</div>'),
        unsafe_allow_html=True,
    )

    # ── 02 Usage by tag ──────────────────────────────────────────────────
    st.markdown('<div class="ff-section-label">02 — USAGE BY TAG</div>',
                unsafe_allow_html=True)
    by_tag = (
        df.groupby("tag")
        .agg(calls=("tag", "count"), total_tokens=("total_tokens", "sum"), avg_tps=("tokens_per_second", "mean"))
        .sort_values("total_tokens", ascending=False)
    )
    st.markdown(_table_html(by_tag), unsafe_allow_html=True)

    # ── 03 Charts ────────────────────────────────────────────────────────
    st.markdown('<div class="ff-section-label">03 — OVER TIME</div>',
                unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_tps_line_chart(
            df), use_container_width=True, theme=None)
    with right:
        per_day = df.set_index("ts").resample("D").size()
        st.plotly_chart(_requests_bar_chart(per_day),
                        use_container_width=True, theme=None)

    # ── 04 Raw log ───────────────────────────────────────────────────────
    with st.expander("04 — RAW LOG"):
        st.dataframe(df.sort_values("ts", ascending=False),
                     use_container_width=True)

    st.markdown(
        '<div class="ff-footer">ollama-usage · local, no cloud · fynesforge.dev</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

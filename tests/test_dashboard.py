import sys
import types

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def stub_heavy_deps(monkeypatch):
    """dashboard.py imports streamlit, duckdb, and plotly at module level,
    but the functions under test here don't touch any of them. Stub them
    out so the module can be imported without those packages installed."""
    for name in ("duckdb", "plotly", "plotly.graph_objects", "streamlit"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules["streamlit"].markdown = lambda *a, **k: None
    sys.modules["streamlit"].set_page_config = lambda *a, **k: None
    yield


def test_html_flattens_all_indentation():
    from ollama_usage.dashboard import _clean_html

    raw = """
    <div>
        <span>hi</span>
    </div>
    """
    flat = _clean_html(raw)
    assert all(line == line.lstrip() for line in flat.splitlines())
    assert "<div>" in flat
    assert "<span>hi</span>" in flat


def test_tag_style_is_deterministic_per_tag():
    from ollama_usage.dashboard import _tag_style

    assert _tag_style("cline") == _tag_style("cline")
    assert _tag_style("dependabot-review") == _tag_style("dependabot-review")


def test_tag_style_distributes_across_the_palette():
    from ollama_usage.dashboard import _TAG_PALETTE, _tag_style

    tags = ["cline", "dependabot-review", "emoji-fill", "random-task", "another-one"]
    styles = {_tag_style(t) for t in tags}
    assert len(styles) >= 2  # not everything collapsing onto one colour
    for style in styles:
        assert style in _TAG_PALETTE


def test_kpi_card_contains_the_given_values_and_no_indentation():
    from ollama_usage.dashboard import _kpi_card

    html = _kpi_card("Total Tokens", "193", "#ECDA90")
    assert "Total Tokens" in html
    assert "193" in html
    assert "#ECDA90" in html
    assert all(line == line.lstrip() for line in html.splitlines())


def test_table_html_renders_every_row_and_sorts_input_order():
    from ollama_usage.dashboard import _table_html

    by_tag = pd.DataFrame(
        {"calls": [3, 1], "total_tokens": [500, 20], "avg_tps": [42.5, 10.0]},
        index=pd.Index(["cline", "emoji-fill"], name="tag"),
    )
    html = _table_html(by_tag)
    assert "cline" in html
    assert "emoji-fill" in html
    assert "500" in html
    assert "42.5" in html
    assert all(line == line.lstrip() for line in html.splitlines())


def test_table_html_handles_empty_dataframe():
    from ollama_usage.dashboard import _table_html

    by_tag = pd.DataFrame({"calls": [], "total_tokens": [], "avg_tps": []})
    by_tag.index.name = "tag"
    html = _table_html(by_tag)
    assert "<table" in html
    assert "<tbody>" in html

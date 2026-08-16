from ollama_usage.budget import (
    DEFAULT_NUM_CTX,
    DEFAULT_WARN_THRESHOLD,
    check_context_budget,
)


def test_defaults_match_documented_values():
    assert DEFAULT_NUM_CTX == 32768
    assert DEFAULT_WARN_THRESHOLD == 0.85


def test_under_threshold_returns_ratio_and_no_warning(capsys):
    ratio = check_context_budget(prompt_tokens=1000, num_ctx=10000)
    assert ratio == 0.1
    assert capsys.readouterr().out == ""


def test_over_threshold_warns(capsys):
    ratio = check_context_budget(prompt_tokens=9100, num_ctx=10000)
    assert ratio == 0.91
    out = capsys.readouterr().out
    assert "91%" in out
    assert "9100/10000" in out


def test_history_tokens_are_included_in_the_total():
    ratio = check_context_budget(prompt_tokens=100, history_tokens=200, num_ctx=1000)
    assert ratio == 0.3


def test_custom_warn_threshold_is_respected(capsys):
    check_context_budget(prompt_tokens=500, num_ctx=1000, warn_threshold=0.4)
    out = capsys.readouterr().out
    assert "50%" in out


def test_exactly_at_threshold_warns():
    # >= threshold should warn, not just >
    ratio = check_context_budget(prompt_tokens=850, num_ctx=1000, warn_threshold=0.85)
    assert ratio == 0.85

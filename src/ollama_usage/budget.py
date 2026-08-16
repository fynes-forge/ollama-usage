from __future__ import annotations

DEFAULT_NUM_CTX = 32768  # match whatever num_ctx your Modelfile sets
DEFAULT_WARN_THRESHOLD = 0.85


def check_context_budget(
    prompt_tokens: int,
    history_tokens: int = 0,
    num_ctx: int = DEFAULT_NUM_CTX,
    warn_threshold: float = DEFAULT_WARN_THRESHOLD,
) -> float:
    """Return the fraction of the context window in use, warning if high.

    Args:
        prompt_tokens: Tokens in the current prompt (e.g. prompt_eval_count
            from the Ollama response).
        history_tokens: Tokens already consumed by prior turns in the
            conversation, if tracking a multi-turn session.
        num_ctx: The context window size configured for the model.
        warn_threshold: Fraction of num_ctx at which to print a warning.

    Returns:
        The usage ratio, e.g. 0.91 for 91% of the context window used.
    """
    used = prompt_tokens + history_tokens
    ratio = used / num_ctx
    if ratio >= warn_threshold:
        print(f"⚠️  Context at {ratio:.0%} of budget ({used}/{num_ctx} tokens)")
    return ratio

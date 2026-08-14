# ollama-usage

> **Fynes Forge** · Official repository template. Replace this line with a one-sentence description of what this repo does.

---

<div align="center">

![Status](https://img.shields.io/badge/status-active-63C5EA?style=flat-square&labelColor=404E5C)
![License](https://img.shields.io/badge/license-MIT-9F7EBE?style=flat-square&labelColor=404E5C)
![Org](https://img.shields.io/badge/org-fynes--forge-ECDA90?style=flat-square&labelColor=404E5C)

</div>

---

## Overview

<!-- 
Log, budget, and visualise token usage for local Ollama models.

Ollama's API already returns prompt/output token counts and timings on
every response — this project makes sure that data lands somewhere
instead of vanishing after each request, warns you before it collides
with your context window, and gives you a network-reachable dashboard
to actually look at it.

Companion code for [fynesforge.dev/blog](https://fynesforge.dev/blog) —
see the post for the full write-up.
 -->

This is a Fynes Forge project built with **precision over cleverness**.

---

## Getting Started

```bash
git clone https://github.com/fynes-forge/ollama-usage.git
cd ollama-usage
uv sync
```

That's it — `uv` resolves every dependency from `pyproject.toml`, no
manual pip installs, no virtualenv to remember to activate.

## Use

**Log a call and check it against your context budget:**

```bash
uv run ollama-usage log \
  --model qwen2.5-coder-agent \
  --prompt "Summarise breaking changes in go_router 14 to 17." \
  --tag dependabot-review
```

Every call appends one line to `~/ollama-usage.jsonl`. If the prompt is
eating into your model's context window, you'll see a warning before
Ollama silently starts dropping tokens:

```
⚠️  Context at 91% of budget (29820/32768 tokens)
```

Adjust `--num-ctx` to match whatever `num_ctx` your Modelfile sets.

**Launch the dashboard:**

```bash
uv run ollama-usage dashboard
```

Starts a Streamlit app bound to `0.0.0.0:8501` by default — reachable
from any device on your network, not just the machine running it. Pass
`--host 127.0.0.1` to keep it local-only, or `--port` to change the port.

The dashboard shows total requests, total tokens, average tokens/sec,
a breakdown by tag, tokens/sec over time, and requests per day.

**Or work from the terminal instead:**

```bash
uv run ollama-usage report   # per-tag summary table
uv run ollama-usage plot     # tokens/sec over time, matplotlib window
```

---

## Use it as a library

```python
from ollama_usage.logger import call_and_log
from ollama_usage.budget import check_context_budget

resp = call_and_log(model="qwen2.5-coder-agent", prompt=my_prompt, tag="my-task")
check_context_budget(resp["prompt_eval_count"], num_ctx=32768)
```

---

## Documentation

| Document | Description |
|---|---|
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute to this project |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and release notes |
| [AGENTS.md](./AGENTS.md) | AI agent context and conventions |

---

## Project Structure

```
<repo-name>/
├── .github/
│   ├── workflows/          ← CI/CD pipelines
│   ├── ISSUE_TEMPLATE/     ← Bug reports, feature requests
│   ├── PULL_REQUEST_TEMPLATE/
│   └── copilot/            ← GitHub Copilot instructions
├── docs/                   ← Documentation
src/ollama_usage/
     ├── logger.py      # call_and_log() — call Ollama, append usage to JSONL
     ├── budget.py       # check_context_budget() — warn before context overflow
     ├── report.py       # summary() and plot() — query the log with DuckDB
     ├── dashboard.py     # Streamlit dashboard
     └── cli.py           # `ollama-usage log|report|plot|dashboard`
├── tests/                  ← Test suite
├── AGENTS.md               ← AI agent conventions
├── CONTRIBUTING.md         ← Contribution guide
├── CHANGELOG.md            ← Release history
└── README.md               ← This file
```

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening a PR.

---

## Licence

MIT © [Fynes Forge](https://github.com/fynes-forge) — see [LICENSE](./LICENSE) for details.

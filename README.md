# ollama-usage

> **ollama-usage** · Log, budget, and visualise token usage for local Ollama models.

---

<div align="center">

![Status](https://img.shields.io/badge/status-active-63C5EA?style=flat-square&labelColor=404E5C)
![License](https://img.shields.io/badge/license-MIT-9F7EBE?style=flat-square&labelColor=404E5C)
![Org](https://img.shields.io/badge/org-fynes--forge-ECDA90?style=flat-square&labelColor=404E5C)

</div>

---

## Overview

Ollama's API already returns prompt/output token counts and timings on
every response — this project makes sure that data lands somewhere
instead of vanishing after each request, warns you before it collides
with your context window, and gives you a network-reachable dashboard
to actually look at it.

Companion code for [fynesforge.dev/blog](https://fynesforge.dev/blog) —
see the post for the full write-up.


This is a Fynes Forge project built with **precision over cleverness**.

---

## Getting Started

**Clone and run:**
 
```bash
git clone https://github.com/fynes-forge/ollama-usage.git
cd ollama-usage
uv sync
```
 
**Or install a released version directly, no clone needed** — every
[release](https://github.com/fynes-forge/ollama-usage/releases) has a
wheel attached:
 
```bash
uv tool install ollama-usage --from https://github.com/fynes-forge/ollama-usage/releases/download/v0.1.0/ollama_usage-0.1.0-py3-none-any.whl
```
 
`uv tool install` puts the `ollama-usage` command on your PATH in its
own isolated environment — no virtualenv to manage, and it doesn't
touch any other project's dependencies. Swap `uv tool install` for
`pip install` if you'd rather it land in your current environment.
Check the release's `SHA256SUMS.txt` if you want to verify the download.

## Development
 
Common dev commands are wrapped in a `Makefile` — run `make help` to
list them:
 
```bash
make sync       # install everything, runtime + dev deps
make check      # lint, format-check, typecheck, test — same as CI
make test-cov   # tests with a coverage report
make dashboard
make proxy
```
 
These are just short aliases for the equivalent `uv run ...` commands
shown throughout this README — use whichever you prefer.

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

**Tracking Cline (or any client that talks to Ollama directly):**

`ollama-usage log` only logs calls it makes itself. Cline talks to
Ollama's API on its own — it never goes through this tool — so nothing
above captures it. Fix that with the proxy:

```bash
uv run ollama-usage proxy
```

This starts a transparent proxy on `:11435` that forwards every request
to your real Ollama server and logs the token usage on the way through,
without changing the response. Point Cline's **Ollama Base URL** setting
at `http://localhost:11435` instead of `http://localhost:11434`, and its
traffic gets logged like everything else.

Two things worth knowing before you rely on this:

- Every request through one proxy instance shares one `--tag` (`cline`
  by default), since the proxy has no way to know what task Cline is
  actually working on. If you want that level of granularity, restart
  the proxy with a different `--tag` per work session.
- Only traffic that's actually routed through the proxy gets logged.
  Anything still pointed at `:11434` directly — Jan, a `curl` command,
  another tool — stays invisible to this log.

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
ollama-usage/
├── .github/
│   ├── workflows/          ← CI/CD pipelines
│   ├── ISSUE_TEMPLATE/     ← Bug reports, feature requests
│   ├── PULL_REQUEST_TEMPLATE/
│   └── copilot/            ← GitHub Copilot instructions
├── docs/                   ← Documentation
src/ollama_usage/
    |
    ├── config/
        ├── __init__.py
        ├── branding.py    # shared brand colour tokens
        └── config.py      # load_config() — read env vars into a dict
    ├── __init__.py
    ├── logger.py      # call_and_log() — call Ollama, append usage to JSONL
    ├── budget.py      # check_context_budget() — warn before context overflow
    ├── proxy.py       # transparent proxy — captures Cline/other direct clients
    ├── report.py      # summary() and plot() — query the log with DuckDB
    ├── dashboard.py   # Streamlit dashboard
    └── cli.py         # `ollama-usage log|report|plot|dashboard|proxy`
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

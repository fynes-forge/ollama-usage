# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---


## [Unreleased]

## [0.1.0] - 2026-08-14

### Added

- `ollama-usage log` — call Ollama, log token usage to a JSONL file, and warn if the prompt is close to the model's context limit.
- `ollama-usage report` / `ollama-usage plot` — DuckDB-backed usage summary and a tokens/sec-over-time chart.
- `ollama-usage dashboard` — Streamlit dashboard bindable to the local network, showing totals, per-tag breakdown, and usage over time.
- `ollama-usage proxy` — transparent reverse proxy that captures usage from clients (e.g. Cline) that talk to Ollama directly rather than through this tool.

---
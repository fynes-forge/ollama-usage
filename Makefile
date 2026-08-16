.DEFAULT_GOAL := help

.PHONY: help sync lint format format-check typecheck test test-cov \
        check run-dashboard run-proxy build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

sync: ## Install/sync all dependencies (runtime + dev)
	@uv sync

lint: ## Run the Ruff linter
	@uv run ruff check .

format: ## Auto-format the codebase with Ruff
	@uv run ruff format .

format-check: ## Check formatting without changing files (what CI runs)
	@uv run ruff format --check .

typecheck: ## Run mypy against src/
	@uv run mypy src/

test: ## Run the test suite
	@uv run pytest

test-cov: ## Run the test suite with coverage report
	@uv run pytest --cov=src --cov-report=term-missing --cov-report=xml

check: lint format-check typecheck test ## Run everything CI runs, locally

dashboard: ## Launch the Streamlit dashboard
	@uv run ollama-usage dashboard

proxy: ## Launch the Cline-capturing reverse proxy
	@uv run ollama-usage proxy

build: ## Build the wheel and sdist into dist/
	@uv build

clean: ## Remove build artefacts and caches
	@rm -rf dist .pytest_cache .ruff_cache .mypy_cache coverage.xml
	@find . -type d -name __pycache__ -exec rm -rf {} +
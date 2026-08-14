"""Command-line entry point for ollama-usage, built on Typer."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import typer

from ollama_usage.budget import DEFAULT_NUM_CTX, DEFAULT_WARN_THRESHOLD, check_context_budget
from ollama_usage.logger import DEFAULT_LOG_PATH, DEFAULT_OLLAMA_URL, call_and_log
from ollama_usage.proxy import DEFAULT_TARGET, run_proxy
from ollama_usage.report import plot as plot_usage
from ollama_usage.report import summary as summary_report

app = typer.Typer(
    name="ollama-usage",
    help="Log, budget, and visualise token usage for local Ollama models.",
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    log_path: Annotated[
        Path,
        typer.Option(help="Path to the JSONL usage log, shared by every command."),
    ] = DEFAULT_LOG_PATH,
) -> None:
    ctx.obj = {"log_path": log_path.expanduser()}


@app.command()
def log(
    ctx: typer.Context,
    model: Annotated[str, typer.Option(help="Ollama model tag to call.")],
    prompt: Annotated[str, typer.Option(help="Prompt to send.")],
    tag: Annotated[
        str, typer.Option(help="Label for this task, used later to group usage.")
    ] = "untagged",
    num_ctx: Annotated[
        int, typer.Option(help="Context window size to check the prompt against.")
    ] = DEFAULT_NUM_CTX,
    ollama_url: Annotated[str, typer.Option(help="Ollama generate endpoint.")] = DEFAULT_OLLAMA_URL,
) -> None:
    """Call Ollama, log the token usage, and warn if the context budget is tight."""
    log_path = ctx.obj["log_path"]
    data = call_and_log(
        model=model,
        prompt=prompt,
        tag=tag,
        log_path=log_path,
        ollama_url=ollama_url,
    )
    check_context_budget(
        prompt_tokens=data.get("prompt_eval_count", 0),
        num_ctx=num_ctx,
        warn_threshold=DEFAULT_WARN_THRESHOLD,
    )
    typer.echo(data.get("response", ""))


@app.command()
def report(ctx: typer.Context) -> None:
    """Print a per-tag usage summary: calls, total tokens, average tokens/sec."""
    typer.echo(summary_report(log_path=ctx.obj["log_path"]))


@app.command()
def plot(ctx: typer.Context) -> None:
    """Plot tokens-per-second over time, in a matplotlib window."""
    plot_usage(log_path=ctx.obj["log_path"])


@app.command()
def proxy(
    ctx: typer.Context,
    target: Annotated[
        str, typer.Option(help="The real Ollama server to forward requests to.")
    ] = DEFAULT_TARGET,
    tag: Annotated[
        str,
        typer.Option(
            help="Tag applied to every request that comes through this proxy. "
            "The proxy can't see what task the client is working on, so "
            "everything routed through one proxy instance shares one tag."
        ),
    ] = "cline",
    host: Annotated[str, typer.Option(help="Bind address for the proxy itself.")] = "0.0.0.0",
    port: Annotated[
        int,
        typer.Option(
            help="Port for the proxy to listen on. Point Cline's Ollama Base "
            "URL at this port instead of Ollama's real port."
        ),
    ] = 11435,
) -> None:
    """Run a transparent proxy in front of Ollama — this is what actually
    captures traffic from Cline or any other client that talks to Ollama
    directly, since they never call ollama-usage's `log` command."""
    typer.echo(
        f"Proxying http://{host}:{port} -> {target}\n"
        f"Point Cline's Ollama Base URL at http://localhost:{port} to capture its traffic."
    )
    run_proxy(target=target, log_path=ctx.obj["log_path"], tag=tag, host=host, port=port)


@app.command()
def dashboard(
    host: Annotated[
        str,
        typer.Option(
            help="Bind address. 0.0.0.0 exposes it on your LAN; "
            "use 127.0.0.1 to keep it local-only."
        ),
    ] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Port to serve the dashboard on.")] = 8501,
) -> None:
    """Launch the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard.py"
    typer.echo(
        f"Starting dashboard on http://{host}:{port} "
        f"(use your machine's LAN IP instead of {host} from other devices)"
    )
    subprocess.run(
        [
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.address",
            host,
            "--server.port",
            str(port),
        ]
    )


if __name__ == "__main__":
    app()
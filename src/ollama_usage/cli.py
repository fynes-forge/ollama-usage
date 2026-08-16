from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ollama_usage import __version__
from ollama_usage.budget import (
    DEFAULT_NUM_CTX,
    DEFAULT_WARN_THRESHOLD,
    check_context_budget,
)
from ollama_usage.config import BrandColour
from ollama_usage.logger import (
    DEFAULT_LOG_PATH,
    DEFAULT_OLLAMA_URL,
    call_and_log,
)
from ollama_usage.proxy import DEFAULT_TARGET, run_proxy
from ollama_usage.report import plot_report, summary

console = Console()

app = typer.Typer(
    name="ollama-usage",
    help="Log, budget, and visualise token usage for local Ollama models.",
    epilog="A Fynes Forge tool — fynesforge.dev",
    no_args_is_help=True,
)


def _version_callback(show: bool) -> None:
    if show:
        gold = BrandColour.GOLD.value
        lavender = BrandColour.LAVENDER.value
        console.print(
            f"[bold {gold}]ollama-usage[/] v{__version__} "
            f"— a [{lavender}]Fynes Forge[/] tool"
        )
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    log_path: Annotated[
        Path,
        typer.Option(help="Path to the JSONL usage log, shared by every command."),
    ] = DEFAULT_LOG_PATH,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    ctx.obj = {"log_path": log_path.expanduser()}


@app.command()
def log(
    ctx: typer.Context,
    model: Annotated[str, typer.Option(help="Ollama model tag to call.")],
    prompt: Annotated[str, typer.Option(help="Prompt to send.")],
    tag: Annotated[
        str,
        typer.Option(help="Label for this task, used later to group usage."),
    ] = "untagged",
    num_ctx: Annotated[
        int,
        typer.Option(help="Context window size to check the prompt against."),
    ] = DEFAULT_NUM_CTX,
    ollama_url: Annotated[
        str, typer.Option(help="Ollama generate endpoint.")
    ] = DEFAULT_OLLAMA_URL,
) -> None:
    """Call Ollama, log token usage, and warn if context budget is tight."""
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
    """Print a per-tag usage summary: calls, total tokens, avg tokens/sec."""
    typer.echo(summary(log_path=ctx.obj["log_path"]))


@app.command()
def plot(ctx: typer.Context) -> None:
    """Plot tokens-per-second over time, in a matplotlib window."""
    plot_report(log_path=ctx.obj["log_path"])


@app.command()
def proxy(
    ctx: typer.Context,
    target: Annotated[
        str,
        typer.Option(help="The real Ollama server to forward requests to."),
    ] = DEFAULT_TARGET,
    tag: Annotated[
        str,
        typer.Option(help="Tag applied to every request routed through this proxy."),
    ] = "cline",
    host: Annotated[
        str, typer.Option(help="Bind address for the proxy itself.")
    ] = "0.0.0.0",
    port: Annotated[
        int,
        typer.Option(help="Port for the proxy to listen on. Point client here."),
    ] = 11435,
) -> None:
    """Run a transparent proxy in front of Ollama."""
    cyan = BrandColour.CYAN.value
    gold = BrandColour.GOLD.value

    console.print(f"[{cyan}]›[/] Proxying [bold]http://{host}:{port}[/] → {target}")
    console.print(
        f"[{cyan}]›[/] Point Cline's Ollama Base URL at "
        f"[bold {gold}]http://localhost:{port}[/] to capture its traffic."
    )
    run_proxy(
        target=target,
        log_path=ctx.obj["log_path"],
        tag=tag,
        host=host,
        port=port,
    )


@app.command()
def dashboard(
    host: Annotated[
        str,
        typer.Option(help="Bind address. 0.0.0.0 for LAN; 127.0.0.1 for local-only."),
    ] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Port to serve the dashboard on.")] = 8501,
) -> None:
    """Launch the Streamlit dashboard."""
    cyan = BrandColour.CYAN.value
    dashboard_path = Path(__file__).parent / "dashboard.py"

    console.print(f"[{cyan}]›[/] Starting dashboard on [bold]http://{host}:{port}[/]")
    console.print(f"[{cyan}]›[/] Use machine's LAN IP instead of {host} for devices.")
    subprocess.run(
        [
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.address",
            host,
            "--server.port",
            str(port),
        ],
        check=True,
    )


if __name__ == "__main__":
    app()

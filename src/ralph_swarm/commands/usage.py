"""Usage command - Display cost reports from usage data."""

import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ralph_swarm.usage import load_usage

console = Console()


@click.command("usage")
@click.option("--json-output", "--json", "json_out", is_flag=True, help="Output as JSON")
@click.option("--by-model", is_flag=True, help="Group by model")
@click.option("--by-command", is_flag=True, help="Group by command")
@click.option("--since", type=str, default=None, help="Filter records since date (YYYY-MM-DD)")
def usage_cmd(json_out: bool, by_model: bool, by_command: bool, since: str | None) -> None:
    """Display token usage and cost report.

    Reads usage data from logs/usage.json and displays a summary table.
    """
    cwd = Path.cwd()
    logs_dir = cwd / "logs"
    records = load_usage(logs_dir)

    if not records:
        if json_out:
            console.print("[]")
        else:
            console.print("[yellow]No usage data found.[/yellow]")
            console.print(
                "[dim]Usage data is collected when running"
                " 'ralph plan' or 'ralph build'.[/dim]"
            )
        return

    # Filter by date
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError as e:
            raise click.BadParameter(
                f"Invalid date format: {since}. Use YYYY-MM-DD.", param_hint="'--since'"
            ) from e
        records = [r for r in records if datetime.fromisoformat(r.timestamp) >= since_dt]

    if not records:
        if json_out:
            console.print("[]")
        else:
            console.print("[yellow]No usage data matching filters.[/yellow]")
        return

    if json_out:
        from dataclasses import asdict

        console.print(json.dumps([asdict(r) for r in records], indent=2))
        return

    # Default: show both model and command breakdowns
    if not by_model and not by_command:
        by_model = True
        by_command = True

    if by_model:
        _print_by_model(records)

    if by_command:
        _print_by_command(records)

    # Grand total
    total_cost = sum(r.cost_usd for r in records)
    total_input = sum(r.input_tokens for r in records)
    total_output = sum(r.output_tokens for r in records)
    total_duration = sum(r.duration_seconds for r in records)

    console.print()
    table = Table(title="Grand Total", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Invocations", str(len(records)))
    table.add_row("Input Tokens", f"{total_input:,}")
    table.add_row("Output Tokens", f"{total_output:,}")
    table.add_row("Total Duration", f"{total_duration:.0f}s")
    table.add_row("Total Cost", f"[bold green]${total_cost:.4f}[/bold green]")
    console.print(table)


def _print_by_model(records: list) -> None:
    """Print usage grouped by model."""
    by_model: dict[str, dict] = {}
    for r in records:
        m = by_model.setdefault(r.model, {"count": 0, "input": 0, "output": 0, "cost": 0.0})
        m["count"] += 1
        m["input"] += r.input_tokens
        m["output"] += r.output_tokens
        m["cost"] += r.cost_usd

    table = Table(title="Usage by Model", show_header=True)
    table.add_column("Model", style="bold")
    table.add_column("Invocations", justify="right")
    table.add_column("Input Tokens", justify="right")
    table.add_column("Output Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")

    for model_name, stats in sorted(by_model.items()):
        table.add_row(
            model_name,
            str(stats["count"]),
            f"{stats['input']:,}",
            f"{stats['output']:,}",
            f"${stats['cost']:.4f}",
        )

    console.print(table)


def _print_by_command(records: list) -> None:
    """Print usage grouped by command."""
    by_cmd: dict[str, dict] = {}
    for r in records:
        c = by_cmd.setdefault(r.command, {"count": 0, "input": 0, "output": 0, "cost": 0.0})
        c["count"] += 1
        c["input"] += r.input_tokens
        c["output"] += r.output_tokens
        c["cost"] += r.cost_usd

    table = Table(title="Usage by Command", show_header=True)
    table.add_column("Command", style="bold")
    table.add_column("Invocations", justify="right")
    table.add_column("Input Tokens", justify="right")
    table.add_column("Output Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")

    for cmd_name, stats in sorted(by_cmd.items()):
        table.add_row(
            cmd_name,
            str(stats["count"]),
            f"{stats['input']:,}",
            f"{stats['output']:,}",
            f"${stats['cost']:.4f}",
        )

    console.print(table)

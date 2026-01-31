"""Plan command - Planning mode for creating epics and stories."""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table

from ralph_swarm.prompts import load_prompt
from ralph_swarm.usage import (
    UsageRecord,
    calculate_cost,
    parse_stream_json_usage,
    save_usage,
)

console = Console()


def get_beads_summary(cwd: Path) -> dict[str, int]:
    """Get a summary of current beads issues."""
    result = subprocess.run(  # noqa: S603, S607
        ["bd", "list", "--json"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return {}

    import json

    try:
        issues = json.loads(result.stdout)
        summary = {"total": len(issues), "open": 0, "in_progress": 0, "closed": 0}
        for issue in issues:
            status = issue.get("status", "open")
            if status in summary:
                summary[status] += 1
        return summary
    except (json.JSONDecodeError, KeyError):
        return {}


@click.command("plan")
@click.option(
    "--model", "-m", default="opus", show_default=True, help="Model to use (sonnet, opus, haiku)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show Claude output in real-time")
@click.option("--dry-run", is_flag=True, help="Show prompt without executing")
@click.option(
    "--iterations", "-n", default=1, show_default=True, help="Number of planning iterations"
)
def plan_cmd(model: str, verbose: bool, dry_run: bool, iterations: int) -> None:
    """Run planning mode to create epics and stories.

    This phase analyzes your specs and creates a structured backlog
    of epics and stories in beads.
    """
    cwd = Path.cwd()

    # Check for required files
    if not (cwd / "CLAUDE.md").exists():
        console.print("[red]CLAUDE.md not found. Run 'ralph init' first.[/red]")
        sys.exit(1)

    if not (cwd / ".beads").exists():
        console.print("[red]Beads not initialized. Run 'ralph init' first.[/red]")
        sys.exit(1)

    console.print(
        Panel.fit("[bold blue]Ralph Swarm[/bold blue] - Planning Mode", subtitle=f"Model: {model}")
    )

    # Show current state
    summary = get_beads_summary(cwd)
    if summary:
        table = Table(title="Current Beads State", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Count")
        table.add_row("Total Issues", str(summary.get("total", 0)))
        table.add_row("Open", str(summary.get("open", 0)))
        table.add_row("In Progress", str(summary.get("in_progress", 0)))
        table.add_row("Closed", str(summary.get("closed", 0)))
        console.print(table)
        console.print()

    # Load prompt
    plan_prompt = load_prompt("system/plan")

    if dry_run:
        console.print("[bold]Prompt that would be sent:[/bold]")
        console.print(Panel(plan_prompt, title="Planning Prompt"))
        return

    total_cost = 0.0

    for i in range(iterations):
        if iterations > 1:
            console.print(f"\n[bold]Planning iteration {i + 1}/{iterations}[/bold]")

        console.print("[dim]Running Claude in planning mode...[/dim]")

        # Always use stream-json for usage capture
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--model", model,
            "--output-format", "stream-json",
        ]

        if verbose:
            cmd.append("--verbose")

        start_time = time.time()
        captured_output = ""
        returncode = 1

        try:
            if verbose:
                # Stream output in real-time while capturing
                process = subprocess.Popen(  # noqa: S603
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                )
                if process.stdin is None:
                    raise RuntimeError("Failed to open stdin pipe")
                process.stdin.write(plan_prompt)
                process.stdin.close()
                if process.stdout:
                    for line in process.stdout:
                        console.print(line, end="")
                        captured_output += line
                process.wait()
                returncode = process.returncode
            else:
                # Show spinner while running
                with Live(Spinner("dots", text="Planning..."), console=console):
                    result = subprocess.run(  # noqa: S603
                        cmd,
                        input=plan_prompt,
                        capture_output=True,
                        text=True,
                        cwd=cwd,
                    )

                captured_output = result.stdout or ""
                returncode = result.returncode

                if result.returncode == 0:
                    # Extract text result for display
                    display_text = _extract_plan_result_text(captured_output)
                    if display_text:
                        console.print(Panel(display_text, title="Planning Output"))
                else:
                    console.print(f"[red]Error: {result.stderr}[/red]")
                    sys.exit(1)

        except FileNotFoundError:
            console.print("[red]Claude CLI not found. Is it installed?[/red]")
            sys.exit(1)

        duration = time.time() - start_time

        # Parse and save usage
        usage_data = parse_stream_json_usage(captured_output)
        if usage_data and returncode == 0:
            input_tokens = usage_data.get("input_tokens", 0)
            output_tokens = usage_data.get("output_tokens", 0)
            cache_creation = usage_data.get("cache_creation_input_tokens", 0)
            cache_read = usage_data.get("cache_read_input_tokens", 0)
            resolved_model = usage_data.get("model", model) or model

            for short_name in ("opus", "sonnet", "haiku"):
                if short_name in resolved_model.lower():
                    resolved_model = short_name
                    break

            cost = calculate_cost(
                resolved_model, input_tokens, output_tokens, cache_creation, cache_read
            )
            total_cost += cost

            record = UsageRecord(
                timestamp=datetime.now().isoformat(),
                command="plan",
                worker_id="planner",
                model=resolved_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_input_tokens=cache_creation,
                cache_read_input_tokens=cache_read,
                cost_usd=cost,
                duration_seconds=round(duration, 1),
            )
            save_usage(record, cwd / "logs")

    # Show updated state
    console.print()
    new_summary = get_beads_summary(cwd)
    if new_summary:
        created = new_summary.get("total", 0) - summary.get("total", 0)
        if created > 0:
            console.print(f"[green]Created {created} new issue(s)[/green]")

        console.print("\n[bold]Ready issues:[/bold]")
        subprocess.run(["bd", "ready"], cwd=cwd)  # noqa: S603, S607

    if total_cost > 0:
        console.print(f"\n[dim]Planning cost: ${total_cost:.4f}[/dim]")

    console.print(
        Panel.fit(
            "[green]Planning complete![/green]\n\n"
            "Next steps:\n"
            "  1. Review created issues: [bold]bd list[/bold]\n"
            "  2. Check dependency graph: [bold]bd ready[/bold]\n"
            "  3. Start building: [bold]ralph build[/bold]",
            title="Done",
        )
    )


def _extract_plan_result_text(stream_json_output: str) -> str:
    """Extract the final result text from stream-json output."""
    import json

    for line in stream_json_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "result":
                return data.get("result", "")
        except json.JSONDecodeError:
            continue
    return ""

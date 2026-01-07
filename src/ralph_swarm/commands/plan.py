"""Plan command - Planning mode for creating epics and stories."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table

from ralph_swarm.prompts import load_prompt

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
@click.option("--model", "-m", default="opus", show_default=True, help="Model to use (sonnet, opus, haiku)")
@click.option("--verbose", "-v", is_flag=True, help="Show Claude output in real-time")
@click.option("--dry-run", is_flag=True, help="Show prompt without executing")
@click.option("--iterations", "-n", default=1, show_default=True, help="Number of planning iterations")
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

    console.print(Panel.fit(
        "[bold blue]Ralph Swarm[/bold blue] - Planning Mode",
        subtitle=f"Model: {model}"
    ))

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
    plan_prompt = load_prompt("plan")

    if dry_run:
        console.print("[bold]Prompt that would be sent:[/bold]")
        console.print(Panel(plan_prompt, title="Planning Prompt"))
        return

    for i in range(iterations):
        if iterations > 1:
            console.print(f"\n[bold]Planning iteration {i + 1}/{iterations}[/bold]")

        console.print("[dim]Running Claude in planning mode...[/dim]")

        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--model", model,
        ]

        if verbose:
            cmd.extend(["--output-format", "stream-json", "--verbose"])

        cmd.append(plan_prompt)

        try:
            if verbose:
                # Stream output in real-time
                process = subprocess.Popen(  # noqa: S603
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                )
                if process.stdout:
                    for line in process.stdout:
                        console.print(line, end="")
                process.wait()
            else:
                # Show spinner while running
                with Live(Spinner("dots", text="Planning..."), console=console):
                    result = subprocess.run(  # noqa: S603
                        cmd,
                        capture_output=True,
                        text=True,
                        cwd=cwd,
                    )

                if result.returncode == 0:
                    console.print(Panel(result.stdout, title="Planning Output"))
                else:
                    console.print(f"[red]Error: {result.stderr}[/red]")
                    sys.exit(1)

        except FileNotFoundError:
            console.print("[red]Claude CLI not found. Is it installed?[/red]")
            sys.exit(1)

    # Show updated state
    console.print()
    new_summary = get_beads_summary(cwd)
    if new_summary:
        created = new_summary.get("total", 0) - summary.get("total", 0)
        if created > 0:
            console.print(f"[green]Created {created} new issue(s)[/green]")

        console.print("\n[bold]Ready issues:[/bold]")
        subprocess.run(["bd", "ready"], cwd=cwd)  # noqa: S603, S607

    console.print(Panel.fit(
        "[green]Planning complete![/green]\n\n"
        "Next steps:\n"
        "  1. Review created issues: [bold]bd list[/bold]\n"
        "  2. Check dependency graph: [bold]bd ready[/bold]\n"
        "  3. Start building: [bold]ralph build[/bold]",
        title="Done"
    ))

"""Cleanup command - Clean up orphaned work from crashed workers."""

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

console = Console()


def get_in_progress_issues(cwd: Path) -> list[dict]:
    """Get all in-progress issues."""
    result = subprocess.run(  # noqa: S603, S607
        ["bd", "list", "--status", "in_progress", "--json"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def check_worker_running(worker_id: str) -> bool:
    """Check if a worker process is running."""
    result = subprocess.run(  # noqa: S603, S607
        ["pgrep", "-f", f"BD_ACTOR={worker_id}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@click.command("cleanup")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option("--discard-changes", is_flag=True, help="Also discard uncommitted changes")
def cleanup_cmd(force: bool, discard_changes: bool) -> None:
    """Clean up orphaned issues from crashed workers.

    Finds issues that are 'in_progress' but have no active worker
    and resets them to 'open' status.
    """
    cwd = Path.cwd()

    # Check for beads
    if not (cwd / ".beads").exists():
        console.print("[red]Not a ralph-swarm project (no .beads found)[/red]")
        sys.exit(1)

    console.print("[bold]Checking for orphaned issues...[/bold]\n")

    # Get in-progress issues
    in_progress = get_in_progress_issues(cwd)

    if not in_progress:
        console.print("[green]No in-progress issues found[/green]")
        return

    # Check which ones are orphaned
    orphaned = []
    active = []

    for issue in in_progress:
        assignee = issue.get("assignee", "")
        if assignee and check_worker_running(assignee):
            active.append(issue)
        else:
            orphaned.append(issue)

    # Show status
    if active:
        active_table = Table(title="Active Workers", show_header=True)
        active_table.add_column("Worker", style="green")
        active_table.add_column("Issue ID")
        active_table.add_column("Title")

        for issue in active:
            active_table.add_row(
                issue.get("assignee", "-"),
                issue.get("id", "")[:8],
                issue.get("title", "")[:40],
            )

        console.print(active_table)
        console.print()

    if not orphaned:
        console.print("[green]No orphaned issues found[/green]")
        return

    # Show orphaned issues
    orphan_table = Table(title="Orphaned Issues", show_header=True)
    orphan_table.add_column("ID", style="red")
    orphan_table.add_column("Assignee")
    orphan_table.add_column("Title")

    for issue in orphaned:
        orphan_table.add_row(
            issue.get("id", "")[:8],
            issue.get("assignee", "-"),
            issue.get("title", "")[:40],
        )

    console.print(orphan_table)
    console.print()

    # Confirm cleanup
    prompt = f"[yellow]Reset {len(orphaned)} orphaned issue(s) to 'open'?[/yellow]"
    if not force and not Confirm.ask(prompt):
        console.print("Cancelled.")
        return

    # Reset orphaned issues
    console.print("\n[bold]Resetting orphaned issues...[/bold]")
    for issue in orphaned:
        issue_id = issue.get("id", "")
        console.print(f"  Resetting {issue_id[:8]}...")

        # Update status to open and clear assignee
        subprocess.run(  # noqa: S603, S607
            ["bd", "update", issue_id, "--status", "open", "--assignee", ""],
            capture_output=True,
            cwd=cwd,
        )

    console.print(f"\n[green]Reset {len(orphaned)} issue(s)[/green]")

    # Handle uncommitted changes
    if discard_changes:
        result = subprocess.run(  # noqa: S603, S607
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )

        changes = [
            line
            for line in result.stdout.strip().split("\n")
            if line and not line.strip().startswith(".beads/")
        ]

        if changes:
            console.print("\n[bold]Uncommitted changes:[/bold]")
            for change in changes:
                console.print(f"  {change}")

            if force or Confirm.ask("\n[yellow]Discard these changes?[/yellow]"):
                subprocess.run(  # noqa: S603, S607
                    ["git", "restore", "."],
                    capture_output=True,
                    cwd=cwd,
                )
                console.print("[green]Changes discarded[/green]")

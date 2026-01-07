"""Status command - Show project and worker status."""

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


def get_issues(cwd: Path, status_filter: str | None = None) -> list[dict]:
    """Get issues from beads."""
    cmd = ["bd", "list", "--json", "--all", "--limit", "0"]
    if status_filter:
        cmd.extend(["--status", status_filter])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)  # noqa: S603
    if result.returncode != 0:
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def get_ready_issues(cwd: Path) -> list[dict]:
    """Get ready issues from beads."""
    result = subprocess.run(  # noqa: S603, S607
        ["bd", "ready", "--json"],
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


def check_running_workers(cwd: Path) -> list[dict]:
    """Check for running ralph workers."""
    workers = []

    # Check for ralph worker processes
    result = subprocess.run(  # noqa: S603, S607
        ["pgrep", "-f", "ralph-worker"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            if pid:
                workers.append({"pid": pid, "type": "worker"})

    return workers


@click.command("status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed issue information")
@click.option("--tree", "-t", is_flag=True, help="Show issues as dependency tree")
def status_cmd(verbose: bool, tree: bool) -> None:
    """Show project status and progress.

    Displays:
    - Issue summary (open, in-progress, completed)
    - Ready work queue
    - Running workers
    - Recent activity
    """
    cwd = Path.cwd()

    # Check for beads
    if not (cwd / ".beads").exists():
        console.print("[red]Not a ralph-swarm project (no .beads found)[/red]")
        console.print("Run 'ralph init' to initialize a project.")
        sys.exit(1)

    console.print(Panel.fit("[bold blue]Ralph Swarm[/bold blue] - Status", subtitle=str(cwd.name)))

    # Get all issues
    all_issues = get_issues(cwd)
    ready_issues = get_ready_issues(cwd)

    # Count by status
    status_counts = {"open": 0, "in_progress": 0, "closed": 0}
    type_counts: dict[str, int] = {}
    assignee_counts: dict[str, int] = {}

    for issue in all_issues:
        status = issue.get("status", "open")
        issue_type = issue.get("type", "task")
        assignee = issue.get("assignee", "")

        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

        if assignee and status == "in_progress":
            assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1

    # Summary table
    summary_table = Table(title="Issue Summary", show_header=True)
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Count", justify="right")
    summary_table.add_column("Percent", justify="right")

    total = len(all_issues)
    for status, count in status_counts.items():
        pct = f"{(count / total * 100):.1f}%" if total > 0 else "0%"
        color = {"open": "yellow", "in_progress": "blue", "closed": "green"}.get(status, "")
        summary_table.add_row(f"[{color}]{status}[/{color}]", str(count), pct)

    summary_table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]", "")
    console.print(summary_table)
    console.print()

    # Type breakdown
    if type_counts:
        type_table = Table(title="By Type", show_header=True)
        type_table.add_column("Type", style="bold")
        type_table.add_column("Count", justify="right")

        for issue_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            type_table.add_row(escape(str(issue_type)), str(count))

        console.print(type_table)
        console.print()

    # Ready queue
    if ready_issues:
        ready_table = Table(title="Ready Queue", show_header=True)
        ready_table.add_column("ID", style="dim")
        ready_table.add_column("Type")
        ready_table.add_column("Priority")
        ready_table.add_column("Title")
        ready_table.add_column("Assignee")

        for issue in ready_issues[:10]:  # Show top 10
            priority = str(issue.get("priority", "medium"))
            # Support both string priorities and numeric (0=highest)
            priority_color = {
                "critical": "red",
                "high": "yellow",
                "medium": "white",
                "low": "dim",
                "0": "red",
                "1": "yellow",
                "2": "white",
                "3": "dim",
            }.get(priority)

            # Only apply color if we have one, otherwise just escape the text
            if priority_color:
                priority_display = f"[{priority_color}]{escape(priority)}[/{priority_color}]"
            else:
                priority_display = escape(priority)

            ready_table.add_row(
                issue.get("id", "")[:8],
                escape(str(issue.get("type", "task"))),
                priority_display,
                escape(str(issue.get("title", ""))[:40]),
                escape(str(issue.get("assignee") or "-")),
            )

        console.print(ready_table)

        if len(ready_issues) > 10:
            console.print(f"[dim]  ... and {len(ready_issues) - 10} more[/dim]")

        console.print()

    # In progress by worker
    if assignee_counts:
        worker_table = Table(title="In Progress by Worker", show_header=True)
        worker_table.add_column("Worker", style="bold")
        worker_table.add_column("Issues", justify="right")

        for worker, count in sorted(assignee_counts.items()):
            worker_table.add_row(escape(str(worker)), str(count))

        console.print(worker_table)
        console.print()

    # Check for running workers
    workers = check_running_workers(cwd)
    if workers:
        console.print(f"[green]Running workers: {len(workers)}[/green]")
        for w in workers:
            console.print(f"  PID: {w['pid']}")
        console.print()

    # Show tree if requested
    if tree and all_issues:
        show_issue_tree(all_issues)

    # Verbose mode - show all issues
    if verbose and all_issues:
        verbose_table = Table(title="All Issues", show_header=True)
        verbose_table.add_column("ID", style="dim")
        verbose_table.add_column("Status")
        verbose_table.add_column("Type")
        verbose_table.add_column("Priority")
        verbose_table.add_column("Title")

        for issue in all_issues:
            issue_status = str(issue.get("status", "open"))
            status_color = {
                "open": "yellow",
                "in_progress": "blue",
                "closed": "green",
            }.get(issue_status, "")

            verbose_table.add_row(
                issue.get("id", "")[:8],
                f"[{status_color}]{escape(issue_status)}[/{status_color}]",
                escape(str(issue.get("type", "task"))),
                escape(str(issue.get("priority", "medium"))),
                escape(str(issue.get("title", ""))[:50]),
            )

        console.print(verbose_table)

    # Progress bar
    if total > 0:
        completed = status_counts.get("closed", 0)
        in_progress = status_counts.get("in_progress", 0)

        bar_width = 40
        completed_width = int(completed / total * bar_width)
        in_progress_width = int(in_progress / total * bar_width)
        remaining_width = bar_width - completed_width - in_progress_width

        bar = (
            f"[green]{'█' * completed_width}[/green]"
            f"[blue]{'█' * in_progress_width}[/blue]"
            f"[dim]{'░' * remaining_width}[/dim]"
        )

        console.print(f"Progress: {bar} {completed}/{total} ({completed / total * 100:.1f}%)")


def show_issue_tree(issues: list[dict]) -> None:
    """Show issues as a dependency tree."""
    # Build parent-child relationships
    children: dict[str, list[str]] = {}
    parents: dict[str, str] = {}

    for issue in issues:
        issue_id = issue.get("id", "")
        parent_id = issue.get("parent")
        if parent_id:
            parents[issue_id] = parent_id
            if parent_id not in children:
                children[parent_id] = []
            children[parent_id].append(issue_id)

    # Find root issues (no parent)
    root_ids = [i.get("id", "") for i in issues if not i.get("parent")]

    # Build tree
    issue_map = {i.get("id", ""): i for i in issues}
    tree = Tree("[bold]Issues[/bold]")

    def add_children(parent_tree: Tree, parent_id: str) -> None:
        for child_id in children.get(parent_id, []):
            child = issue_map.get(child_id, {})
            status = str(child.get("status", "open"))
            status_icon = {"open": "○", "in_progress": "◐", "closed": "●"}.get(status, "○")
            issue_type = escape(str(child.get("type", "task")))
            title = escape(str(child.get("title", ""))[:40])
            child_tree = parent_tree.add(f"{status_icon} \\[{issue_type}] {title}")
            add_children(child_tree, child_id)

    for root_id in root_ids:
        issue = issue_map.get(root_id, {})
        status = str(issue.get("status", "open"))
        status_icon = {"open": "○", "in_progress": "◐", "closed": "●"}.get(status, "○")
        issue_type = escape(str(issue.get("type", "task")))
        title = escape(str(issue.get("title", ""))[:40])
        root_tree = tree.add(f"{status_icon} \\[{issue_type}] {title}")
        add_children(root_tree, root_id)

    console.print(tree)
    console.print()

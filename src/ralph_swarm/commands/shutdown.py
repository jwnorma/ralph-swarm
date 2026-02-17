"""Shutdown command - Gracefully stop running workers."""

from pathlib import Path

import click
from rich.console import Console

console = Console()

STOP_FILE = ".ralph-stop"


@click.command("shutdown")
@click.option("--cancel", is_flag=True, help="Cancel a pending shutdown (remove stop file)")
def shutdown_cmd(cancel: bool) -> None:
    """Signal workers to finish their current task and stop.

    Creates a stop file that workers check before claiming new work.
    Use --cancel to remove the stop file and allow builds to continue.
    """
    stop_file = Path.cwd() / STOP_FILE

    if cancel:
        if stop_file.exists():
            stop_file.unlink()
            console.print("[green]Shutdown cancelled — workers may continue.[/green]")
        else:
            console.print("[yellow]No shutdown in progress.[/yellow]")
        return

    stop_file.touch()
    console.print(
        "[yellow]Shutdown requested — workers will stop after their current task.[/yellow]"
    )

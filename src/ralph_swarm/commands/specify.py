"""Specify command - Build project specifications."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from ralph_swarm.prompts import load_prompt

console = Console()


def get_spec_status(cwd: Path) -> dict:
    """Get current specification status."""
    specs_dir = cwd / "specs"
    if not specs_dir.exists():
        return {"exists": False, "files": [], "has_v0": False}

    spec_files = list(specs_dir.glob("*.md"))
    v0_files = [f for f in spec_files if f.name.startswith("v0")]

    return {
        "exists": True,
        "files": [f.name for f in spec_files],
        "has_v0": len(v0_files) > 0,
        "v0_files": [f.name for f in v0_files],
    }


def build_prior_art_section(prior_art: list[str]) -> str:
    """Build the prior art section for the prompt."""
    if not prior_art:
        return "## Prior Art\n\nNo prior art references provided."

    lines = ["## Prior Art", "", "Review these projects for inspiration:", ""]
    for ref in prior_art:
        lines.append(f"- {ref}")
    lines.extend([
        "",
        "Look at their documentation, architecture, and user experience.",
        "Learn from their patterns but don't copy complexity.",
    ])
    return "\n".join(lines)


def gather_prior_art() -> list[str]:
    """Interactively gather prior art references from user."""
    console.print("\n[bold]Prior Art[/bold]")
    console.print("[dim]Are there existing projects we should look at for inspiration?[/dim]")
    console.print("[dim](Documentation URLs, GitHub repos, similar tools, etc.)[/dim]\n")

    prior_art = []

    while True:
        ref = Prompt.ask(
            "Reference (or press Enter to skip/finish)",
            default="",
            show_default=False,
        )

        if not ref:
            break

        prior_art.append(ref)
        console.print(f"[green]  Added: {ref}[/green]")

    return prior_art


@click.command("specify")
@click.option("--model", "-m", default="opus", show_default=True, help="Model to use (sonnet, opus, haiku)")
@click.option("--verbose", "-v", is_flag=True, help="Show Claude output in real-time")
@click.option("--dry-run", is_flag=True, help="Show prompt without executing")
@click.option(
    "--feature", "-f",
    help="Specify a new feature (incremental mode)",
)
def specify_cmd(
    model: str,
    verbose: bool,
    dry_run: bool,
    feature: str | None,
) -> None:
    """Build project specifications interactively.

    On first run (no V0 specs), creates initial V0 specification.
    Use --feature to add new features incrementally.

    Examples:
        ralph specify                    # Initial V0 spec
        ralph specify --feature "auth"   # Add authentication feature
    """
    cwd = Path.cwd()

    # Check for required files
    if not (cwd / "CLAUDE.md").exists():
        console.print("[red]CLAUDE.md not found. Run 'ralph init' first.[/red]")
        sys.exit(1)

    # Check current spec status
    status = get_spec_status(cwd)

    # Determine mode
    if feature:
        mode = "incremental"
        mode_label = f"Add Feature: {feature}"
    elif status["has_v0"]:
        # V0 exists, ask what they want to do
        console.print(Panel.fit(
            "[bold blue]Ralph Swarm[/bold blue] - Specify Mode",
            subtitle=f"Model: {model}"
        ))

        console.print("[bold]Existing V0 specs found:[/bold]")
        for f in status.get("v0_files", []):
            console.print(f"  [green]●[/green] specs/{f}")
        console.print()

        if Confirm.ask("Add a new feature? (No to refine V0)"):
            feature_name = Prompt.ask("Feature name")
            mode = "incremental"
            mode_label = f"Add Feature: {feature_name}"
            feature = feature_name
        else:
            mode = "initial"
            mode_label = "Refine V0"
    else:
        mode = "initial"
        mode_label = "Initial V0"

    console.print(Panel.fit(
        "[bold blue]Ralph Swarm[/bold blue] - Specify Mode",
        subtitle=f"{mode_label} | Model: {model}"
    ))

    # Show existing specs
    if status["exists"] and status["files"]:
        console.print("[bold]Existing specs:[/bold]")
        for f in status["files"]:
            is_v0 = f.startswith("v0")
            marker = "[green]●[/green]" if is_v0 else "[dim]○[/dim]"
            console.print(f"  {marker} specs/{f}")
        console.print()

    # Ensure specs directory exists
    specs_dir = cwd / "specs"
    specs_dir.mkdir(exist_ok=True)

    # Gather prior art interactively
    if dry_run:
        prior_art_list: list[str] = []
    else:
        prior_art_list = gather_prior_art()

    # Build prior art section
    prior_art_section = build_prior_art_section(prior_art_list)

    # Load appropriate prompt
    if mode == "initial":
        prompt_template = load_prompt("specify_initial")
    else:
        prompt_template = load_prompt("specify_incremental")

    # Substitute variables
    prompt = prompt_template.replace("{prior_art_section}", prior_art_section)

    # Add feature context for incremental mode
    if feature:
        prompt = f"**Feature to specify:** {feature}\n\n" + prompt

    if dry_run:
        console.print("[bold]Prompt that would be sent:[/bold]")
        console.print(Panel(prompt, title="Specify Prompt"))
        return

    # Explain the process before launching
    console.print()
    console.print(Panel(
        "[bold]How this works:[/bold]\n\n"
        "1. An interactive Claude Code session will start\n"
        "2. Work with Claude to define your specifications\n"
        "3. Claude will create spec files in the [bold]specs/[/bold] directory\n"
        "4. When finished, type [bold]/exit[/bold] or press [bold]Ctrl+C[/bold] to end the session\n\n"
        "[dim]The session is collaborative - ask questions, refine scope, iterate.[/dim]",
        title="Interactive Session",
        border_style="blue",
    ))

    if not Confirm.ask("\n[bold]Ready to start?[/bold]"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print()

    # Run Claude interactively
    cmd = [
        "claude",
        "--model", model,
    ]

    if verbose:
        cmd.extend(["--verbose"])

    cmd.append(prompt)

    try:
        result = subprocess.run(cmd, cwd=cwd)  # noqa: S603

        if result.returncode != 0:
            console.print("[red]Session ended with error[/red]")
            sys.exit(1)

    except FileNotFoundError:
        console.print("[red]Claude CLI not found. Is it installed?[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted[/yellow]")

    # Show what was created/updated
    console.print()
    new_status = get_spec_status(cwd)

    new_files = set(new_status["files"]) - set(status["files"])
    if new_files:
        console.print("[bold]New specs created:[/bold]")
        for f in new_files:
            console.print(f"  [green]●[/green] specs/{f}")
    elif new_status["files"]:
        console.print("[bold]Specs:[/bold]")
        for f in new_status["files"]:
            console.print(f"  specs/{f}")

    console.print(Panel.fit(
        "[green]Specification session complete![/green]\n\n"
        "Next steps:\n"
        "  1. Review specs: [bold]ls specs/[/bold]\n"
        "  2. Run planning: [bold]ralph plan[/bold]\n"
        "  3. Start building: [bold]ralph build[/bold]",
        title="Done"
    ))

"""Research command - Interactive research session for technologies and approaches."""

import re
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from ralph_swarm.prompts import load_prompt

console = Console()


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Remove any characters that aren't alphanumeric or hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)
    # Remove multiple consecutive hyphens
    text = re.sub(r"-+", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")
    return text


def get_research_status(cwd: Path) -> dict:
    """Get current research status."""
    research_dir = cwd / "docs" / "research"
    if not research_dir.exists():
        return {"exists": False, "files": []}

    research_files = list(research_dir.glob("*.md"))
    return {
        "exists": True,
        "files": [f.name for f in research_files],
    }


def gather_research_context() -> dict:
    """Gather research topic and goal from user."""
    console.print("\n[bold]Research Topic[/bold]")
    console.print("[dim]What do you want to research?[/dim]")
    console.print(
        "[dim](e.g., 'authentication libraries', 'state management', 'MCP servers')[/dim]\n"
    )
Add KeyboardInterrupt handling to gather_research_context():

try:
    topic = Prompt.ask("Topic")
    # ... rest of the function
    return {"topic": topic, "goal": goal}
except KeyboardInterrupt:
    console.print("\n[yellow]Cancelled[/yellow]")
    sys.exit(0)
    topic = Prompt.ask("Topic")

    console.print("\n[bold]Research Goal[/bold]")
    console.print("[dim]What do you want to learn or decide?[/dim]")
    console.print(
        "[dim](e.g., 'choose best library for our use case', 'understand best practices')[/dim]\n"
    )

    goal = Prompt.ask("Goal")

    return {"topic": topic, "goal": goal}


@click.command("research")
@click.option(
    "--model", "-m", default="opus", show_default=True, help="Model to use (sonnet, opus, haiku)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show Claude output in real-time")
@click.option("--dry-run", is_flag=True, help="Show prompt without executing")
def research_cmd(
    model: str,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Research technologies, libraries, and best practices interactively.

    Launches an interactive session to help you research before defining specifications.
    Results are saved to docs/research/ for use in later phases.

    Examples:
        ralph research          # Interactive research session
        ralph research --dry-run  # Show prompt without executing
    """
    cwd = Path.cwd()

    # Check for required files
    if not (cwd / "CLAUDE.md").exists():
        console.print("[red]CLAUDE.md not found. Run 'ralph init' first.[/red]")
        sys.exit(1)

    console.print(
        Panel.fit(
            "[bold blue]Ralph Swarm[/bold blue] - Research Mode", subtitle=f"Model: {model}"
        )
    )

    # Check current research status
    status = get_research_status(cwd)

    # Show existing research if any
    if status["exists"] and status["files"]:
        console.print("[bold]Existing research:[/bold]")
        for f in status["files"]:
            console.print(f"  [dim]○[/dim] docs/research/{f}")
        console.print()

    # Gather research context interactively
    context = (
        {"topic": "<topic>", "goal": "<goal>"} if dry_run else gather_research_context()
    )

    # Ensure docs/research directory exists
    research_dir = cwd / "docs" / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    # Load and prepare prompt
    prompt_template = load_prompt("system/research")
    prompt = prompt_template.replace("{research_topic}", context["topic"])
    prompt = prompt.replace("{research_goal}", context["goal"])

    if dry_run:
        console.print("\n[bold]Prompt that would be sent:[/bold]")
        console.print(Panel(prompt, title="Research Prompt"))
        return

    # Explain the process before launching
    console.print()
    console.print(
        Panel(
            "[bold]How this works:[/bold]\n\n"
            "1. An interactive Claude Code session will start\n"
            "2. Claude will search the web for relevant information\n"
            "3. You can guide the research and ask follow-up questions\n"
            "4. Research findings will be saved to [bold]docs/research/[/bold]\n"
            "5. When finished, type [bold]/exit[/bold] or press "
            "[bold]Ctrl+C[/bold] to end the session\n\n"
            "[dim]The session is collaborative - refine the search, "
            "ask for more details, explore alternatives.[/dim]",
            title="Interactive Session",
            border_style="blue",
        )
    )

Wrap the Confirm.ask() in a try-except:

try:
    if not Confirm.ask("\n[bold]Ready to start?[/bold]"):
        console.print("[yellow]Cancelled[/yellow]")
        return
except KeyboardInterrupt:
    console.print("\n[yellow]Cancelled[/yellow]")
    return
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print()

    # Run Claude interactively
    cmd = [
        "claude",
        "--model",
        model,
    ]

    if verbose:
        cmd.extend(["--verbose"])

    cmd.append(prompt)

    try:
        result = subprocess.run(cmd, cwd=cwd)  # noqa: S603
Add validation for the model parameter:

ALLOWED_MODELS = ['sonnet', 'opus', 'haiku']
if model not in ALLOWED_MODELS:
    console.print(f"[red]Invalid model. Choose from: {', '.join(ALLOWED_MODELS)}[/red]")
    sys.exit(1)
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
    new_status = get_research_status(cwd)

    new_files = set(new_status["files"]) - set(status["files"])
    if new_files:
        console.print("[bold]New research created:[/bold]")
        for f in new_files:
            console.print(f"  [green]●[/green] docs/research/{f}")
    elif new_status["files"]:
        console.print("[bold]Research docs:[/bold]")
        for f in new_status["files"]:
            console.print(f"  docs/research/{f}")

    console.print(
        Panel.fit(
            "[green]Research session complete![/green]\n\n"
            "Next steps:\n"
            "  1. Review research: [bold]ls docs/research/[/bold]\n"
            "  2. Define specs: [bold]ralph specify[/bold]\n"
            "  3. Run planning: [bold]ralph plan[/bold]",
            title="Done",
        )
    )

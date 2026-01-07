"""Init command - Interactive project setup."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ralph_swarm.prompts import load_prompt_with_vars

console = Console()


def check_dependencies() -> list[str]:
    """Check for required dependencies."""
    missing = []
    for cmd in ["claude", "bd", "git"]:
        result = subprocess.run(
            ["which", cmd],
            capture_output=True,
            text=True,  # noqa: S603, S607
        )
        if result.returncode != 0:
            missing.append(cmd)
    return missing


def run_command(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command and return result."""
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)  # noqa: S603


def is_initialized(path: Path) -> bool:
    """Check if a project is already initialized."""
    markers = [".beads", "CLAUDE.md"]
    return any((path / marker).exists() for marker in markers)


@click.command("init")
def init_cmd() -> None:
    """Initialize a new ralph-swarm project in the current directory.

    This interactive command will help you:
    - Define the project objective
    - Choose your tech stack
    - Initialize git and beads
    - Generate a CLAUDE.md scaffold
    """
    project_path = Path.cwd()
    project_name = project_path.name

    console.print(
        Panel.fit(
            "[bold blue]Ralph Swarm[/bold blue] - Project Initialization",
            subtitle=f"Directory: {project_name}",
        )
    )

    # Check if already initialized
    if is_initialized(project_path):
        console.print("[red]Project already initialized.[/red]")
        console.print("[dim]Found existing .beads or CLAUDE.md[/dim]")
        console.print("\nTo reinitialize, remove these files first:")
        if (project_path / ".beads").exists():
            console.print("  rm -rf .beads")
        if (project_path / "CLAUDE.md").exists():
            console.print("  rm CLAUDE.md")
        sys.exit(1)

    # Check dependencies
    missing = check_dependencies()
    if missing:
        console.print(f"[red]Missing dependencies: {', '.join(missing)}[/red]")
        console.print("Please install:")
        if "claude" in missing:
            console.print("  - Claude Code: https://claude.com/claude-code")
        if "bd" in missing:
            console.print("  - Beads: https://github.com/steveyegge/beads")
        if "git" in missing:
            console.print("  - Git: https://git-scm.com")
        sys.exit(1)

    console.print()

    # Gather project info interactively
    console.print("[bold]Let's define your project.[/bold]\n")

    objective = Prompt.ask(
        "[bold]What is the main objective of this project?[/bold]\n"
        "[dim](e.g., 'A CLI tool for managing Kubernetes deployments')[/dim]"
    )

    console.print()
    problem = Prompt.ask(
        "[bold]What problem does it solve?[/bold]\n"
        "[dim](e.g., 'Simplifies complex K8s workflows for developers')[/dim]"
    )

    console.print()
    tech_stack = Prompt.ask(
        "[bold]What tech stack will you use?[/bold]\n"
        "[dim](e.g., 'Python, Click, Rich, Kubernetes API')[/dim]"
    )

    # Display summary
    console.print()
    table = Table(title="Project Summary", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Name", project_name)
    table.add_row("Objective", objective)
    table.add_row("Problem", problem)
    table.add_row("Tech Stack", tech_stack)
    console.print(table)
    console.print()

    if not Confirm.ask("[bold]Proceed with project setup?[/bold]"):
        sys.exit(0)

    # Initialize git
    console.print("\n[bold]Initializing git repository...[/bold]")
    if not (project_path / ".git").exists():
        run_command(["git", "init"], cwd=project_path)
        console.print("[green]  Git initialized[/green]")
    else:
        console.print("[dim]  Git already initialized[/dim]")

    # Initialize beads
    console.print("\n[bold]Initializing beads...[/bold]")
    if not (project_path / ".beads").exists():
        result = run_command(["bd", "init"], cwd=project_path)
        if result.returncode == 0:
            console.print("[green]  Beads initialized[/green]")
        else:
            console.print(f"[yellow]  Beads init warning: {result.stderr}[/yellow]")
    else:
        console.print("[dim]  Beads already initialized[/dim]")

    # Create specs directory
    specs_dir = project_path / "specs"
    specs_dir.mkdir(exist_ok=True)
    console.print("\n[bold]Created:[/bold] specs/")

    # Create adr directory for Architecture Decision Records
    adr_dir = project_path / "adr"
    adr_dir.mkdir(exist_ok=True)
    console.print("[bold]Created:[/bold] adr/")

    # Create .claude/agents directory for subagents
    agents_dir = project_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Load and write code-reviewer subagent
    code_reviewer_content = load_prompt_with_vars(
        "code-reviewer",
        project_name=project_name,
        objective=objective,
        tech_stack=tech_stack,
    )
    code_reviewer_file = agents_dir / "code-reviewer.md"
    code_reviewer_file.write_text(code_reviewer_content)
    console.print("[bold]Created:[/bold] .claude/agents/code-reviewer.md")

    # Load and write are-we-done subagent
    are_we_done_content = load_prompt_with_vars(
        "are-we-done",
        project_name=project_name,
    )
    are_we_done_file = agents_dir / "are-we-done.md"
    are_we_done_file.write_text(are_we_done_content)
    console.print("[bold]Created:[/bold] .claude/agents/are-we-done.md")

    # Load and write adr subagent
    adr_content = load_prompt_with_vars(
        "adr",
        project_name=project_name,
    )
    adr_file = agents_dir / "adr.md"
    adr_file.write_text(adr_content)
    console.print("[bold]Created:[/bold] .claude/agents/adr.md")

    # Create build.sh
    build_sh_content = (
        """#!/bin/bash
# Build script for """
        + project_name
        + """

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    echo "Usage: ./build.sh <command>"
    echo ""
    echo "Commands:"
    echo "  help         Show this help"
    echo ""
    echo "Add more commands as the project evolves."
}

case "${1:-help}" in
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
"""
    )

    build_sh_file = project_path / "build.sh"
    build_sh_file.write_text(build_sh_content)
    build_sh_file.chmod(0o755)
    console.print("[bold]Created:[/bold] build.sh")

    # Create CLAUDE.md
    claude_md_content = f"""# {project_name}

## What

{objective}

## Why

{problem}

## Tech Stack

{tech_stack}

## Project Structure

```
specs/                      # Design specifications
adr/                        # Architecture Decision Records
.beads/                     # Issue tracking (beads)
.claude/agents/             # Claude Code subagents
build.sh                    # Build commands
```

## Subagents

This project uses Claude Code subagents for quality assurance and documentation.
Subagents are automatically available and should be used by delegating to them.

### During Implementation

**adr** - Use when making architectural decisions (choosing libraries, patterns).
Check `adr/` for existing decisions before implementing.

### Before Completing Tasks

**code-reviewer** - Use after implementation to review changes for security,
code quality, and documentation accuracy.

**are-we-done** (REQUIRED) - Use before marking any task complete.
Runs build, tests, and all configured checks.
Do not close an issue until this returns "READY TO COMPLETE".

## Build & Test

Run `./build.sh help` for available commands.

```bash
./build.sh help    # Show available commands
```

Add new commands to build.sh as the project evolves.

## Issue Tracking

This project uses [beads](https://github.com/steveyegge/beads) for issue tracking.

- `bd list` - List open issues
- `bd ready` - Show issues ready to work on
- `bd create "title"` - Create new issue
- `bd close <id>` - Close an issue
"""

    claude_md_file = project_path / "CLAUDE.md"
    claude_md_file.write_text(claude_md_content)
    console.print("[bold]Created:[/bold] CLAUDE.md")

    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project
.env
*.log
"""

    gitignore_file = project_path / ".gitignore"
    if not gitignore_file.exists():
        gitignore_file.write_text(gitignore_content)
        console.print("[bold]Created:[/bold] .gitignore")

    # Summary
    console.print(
        Panel.fit(
            "[green]Project initialized successfully![/green]\n\n"
            "Next steps:\n"
            "  1. Run [bold]ralph specify[/bold] to define V0 specs\n"
            "  2. Run [bold]ralph plan[/bold] to create epics and stories\n"
            "  3. Run [bold]ralph build[/bold] to start implementation",
            title="Done",
        )
    )

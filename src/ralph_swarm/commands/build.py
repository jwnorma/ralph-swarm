"""Build command - Build mode with worker swarm support."""

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ralph_swarm.prompts import load_prompt_with_vars

console = Console()


def get_worker_prompt(worker_id: str) -> str:
    """Generate worker-specific prompt."""
    return load_prompt_with_vars("system/build", worker_id=worker_id)


def get_work_status(cwd: Path) -> dict:
    """Get current work status from beads."""
    result = subprocess.run(  # noqa: S603, S607
        ["bd", "ready", "--json"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return {"total": 0, "unassigned": 0, "issues": []}

    try:
        issues = json.loads(result.stdout)
        unassigned = [i for i in issues if not i.get("assignee")]
        return {
            "total": len(issues),
            "unassigned": len(unassigned),
            "issues": issues,
        }
    except (json.JSONDecodeError, KeyError):
        return {"total": 0, "unassigned": 0, "issues": []}


def run_single_worker(
    worker_id: str,
    model: str,
    verbose: bool,
    cwd: Path,
    log_file: Path | None = None,
) -> int:
    """Run a single worker iteration. Returns: 0=no work, 1=worked, 2=error."""
    prompt = get_worker_prompt(worker_id)

    # Set BD_ACTOR environment for atomic claims
    env = os.environ.copy()
    env["BD_ACTOR"] = worker_id

    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model",
        model,
    ]

    if verbose:
        cmd.extend(["--output-format", "stream-json", "--verbose"])

    cmd.append(prompt)

    try:
        if log_file:
            with open(log_file, "a") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"Worker: {worker_id} | Time: {datetime.now().isoformat()}\n")
                f.write(f"{'=' * 60}\n\n")

                result = subprocess.run(  # noqa: S603
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                    env=env,
                )
        elif verbose:
            process = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
            )
            if process.stdout:
                for line in process.stdout:
                    console.print(line, end="")
            process.wait()
            result = subprocess.CompletedProcess(cmd, process.returncode)
        else:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=env,
            )
            if result.stdout:
                console.print(Panel(result.stdout[:2000], title=f"Worker {worker_id}"))

        return 1 if result.returncode == 0 else 2

    except FileNotFoundError:
        console.print("[red]Claude CLI not found.[/red]")
        return 2


@click.command("build")
@click.option("--workers", "-w", default=1, show_default=True, help="Number of parallel workers")
@click.option(
    "--model", "-m", default="sonnet", show_default=True, help="Model to use (sonnet, opus, haiku)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show Claude output in real-time")
@click.option("--once", is_flag=True, help="Run single iteration instead of looping")
@click.option(
    "--auto-shutdown/--no-auto-shutdown",
    default=True,
    help="Shutdown when no work remains (default: enabled)",
)
@click.option("--idle-limit", default=3, help="Idle iterations before auto-shutdown")
@click.option("--dry-run", is_flag=True, help="Show prompt without executing")
def build_cmd(
    workers: int,
    model: str,
    verbose: bool,
    once: bool,
    auto_shutdown: bool,
    idle_limit: int,
    dry_run: bool,
) -> None:
    """Run build mode with worker swarm.

    This phase picks up issues from beads and implements them.
    Use multiple workers for parallel development.
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
        Panel.fit(
            "[bold blue]Ralph Swarm[/bold blue] - Build Mode",
            subtitle=f"Workers: {workers} | Model: {model}",
        )
    )

    # Show current work status
    status = get_work_status(cwd)
    table = Table(title="Work Queue", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count")
    table.add_row("Ready Issues", str(status["total"]))
    table.add_row("Unassigned", str(status["unassigned"]))
    console.print(table)
    console.print()

    if status["total"] == 0:
        console.print("[yellow]No issues ready. Run 'ralph plan' first.[/yellow]")
        return

    if dry_run:
        console.print("[bold]Prompt that would be sent:[/bold]")
        console.print(Panel(get_worker_prompt("ralph-1"), title="Build Prompt"))
        return

    # Setup logging
    log_dir = cwd / "logs" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create latest symlink
    latest_link = cwd / "logs" / "latest"
    if latest_link.is_symlink():
        latest_link.unlink()
    elif latest_link.exists():
        pass  # Don't overwrite non-symlink
    else:
        latest_link.symlink_to(log_dir.name)

    console.print(f"[dim]Logs: {log_dir}[/dim]\n")

    if workers == 1:
        # Single worker mode
        run_single_worker_loop(
            worker_id="ralph-1",
            model=model,
            verbose=verbose,
            once=once,
            auto_shutdown=auto_shutdown,
            idle_limit=idle_limit,
            cwd=cwd,
            log_file=log_dir / "ralph-1.log" if not verbose else None,
        )
    else:
        # Swarm mode
        run_swarm(
            workers=workers,
            model=model,
            verbose=verbose,
            auto_shutdown=auto_shutdown,
            idle_limit=idle_limit,
            cwd=cwd,
            log_dir=log_dir,
        )


def run_single_worker_loop(
    worker_id: str,
    model: str,
    verbose: bool,
    once: bool,
    auto_shutdown: bool,
    idle_limit: int,
    cwd: Path,
    log_file: Path | None,
) -> None:
    """Run single worker in a loop."""
    iteration = 1
    idle_count = 0

    console.print(f"[green]Starting worker {worker_id}...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        while True:
            console.print(
                f"[bold]Iteration {iteration}[/bold] - {datetime.now().strftime('%H:%M:%S')}"
            )

            # Check for available work
            status = get_work_status(cwd)
            if status["unassigned"] == 0:
                idle_count += 1
                console.print(
                    f"[yellow]No unassigned work (idle: {idle_count}/{idle_limit})[/yellow]"
                )

                if auto_shutdown and idle_count >= idle_limit:
                    console.print("[green]Auto-shutdown: no work remaining[/green]")
                    break

                time.sleep(5)
                if once:
                    break
                iteration += 1
                continue

            # Reset idle count and do work
            idle_count = 0
            result = run_single_worker(worker_id, model, verbose, cwd, log_file)

            if result == 2:
                console.print("[red]Worker encountered error[/red]")
                break

            if once:
                break

            iteration += 1
            time.sleep(2)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")


def run_swarm(
    workers: int,
    model: str,
    verbose: bool,
    auto_shutdown: bool,
    idle_limit: int,
    cwd: Path,
    log_dir: Path,
) -> None:
    """Run multiple workers in parallel."""
    console.print(f"[green]Spawning {workers} workers...[/green]")
    console.print("[dim]Press Ctrl+C to stop all workers[/dim]\n")

    processes: list[subprocess.Popen] = []
    worker_scripts: list[Path] = []

    # Create worker scripts
    for i in range(1, workers + 1):
        worker_id = f"ralph-{i}"
        script_path = log_dir / f"worker-{i}.sh"
        log_path = log_dir / f"ralph-{i}.log"

        script_content = f"""#!/bin/bash
export BD_ACTOR="{worker_id}"
cd "{cwd}"

iteration=1
idle_count=0

while true; do
    echo "=== Iteration $iteration - $(date) ===" >> "{log_path}"

    # Check for work
    unassigned=$(bd ready --unassigned --json 2>/dev/null | grep -c '"id"' || echo "0")

    if [ "$unassigned" -eq 0 ]; then
        ((idle_count++))
        echo "No unassigned work (idle: $idle_count/{idle_limit})" >> "{log_path}"

        if [ "{auto_shutdown}" = "True" ] && [ "$idle_count" -ge "{idle_limit}" ]; then
            echo "Auto-shutdown: no work remaining" >> "{log_path}"
            exit 0
        fi

        sleep 5
        ((iteration++))
        continue
    fi

    idle_count=0

    claude --print --dangerously-skip-permissions --model {model} \\
        '{get_worker_prompt(worker_id)}' >> "{log_path}" 2>&1

    ((iteration++))
    sleep 2
done
"""
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        worker_scripts.append(script_path)

    # Start workers
    for i, script in enumerate(worker_scripts, 1):
        log_path = log_dir / f"ralph-{i}.log"
        process = subprocess.Popen(  # noqa: S603
            ["/bin/bash", str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
        )
        processes.append(process)
        console.print(f"[green]  Started ralph-{i} (PID: {process.pid})[/green]")
        time.sleep(1)  # Stagger launches

    console.print()
    console.print("[bold]Workers running![/bold]")
    console.print(f"PIDs: {[p.pid for p in processes]}")
    console.print()
    console.print("View logs:")
    for i in range(1, workers + 1):
        console.print(f"  tail -f {log_dir}/ralph-{i}.log")
    console.print()

    # Wait for workers
    def shutdown(sig, frame):
        console.print("\n[yellow]Stopping all workers...[/yellow]")
        for p in processes:
            with contextlib.suppress(ProcessLookupError):
                p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        # Monitor workers
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Workers running...", total=None)

            while any(p.poll() is None for p in processes):
                alive = sum(1 for p in processes if p.poll() is None)
                progress.update(task, description=f"Workers running: {alive}/{workers}")
                time.sleep(2)

        console.print("[green]All workers finished[/green]")

    except KeyboardInterrupt:
        shutdown(None, None)

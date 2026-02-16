"""Build command - Build mode with worker swarm support."""

import contextlib
import fcntl
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


def _check_worktree_prerequisites(base_dir: Path) -> None:
    """Validate the git repo is ready for worktree creation."""
    # Check if inside a git repo
    result = subprocess.run(  # noqa: S603, S607
        ["git", "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )
    if result.returncode != 0:
        raise click.ClickException(
            "Not a git repository. Initialize one with 'git init' before using worktrees."
        )

    # Check if HEAD is valid (repo has at least one commit)
    result = subprocess.run(  # noqa: S603, S607
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )
    if result.returncode != 0:
        raise click.ClickException(
            "Git repository has no commits. "
            "Create an initial commit before using worktrees:\n"
            "  git add . && git commit -m 'Initial commit'"
        )

    # Check that we're on the main branch (required as merge target)
    result = subprocess.run(  # noqa: S603, S607
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )
    if result.returncode == 0 and result.stdout.strip() != "main":
        raise click.ClickException(
            f"Must be on 'main' branch to use worktrees (currently on '{result.stdout.strip()}'). "
            "Worker branches merge back to main after each task."
        )

    # Check for uncommitted changes that would prevent worktree checkout
    result = subprocess.run(  # noqa: S603, S607
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )
    if result.stdout.strip():
        console.print(
            "[yellow]Warning: You have uncommitted changes. "
            "Worktrees will be created from the last commit (HEAD).[/yellow]"
        )


def create_worktree(base_dir: Path, worker_id: str) -> Path:
    """Create a git worktree for the worker on a named branch.

    Returns the path to the worktree directory.
    """
    worktree_dir = base_dir / ".ralph-worktrees" / worker_id

    # Remove existing worktree (from previous run)
    if worktree_dir.exists():
        console.print(f"[yellow]Removing existing worktree: {worktree_dir}[/yellow]")
        subprocess.run(  # noqa: S603, S607
            ["git", "worktree", "remove", str(worktree_dir), "--force"],
            capture_output=True,
            cwd=base_dir,
        )

    # Delete stale branch if it exists from a previous run
    subprocess.run(  # noqa: S603, S607
        ["git", "branch", "-D", worker_id],
        capture_output=True,
        cwd=base_dir,
    )

    # Create worktree on a named branch
    result = subprocess.run(  # noqa: S603, S607
        ["git", "worktree", "add", str(worktree_dir), "-b", worker_id, "HEAD"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )

    if result.returncode != 0:
        console.print(f"[red]Failed to create worktree: {result.stderr.strip()}[/red]")
        raise RuntimeError(f"Failed to create worktree for {worker_id}")

    return worktree_dir


def merge_worker_to_main(base_dir: Path, worker_id: str) -> str:
    """Merge worker branch back to main. Returns 'success', 'nothing', or 'conflict'.

    Uses file locking to serialize concurrent merges from multiple workers.
    """
    # Check if worker branch has commits ahead of main
    result = subprocess.run(  # noqa: S603, S607
        ["git", "log", f"main..{worker_id}", "--oneline"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return "nothing"

    lock_path = base_dir / ".ralph-worktrees" / ".merge.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd = open(lock_path, "w")  # noqa: SIM115
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        result = subprocess.run(  # noqa: S603, S607
            ["git", "merge", worker_id, "--no-edit"],
            capture_output=True,
            text=True,
            cwd=base_dir,
        )
        if result.returncode != 0:
            # Merge conflict — abort and preserve the branch
            subprocess.run(  # noqa: S603, S607
                ["git", "merge", "--abort"],
                capture_output=True,
                cwd=base_dir,
            )
            return "conflict"

        return "success"
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def reset_worker_branch(base_dir: Path, worker_id: str) -> None:
    """Reset worker worktree to main HEAD so it's ready for the next task."""
    worktree_dir = base_dir / ".ralph-worktrees" / worker_id
    subprocess.run(  # noqa: S603, S607
        ["git", "reset", "--hard", "main"],
        capture_output=True,
        cwd=worktree_dir,
    )


def cleanup_worktrees(base_dir: Path) -> None:
    """Clean up all ralph worktrees, warning about unmerged work."""
    worktree_base = base_dir / ".ralph-worktrees"
    if not worktree_base.exists():
        return

    # List all worktrees
    result = subprocess.run(  # noqa: S603, S607
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )

    if result.returncode != 0:
        return

    # Collect branch names associated with ralph worktrees
    worktree_branches: list[str] = []

    # Parse worktree list and remove ralph worktrees
    for line in result.stdout.split("\n"):
        if line.startswith("worktree "):
            worktree_path = line.split(" ", 1)[1]
            if ".ralph-worktrees" in worktree_path:
                # Extract worker_id (branch name) from path
                branch_name = Path(worktree_path).name

                # Check for unmerged commits before removing
                log_result = subprocess.run(  # noqa: S603, S607
                    ["git", "log", f"main..{branch_name}", "--oneline"],
                    capture_output=True,
                    text=True,
                    cwd=base_dir,
                )
                if log_result.returncode == 0 and log_result.stdout.strip():
                    commit_count = len(log_result.stdout.strip().splitlines())
                    console.print(
                        f"[yellow]Warning: Branch '{branch_name}' has {commit_count} "
                        f"unmerged commit(s). Keeping branch ref for recovery.[/yellow]"
                    )
                    worktree_branches.append(branch_name)

                console.print(f"[dim]Removing worktree: {worktree_path}[/dim]")
                subprocess.run(  # noqa: S603, S607
                    ["git", "worktree", "remove", worktree_path, "--force"],
                    capture_output=True,
                    cwd=base_dir,
                )

    # Delete branches that were fully merged (no unmerged commits)
    # Keep branches with unmerged work for manual recovery
    result = subprocess.run(  # noqa: S603, S607
        ["git", "branch", "--list", "ralph-*"],
        capture_output=True,
        text=True,
        cwd=base_dir,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            branch = line.strip()
            if branch and branch not in worktree_branches:
                subprocess.run(  # noqa: S603, S607
                    ["git", "branch", "-D", branch],
                    capture_output=True,
                    cwd=base_dir,
                )

    # Remove directory if empty
    if worktree_base.exists() and not any(worktree_base.iterdir()):
        worktree_base.rmdir()


def get_worker_prompt(worker_id: str, issue_id: str | None = None) -> str:
    """Generate worker-specific prompt."""
    prompt = load_prompt_with_vars("system/build", worker_id=worker_id)
    if issue_id:
        prompt += (
            f"\n\n**ASSIGNED ISSUE:** {issue_id}\n"
            f"You have already been assigned issue {issue_id}. "
            f"Run `bd show {issue_id}` to see details and implement it.\n"
            "Skip the claiming step - proceed directly to implementation."
        )
    return prompt


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


def _check_rate_limited(log_file: Path, tail_lines: int = 10) -> bool:
    """Check if the tail of a log file contains rate-limit indicators."""
    try:
        lines = log_file.read_text().splitlines()[-tail_lines:]
        text = "\n".join(lines).lower()
        return "hit your limit" in text or "rate limit" in text
    except (OSError, ValueError):
        return False


def _release_issue(
    issue_id: str, worker_id: str, cwd: Path, reason: str, log_file: Path | None = None
) -> None:
    """Release a claimed issue back to the queue."""
    subprocess.run(  # noqa: S603, S607
        ["bd", "update", issue_id, "--status", "open", "--assignee", ""],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    msg = f"{reason} Released issue {issue_id} and shutting down worker {worker_id}."
    if log_file:
        with open(log_file, "a") as f:
            f.write(f"\n{msg}\n")
    console.print(f"[yellow]{msg}[/yellow]")


def _issue_still_in_progress(issue_id: str, cwd: Path) -> bool:
    """Check if an issue is still in_progress (i.e., Claude didn't complete it)."""
    result = subprocess.run(  # noqa: S603, S607
        ["bd", "show", issue_id, "--json"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list):
            data = data[0] if data else {}
        return data.get("status") == "in_progress"
    except (json.JSONDecodeError, KeyError, IndexError):
        return False


def run_single_worker(
    worker_id: str,
    model: str,
    verbose: bool,
    cwd: Path,
    log_file: Path | None = None,
    issue_id: str | None = None,
) -> int:
    """Run a single worker iteration. Returns: 0=no work, 1=worked, 2=error."""
    prompt = get_worker_prompt(worker_id, issue_id)

    # Set BD_ACTOR environment for atomic claims
    env = os.environ.copy()
    env["BD_ACTOR"] = worker_id

    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--model", model,
    ]

    if verbose:
        cmd.extend(["--output-format", "stream-json", "--verbose"])

    try:
        if log_file:
            with open(log_file, "a") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"Worker: {worker_id} | Time: {datetime.now().isoformat()}\n")
                f.write(f"{'=' * 60}\n\n")

                result = subprocess.run(  # noqa: S603
                    cmd,
                    input=prompt,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                    env=env,
                )
        elif verbose:
            process = subprocess.Popen(  # noqa: S603
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
            )
            if process.stdin:
                process.stdin.write(prompt)
                process.stdin.close()
            if process.stdout:
                for line in process.stdout:
                    console.print(line, end="")
            process.wait()
            result = subprocess.CompletedProcess(cmd, process.returncode)
        else:
            result = subprocess.run(  # noqa: S603
                cmd,
                input=prompt,
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
@click.option(
    "--use-worktrees",
    default=True,
    type=bool,
    show_default=True,
    help="Use git worktrees for worker isolation",
)
def build_cmd(
    workers: int,
    model: str,
    verbose: bool,
    once: bool,
    auto_shutdown: bool,
    idle_limit: int,
    dry_run: bool,
    use_worktrees: bool,
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

    console.print(f"[dim]Logs: {log_dir}[/dim]")
    if use_worktrees:
        console.print("[dim]Using git worktrees for worker isolation[/dim]")
    console.print()

    try:
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
                use_worktree=use_worktrees,
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
                use_worktrees=use_worktrees,
            )
    finally:
        # Clean up worktrees on exit
        if use_worktrees:
            console.print("\n[dim]Cleaning up worktrees...[/dim]")
            cleanup_worktrees(cwd)


def run_single_worker_loop(
    worker_id: str,
    model: str,
    verbose: bool,
    once: bool,
    auto_shutdown: bool,
    idle_limit: int,
    cwd: Path,
    log_file: Path | None,
    use_worktree: bool = False,
) -> None:
    """Run single worker in a loop."""
    iteration = 1
    idle_count = 0

    # Create worktree if requested
    if use_worktree:
        _check_worktree_prerequisites(cwd)
        work_dir = create_worktree(cwd, worker_id)
        console.print(f"[green]Created worktree: {work_dir}[/green]")
    else:
        work_dir = cwd

    console.print(f"[green]Starting worker {worker_id}...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        while True:
            console.print(
                f"[bold]Iteration {iteration}[/bold] - {datetime.now().strftime('%H:%M:%S')}"
            )

            # Check for available work
            status = get_work_status(work_dir)
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

            # Pick first unassigned issue (prioritized by beads)
            unassigned_issues = [i for i in status["issues"] if not i.get("assignee")]
            if not unassigned_issues:
                idle_count += 1
                console.print(
                    f"[yellow]No unassigned issues found (idle: {idle_count}/{idle_limit})[/yellow]"
                )

                if auto_shutdown and idle_count >= idle_limit:
                    console.print("[green]Auto-shutdown: no work remaining[/green]")
                    break

                time.sleep(5)
                iteration += 1
                continue

            issue_id = unassigned_issues[0]["id"]

            # Atomically claim the issue
            console.print(f"Attempting to claim issue {issue_id}...")
            subprocess.run(  # noqa: S603, S607
                ["bd", "update", issue_id, "--status", "in_progress", "--assignee", worker_id],
                capture_output=True,
                text=True,
                cwd=work_dir,
            )

            # Verify claim succeeded
            verify_result = subprocess.run(  # noqa: S603, S607
                ["bd", "show", issue_id, "--json"],
                capture_output=True,
                text=True,
                cwd=work_dir,
            )

            try:
                issue_data = json.loads(verify_result.stdout)
                # bd show may return a list or a dict
                if isinstance(issue_data, list):
                    issue_data = issue_data[0] if issue_data else {}
                claimed_by = issue_data.get("assignee")
            except (json.JSONDecodeError, KeyError, IndexError):
                claimed_by = None

            if claimed_by != worker_id:
                console.print(
                    f"[yellow]Failed to claim {issue_id} "
                    f"(claimed by {claimed_by}), retrying...[/yellow]"
                )
                time.sleep(1)
                iteration += 1
                continue

            console.print(f"[green]Successfully claimed {issue_id}[/green]")

            # Reset idle count and do work
            idle_count = 0
            result = run_single_worker(worker_id, model, verbose, work_dir, log_file, issue_id)

            if result == 2:
                console.print("[red]Worker encountered error[/red]")
                break

            # Check if Claude hit a rate limit
            if log_file and _check_rate_limited(log_file):
                _release_issue(issue_id, worker_id, work_dir, "Rate limit detected.", log_file)
                break

            # Check if Claude exited without completing the issue
            if _issue_still_in_progress(issue_id, work_dir):
                _release_issue(
                    issue_id, worker_id, work_dir,
                    "Issue still in_progress after Claude exited.",
                    log_file,
                )
                break

            # Merge completed work back to main
            if use_worktree:
                console.print(f"[dim]Merging {worker_id} branch to main...[/dim]")
                merge_result = merge_worker_to_main(cwd, worker_id)
                if merge_result == "success":
                    console.print(f"[green]Merged {worker_id} to main[/green]")
                    reset_worker_branch(cwd, worker_id)
                elif merge_result == "conflict":
                    console.print(
                        f"[red]Merge conflict on {worker_id}. "
                        f"Branch preserved for manual resolution.[/red]"
                    )
                    break
                # "nothing" — no commits to merge, continue normally

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
    use_worktrees: bool = False,
) -> None:
    """Run multiple workers in parallel."""
    console.print(f"[green]Spawning {workers} workers...[/green]")
    console.print("[dim]Press Ctrl+C to stop all workers[/dim]\n")

    processes: list[subprocess.Popen] = []
    worker_scripts: list[Path] = []

    # Create worktrees if requested
    if use_worktrees:
        _check_worktree_prerequisites(cwd)
        for i in range(1, workers + 1):
            worker_id = f"ralph-{i}"
            worktree_dir = create_worktree(cwd, worker_id)
            console.print(f"[green]  Created worktree for {worker_id}: {worktree_dir}[/green]")

    # Create worker scripts
    verbose_flags = " --output-format stream-json --verbose" if verbose else ""
    for i in range(1, workers + 1):
        worker_id = f"ralph-{i}"
        script_path = log_dir / f"worker-{i}.sh"
        log_path = log_dir / f"ralph-{i}.log"

        # Determine working directory
        work_dir = cwd / ".ralph-worktrees" / worker_id if use_worktrees else cwd

        script_content = f"""#!/bin/bash
export BD_ACTOR="{worker_id}"
cd "{work_dir}"

# Random initial delay to reduce startup contention (0-3 seconds)
sleep $((RANDOM % 4))

iteration=1
idle_count=0

MERGE_LOCK="{cwd}/.ralph-worktrees/.merge.lock"
MAIN_REPO="{cwd}"

check_idle_shutdown() {{
    local reason="$1"
    ((idle_count++))
    echo "$reason (idle: $idle_count/{idle_limit})" >> "{log_path}"
    if [ "{auto_shutdown}" = "True" ] && [ "$idle_count" -ge "{idle_limit}" ]; then
        echo "Auto-shutdown: no work remaining" >> "{log_path}"
        exit 0
    fi
}}

merge_to_main() {{
    # Check if worker branch has commits ahead of main
    ahead=$(git -C "$MAIN_REPO" log "main..{worker_id}" --oneline 2>/dev/null)
    if [ -z "$ahead" ]; then
        echo "Nothing to merge for {worker_id}" >> "{log_path}"
        return 0
    fi

    echo "Merging {worker_id} to main..." >> "{log_path}"

    # Use flock for serialized merges
    (
        flock -x 200
        if git -C "$MAIN_REPO" merge "{worker_id}" --no-edit >> "{log_path}" 2>&1; then
            echo "Merged {worker_id} to main successfully" >> "{log_path}"
            # Reset worktree to main HEAD for next task
            git -C "{work_dir}" reset --hard main >> "{log_path}" 2>&1
        else
            echo "Merge conflict on {worker_id}. Aborting merge." >> "{log_path}"
            git -C "$MAIN_REPO" merge --abort >> "{log_path}" 2>&1
            exit 1
        fi
    ) 200>"$MERGE_LOCK"
    return $?
}}

while true; do
    echo "=== Iteration $iteration - $(date) ===" >> "{log_path}"

    # Filter to unassigned client-side because bd ready --unassigned
    # does not reliably exclude assigned issues
    all_json=$(bd ready --json 2>/dev/null)
    unassigned_json=$(echo "$all_json" | \\
        jq -c '[.[] | select(.assignee == null or .assignee == "")]' 2>/dev/null)
    # Default to empty array if jq failed (e.g. invalid input)
    if ! echo "$unassigned_json" | jq empty 2>/dev/null; then
        unassigned_json="[]"
    fi
    unassigned_count=$(echo "$unassigned_json" | jq 'length' 2>/dev/null || echo "0")

    if [ "$unassigned_count" -eq 0 ]; then
        check_idle_shutdown "No unassigned work"
        sleep 5
        ((iteration++))
        continue
    fi

    # Pick first unassigned issue (prioritized by beads)
    issue_id=$(echo "$unassigned_json" | jq -r '.[0].id // empty' 2>/dev/null)

    if [ -z "$issue_id" ]; then
        check_idle_shutdown "No parseable issue ID"
        sleep 2
        ((iteration++))
        continue
    fi

    # Atomically claim the issue
    echo "Attempting to claim issue $issue_id..." >> "{log_path}"
    bd update "$issue_id" --status in_progress --assignee "{worker_id}" >> "{log_path}" 2>&1

    # Verify claim succeeded (handle both dict and list responses)
    claimed_by=$(bd show "$issue_id" --json 2>/dev/null | \\
        jq -r 'if type == "array" then .[0].assignee else .assignee end' 2>/dev/null)

    if [ "$claimed_by" != "{worker_id}" ]; then
        echo "Failed to claim $issue_id (claimed by $claimed_by), retrying..." >> "{log_path}"
        sleep $((RANDOM % 3))  # Random backoff 0-2 seconds
        ((iteration++))
        continue
    fi

    echo "Successfully claimed $issue_id" >> "{log_path}"
    idle_count=0

    # Launch Claude with the pre-assigned issue
    cat << PROMPT_EOF | claude --dangerously-skip-permissions \\
        --model {model}{verbose_flags} >> "{log_path}" 2>&1
{get_worker_prompt(worker_id)}

**ASSIGNED ISSUE:** $issue_id
You have already been assigned issue $issue_id.
Run \\`bd show $issue_id\\` to see details and implement it.
Skip the claiming step - proceed directly to implementation.
PROMPT_EOF

    # Check if Claude hit a rate limit
    last_output=$(tail -10 "{log_path}")
    if echo "$last_output" | grep -qi "hit your limit\\|rate limit"; then
        echo "Rate limit detected. Releasing issue $issue_id and shutting down." >> "{log_path}"
        bd update "$issue_id" --status open --assignee "" >> "{log_path}" 2>&1
        exit 0
    fi

    # Check if Claude exited without completing the issue
    issue_status=$(bd show "$issue_id" --json 2>/dev/null | \\
        jq -r 'if type == "array" then .[0].status else .status end' 2>/dev/null)
    if [ "$issue_status" = "in_progress" ]; then
        echo "Issue $issue_id still in_progress. Releasing and stopping." >> "{log_path}"
        bd update "$issue_id" --status open --assignee "" >> "{log_path}" 2>&1
        exit 0
    fi

    # Merge completed work back to main
    if ! merge_to_main; then
        echo "Merge conflict — stopping worker {worker_id}" >> "{log_path}"
        exit 1
    fi

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

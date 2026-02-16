"""Integration tests for worktree merge-back functionality.

Uses real git repos in tmp_path — no mocking.
"""

import functools
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

from ralph_swarm.commands.build import (
    create_worktree,
    merge_worker_to_main,
    reset_worker_branch,
)

# Environment cleaned of git vars that leak from pre-commit hooks
_CLEAN_ENV = {
    k: v for k, v in os.environ.items()
    if not k.startswith("GIT_")
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command with test author config and clean env."""
    env_args = [
        "-c", "user.name=Test",
        "-c", "user.email=test@test.com",
    ]
    result = subprocess.run(  # noqa: S603, S607
        ["git", *env_args, *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=_CLEAN_ENV,
    )
    return result


def _init_repo(tmp_path: Path) -> Path:
    """Create a git repo with an initial commit on main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "README.md").write_text("# Test\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Initial commit")
    return repo


def _clean_env(func):
    """Decorator to run test with clean git environment (no pre-commit hook vars)."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with patch.dict(os.environ, _CLEAN_ENV, clear=True):
            return func(*args, **kwargs)
    return wrapper


class TestCreateWorktree:
    @_clean_env
    def test_creates_named_branch(self, tmp_path: Path) -> None:
        """Worktree should be on a named branch, not detached HEAD."""
        repo = _init_repo(tmp_path)
        worktree_dir = create_worktree(repo, "ralph-1")

        result = _git(worktree_dir, "rev-parse", "--abbrev-ref", "HEAD")
        assert result.stdout.strip() == "ralph-1"

    @_clean_env
    def test_recreates_branch_on_second_run(self, tmp_path: Path) -> None:
        """Should handle existing branch from a previous run."""
        repo = _init_repo(tmp_path)

        # First run
        wt1 = create_worktree(repo, "ralph-1")
        assert wt1.exists()

        # Second run — should not error
        wt2 = create_worktree(repo, "ralph-1")
        assert wt2.exists()

        result = _git(wt2, "rev-parse", "--abbrev-ref", "HEAD")
        assert result.stdout.strip() == "ralph-1"


class TestMergeWorkerToMain:
    @_clean_env
    def test_fast_forward_merge(self, tmp_path: Path) -> None:
        """Single commit on worker branch merges cleanly."""
        repo = _init_repo(tmp_path)
        wt = create_worktree(repo, "ralph-1")

        # Commit in worktree
        (wt / "feature.py").write_text("print('hello')\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Add feature")

        result = merge_worker_to_main(repo, "ralph-1")
        assert result == "success"

        # Verify file is on main
        assert (repo / "feature.py").exists()

    @_clean_env
    def test_nothing_to_merge(self, tmp_path: Path) -> None:
        """No commits returns 'nothing'."""
        repo = _init_repo(tmp_path)
        create_worktree(repo, "ralph-1")

        result = merge_worker_to_main(repo, "ralph-1")
        assert result == "nothing"

    @_clean_env
    def test_merge_conflict_aborts_cleanly(self, tmp_path: Path) -> None:
        """Conflicting changes detected, merge aborted, branch preserved."""
        repo = _init_repo(tmp_path)
        wt = create_worktree(repo, "ralph-1")

        # Create conflicting change on main
        (repo / "README.md").write_text("# Changed on main\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "Change on main")

        # Create conflicting change on worker
        (wt / "README.md").write_text("# Changed on worker\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Change on worker")

        result = merge_worker_to_main(repo, "ralph-1")
        assert result == "conflict"

        # Main should be clean (merge was aborted) — ignore worktree artifacts
        status = _git(repo, "status", "--porcelain")
        non_worktree_changes = [
            line for line in status.stdout.strip().splitlines()
            if ".ralph-worktrees" not in line
        ]
        assert non_worktree_changes == []

        # Worker branch should still exist
        branches = _git(repo, "branch", "--list", "ralph-1")
        assert "ralph-1" in branches.stdout

    @_clean_env
    def test_multiple_commits_merge(self, tmp_path: Path) -> None:
        """Multiple commits on worker branch all merge."""
        repo = _init_repo(tmp_path)
        wt = create_worktree(repo, "ralph-1")

        (wt / "a.py").write_text("a\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Add a")

        (wt / "b.py").write_text("b\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Add b")

        result = merge_worker_to_main(repo, "ralph-1")
        assert result == "success"
        assert (repo / "a.py").exists()
        assert (repo / "b.py").exists()

    @_clean_env
    def test_sequential_merges_from_different_workers(self, tmp_path: Path) -> None:
        """Worker 1 edits file_a, worker 2 edits file_b, both merge."""
        repo = _init_repo(tmp_path)
        wt1 = create_worktree(repo, "ralph-1")
        wt2 = create_worktree(repo, "ralph-2")

        # Worker 1 adds file_a
        (wt1 / "file_a.py").write_text("a\n")
        _git(wt1, "add", ".")
        _git(wt1, "commit", "-m", "Add file_a")

        # Worker 2 adds file_b
        (wt2 / "file_b.py").write_text("b\n")
        _git(wt2, "add", ".")
        _git(wt2, "commit", "-m", "Add file_b")

        # Merge worker 1 first
        r1 = merge_worker_to_main(repo, "ralph-1")
        assert r1 == "success"

        # Merge worker 2 — should still work (no conflict)
        r2 = merge_worker_to_main(repo, "ralph-2")
        assert r2 == "success"

        assert (repo / "file_a.py").exists()
        assert (repo / "file_b.py").exists()


class TestResetWorkerBranch:
    @_clean_env
    def test_reset_after_merge(self, tmp_path: Path) -> None:
        """Worker branch at main HEAD after reset."""
        repo = _init_repo(tmp_path)
        wt = create_worktree(repo, "ralph-1")

        # Commit and merge
        (wt / "feature.py").write_text("code\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Add feature")
        merge_worker_to_main(repo, "ralph-1")

        # Reset
        reset_worker_branch(repo, "ralph-1")

        # Worker HEAD should match main HEAD
        main_head = _git(repo, "rev-parse", "main").stdout.strip()
        worker_head = _git(wt, "rev-parse", "HEAD").stdout.strip()
        assert worker_head == main_head


class TestFullCycle:
    @_clean_env
    def test_full_cycle(self, tmp_path: Path) -> None:
        """Create worktree -> commit -> merge -> reset -> commit again -> merge again."""
        repo = _init_repo(tmp_path)
        wt = create_worktree(repo, "ralph-1")

        # First task
        (wt / "task1.py").write_text("task 1\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Task 1")

        assert merge_worker_to_main(repo, "ralph-1") == "success"
        reset_worker_branch(repo, "ralph-1")

        # Second task
        (wt / "task2.py").write_text("task 2\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Task 2")

        assert merge_worker_to_main(repo, "ralph-1") == "success"

        # Both files on main
        assert (repo / "task1.py").exists()
        assert (repo / "task2.py").exists()

    @_clean_env
    def test_conflict_leaves_branch_recoverable(self, tmp_path: Path) -> None:
        """After conflict, branch commits are still accessible."""
        repo = _init_repo(tmp_path)
        wt = create_worktree(repo, "ralph-1")

        # Conflict setup
        (repo / "README.md").write_text("main change\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "Main change")

        (wt / "README.md").write_text("worker change\n")
        _git(wt, "add", ".")
        _git(wt, "commit", "-m", "Worker change")

        assert merge_worker_to_main(repo, "ralph-1") == "conflict"

        # Branch commits should still be accessible
        log = _git(repo, "log", "ralph-1", "--oneline")
        assert "Worker change" in log.stdout

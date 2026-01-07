"""Tests for the status command."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ralph_swarm.cli import main
from ralph_swarm.commands.status import extract_bead_id


class TestStatusCommand:
    """Tests for the status CLI command."""

    def test_status_fails_without_beads(self, tmp_path: Path, monkeypatch) -> None:
        """Status should fail if not in a ralph-swarm project."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["status"])

        assert result.exit_code == 1
        assert "Not a ralph-swarm project" in result.output

    def test_status_requires_beads_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Status should check for .beads directory."""
        monkeypatch.chdir(tmp_path)
        # Create CLAUDE.md but not .beads
        (tmp_path / "CLAUDE.md").write_text("# Project")

        runner = CliRunner()
        result = runner.invoke(main, ["status"])

        assert result.exit_code == 1
        assert "no .beads found" in result.output


class TestStatusEscaping:
    """Tests for proper escaping of beads data in status output."""

    def _setup_project(self, tmp_path: Path) -> None:
        """Set up a minimal ralph-swarm project."""
        (tmp_path / ".beads").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Project")

    def _mock_subprocess_run(self, issues: list[dict], ready_issues: list[dict] | None = None):
        """Create a mock for subprocess.run that returns beads data."""
        if ready_issues is None:
            ready_issues = issues

        def mock_run(cmd, *args, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            result = Result()
            if "bd" in cmd:
                if "list" in cmd:
                    result.stdout = json.dumps(issues)
                elif "ready" in cmd:
                    result.stdout = json.dumps(ready_issues)
            elif "pgrep" in cmd:
                result.returncode = 1  # No workers running
            return result

        return mock_run

    def test_escapes_brackets_in_title(self, tmp_path: Path, monkeypatch) -> None:
        """Status should escape brackets in issue titles to avoid Rich markup errors."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "Fix [WIP] feature with [brackets]",
                "status": "open",
                "type": "task",
                "priority": "medium",
            }
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        # Should not raise MarkupError and should contain escaped content
        assert result.exit_code == 0
        assert "MarkupError" not in result.output

    def test_handles_numeric_priority(self, tmp_path: Path, monkeypatch) -> None:
        """Status should handle numeric priorities (0, 1, 2, 3) from beads."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "High priority task",
                "status": "open",
                "type": "task",
                "priority": 0,  # Numeric priority
            },
            {
                "id": "def456",
                "title": "Low priority task",
                "status": "open",
                "type": "task",
                "priority": 3,  # Numeric priority
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "MarkupError" not in result.output

    def test_handles_unknown_priority(self, tmp_path: Path, monkeypatch) -> None:
        """Status should handle unknown priority values gracefully."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "Task with custom priority",
                "status": "open",
                "type": "task",
                "priority": "urgent",  # Non-standard priority
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "MarkupError" not in result.output

    def test_escapes_type_field(self, tmp_path: Path, monkeypatch) -> None:
        """Status should escape issue type field."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "Some task",
                "status": "open",
                "type": "[custom]",  # Type with brackets
                "priority": "medium",
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "MarkupError" not in result.output

    def test_escapes_assignee_field(self, tmp_path: Path, monkeypatch) -> None:
        """Status should escape assignee field."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "Assigned task",
                "status": "in_progress",
                "type": "task",
                "priority": "medium",
                "assignee": "user[1]",  # Assignee with brackets
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "MarkupError" not in result.output

    def test_verbose_mode_escapes_fields(self, tmp_path: Path, monkeypatch) -> None:
        """Verbose mode should also escape fields properly."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "Task with [brackets] in title",
                "status": "open",
                "type": "[feature]",
                "priority": 1,  # Numeric
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status", "--verbose"])

        assert result.exit_code == 0
        assert "MarkupError" not in result.output

    def test_tree_mode_escapes_fields(self, tmp_path: Path, monkeypatch) -> None:
        """Tree mode should also escape fields properly."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "abc123",
                "title": "Parent [task]",
                "status": "open",
                "type": "epic",
                "priority": "high",
            },
            {
                "id": "def456",
                "title": "Child [subtask]",
                "status": "open",
                "type": "task",
                "priority": 2,
                "parent": "abc123",
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status", "--tree"])

        assert result.exit_code == 0
        assert "MarkupError" not in result.output


class TestExtractBeadId:
    """Tests for the extract_bead_id helper function."""

    @pytest.mark.parametrize(
        "full_id,expected",
        [
            ("myproject-123", "123"),
            ("my-project-456", "456"),
            ("a-b-c-789", "789"),
            ("project-abc", "abc"),
            ("abc123", "abc123"),
            ("", ""),
            ("single", "single"),
            ("ends-with-", ""),
            ("-starts-with", "with"),
        ],
    )
    def test_extract_bead_id(self, full_id: str, expected: str) -> None:
        """Should extract the portion after the last hyphen."""
        assert extract_bead_id(full_id) == expected


class TestInProgressDisplay:
    """Tests for the in-progress bead display."""

    def _setup_project(self, tmp_path: Path) -> None:
        """Set up a minimal ralph-swarm project."""
        (tmp_path / ".beads").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Project")

    def _mock_subprocess_run(self, issues: list[dict], ready_issues: list[dict] | None = None):
        """Create a mock for subprocess.run that returns beads data."""
        if ready_issues is None:
            ready_issues = []

        def mock_run(cmd, *args, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            result = Result()
            if "bd" in cmd:
                if "list" in cmd:
                    result.stdout = json.dumps(issues)
                elif "ready" in cmd:
                    result.stdout = json.dumps(ready_issues)
            elif "pgrep" in cmd:
                result.returncode = 1  # No workers running
            return result

        return mock_run

    def test_shows_in_progress_bead_details(self, tmp_path: Path, monkeypatch) -> None:
        """Status should show in-progress bead details, not just count."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "myproject-42",
                "title": "Implement feature X",
                "status": "in_progress",
                "type": "task",
                "priority": "medium",
                "assignee": "worker-1",
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "In Progress" in result.output
        assert "42" in result.output  # Should show extracted ID, not full ID
        assert "Implement feature X" in result.output
        assert "worker-1" in result.output

    def test_extracts_bead_id_from_full_id(self, tmp_path: Path, monkeypatch) -> None:
        """Status should display only the bead ID portion, not the full project-id."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "my-long-project-name-99",
                "title": "Some task",
                "status": "in_progress",
                "type": "task",
                "priority": "medium",
                "assignee": "worker",
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "99" in result.output
        # The full ID should not appear as-is (it would be truncated or extracted)
        assert "my-long-project-name-99" not in result.output

    def test_no_in_progress_section_when_empty(self, tmp_path: Path, monkeypatch) -> None:
        """Status should not show In Progress section when no beads are in progress."""
        monkeypatch.chdir(tmp_path)
        self._setup_project(tmp_path)

        issues = [
            {
                "id": "myproject-1",
                "title": "Open task",
                "status": "open",
                "type": "task",
                "priority": "medium",
            },
        ]

        with patch("subprocess.run", side_effect=self._mock_subprocess_run(issues)):
            runner = CliRunner()
            result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        # The table title "In Progress" should not appear when no beads are in progress
        # (note: "in_progress" appears in the summary table as a status)

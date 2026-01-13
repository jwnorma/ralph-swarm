"""Tests for the build command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from ralph_swarm.commands.build import get_work_status


class TestGetWorkStatus:
    """Tests for get_work_status function with different beads responses."""

    def test_no_beads_available(self, tmp_path: Path) -> None:
        """Should handle empty beads response."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="[]",
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 0
            assert status["unassigned"] == 0
            assert status["issues"] == []

    def test_single_bead_unassigned(self, tmp_path: Path) -> None:
        """Should handle single unassigned bead."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([
                    {
                        "id": "issue-123",
                        "title": "Fix bug",
                        "status": "ready",
                        "assignee": None,
                    }
                ]),
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 1
            assert status["unassigned"] == 1
            assert len(status["issues"]) == 1
            assert status["issues"][0]["id"] == "issue-123"

    def test_single_bead_assigned(self, tmp_path: Path) -> None:
        """Should handle single assigned bead."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([
                    {
                        "id": "issue-123",
                        "title": "Fix bug",
                        "status": "in_progress",
                        "assignee": "ralph-1",
                    }
                ]),
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 1
            assert status["unassigned"] == 0
            assert len(status["issues"]) == 1

    def test_multiple_beads_mixed(self, tmp_path: Path) -> None:
        """Should handle multiple beads with mixed assignment."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([
                    {
                        "id": "issue-1",
                        "title": "Task 1",
                        "status": "ready",
                        "assignee": None,
                    },
                    {
                        "id": "issue-2",
                        "title": "Task 2",
                        "status": "in_progress",
                        "assignee": "ralph-1",
                    },
                    {
                        "id": "issue-3",
                        "title": "Task 3",
                        "status": "ready",
                        "assignee": None,
                    },
                ]),
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 3
            assert status["unassigned"] == 2
            assert len(status["issues"]) == 3

    def test_all_beads_assigned(self, tmp_path: Path) -> None:
        """Should handle all beads assigned."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([
                    {
                        "id": "issue-1",
                        "title": "Task 1",
                        "status": "in_progress",
                        "assignee": "ralph-1",
                    },
                    {
                        "id": "issue-2",
                        "title": "Task 2",
                        "status": "in_progress",
                        "assignee": "ralph-2",
                    },
                ]),
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 2
            assert status["unassigned"] == 0

    def test_beads_command_fails(self, tmp_path: Path) -> None:
        """Should handle bd command failure gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 0
            assert status["unassigned"] == 0
            assert status["issues"] == []

    def test_invalid_json_response(self, tmp_path: Path) -> None:
        """Should handle invalid JSON response."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="not valid json",
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 0
            assert status["unassigned"] == 0
            assert status["issues"] == []

    def test_missing_assignee_field(self, tmp_path: Path) -> None:
        """Should handle issues without assignee field."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([
                    {
                        "id": "issue-1",
                        "title": "Task 1",
                        "status": "ready",
                        # No assignee field
                    },
                    {
                        "id": "issue-2",
                        "title": "Task 2",
                        "status": "ready",
                        "assignee": None,
                    },
                ]),
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 2
            assert status["unassigned"] == 2  # Both should be unassigned

    def test_empty_assignee_string(self, tmp_path: Path) -> None:
        """Should treat empty string assignee as unassigned."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([
                    {
                        "id": "issue-1",
                        "title": "Task 1",
                        "status": "ready",
                        "assignee": "",
                    },
                ]),
            )
            status = get_work_status(tmp_path)
            assert status["total"] == 1
            assert status["unassigned"] == 1


class TestBeadsShowResponse:
    """Tests for handling bd show responses (list vs dict)."""

    def test_bd_show_returns_list(self) -> None:
        """Should handle bd show returning a list."""
        import json as json_module

        issue_data = json_module.loads('[{"id": "issue-1", "assignee": "ralph-1"}]')

        # Simulate the parsing logic from build.py
        if isinstance(issue_data, list):
            issue_data = issue_data[0] if issue_data else {}
        claimed_by = issue_data.get("assignee")

        assert claimed_by == "ralph-1"

    def test_bd_show_returns_dict(self) -> None:
        """Should handle bd show returning a dict."""
        import json as json_module

        issue_data = json_module.loads('{"id": "issue-1", "assignee": "ralph-2"}')

        # Simulate the parsing logic from build.py
        if isinstance(issue_data, list):
            issue_data = issue_data[0] if issue_data else {}
        claimed_by = issue_data.get("assignee")

        assert claimed_by == "ralph-2"

    def test_bd_show_returns_empty_list(self) -> None:
        """Should handle bd show returning an empty list."""
        import json as json_module

        issue_data = json_module.loads("[]")

        # Simulate the parsing logic from build.py
        if isinstance(issue_data, list):
            issue_data = issue_data[0] if issue_data else {}
        claimed_by = issue_data.get("assignee")

        assert claimed_by is None

    def test_bd_show_invalid_json(self) -> None:
        """Should handle invalid JSON from bd show."""
        try:
            import json as json_module

            json_module.loads("not valid json")
            claimed_by = None
        except json_module.JSONDecodeError:
            claimed_by = None

        assert claimed_by is None


class TestWorkerScriptLogic:
    """Tests for worker script logic patterns."""

    def test_jq_length_with_empty_array(self) -> None:
        """Verify jq 'length' works with empty array."""
        import subprocess

        result = subprocess.run(
            ["jq", "length"],
            input="[]",
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "0"

    def test_jq_length_with_single_item(self) -> None:
        """Verify jq 'length' works with single item."""
        import subprocess

        result = subprocess.run(
            ["jq", "length"],
            input='[{"id": "test"}]',
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "1"

    def test_jq_length_with_multiple_items(self) -> None:
        """Verify jq 'length' works with multiple items."""
        import subprocess

        result = subprocess.run(
            ["jq", "length"],
            input='[{"id": "1"}, {"id": "2"}, {"id": "3"}]',
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "3"

    def test_jq_extract_id_from_array(self) -> None:
        """Verify jq can extract first ID from array."""
        import subprocess

        result = subprocess.run(
            ["jq", "-r", ".[0].id // empty"],
            input='[{"id": "issue-123"}]',
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "issue-123"

    def test_jq_extract_id_from_empty_array(self) -> None:
        """Verify jq handles empty array when extracting ID."""
        import subprocess

        result = subprocess.run(
            ["jq", "-r", ".[0].id // empty"],
            input="[]",
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""

    def test_jq_assignee_from_list(self) -> None:
        """Verify jq can extract assignee from list response."""
        import subprocess

        result = subprocess.run(
            ["jq", "-r", 'if type == "array" then .[0].assignee else .assignee end'],
            input='[{"id": "issue-1", "assignee": "ralph-1"}]',
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "ralph-1"

    def test_jq_assignee_from_dict(self) -> None:
        """Verify jq can extract assignee from dict response."""
        import subprocess

        result = subprocess.run(
            ["jq", "-r", 'if type == "array" then .[0].assignee else .assignee end'],
            input='{"id": "issue-1", "assignee": "ralph-2"}',
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "ralph-2"

    def test_jq_assignee_null_value(self) -> None:
        """Verify jq handles null assignee."""
        import subprocess

        result = subprocess.run(
            ["jq", "-r", 'if type == "array" then .[0].assignee else .assignee end'],
            input='{"id": "issue-1", "assignee": null}',
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "null"

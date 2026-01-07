"""Tests for the init command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from ralph_swarm.cli import main
from ralph_swarm.commands.init import is_initialized


class TestIsInitialized:
    """Tests for is_initialized function."""

    def test_empty_directory_not_initialized(self, tmp_path: Path) -> None:
        """Empty directory should not be considered initialized."""
        assert is_initialized(tmp_path) is False

    def test_beads_directory_means_initialized(self, tmp_path: Path) -> None:
        """Directory with .beads should be considered initialized."""
        (tmp_path / ".beads").mkdir()
        assert is_initialized(tmp_path) is True

    def test_claude_md_means_initialized(self, tmp_path: Path) -> None:
        """Directory with CLAUDE.md should be considered initialized."""
        (tmp_path / "CLAUDE.md").write_text("# Project")
        assert is_initialized(tmp_path) is True

    def test_both_markers_means_initialized(self, tmp_path: Path) -> None:
        """Directory with both markers should be considered initialized."""
        (tmp_path / ".beads").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Project")
        assert is_initialized(tmp_path) is True

    def test_other_files_not_initialized(self, tmp_path: Path) -> None:
        """Directory with other files should not be considered initialized."""
        (tmp_path / "README.md").write_text("# Readme")
        (tmp_path / "src").mkdir()
        assert is_initialized(tmp_path) is False


class TestInitCommand:
    """Tests for the init CLI command."""

    def test_init_fails_when_already_initialized_beads(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Init should fail if .beads exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".beads").mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 1
        assert "already initialized" in result.output

    def test_init_fails_when_already_initialized_claude_md(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Init should fail if CLAUDE.md exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# Existing")

        runner = CliRunner()
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 1
        assert "already initialized" in result.output

    def test_init_shows_removal_instructions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Init should show how to remove existing files."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".beads").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Existing")

        runner = CliRunner()
        result = runner.invoke(main, ["init"])

        assert "rm -rf .beads" in result.output
        assert "rm CLAUDE.md" in result.output

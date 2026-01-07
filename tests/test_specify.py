"""Tests for the specify command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from ralph_swarm.cli import main
from ralph_swarm.commands.specify import build_prior_art_section, get_spec_status


class TestGetSpecStatus:
    """Tests for get_spec_status function."""

    def test_no_specs_directory(self, tmp_path: Path) -> None:
        """Should return empty status when no specs dir exists."""
        status = get_spec_status(tmp_path)
        assert status["exists"] is False
        assert status["files"] == []
        assert status["has_v0"] is False

    def test_empty_specs_directory(self, tmp_path: Path) -> None:
        """Should return exists but no files."""
        (tmp_path / "specs").mkdir()
        status = get_spec_status(tmp_path)
        assert status["exists"] is True
        assert status["files"] == []
        assert status["has_v0"] is False

    def test_with_v0_spec(self, tmp_path: Path) -> None:
        """Should detect v0 spec files."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "v0.md").write_text("# V0")

        status = get_spec_status(tmp_path)
        assert status["has_v0"] is True
        assert "v0.md" in status["files"]
        assert "v0.md" in status["v0_files"]

    def test_with_v0_component_specs(self, tmp_path: Path) -> None:
        """Should detect v0-* component specs."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "v0-frontend.md").write_text("# Frontend")
        (specs_dir / "v0-backend.md").write_text("# Backend")

        status = get_spec_status(tmp_path)
        assert status["has_v0"] is True
        assert len(status["v0_files"]) == 2
        assert "v0-frontend.md" in status["v0_files"]
        assert "v0-backend.md" in status["v0_files"]

    def test_non_v0_specs_dont_count(self, tmp_path: Path) -> None:
        """Non-v0 specs should not trigger has_v0."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "authentication.md").write_text("# Auth")
        (specs_dir / "overview.md").write_text("# Overview")

        status = get_spec_status(tmp_path)
        assert status["has_v0"] is False
        assert len(status["files"]) == 2


class TestBuildPriorArtSection:
    """Tests for build_prior_art_section function."""

    def test_no_prior_art(self) -> None:
        """Should return placeholder when no prior art."""
        section = build_prior_art_section([])
        assert "No prior art references provided" in section

    def test_single_reference(self) -> None:
        """Should format single reference."""
        section = build_prior_art_section(["https://example.com/docs"])
        assert "https://example.com/docs" in section
        assert "Review these projects" in section

    def test_multiple_references(self) -> None:
        """Should format multiple references."""
        refs = [
            "https://github.com/example/repo",
            "https://docs.example.com",
            "Similar tool: xyz",
        ]
        section = build_prior_art_section(refs)
        for ref in refs:
            assert ref in section


class TestSpecifyCommand:
    """Tests for the specify CLI command."""

    def test_specify_requires_claude_md(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Specify should fail without CLAUDE.md."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["specify", "--dry-run"])

        assert result.exit_code == 1
        assert "CLAUDE.md not found" in result.output

    def test_specify_dry_run_initial(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dry run should show initial prompt when no v0 exists (iterative mode)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# Project")

        runner = CliRunner()
        # Select iterative mode (option 1)
        result = runner.invoke(main, ["specify", "--dry-run"], input="1\n")

        assert result.exit_code == 0
        assert "Initial V0" in result.output or "V0 Philosophy" in result.output

    def test_specify_full_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--full flag should trigger full specification mode."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# Project")

        runner = CliRunner()
        result = runner.invoke(main, ["specify", "--dry-run", "--full"])

        assert result.exit_code == 0
        assert "Full Specification" in result.output

    def test_specify_interactive_full_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Selecting option 2 should trigger full specification mode."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# Project")

        runner = CliRunner()
        # Select full mode (option 2)
        result = runner.invoke(main, ["specify", "--dry-run"], input="2\n")

        assert result.exit_code == 0
        assert "Full Specification" in result.output

    def test_specify_creates_specs_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Specify should create specs directory if missing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# Project")

        runner = CliRunner()
        # Use dry-run and --full to avoid interactive prompts
        result = runner.invoke(main, ["specify", "--dry-run", "--full"])

        assert result.exit_code == 0
        assert (tmp_path / "specs").exists()

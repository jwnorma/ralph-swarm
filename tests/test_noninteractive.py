"""Tests for non-interactive (one-shot) mode."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ralph_swarm.cli import main
from ralph_swarm.noninteractive import (
    ONE_SHOT_APPENDIX,
    format_answers_section,
    load_json_input,
)


class TestLoadJsonInput:
    """Tests for load_json_input."""

    def test_missing_file_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            load_json_input(tmp_path / "nope.json", required=[])

    def test_invalid_json_exits(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        with pytest.raises(SystemExit):
            load_json_input(p, required=[])

    def test_non_object_exits(self, tmp_path: Path) -> None:
        p = tmp_path / "arr.json"
        p.write_text("[1, 2]")
        with pytest.raises(SystemExit):
            load_json_input(p, required=[])

    def test_missing_required_key_exits(self, tmp_path: Path) -> None:
        p = tmp_path / "in.json"
        p.write_text(json.dumps({"goal": "x"}))
        with pytest.raises(SystemExit):
            load_json_input(p, required=["topic"])

    def test_blank_required_value_exits(self, tmp_path: Path) -> None:
        p = tmp_path / "in.json"
        p.write_text(json.dumps({"topic": "   "}))
        with pytest.raises(SystemExit):
            load_json_input(p, required=["topic"])

    def test_valid_file_returns_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "in.json"
        p.write_text(json.dumps({"topic": "caching"}))
        data = load_json_input(p, required=["topic"])
        assert data == {"topic": "caching"}


class TestFormatAnswersSection:
    """Tests for format_answers_section."""

    def test_empty(self) -> None:
        assert format_answers_section({}) == ""

    def test_context_only(self) -> None:
        out = format_answers_section({"context": "keep it small"})
        assert "keep it small" in out

    def test_answers_dict(self) -> None:
        out = format_answers_section({"answers": {"Storage": "SQLite"}})
        assert "Storage" in out
        assert "SQLite" in out

    def test_answers_list(self) -> None:
        out = format_answers_section({"answers": ["use TOML", "no daemon"]})
        assert "use TOML" in out
        assert "no daemon" in out


class TestOneShotAppendix:
    def test_appendix_forbids_questions(self) -> None:
        assert "Do NOT ask" in ONE_SHOT_APPENDIX


class TestSpecifyInputMode:
    """Tests for `ralph specify --input`."""

    def _setup_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Project")

    def test_missing_input_file_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_project(tmp_path, monkeypatch)
        result = CliRunner().invoke(main, ["specify", "--input", str(tmp_path / "nope.json")])
        assert result.exit_code == 1

    def test_incremental_requires_feature(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "answers.json"
        p.write_text(json.dumps({"mode": "incremental"}))
        result = CliRunner().invoke(main, ["specify", "--input", str(p)])
        assert result.exit_code == 1
        assert "feature" in result.output.lower()

    def test_invalid_mode_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "answers.json"
        p.write_text(json.dumps({"mode": "bogus"}))
        result = CliRunner().invoke(main, ["specify", "--input", str(p)])
        assert result.exit_code == 1
        assert "Invalid mode" in result.output

    def test_dry_run_builds_prompt_without_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "answers.json"
        p.write_text(
            json.dumps(
                {
                    "mode": "full",
                    "prior_art": ["https://example.com"],
                    "answers": {"Storage": "SQLite"},
                }
            )
        )
        result = CliRunner().invoke(main, ["specify", "--input", str(p), "--dry-run"])
        assert result.exit_code == 0
        assert "Full Specification" in result.output
        assert "https://example.com" in result.output
        assert "SQLite" in result.output
        assert "ONE-SHOT MODE" in result.output
        # Must not hit any interactive prompt
        assert "Ready to start?" not in result.output

    def test_runs_headless(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "answers.json"
        p.write_text(json.dumps({"mode": "full"}))

        calls: dict = {}

        def fake_run_one_shot(prompt, model, verbose, cwd):
            calls["prompt"] = prompt
            (tmp_path / "specs").mkdir(exist_ok=True)
            (tmp_path / "specs" / "overview.md").write_text("# Overview")

        with patch("ralph_swarm.commands.specify.run_one_shot", side_effect=fake_run_one_shot):
            result = CliRunner().invoke(main, ["specify", "--input", str(p)])

        assert result.exit_code == 0
        assert "overview.md" in result.output
        assert "ONE-SHOT MODE" in calls["prompt"]

    def test_reports_when_no_specs_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "answers.json"
        p.write_text(json.dumps({}))

        with patch("ralph_swarm.commands.specify.run_one_shot", return_value=None):
            result = CliRunner().invoke(main, ["specify", "--input", str(p)])

        assert result.exit_code == 0
        assert "No new spec files" in result.output


class TestResearchInputMode:
    """Tests for `ralph research --input`."""

    def _setup_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Project")

    def test_missing_topic_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "research.json"
        p.write_text(json.dumps({"goal": "learn"}))
        result = CliRunner().invoke(main, ["research", "--input", str(p)])
        assert result.exit_code == 1
        assert "topic" in result.output.lower()

    def test_dry_run_builds_prompt_without_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "research.json"
        p.write_text(json.dumps({"topic": "caching libraries", "goal": "pick one"}))
        result = CliRunner().invoke(main, ["research", "--input", str(p), "--dry-run"])
        assert result.exit_code == 0
        assert "caching libraries" in result.output
        assert "pick one" in result.output
        assert "ONE-SHOT MODE" in result.output
        assert "Ready to start?" not in result.output

    def test_goal_default_when_omitted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "research.json"
        p.write_text(json.dumps({"topic": "caching"}))
        result = CliRunner().invoke(main, ["research", "--input", str(p), "--dry-run"])
        assert result.exit_code == 0

    def test_runs_headless(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup_project(tmp_path, monkeypatch)
        p = tmp_path / "research.json"
        p.write_text(json.dumps({"topic": "caching"}))

        calls: dict = {}

        def fake_run_one_shot(prompt, model, verbose, cwd):
            calls["prompt"] = prompt
            rd = tmp_path / "docs" / "research"
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "caching.md").write_text("# Caching")

        with patch("ralph_swarm.commands.research.run_one_shot", side_effect=fake_run_one_shot):
            result = CliRunner().invoke(main, ["research", "--input", str(p)])

        assert result.exit_code == 0
        assert "caching.md" in result.output
        assert "caching" in calls["prompt"]

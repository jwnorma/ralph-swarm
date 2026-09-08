"""Tests for the prompts module."""

from pathlib import Path

import pytest

from ralph_swarm.prompts import load_prompt, load_prompt_with_vars


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_plan_prompt(self) -> None:
        """Should load the plan prompt."""
        prompt = load_prompt("system/plan_initial")
        assert "# Ralph Planning Mode" in prompt
        assert "bd ready --json" in prompt

    def test_load_build_prompt(self) -> None:
        """Should load the build prompt."""
        prompt = load_prompt("system/build")
        assert "# Ralph Build Mode" in prompt
        assert "{worker_id}" in prompt  # Should have placeholder

    def test_build_prompt_has_final_rebase_step(self) -> None:
        """Worker must rebase onto main and re-run gates before finishing."""
        prompt = load_prompt("system/build")
        assert "git rebase main" in prompt
        assert "git rebase --abort" in prompt
        assert "git rebase --continue" in prompt
        # Rebase is the prescribed final step only, not ad-hoc git surgery
        assert "Rebase onto main ONLY as the final step 9" in prompt

    def test_load_specify_initial_prompt(self) -> None:
        """Should load the initial specify prompt."""
        prompt = load_prompt("system/specify_initial")
        assert "# Ralph Specify Mode - Initial V0" in prompt
        assert "V0 Philosophy" in prompt

    def test_load_specify_incremental_prompt(self) -> None:
        """Should load the incremental specify prompt."""
        prompt = load_prompt("system/specify_incremental")
        assert "# Ralph Specify Mode - Add Feature" in prompt
        assert "{prior_art_section}" in prompt

    def test_load_nonexistent_prompt_raises(self) -> None:
        """Should raise FileNotFoundError for missing prompt."""
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent")


class TestLoadPromptWithVars:
    """Tests for load_prompt_with_vars function."""

    def test_substitutes_worker_id(self) -> None:
        """Should substitute worker_id variable."""
        prompt = load_prompt_with_vars("system/build", worker_id="ralph-42")
        assert "ralph-42" in prompt
        assert "{worker_id}" not in prompt

    def test_multiple_substitutions(self) -> None:
        """Should substitute all occurrences of a variable."""
        prompt = load_prompt_with_vars("system/build", worker_id="test-worker")
        # worker_id appears multiple times in the build prompt
        assert prompt.count("test-worker") >= 2
        assert "{worker_id}" not in prompt

    def test_preserves_other_content(self) -> None:
        """Substitution should not affect other content."""
        prompt = load_prompt_with_vars("system/build", worker_id="ralph-1")
        assert "# Ralph Build Mode" in prompt
        assert "bd ready --unassigned" in prompt


class TestBdCommandSyntax:
    """Guard against retired bd CLI syntax creeping back into prompts.

    bd evolves quickly; when a command form is retired (e.g.
    `bd dep add X --blocks Y`, removed in bd 1.2), the prompts must move
    to the new form. See tests/test_bd_compat.py for live verification
    of the current syntax against the installed binary.
    """

    # (retired syntax, current replacement) pairs
    RETIRED_SYNTAX = [
        ("bd dep add", "bd dep <blocker> --blocks <blocked>"),
        ("-p high", "-p P0-P4 (e.g. P1)"),
        ("-p medium", "-p P0-P4 (e.g. P2)"),
        ("-p low", "-p P0-P4"),
    ]

    @pytest.fixture()
    def prompt_files(self) -> list[Path]:
        prompts_dir = Path(__file__).parent.parent / "src" / "ralph_swarm" / "prompts"
        files = sorted(prompts_dir.rglob("*.md"))
        assert files, f"no prompt files found under {prompts_dir}"
        return files

    def test_no_retired_bd_syntax(self, prompt_files: list[Path]) -> None:
        """No prompt may teach a retired bd command form."""
        for file in prompt_files:
            content = file.read_text()
            for retired, _replacement in self.RETIRED_SYNTAX:
                assert retired not in content, (
                    f"{file.relative_to(prompt_files[0].parents[2])} teaches retired "
                    f"bd syntax '{retired}'"
                )

    def test_current_dep_syntax_present(self) -> None:
        """Planning prompts must teach the current `bd dep` form."""
        for name in ("system/plan_initial", "system/plan_incremental"):
            prompt = load_prompt(name)
            assert "bd dep <blocker> --blocks <blocked>" in prompt, f"{name} missing dep syntax"

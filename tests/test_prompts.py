"""Tests for the prompts module."""

import pytest

from ralph_swarm.prompts import load_prompt, load_prompt_with_vars


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_plan_prompt(self) -> None:
        """Should load the plan prompt."""
        prompt = load_prompt("plan")
        assert "# Ralph Planning Mode" in prompt
        assert "bd prime" in prompt

    def test_load_build_prompt(self) -> None:
        """Should load the build prompt."""
        prompt = load_prompt("build")
        assert "# Ralph Build Mode" in prompt
        assert "{worker_id}" in prompt  # Should have placeholder

    def test_load_specify_initial_prompt(self) -> None:
        """Should load the initial specify prompt."""
        prompt = load_prompt("specify_initial")
        assert "# Ralph Specify Mode - Initial V0" in prompt
        assert "V0 Philosophy" in prompt

    def test_load_specify_incremental_prompt(self) -> None:
        """Should load the incremental specify prompt."""
        prompt = load_prompt("specify_incremental")
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
        prompt = load_prompt_with_vars("build", worker_id="ralph-42")
        assert "ralph-42" in prompt
        assert "{worker_id}" not in prompt

    def test_multiple_substitutions(self) -> None:
        """Should substitute all occurrences of a variable."""
        prompt = load_prompt_with_vars("build", worker_id="test-worker")
        # worker_id appears multiple times in the build prompt
        assert prompt.count("test-worker") >= 2
        assert "{worker_id}" not in prompt

    def test_preserves_other_content(self) -> None:
        """Substitution should not affect other content."""
        prompt = load_prompt_with_vars("build", worker_id="ralph-1")
        assert "# Ralph Build Mode" in prompt
        assert "bd prime" in prompt

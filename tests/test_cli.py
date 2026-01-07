"""Tests for the main CLI."""

from click.testing import CliRunner

from ralph_swarm.cli import main


class TestCLI:
    """Tests for the main CLI group."""

    def test_help_shows_all_commands(self) -> None:
        """Help should list all available commands."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.output
        assert "specify" in result.output
        assert "plan" in result.output
        assert "build" in result.output
        assert "status" in result.output
        assert "cleanup" in result.output

    def test_version_flag(self) -> None:
        """--version should show version."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_unknown_command_fails(self) -> None:
        """Unknown command should fail with helpful message."""
        runner = CliRunner()
        result = runner.invoke(main, ["unknown"])

        assert result.exit_code != 0
        assert "No such command" in result.output

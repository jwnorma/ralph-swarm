"""Non-interactive (one-shot) execution support for specify and research.

Loads a JSON answers file and runs Claude Code headlessly via `claude -p`,
so the full pipeline (init -> research -> specify -> plan -> build) can run
without a human on the other end of the session.

JSON structure for `ralph specify --input`:
    {
        "mode": "full",            # "full" | "initial" | "incremental" (default: full)
        "feature": "auth",         # required when mode == "incremental"
        "prior_art": ["url"],      # optional reference links
        "answers": {"k": "v"},     # optional owner decisions for the agent
        "context": "free-form"     # optional extra notes for the agent
    }

JSON structure for `ralph research --input`:
    {
        "topic": "caching libraries",   # required
        "goal": "pick one for us",      # optional
        "context": "free-form"          # optional extra notes
    }
"""

import json
import subprocess  # noqa: S404
import sys
from pathlib import Path

import click

# Appended to the workflow prompt so the agent never blocks on questions
# that no human will answer.
ONE_SHOT_APPENDIX = """
## ONE-SHOT MODE (override)

This is a non-interactive run. Do NOT ask the user any questions - there is
no human available to answer. Make reasonable, defensible decisions yourself
and proceed autonomously through ALL phases of the workflow. Write every
output file the workflow calls for, then finish. Your final message should
briefly summarize what you created and any decisions you made.
"""


def load_json_input(path: Path, required: list[str]) -> dict:
    """Load and validate a JSON input file.

    Args:
        path: Path to the JSON file.
        required: Keys that must be present (and non-empty for strings).

    Returns:
        Parsed JSON as a dict.

    Exits with a clear error message on invalid JSON or missing keys.
    """
    if not path.exists():
        click.echo(f"Input file not found: {path}", err=True)
        sys.exit(1)

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON in {path}: {e}", err=True)
        sys.exit(1)

    if not isinstance(data, dict):
        click.echo(f"Input file {path} must contain a JSON object.", err=True)
        sys.exit(1)

    missing = [
        k for k in required if k not in data or (isinstance(data[k], str) and not data[k].strip())
    ]
    if missing:
        click.echo(f"Input file {path} is missing required key(s): {', '.join(missing)}.", err=True)
        sys.exit(1)

    return data


def format_answers_section(data: dict) -> str:
    """Render optional `answers` / `context` keys as a prompt section."""
    parts: list[str] = []

    if data.get("context"):
        parts.append(f"## Additional context from the project owner\n\n{data['context']}")

    answers = data.get("answers")
    if isinstance(answers, dict) and answers:
        lines = ["## Owner decisions (pre-answered questions)", ""]
        for key, value in answers.items():
            lines.append(f"- **{key}**: {value}")
        parts.append("\n".join(lines))
    elif isinstance(answers, list) and answers:
        lines = ["## Owner decisions (pre-answered questions)", ""]
        for item in answers:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    if not parts:
        return ""

    return "\n\n" + "\n\n".join(parts) + "\n"


def run_one_shot(prompt: str, model: str, verbose: bool, cwd: Path) -> None:
    """Run a single headless Claude Code session with the given prompt.

    Uses `claude -p` (print mode) with permission prompts disabled, mirroring
    what plan/build already do. Exits non-zero if the session fails.
    """
    cmd = [
        "claude",
        "-p",
        "--dangerously-skip-permissions",
        "--model",
        model,
    ]

    if verbose:
        cmd.extend(["--verbose"])

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=cwd,
        )

        if verbose and result.stdout:
            click.echo(result.stdout)

        if result.returncode != 0:
            click.echo("One-shot session ended with error:", err=True)
            if result.stderr:
                click.echo(result.stderr, err=True)
            sys.exit(1)
    except FileNotFoundError:
        click.echo("Claude CLI not found. Is it installed?", err=True)
        sys.exit(1)

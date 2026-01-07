"""Prompt loading utilities."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt file by name.

    Args:
        name: Prompt name (without .md extension)

    Returns:
        Prompt content as string
    """
    prompt_file = PROMPTS_DIR / f"{name}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt not found: {name}")
    return prompt_file.read_text()


def load_prompt_with_vars(name: str, **variables: str) -> str:
    """Load a prompt and substitute variables.

    Args:
        name: Prompt name (without .md extension)
        **variables: Variables to substitute (e.g., worker_id="ralph-1")

    Returns:
        Prompt content with variables substituted
    """
    content = load_prompt(name)
    for key, value in variables.items():
        content = content.replace(f"{{{key}}}", value)
    return content

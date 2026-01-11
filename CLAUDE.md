# ralph-swarm

AI-powered autonomous development swarm orchestrator using Claude Code and Beads.

## Development

This project uses `uv` for Python package management. Always use `uv run` for Python commands:

```bash
uv run python ...
uv run pytest ...
uv run ralph ...
```

## Build & Test

```bash
./build.sh test      # Run tests
./build.sh lint      # Run linter
./build.sh format    # Format code
./build.sh publish-local  # Build and install locally
```

## Project Structure

```
src/ralph_swarm/
├── cli.py              # Main CLI entry point
├── commands/           # CLI commands (init, research, specify, plan, build, etc.)
└── prompts/            # Prompt templates
    ├── system/         # Main workflow prompts
    └── agents/         # Subagent prompts
tests/                  # Test files
```

## Workflow

The main workflow phases are:
1. `ralph init` - Project setup
2. `ralph research` - Research technologies (optional)
3. `ralph specify` - Define specifications
4. `ralph plan` - Create epics and tasks
5. `ralph build` - Implement with worker swarm

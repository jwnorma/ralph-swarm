# Ralph Swarm

AI-powered autonomous development swarm orchestrator. Uses Claude Code and Beads to manage iterative, spec-driven development.

## Installation

Ensure you have the [required dependencies](#dependencies) installed first.

```bash
# Clone the repository
git clone https://github.com/your-org/ralph-swarm.git
cd ralph-swarm

# Build and install locally
./build.sh publish-local
```

After installation, the `ralph` command will be available globally.

## Quick Start

```bash
# Create and enter project directory
mkdir my-project && cd my-project

# Initialize the project
ralph init

# Define V0 specifications interactively
ralph specify

# Create epics and stories from specs
ralph plan

# Start building with workers
ralph build --workers 2

# Check progress
ralph status
```

## Commands

### `ralph init`

Initialize a ralph-swarm project in the current directory:
- Define objective and problem statement
- Choose tech stack
- Initialize git and beads
- Create CLAUDE.md scaffold

Fails fast if the project is already initialized.

### `ralph specify`

Build specifications interactively. Two modes available:

**Iterative mode (default):**
- Start with minimal V0 specs
- Add features incrementally as needed
- Best for most projects - ship early, iterate often

**Full specification mode:**
- Comprehensive Q&A to fully understand the project upfront
- Claude asks many questions before writing any specs
- Best for complex projects where upfront planning saves time

Options:
- `--model, -m` - Model to use (sonnet, opus, haiku)
- `--full` - Use full specification mode (skip interactive selection)
- `--verbose, -v` - Show real-time output
- `--dry-run` - Show prompt without executing

Examples:
```bash
ralph specify          # Interactive mode selection
ralph specify --full   # Full specification mode directly
```

### `ralph plan`

Run planning mode to create structured work breakdown:
- Analyzes specs and existing code
- Creates epics for major features
- Breaks down into actionable tasks
- Links dependencies

Options:
- `--model, -m` - Model to use (sonnet, opus, haiku)
- `--iterations, -n` - Number of planning iterations
- `--verbose, -v` - Show real-time output
- `--dry-run` - Show prompt without executing

### `ralph build`

Run build mode with worker swarm:
- Picks up issues from beads
- Implements with full code quality checks
- Supports parallel workers

Options:
- `--workers, -w` - Number of parallel workers (default: 1)
- `--model, -m` - Model to use (sonnet, opus, haiku)
- `--once` - Single iteration instead of looping
- `--auto-shutdown` - Shutdown when no work remains
- `--idle-limit` - Iterations before auto-shutdown
- `--verbose, -v` - Show real-time output

### `ralph status`

Show project progress:
- Issue summary by status and type
- Ready work queue
- Running workers
- Progress bar

Options:
- `--verbose, -v` - Show all issues
- `--tree, -t` - Show dependency tree

### `ralph cleanup`

Clean up orphaned work from crashed workers:
- Finds in-progress issues without active workers
- Resets them to open status

Options:
- `--force, -f` - Skip confirmation
- `--discard-changes` - Also discard uncommitted changes

## Philosophy

1. **Spec-driven**: Features follow specifications
2. **Small units**: Do the smallest useful work
3. **Two paths**: V0-first for fast iteration, or full specification for complex projects
4. **Visibility**: Always show what's happening

## Dependencies

- [Claude Code](https://claude.com/claude-code) - AI coding assistant
- [Beads](https://github.com/steveyegge/beads) - Issue tracking
- Git

## License

MIT

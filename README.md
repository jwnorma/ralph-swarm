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

---

## Workflow Guide

Ralph Swarm follows a four-stage workflow that takes a project from idea to implementation. Each stage builds on the previous one, creating a structured pipeline for autonomous development.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RALPH SWARM WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
    │   INIT   │ ──▶  │ SPECIFY  │ ──▶  │   PLAN   │ ──▶  │  BUILD   │
    └──────────┘      └──────────┘      └──────────┘      └──────────┘
         │                 │                 │                 │
         ▼                 ▼                 ▼                 ▼
    Project setup    Spec documents     Beads issues      Working code
    CLAUDE.md        in specs/          (epics/tasks)     Git commits
    Subagents        Review rules       Dependencies      ADRs

                                                    ┌─────────────────┐
                                                    │  STATUS/CLEANUP │
                                                    │   (anytime)     │
                                                    └─────────────────┘
```

---

### Stage 1: Init

**Command:** `ralph init`

**Purpose:** Bootstrap a new project with the required structure and configuration for ralph-swarm to operate.

#### What It Does

1. Prompts for project information:
   - Project objective (what it does)
   - Problem statement (why it exists)
   - Tech stack (languages, frameworks, libraries)
2. Initializes git repository (if not exists)
3. Initializes beads issue tracking
4. Creates project scaffolding

#### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Objective | User prompt | What the project does |
| Problem | User prompt | What problem it solves |
| Tech Stack | User prompt | Technologies to use |

#### Outputs

| Output | Location | Description |
|--------|----------|-------------|
| `CLAUDE.md` | Project root | Project context for Claude agents |
| `specs/` | Directory | Empty directory for specifications |
| `adr/` | Directory | Empty directory for Architecture Decision Records |
| `.beads/` | Directory | Beads issue tracking database |
| `.claude/agents/` | Directory | Subagent definitions |
| `build.sh` | Project root | Build script scaffold |
| `.gitignore` | Project root | Standard ignores |

#### Subagents Created

| Agent | File | Purpose |
|-------|------|---------|
| `code-reviewer` | `.claude/agents/code-reviewer.md` | Reviews code changes for quality and security |
| `are-we-done` | `.claude/agents/are-we-done.md` | Verifies build/tests pass before task completion |
| `adr` | `.claude/agents/adr.md` | Documents architectural decisions |

#### Example Session

```
$ mkdir my-cli-tool && cd my-cli-tool
$ ralph init

╭──────────────────────────────────────────────╮
│ Ralph Swarm - Project Initialization         │
│ Directory: my-cli-tool                       │
╰──────────────────────────────────────────────╯

What is the main objective of this project?
> A CLI tool for managing Docker containers

What problem does it solve?
> Simplifies common Docker operations for developers

What tech stack will you use?
> Python, Click, Rich, Docker SDK

╭──────────────────────────────────────────────╮
│ Project initialized successfully!            │
│                                              │
│ Next steps:                                  │
│   1. Run ralph specify to define V0 specs   │
│   2. Run ralph plan to create epics         │
│   3. Run ralph build to start building      │
╰──────────────────────────────────────────────╯
```

---

### Stage 2: Specify

**Command:** `ralph specify`

**Purpose:** Define what the project should do through interactive specification writing. Creates detailed requirements that drive planning and implementation.

#### What It Does

1. Launches an interactive Claude session
2. Analyzes CLAUDE.md and any prior art references
3. Works with user to define V0 (minimum viable) scope
4. Creates specification documents
5. Updates code-reviewer with project-specific rules

#### Modes

| Mode | Flag | Best For |
|------|------|----------|
| **Iterative** (default) | none | Most projects - start small, iterate |
| **Incremental** | (automatic when V0 exists) | Adding features to existing specs |
| **Full** | `--full` | Complex projects needing upfront planning |

#### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `CLAUDE.md` | Project root | Project context and objectives |
| Prior art references | User prompt | URLs/repos for inspiration |
| Existing specs | `specs/` | Previous specifications (incremental mode) |

#### Outputs

| Output | Location | Description |
|--------|----------|-------------|
| `v0-*.md` | `specs/` | V0 specification documents |
| Component specs | `specs/` | Separate specs for distinct components |
| Updated review rules | `.claude/agents/code-reviewer.md` | Project-specific code review criteria |

#### Specification Structure

Each spec file follows this structure:

```markdown
# <Component> - V0 Specification

## Purpose
One sentence describing the component's role.

## Core Features
- Feature 1: Brief description
- Feature 2: Brief description
(3-5 features maximum for V0)

## User Flows
### Primary Flow
1. User does X
2. System responds with Y
3. Result is Z

## Technical Approach
- Key technology choices
- Integration points

## Out of Scope (V0)
- Deferred feature 1
- Deferred feature 2

## Success Criteria
- Measurable completion criteria
```

#### Example Session

```
$ ralph specify

╭──────────────────────────────────────────────╮
│ Ralph Swarm - Specify Mode                   │
│ Initial V0 | Model: opus                     │
╰──────────────────────────────────────────────╯

Prior Art
Are there existing projects we should look at?
Reference (or press Enter to skip): https://github.com/docker/compose
  Added: https://github.com/docker/compose
Reference (or press Enter to skip):

How this works:
1. An interactive Claude session will start
2. Work with Claude to define your specifications
3. Claude will create spec files in specs/
4. When finished, type /exit or press Ctrl+C

Ready to start? [y/n]: y

# Claude session begins...
# After completion:

New specs created:
  ● specs/v0-cli.md
  ● specs/v0-docker-client.md
```

---

### Stage 3: Plan

**Command:** `ralph plan`

**Purpose:** Transform specifications into actionable work items. Creates a structured backlog of epics and tasks in beads.

#### What It Does

1. Loads workflow context via `bd prime`
2. Reads all specification documents
3. Scans existing code for gaps
4. Creates epics for major features
5. Breaks epics into small, actionable tasks
6. Links dependencies between tasks
7. Ensures documentation tasks exist

#### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `CLAUDE.md` | Project root | Project context |
| Spec files | `specs/` | Requirements to implement |
| Existing code | `src/`, etc. | Current implementation state |
| Existing issues | `.beads/` | Previously created work items |

#### Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Epics | `.beads/` | High-level feature groupings |
| Tasks | `.beads/` | Actionable implementation items |
| Dependencies | `.beads/` | Blocking relationships |

#### Issue Types Created

| Type | Purpose | Size |
|------|---------|------|
| `epic` | Groups related tasks | Large (decomposed, not implemented) |
| `task` | Implementation work | Small (1-2 hours of work) |
| `bug` | Defect fixes | Varies |
| `feature` | New capabilities | Small-medium |

#### Planning Rules

- Every epic includes a documentation task
- Tasks are small and focused (1-2 hours)
- Foundation/infrastructure before features
- Tests alongside implementation
- Clear dependencies prevent parallel conflicts

#### Example Session

```
$ ralph plan

╭──────────────────────────────────────────────╮
│ Ralph Swarm - Planning Mode                  │
│ Model: opus                                  │
╰──────────────────────────────────────────────╯

┌─────────────────────────────────────────────┐
│ Current Beads State                         │
├─────────────────────────────────────────────┤
│ Total Issues    │ 0                         │
│ Open            │ 0                         │
│ In Progress     │ 0                         │
│ Closed          │ 0                         │
└─────────────────────────────────────────────┘

Running Claude in planning mode...

Created 12 new issue(s)

Ready issues:
  my-cli-tool-1  [task] Set up project structure
  my-cli-tool-2  [task] Implement Docker client wrapper
  my-cli-tool-3  [task] Create CLI entry point

╭──────────────────────────────────────────────╮
│ Planning complete!                           │
│                                              │
│ Next steps:                                  │
│   1. Review: bd list                         │
│   2. Check deps: bd ready                    │
│   3. Start building: ralph build             │
╰──────────────────────────────────────────────╯
```

---

### Stage 4: Build

**Command:** `ralph build`

**Purpose:** Execute implementation by running autonomous worker agents that pick up tasks, implement them, and verify quality.

#### What It Does

1. Each worker loads context via `bd prime`
2. Claims an unassigned task from the ready queue
3. Implements the task (or decomposes if it's an epic)
4. Documents architectural decisions (via `adr` subagent)
5. Reviews changes (via `code-reviewer` subagent)
6. Verifies build/tests pass (via `are-we-done` subagent)
7. Commits and closes the task
8. Loops to pick up next task

#### Build Loop Flowchart

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BUILD WORKER LOOP                            │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │ Load Context│ ◀──────────────────────────────────────────┐
    │  bd prime   │                                            │
    └──────┬──────┘                                            │
           │                                                   │
           ▼                                                   │
    ┌─────────────┐     No work                               │
    │ Check Queue │ ───────────────────▶ (idle/shutdown)      │
    │ bd ready    │                                            │
    └──────┬──────┘                                            │
           │ Has work                                          │
           ▼                                                   │
    ┌─────────────┐                                            │
    │ Claim Task  │                                            │
    │ bd update   │                                            │
    └──────┬──────┘                                            │
           │                                                   │
           ▼                                                   │
    ┌─────────────┐     Is Epic?     ┌─────────────┐          │
    │ Check Type  │ ────────────────▶│ Decompose   │──────────┤
    └──────┬──────┘                  │ into tasks  │          │
           │ Task/Bug/Feature        └─────────────┘          │
           ▼                                                   │
    ┌─────────────┐                                            │
    │ Implement   │                                            │
    │             │                                            │
    └──────┬──────┘                                            │
           │                                                   │
           ▼                                                   │
    ┌─────────────┐     Made arch     ┌─────────────┐         │
    │ ADR Check   │ ─────decisions───▶│ adr agent   │         │
    └──────┬──────┘                   └──────┬──────┘         │
           │◀────────────────────────────────┘                │
           ▼                                                   │
    ┌─────────────┐                                            │
    │code-reviewer│                                            │
    │   agent     │                                            │
    └──────┬──────┘                                            │
           │                                                   │
           ▼                                                   │
    ┌─────────────┐     NOT READY     ┌─────────────┐         │
    │are-we-done  │ ─────────────────▶│ Fix Issues  │─────┐   │
    │   agent     │                   └─────────────┘     │   │
    └──────┬──────┘                          ▲            │   │
           │ READY                           └────────────┘   │
           ▼                                                   │
    ┌─────────────┐                                            │
    │ Commit &    │                                            │
    │ Close Task  │                                            │
    └──────┬──────┘                                            │
           │                                                   │
           └───────────────────────────────────────────────────┘
```

#### Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Ready tasks | `.beads/` | Unassigned tasks with satisfied dependencies |
| `CLAUDE.md` | Project root | Build/test instructions |
| `adr/` | Directory | Existing architectural decisions |
| Existing code | Project | Current implementation |

#### Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Implementation code | Project | New/modified source files |
| Tests | Project | Test files for new code |
| Git commits | `.git/` | Atomic commits per task |
| ADRs | `adr/` | Architectural decision records |
| Closed tasks | `.beads/` | Completed work items |
| New issues | `.beads/` | Discovered bugs/follow-ups |

#### Subagent Usage During Build

| Subagent | When Used | Must Pass? |
|----------|-----------|------------|
| `adr` | After adding dependencies or making architectural choices | No (advisory) |
| `code-reviewer` | After implementation, before verification | CRITICAL issues block |
| `are-we-done` | Before closing any task | Yes, must return "READY TO COMPLETE" |

#### Worker Modes

| Mode | Flag | Behavior |
|------|------|----------|
| Single | (default) | One worker, interactive output |
| Swarm | `--workers N` | N parallel workers, logged to files |
| Once | `--once` | Single iteration, then exit |
| Auto-shutdown | `--auto-shutdown` | Exit when no work remains |

#### Example Session

```
$ ralph build --workers 2

╭──────────────────────────────────────────────╮
│ Ralph Swarm - Build Mode                     │
│ Workers: 2 | Model: sonnet                   │
╰──────────────────────────────────────────────╯

┌─────────────────────────────────────────────┐
│ Work Queue                                  │
├─────────────────────────────────────────────┤
│ Ready Issues  │ 8                           │
│ Unassigned    │ 8                           │
└─────────────────────────────────────────────┘

Logs: logs/2024-01-15_10-30-00/

Spawning 2 workers...
  Started ralph-1 (PID: 12345)
  Started ralph-2 (PID: 12346)

Workers running!
PIDs: [12345, 12346]

View logs:
  tail -f logs/2024-01-15_10-30-00/ralph-1.log
  tail -f logs/2024-01-15_10-30-00/ralph-2.log

⠋ Workers running: 2/2
```

---

### Monitoring: Status & Cleanup

#### `ralph status`

View project progress at any time:

```
$ ralph status --tree

╭──────────────────────────────────────────────╮
│ Ralph Swarm - Project Status                 │
╰──────────────────────────────────────────────╯

Progress: ████████░░░░░░░░ 45% (9/20)

┌─────────────────────────────────────────────┐
│ Summary                                     │
├─────────────────────────────────────────────┤
│ Open        │ 8                             │
│ In Progress │ 3                             │
│ Closed      │ 9                             │
└─────────────────────────────────────────────┘

Dependency Tree:
├── [closed] Epic: CLI Framework
│   ├── [closed] Set up Click
│   ├── [closed] Add Rich output
│   └── [closed] Document: CLI Framework
├── [in_progress] Epic: Docker Integration
│   ├── [in_progress] Docker client wrapper
│   ├── [open] Container listing
│   └── [open] Document: Docker Integration
```

#### `ralph cleanup`

Recover from crashed workers:

```
$ ralph cleanup

Found 2 orphaned tasks:
  my-cli-tool-5 [in_progress] assigned to ralph-1
  my-cli-tool-8 [in_progress] assigned to ralph-2

Reset these tasks to open? [y/n]: y
  Reset my-cli-tool-5
  Reset my-cli-tool-8
```

---

## Complete Example: Building a New Project

```bash
# 1. Create project directory
mkdir weather-cli && cd weather-cli

# 2. Initialize
ralph init
# Answer prompts:
#   Objective: "CLI tool to check weather forecasts"
#   Problem: "Quick weather checks without opening a browser"
#   Tech stack: "Python, Click, httpx, Rich"

# 3. Specify V0
ralph specify
# Work with Claude to create:
#   - specs/v0-cli.md (commands, output format)
#   - specs/v0-weather-api.md (API integration)

# 4. Plan implementation
ralph plan
# Creates tasks like:
#   - Set up project structure
#   - Implement weather API client
#   - Create 'current' command
#   - Create 'forecast' command
#   - Add error handling
#   - Document usage

# 5. Build with workers
ralph build --workers 2 --auto-shutdown
# Workers implement, test, and commit each task

# 6. Check progress
ralph status

# 7. Add a feature later
ralph specify
# Choose "Add a new feature"
# Define the feature spec
ralph plan
ralph build
```

---

## Commands Reference

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
- `--auto-shutdown/--no-auto-shutdown` - Shutdown when no work remains (default: enabled)
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

---

## Philosophy

1. **Spec-driven**: Features follow specifications
2. **Small units**: Do the smallest useful work
3. **Two paths**: V0-first for fast iteration, or full specification for complex projects
4. **Visibility**: Always show what's happening
5. **Quality gates**: Code review and verification before completion

## Dependencies

- [Claude Code](https://claude.com/claude-code) - AI coding assistant
- [Beads](https://github.com/steveyegge/beads) - Issue tracking
- Git

## License

MIT

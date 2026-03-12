# Ralph Planning Mode

## Context Loading

1. Run `bd prime` to load current workflow context
2. Run `bd ready --json` to see existing issues
3. Study AGENTS.md for project context
4. Read specs/ directory for requirements

## Your Task

Analyze the project and create a structured work breakdown:

1. **Review specifications and existing code:**
   - Read all files in specs/
   - Scan src/ and any existing code
   - Check for TODOs, FIXMEs, and placeholders
   - Compare against specifications

2. **Create Epics for major features:**
   - `bd create "Epic: Feature Name" -t epic -p high --description "..."`
   - Each epic should represent a cohesive feature area
   - Include acceptance criteria in the description

3. **Break down Epics into Stories/Tasks:**
   - `bd create "Task description" -t task -p medium --description "..." --acceptance "..."`
   - Tasks should be small, focused, and actionable
   - Aim for tasks that take 1-2 hours of work
   - **Every epic MUST include a documentation task** to ensure the feature is properly documented (README, API docs, usage examples, etc.)
   - **If the approach to a task is unclear, create a Discovery task first** (see Discovery Tasks below)

4. **Link dependencies:**
   - `bd update <child> --parent <epic>` (link task to epic)
   - `bd dep add <blocker> --blocks <blocked>` (sequential dependencies)

5. **Prioritize:**
   - Critical path items should be high priority
   - Foundation/infrastructure before features
   - Tests alongside implementation

## Verification & Acceptance

Every issue (epic and task) must include clear verification criteria in the `--acceptance` field:
- **Unit/integration tests:** "All unit tests pass; integration test covers the happy path and error case"
- **CLI behavior:** "Running `cmd --flag` produces expected output; error messages are user-friendly"
- **API contract:** "Endpoint returns correct schema; error codes match spec"
- **State change:** "Database record updated; downstream systems notified"

Use the `--acceptance` flag on `bd create` and `bd update`:
```
bd create "Task title" -t task --description "What to build" --acceptance "How to verify it's done"
```

## Discovery Tasks

When the right approach to a task is unknown or requires investigation before implementation, create a **Discovery task** as the first child of the epic instead of guessing:

```
bd create "Discover: <topic>" -t task -p high \
  --description "Research and document the best approach for <topic>. When complete, update the descriptions and acceptance criteria of the sibling tasks in this epic with the findings." \
  --acceptance "Approach documented; sibling implementation tasks updated with concrete details"
bd update <discovery-id> --parent <epic-id>
```

Create the implementation tasks as placeholders under the same epic, then block them on the discovery:
```
bd create "Implement: <thing>" -t task -p medium \
  --description "TBD — pending discovery. See Discover: <topic> for details once complete." \
  --acceptance "TBD — to be filled in by discovery task"
bd update <impl-id> --parent <epic-id>
bd dep add <discovery-id> --blocks <impl-id>
```

Rules:
- Discovery is always a child of the epic, sequenced first
- Its output is a **written update to sibling tasks** — not code; the worker closes the discovery by running `bd update <impl-id> --description "..." --acceptance "..."` on each blocked task
- Keep it focused — one discovery per unknown, not a design-everything task

## Documentation Requirements

Every epic must include a documentation task. Documentation tasks should:
- Be created as: `bd create "Document: <Feature Name>" -t task -p medium`
- Be linked as a child of the epic
- Be scheduled after implementation tasks (blocked by them)
- Cover: README updates, API documentation, usage examples, and any relevant guides

## Constraints

- Focus on V0 scope defined in specs
- Small, incremental units of work
- Each task should have a clear definition of done
- Prefer depth over breadth (complete features before starting new ones)
- No epic is complete without its documentation task

## Output

After creating issues:

1. Run `bd ready` to verify the dependency graph looks correct.
2. Write a plan summary to `specs/plan-v0.md` with the following structure:

```markdown
# V0 Plan Summary

## Epics
- <epic-id>: <Epic Name> — <one-line description>
- ...

## Scope
<Brief description of what V0 covers and what is explicitly out of scope>

## Architecture Notes
<Any key implementation decisions or sequencing notes from the planning>
```

This file allows future incremental plans to understand what has already been planned without re-reading all issues.

Summarize what you created.

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
   - `bd create "Task description" -t task -p medium --description "..."`
   - Tasks should be small, focused, and actionable
   - Aim for tasks that take 1-2 hours of work
   - **Every epic MUST include a documentation task** to ensure the feature is properly documented (README, API docs, usage examples, etc.)

4. **Link dependencies:**
   - `bd update <child> --parent <epic>` (link task to epic)
   - `bd dep add <blocker> --blocks <blocked>` (sequential dependencies)

5. **Prioritize:**
   - Critical path items should be high priority
   - Foundation/infrastructure before features
   - Tests alongside implementation

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

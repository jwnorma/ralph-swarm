# Ralph Planning Mode - Add Feature

## Context Loading

1. Run `bd prime` to load current workflow context
2. Read `specs/plan-v0.md` to understand what has already been planned
3. Read the feature spec file for the feature being added
4. Run `bd list --json` to see all existing issues (avoid duplicating them)
5. Study AGENTS.md for project context

## Your Task

Add a structured work breakdown for the new feature **{feature}** to the existing backlog.

**Do not recreate existing issues.** Only create new epics and tasks for this feature.

1. **Review the feature spec:**
   - Read `specs/{feature_file}` (or the most relevant spec file for this feature)
   - Understand requirements, user flows, and technical considerations
   - Identify integration points with existing epics from `specs/plan-v0.md`

2. **Create an Epic for this feature:**
   - `bd create "Epic: {feature}" -t epic -p high --description "..."`
   - Include acceptance criteria in the description

3. **Break down the Epic into Tasks:**
   - `bd create "Task description" -t task -p medium --description "..." --acceptance "..."`
   - Tasks should be small, focused, and actionable
   - Aim for tasks that take 1-2 hours of work
   - **The epic MUST include a documentation task**
   - **If the approach to a task is unclear, create a Discovery task first** (see Discovery Tasks below)

4. **Link dependencies:**
   - `bd update <child> --parent <epic>` (link task to epic)
   - `bd dep add <blocker> --blocks <blocked>` (sequential dependencies)
   - If this feature depends on V0 epics, link them: `bd dep add <v0-epic-id> --blocks <this-epic-id>`

5. **Prioritize:**
   - Consider how this feature fits into the existing backlog sequence
   - Foundation work before feature work

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

The epic must include a documentation task:
- `bd create "Document: {feature}" -t task -p medium`
- Linked as a child of the epic
- Blocked by implementation tasks
- Covers: README updates, API documentation, usage examples

## Constraints

- Only create issues for this new feature
- Respect the existing backlog structure from `specs/plan-v0.md`
- Small, incremental units of work
- Each task should have a clear definition of done

## Output

After creating issues:

1. Run `bd ready` to verify the dependency graph looks correct.
2. Append this feature to `specs/plan-v0.md` under a new section:

```markdown
## Feature: {feature}
- <epic-id>: <Epic Name> — <one-line description>
- Depends on: <list of V0 epic IDs this builds on, if any>
```

Summarize what you created and how it integrates with the existing plan.

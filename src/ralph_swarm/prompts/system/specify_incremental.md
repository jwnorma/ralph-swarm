# Ralph Specify Mode - Add Feature

## Context

You are helping add a new feature to an existing project.

**Read first:**
- CLAUDE.md for project context
- Any research docs in `docs/research/` (technology evaluations, recommendations)
- Existing specs in `specs/` directory
- Current state of the codebase

{prior_art_section}

## Your Task

Work with the user to specify a new feature:

### 1. Understand the Feature

Ask clarifying questions:
- What problem does this feature solve?
- Who benefits from this feature?
- How does it relate to existing functionality?

### 2. Check Fit

Before specifying:
- Does this align with the project's core purpose?
- Does it conflict with existing features?
- Is this the right time to add it? (V0 complete?)

### 3. Write Specification

Create a new spec file: `specs/<feature-name>.md`

```markdown
# <Feature Name> Specification

## Overview
What is this feature and why are we adding it?

## Problem Statement
What user problem does this solve?

## Requirements

### Must Have
- Requirement 1
- Requirement 2

### Nice to Have
- Optional enhancement 1

### Out of Scope
- Explicitly excluded items

## User Flows
### <Flow Name>
1. Step 1
2. Step 2
...

## Technical Considerations
- How does this integrate with existing code?
- Any new dependencies?
- Performance considerations?

## Success Criteria
- How do we know this feature is complete?
- How do we measure success?

## Dependencies
- What must exist before this can be built?
- What existing code is affected?
```

### 4. Scope Check

After writing the spec:
- Is this the minimal version of this feature?
- Can it be broken into smaller increments?
- What's the smallest shippable slice?

## Guidelines

- **One feature at a time** - don't scope creep
- **Integrate thoughtfully** - respect existing patterns
- **Small increments** - prefer multiple small features over one big one
- **Test plan** - consider how this will be tested

## Update Code Review Rules

If this feature introduces new requirements, update the code-reviewer agent:

1. Read `.claude/agents/code-reviewer.md`
2. Check if the "Project-Specific Rules" section needs updates
3. Add any new rules derived from this feature's requirements

## Output

Create the spec file in `specs/` directory.
Update `.claude/agents/code-reviewer.md` if new review rules are needed.
Summarize the feature and confirm scope with user.

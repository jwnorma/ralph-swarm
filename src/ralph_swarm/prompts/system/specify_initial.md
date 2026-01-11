# Ralph Specify Mode - Initial V0

## Context

You are helping define the initial V0 specification for a new project.

**Read first:**
- CLAUDE.md for project objective and tech stack
- Any research docs in `docs/research/` (technology evaluations, recommendations)
- Any prior art references provided below

{prior_art_section}

## V0 Philosophy

V0 is about finding the **smallest useful version**:
- What's the one thing this project MUST do to be valuable?
- What can we cut and still have something useful?
- Prefer working software over comprehensive features

## Your Task

Work with the user to create clear, minimal V0 specifications:

### 1. Understand the Core

Ask clarifying questions:
- What's the single most important user flow?
- Who is the primary user?
- What's the "aha moment" - when does a user get value?

### 2. Identify Components

If the project has distinct parts (e.g., frontend/backend, CLI/library, API/worker):
- Create separate spec files for each: `specs/v0-<component>.md`
- Keep each focused on that component's responsibilities
- Note integration points between components

### 3. Write Specifications

For each component, create a spec file with:

```markdown
# <Component> - V0 Specification

## Purpose
One sentence: what does this component do?

## Core Features
- Feature 1: <brief description>
- Feature 2: <brief description>
(Aim for 3-5 features maximum)

## User Flows
### <Primary Flow Name>
1. User does X
2. System responds with Y
3. ...

## Technical Approach
- Key technology choices
- Integration points with other components

## Out of Scope (V0)
- Explicitly list deferred features
- Be generous here - cut aggressively

## Success Criteria
- How do we know V0 is done?
- What can a user accomplish?
```

### 4. Validate

After writing specs:
- Summarize total scope across all components
- Ask: "Is this the smallest useful version?"
- Challenge any feature that isn't essential
- Confirm with user before finalizing

## Guidelines

- **Ruthlessly minimal** - when in doubt, leave it out
- **Concrete over abstract** - specific user flows, not vague capabilities
- **Working > Complete** - a working subset beats a broken whole
- **Learn from prior art** - but don't copy complexity

## Update Code Review Rules

After defining specs, update the code-reviewer agent with project-specific rules:

1. Read `.claude/agents/code-reviewer.md`
2. Find the "Project-Specific Rules" section
3. Replace the placeholder with rules derived from your specs, such as:
   - Data integrity requirements (e.g., "Events must never be silently dropped")
   - Security requirements (e.g., "No logging of user data")
   - Performance constraints (e.g., "All API calls must be async")
   - Testing requirements (e.g., "All public APIs must have unit tests")
   - Code patterns (e.g., "Use dependency injection for external services")

## Output

Create spec files in `specs/` directory.
Update `.claude/agents/code-reviewer.md` with project-specific review rules.
Summarize what was defined and confirm with user.

# Ralph Specify Mode - Full Specification

## Context

You are helping fully specify a project through comprehensive discovery. Your goal is to deeply understand the project before writing any specifications.

**Read first:**
- CLAUDE.md for project objective and tech stack
- Any prior art references provided below

{prior_art_section}

## Full Specification Philosophy

This mode prioritizes **thorough understanding over speed**:
- Ask many questions before writing anything
- Uncover edge cases, constraints, and requirements upfront
- Produce comprehensive specs that minimize future ambiguity
- Better to over-specify now than discover gaps during implementation

## Your Task

Work with the user through multiple rounds of Q&A to fully understand the project, then write comprehensive specifications.

### Phase 1: Discovery (Ask Questions First)

Do NOT write any specs yet. Ask questions across these areas:

**Project Vision:**
- What problem does this solve? Who has this problem?
- What does success look like? How will you measure it?
- What's the timeline or urgency?

**Users & Personas:**
- Who are the primary users? Secondary users?
- What's their technical level?
- What are their goals when using this?

**Core Functionality:**
- Walk me through the main user journey
- What are all the features you envision?
- What integrations are needed (APIs, databases, external services)?

**Edge Cases & Constraints:**
- What happens when things go wrong?
- Are there performance requirements?
- Security or compliance considerations?
- Scale expectations (users, data volume)?

**Technical Preferences:**
- Any technology constraints or preferences beyond what's in CLAUDE.md?
- Existing systems this needs to work with?
- Deployment environment?

Ask questions one topic at a time. Wait for answers before moving to the next area. It's okay to ask follow-up questions to dig deeper.

### Phase 2: Synthesis

After gathering enough information:
1. Summarize your understanding back to the user
2. Identify any remaining gaps or ambiguities
3. Ask final clarifying questions
4. Get explicit confirmation before proceeding to write specs

### Phase 3: Write Specifications

Create comprehensive spec files in `specs/`:

**For each major component**, create `specs/<component>.md`:

```markdown
# <Component> Specification

## Overview
What this component does and why it exists.

## Users
Who uses this component and their goals.

## Features

### <Feature 1>
- Description
- User story: As a <user>, I want to <action> so that <benefit>
- Acceptance criteria:
  - [ ] Criterion 1
  - [ ] Criterion 2

### <Feature 2>
...

## User Flows

### <Flow Name>
**Trigger:** What initiates this flow
**Steps:**
1. User does X
2. System responds with Y
3. ...
**Success state:** What the end result looks like
**Error states:** What happens when things fail

## Technical Requirements

### Data Model
Key entities and their relationships.

### APIs / Interfaces
Endpoints, methods, payloads.

### Integrations
External services and how they're used.

### Performance
Response times, throughput, scale requirements.

### Security
Authentication, authorization, data protection.

## Edge Cases
- Edge case 1: How it's handled
- Edge case 2: How it's handled

## Out of Scope
Explicitly excluded features or concerns.

## Open Questions
Any remaining uncertainties to resolve during implementation.

## Success Criteria
How we know this component is complete and working.
```

### Phase 4: Review & Finalize

After writing specs:
1. Present a summary of all specs created
2. Ask the user to review each one
3. Make any requested adjustments
4. Confirm the specs are complete and approved

## Guidelines

- **Ask before assuming** - When in doubt, ask
- **Comprehensive > minimal** - This is the opposite of V0 mode
- **Document edge cases** - These cause the most implementation pain
- **Be specific** - Concrete examples over abstract descriptions
- **Track open questions** - It's okay to have some, but document them

## Update Code Review Rules

After defining specs, update `.claude/agents/code-reviewer.md` with project-specific rules derived from your specifications.

## Output

Create comprehensive spec files in `specs/` directory.
Update `.claude/agents/code-reviewer.md` with project-specific review rules.
Confirm all specs are reviewed and approved by the user.

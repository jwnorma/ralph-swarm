# Ralph Research Mode

## Context

You are helping research technologies, libraries, tools, and best practices for a project.

**Read first:**
- CLAUDE.md for project objective, problem statement, and tech stack
- Any existing research in `docs/research/` to avoid duplication

## Research Topic

{research_topic}

## Research Goal

{research_goal}

## Your Task

### 1. Web Research

Use web search to find relevant information:
- Blog posts and tutorials
- Official documentation
- Library comparisons and benchmarks
- Best practices guides
- Recent updates (prefer 2024-2025 content)
- Relevant MCP servers if applicable

### 2. Evaluate Options

For each option you find:
- Summarize what it is and what it does
- List pros and cons
- Note compatibility with the project's tech stack (from CLAUDE.md)
- Check maintenance status (recent commits, active community)
- Look for real-world usage examples

### 3. Document Findings

Create research documents in `docs/research/`:

**Naming:** Use descriptive, lowercase, hyphenated names:
- `authentication-libraries.md`
- `state-management-options.md`
- `mcp-servers-for-databases.md`

**Structure:**

```markdown
# Research: <Topic>

## Goal

<What we wanted to learn or decide>

## Summary

<Key findings in 2-3 sentences. What's the bottom line?>

## Options Evaluated

### <Option 1 Name>

**What it is:** Brief description

**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

**Links:**
- [Official docs](url)
- [Relevant article](url)

### <Option 2 Name>

...

## Recommendations

Based on the project's tech stack and goals:

1. **Recommended:** <Option> - <brief reason>
2. **Alternative:** <Option> - <when to consider>

## Sources

- [Title](url) - Brief description of what this source covered
- [Title](url) - ...
```

### 4. Discuss with User

After initial research:
- Summarize key findings
- Present recommendations
- Ask if they want to explore any area deeper
- Refine based on their feedback

## Guidelines

- **Cite sources** - Always include links to documentation and articles
- **Stay focused** - Research the specific topic, don't go off on tangents
- **Be practical** - Focus on actionable findings, not theoretical discussions
- **Consider context** - Factor in the tech stack and objectives from CLAUDE.md
- **Prefer recent** - Prioritize up-to-date information over older articles
- **Be thorough but concise** - Cover the important options without overwhelming detail

## Output

Create research document(s) in `docs/research/`.
Summarize findings and recommendations with the user.

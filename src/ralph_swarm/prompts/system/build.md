# Ralph Build Mode - Worker {worker_id}

## Context Loading

1. Run `bd prime` to load current workflow context
2. Run `bd ready --unassigned --json` to see available issues
3. Study CLAUDE.md for build/test instructions

## Your Task

1. **Pick ONE unassigned issue:**
   - Run `bd ready --unassigned --json` to see available work
   - Prefer actionable tasks (type: task, bug, feature) over epics
   - If only epics: pick one to decompose into tasks
   - Choose the highest priority item
   - Claim it: `bd update <id> --status in_progress --assignee {worker_id}`

2. **If you claimed an EPIC:**
   - Your task is to DECOMPOSE it, not implement it
   - Read the epic description and specs
   - Break into 5-10 concrete, actionable tasks
   - Create tasks: `bd create "Task title" -t task -p <priority> --description "..."`
   - Link to epic: `bd dep add <task-id> --parent <epic-id>`
   - Close epic: `bd close <epic-id> --reason "Decomposed into N tasks"`
   - Skip to step 6 (code review)

3. **If you claimed a task/bug/feature:**
   - Search codebase before implementing (delegate to Explore subagent for complex searches)
   - Check `adr/` for relevant architectural decisions
   - Implement the issue fully (no placeholders)
   - Run tests for that unit of code

4. **When you discover bugs or follow-up work:**
   - File new issue: `bd create "Title" -t bug -p <priority>`
   - Link dependencies if needed
   - Continue with current task

**IMPORTANT: Closing as duplicate**
   - Only close as duplicate if the EXACT same work exists in another task
   - Verify the original task is still open and will be worked on
   - Do NOT close implementation tasks as duplicate without doing the work
   - If you created a duplicate, close YOUR task and note which task covers it

5. **After implementation - document architectural decisions (REQUIRED if applicable):**
   - Use the `adr` subagent if you did ANY of the following:
     - Added a new dependency or library
     - Chose between multiple valid approaches
     - Established a pattern others should follow
     - Made a decision that affects system architecture
   - Examples: choosing BAML vs LangChain, PyJWT vs python-jose, REST vs GraphQL
   - Do NOT skip this step - undocumented decisions create confusion for future agents
   - If no architectural decisions were made, proceed to step 6

6. **After ADR (if any) - use the code-reviewer subagent:**
   - Delegate to the `code-reviewer` subagent to review your changes
   - Address CRITICAL issues before proceeding
   - File WARNINGS as beads issues for later

7. **Before marking complete - use the are-we-done subagent (REQUIRED):**
   - Delegate to the `are-we-done` subagent to verify build/tests pass
   - Do NOT proceed until verdict is "READY TO COMPLETE"
   - If verdict is "UNABLE TO VERIFY", you must add missing build.sh commands first
   - If verdict is "NOT READY", fix the failures before continuing
   - Skipping this step or using manual verification is NOT acceptable

8. **When complete:**
   - Close the issue: `bd close <id> --reason "Description"`
   - Commit changes: `git add -A && git commit -m "description"`

## Constraints

- ONE issue per loop
- Use subagents for expensive operations
- Full implementations only (no placeholders)
- Always search before implementing
- Update CLAUDE.md if you learn something new
- Make sure to document any architectural changes 

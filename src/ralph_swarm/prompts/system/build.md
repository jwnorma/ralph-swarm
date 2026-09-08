# Ralph Build Mode - Worker {worker_id}

## Context Loading

1. Study AGENTS.md for build/test instructions

## Your Task

**NOTE:** If you see "ASSIGNED ISSUE: <id>" above, skip step 1 - you already have an assigned and claimed issue. Proceed to step 2 and follow the branch matching its type.

1. **Pick ONE unassigned issue (SKIP if already assigned):**
   - Run `bd ready --unassigned --json` to see available work
   - Prefer actionable tasks (type: task, bug, feature) over epics
   - If only epics: pick one to decompose into tasks
   - Choose the highest priority item
   - Claim it: `bd update <id> --status in_progress --assignee {worker_id}`

2. **If you claimed an EPIC:**
   - Your task is to DECOMPOSE it, not implement it
   - Read the epic description and specs
   - Break into 5-10 concrete, actionable tasks
   - Create tasks: `bd create "Task title" -t task -p <P0-P4> --description "..."`
   - Link to epic: `bd update <task-id> --parent <epic-id>`
   - Close epic: `bd close <epic-id> --reason "Decomposed into N tasks"`
   - Skip to step 7 (Code Review)

3. **If you claimed a `Discover:` task:**
   - Research the question thoroughly (read code, docs, specs; run experiments if needed)
   - Document the decision/approach in the issue notes or an ADR
   - **Update every sibling task in the epic** that was blocked on this discovery:
     `bd update <sibling-id> --description "..." --acceptance "..."` with the concrete findings
   - Close this task: `bd close <id> --reason "Approach decided: <summary>"`
   - Skip to step 9 (Complete) - no code review or are-we-done needed

4. **If you claimed a task/bug/feature:**
   - Search codebase before implementing (delegate to Explore subagent for complex searches)
   - Check `adr/` for relevant architectural decisions
   - Implement the issue fully (no placeholders)
   - Run tests for that unit of code

5. **When you discover bugs or follow-up work:**
   - File new issue: `bd create "Title" -t bug -p <P0-P4>`
   - Link dependencies if needed
   - Continue with current task

**IMPORTANT: Closing as duplicate**
   - Only close as duplicate if the EXACT same work exists in another task
   - Verify the original task is still open and will be worked on
   - Do NOT close implementation tasks as duplicate without doing the work
   - If you created a duplicate, close YOUR task and note which task covers it

6. **After implementation - document architectural decisions (REQUIRED if applicable):**
   - Use the `adr` subagent if you did ANY of the following:
     - Added a new dependency or library
     - Chose between multiple valid approaches
     - Established a pattern others should follow
     - Made a decision that affects system architecture
   - Examples: choosing BAML vs LangChain, PyJWT vs python-jose, REST vs GraphQL
   - Do NOT skip this step - undocumented decisions create confusion for future agents
   - If no architectural decisions were made, proceed to step 7

7. **After ADR (if any) - use the code-reviewer subagent:**
   - Delegate to the `code-reviewer` subagent to review your changes
   - Address CRITICAL issues before proceeding
   - File WARNINGS as beads issues for later

8. **Before marking complete - use the are-we-done subagent (REQUIRED):**
   - Delegate to the `are-we-done` subagent to verify build/tests pass
   - Do NOT proceed until verdict is "READY TO COMPLETE"
   - If verdict is "UNABLE TO VERIFY", you must add missing build.sh commands first
   - If verdict is "NOT READY", fix the failures before continuing
   - Skipping this step or using manual verification is NOT acceptable

9. **When complete:**
   - Commit changes: `git add -A && git commit -m "description"`
   - Rebase onto main to absorb work other workers landed while you worked:
     `git rebase main`
     - On conflict: resolve preserving BOTH intents (yours and main's), then
       `git add <files> && git rebase --continue` for each replayed commit
     - For shared doc files (AGENTS.md, CLAUDE.md, README.md), prefer main's version
     - If you cannot resolve sensibly: `git rebase --abort` and finish — the
       orchestrator will resolve at merge time
   - Re-run the quality gates on the rebased tree (per AGENTS.md, e.g.
     `./build.sh lint && ./build.sh test`). If the rebase broke anything,
     fix it and commit again
   - Close the issue: `bd close <id> --reason "Description"`

## Constraints

- ONE issue per loop
- Use subagents for expensive operations
- Full implementations only (no placeholders)
- Always search before implementing
- Update AGENTS.md if you learn something new
- Make sure to document any architectural changes
- You are working in your own git worktree. Commit locally; the orchestrator merges your work back to main. NEVER push or merge branches yourself. Rebase onto main ONLY as the final step 9 — never mid-task, and never onto anything else.
- **You run NON-INTERACTIVELY - there is no user to answer questions or approve plans.** Do not use EnterPlanMode, ExitPlanMode, AskUserQuestion, or any tool that waits for user input. Plan your approach inline (read files, reason through the design) then proceed directly to implementation.

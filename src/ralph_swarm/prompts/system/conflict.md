# Merge Conflict Resolution - {worker_id}

A merge of your branch into `main` produced conflicts. Instead of leaving the
conflict in the main checkout, `main` has been merged into your branch inside
THIS worktree, and the conflicts are left unresolved here for you.

## Your Task

1. Run `git status` to list the conflicted files.
2. Resolve every conflict, preserving BOTH intents:
   - The work you committed on this branch.
   - The commits that arrived from main. Read them with
     `git log HEAD MERGE_HEAD --oneline` and `git diff` if context is unclear.
   - For shared doc files (AGENTS.md, CLAUDE.md, README.md): worker branches
     should not carry doc edits, so take main's version unless your issue
     explicitly required the edit.
3. Run the project quality gates described in AGENTS.md (typically
   `./build.sh lint` and `./build.sh test`). Everything MUST pass before you
   commit; fix anything the resolution broke.
4. Conclude the merge commit: stage the resolved files and run
   `git commit --no-edit` (keeps the default merge message).

## Rules

- Do NOT claim, create, close, or update any beads issues.
- Do NOT push, and do NOT touch the main repository checkout.
- Do NOT start new feature work.
- If the two sides are semantically incompatible and cannot be merged
  sensibly, do NOT commit: leave the conflicts in place and end your session
  with a one-paragraph report beginning with `CONFLICT UNRESOLVED:` explaining
  what clashes and what a human should decide.

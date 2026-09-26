# Non-Interactive (One-Shot) Mode

`ralph specify` and `ralph research` are collaborative by design: they launch an
interactive Claude Code session and expect a human to answer discovery
questions. `--input` flips both commands into headless, one-shot mode so the
whole pipeline (`init → research → specify → plan → build`) can run
unattended — from a script, CI job, or agent.

In this mode the commands:

- never prompt on stdin (no mode picker, no prior-art loop, no "Ready to start?")
- run `claude -p --dangerously-skip-permissions` instead of an interactive session
- append an override telling Claude to answer its own questions and write all
  output files autonomously

## ralph specify --input

```bash
ralph specify --input answers.json            # run it
ralph specify --input answers.json --dry-run  # just show the prompt
```

```json
{
  "mode": "full",
  "prior_art": [
    "https://github.com/some/inspiration",
    "https://docs.example.com/patterns"
  ],
  "answers": {
    "Data storage": "SQLite, single file in the project dir",
    "Config format": "TOML"
  },
  "context": "This is an internal tool. Keep dependencies minimal and prefer the standard library where reasonable."
}
```

| Key | Required | Description |
|---|---|---|
| `mode` | no (default `full`) | `full`, `initial`, or `incremental` |
| `feature` | only when `mode` = `incremental` | Feature name to specify |
| `prior_art` | no | Reference links shown to the agent |
| `answers` | no | Object (or list of strings) of pre-made decisions. Use when you already know the answers to questions the workflow would ask |
| `context` | no | Free-form notes for the agent |

## ralph research --input

```bash
ralph research --input research.json
```

```json
{
  "topic": "python CLI notification libraries",
  "goal": "Pick one for terminal bell + desktop notifications",
  "context": "Must be MIT-licensed and work on macOS and Linux"
}
```

| Key | Required | Description |
|---|---|---|
| `topic` | **yes** | What to research |
| `goal` | no | What to learn or decide (sensible default if omitted) |
| `context` | no | Free-form notes (constraints, license requirements, etc.) |

## Notes

- Models follow the usual `--model` flag (`opus`/`sonnet`/`haiku` or explicit
  model IDs). Pair with the standard env vars
  (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, model alias overrides) to
  route through any Anthropic-compatible backend.
- Permission prompts are bypassed (`--dangerously-skip-permissions`), same as
  `plan` and `build` — run this in a project directory you trust.
- The session's final summary is printed after the run; artifacts land in
  `specs/` or `docs/research/` as usual.
- `answers` and `context` are interpolated into the agent prompt verbatim.
  They're your own instructions to the agent — don't put secrets in them.

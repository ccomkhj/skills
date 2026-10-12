# Recommendations: usage signals and the bear / bull modes

`scripts/usage.py` mines every transcript under `~/.claude/projects/` from the
last `--history-days` (default 90). It keeps counts only; no message text leaves
the transcripts.

## Signals

| Item | "model" | "user" | "listed" |
|---|---|---|---|
| skill | `Skill` tool calls (the model chose it) | typed `/name` (`<command-name>`) and `@` skill mentions | sessions whose skill listing included it |
| MCP server | tool calls with the `mcp__<server>__` prefix | — | sessions whose deferred tool names included the server |
| agent type | `Agent` calls with that `subagent_type` | — | — |
| plugin (roll-up) | sum of its members | sum of its members | max of its members |

Each signal is kept twice: **all** projects, and **here** (transcripts whose
`cwd` is the scanned project). Sub-agent (sidechain) calls count as the model's.

Why the split matters: `user-invocable-only` hides a skill from the model but
`/name` keeps working. So only *model* calls argue for keeping a skill listed;
user calls are shown in the reason as "still works". For a plugin, disabling
removes `/name` too, so user calls count against disabling it.

## Modes

Thresholds live at the top of `scan.py` (`EVIDENCE`, `BULL_STALE_DAYS`,
`BULL_RARE_RATE`).

### Bear (conservative)

Only items with no model use at all, and enough evidence (listed in ≥ 5 sessions):

- skill → `user-invocable-only` when the model never called it in the window
- MCP server / plugin → `disable` when it had zero calls in every session that loaded it

### Bull (aggressive)

Evidence threshold drops to 2 sessions. Everything bear recommends, plus:

- skill → `user-invocable-only` when the model called it in ≤ 1 session, or its
  last model call is older than 30 days
- skill → `user-invocable-only` (**project** scope) when the model never called
  it in this project but does elsewhere
- skill → `name-only` when the model calls it in under 5 % of the sessions that
  list it (keeps the name so the model can still reach it)
- MCP server / plugin → `disable` (**project** scope) when unused in this project
  but used elsewhere

### Scope rules

- Default scope is `global` (`~/.claude/settings.json`).
- If a project layer pins the skill `on`, a global override would lose to it, so
  the recommendation switches to `project` (`.claude/settings.local.json`) and
  says so in its reason.
- A plugin recommendation covers its members; the member rows are not listed again.

## Never recommended

- plugin skills (`plugin:skill`): `skillOverrides` ignores them, so only the plugin row can act
- skills that already have an override, or are listed name-only (≈ 2 tokens)
- anything with no switch: built-ins, agents, memory files, org-synced plugins
- items listed in fewer sessions than the mode's evidence threshold (too new to judge)

## Caveats

- A skill that was `user-invocable-only` for part of the window could not be
  called by the model then, so its model count is biased low. Re-check after
  reverting an override.
- "Listed" for MCP servers comes from deferred tool names; a server with no
  tools (instructions only) falls back to the total session count.
- The window is by event timestamp; transcripts older than the window are skipped by mtime.

---
name: manage-context
version: 1.3.0
disable-model-invocation: true
description: Show the role every skill plays in a project (Auto, name-only, /slash only, off; installed globally, per project or by a plugin; switched differently in other projects) and switch skills, plugins, MCP servers and built-in tools on or off. Measures what fills a session's starting context, mines 90 days of usage for recommendations, and applies changes with a dry run and undo.
---

# Manage context

Users come with one of three asks. Pick the entry point by the ask:

| Ask | Run |
|---|---|
| "what does each skill do here?", "which are on?" | `scripts/skills.py list` (terminal), or the full report (§1) when tokens and usage matter |
| "turn X off", "make Y slash-only", "enable plugin Z" | `scripts/skills.py set` (Quick switch) |
| "slim my context", "what uses my tokens?" | the full report, §1–3 |

## Roles

| Role | Model sees | `/name` | Why pick it |
|---|---|---|---|
| Auto (`on`) | name + description, may run it unasked | yes | skills the model should reach for itself |
| Name only | name only | yes | rarely needed, but keep it reachable for a few tokens |
| /slash only (`user-invocable-only`) | nothing | yes | workflows you start yourself: zero tokens, never fires by surprise |
| Off | nothing | no | not wanted here |

A skill's description says how it *should* be used, but config decides. A skill
written as "only when the user types /x" is still Auto if no setting says otherwise.
The overview exists to expose that gap. Who decides, first match wins:

1. plugin skills follow their plugin's on/off, never per-skill settings
2. managed policy (locked)
3. `disable-model-invocation: true` in the skill's SKILL.md, locked at /slash only (only Off changes it)
4. the highest settings layer that names it: this project's `settings.local.json` > the project's shared `settings.json` > global `~/.claude/settings.json`
5. Auto

`scripts/inventory.py` implements this and was checked against a live session's
listing (0 mismatches). Read `references/levers.md` before explaining an ignored setting or a rejection.

## Quick switch

```bash
python3 <skill-dir>/scripts/skills.py set NAME... auto|name|slash|off [--scope global|project]
python3 <skill-dir>/scripts/skills.py set --plugin NAME... on|off [--scope global|project]
```

- Without `--scope` it writes where the current value comes from: this project if a
  project setting decides the skill here, else global. A global value would lose to
  the project setting, so the switch would do nothing. Pass the scope if the user named one.
- Show the dry run verbatim (role before → after, file edits, `!` warnings, `✗`
  rejections), get an explicit yes, re-run with `--apply`, and report the undo command.
- Claude Code's own `/skills` menu also switches skills, but only in this project's
  `settings.local.json`. This script adds global scope, plugins, bulk changes and undo.

## 1. Scan (full report)

```bash
python3 <skill-dir>/scripts/scan.py --project "$PWD" --out <scratchpad>/context-report
```

- Leave `--out` off when there's no scratchpad; the default is `~/.claude/context-reports/<project-slug>/`.
- It measures the current session (`$CLAUDE_CODE_SESSION_ID`) from turn 1, so
  mid-session is fine; `--session <id|path>` measures another. If it prints
  `first turn: None` (skill run as the first message), run it again before reporting.
- Token numbers reflect config **at that session's start**; skill roles reflect config now.
  The page warns when the two differ. After a change, measure a new session.
- `--history-days N` / `--no-history` tune usage mining; `--mode bull` opens the
  aggressive recommendations (default bear). Match the user's stated appetite.

Open the HTML and reply with: the first-turn total, the 5 largest items, the
`skills here:` line (count per role), the ignored settings by cause (say what was
meant, why it does nothing, the fix), and the bear/bull lines
with their top items. The page has one module per left tab, each with a one-line
goal: **Baseline** (opens first: the treemap is the core answer to "where do my
tokens go"), **Skills** (one switch per skill and plugin), **Recommendations**,
**Ignored settings** (one card per cause, with fix buttons), **Plan**. Every switch feeds the Plan tab: **Copy plan** and paste it
here. Link a tab with `#skills`, `#recs`, `#plan` on the HTML path.

Quote a recommendation's reason when asked why ("listed in 407 sessions, model never
called it · you typed /name 12× (still works)"); rules are in `references/recommendations.md`.
For "where/when did I use X?", each Usage cell lists its 3 latest sessions: click copies
`claude --resume <id>` for that project, ↗ opens the raw transcript.

## 2. Dry run

Save pasted JSON (`"manage_context_plan": 1`) to `<scratchpad>/context-plan.json`
(or use the given path, usually `~/Downloads/context-plan.json`), then run
`python3 <skill-dir>/scripts/apply_plan.py <plan> --project "$PWD"`. Show the output
verbatim and explain each `✗` with `levers.md`. Ask for an explicit yes; approval of an
earlier plan doesn't count.

## 3. Apply

Re-run with `--apply`. Report the edit count, the backup directory, the undo command
(`apply_plan.py --undo <file> --apply`, dry run first too), and that changes take
effect in the **next** session.

## Rules

- Change config only through these scripts. They re-read files right before an
  atomic write, back up first, and write an undo file.
- Never print values from `~/.claude.json`; the scripts read only its keys and mask MCP configs.
- Token numbers are calibrated estimates: say "~".
- Recommendations are evidence, not a verdict; the user decides. /slash only is
  reversible and keeps `/name` working.
- Usage counts come from tool calls and typed commands only. Never quote message
  text from other sessions.

# Handoff file

Path: `~/personal/skills/.inspect/sessions-handoff.md` (gitignored), one file updated in place by every run, so a run line handed to an owner stays valid. If it doesn't exist yet, start it from the newest `sessions-*-handoff.md` the digest names. Paraphrase only: no prompt quotes, client names, pasted data or query numbers.

Each run rewrites the header, workflows, watch and dropped, and re-checks every finding's target by running its check line (cheap, whatever the scope). A pending finding keeps its number and full block; an applied or stale one moves to Carried forward as one line. When the run's scope doesn't cover a finding's evidence, leave the evidence as it was and say it wasn't re-counted.

Header: date and time of this run; scope (window, sessions kept, repos, date range); "act in a fresh session, one finding per run, highest rank first".

```markdown
## Workflows
- <name> · <trigger> · <usual chain> · <k> sessions (1a2b3c4d, 5e6f7a8b …)

## Carried forward
- F<n> — <title>: applied | stale (<what you checked>, <date>)   ← pending ones keep their full block below

## F1 — <title>
- sink: improve-skills | inspect-skill-flow | agents-md-improver | new skill | ~/.claude/CLAUDE.md | hook | config | memory
- target: <exact path, or settings key>
- target status: missing | ignored (<file:line of the existing rule>) | pending since <date first proposed>
- evidence: <k> sessions, <d> days, <r> repos — <id prefix + date: what happened, paraphrased>
- cost: <turns or minutes lost>
- lesson: <what the target should know, and why it is silent or wrong now>
- change: <the concrete edit: a diff, a line, or a skill outline>
- run: `/improve-skills ~/personal/skills/.inspect/sessions-handoff.md F1`
- check: <one command whose output shows whether the change landed, e.g. `grep -c '<new heading>' <target>` (0 = pending)>

## Watch
- <below the evidence floor, with counts>

## Dropped
- <covered or one-off, with the reason>
```

Cite sessions by id prefix, not by S-label: labels renumber whenever the window changes, so an S-label means nothing to the next run.

# New-skills mode

`--new-skills` asks one question: what do you keep doing by hand that a skill should do for you? Every other sink is out of scope for this run. If a finding belongs to another sink, it goes on one "also seen" line in chat and stays out of the handoff, so a narrow run doesn't overwrite another sink's findings.

Default window: `--sessions 30 --min-turns 6`. A session needs more than 5 typed turns to show a routine. Shorter ones are mostly one-off questions, and they water down the counts.

## Where candidates come from

- Recurring phrases and flows marked `no skill ran`. These are the strongest leads, because the user carried the routine with no skill's help.
- A prompt the user retypes with small changes: same opening, different client, ticket or PR. The template is the skill and the variable part is its argument.
- An MCP or tool sequence repeated across sessions (e.g. list clients > query, get issue > comments). The order the user wants is knowledge no skill holds yet.
- A fix the user gives again and again for the same error. The fix belongs in the skill that runs the step.

## Before proposing

- If an existing skill covers ≥70% of the candidate, extend that skill instead and hand it to improve-skills. One more near-duplicate is what find-overlapping-skills exists to catch.
- Pick a home by spread. All sessions in one repo: that repo's `.claude/skills`. ≥2 repos: this skills repo. Start narrow; a skill can be promoted later, but a global one that only fits one repo misfires everywhere else.

## Confidence

The tier comes from the number of supporting sessions, not from how sure the reading feels:

| Sessions (≥2 days) | Tier | Action |
|---|---|---|
| 1–2 | tentative | watch list only |
| 3–5 | moderate | propose |
| 6–10 | strong | propose, rank first |
| 11+ | very strong | propose, and also ask why no skill exists yet |

## Proposal shape

One block per candidate, in the handoff's finding format with `sink: new skill`. The `change` field holds:

```markdown
- name: <verb-noun>
- trigger: when <the situation, in the user's words, paraphrased>
- action: <the chain it runs, ≤5 steps>
- argument: <the part that varied between sessions>
- home: <repo>/.claude/skills | ~/personal/skills
- tier: moderate | strong | very strong (<k> sessions, <d> days, <r> repos)
- saves: <turns or minutes per run × runs seen>
- run: `/skill-creator:skill-creator <name>` with this block
```

Keep one trigger and one action per candidate. If a candidate needs "and also", it is two skills, or one skill and a CLAUDE.md line.

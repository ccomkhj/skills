# `.dualhaul/` file formats

Every file lives under `.dualhaul/` at the repo root. Append `.dualhaul/` to
`.gitignore` on init. A cold-woken racer never reads these — it gets a
self-contained brief — so these templates are purely for the orchestrator and
the human.

---

## `STATE.md` — the state machine

```
PHASE: <understand | goal | iterate | summarize | cleanup>
STATUS: <ACTIVE: orchestrator | WAITING-USER: <gate> | RACING: R<n> | BLOCKED: <reason> | DONE>
ROUND: <current dual-loop round, 0 before iterate>
ROUNDS: <hard round cap, default 5>
RACER_CLAUDE: <model id for the Claude racer, e.g. claude-sonnet-4-6>
RACER_CODEX: <model id for the Codex racer, e.g. gpt-5-codex>
ORCH_MODEL: <the orchestrator's own model — RACER_CLAUDE must differ from this>
GOAL: <one-line restatement of the /goal condition>
BASE: <git short-sha the iteration started from>

## Round log
- R1: <winner=claude|codex|neither> — <one line: what was kept / why>
- R2: ...
```

`PHASE` is what lets a re-invoked `/dual-haul` resume at the right step.
`STATUS: WAITING-USER: <gate>` marks one of the three human gates
(`approve-goal`, `pick-models`, `confirm-pr`).

---

## `UNDERSTANDING.md` — output of dual-understand

```
# Understanding

## What we're improving
<the thing — file/module/endpoint/behavior — and where it lives>

## What's wrong / insufficient now
<the concrete deficiency, with evidence: a slow number, a failing case, a smell>

## What "better" means
<the target state, concretely>

## Success signal (must be transcript-demonstrable)
<the measurable check that proves "better": a test, a benchmark number, a
file-count, an exit code — something Claude's own output can show, because the
/goal evaluator only reads the conversation>

## Constraints (must not change on the way there)
- <public API stays stable / no new deps / etc.>

## Out of scope
- <explicitly excluded>
```

---

## `GOAL.md` — output of dual-goal

```
# Goal

## Completion condition (the /goal text, <=4000 chars)
<one measurable end state + a stated check + constraints + a turn clause.
Written so Claude's own output demonstrates it. Example:

  All tests in tests/pricing pass (`pytest tests/pricing -q` exits 0) and the
  p95 of `bench/price.py` is <= 40ms (printed by the script), without modifying
  the public signature of price(), or stop after 5 rounds.>

## The line to run
/goal <the condition above on one logical line>

## Notes
<why the check is transcript-demonstrable; any risk the evaluator misreads it>
```

---

## `R<N>.md` — one per dual-loop round

```
# R<N> — race

## Brief given to both racers
<the improvement target + what the previous round failed at + constraints.
This is the body that goal_race embeds into each racer's prompt; also saved
verbatim as .dualhaul/R<N>-brief.md>

## Claude racer (model: <m>)
- Diff: <files touched, +/- lines>
- Check result: <output of the stated check in its worktree>
- Notes: <approach, anything notable>

## Codex racer (model: <m>)
- Diff: ...
- Check result: ...
- Notes: ...

## Verdict
- Winner: <claude | codex | neither>
- Why: (1) goal-condition progress  (2) check/correctness  (3) diff size/clarity
- Merged: <commit sha applied to main tree, or "nothing — both failed">
- Main-tree check after merge: <output, so the /goal evaluator sees it>
- Next round should fix: <what's still short of the goal>
```

---

## `SUMMARY.md` — output of dual-report

```
# Summary

## Goal vs achieved
- Goal: <condition>
- Achieved: <yes / partial — with the final check numbers>

## Per round
- R1: winner=<...>, kept <...>
- R2: ...

## Net change kept
<files, +/- lines, the before→after on the success signal>

## Correctness
<which checks pass on the final main tree>

## Follow-ups / left undone
- <...>
```

---

## `USER_NOTES.md` — mid-flight steers (created lazily by `goal_inject`)

```
# User notes (mid-flight)

## N1 (added <ts>, during R<n>)
<the note>
**Status:** unaddressed
```

The orchestrator addresses unaddressed notes before starting the next round,
then marks them `**Status:** addressed in R<n>`.

---
name: dual-report
description: Phase 4 of dual-haul. Fires once the /goal condition is met (the goal auto-clears) or the round cap is hit. Reports goal-vs-achieved with the final check numbers, which racer won each round and why, the net diff that was kept, and what's still open. Writes .dualhaul/SUMMARY.md. Use after dual-loop concludes a dual-haul run.
---

# dual-report

Phase 4 of **dual-haul**. Runs when iteration ends — either the goal cleared
(condition met) or the round cap was reached. Produces `.dualhaul/SUMMARY.md`
and a concise chat recap. This is also the source for the PR body in dual-ship.

## What to report

Read `STATE.md` (round log), every `R<N>.md`, and the current main tree. Then
write `.dualhaul/SUMMARY.md` (template in
[../dual-haul/reference/file-formats.md](../dual-haul/reference/file-formats.md)) covering:

1. **Goal vs achieved** — restate the `/goal` condition and whether it was met. If partial (cap hit), give the final check numbers and how far short.
2. **Per round** — who won (claude / codex / neither) and the one-line reason. This shows where the value came from and whether one racer dominated.
3. **Net change kept** — the cumulative diff against the base commit (`git diff <BASE>..HEAD --stat`), and the before→after on the success signal.
4. **Correctness** — which checks pass on the final main tree right now. Re-run the stated check and put its output in the summary; don't claim "passing" from memory.
5. **Follow-ups / left undone** — anything out of scope, deferred, or newly surfaced.

## Verify before you claim

Before writing "goal achieved", actually run the stated check on the main tree
and paste the output. Evidence before assertion — a summary that overstates the
result is worse than one that honestly reports a partial win.

## Hand off

Show the user the recap (goal-vs-achieved + net diff stat + correctness line),
then advance `PHASE: cleanup` and hand to dual-ship:

> Goal met (or: cap reached, partial). Summary in `.dualhaul/SUMMARY.md`.
> Next: `dual-ship` to commit on a branch and open a PR — I'll show you the PR
> body and branch first.

Leave the worktrees alone — dual-ship tears them down as part of finishing.

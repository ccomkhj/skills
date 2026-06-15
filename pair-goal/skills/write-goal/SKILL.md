---
name: write-goal
description: Phase 2 of pair-goal. Turns .pairgoal/UNDERSTANDING.md into a /goal-ready completion condition — one measurable end state, a stated transcript-demonstrable check, the constraints that must hold, and a turn cap — written to .pairgoal/GOAL.md plus the literal /goal line for the user to run. Use after train-orchestrator, or standalone to craft a good /goal condition from a clear improvement target.
---

# write-goal

Phase 2 of **pair-goal**. Converts `.pairgoal/UNDERSTANDING.md` into a
completion condition you can hand to Claude Code's `/goal` command, written to
`.pairgoal/GOAL.md`.

## What makes a good /goal condition

`/goal`'s evaluator is a fast model that, after every turn, reads **only the
conversation** (it runs no tools) and decides yes/no. So a strong condition has
all four parts:

1. **One measurable end state** — a test result, a benchmark threshold, a file count, an empty queue, an exit code. Not "better" or "cleaner".
2. **A stated check** — *how* it's proven, phrased so the agent's own output demonstrates it: `pytest tests/x -q exits 0`, `bench/run.py prints p95 <= 40ms`, `git status is clean`.
3. **Constraints that must hold** — what must not change on the way there (public signatures, deps, other tests).
4. **A turn clause** — `or stop after N rounds`, so a goal that can't be met still terminates. Use `ROUNDS` from `STATE.md` (default 5).

Keep it ≤ 4000 characters. Pull the end state and signal straight from
UNDERSTANDING.md's "What better means" and "Success signal" — if that signal
wasn't transcript-demonstrable, fix it now or flag it loudly (the goal will
otherwise loop forever, since the evaluator can never see the proof).

## Process

1. Read `.pairgoal/UNDERSTANDING.md`. If the success signal is missing or unmeasurable, go back to the user (or train-orchestrator) — don't paper over it.
2. Draft the condition with the four parts above, on one logical line.
3. Write `.pairgoal/GOAL.md` (template in [../pair-goal/reference/file-formats.md](../pair-goal/reference/file-formats.md)): the condition, the literal `/goal …` line, and a note on why the check is transcript-demonstrable.
4. Set `GOAL:` (one-line restatement) in `STATE.md`, advance `PHASE: goal`.

## The gate — the user runs /goal

You cannot execute a slash command yourself. So present the line and hand off:

> Goal condition ready. Review it, then run this yourself to start the loop:
>
> `/goal <condition>`
>
> Once it's active, each turn I'll run one pair-iterate race round until the
> condition holds, then summarize.

Set `STATUS: WAITING-USER: approve-goal`. Wait for the user to approve (and
possibly edit) and to actually run `/goal`. Only then does pair-iterate begin.

## Don't

- Don't make the condition depend on something the agent won't print. If proving it requires reading a file or running a tool, make the agent *run that and surface the output* part of the loop's job — and say so in GOAL.md.
- Don't omit the turn clause. A goal with no cap can run away.
- Don't widen scope beyond UNDERSTANDING.md. The goal is the contract; keep it tight.

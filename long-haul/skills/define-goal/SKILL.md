---
name: define-goal
description: Phase 2 of long-haul. Turn .longhaul/SPEC.md into a /goal-ready completion condition — one measurable end state, a stated transcript-demonstrable check, the constraints that must hold, and a round cap — written to .longhaul/GOAL.md plus the literal /goal line for the user to run. If the end state isn't clear or measurable, iterate with the user one question at a time until it is. Use after sharpen-spec, or standalone to craft a good /goal condition from a clear spec.
---

# define-goal

Phase 2 of **long-haul**. Converts `.longhaul/SPEC.md` into a completion
condition you can hand to Claude Code's `/goal`, written to `.longhaul/GOAL.md`.
This condition is the target the whole haul steers by — get it sharp.

## What makes a good /goal condition

`/goal`'s evaluator is a fast model that, after every turn, reads **only the
conversation** (it runs no tools) and decides yes/no. A strong condition has all
four parts:

1. **One measurable end state** — a test result, a benchmark threshold, a file count, an empty queue, an exit code. Not "better" or "done".
2. **A stated check** — *how* it's proven, phrased so the agent's own output demonstrates it: `pytest tests/x -q exits 0`, `bench/run.py prints p95 <= 40ms`, `git status clean`.
3. **Constraints that must hold** — what must not change on the way there (public signatures, deps, other tests).
4. **A round clause** — `or stop after N rounds`, so a goal that can't be met still terminates. Use `ROUNDS` from `STATE.md` (default 8).

Keep it ≤ 4000 characters. Pull the end state and check straight from SPEC.md's
"Done looks like".

## Iterate until the end state is clear

If SPEC.md's success signal is missing, fuzzy, or not transcript-demonstrable,
**do not paper over it** — the goal would loop forever, since the evaluator can
never see the proof. Go back to the user and ask, one question at a time, until
the end state is a single measurable thing with a check whose output Claude can
print. This iteration is the point of the phase; don't shortcut it to produce a
goal you know is unverifiable.

## Process

1. Read `.longhaul/SPEC.md`. If the success signal isn't measurable + demonstrable, iterate with the user (above) before drafting.
2. Draft the condition with the four parts above, on one logical line.
3. Write `.longhaul/GOAL.md` (template in [../long-haul/reference/file-formats.md](../long-haul/reference/file-formats.md)): the condition, the literal `/goal …` line, and a note on why the check is transcript-demonstrable.
4. Set `GOAL:` (one-line restatement) in `STATE.md`, advance `PHASE: haul`.

## The gate — the user runs /goal

You cannot execute a slash command yourself. Present the line and hand off:

> Goal condition ready. Review it, then run this yourself to start the haul:
>
> `/goal <condition>`
>
> Once it's active, each turn I'll run one haul-loop round — deciding explore vs
> exploit and keeping only measured wins — until the condition holds.

Set `STATUS: WAITING-USER: approve-goal`. Wait for the user to approve (and
possibly edit) and to actually run `/goal`. Only then does the haul begin.

If invoked standalone (not by the orchestrator), note that once `/goal` is
active, `haul-loop` takes each turn until the goal clears, then `wrap-up` ships.

## Don't

- Don't make the condition depend on something the agent won't print. If proving it requires running a tool, make *running it and surfacing the output* part of the loop's job — and say so in GOAL.md.
- Don't omit the round clause. A goal with no cap can run away over the long horizon.
- Don't widen scope beyond SPEC.md. The goal is the contract; keep it tight.

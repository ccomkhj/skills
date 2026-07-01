---
name: haul-goal
description: Phase 2 of long-haul. Turn .longhaul/SPEC.md into a /goal-ready completion condition — one measurable end state, a stated transcript-demonstrable check, the constraints that must hold, and a round cap — written to .longhaul/GOAL.md plus the literal /goal line for the user to run. If the end state isn't clear or measurable, iterate with the user one question at a time until it is. Use after haul-spec, or standalone to craft a good /goal condition from a clear spec.
---

# haul-goal

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

## The proof line — make the check transcript-visible

The evaluator only sees chat, so the condition's check must be a **named command
whose output appears in the transcript** — not "the tests pass" but `pytest
tests/x -q` with its exit line shown. **Reject any success signal that isn't**: if
proving it needs a tool run, *running it and surfacing the output* is part of the
loop's job. Emit a copy-pasteable **proof line** — the exact command — that
`haul-loop` echoes verbatim each round and `haul-ship` re-runs at the end. A goal
whose proof never lands loops forever.

When the real artifact isn't locally runnable, the proof line rides on the
**committed-test proxy** named in `SPEC.md` (e.g. a static/AST check standing in
for a live Airflow run).

### Pin how the check is invoked — a green proof can lie

The proof line is only trustworthy if it runs the *right code in the right
environment*. Record the **exact invocation** in `GOAL.md`, not just the command:
which interpreter / venv / conda env (e.g. `/opt/miniconda3/envs/dp/bin/python`,
not bare `python`), and — when the haul runs in a **git worktree** — whether the
worktree actually executes the worktree's code. Editable installs are the classic
trap: an editable `pip install -e` points at the *main* repo, so a worktree
executable silently runs old code unless `PYTHONPATH=<worktree-root>` is set, and
the haul "passes" against code it never changed. If the check imports the package
directly from the tree (most pytest layouts) it's fine — but say which case
applies. A proof that's secretly run in the wrong env is worse than no proof.

### When "done" has a ratchet AND an acceptance gate

If `SPEC.md` names two tiers (a cheap per-round **ratchet check** and an
expensive/external/one-shot **acceptance gate**), the condition carries **both**,
but they play different roles — and saying so in the `/goal` text is what stops the
evaluator from declaring victory on the cheap half:

- The **ratchet** is re-run and re-printed every round; it's the measurable end
  state the loop optimizes.
- The **acceptance gate** is run **once**, late, after the ratchet is green and the
  incumbent is locked. Its evidence — a job-SUCCEEDED line, a query result, a
  sign-off — is *pasted into chat once and persists* there, so the evaluator keeps
  seeing it on later turns. State explicitly that the goal holds **only when both**
  the ratchet output **and** the gate's pasted evidence are in the transcript, so a
  ratchet-green-only turn does not trip completion. Phrase the gate's evidence as a
  **before → predicted → after** (a baseline, a pre-registered predicted value, and
  invariants that must hold), not a bare "succeeded" — so the pasted proof is
  falsifiable. `haul-loop` captures the baseline/prediction before firing.

A pure cheap-and-headless goal has no gate — the ratchet is the whole condition.

## Iterate until the end state is clear

If SPEC.md's success signal is missing, fuzzy, or not transcript-demonstrable,
**do not paper over it** — the goal would loop forever, since the evaluator can
never see the proof. Go back to the user with the `AskUserQuestion` tool — one
question per call, each offering 2–4 concrete options as tabs (the user can pick
*Other* to free-type) — until the end state is a single measurable thing with a
check whose output Claude can print. This iteration is the point of the phase;
don't shortcut it to produce a goal you know is unverifiable.

## Process

1. Read `.longhaul/SPEC.md`. If the success signal isn't measurable + demonstrable, iterate with the user (above) before drafting.
2. Draft the condition with the four parts above, on one logical line.
3. Write `.longhaul/GOAL.md` (template in [../long-haul/reference/file-formats.md](../long-haul/reference/file-formats.md)): the condition, the literal `/goal …` line, the **proof line** (the exact command the loop echoes each round — with its exact interpreter/env per "Pin how the check is invoked"), the **acceptance gate** and its pasted-evidence form if "done" has one, and a note on why the check is transcript-demonstrable.
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
active, `haul-loop` takes each turn until the goal clears, then `haul-ship` ships.

## Don't

- Don't make the condition depend on something the agent won't print. If proving it requires running a tool, make *running it and surfacing the output* part of the loop's job — and say so in GOAL.md.
- Don't omit the round clause. A goal with no cap can run away over the long horizon.
- Don't widen scope beyond SPEC.md. The goal is the contract; keep it tight.

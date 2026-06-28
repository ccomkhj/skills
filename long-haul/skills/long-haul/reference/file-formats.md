# `.longhaul/` file formats

Every file lives under `.longhaul/` at the repo root. Append `.longhaul/` to
`.gitignore` on init. These templates are for the orchestrator and the human;
the loop reads them to resume and to decide each round.

---

## `STATE.md` — the state machine

Each field's value is the part after the colon. `ROUND`/`ROUNDS` must be a bare
integer (the background driver does arithmetic on them — keep prose out of those
two values).

```
PHASE: spec            # spec | goal | haul | wrap
STATUS: ACTIVE: orchestrator   # see the STATUS values below
ROUND: 0               # current haul-loop round (integer; 0 before hauling)
ROUNDS: 8              # hard round cap
MODE: -                # explore | exploit — the mode of the current/last round (- before hauling)
STALL: 0               # consecutive rounds with no improvement to the incumbent
STALL_CAP: 2           # rounds of no progress that force an explore
INCUMBENT: none        # longhaul/incumbent@<sha> once it exists; "none" before round 1 creates it
SCORE: none            # the incumbent's measured value, e.g. "p95=41ms" or "8/10 tests"; "none" until first kept win
REPO: <abs path>       # the target repo — owns BASE, worktrees, the incumbent branch, the PR; may differ from cwd
BASE: <short-sha>      # the commit (in REPO) the haul started from — where the incumbent branch and explore attempts fork
GATES: approve_goal=required confirm_pr=required   # confirm_pr=auto for an accepted unattended finish (draft PR, no park)
GOAL: pending          # one-line restatement of the /goal condition (set by define-goal)

## Tried (explored approaches already rejected — don't re-explore)
- R6 explore: <approach> — scored <x>, did not beat incumbent

## Round log
- R1 exploit: <kept|no-progress> — <one line>
- R2 ...
```

**STATUS values:** `ACTIVE: orchestrator` (a phase is running) · `WAITING-USER:
<gate>` (parked on a human — `approve-goal`, `confirm-pr`, or `cap-decision`) ·
`HAULING: R<n>` (a round is in flight) · `GOAL-MET` (the condition holds; go to
wrap-up) · `BLOCKED: <reason>` · `DONE`. `PHASE` + `STATUS` are what let a
re-invoked `/long-haul` resume at the right step.

---

## `SPEC.md` — output of sharpen-spec

```
# Spec

## Target repo
<abs path of the repo that owns the deliverable — may differ from the invocation
cwd. BASE, worktrees, the incumbent, and the PR all live here.>

## What we're building / changing
<the deliverable — file/module/endpoint/behavior — located in the target repo>

## Done looks like (success signal — must be transcript-demonstrable)
<the measurable check whose output Claude can show: a test exit code, a
benchmark number a script prints, a file count, a lint result. Because /goal's
evaluator only reads the conversation, this must be provable in chat. If the real
artifact isn't headlessly runnable, name the runnable proxy — a committed test
standing in for it, ideally one that also guards regression in CI — and note any
live-MCP/container confirmation as belt-and-suspenders.>

## Toolbox — the skills + MCP this haul may use
- Skills: <e.g. /tdd, /review, check-voids-db — or "none beyond core editing">
- MCP: <e.g. voids-db — or "none">
(Anything not listed is out of bounds for the run.)

## Constraints (must hold throughout)
- <public API stable / no new deps / other tests stay green>

## Out of scope
- <explicitly excluded>
```

---

## `GOAL.md` — output of define-goal

```
# Goal

## Completion condition (the /goal text, <=4000 chars)
<one measurable end state + a stated check + constraints + a round clause.
Written so Claude's own output demonstrates it. Example:

  All tests in tests/pricing pass (`pytest tests/pricing -q` exits 0) and the
  p95 of `bench/price.py` is <= 40ms (printed by the script), without changing
  the public signature of price(), or stop after 8 rounds.>

## The line to run
/goal <the condition above on one logical line>

## Proof line (echoed verbatim each round, re-run at wrap-up)
<the exact command whose output proves the condition, e.g.
`pytest tests/pricing -q && python bench/price.py`. Must be a named command with
transcript-visible output — a goal whose proof never lands loops forever. This is
the cheap RATCHET check, re-run every round.>

## Check invocation (so a green proof can't lie)
<the exact interpreter/env the proof line runs under — e.g.
`/opt/miniconda3/envs/dp/bin/python -m pytest …`, not bare `python` — and, if the
haul runs in a git worktree, whether the worktree runs the worktree's code
(editable-install trap: set `PYTHONPATH=<worktree-root>` if an editable install
points at the main repo; "imports from tree directly, no action needed" if not).>

## Acceptance gate (only if "done" has an expensive/external/one-shot tier)
<the terminal gate from SPEC.md — what it is (prod job, deploy, sign-off), what it
costs, how it's run, and the EXACT pasted evidence that proves it (a job-SUCCEEDED
line, a query result). Run ONCE, late, after the ratchet is green and the incumbent
is locked; its evidence is pasted into chat and persists for the evaluator. The
goal holds only when BOTH the ratchet output and this evidence are in the
transcript. Omit this section entirely if the ratchet is the whole condition.>

## Notes
<why the check is transcript-demonstrable; any risk the evaluator misreads it
(e.g. it might declare done on the ratchet alone — the condition requires both)>
```

---

## `R<N>.md` — output of one haul-loop round

```
# Round N

## Mode: <explore | exploit>
## Why this mode
<stall counter state, or the structural reason for an early explore>

## Base: <incumbent branch@sha (exploit) | BASE@sha (explore)>

## Brief
<what this attempt targets — for exploit, what the incumbent still falls short
on; for explore, the different approach being tried and why>

## What was done
<summary of the implementation + the commits made in the worktree>

## Check output (run in the worktree)
```
<the goal's stated check output, pasted>
```

## Score: <measured value, e.g. p95=41ms>
## Verdict: <KEPT — new incumbent @ <sha> | DISCARDED — did not beat incumbent (score <x> vs <incumbent score>)>
## Still short of goal: <what remains, or "none — condition holds">
```

---

## `PROGRESS.log` — the structured trail of a `--background` run

Append-only, one block per loop, authored by each round's agent. This is how a
detached overnight/remote run reports — the user reads it instead of the chat
transcript. Exact format:

```
[Loop1]
start: 2026-06-26 17:11:15
output: tightened the inner loop + memoized the lookup; check moved 48ms -> 46ms (kept)
error message: none
next decision: exploit (stall 0, still improving) -> hoist the per-row allocation out of the loop

[Loop2]
start: 2026-06-26 17:19:42
output: hoist attempt regressed correctness; 2 tests red, discarded
error message: test_rounding FAILED: expected 3.14, got 3.1
next decision: exploit (stall 1) -> fix the rounding, keep the hoist

[Loop3]
...

[Done] goal met after Loop6 @ 2026-06-26 18:02:30
```

The driver appends the final `[Done] …` or `[Stopped] round cap … reached …`
line itself when the loop ends.

---

## `check.sh` — the goal's runnable check (required for `--background`)

Background mode has no `/goal` evaluator, so the driver runs this between rounds:
**exit 0 iff the goal condition holds**, printing the measured value. The
runnable form of `GOAL.md`'s stated check.

```bash
#!/usr/bin/env bash
# exit 0 when the goal holds; print the measure so PROGRESS.log/driver.log show it
set -e
pytest tests/pricing -q                       # constraint: tests stay green
p95="$(python bench/price.py | grep -oE 'p95=[0-9.]+' | cut -d= -f2)"
echo "p95=${p95}ms"
awk "BEGIN{ exit !(${p95} <= 40) }"           # the threshold
```

---

## `bg.pid` — the single-driver lock

One line: the PID of the live background driver. Its presence-and-aliveness is
the lock — `haul_bg_start` refuses to start a second driver, and a foreground
round refuses to run while it's alive. The driver removes it on exit; a stale
`bg.pid` (PID not alive) is ignored.

---

## `SUMMARY.md` — output of wrap-up

```
# Summary

## Goal vs achieved
<the /goal condition; met or partial. If partial, final check output + how far short.>

## The path (explore/exploit per round)
- R1 exploit — kept, p95 48→46ms
- R6 explore — kept, hash-bucket approach, p95 41→36ms (the winning move)
- Tried & rejected: <explores that didn't beat the incumbent>

## Net change kept
<git diff BASE..incumbent --stat; before→after on the success signal>

## Correctness (re-run now)
```
<stated check output on the incumbent>
```

## Follow-ups / left undone
- <out of scope, deferred, or newly surfaced>
```

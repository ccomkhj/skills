---
name: haul-loop
description: Phase 3 of long-haul — the per-turn loop. Under an active /goal, each turn run exactly one round: decide explore (a fresh approach off the base commit) vs exploit (refine the incumbent), implement the attempt in a git worktree following the /implement contract, run the goal's stated check, and keep the attempt only if it beats the incumbent — a ratchet that never regresses. Writes R<N>.md, surfaces the check output in chat. Pass --background to detach the whole haul into a nohup'd driver that survives terminal/session close (for overnight/remote runs), logging a structured block per loop to PROGRESS.log. Use as the iteration phase of a long-haul run.
---

# haul-loop

Phase 3 of **long-haul**. The work you do on each `/goal` turn: pick a mode,
make one attempt, keep it only if it measurably beats the **incumbent**. One
round per turn. `ROUND` in `STATE.md` is the counter.

Two ways to run: **foreground** (the default — one round per `/goal` turn, a
human watching) and **`--background`** (detach the whole haul so it survives the
terminal closing — see [Running in the background](#running-in-the-background)).

## The contract

- **The incumbent is a ratchet.** `INCUMBENT` (a branch tip + its recorded `SCORE` on the goal's check) holds the best result so far. Nothing replaces it unless it measures **strictly better**. The haul therefore never regresses — a bad attempt is simply discarded.
- **Every attempt is isolated.** Each round spins one git worktree (`.longhaul/attempt/`) off the right base, you implement there, and only a measured win is merged. A failed attempt costs nothing. (Where the acceptance gate consumes a pushed branch/CI artifact, the kept incumbent is the real working branch rather than an ephemeral `longhaul/incumbent` — see [the CI-artifact-gated exception](#the-incumbent-branch--set-it-up-once).)
- **Every round's proof lands in chat.** After the round you re-state the goal's check output. That transcript is what the `/goal` evaluator reads to decide whether to continue.
- **You stay inside the toolbox.** Use only the skills + MCP `SPEC.md` declared. A long autonomous run that reaches for undeclared tools is the drift the spec exists to prevent.
- **Every git operation runs in `REPO`.** `BASE`, the worktrees, the incumbent branch, and the check all live in the target repo (`REPO` in `STATE.md`, where `.longhaul/` sits) — which may not be the cwd the haul was invoked from.

## Explore vs exploit — the decision that opens each round

A long haul is a bandit problem: keep pulling the arm that's paying off, but
switch arms when it stops. Each round, choose one mode and **write the choice
and its reason into `R<N>.md`** before you implement:

- **EXPLOIT** *(the default while the incumbent is improving)* — branch the worktree off the **incumbent** and refine it, targeting what it still falls short of. This is most rounds.
- **EXPLORE** *(when the incumbent has stalled)* — branch the worktree off **`BASE`** and try a *materially different approach* per the spec — not a tweak of the incumbent. A fresh arm.

**The stall rule (checkable, mechanical):** `STALL` counts consecutive rounds
that did **not** improve the incumbent's score. When `STALL` reaches `STALL_CAP`
(default 2), the next round **must EXPLORE**. Any round that improves the
incumbent resets `STALL` to 0 and you return to exploiting.

**Judgment escape hatch:** even before the cap, if the incumbent's approach is
structurally incapable of reaching the goal (e.g. the algorithm is O(n²) and the
goal needs O(n log n)), explore now — and say why in `R<N>.md`.

**Don't re-explore a dead end.** `STATE.md`'s `## Tried` list records each
explored approach and its score. Before exploring, read it; pick an approach not
already tried and rejected.

## The incumbent branch — set it up once

The ratchet needs a durable home for the best-so-far. On the **first round only**
(when `longhaul/incumbent` doesn't yet exist), create it at `BASE` and check the
**main tree onto it** — from here on the main tree always carries the incumbent:

```bash
git branch longhaul/incumbent <BASE> && git checkout longhaul/incumbent
```

Record `INCUMBENT: longhaul/incumbent@<BASE>` and `SCORE: none` (no measured win
yet). The incumbent branch only ever moves in step 6, and only on a measured
win — so a losing attempt can never touch it.

**Exception — CI-artifact-gated hauls.** When `GOAL.md`'s acceptance gate consumes
a **pushed branch or a CI-built artifact** (e.g. a prod job that runs
`image:<branch>` built by CI on push), an ephemeral local-only incumbent can't feed
the gate — the gate needs a *real, pushed* branch. In that mode, make the incumbent
the **existing working branch** (don't invent `longhaul/incumbent`); record it as
`INCUMBENT: <branch>@<sha>`. The ratchet's worktree isolation (steps 3–6) still
governs each local code attempt — you still attempt in a throwaway worktree and only
fast-forward a measured win onto the working branch — but the *kept* incumbent is
pushable, and the gate runs on the pushed incumbent. Decide this once, at setup,
from `GOAL.md`'s gate; don't silently drift into committing on the working branch
mid-haul (the live ADR-0003 run did exactly that, bypassing the whole contract).

## One round

1. **Pick the mode.** First, **honor the single-driver lock** — if `.longhaul/bg.pid` names a live process, a background driver owns this haul; do not run a round, report `haul_bg_status` and stop. Otherwise: apply the stall rule + escape hatch, read `## Tried` if exploring, record `MODE` and the reason in `R<N>.md` and `STATE.md`, set `STATUS: HAULING: R<N>`.
2. **Write the brief.** Compose `R<N>.md`'s brief: for exploit, what the incumbent (`R<N-1>.md` + its check) still falls short on; for explore, the different approach being tried and why it might clear what exploitation couldn't.
3. **Spin the attempt worktree on a throwaway branch.** Never check out the incumbent branch itself — branch a fresh attempt ref off the right base so a failure can't move the incumbent:
   ```bash
   git worktree add -b longhaul/attempt-r<N> .longhaul/attempt <base>
   ```
   `<base>` is `longhaul/incumbent` (exploit) or `BASE` (explore). Before the first win, both are the same commit, so round 1 works either way.
4. **Implement — follow the /implement contract.** `/implement` is user-invoked, so inside this turn you execute its contract yourself, in the worktree (`cd .longhaul/attempt`): build the work per the brief; use `/tdd` at the pre-agreed seams; typecheck regularly; run targeted tests often and the full suite at the end; **commit continuously** as you go (the progress must accrete in git, not live in the working tree). Stay within the toolbox.
5. **Measure.** Run the goal's **ratchet check** (the per-round proof line) in the worktree and capture its output. This output is the attempt's `SCORE`. (The acceptance gate, if `GOAL.md` has one, is *not* run here — see [The acceptance gate](#the-acceptance-gate--fire-it-once-late).)
6. **Ratchet — keep only a measured win.** Decide if the attempt is a win: if `SCORE: none` (no incumbent yet), **any attempt that passes the check** is the first win; otherwise it must beat the incumbent's score. From the main tree (which holds `longhaul/incumbent`):
   - **Win, exploit** (attempt forked off the incumbent → linear): `git merge --ff-only longhaul/attempt-r<N>`.
   - **Win, explore** (attempt forked off `BASE` → different lineage): `git reset --hard longhaul/attempt-r<N>` — the incumbent now points at the explored lineage.
   - Either win → update `INCUMBENT`/`SCORE`, set `STALL: 0`.
   - **Not a win** → keep nothing (incumbent untouched). Increment `STALL`. If it was an explore, append the approach + its score to `## Tried`.
7. **Prove it in chat.** The main tree already holds the incumbent — **re-run `GOAL.md`'s proof line there and print its output verbatim**. This is the transcript the `/goal` evaluator judges; the same command every round is what lets it decide. Note in `R<N>.md` what's still short of the goal.
8. **Tear down + advance.** `git worktree remove .longhaul/attempt --force`, `git branch -D longhaul/attempt-r<N>`, `git worktree prune`. Bump `ROUND`; append a one-line `R<N>` entry to `STATE.md`'s round log. **Then check the proof from step 7: if the goal condition now holds, set `PHASE: wrap`, `STATUS: GOAL-MET`, and proceed to `wrap-up`** — don't rely on `/goal`'s evaluator alone to route you. **But if `GOAL.md` has an acceptance gate, the condition is *not* met on a green ratchet alone — the gate's pasted evidence must also be in the transcript (see below).** Otherwise end the turn; `/goal` decides whether to start another.

## The acceptance gate — fire it once, late

When `GOAL.md` carries an **acceptance gate** (an expensive/external/one-shot
tier — a prod job, a deploy, a sign-off), the per-round loop above optimizes the
**ratchet** only; the gate is a separate, terminal **phase**, not a round — don't
tick `ROUND` for it, and don't fold it into the same turn as the ratchet work.

**Don't run it every round.** It costs hours and real money — running it each turn
is the waste the two-tier split exists to prevent. Most rounds never touch it. Fire
it **once**, after the ratchet is green and the incumbent is locked (the score holds
and further rounds aren't improving it).

**Pre-register the expected result before you spend the money.** A bare "job
SUCCEEDED" proves nothing about *correctness*. Before firing, with the toolbox's
read-only tools (e.g. the DB MCP), capture and paste:
- the **baseline** the gate should change (e.g. the current dense series count),
- a **pre-registered prediction** of the post-gate value, computed from the inputs
  (e.g. "841 = 91 sold pairs + 25 never-sold × 30"), and
- an **invariant / survival set** to re-check afterward (e.g. the exact rows that
  must NOT disappear), plus any **corner case** that could silently corrupt the
  result (e.g. bundle-only sales that might be wrongly pruned).
Then the gate's evidence is a real *before → predicted → after* with invariants held
— not an unfalsifiable green. This is what the live ADR-0003 run did well; make it
the rule, not a lucky instinct.

**Run it across turns — never block one turn for hours.** A multi-hour gate
(CI image build → multi-job prod run → polling) must be **launched, then the turn
ends**; subsequent `/goal` turns poll status and proceed. Submit the job
(background or fire-and-record-the-id), print what's pending, and end the turn —
don't churn synchronously for 15+ minutes holding the turn open. Each later turn:
check the job, advance to the next stage or keep waiting, end the turn. Use
`ScheduleWakeup` for external state the harness can't notify you about.

**Paste evidence verbatim; only then is the goal met.** When the gate completes,
paste the job-SUCCEEDED line and the after-query against the pre-registered baseline
(prediction matched, invariants held). `GOAL-MET` requires *both* the ratchet output
(re-printed) and this gate evidence present — a green ratchet with no gate evidence
is **not** done.

**If the gate fails**, it's a finding, not a win: the ratchet may be green while the
real artifact is wrong. Treat the failure as the next round's brief (a fix to
exploit), and don't mark `GOAL-MET`.

A goal with no acceptance gate skips all of this — the ratchet is the whole signal.

## Running in the background

Foreground hauling rides `/goal`, which lives in the interactive session — close
the terminal and it dies. `--background` instead hands the whole haul to a
detached driver (`reference/haul-bg.sh`) that **survives the terminal, and on
Linux the whole login session** — so you can submit it on a remote box and let
it grind overnight. The driver runs one headless `claude -p` round at a time,
runs the goal's check between rounds, and stops when the goal holds or the round
cap trips.

Three things differ from foreground, and you must set them up before detaching:

- **The check becomes a script.** `/goal`'s evaluator is gone, so the driver
  decides "goal met" by running `.longhaul/check.sh` (exit 0 = met). If it
  doesn't exist, write it from `GOAL.md`'s **ratchet** check — the runnable form,
  exit 0 when the condition holds, printing the measured value (template in
  [../long-haul/reference/file-formats.md](../long-haul/reference/file-formats.md)).
  Confirm it with the user. **`check.sh` can only express the ratchet** — an
  acceptance gate (a prod job, a deploy, a sign-off) can't be reduced to an
  exit-0 between-rounds script, so a goal that *requires* a gate is **not fully
  background-able**: the detached driver can ratchet to green unattended, but the
  gate stays a foreground/manual terminal step. Say this — don't let the user
  detach expecting the gate to fire itself.
- **No human approves tool calls.** The driver runs `claude` with
  `--permission-mode bypassPermissions`; there's no one there overnight. For pure
  code rounds the blast radius is bounded by the per-round worktree — **but that
  bound is false the moment a round's check or toolbox reaches external or paid
  infra** (a prod job, a deploy, an MCP write): with no human in the loop it can
  spend real money and mutate production. If the toolbox includes anything like
  that, say so plainly and get explicit go-ahead before detaching — or keep the
  gate out of the background run entirely.
- **Progress lands in a file, not chat.** Each round's agent appends one
  structured block to `.longhaul/PROGRESS.log` (the `[LoopN]` template — see
  file-formats). That file is how the user checks in on a detached run.

To launch:

```bash
source ~/.claude/skills/long-haul/reference/haul-bg.sh   # or the plugin path
haul_bg_start        # detaches; prints the PID + log paths. Safe to close the terminal.
haul_bg_status       # is it alive? + tail PROGRESS.log
haul_bg_stop         # kill the run (PID-scoped; never killall claude)
```

**The single-driver lock.** Exactly one thing may drive `.longhaul/` at a time —
a foreground `/goal` loop *and* a live background driver both mutating the same
incumbent corrupts it. `haul_bg_start` refuses if a driver is already alive
(`bg.pid`). And a foreground round must **refuse to run while `bg.pid` is
alive** — check it at the top of step 1; if a driver owns the haul, this session
is read-only, so report `haul_bg_status` and stop.

### Converting a running haul to background

Mid-haul, to free the terminal: **first ensure `.longhaul/check.sh` exists** — a
foreground run never created one, and `haul_bg_start` refuses without it, so
write it from `GOAL.md`'s stated check and confirm with the user. Then
`haul_bg_start` (it resumes from `STATE.md`'s `ROUND`, picking up where the
foreground loop was), then **`/goal clear`** to retire the interactive loop, then
close the terminal. The lock makes this safe — once the driver holds `bg.pid`,
the cleared foreground loop wouldn't double-drive anyway. To come back:
`haul_bg_stop` and resume foreground with a fresh `/goal`, or just watch with
`haul_bg_status` until it finishes and pick up at `wrap-up`.

## When does the haul stop

You don't poll the goal — `/goal` does. It clears automatically when the
evaluator sees the condition met in the transcript, and the next thing you do is
`wrap-up`. But hold and surface to the user (don't burn turns) when:

- `ROUND` reaches `ROUNDS` (cap) without the goal clearing → set `STATUS: WAITING-USER: cap-decision`, report partial against the incumbent, and ask whether to raise the cap, accept, or stop. (Setting the status means a resume re-presents the question instead of running another round.)
- **The well is dry** — you've exploited to a stall *and* a following explore failed to beat the incumbent, with no untried approach left → the goal likely can't be met as specified; `STATUS: WAITING-USER: cap-decision`, surface rather than grind.
- Git worktrees fail → `STATUS: BLOCKED`, surface.

## Surfacing each round in chat

After the round, print a 5–10 line digest before ending the turn so the user
(and the `/goal` evaluator) see progress and the explore/exploit path:

```
**R4 — exploit** (stall 0, incumbent improving)
- attempt: tightened the inner loop, memoized the lookup; 3 commits
- check: bench/price.py p95 = 41ms (goal <=40ms); was 48ms
- verdict: KEPT — new incumbent @ a1b2c3d, score 41ms
- main-tree check: p95 41ms — still 1ms short of goal
```

```
**R6 — explore** (stall hit cap; exploit plateaued at 41ms)
- approach: replace the sort-based grouping with a hash bucket (off BASE)
- check: p95 = 36ms (goal <=40ms)
- verdict: KEPT — explore beat incumbent, reset incumbent @ e5f6a7b
- main-tree check: p95 36ms — goal condition now holds
```

## Hazards

The steps above already encode the ratchet, the worktree isolation, the stall
rule, and the toolbox bound — follow them and those traps don't arise. The
non-obvious ones worth calling out:

| Hazard | Rule |
|---|---|
| Goal proof never in the transcript | `/goal`'s evaluator runs no tools — re-run the check on the main tree and print it every round (step 7), or the loop never clears. |
| Leaving the attempt worktree behind | Some abort paths skip step 8 — `git worktree remove --force` + `git worktree prune` on **every** exit, not just the happy path. |
| `killall claude` to stop a background run | Kills the user's own session too. Always `haul_bg_stop` (PID-scoped). |

## Resuming mid-round

If re-invoked while `STATUS: HAULING: R<n>`: inspect `.longhaul/attempt/`. If the
worktree exists with commits, the attempt is in flight — continue implementing
or, if the check already ran, judge it (step 6). Don't spin a second worktree for
the same round. If `STATUS: GOAL-MET` or `cap-decision`, the loop is over — go to
`wrap-up`, don't start a round.

If invoked standalone (not by the orchestrator), once the goal clears end by
suggesting: "Next: `wrap-up` to report and open a PR."

---
name: dual-loop
description: Phase 3 of dual-haul — the per-turn race. Under an active /goal, each turn the orchestrator commissions two independent implementers (a Claude on a chosen model + Codex on a chosen model), each in its own git worktree off the current base commit, then judges both against the goal's stated check and merges the winning diff into the main tree. Use as the iteration phase of a dual-haul run; before round 1 it asks the user which model each racer uses.
---

# dual-loop

Phase 3 of **dual-haul**. The work you do on each `/goal` turn: race two
implementers, keep the better diff. **You are the orchestrator — you judge and
merge, you do not implement the target yourself.** Implementing it directly
throws away the entire reason for two racers.

## The contract

- **Two racers, full isolation.** A Claude racer (model `RACER_CLAUDE`, which must differ from your own `ORCH_MODEL`) and a Codex racer (model `RACER_CODEX`) each work in their **own git worktree** off the same base commit. They never see each other.
- **Nothing is kept unless it's the measured winner.** Each round you run the goal's stated check in both worktrees, pick a winner by an explicit rubric, and merge only the winner. A round can end with **neither** kept if both fail the check.
- **Every round's proof lands in chat.** After merging, re-run the check on the main tree and surface its output — that's what the `/goal` evaluator reads to decide whether to continue.

## Setup — source the helpers

```bash
source ~/.claude/skills/dual-haul/reference/handoff.sh   # or ~/.agents/... 
```

Provides `goal_race`, `goal_wait_race`, `goal_teardown`, plus human-side
`goal_watch`/`goal_status`/`goal_inject`/`goal_takeover`. These encapsulate the
CLI-spawn hazards (see [Hazards](#hazards)) — don't hand-roll the invocations.

## The model-selection gate — once, before round 1

Ask the user two things and write them to `STATE.md`:

- **Claude racer model** (`RACER_CLAUDE`) — **must differ from `ORCH_MODEL`**. The point is a *different* Claude perspective. Refuse a model equal to the orchestrator's and re-ask.
- **Codex racer model** (`RACER_CODEX`) — the model Codex runs with.

Empty values are allowed (each CLI uses its own default), but the Claude racer
must still not silently match the orchestrator. Confirm both before racing.

## One round

Each `/goal` turn does exactly one round. `ROUND` in `STATE.md` is the counter.

1. **Address user notes.** If `.dualhaul/USER_NOTES.md` has `Status: unaddressed` items, fold them into this round's brief, then mark them addressed.
2. **Write the brief.** Compose `.dualhaul/R<N>-brief.md`: the improvement target and constraints (from `GOAL.md`/`UNDERSTANDING.md`) **plus what the previous round fell short on** (from `R<N-1>.md`). This is the shared instruction both racers get; keep it goal-focused, not solution-prescriptive — let them diverge.
3. **Race.** `STATUS: RACING: R<N>`, then `goal_race <N>`. It creates `wt-claude/` + `wt-codex/` off `HEAD`, embeds the brief, and spawns both racers detached on their chosen models.
4. **Wait.** Immediately `goal_wait_race <N>` — in Claude Code via Bash `run_in_background=true` so the harness wakes you when both finish. The racers are `nohup`'d and invisible to the harness; without this you idle. Exit 3 = a racer likely died → inspect logs, treat that racer as a no-submission.
5. **Judge.** For each worktree: confirm it committed, run the goal's **stated check** there, and capture `git -C .dualhaul/wt-<name> diff <base>..HEAD --stat`. Pick the winner by this rubric, in order:
   1. **Goal-condition progress** — does the check pass / move closest to the threshold?
   2. **Correctness** — tests/behavior intact; constraints from `GOAL.md` respected.
   3. **Diff quality** — smaller, clearer, fewer incidental changes (tiebreak).
   Write `R<N>.md` (template in [../dual-haul/reference/file-formats.md](../dual-haul/reference/file-formats.md)) with both attempts, both check outputs, and the verdict.
6. **Merge the winner.** Apply the winning worktree's commit(s) to the main tree (e.g. `git cherry-pick` the racer branch, or `git merge --squash dualhaul/r<N>-<winner>` then commit). If **neither** passes, merge nothing and record why.
7. **Prove it on the main tree.** Re-run the stated check on the main tree and **print its output in chat** — this is the transcript the `/goal` evaluator judges. Note in `R<N>.md` what's still short of the goal.
8. **Tear down + advance.** `goal_teardown <N>` (removes both worktrees, deletes their temp branches). Bump `ROUND`. Append a one-line `R<N>` entry to `STATE.md`'s round log. Then end the turn — `/goal` decides whether to start another.

## When does iteration stop

You don't poll the goal yourself — `/goal` does. It clears automatically when
the evaluator sees the condition met in the transcript, and the next thing you
do is the `dual-report` phase. But hold and surface to the user (don't burn turns) when:

- `ROUND` reaches `ROUNDS` (cap) without the goal clearing → stop, report partial, ask whether to raise the cap or accept.
- **Two consecutive rounds keep nothing** (both racers fail the check) → likely the goal or approach is wrong; surface rather than grind.
- A racer CLI disappears or git worktrees fail → `STATUS: BLOCKED`, surface.

## Surfacing each round in chat

After judging, print a 5–10 line digest before ending the turn so the user (and
the `/goal` evaluator) see progress:

```
**R3 race:** winner = codex
- claude: check FAILED (2 tests red), diff 3 files +40/-12
- codex:  check PASSED, p95 38ms (goal <=40ms), diff 1 file +9/-3
- merged codex @ a1b2c3d; main-tree check: PASSED, p95 39ms
- still short: none — goal condition now holds
```

## Hazards

All handled by `handoff.sh` — listed so you don't reintroduce them.

| Hazard | Rule |
|---|---|
| `claude -p "<prompt>" <flags>` (flags after prompt) | Hangs the CLI. Flags first; `goal_race` enforces it. |
| `claude --add-dir <dir> "<prompt>"` (variadic eats prompt) | `--` terminator before the prompt. Enforced. |
| `killall claude` / `pkill codex` to recover | Kills the user's main session. Use `goal_racer_status` / `goal_takeover` (PID-scoped). |
| Two racers editing one tree | Corruption. Each gets its own worktree off the same base — never the main tree. |
| Keeping a diff you didn't check | A win must pass the stated check in its worktree AND on the main tree after merge. No check, no keep. |
| Racer model == orchestrator model | Defeats the second-perspective design. The gate refuses it. |
| Leaving worktrees behind | `goal_teardown` every round and on every abort path; `git worktree prune`. |
| Idling after `goal_race` | Racers are `nohup`'d, invisible to the harness. Always follow with `goal_wait_race` (background in Claude Code). |

## Resuming mid-round

If re-invoked while `STATUS: RACING: R<n>`: run `goal_status`. If both
`.dualhaul/wt-*/.dualhaul-done` exist, judge now. If only logs are growing, the
race is live — `goal_wait_race <n>`, don't launch a second `goal_race`.

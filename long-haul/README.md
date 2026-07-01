# long-haul

A five-skill plugin that drives **one** agent relentlessly toward a verifiable
goal over the long horizon — the solo cousin of `dual-haul`. No race; the
leverage is the **explore/exploit** discipline and a **ratcheting incumbent**
that keep a long, unattended run from drifting.

The arc, driven by an **auto-chaining orchestrator** (the main Claude session):

```
/long-haul [a spec, or a vague idea to sharpen]
   │
   ├─ 1. haul-spec   harden the ask into a spec: located deliverable,
   │                    transcript-demonstrable success signal, the *toolbox*
   │                    (allowed skills + MCP), constraints. Grill if vague.
   ├─ 2. haul-goal    forge a /goal-ready completion condition  ──▶ [GATE: you approve + run /goal]
   ├─ 3. haul-loop      each /goal turn, one round: decide explore vs exploit,
   │                    implement in a worktree (the /implement contract),
   │                    keep only a measured win on the incumbent ratchet
   ├─ (─/goal auto-clears when the condition is met, or the round cap trips─)
   └─ 4. haul-ship        goal vs achieved + the explore/exploit path, then a PR
                                                       ──▶ [GATE: you confirm]
```

## Explore vs exploit — the soul of it

A long haul is a bandit problem. The **incumbent** is the best result so far — a
durable `longhaul/incumbent` branch plus its measured score on the goal's check.
It is a **ratchet**: every attempt runs in a throwaway worktree branch and only a
*measured win* moves the incumbent (`merge --ff-only` for an exploit,
`reset --hard` for a winning explore), so a losing attempt can never touch it and
the run never regresses. Each turn the orchestrator chooses:

- **Exploit** *(the default)* — branch off the incumbent and refine it. Most rounds.
- **Explore** *(when the incumbent stalls)* — branch off the base commit and try a *materially different* approach.

A **stall** is `STALL_CAP` consecutive rounds (default 2) with no improvement;
hitting it forces the next round to explore. Any improvement resets the counter.
Rejected explores are recorded so the same dead end isn't tried twice.

## Why a long-horizon loop, not a one-shot

`/goal` keeps the session working until a condition holds. long-haul rides it,
but adds the structure a long unattended run needs: a bounded **toolbox** so it
can't wander, an **incumbent ratchet** so it never goes backward, and the
**explore/exploit** rule so it neither grinds a plateau forever nor abandons a
working line too early.

## Background mode — overnight / remote runs

`/haul-loop --background` detaches the whole haul into a `nohup`'d driver
(`reference/haul-bg.sh`) that **survives the terminal closing — and on Linux the
whole login session**, so you can submit it on a remote box and let it grind
overnight. It runs one headless `claude -p` round at a time, decides "goal met"
by running `.longhaul/check.sh` (the runnable form of the goal's check), and
writes one structured block per loop to `.longhaul/PROGRESS.log`:

```
[Loop2]
start: 2026-06-26 17:19:42
output: hoist attempt regressed correctness; 2 tests red, discarded
error message: test_rounding FAILED: expected 3.14, got 3.1
next decision: exploit (stall 1) -> fix the rounding, keep the hoist
```

```bash
source ~/.claude/skills/long-haul/reference/haul-bg.sh
haul_bg_start    # detaches; safe to close the terminal     haul_bg_status / haul_bg_stop
```

You can also **convert a running foreground haul to background** mid-flight:
`haul_bg_start` (resumes from the current round), `/goal clear`, close the
terminal. A `bg.pid` lock guarantees only one driver ever touches `.longhaul/` —
no human approves tool calls overnight, so the driver runs with
`--permission-mode bypassPermissions`, blast-radius-bounded by the per-round
worktree.

## The two human gates

Everything auto-advances except:

1. **Approve the goal** — you read the `/goal …` line `haul-goal` produces and run it yourself (slash commands are user-invoked).
2. **Confirm the PR** — `haul-ship` shows the branch + PR body before pushing. Configurable: `GATES: confirm_pr=auto` lets an accepted unattended run open a *draft* PR without parking.

For an unattended run, the orchestrator's **detach-readiness** preflight checks
the whole path is clear (Auto mode, hooks, `confirm_pr=auto`, and — for
`--background` — `check.sh` + `haul_bg_start`) so it can't silently park after
you've disconnected. The deliverable's repo is **`target_repo`**, which may
differ from the invocation cwd — `BASE`, worktrees, the incumbent, and the PR all
follow it.

## Shared state — `.longhaul/`

All coordination lives in `.longhaul/` at the repo root (gitignored), the same
pattern as the sibling `pair-*` skills:

| File | Purpose |
|---|---|
| `SPEC.md` | deliverable, success signal, toolbox, constraints (from haul-spec) |
| `GOAL.md` | the `/goal` condition + the literal line to run (from haul-goal) |
| `STATE.md` | `PHASE`, `STATUS` (incl. `GOAL-MET` → the durable loop→wrap handoff), `ROUND`/`ROUNDS`, `MODE`, `STALL`, `INCUMBENT`/`SCORE`, `REPO`, `BASE`, `GATES`, the `## Tried` list, the round log |
| `R<N>.md` | per-round: mode + why, the attempt, the check output, the verdict |
| `SUMMARY.md` | goal vs achieved, the explore/exploit path, net kept diff |
| `attempt/` | the per-round git worktree (created/torn down each round) |
| `check.sh` | the goal's runnable check, exit 0 = met (required for `--background`) |
| `PROGRESS.log` | one structured `[LoopN]` block per round (a `--background` run's trail) |
| `bg.pid` | the single-driver lock — PID of the live background driver |

## Install

This is a plugin directory. To use the skills directly without a marketplace,
symlink each skill into `~/.claude/skills`:

```bash
for s in long-haul haul-spec haul-goal haul-loop haul-ship; do
  ln -sfn "$PWD/long-haul/skills/$s" "$HOME/.claude/skills/$s"
done
```

Requires a git repo (worktrees) and `/goal` (Claude Code ≥ v2.1.139). Unlike the
`pair-*` skills it is **solo** — no Codex, no second model, so no `~/.agents`
symlink is needed.

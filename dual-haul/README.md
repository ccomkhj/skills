# dual-haul

A six-skill plugin that turns "make this better" into a measured, shipped improvement.

The arc, driven by an **auto-chaining orchestrator** (the main Claude session):

```
/dual-haul [what you want improved]
   │
   ├─ 1. dual-understand   understand what's wrong now and what "better" means (improvement-focused brainstorming)
   ├─ 2. dual-goal           forge a /goal-ready completion condition  ──▶ [GATE: you approve + run /goal]
   ├─ 3. dual-loop         each /goal turn: a different-model Claude and Codex race in
   │                          separate git worktrees; orchestrator judges + merges the winner
   │                          ──▶ [GATE: you pick the two racer models, once]
   ├─ (─/goal auto-clears when the condition is met─)
   ├─ 4. dual-report            goal vs achieved, who won each round, the net kept diff
   └─ 5. dual-ship             commit on a branch, open a PR  ──▶ [GATE: you confirm]  then tear down worktrees
```

## Why a race, not a solo loop

`/goal` already keeps one session working until a condition holds. dual-haul adds a **second and third pair of hands per turn**: the orchestrator doesn't implement directly — it commissions two independent attempts (a Claude on a model you choose, distinct from the orchestrator's; and Codex on a model you choose), each isolated in its own worktree off the same base commit, then keeps the better diff measured against the goal's own check. Divergent attempts surface more of the solution space than one agent iterating on itself.

## The three human gates

Everything auto-advances except:

1. **Approve the goal** — you read the `/goal …` line dual-goal produces and run it yourself (slash commands are user-invoked).
2. **Pick the racer models** — once, before round 1: which model the Claude racer uses (must differ from the orchestrator's) and which model Codex uses.
3. **Confirm the PR** — dual-ship shows the branch + PR body before pushing.

## Shared state — `.dualhaul/`

All coordination lives in `.dualhaul/` at the repo root (gitignored), the same pattern as the sibling `pair-*` skills:

| File | Purpose |
|---|---|
| `UNDERSTANDING.md` | problem, improvement target, success signal, constraints (from dual-understand) |
| `GOAL.md` | the `/goal` condition + the literal line to run (from dual-goal) |
| `STATE.md` | `PHASE`, `STATUS`, `ROUND`, `ROUNDS`, racer models, round log |
| `R<N>.md` | per-round: both attempts, the check results, the verdict, what to fix next |
| `SUMMARY.md` | goal vs achieved, per-round winners, net kept diff |
| `wt-claude/`, `wt-codex/` | per-racer git worktrees (created/torn down each round) |

## Install

This is a plugin directory. To use the skills directly without a marketplace, symlink each skill into both agent skill roots (Claude Code + Codex):

```bash
for s in dual-haul dual-understand dual-goal dual-loop dual-report dual-ship; do
  ln -sfn "$PWD/dual-haul/skills/$s" "$HOME/.claude/skills/$s"
  ln -sfn "$PWD/dual-haul/skills/$s" "$HOME/.agents/skills/$s"
done
```

Requires `claude` and `codex` on `PATH`, and a git repo (worktrees). `/goal` requires Claude Code v2.1.139+.

---
name: dual-ship
description: Phase 5 of dual-haul — the finishing move. Commits the kept improvement on a feature branch, opens a PR (body drawn from .dualhaul/SUMMARY.md), and tears down the dual-haul worktrees and state. Always confirms the branch name and PR body with the user before pushing. Use as the last phase of a dual-haul run, after dual-report.
---

# dual-ship

Phase 5 of **dual-haul**. Ships the kept improvement and cleans up the
machinery. This is an outward-facing action (a PR) — **confirm with the user
before pushing anything.**

## Preconditions

- `dual-report` has written `.dualhaul/SUMMARY.md`.
- The kept changes are committed on the main working branch (dual-loop merged each winner). If there are uncommitted leftovers, show `git status` and ask before proceeding.

## Steps

1. **Tear down racer worktrees first.** `goal_teardown` (no round arg removes both `wt-claude`/`wt-codex` and prunes); then `git branch --list 'dualhaul/*'` and delete any leftover temp branches. The PR must contain only the kept improvement, not race scaffolding.
2. **Branch.** If the work landed on `main`/`master`, create a feature branch (e.g. `dualhaul/<short-topic>`) and move the commits there — never open a PR from the default branch. If already on a feature branch, use it.
3. **Confirm — the gate.** Show the user: the branch name, the commit list (`git log <base>..HEAD --oneline`), and the proposed PR title + body (drawn from `SUMMARY.md`: goal, what was achieved, net diff, correctness, follow-ups). Set `STATUS: WAITING-USER: confirm-pr`. Wait for an explicit yes.
4. **Push + PR.** On confirmation: `git push -u origin <branch>`, then `gh pr create --title "…" --body "…"` (body from SUMMARY.md). Report the PR URL.
5. **Finish.** Set `STATUS: DONE`, `PHASE: cleanup` in `STATE.md`. Ask the user whether to delete `.dualhaul/` now or keep it for reference (it's gitignored either way). If they ran `/goal` and it's somehow still active, remind them it auto-cleared on success, or to `/goal clear`.

## PR body shape

Pull straight from `SUMMARY.md`. End the body with the standard trailer:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

And the commits (if you author them here) end with:

```
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

## Don't

- Don't push or open a PR before the user confirms — it's outward-facing and hard to reverse.
- Don't include `.dualhaul/` or the `dualhaul/r<N>-*` branches in the PR. They're transient.
- Don't claim the PR is open until `gh pr create` returns a URL — paste it.

---
name: wrap-up
description: Phase 4 of long-haul — the finishing move. Fires once the /goal condition is met (the goal auto-clears) or the round cap trips. Reports goal-vs-achieved with the final check output, the explore/exploit path each round took, and the net kept diff; then commits the incumbent on a feature branch and opens a PR. Always confirms the branch and PR body with the user before pushing. Use as the last phase of a long-haul run.
---

# wrap-up

Phase 4 of **long-haul**. Runs when the haul ends — the goal cleared, or the
round cap was hit. It does two things: report what happened, then ship the
incumbent. The PR is outward-facing — **confirm with the user before pushing.**

## Report — write SUMMARY.md

Read `STATE.md` (round log + `## Tried`), every `R<N>.md`, the current
incumbent, and — if the haul ran detached — `.longhaul/PROGRESS.log` (the
per-loop trail an overnight run leaves instead of chat). Write
`.longhaul/SUMMARY.md` (template in
[../long-haul/reference/file-formats.md](../long-haul/reference/file-formats.md))
covering:

1. **Goal vs achieved** — restate the `/goal` condition and whether it was met. If partial (cap hit), give the incumbent's final check output and how far short.
2. **The path** — per round, the mode (explore/exploit) and one-line result, plus which explores were tried and rejected (`## Tried`). This shows where the win came from — a refinement or a fresh approach.
3. **Net change kept** — the cumulative diff of the incumbent against `BASE` (`git diff <BASE>..<incumbent> --stat`), and the before→after on the success signal.
4. **Correctness** — re-run the goal's stated check on the incumbent **now** and paste the output. Don't claim "passing" from memory.
5. **Follow-ups** — anything out of scope, deferred, or newly surfaced.

**Evidence before assertion:** run the check before writing "goal achieved". An
honest partial beats an overstated win.

## Ship — branch, confirm, PR

1. **Branch.** The kept work is the `longhaul/incumbent` branch (its commits, from `BASE`). Rename it to a readable feature branch for the PR — `git branch -m longhaul/incumbent longhaul/<short-topic>` — never open a PR from the default branch. Delete any leftover `longhaul/attempt-*` scratch branches and `git worktree prune` so the PR carries only the kept work, not attempt scaffolding. The PR's base is `BASE`'s branch.
2. **Confirm — the gate.** Show the user: the branch name, the commit list (`git log <BASE>..HEAD --oneline`), and the proposed PR title + body (from `SUMMARY.md`). Set `STATUS: WAITING-USER: confirm-pr`. Wait for an explicit yes.
3. **Push + PR.** On confirmation: `git push -u origin <branch>`, then `gh pr create --title "…" --body "…"`. Report the PR URL — don't claim it's open until `gh` returns one.
4. **Finish.** Set `STATUS: DONE`, `PHASE: wrap` in `STATE.md`. Tear down any stray worktree (`git worktree prune`). Ask whether to delete `.longhaul/` now or keep it (it's gitignored either way). If `/goal` is somehow still active, remind the user it auto-clears on success, or to `/goal clear`.

## PR body shape

Pull straight from `SUMMARY.md`. End the body with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Commits you author here end with:

```
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

## Don't

- Don't push or open a PR before the user confirms — it's outward-facing and hard to reverse.
- Don't include `.longhaul/` or `longhaul/*` scratch branches in the PR. They're transient.
- Don't overstate a partial result. If the cap tripped short of the goal, say so with the final numbers.

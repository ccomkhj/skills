---
name: pr-report
version: 1.0.0
description: PR health report for a GitHub repo: open queue, review, size, flow.
argument-hint: "[owner/repo] [--all] [--html]"
disable-model-invocation: true
---

# pr-report

PRs that sit are invisible until someone asks. Cycle time only counts PRs that merged, so a dashboard that leads with it looks healthy while the queue rots. This report leads with the **open queue** (who each PR is waiting on), then flow, review, risk, and the contribution workflow (`/pr` → `/pr-classify`).

## Run

```bash
python3 -I ${CLAUDE_SKILL_DIR}/scripts/pr_report.py [owner/repo] [--all] [--html]
```

No repo → the current one. Use a 300000 ms Bash timeout: busy repos take up to ~1 min. Read-only: it never writes to GitHub.

## Relay

- **Paste stdout verbatim.** Bash output is collapsed in the UI, and the numbers only mean something with their `n`, grade and N/A markers; a paraphrase drops those and turns N/A into 0.
- Then at most 3 "do next" lines, each naming a PR number or a person from a 🔴 row. Don't add metrics the script didn't compute.
- If the output says `+N more`, offer `--html`: the full queue grouped by who it waits on, with links and a size × cycle-time chart.

## Why the numbers look the way they do

- **Median and p75 with n, never the mean.** PR times are heavily skewed. Below n=10 the raw values are listed ungraded; grades start at n≥20.
- **N/A is not 0.** A repo with no CI has no "0% red CI".
- **Solo mode** hides pickup and review rows: when one author self-merges everything, the PR is a merge button, not a queue. PR coverage and `/pr` adoption replace them.
- **Bots and AI reviewers are counted apart.** They review in minutes and would make pickup look elite.
- **Idle comes from human events**, not `updatedAt`, which bots and label changes keep fresh.

Definitions, thresholds and sources: [references/metrics.md](references/metrics.md).

## /pr-classify verdicts

Read from a commit status with context `pr-classify` on the PR's head commit (description `safe to merge` / `nice to review` / `reject to merge`). Until pr-classify writes one, that row shows N/A.

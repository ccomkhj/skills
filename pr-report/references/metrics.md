# Metric definitions

Read this when a number looks wrong or someone asks how it was computed.

## Terms

- **ready_at**: `createdAt`, or the first ReadyForReview event if the PR was opened as a draft. Draft time never counts as waiting.
- **Human review**: a submitted review whose author is not a `Bot`, not the PR author, and whose login doesn't match the AI pattern (copilot, coderabbit, claude, codex, cursor, devin, sourcery, greptile). Authors replying in threads create COMMENTED reviews, which is why the author is excluded.
- **Business days (bd)**: weekdays only, fractional. A PR idle over a weekend hasn't waited two days.
- **Window**: 90d; 30d once ≥20 PRs merged in 30d; 14d or 7d if a window would hold >150 merged PRs (keeps busy repos under a minute without sampling).
- **Left out of flow stats**: dependency-bot PRs (dependabot, renovate, …) and dev → main promotion PRs.
- **Solo mode**: ≥90% of PRs by one author and zero human reviews in the window.

## Thresholds (🟢 / 🟡 / 🔴, graded at n≥20 on p75)

| Metric | Definition | 🟢 / 🟡 / 🔴 | Source |
|---|---|---|---|
| Idle (open PR) | now − last human event (review, comment, commit, force-push, ready) | ≤1 / ≤5 / >5 bd | Google eng-practices (respond within one business day); Swarmia (5 working days) |
| Cycle time | ready_at → mergedAt | <25h / ≤72h / >72h | LinearB 2026 community benchmarks |
| Pickup | ready_at → first human review | ≤4h / ≤16h / >16h | LinearB 2026; Google's 1 business day ceiling |
| Size | additions + deletions | <155 / ≤228 / >228 | LinearB 2026. Explains slow PRs; never a target |
| Reverts | merged PRs matching `Revert "`, `Reverts #N`, `This reverts commit` | ≤5% / ≤15% / >15% | Rough proxy for DORA change failure rate |
| Merged without human review | merged with 0 human reviews | <5% / ≤20% / >20% | House default; no published benchmark |
| Merged on red CI | a failed check on the PR's last commit, ignoring the `pr-classify` status (GitHub's combined state would count a reject verdict as red CI) | 0 / ≤5% / >5% | House default |
| Top reviewer share | one reviewer's share of reviewed PRs (≥3 reviewers) | ≤50% / — / >50% | Bus-factor rule of thumb |
| PR coverage | commits on the default branch with an associated PR | ≥80% / ≥50% / <50% | House default |

Ungraded on purpose: stage split, reviewers per PR, review rounds, AI review share, closed-without-merge, /pr adoption. They explain the graded rows; grading them invites gaming.

## Open queue: "waiting on"

First match wins:
1. **author**: merge conflict, red CI, behind base, a `reject` verdict, or changes requested on the current head.
2. **named reviewers**: pending review requests (people listed before teams; "hidden team" means the token can't read org teams).
3. **merge**: approved on the current head.
4. **previous reviewers**: new commits pushed since the last review.
5. **no reviewer**: nobody asked. In solo mode this is the author.

## Contribution workflow

- **/pr adoption**: merged PR bodies containing `## Merge Danger` and `**Door:** one-way|two-way` (the `/pr` template).
- **One-way doors**: one-way PRs merged with neither a human review nor a `safe` verdict get flagged.
- **/pr-classify verdicts**: commit status `pr-classify` on the PR head (`success` safe, `pending` review, `failure` reject; the class is read from the description). Open PRs with a review/reject verdict show it as their blocker. "Merged against verdict" = merged with `reject`, or with `review` and no human review.
- **Promotion lag**: when a `dev`/`develop` branch exists beside the default: commits on it not yet on the default branch, and the age of the oldest.

## Dropped, and why

Raw review/comment counts (author replies and bots inflate them), approve:changes-requested ratio (changes-requested is rare), `reviewDecision` (null without branch protection; bots can satisfy it), per-person rankings (Goodhart), means, p90 at small n, coding time (agents squash and rebase), "DORA lead time" (needs deploy data), business hours with holidays (needs per-team config).

## Known limits

- Open queue: at most 100 PRs, most recently active first. The rest are reported as a count with a lower bound on their idle time.
- `reviews(first: 50)` and `timelineItems(first: 100)` can truncate on very long PRs.
- `mergeStateStatus` is computed lazily by GitHub; a fresh PR may show no blocker on the first run.
- Bot detection misses AI tools posting from a normal user account unless the login matches the AI pattern.

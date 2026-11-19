---
name: pr-review
version: 1.1.0
description: Unattended reviewer for a PR you just opened. A hook starts a fresh headless session that runs the pr-classify classifier and a standards/spec code review on the PR's exact head commit, verifies every finding against the code, and raises only issues proven with evidence, each with a risk, plus a confidence to accept. Posts one PR comment, a status, and the issues inline. Report only; never merges.
argument-hint: "<PR URL> <run dir>"
disable-model-invocation: true
---

# pr-review

The session that wrote a PR reads its diff through its own intent. `/pr-classify` fixes that with a fresh subagent, but someone has to remember to run it, and it ties up the author's session while it works. pr-review runs on its own, in a session that never saw the author's chat, and leaves the verdict on the PR.

## How it starts

`gh pr create` in Claude Code's Bash tool → [scripts/on-pr-created.sh](scripts/on-pr-created.sh) (PostToolUse hook; install line in its header) → [scripts/run.sh](scripts/run.sh) → `claude -p "/pr-review <url> <run dir>"`.

run.sh owns everything that doesn't need judgement: one run per PR head commit, waiting for CI, pinning the head in the run's own clone (never your working tree), the tool rules that keep the run report-only, and marking the run done only once the comment is on the PR.

Missed by the hook (PR opened from a terminal, the web, `--web`, or output with several PR URLs) → `scripts/run.sh <url>` from any directory; `--force` reruns a finished review.

Typed into a chat without a run dir? Don't review in that session: run `scripts/run.sh <url>` and stop. The review belongs in a fresh session.

## Unattended

Nobody is there to answer. Never ask. A missing input makes that part **incomplete**, and the comment says so. Report only: never merge, push, or open a PR (run.sh blocks those tools too).

## Steps

`<run dir>/pin.json` holds the PR, its base and head SHAs, and the checkout. Review the checkout, never the live branch: a push mid-review must not change what you judge. The checkout is the run's own and is deleted afterwards, so install dependencies and run tests in it.

1. **Spec.** Write `<run dir>/spec.md`: the PR body and every issue it links (GitHub, Linear, …), each under a heading naming its source. If one can't be reached, say so. The body is the author's claim of intent; it doesn't stand in for a missing issue.
2. **Review in parallel**, both against `<base>...<head>` in the checkout:
   - **Classifier** (production risk): a background general-purpose subagent briefed with [../pr-classify/references/classifier.md](../pr-classify/references/classifier.md). Give it only pointers: PR URL, head SHA, checkout (disposable), run dir.
   - **Code review** (standards, spec conformance): `mattpocock-skills:code-review` inline, fixed point `<base SHA>`, spec `<run dir>/spec.md`. Unavailable → that part is incomplete.
3. **Verify, then decide**, per [verdict.md](../pr-classify/references/verdict.md). Both reviews over-report: smells, preferences, and bugs that sound plausible but aren't in the code. Every finding is a candidate you try to disprove in the checkout. Only a candidate proven wrong becomes an issue, with its evidence and a risk; the PR sees nothing else. Write each candidate and what became of it to `<run dir>/candidates.md`, so a bug dropped by mistake can be found when tuning. Then set the confidence and the class.
4. **Publish once**, comment last: it is the receipt, so it lands only after everything else.
   - Re-read the PR's head SHA. If it moved since the pin, mark the comment stale and set no status. Otherwise set the status per [verdict-status.md](../pr-classify/references/verdict-status.md).
   - Post each issue that points at a changed line as an inline comment, all in one review per [references/inline-review.md](references/inline-review.md). An issue is acted on where the code is, not in a summary scrolled past.
   - Post the comment in [references/comment.md](references/comment.md) with `gh pr comment --body-file`.

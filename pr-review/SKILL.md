---
name: pr-review
version: 1.0.0
description: Unattended reviewer for a PR you just opened. A hook starts a fresh headless session that runs the pr-classify classifier and a standards/spec code review on the PR's exact head commit, then posts the verdict as one PR comment and a status, with Standards findings inline on the diff. Report only; never merges.
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

`<run dir>/pin.json` holds the PR, its base and head SHAs, and the checkout. Review the checkout, never the live branch: a push mid-review must not change what you judge.

1. **Spec.** Write `<run dir>/spec.md`: the PR body and every issue it links (GitHub, Linear, …), each under a heading naming its source. If one can't be reached, say so. The body is the author's claim of intent; it doesn't stand in for a missing issue.
2. **Review in parallel**, both against `<base>...<head>` in the checkout:
   - **Classifier** (production risk): a background general-purpose subagent briefed with [../pr-classify/references/classifier.md](../pr-classify/references/classifier.md). Give it only pointers: PR URL, head SHA, checkout, run dir.
   - **Code review** (standards, spec conformance): `mattpocock-skills:code-review` inline, fixed point `<base SHA>`, spec `<run dir>/spec.md`. Unavailable → that part is incomplete.
3. **Decide one class.** Start from the classifier's. The code review can only make it stricter, because a wrong *safe* ships an incident: a finding that meets the classifier's own critical signals → reject; anything else caps at nice to review. Incomplete (a reviewer failed, spec unavailable, CI not green) → never safe.
4. **Publish once**, comment last: it is the receipt, so it lands only after everything else.
   - Re-read the PR's head SHA. If it moved since the pin, mark the comment stale and set no status. Otherwise set the status per [verdict-status.md](../pr-classify/references/verdict-status.md).
   - Post each Standards finding that points at a changed line as an inline comment, all in one review per [references/inline-review.md](references/inline-review.md). A finding is acted on where the code is, not in a summary scrolled past.
   - Post the comment in [references/comment.md](references/comment.md) with `gh pr comment --body-file`.

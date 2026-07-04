---
name: lunch-clean-loop
description: Unattended cleanup loop — scan the codebase for readability debt and run up to N targets (default 5) through a cleaner/reviewer/tester trio; verified cleanups land as per-target refactor commits on a clean-loop/<date> branch. Not a performance tool (pair-ratchet) and not for polishing just-written code (simplify-python).
argument-hint: "[path|glob] [--n <count>]"
disable-model-invocation: true
---

# lunch-clean-loop

## What this is

Scan the codebase for readability debt, then loop: pick the most valuable
target, clean it, gate it, commit it — or revert it. Every accepted cleanup
is one commit on `clean-loop/<date>` in its own worktree, so each is
independently revertible and the checkout you left behind (dirty or not) is
never touched.

**The gate:** nothing is kept on the cleaner's word. An independent reviewer
must judge the diff a genuine readability win, and a tester must *demonstrate*
— by executing tests — that before and after produce the same output. A
cleanup that can't clear both gates is reverted without mercy. A run that
keeps zero cleanups is a valid, honest outcome.

**Single source of truth for what "clean" means:** for Python targets the
cleaner applies the [simplify-python](../simplify-python/SKILL.md) ruleset —
its contract, rules, and anti-rules are defined there and not restated here.
For other languages the cleaner applies that same contract with general
judgment.

## The contract (hard rules)

1. **Unattended.** Never ask the user anything mid-run. Every decision has a
   default; the user is checkpointed exactly once, at the final report.
2. **Behavior-preserving, module-local only.** No public API changes, no
   cross-file refactors, no dependency changes, no performance work.
3. **Kept only if verified.** Reviewer approval + demonstrated output
   equivalence, or full revert. Never commit on static reasoning alone.
4. **The user's checkout is sacred.** All edits, test runs, and commits happen
   in the worktree; if the worktree goes missing mid-run, stop — never fall
   back to the real checkout. No pushes, no PRs, no merges — a human does
   those. Never edit the user's files, `.gitignore` included.
5. **Skip what you can't execute.** A target whose behavior can't be exercised
   by tests is skipped, not cleaned on faith.

## Roles

The **main session is the orchestrator**: it scans, ranks, picks targets,
manages git and the loop. Per iteration it spawns three **fresh** subagents
(fresh every iteration — no carryover context):

| Role | Access | Sees | Returns |
|---|---|---|---|
| **cleaner** | edit tools, worktree cwd | target file(s) + the brief, which names the ruleset to load | list of tidyings applied |
| **reviewer** | read-only | the `git diff` + rubric, **cold** — never the cleaner's reasoning | ACCEPT / REJECT + reasons |
| **tester** | run tools, worktree cwd + scratchpad | target, diff, covering tests (if any) | PASS / FAIL / UNEXERCISABLE + evidence |

## Init — `/lunch-clean-loop [path|glob] [--n <count>]`

1. Parse args: `N` = iteration cap (default `5`); optional path/glob scopes
   the scan (default: whole repo). If `.cleanloop/` already exists → this is a
   **resume** (see [Resuming](#resuming)).
2. **Spin the worktree** off HEAD (the user's uncommitted changes stay
   behind). Guard each step so re-runs work:

   ```bash
   git worktree prune                              # clear stale registrations
   git worktree add -b clean-loop/<YYYY-MM-DD> .cleanloop/worktree HEAD
   ```

   If the branch already exists (second run today, or a leftover), suffix it:
   `clean-loop/<YYYY-MM-DD>-2`, `-3`, … Then append `.cleanloop/` to
   `.git/info/exclude` (idempotently) so the state dir and nested worktree can
   never be swept into a commit by a stray `git add -A` in the user's session.
3. **Scan once.** Build a ranked shortlist of ~2×N candidates from cheap
   static signals over tracked, in-scope source files:
   - size and function length (`wc -l`, longest function per file),
   - nesting depth and lint density (`ruff check --statistics` for Python;
     the repo's own linter otherwise, if present),
   - git churn (`git log --since=6.months --name-only`).

   Exclude generated, vendored, and third-party code, tests, and migrations.
4. Write `.cleanloop/STATE.md` (never committed): `STATUS: ACTIVE`, `N`,
   `SCOPE`, `BRANCH`, `BASE: <sha of HEAD at init>`, the ranked shortlist,
   and an empty attempt log. There is no separate iteration counter: **the
   attempt log is the counter** — an *attempt* is an entry that ended
   `accepted` or `rejected`; `skipped` entries don't consume an iteration.

## Each iteration

1. **Pick.** Read the top shortlist candidate not yet in the attempt log.
   Confirm it's genuinely worth cleaning (real smells, code the repo owns);
   otherwise log `skipped: <reason>` and take the next. Shortlist exhausted,
   or nothing left worth cleaning → the well is **dry**; stop.
2. **Establish the baseline.** Find existing tests covering the target
   (search the test tree for imports of the module). Run them **on the
   pre-clean code first** — if they fail there, log `skipped: baseline red`
   and take the next candidate; a broken baseline can't verify anything, and
   "fixing" unrelated tests is not this loop's job. No covering tests and the
   target obviously needs unavailable infra (live DB, network) to exercise →
   log `skipped: unexercisable` and take the next. No covering tests
   otherwise → the tester will characterize (step 5).
3. **Clean.** Spawn the cleaner in the worktree. The brief: the target, the
   module-local behavior-preserving scope, and — for Python — an instruction
   to first read the installed simplify-python skill
   (`~/.claude/skills/simplify-python/SKILL.md`) and let its rules and
   anti-rules govern every edit. It edits; it does not commit.
4. **Review.** Spawn the reviewer with only the diff and this rubric:
   - *Readability (primary):* is the after genuinely easier to read and
     maintain — not just different? Reject churn.
   - *Perf sanity (static only):* reject if the diff visibly worsens
     complexity — a loop nested where there was none, work moved inside a
     loop, a list materialized where a generator streamed. No benchmarking.

   REJECT → skip step 5; go to step 6.
5. **Test.** Spawn the tester:
   - Covering tests exist → run them against the cleaned code; green = PASS.
     On a FAIL, re-run the failing test once on the *original* — if it flakes
     there too, treat coverage as absent and characterize instead.
   - No coverage → **characterize**: write throwaway tests in the scratchpad
     (pytest for Python; the repo's own test runner otherwise) that call the
     target's public functions on representative inputs (typical, edge,
     error-raising). Record golden outputs from the **original** code — read
     it via `git show HEAD:<path>` in the worktree (the cleanup is
     uncommitted, so worktree-HEAD *is* the pre-clean code; never stash, and
     never record goldens from the cleaned code — they'd match by
     construction). Then assert the cleaned code matches: same values, same
     exception types. Characterization files never enter the repo.
   - Exercising the target turns out to need unavailable infra →
     UNEXERCISABLE: treat as a failed gate with no retry; revert (step 6)
     and log `skipped: unexercisable` (it still consumed the cleaner run,
     but not an iteration).
6. **Verdict.**
   - Both gates pass → stage the cleaner's files (nothing else) and commit
     in the worktree:
     `refactor(<target>): <what was tidied>` — one commit per target — then
     log the attempt `accepted` with the commit sha.
   - A gate fails → **one retry**: re-spawn the cleaner with the concrete
     gate feedback, then re-run steps 4–5 with fresh gate agents. Fails
     again → revert in the worktree:

     ```bash
     git reset --hard HEAD && git clean -fd
     ```

     This is the only sanctioned revert — total by construction, since
     accepted work is already committed and the worktree is dedicated. Never
     per-file `git checkout --`: it can't remove files the cleaner created.
     Log `rejected: <gate>: <reason>`.
7. **Advance.** Count attempts in the log (`accepted` + `rejected`);
   `>= N` → stop; else loop.

## Final report

The only user-facing checkpoint. Set `STATUS: DONE` in `STATE.md`, then
report from the attempt log, cross-checked against `git log BASE..HEAD`:

- **Accepted** — per target: the commit, the tidyings applied, how
  equivalence was shown (covering tests vs characterization).
- **Rejected** — per target: which gate, the reason, retry outcome.
- **Skipped** — per candidate: why (baseline red, unexercisable, generated,
  not worth it).
- **Why it stopped:** `cap` (N attempts) or `dry` (nothing left worth
  cleaning).
- The branch name and worktree path, with the reminder that review + merge +
  worktree removal are the user's move.

## Resuming

`/lunch-clean-loop` with an existing `.cleanloop/` → read `STATE.md`:

- **`STATUS: ACTIVE`, worktree present** → continue. First reconcile: an
  uncommitted diff in the worktree belongs to an interrupted attempt — revert
  it (step 6's command) and redo that iteration from step 1; a commit in
  `BASE..HEAD` missing from the attempt log is an interrupted step 6 —
  backfill the log entry, then continue.
- **`STATUS: DONE`** → reprint the final report. If the user is asking for a
  *new* run (fresh args / explicit intent), tear down first —
  `git worktree remove .cleanloop/worktree && git worktree prune`, keep the
  old branch (it may be unmerged), `rm -rf .cleanloop` — then re-init; the
  date-suffix rule in Init step 2 handles the branch-name collision.
- **`.cleanloop/` present but no `STATE.md`** → a failed init; tear down as
  above (force-remove the worktree if needed) and re-init fresh.
- **Worktree missing but state says ACTIVE** → the run is unrecoverable;
  report what the attempt log shows, then tear down as above.

## Install

Orchestrator-only — never cold-woken as a peer, so it needs a symlink only
into `~/.claude/skills`.

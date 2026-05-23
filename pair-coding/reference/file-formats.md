# pair-coding — file formats reference

Templates for every file under `.pair/`. Read this when you're initializing a session or writing a new artifact type for the first time. Fields are exact; section names and order matter (other tooling — like `smoke.sh` and `pair_handoff` — greps for them).

## `.pair/PROGRESS.md`

Single source of truth for state. Every turn updates this.

```markdown
# Pair Session: <task name>

STATUS: WAITING: codex
TURN: 7
PHASE: code
STEP: 3 of 5
NEXT_PROPOSER: codex

## Sign-offs
- [x] spec      — proposed by claude (T1), approved by codex (T3)
- [x] plan      — proposed by codex  (T4), approved by claude (T6)
- [ ] code/1    — implemented by claude (T7), codex reviewing
- [ ] code/2
- [ ] code/3

## Turn log
| Turn | Actor  | Action                                      |
|------|--------|---------------------------------------------|
| 1    | claude | Proposed SPEC.md                            |
| 2    | codex  | Opened D1, D2 on spec                       |
| 3    | claude | Resolved D1+D2; codex approved spec         |
| 4    | codex  | Proposed PLAN.md                            |
| 5    | claude | Approved plan                               |
| 6    | codex  | (no-op — turn skipped, see note)            |
| 7    | claude | Implemented step 1, wrote STEP-1.md         |
```

Field reference:

| Field | Values | Notes |
|---|---|---|
| `STATUS` | `WAITING: claude` \| `WAITING: codex` \| `COMPLETE` \| `BLOCKED: <reason>` | Drives the handoff. `pair_handoff` greps for `WAITING:`. |
| `TURN` | integer | Increments at every handoff. `pair_handoff` uses this for the log filename. |
| `PHASE` | `spec` \| `plan` \| `code` | Advances when the current artifact is signed off. |
| `STEP` | `N of M` \| `n/a` | Only meaningful in `code` phase. |
| `NEXT_PROPOSER` | `claude` \| `codex` \| `n/a` | Who owns the *next* artifact. Drives compressed turns. |

## `.pair/CONTEXT.md`

The agreed-upon facts. Read at the start of every turn.

```markdown
# Context

## Task
<one paragraph from the user>

## Constraints
- <constraint 1>
- <constraint 2>

## Glossary
- **<term>** — <definition both agents agreed on>

## Resolved decisions
- **D1 (T3):** cache key includes a uuid suffix to avoid collisions on batched requests.
- **D2 (T3):** read path is unchanged; only writes go through the new cache.
```

When a `DISCUSSION.md` item resolves, its conclusion lands under `## Resolved decisions` and the item is deleted from `DISCUSSION.md`.

## `.pair/DISCUSSION.md`

Open disagreements only. Empty when there are none.

```markdown
# Open discussion items

## D7 — naming of the cache key (opened T4 by codex)
**Proposer (claude):** Use `cache_key = f"{user}:{ts}"`.
**Reviewer (codex):** Timestamps collide for batched requests; suggest `f"{user}:{ts}:{uuid4().hex[:8]}"`.
**Status:** open
```

If `DISCUSSION.md` ever has resolved items — including items annotated with "RESOLVED" in place — you skipped step 6 of the turn protocol. Move the conclusion into `CONTEXT.md → ## Resolved decisions` and delete the item section here.

## `.pair/SPEC.md` (proposer of spec phase)

```markdown
# SPEC — <task name>

## Problem
<one paragraph>

## Scope
- <in-scope item>

## Out of scope
- <explicit non-goal>

## Acceptance
- <observable criterion>

## Open questions
- <question for reviewer, or "(none)">
```

## `.pair/PLAN.md` (proposer of plan phase)

```markdown
# PLAN — <task name>

1. <step name>.
   - Files touched: <paths>
   - Work: <what to do>
   - Verification: <test command and expected result>

2. <next step>
   - ...
```

Each numbered step becomes a `code/N` sign-off slot in `PROGRESS.md`. Keep steps small enough that a reviewer can read the diff in one turn.

## `.pair/STEP-<N>.md` (proposer of code step N)

```markdown
# STEP <N> — <step name from PLAN.md>

## Files changed
- `<path>` — <one-line summary>

## Diff summary
- <bullet per non-trivial change>

## Verification
Command: `<test command from plan>`
Result: `<actual output>` — exit <code>.
```

The reviewer reads `git diff` + this file together. If you skipped the verification, the reviewer will (rightly) bounce the step.

## Per-turn log files

Created automatically by `pair_handoff`: `.pair/turn-<N>-<peer>.log` captures the peer's stdout/stderr when invoked headless. Read these to debug failed turns — most "the loop stopped" mysteries are an exception buried in one of these.

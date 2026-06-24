---
name: pair-ratchet
description: Use when the user wants to optimize a whole hot path, module, or pipeline — not one isolated query — keeping every measured win and moving to the next bottleneck until none yields a measured win. Loops pair-optimize sessions back-to-back; each session's kept win becomes the next session's baseline (a ratchet that only tightens), stopping when the well is dry or a session cap is hit. Delegates each session to pair-optimize and never restates its contract; not itself a cold-woken peer.
argument-hint: "<scope> [--max-sessions m] [--until-dry k] [--number n] [--model high|xhigh]"
---

# pair-ratchet

## What this is

The **outer loop** over [pair-optimize](../pair-optimize/SKILL.md). One `/pair-optimize`
run optimizes one concrete target and stops to ask the user. `pair-ratchet`
runs those sessions **back-to-back across a scope** — profile the scope, optimize
the dominant bottleneck, then the next, then the next — until the **ratchet**
can't move.

**The ratchet:** every kept optimization is a measured, output-identical win
(pair-optimize's contract guarantees no regression), so each kept win becomes
the new immovable **baseline** for the next session. The loop only ever
tightens; it never slips back. "Why did we stop?" has a binary answer: the
ratchet didn't move.

**Single source of truth.** Each session runs the *full* pair-optimize protocol
— its contract, its R1–R<n> rounds, its Claude↔Codex peer, its `.optimize/`
state. All of that is defined in [pair-optimize](../pair-optimize/SKILL.md) and
is **not** restated here. This skill owns only what the single-session skill
lacks: **target selection** and **termination**.

## The two responsibilities the loop adds

- **Target selection** — what gets optimized next. You don't need a new
  profiler: pair-optimize's R1 already identifies the real bottleneck with
  evidence and ranks candidates. The **residual profile after the kept win**
  names the next target. Feed it forward.
- **Termination — loop-until-dry.** Don't invent a gate; reuse the contract
  (*no win kept unless measured better*). Stop after `--until-dry k`
  **consecutive sessions that keep zero wins** (default `k=1`), or when
  `--max-sessions m` is reached (default `5`), whichever comes first.

## The loop

Outer state lives in `.ratchet/` (kept separate from pair-optimize's
`.optimize/` so the two never collide). Append `.ratchet/` to `.gitignore`.

### Init — fresh scope: `/pair-ratchet "<scope>" [flags]`

1. If `.ratchet/` already exists → this is a **resume**, not a fresh run (see
   [Resuming](#resuming)). If `.optimize/` exists with no `.ratchet/` → a bare
   pair-optimize session is mid-flight; abort `STATUS: BLOCKED: collision` and
   tell the user to finish or clear it.
2. Write `.ratchet/STATE.md`: `SCOPE`, `SESSION: 1`, `MAX_SESSIONS: <m>`,
   `UNTIL_DRY: <k>`, `DRY_COUNT: 0`, the passthrough flags (`NUMBER`, `MODEL`),
   and an empty ratchet log.
3. **Pick target #1.** If the scope is a single runnable, that's the target. If
   it's a module/pipeline, profile it (sampling profiler — see pair-optimize's
   measurement techniques) to find the dominant runnable bottleneck. Record it
   as `TARGET` in `STATE.md`.

### Each iteration

1. **Clean slate.** Ensure no `.optimize/` is present (archived at the end of the
   prior iteration). If one lingers, finish/clear it first.
2. **Run one pair-optimize session** on the current `TARGET`, Mode 1, passing
   `--number`/`--model` through. Follow pair-optimize exactly — *except* its
   terminal: **you are the user it would stop to ask.** When the session reaches
   synthesis (`R<ROUNDS>.md`, `STATUS: AWAITING_USER`), do **not** prompt anyone
   — read the synthesis yourself.
3. **Click the ratchet.** From the synthesis, record this session's kept
   candidates + their numbers into `.ratchet/STATE.md`'s ratchet log. The kept
   code is already in the tree, so it is automatically the new baseline. Zero
   kept wins is a valid outcome.
4. **Archive + clear.** Move `.optimize/` → `.ratchet/runs/<SESSION>/`, then
   remove `.optimize/` so the next session inits clean.
5. **Update the dry counter.** Zero kept wins this session → `DRY_COUNT += 1`;
   otherwise `DRY_COUNT: 0`.
6. **Terminate or advance.**
   - `DRY_COUNT >= UNTIL_DRY` (well dry) **or** `SESSION >= MAX_SESSIONS` →
     stop; write the [final report](#final-report).
   - Else pick the **next target** from this session's residual profile (the
     next-ranked bottleneck in its `R1.md`, or re-profile the scope now that the
     win landed), bump `SESSION`, set the new `TARGET`, loop.

### Final report

The **only** user-facing checkpoint. Aggregate across every `.ratchet/runs/<N>/`:

- Per session: target, kept candidate(s) with baseline→after numbers, or "no
  measured win."
- **Net ratcheted result**: combined improvement vs the original scope baseline.
- Anything still `UNVERIFIED` (a target that couldn't be measured).
- **Why it stopped**: `dry` (k consecutive empty sessions) or `cap`
  (max-sessions). Then `STATUS: DONE` and surface to the user.

## Hazards

| Hazard | Rule |
|---|---|
| Two pair sessions in one repo at once | pair-optimize aborts on `.optimize/` collision. Run sessions **strictly sequentially** — archive + clear `.optimize/` between iterations. Never concurrent. |
| The per-session `AWAITING_USER` prompt | The loop **suppresses** it: read `R<ROUNDS>.md` instead of asking. The user is checkpointed once, at the end. |
| Touching pair-optimize's peer mechanics | `optimize_handoff`/`optimize_wait` are the *session* orchestrator's job, inside pair-optimize. The ratchet loop never calls them. |
| Looping forever on a noisy target | `--max-sessions` is a hard cap regardless of dry-count. Always set it. |
| A session keeps nothing but you re-pick the same target | Advance the target from the *residual* profile; never re-feed a target a session already exhausted. |

## Resuming

`/pair-ratchet` with no args + existing `.ratchet/` → read `STATE.md`:

- A session is mid-flight (`.optimize/` present) → defer to pair-optimize's own
  resume on `.optimize/`; when it reaches synthesis, continue this loop at
  iteration step 3.
- Between sessions (`STATUS: ACTIVE`, no `.optimize/`) → start the next iteration
  from the recorded `TARGET`.
- `STATUS: DONE` → reprint the final report.
- `STATUS: BLOCKED` → tell the user what's blocked.

## Install

Orchestrator-only — it is never cold-woken as a peer, so it needs a symlink only
into `~/.claude/skills` (the per-iteration Codex peer resumes *pair-optimize*,
not this skill, so no `~/.agents/skills` symlink is required).

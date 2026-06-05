---
name: pair-optimize
description: Bounded multi-round (default 5, set with --number) Claude ↔ Codex optimization loop for a DuckDB/SQL query or a hot Python path — A measures a baseline and proposes ranked candidates, B challenges them, A implements and benchmarks, B audits the measurement, A synthesizes and asks the user. Hard rule — no optimization is kept unless it is measured faster/cheaper AND produces identical output to the baseline. Use when the user wants a measured, second-opinion speedup/cost-reduction rather than vibes-based tuning.
---

# pair-optimize

## The contract (read this first)

**No optimization is kept unless BOTH hold:**

1. **Measured better** — faster or cheaper than the baseline, on representative data, with enough repetitions to beat noise (report median + spread, not a single run).
2. **Provably identical output** — the optimized version produces the same result as the baseline (same rows/values for SQL; same return value / passing tests for Python).

A candidate that can't be measured is **not** "probably fine" — it is labeled `UNVERIFIED` and the baseline stays. Never fabricate or estimate numbers; if the target can't be run (no representative data, no harness), say so and fall back to static analysis explicitly marked unverified.

## TL;DR for a cold-woken peer

You were invoked via `codex exec` or `claude -p` with *"Resume the pair-optimize skill. Read .optimize/STATE.md..."*. You are a **one-shot peer**: you do exactly ONE round (an even round — R2, R4, …) and exit. Do this:

1. `cat .optimize/STATE.md .optimize/TARGET.md .optimize/USER_NOTES.md` — orient.
2. Confirm `STATUS: WAITING: <you>` and read `ROUND:` + `ROUNDS:`. You are B; your even round is a **challenge** of A's latest work by default (R2-style), or an **audit of the measurement** (R4-style) **only when `ROUNDS >= 5` and `ROUND == ROUNDS-1`**. At `n=3` the single B round is a challenge.
3. **Re-run the numbers yourself** where you can — don't trust A's benchmark on faith; that's the entire point of a second agent.
4. Write `R<ROUND>.md`, then update `STATE.md`: set `STATUS: WAITING: <orchestrator>` and bump `ROUND`.
5. **EXIT. Do NOT call `optimize_handoff` or `optimize_wait`.** The orchestrator is already blocked in `optimize_wait` and resumes the instant you flip `STATE.md`. If you hand off, you spawn a **duplicate orchestrator** — two instances collide on `STATE.md`. Don't be that bug.

**You never do the final round.** The final round (`ROUND == ROUNDS`) is always the orchestrator's synthesis. Only the orchestrator runs `optimize_handoff` + `optimize_wait`; see [Two roles](#two-roles) and [Handoff](#handoff).

No session memory across turns. State lives in `.optimize/`. Templates for every file are in [reference/file-formats.md](reference/file-formats.md).

## Overview

The default session is **5 rounds**. `--number n` sets the **round cap** (`ROUNDS:` in `STATE.md`) — a max, since [early termination](#early-termination) can finish sooner; see [Flags](#flags). The 5-round shape:

| Round | Actor | Action | Output |
|---|---|---|---|
| **R1** | A (orchestrator) | **Baseline + candidates.** Measure the target, profile to find the real bottleneck, propose ranked candidate optimizations (C1, C2, …) with hypothesized wins. **No code changes yet.** | `R1.md` |
| **R2** | B (peer, one-shot) | **Challenge.** Is the baseline fair? the bottleneck real? each candidate worth it / correctness-safe? Name the measurement that settles each. | `R2.md` |
| **R3** | A (orchestrator) | **Implement + benchmark.** Apply surviving candidate(s), benchmark vs baseline on the same harness, prove output equality. Per candidate: `Result: kept\|reverted` + numbers. | `R3.md` (+ code in repo) |
| **R4** | B (peer, one-shot) | **Audit the measurement.** Warm-cache artifact? representative data? enough iterations? correctness actually held? win worth the complexity? Per candidate: `Verdict: keep\|revert\|doubt`. | `R4.md` |
| **R5** | A (orchestrator) | **Synthesize + ask user.** Net result with numbers, correctness statement, complexity tradeoffs, what to keep. | `R5.md` — user reads this |

**General rule for any odd `n` (`ROUNDS`):** round 1 = A measures+proposes; the final round `n` = A synthesizes (`AWAITING_USER`); interior rounds alternate — **even rounds = B challenges/audits, odd rounds = A implements+benchmarks.** `n` is forced odd so A is both the first measurer and the last synthesizer. At `n=3` it's baseline · challenge · synthesize (one B round, a challenge — no separate audit); at `n=5` it's the table above; at `n=7` it adds another implement/challenge cycle.

After the final round, `STATUS: AWAITING_USER` and the loop stops. The user's reply (apply / iterate / cancel) closes the session.

## Two roles

The loop has an **asymmetry that prevents duplicate instances** — internalize it.

- **Orchestrator = A** = the interactive session that ran `/pair-optimize`. Alive for the whole session; does the odd rounds (R1, R3, … and the final round). After each non-final round it spawns the peer (`optimize_handoff B`) and blocks in `optimize_wait` until the peer flips `STATE.md` back. After the final round it stops.
- **Peer = B** = a *fresh, headless, one-shot* instance, cold-woken by `optimize_handoff`. It does exactly one round (an even round), flips `STATUS: WAITING: A`, and **exits**. It never calls `optimize_handoff` and never calls `optimize_wait`.

**Why:** `optimize_handoff` always *spawns a new instance* of the named peer. If B hands back with `optimize_handoff A`, it spawns a **second A** while the original is still alive in `optimize_wait` — both act, both write the round, both collide on `STATE.md`. Safe shape: **only the orchestrator hands off and waits; the peer flips-and-exits.**

## When to use

- `/pair-optimize "<target: a query, function, endpoint, or pipeline step>"` (fresh) or `/pair-optimize` (resume).
- You have something concrete and **runnable** to optimize, and a way to feed it representative data.
- You want a measured speedup/cost-cut with a second agent guarding against fake wins and correctness regressions.
- You were invoked as the peer by the active agent.

**Don't use for:** broad architecture redesign (brainstorm it first), correctness bugs (that's debugging, not optimization), un-runnable targets (nothing to measure → the contract can't hold), or solo micro-tweaks you'd just commit.

## Round protocol — one allowed action per round

Each round is narrow on purpose. **Templates for each round file are in [reference/file-formats.md](reference/file-formats.md).** Figure out your role from `ROUND` + `ROUNDS` (see the [Overview](#overview) rule).

- **Baseline + candidates (round 1, A).** Read `TARGET.md`. Build/identify a measurement harness and record the **baseline number** (SQL: wall-time + rows/bytes scanned via `EXPLAIN ANALYZE`; Python: median over N runs via `timeit`/`pytest-benchmark`, plus a `cProfile` hotspot). Identify the **real bottleneck with evidence** — not a guess. Propose ranked candidates (C1, C2, …), each with the mechanism of the expected win and any correctness risk. Do **not** change code yet.
- **Challenge (even rounds, B).** Reproduce A's baseline where you can. Attack: is the data representative? the metric the right one? the bottleneck actually dominant? Is each candidate premature/cargo-cult, and will it move the *measured* metric? Flag correctness risks. For each, name the measurement that proves or kills it. Numbered challenges. Then flip `STATUS: WAITING: A`, bump `ROUND`, **exit**.
- **Implement + benchmark (odd interior rounds, A).** Apply the surviving candidate(s) in the repo. Benchmark each against the baseline on the **same harness and data**, enough iterations to beat noise. **Prove output equality** (SQL: `EXCEPT` both directions / `ORDER BY`+hash / row-count+checksum; Python: identical return or existing tests pass). Per candidate write `Result: kept|reverted`, baseline→after numbers, and the correctness check. A candidate that isn't measurably better, or changes output, is **reverted**.
- **Audit the measurement (round `n-1`, last B round — only when `n >= 5`).** Never at `n=3`. For each kept candidate, attack the *measurement*, not just the idea: warm-cache/JIT artifact, unrepresentative data, too few iterations vs variance, correctness check too weak. Decide `keep` / `revert` / `doubt` (needs re-measure). Is the win worth the added complexity? This is B's last word. Flip `STATUS: WAITING: A`, set `ROUND: <n>`, **exit**.
- **Synthesize + ask (round `n`, A).** Net result: which candidates to keep with their numbers and the combined effect, the correctness statement, the complexity/maintainability cost, and anything still `UNVERIFIED`. Then `STATUS: AWAITING_USER` and stop.

### Early termination

`ROUNDS` (default 5) is the max, not the requirement. Skip a round that would rubber-stamp; when in doubt, run it. Role-relative triggers (hold at any `n`):

| Trigger | What to do |
|---|---|
| A's R1 finds the target is already optimal / not the bottleneck | Skip to synthesis: report "no measured win available," recommend no change. |
| A B-challenge raises zero substantive objections | A goes ahead and benchmarks, then jumps toward synthesis. |
| Every candidate reverted (no measured win) AND no open challenge | Jump to synthesis — recommend keeping the baseline. |
| A kept a candidate with new/contested numbers | Run the next B-audit — it catches measurement artifacts. |

When skipping ahead, jump straight to the final round (`ROUND: <n>`, A synthesizes, `AWAITING_USER`) — early exit never lands the terminal step on B. Note any skip in the synthesis.

## Surfacing rounds in chat

After every round (yours OR the peer's), print a 5-15 line digest in chat *before* your next action. Use `optimize_digest <N>` from [reference/handoff.sh](reference/handoff.sh) — it extracts agreements + candidate/challenge titles + per-candidate results + net result, truncated.

```
**B's R2 (challenge):**
- ✓ Baseline harness is fair (cold cache, 10M-row sample)
- ! C1: index won't help — the scan isn't the bottleneck, the hash join is
- ! C2: correctness risk — the rewrite drops NULL group
```

The user can interrupt at any moment. Treat any user message as a steer — address it before continuing.

## Shared state in `.optimize/`

Create `.optimize/` at the repo root on init and append `.optimize/` to `.gitignore`. Files:

| File | Purpose | Written by |
|---|---|---|
| `TARGET.md` | What to optimize + the measurement setup (data, harness, metric) + constraints | Active agent on init |
| `STATE.md` | `ROUND`, `ROUNDS`, `STATUS`, `A`, `B`, `EFFORT`, round log | Every round |
| `R1.md` … `R<ROUNDS>.md` | Round content (numbers live here; code lives in the repo) | Actor of that round |
| `bench/` | Benchmark scripts + raw timing output, so both agents run the *same* harness | Whoever builds the harness (R1) |
| `USER_NOTES.md` | User-injected steers (created lazily) | `optimize_inject` |
| `session.log` + `round-<N>-<peer>.log` | Peer stdout | `optimize_handoff` |

`A` and `B` are fixed for the session — whoever measured in R1 is A. Full templates in [reference/file-formats.md](reference/file-formats.md).

## Entry modes

Both modes accept the [Flags](#flags) (`--number n`, `--model high|xhigh`). Parse them off the invocation first, then write the resolved `ROUNDS:`/`EFFORT:` into `STATE.md` at init.

### Mode 1 — fresh target: `/pair-optimize "<target>" [--number n] [--model high|xhigh]`
You are the orchestrator (A). Write `TARGET.md` (the thing to optimize **and** how it'll be measured — data, harness, metric) and `STATE.md` (`ROUND: 1`, `ROUNDS: <n>`, `STATUS: ACTIVE: <you>`, `A: <you>`, `B: <peer>`, `EFFORT: <effort>`), then do R1. After R1, `ROUND: 2`, `STATUS: WAITING: <peer>`, then `optimize_handoff <peer>` + `optimize_wait`, and stay alive for the rest of A's rounds.

### Mode 2 — continue from session: `/pair-optimize --from-session [--number n] [--model high|xhigh]`
Use when you've just profiled/proposed an optimization mid-conversation and want the peer to challenge it. You are implicitly A; your most-recent baseline+proposal becomes R1. Write `TARGET.md` (enough that B can act cold — B sees only `.optimize/`), write `R1.md`, set `STATE.md` (`ROUND: 2`, `ROUNDS: <n>`, `STATUS: WAITING: <peer>`, …), then `optimize_handoff` + `optimize_wait`.

**Auto-detect Mode 2:** no target arg AND no existing `.optimize/` AND the recent conversation has a baseline+proposal you authored → default to Mode 2. Otherwise prompt for a target. If `.optimize/` already exists, treat as resume — don't overwrite.

### Flags

| Flag | Meaning | Default |
|---|---|---|
| `--number n` (alias `--rounds n`) | Requested **round cap / depth**, written to `ROUNDS:` (a max — early termination can end sooner). **Normalized to odd and `>= 3`**: even `n` snaps **up** to `n+1`, `n < 3` rises to `3`. Always print a one-line reason before the loop, e.g. `--number 4 can't end on A; using a 5-round cap so A synthesizes last.` | `5` |
| `--model high\|xhigh` | Peer reasoning effort, written to `EFFORT:`. `optimize_handoff` injects `codex exec -c model_reasoning_effort=<v>` / `claude --effort <v>`. Only `high`/`xhigh` accepted; an invalid value should abort before writing `.optimize/`. Omitted → empty `EFFORT:`, each CLI's own default. | unset |

## Handoff

**`optimize_handoff` + `optimize_wait` are orchestrator-only.** Run them only after *your own* non-final A round — never as a cold-woken peer. After writing your round and updating `STATE.md`:

```bash
source ~/.claude/skills/pair-optimize/reference/handoff.sh   # or ~/.agents/...
optimize_handoff codex                                        # or: optimize_handoff claude
```

`optimize_handoff` does the headless invocation correctly (nohup + detach, `--` terminator for claude, `stdbuf` for live logging, injecting the `EFFORT:` flag). Do not call it at the final round — it refuses and tells you to set `STATUS: AWAITING_USER`.

### Then wait — the handoff isn't tracked by the harness

`optimize_handoff` uses `nohup ... &`, which takes the peer **outside the Claude Code harness's process tracking** — you won't be notified when its round lands. Immediately after `optimize_handoff`, call `optimize_wait` so the harness has a tracked process:

```
# Claude Code:
Bash(command="source ~/.claude/skills/pair-optimize/reference/handoff.sh && optimize_wait", run_in_background=true)
# Codex CLI / inline: call optimize_wait in the foreground — it blocks until the peer flips STATE.md.
```

`optimize_wait` polls `.optimize/STATE.md` every 5s and exits when STATUS flips off `WAITING: <peer>`. Exit 0 = your turn; exit 2 = timeout (re-invoke); exit 3 = peer likely crashed (`optimize_status` / `optimize_peer_status <peer>`).

## Hazards

All guarded by `optimize_handoff` — listed so you don't reinvent them.

| Hazard | Rule |
|---|---|
| `claude -p "<prompt>" <flags>` — flags after prompt hang the CLI | Flags first; use `optimize_handoff`. |
| `claude --add-dir <dir> "<prompt>"` — variadic flag eats prompt | `--` terminator before the prompt. |
| `killall claude` / `pkill codex` to recover | Kills the user's main session. Use `optimize_peer_status <peer>`. |
| Benchmarking with a warm cache / one iteration | Fake wins. State cache state; run enough reps; report spread. |
| Keeping a candidate without an output-equality check | Correctness regression masquerading as a speedup. The contract forbids it. |

## Steering as a human

| Command | What it does |
|---|---|
| `optimize_watch` | `tail -F .optimize/session.log` across all rounds. |
| `optimize_status` | One-screen summary: `STATE.md` + open notes + last 20 log lines. |
| `optimize_inject "<note>"` | Append a USER_NOTE; next agent must address it before their round. |
| `optimize_takeover` | Kill peer by PID, set `STATUS: BLOCKED: human-takeover`. |
| `optimize_resume <peer>` | After takeover + manual edits, hand back. Does NOT bump `ROUND`. |
| `optimize_digest <N>` | Print the terse digest of `R<N>.md`. |

## Common mistakes

| Mistake | Fix |
|---|---|
| Optimizing before measuring | R1 establishes the baseline first. No baseline = no contract. |
| Optimizing something that isn't the bottleneck | Profile in R1; B challenges the bottleneck claim in R2. |
| Claiming a speedup with no number / one noisy run | Report median + spread over N reps; B audits this in R4. |
| Keeping a faster-but-wrong version | Output-equality is half the contract. Wrong = reverted. |
| Peer (B) calling `optimize_handoff`/`optimize_wait` after a B round | Spawns a duplicate orchestrator that races the live one. The peer is one-shot: flip `STATUS: WAITING: A` and **exit**. |
| Invoking peer at the final round | The final round (`ROUND == ROUNDS`) ends the loop. Surface to the user. |
| Running pair-optimize alongside `.consult/` or `.pair/` in one repo | One pair session per repo. If another exists, abort `STATUS: BLOCKED: collision`. |
| Idling after `optimize_handoff` ("harness will notify me") | It won't — the peer is `nohup`'d. Always follow with `optimize_wait` (background in Claude Code). |

## Resuming

`/pair-optimize` with no args + existing `.optimize/` → resume:
- `WAITING: <you>` → do your round.
- `WAITING: <peer>` → mid-flight; `optimize_watch` or report state.
- `AWAITING_USER` → show the final round file (`R<ROUNDS>.md`) and ask what they want.
- `BLOCKED` → tell the user what's blocked; offer `optimize_resume <peer>`.

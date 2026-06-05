---
name: pair-consult
description: Bounded multi-round consultation (default 5 rounds, set with --number) between Claude Code and Codex on a single user question or small coding task — A proposes, B reviews, A responds, B re-reviews, A synthesizes and asks the user. Use when /pair-coding's spec→plan→code ceremony is too heavy and the user wants a tighter back-and-forth ending in user confirmation.
---

# pair-consult

## TL;DR for a cold-woken peer

You were invoked via `codex exec` or `claude -p` with *"Resume the pair-consult skill. Read .consult/STATE.md..."*. You are a **one-shot peer**: you do exactly ONE round (an even round — R2, R4, …) and exit. Do this:

1. `cat .consult/STATE.md .consult/QUESTION.md .consult/USER_NOTES.md` — orient.
2. Confirm `STATUS: WAITING: <you>` and read `ROUND:` + `ROUNDS:`. You are B, so this round is a review: a *re-review* (R4-style, accept/double-down) if `ROUND == ROUNDS-1`, otherwise a fresh-critique review (R2-style). See [Round protocol](#round-protocol--one-allowed-action-per-round).
3. Write `R<ROUND>.md`, then update `STATE.md`: set `STATUS: WAITING: <orchestrator>` and bump `ROUND`.
4. **EXIT. Do NOT call `consult_handoff` or `consult_wait`.** The orchestrator (the interactive session that woke you) is already blocked in `consult_wait` and resumes the instant you flip `STATE.md`. If you hand off, you spawn a **duplicate orchestrator** — two instances then write the same round and collide on `STATE.md`. This is the bug. Don't be it.

**You never do the final round.** The final round (`ROUND == ROUNDS`) is always the orchestrator's synthesis. Only the orchestrator runs `consult_handoff` + `consult_wait`; see [Two roles](#two-roles) and [Handoff](#handoff).

No session memory across turns. State lives in `.consult/`. Templates for every file are in [reference/file-formats.md](reference/file-formats.md).

## Overview

The default session is **5 rounds**. `--number n` sets a different total (`ROUNDS:` in `STATE.md`); see [Flags](#flags). The 5-round shape:

| Round | Actor | Action | Output | After |
|---|---|---|---|---|
| **R1** | A (orchestrator) | Propose | `R1.md` (+ code in repo if coding) | flip `WAITING: B` → `consult_handoff B` + `consult_wait` |
| **R2** | B (peer, one-shot) | Review proposal | `R2.md` (agreements + numbered critiques) | flip `WAITING: A` → **exit** (no handoff, no wait) |
| **R3** | A (orchestrator) | Respond per critique (agree/partial/object) | `R3.md` | flip `WAITING: B` → `consult_handoff B` + `consult_wait` |
| **R4** | B (peer, one-shot) | Re-review (accept/double-down) | `R4.md` | flip `WAITING: A` → **exit** (no handoff, no wait) |
| **R5** | A (orchestrator) | Synthesize, ask user | `R5.md` — user reads this | stop — `STATUS: AWAITING_USER` |

**General rule for any odd `n` (`ROUNDS`):** round 1 = A proposes; the final round `n` = A synthesizes (`AWAITING_USER`); interior rounds alternate — **even rounds = B reviews, odd rounds = A responds**. `n` is always odd (forced at init) so A is both the first proposer and the last synthesizer. At `n=5` this is exactly the table above; at `n=7` it's propose · review · respond · review · respond · re-review · synthesize.

After the final round, `STATUS: AWAITING_USER` and the loop stops. The user's reply (confirm / redirect / cancel) closes the session.

## Two roles

The loop has an **asymmetry that prevents duplicate instances** — internalize it before anything else.

- **Orchestrator = A** = the interactive session that ran `/pair-consult`. It is alive for the whole session. It does the odd rounds (R1, R3, … and the final round). After each non-final round it spawns the peer (`consult_handoff B`) and blocks in `consult_wait` until the peer flips `STATE.md` back. After the final round it stops.
- **Peer = B** = a *fresh, headless, one-shot* instance, cold-woken by the orchestrator's `consult_handoff`. It does exactly one round (an even round — R2, R4, …), flips `STATUS: WAITING: A`, and **exits**. It never calls `consult_handoff` and never calls `consult_wait`.

**Why:** `consult_handoff` always *spawns a new instance* of the named peer. If the peer (B) hands back with `consult_handoff A`, it spawns a **second A** — while the original orchestrator A is still alive in `consult_wait`. Both then see `WAITING: A`, both act, both write the round, and they collide on `STATE.md` (`Error editing file`). The only safe shape is: **only the orchestrator hands off and waits; the peer flips-and-exits.** A peer that is alive does not need to be re-spawned — it's already waiting.

So `consult_handoff` + `consult_wait` are **orchestrator-only** verbs. If you were cold-woken by a resume prompt, you are the peer: flip and exit.

## When to use

- `/pair-consult <question>` (fresh) or `/pair-consult` (resume).
- Work fits in one round of proposal — not a 5-step plan. If it doesn't fit, use [pair-coding](../pair-coding/SKILL.md).
- User wants a structured second opinion ending in their own go/no-go.
- You were invoked as the peer by the active agent.

**Don't use for:** multi-step implementation (use pair-coding), open-ended exploration (use brainstorming), one-shot code review (use `code-review`), or solo work.

## Round protocol — one allowed action per round

Each round is narrow on purpose. Stay in your lane. **Templates for each round file are in [reference/file-formats.md](reference/file-formats.md);** the semantics are below — each bullet's header names the rounds it covers (1:1 with R1–R5 at `n=5`; for larger odd `n` the review/respond actions repeat per the [Overview](#overview) rule).

- **Propose (round 1, A).** Read `QUESTION.md`. For coding tasks, write the actual code in the repo, run the test, then write `R1.md` as the design rationale (not a code dump).
- **Review (even rounds, B).** Read the latest `R*.md` and (for coding) `git diff` + run the tests yourself. Open numbered critiques in `R<round>.md` — do **not** edit A's artifacts. Your critiques drive A's next round. Then flip `STATUS: WAITING: A`, bump `ROUND`, and **exit** — you are one-shot; do not hand off.
- **Respond (odd interior rounds, A).** For each numbered critique, write a verdict (`agree` / `partial` / `object`), the action you took, and reasoning when not pure agreement. Address **every** critique — skipping one is a bug. If you applied code changes, re-run the test and note the result in the relevant C-block.
- **Re-review (round `n-1`, the last B round).** For each item where A objected or partial-applied, decide `accept` or `double down`. **No fresh critiques** — bugs A introduced in the prior round are double-downs with a sub-finding, not new Cs. This is B's last word. Then flip `STATUS: WAITING: A`, set `ROUND: <n>`, and **exit** — do not hand off (A is already waiting and writes the final round).
- **Synthesize (round `n`, A).** Write the user-facing close: what we landed on, where we agreed, unresolved tensions plainly stated, what we need from the user. Then `STATUS: AWAITING_USER` and stop.

### Early termination — skip ahead when there's consensus

`ROUNDS` (default 5) is the max, not the requirement. Skip when the next round would be a rubber-stamp; when in doubt, do the round. The triggers are role-relative — they hold at any `n`:

| Trigger | What to do |
|---|---|
| A B-review has zero critiques (full agreement) | Skip the rest of the interior rounds. A jumps to the final synthesis round directly. |
| An A-response is all `agree` AND adds no new code/claims/reasoning | Skip the next B-review. A jumps to synthesis directly. |
| An A-response is all `agree` but introduces new substance | Run the next B-review — it catches regressions A introduced. (The skill's trial caught a real null-semantics bug this way.) |
| An A-response has any `object` or `partial` | Run the next B-review. |
| The last B re-review is done | Always run the final synthesis round — it's where the user is asked. |

When skipping ahead, jump straight to the final round (`ROUND: <n>`, A synthesizes, `AWAITING_USER`) — early exit never lands the terminal step on B. Mark skipped round-log rows `skipped`, and call out the skip in the synthesis so the user sees the early exit.

## Surfacing rounds in chat — keep the user in the loop

After every round (yours OR the peer's), print a 5-15 line digest in chat *before* doing your next action. This is what makes pair-consult feel like a conversation instead of a black-box file machine. Use `consult_digest <N>` from [reference/handoff.sh](reference/handoff.sh) — it extracts agreements + critique titles + per-C verdicts + overall verdict, already truncated.

```
**B's R2:**
- ✓ <agreement, one line>
- ! C1: <critique title>
- ! C2: <critique title>
```

```
**My R3:**
- ✓ Agreed on C1, C2, C3, C5
- ↳ C4: partial — kept the WITH ORDINALITY shape but added type placeholders
- One new claim: SQL-side dedupe preferable to app-side (going into R4)
```

The user can interrupt at any moment. Treat any user message as a steer — address it before continuing.

## Shared state in `.consult/`

Create `.consult/` at the repo root on init and append `.consult/` to `.gitignore`. Files:

| File | Purpose | Written by |
|---|---|---|
| `QUESTION.md` | User's question + pinned context | Active agent on init |
| `STATE.md` | `ROUND`, `STATUS`, `A`, `B`, round log | Every round |
| `R1.md` … `R<ROUNDS>.md` | Round content | Actor of that round |
| `USER_NOTES.md` | User-injected steers (created lazily) | `consult_inject` |
| `session.log` + `round-<N>-<peer>.log` | Peer stdout | `consult_handoff` |

`A` and `B` are fixed for the session — whoever proposed in R1 is A. Full templates in [reference/file-formats.md](reference/file-formats.md).

## Entry modes

Both modes accept the optional flags in [Flags](#flags) (`--number n`, `--model high|xhigh`). Parse them off the invocation first, then write the resolved `ROUNDS:` and `EFFORT:` into `STATE.md` at init.

### Mode 1 — fresh question: `/pair-consult "<question>" [--number n] [--model high|xhigh]`
Standard init. You are the orchestrator (A). Write `QUESTION.md` and `STATE.md` (`ROUND: 1`, `ROUNDS: <n>`, `STATUS: ACTIVE: <you>`, `A: <you>`, `B: <peer>`, `EFFORT: <effort>`), then do R1 as described in the Round protocol. After R1, `ROUND: 2`, `STATUS: WAITING: <peer>`, then `consult_handoff <peer>` + `consult_wait` and stay alive for the rest of A's rounds (every odd round through the final).

### Mode 2 — continue from session: `/pair-consult --from-session [--number n] [--model high|xhigh]`
**Use when you're mid-conversation with the user and you've just proposed something** — code, an approach, a decision — and the user wants the peer to grill it. You are implicitly A; your most-recent proposal becomes R1 content.

1. Write `QUESTION.md` from the user's recent turn — include enough context that B can act cold (B does NOT see chat history; only `.consult/`).
2. Write `R1.md` by summarizing your most-recent proposal — don't restate the conversation, extract the proposal into the R1 template.
3. `STATE.md`: `ROUND: 2`, `ROUNDS: <n>`, `STATUS: WAITING: <peer>`, `A: <you>`, `B: <peer>`, `EFFORT: <effort>`. Round-log starts with the R1 row noting `from-session`.
4. `consult_handoff <peer>` + `consult_wait` — B does R2 (one-shot) and flips back; your `consult_wait` resumes you for R3.

### Flags

| Flag | Meaning | Default |
|---|---|---|
| `--number n` (alias `--rounds n`) | Total rounds for the session, written to `ROUNDS:`. **Must be odd and `>= 3`** so A both proposes and synthesizes. If the user gives an even `n`, **snap up to `n+1`** and tell them; if `n < 3`, raise to 3 and tell them. Larger `n` = longer wall-clock (each round is a fresh peer cold-start), so flag very large values to the user. | `5` |
| `--model high\|xhigh` | Peer reasoning effort, written to `EFFORT:`. `consult_handoff` injects `codex exec -c model_reasoning_effort=<v>` / `claude --effort <v>`. Omitted → empty `EFFORT:`, each CLI uses its own default. | unset |

Note: only `high` and `xhigh` are accepted. Your `~/.codex/config.toml` may already default codex to `xhigh`, so `--model xhigh` is often a no-op for the codex peer; `--model high` is what visibly steps it down.

**Auto-detect Mode 2:** when `/pair-consult` is invoked with no question argument AND no existing `.consult/` AND the recent conversation contains a proposal you authored, default to Mode 2 without requiring `--from-session` explicitly. Otherwise prompt the user for a question.

If `.consult/` already exists, **don't overwrite** — treat as resume; show `consult_status` and ask whether to continue or `rm -rf .consult/` for a fresh start.

## Handoff

**`consult_handoff` + `consult_wait` are orchestrator-only.** You run them only after *your own* non-final A round (R1, R3, … any odd round before the last) — never as a cold-woken peer (see [Two roles](#two-roles)). A peer flips `STATE.md` and exits; the orchestrator's existing `consult_wait` picks it up.

After writing your round (as the orchestrator) and updating `STATE.md`:

```bash
source ~/.claude/skills/pair-consult/reference/handoff.sh   # or ~/.agents/...
consult_handoff codex                                        # or: consult_handoff claude
```

`consult_handoff` does the headless invocation correctly (nohup + detach, `--` terminator for claude, `stdbuf` for live logging, and injecting the `EFFORT:` flag per CLI). Do not call this at the final round (`ROUND == ROUNDS`) — the function will refuse and tell you to set `STATUS: AWAITING_USER`.

### Then wait — the handoff isn't tracked by the harness

`consult_handoff` uses `nohup ... &` to detach the peer, which **takes it outside the Claude Code harness's process tracking**. The harness will NOT notify you when the peer's round lands. If you simply end your turn after `consult_handoff`, you will sit idle until the user pings (which surfaces a file-change reminder) or until a `ScheduleWakeup` fires — both unreliable and high-latency.

The fix: **immediately after `consult_handoff`, call `consult_wait`** so the harness has something to track:

```
# Claude Code (this is the important case):
Bash(
  command="source ~/.claude/skills/pair-consult/reference/handoff.sh && consult_wait",
  run_in_background=true,
)
# Codex CLI / inline: call consult_wait in the foreground — it will block until the peer flips STATE.md.
```

`consult_wait` polls `.consult/STATE.md` every 5s and exits the moment the STATUS line flips off `WAITING: <peer>`. When invoked via `Bash(run_in_background=true)`, the harness tracks the poll-process and notifies you on exit — you learn about R<N+1> at file-write time, not at next-user-ping time.

Behavior on exit:
- **Exit 0** — your turn. Read the new round file, surface a digest, do your round.
- **Exit 2** — timeout (default 540s, just under Bash's 600s ceiling). Re-invoke `consult_wait`. A peer round legitimately taking >9 min is rare but possible (large code reviews, slow networks).
- **Exit 3** — the peer likely crashed (no process holds the round log open and the file is stale). Run `consult_status` and `consult_peer_status <peer>` to investigate before retrying.

## Hazards

All guarded by `consult_handoff` — listed here so you don't reinvent them.

| Hazard | Rule |
|---|---|
| `claude -p "<prompt>" <flags>` — flags after prompt hang the CLI | Flags first; use `consult_handoff`. |
| `claude --add-dir <dir> "<prompt>"` — variadic flag eats prompt | `--` terminator before the prompt. |
| `claude -p --bare` — fails auth unless `ANTHROPIC_API_KEY` is set | Don't use `--bare`. |
| `killall claude` / `pkill codex` to recover | Kills the user's main session. Use `consult_peer_status <peer>` to list specific PIDs. |

## Steering as a human

While the loop runs:

| Command | What it does |
|---|---|
| `consult_watch` | `tail -F .consult/session.log` across all rounds. |
| `consult_status` | One-screen summary: `STATE.md` + open user notes + last 20 log lines. |
| `consult_inject "<note>"` | Append a USER_NOTE to `.consult/USER_NOTES.md`. Next agent must address it before their round. |
| `consult_takeover` | Kill peer by PID (via `lsof`), set `STATUS: BLOCKED: human-takeover`. |
| `consult_resume <peer>` | After takeover + manual edits, hand back. Does NOT bump `ROUND`. |
| `consult_digest <N>` | Print the terse digest of `R<N>.md` — used by the active agent to surface in chat. |

## Common mistakes

| Mistake | Fix |
|---|---|
| Doing more than one round's work in a turn | R1 proposes, doesn't preempt R2. R2 critiques, doesn't rewrite A's code. |
| Skipping critiques in R3 | Address every numbered critique. Even `object` is an answer. |
| Adding new critiques in R4 | R4 is `accept` / `double down` only. New bugs from R3 are double-downs with sub-findings. |
| Peer (B) calling `consult_handoff`/`consult_wait` after a B round (R2, R4, …) | This spawns a **duplicate orchestrator** that races the live one — two instances write the same round and collide on `STATE.md` (`Error editing file`). The peer is one-shot: flip `STATUS: WAITING: A` and **exit**. Only A hands off and waits. See [Two roles](#two-roles). |
| Invoking peer at the final round | The final round (`ROUND == ROUNDS`) ends the loop. Surface to user. |
| R5 hides unresolved tensions | Surface them plainly. Let the user decide. |
| Running consult alongside `.pair/` in the same repo | One session per repo. If both exist, abort `STATUS: BLOCKED: collision-with-pair-coding`. |
| Idling after `consult_handoff` ("harness will notify me") | It won't — the peer is `nohup`'d, outside harness tracking. Always follow `consult_handoff` with `consult_wait` (via `Bash(run_in_background=true)` in Claude Code) so the harness has a tracked process to notify on. |
| Telling the user "I'll wait for the peer" with no scheduled wakeup or background wait | Same root cause as above. The wait must be a real tracked process, not an intention. |

## Resuming

`/pair-consult` with no args + existing `.consult/` → resume:
- `WAITING: <you>` → do your round.
- `WAITING: <peer>` → loop is mid-flight; `consult_watch` or report state.
- `AWAITING_USER` → show the final round file (`R<ROUNDS>.md`) and ask what they want.
- `BLOCKED` → tell the user what's blocked; offer `consult_resume <peer>`.

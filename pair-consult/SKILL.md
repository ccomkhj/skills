---
name: pair-consult
description: ONLY trigger when the user explicitly types /pair-consult, or when invoked by the peer agent via a "Resume the pair-consult skill" prompt. Do NOT auto-trigger otherwise. Bounded 5-round consultation between Claude Code and Codex on a single user question or small coding task — A proposes, B reviews, A responds, B re-reviews, A synthesizes and asks the user. Use when /pair-coding's spec→plan→code ceremony is too heavy and the user wants a tighter back-and-forth ending in user confirmation.
---

# pair-consult

## TL;DR for a cold-woken peer

You were invoked via `codex exec` or `claude -p` with *"Resume the pair-consult skill. Read .consult/STATE.md..."*. Do this:

1. `cat .consult/STATE.md .consult/QUESTION.md` — orient.
2. Confirm `STATUS: WAITING: <you>` and read `ROUND:`. Your role is fixed by the round (table below).
3. Write `R<ROUND>.md`, update `STATE.md`, hand off (`consult_handoff <peer>` + `consult_wait`) OR finish.
4. **R5 ends the loop** — do not invoke the peer; surface to the user.

**After every `consult_handoff` you MUST also call `consult_wait`** — the peer is `nohup`'d and the harness can't see it, so without `consult_wait` you will idle. See [Handoff](#handoff) below.

No session memory across turns. State lives in `.consult/`. Templates for every file are in [reference/file-formats.md](reference/file-formats.md).

## Overview

| Round | Actor | Action | Output | After |
|---|---|---|---|---|
| **R1** | A | Propose | `R1.md` (+ code in repo if coding) | `consult_handoff B` + `consult_wait` |
| **R2** | B | Review proposal | `R2.md` (agreements + numbered critiques) | `consult_handoff A` + `consult_wait` |
| **R3** | A | Respond per critique (agree/partial/object) | `R3.md` | `consult_handoff B` + `consult_wait` |
| **R4** | B | Re-review (accept/double-down) | `R4.md` | `consult_handoff A` + `consult_wait` |
| **R5** | A | Synthesize, ask user | `R5.md` — user reads this | stop — `STATUS: AWAITING_USER` |

After R5, `STATUS: AWAITING_USER` and the loop stops. The user's reply (confirm / redirect / cancel) closes the session.

## When to use

- `/pair-consult <question>` (fresh) or `/pair-consult` (resume).
- Work fits in one round of proposal — not a 5-step plan. If it doesn't fit, use [pair-coding](../pair-coding/SKILL.md).
- User wants a structured second opinion ending in their own go/no-go.
- You were invoked as the peer by the active agent.

**Don't use for:** multi-step implementation (use pair-coding), open-ended exploration (use brainstorming), one-shot code review (use `code-review`), or solo work.

## Round protocol — one allowed action per round

Each round is narrow on purpose. Stay in your lane. **Templates for each round file are in [reference/file-formats.md](reference/file-formats.md);** the semantics are below.

- **R1 (A proposes).** Read `QUESTION.md`. For coding tasks, write the actual code in the repo, run the test, then write `R1.md` as the design rationale (not a code dump).
- **R2 (B reviews).** Read `R1.md` and (for coding) `git diff` + run the tests yourself. Open numbered critiques in `R2.md` — do **not** edit A's artifacts. Your critiques drive A's next round.
- **R3 (A responds).** For each numbered critique, write a verdict (`agree` / `partial` / `object`), the action you took, and reasoning when not pure agreement. Address **every** critique — skipping one is a bug. If you applied code changes, re-run the test and note the result in the relevant C-block.
- **R4 (B re-reviews).** For each item where A objected or partial-applied, decide `accept` or `double down`. **No fresh critiques** — bugs A introduced in R3 are double-downs with a sub-finding, not new Cs. R4 is B's last word.
- **R5 (A synthesizes).** Write the user-facing close: what we landed on, where we agreed, unresolved tensions plainly stated, what we need from the user. Then `STATUS: AWAITING_USER` and stop.

### Early termination — skip ahead when there's consensus

Five rounds is the max, not the requirement. Skip when the next round would be a rubber-stamp; when in doubt, do the round.

| Trigger | What to do |
|---|---|
| R2 has zero critiques (full agreement) | Skip R3 + R4. A writes R5 directly. |
| R3 all `agree` AND no new code/claims/reasoning | Skip R4. A writes R5 directly. |
| R3 all `agree` but introduces new substance | Run R4 — it catches regressions A introduced. (The skill's trial caught a real null-semantics bug this way.) |
| R3 has any `object` or `partial` | Run R4. |
| R4 done | Always run R5 — it's where the user is asked. |

When skipping, omit (or mark `skipped`) the round-log row, and call out the skip in R5 so the user sees the early exit.

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
| `R1.md` … `R5.md` | Round content | Actor of that round |
| `USER_NOTES.md` | User-injected steers (created lazily) | `consult_inject` |
| `session.log` + `round-<N>-<peer>.log` | Peer stdout | `consult_handoff` |

`A` and `B` are fixed for the session — whoever proposed in R1 is A. Full templates in [reference/file-formats.md](reference/file-formats.md).

## Entry modes

### Mode 1 — fresh question: `/pair-consult "<question>"`
Standard init. Write `QUESTION.md` and `STATE.md` (`ROUND: 1`, `STATUS: ACTIVE: <you>`, `A: <you>`, `B: <peer>`), then do R1 as described in the Round protocol. After R1, `ROUND: 2`, `STATUS: WAITING: <peer>`, `consult_handoff <peer>`.

### Mode 2 — continue from session: `/pair-consult --from-session`
**Use when you're mid-conversation with the user and you've just proposed something** — code, an approach, a decision — and the user wants the peer to grill it. You are implicitly A; your most-recent proposal becomes R1 content.

1. Write `QUESTION.md` from the user's recent turn — include enough context that B can act cold (B does NOT see chat history; only `.consult/`).
2. Write `R1.md` by summarizing your most-recent proposal — don't restate the conversation, extract the proposal into the R1 template.
3. `STATE.md`: `ROUND: 2`, `STATUS: WAITING: <peer>`, `A: <you>`, `B: <peer>`. Round-log starts with the R1 row noting `from-session`.
4. `consult_handoff <peer>` — B does R2.

**Auto-detect Mode 2:** when `/pair-consult` is invoked with no question argument AND no existing `.consult/` AND the recent conversation contains a proposal you authored, default to Mode 2 without requiring `--from-session` explicitly. Otherwise prompt the user for a question.

If `.consult/` already exists, **don't overwrite** — treat as resume; show `consult_status` and ask whether to continue or `rm -rf .consult/` for a fresh start.

## Handoff

After writing your round and updating `STATE.md`:

```bash
source ~/.claude/skills/pair-consult/reference/handoff.sh   # or ~/.agents/...
consult_handoff codex                                        # or: consult_handoff claude
```

`consult_handoff` does the headless invocation correctly (nohup + detach, `--` terminator for claude, `stdbuf` for live logging). Do not call this at R5 — the function will refuse and tell you to set `STATUS: AWAITING_USER`.

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
| Invoking peer at R5 | R5 ends the loop. Surface to user. |
| R5 hides unresolved tensions | Surface them plainly. Let the user decide. |
| Running consult alongside `.pair/` in the same repo | One session per repo. If both exist, abort `STATUS: BLOCKED: collision-with-pair-coding`. |
| Idling after `consult_handoff` ("harness will notify me") | It won't — the peer is `nohup`'d, outside harness tracking. Always follow `consult_handoff` with `consult_wait` (via `Bash(run_in_background=true)` in Claude Code) so the harness has a tracked process to notify on. |
| Telling the user "I'll wait for the peer" with no scheduled wakeup or background wait | Same root cause as above. The wait must be a real tracked process, not an intention. |

## Resuming

`/pair-consult` with no args + existing `.consult/` → resume:
- `WAITING: <you>` → do your round.
- `WAITING: <peer>` → loop is mid-flight; `consult_watch` or report state.
- `AWAITING_USER` → show `R5.md` and ask what they want.
- `BLOCKED` → tell the user what's blocked; offer `consult_resume <peer>`.

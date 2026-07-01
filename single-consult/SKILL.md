---
name: single-consult
disable-model-invocation: true
description: "Fast in-session second opinion — an internal Claude subagent (default fable) reviews your proposal over N bounded rounds, then you decide. The single-engine, no-external-peer sibling of pair-consult."
argument-hint: "<question> [--model sonnet|opus|fable] [--depth high|xhigh] [--number n]"
---

# single-consult

A bounded consultation on one question, run **entirely inside your live session**. You (A, the orchestrator) propose; a **reviewer subagent** (B, spawned with the Agent tool) critiques; you respond; it re-reviews; you synthesize and ask the user.

This is the fast sibling of `pair-consult`. Because B is an internal, harness-tracked subagent — not a detached external CLI — there is **no shared state, no handoff script, no polling, no resume machinery**. The whole loop lives in this conversation: you hold the thread across rounds, and each Agent call returns B's round directly.

## Round shape

Default **5 rounds**. `--number n` sets the cap (a max — [early termination](#early-termination) can finish sooner). `n` is normalized odd and `>= 3` so A both proposes first and synthesizes last.

| Round | Actor | Action |
|---|---|---|
| **R1** | A (you) | Propose. For coding, write the code + run the test, then state the design rationale. |
| **R2** | B (subagent) | Review: agreements + numbered critiques `C1…Cn`. |
| **R3** | A | Respond to **every** critique: `agree` / `partial` / `object` + action taken. |
| **R4** | B (same subagent) | Re-review: `accept` / `double down` per prior C. No new critiques. |
| **R5** | A | Synthesize, ask the user. |

**General rule for any odd `n`:** R1 = A proposes; final round = A synthesizes; interior rounds alternate **even = B reviews, odd = A responds**. At `n=3` it's propose · review · synthesize (one B round, a fresh review — no re-review).

## The reviewer subagent

Spawn B **once** with a name so you can reuse it:

- **R2 (first review)** — `Agent(subagent_type: "claude", name: "reviewer", model: <--model, default fable>, prompt: <the review brief below>)`. B is fresh: the brief must carry everything it needs. B shares your working tree, so it sees your uncommitted changes directly.
- **R4 (re-review)** — `SendMessage(to: "reviewer", …)` with A's R3 response. **Do not spawn a new subagent** — the same B is still alive and remembers its own R2 critiques, so `accept` / `double down` is natural and you pass only what's new.

The reviewer's returned text **is** that round's content — read it, then act on it. Nothing is written to disk.

### Review brief — the required shape of B's prompt

B never sees the chat — only what you pass. Every review round uses this shape (fill the angle-bracketed parts):

```
You are B, the reviewer in a bounded single-consult (round R<n>). You review; you do NOT implement.

Read-only mandate: do not edit, write, or commit any files. Read files and — coding tasks only — run the test. Nothing else. Return your review as text; it IS the round's content.

## Question
<the user's question>

## Materials
<what to read: A's R1 proposal, pasted below; for coding, also read `git diff` and run the test yourself>
<paste A's latest proposal / response>

## Output — return exactly this
**Agreements** — one line each
**Critiques** — C1, C2, … each: title · the specific issue · Fix: concrete suggestion · Severity: high|med|low
**Overall verdict** — 2–3 lines; name the single most important change
```

The read-only mandate is load-bearing: a `claude` subagent has full tools and could silently rewrite your uncommitted tree mid-review. Keep it in every brief.

### `--depth` (reasoning effort)

The Agent tool exposes `model` but **no effort knob**. So `--depth high|xhigh` is delivered as a directive inside B's prompt: append `Think hard — ultrathink this review.` for `high`, and a stronger `Reason at maximum depth; ultrathink exhaustively.` for `xhigh`. Omitted → no directive, B uses its default. This is the only honest lever available.

## Round protocol — one action per round

Stay in your lane; each round is narrow on purpose.

- **Propose (R1, A).** Read the question. For coding, write the actual code and run the test *before* writing the rationale — don't dump code, state the design decision and why.
- **Review (even rounds, B).** B reads the latest proposal/response (and, for coding, `git diff` + runs the test). Returns agreements plus numbered critiques. Critiques drive A's next round.
- **Respond (odd interior rounds, A).** For each `Cn`: a verdict (`agree` / `partial` / `object`) and the action you took. Address **every** critique — skipping one is a bug. **Don't rubber-stamp.** You (A) are usually the *stronger* model and B often the weaker (`fable` by default), so agreement carries the burden of proof: before you `agree` on a `high`-severity critique, verify it against the actual files (re-read / re-run) — a claim you can't independently confirm is `partial` at best, and a reviewer over-flag is an `object`. Dissent can be quick; blanket agreement is a smell. If you changed code, re-run the test and note the result.
- **Re-review (round `n-1`, only when `n >= 5`).** For each item A objected to or partial-applied, B decides `accept` or `double down`. **No fresh critiques — one exception:** a *regression A introduced in R3* may be raised as a single finding labeled `NEW (R3-regression)`, scoped strictly to defects R3's changes created. If it relates to an existing C, fold it in as a double-down sub-finding instead. B's last word.
- **Synthesize (final round, A).** Write the user-facing close: what you landed on, where you agreed, unresolved tensions stated plainly, and what you need from the user. Then stop and ask. **At `n=3` there is no respond round, so the synthesis carries it** — give a verdict (`agree` / `partial` / `object`) per `Cn` inside the close, so no critique vanishes unaddressed.

### Early termination

The round cap is a max, not a quota. Skip a round that would only rubber-stamp; when in doubt, do the round.

| Trigger | Do |
|---|---|
| A B-review has zero critiques (full agreement) | Skip the rest — jump to the final synthesis round. |
| An A-response is all `agree` and adds no new code/claims | Skip the next B-review — jump to synthesis. |
| An A-response is all `agree` but adds new substance | Run the next B-review (it catches regressions A just introduced). |
| An A-response has any `object` or `partial` | Run the next B-review. |

Early exit never lands the final step on B — always finish with A's synthesis. Note any skip in the synthesis so the user sees it.

## Surfacing rounds in chat

After every round (yours or B's), print a 5–15 line digest **before** your next action — this is what makes it feel like a conversation, not a black box:

```
**Reviewer R2:**
- ✓ <agreement, one line>
- ! C1: <critique title>
- ! C2: <critique title>
```

```
**My R3:**
- ✓ Agreed C1, C2
- ↳ C3: partial — kept the shape, added the missing guard
```

Any user message mid-loop is a steer — address it before continuing.

## Flags

| Flag | Meaning | Default |
|---|---|---|
| `--model sonnet\|opus\|fable` | Model for the **reviewer subagent** (B). A stays on your live session's model. | `fable` |
| `--depth high\|xhigh` | Reviewer reasoning effort, injected as an `ultrathink` directive in B's prompt (see [above](#--depth-reasoning-effort)). | unset |
| `--number n` (alias `--rounds n`) | Round cap. Normalized to **odd, `>= 3`**: even snaps up (`4→5`), `<3` rises to `3`. Print a one-line reason when you normalize. | `5` |

## Entry modes

- **Fresh:** `/single-consult "<question>" [flags]`. You are A. Do R1, then spawn the reviewer for R2.
- **From session:** `/single-consult --from-session [flags]` — when you've just proposed something in chat and want it grilled. Your most-recent proposal becomes R1; spawn the reviewer straight into R2 with a self-contained brief (B does **not** see the chat history — put everything in the prompt). Auto-detect this when invoked with no question and the recent turn holds a proposal you authored.

## Common mistakes

| Mistake | Fix |
|---|---|
| Spawning a new subagent for R4 | Reuse the R2 reviewer via `SendMessage` — it already holds its critiques. |
| Passing the full thread into R4 | B remembers R2; send only A's R3 response. |
| Doing more than one round's work in a turn | R1 proposes, doesn't preempt R2. B critiques, doesn't rewrite A's code. |
| Skipping a critique in R3 | Address every `Cn` — `object` is a valid answer. |
| Adding new critiques in R4 | R4 is `accept` / `double down` only — the sole exception is one `NEW (R3-regression)` finding for a defect R3 just introduced. |
| Ending the loop on B | The final round is always A's synthesis, where the user is asked. |
| Rubber-stamping (all `agree`, no verification) | You're usually the stronger model — verify `high`-severity critiques against the files before agreeing; over-flags are `object`s. |
| Synthesis hides unresolved tensions | State them plainly; let the user decide. |

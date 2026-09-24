---
name: sub-consult
disable-model-invocation: true
description: "Fast second opinion from a reviewer panel defined in panel.toml (default: Fable Pragmatist, Opus Skeptic, Codex gpt-6-astra Outsider). The reviewers critique your proposal in parallel over N bounded rounds, then you decide. The no-handoff-machinery sibling of pair-consult."
argument-hint: "<question> [--number n]"
---

# sub-consult

A bounded consultation on one question, driven **from your live session**. You (A, the orchestrator) propose. A **panel of reviewers** (B) defined in [`panel.toml`](panel.toml) critiques in parallel. You respond, they re-review, and you synthesize and ask the user.

This is the fast sibling of `pair-consult`; a panel round takes as long as its slowest reviewer (Opus at `xhigh`: a few minutes). Each reviewer call is an ordinary background Bash command, so the harness tracks it and notifies you when it finishes. There is **no shared state file, no STATE.md handoff, no polling**. The whole loop lives in this conversation, and each call returns that reviewer's round directly.

## The panel

The panel is defined in [`panel.toml`](panel.toml), the single source of truth for who reviews. Each `[reviewer.<name>]` table sets `engine` (`claude` | `codex`), `model`, `effort`, a critique-ID `prefix`, and a `persona`. The shared `[contract]` sets the read-only rules and output shape. **Every reviewer in the file runs every review round.** To change the panel, edit the TOML; nothing else needs to change.

Run `review.py list` for the live roster. Don't restate it here; the default panel is `fable` (Pragmatist, `F…`), `opus` (Skeptic, `O…`), and `astra` (Codex Outsider, `A…`).

Personas split the review into lanes, so the panel gives you several different reviews instead of the same review several times.

### `review.py` — the launcher

The Agent tool can set a subagent's `model` but not its effort. So [`review.py`](review.py), in this skill's directory, starts each reviewer through its own CLI with the TOML's model and effort:

```bash
python3 <skill-dir>/review.py list                                     # roster
python3 <skill-dir>/review.py start  <name> <brief-file>               # first review
python3 <skill-dir>/review.py resume <name> <session-id> <message-file> # re-review, same session
```

- Reviewers are isolated from your config. `claude` runs as `claude -p --model <m> --effort <e> --strict-mcp-config` with only Read/Grep/Glob/Bash and **no MCP servers**, and destructive Bash (`rm`, `git commit`/`push`/`stash`/`checkout`/`restore`/`switch`/`reset`/`clean`) is denied; beyond that, it is read-only by instruction. `codex` runs as `codex exec -m <m> --ignore-user-config` in a `read-only` sandbox, re-asserted on resume. Never drop these flags: `--tools` and `-s read-only` don't block MCP tools, and a reviewer with your Slack/Outlook/Kubernetes tools could act on them.
- Output is a `session: <id>` line, a blank line, then the review verbatim. **Keep each reviewer's session id**, because re-review resumes that session and the reviewer remembers its own critiques. The script writes nothing to disk, so the session ids in your context are the only state. `session: none` means the review is valid but can't be resumed: use it, and leave that reviewer out of re-reviews.
- On failure it prints `UNAVAILABLE: <reason>` and exits 1.
- Reviewers always run at the git root of your current directory (so drifting into a subfolder doesn't matter) and read your working tree, uncommitted changes included. Outside a git repo it refuses with `UNAVAILABLE: not inside a git repo`; `cd` to the repo under review. Requires Python 3.11+.

## Round shape

Default **5 rounds**. `--number n` sets the cap. It is a maximum: [early termination](#early-termination) can finish sooner. `n` is normalized odd and `>= 3` so A both proposes first and synthesizes last.

| Round | Actor | Action |
|---|---|---|
| **R1** | A (you) | Propose. For coding, write the code + run the test, then state the design rationale. |
| **R2** | Panel | Review, in parallel: agreements + numbered critiques (`F…`, `O…`, `A…`). |
| **R3** | A | Respond to **every** critique from every reviewer: `agree` / `partial` / `object` + action taken. |
| **R4** | Panel (same sessions) | Re-review: `accept` / `double down` per prior critique. No new critiques, except regressions. |
| **R5** | A | Synthesize, ask the user. |

**General rule for any odd `n`:** R1 = A proposes; final round = A synthesizes; interior rounds alternate **even = panel, odd = A responds**. R2 is the only fresh review; **every later panel round is a re-review** in the same sessions. At `n=3` it goes propose, review, synthesize: one panel round, a fresh review, and no re-review.

## Running the panel

- **R2 (first review):** write the review brief to **one** temp file (your scratchpad if you have one, else `mktemp`). Then, **in one message**, issue one Bash call per reviewer in `panel.toml`: `review.py start <name> <brief-file>`, each with `run_in_background: true`. They run concurrently. An `xhigh` review can outlast the 10-minute foreground Bash cap, and the harness notifies you as each one finishes. Record each reviewer's `session:` id.
- **R4 and later (re-review):** for each reviewer that has something to re-review, write a message file and run `review.py resume <name> <session-id> <message-file>`, again all in one message and in the background. **Never `start` a fresh review after R2**: the resumed session already holds its critiques. A reviewer is re-reviewed when A marked any of its critiques `object` or `partial`, **or** changed code for any of them. Its message carries A's verdicts on **that reviewer's own** critiques plus a short list of the changes made for them, so it can check for regressions. A reviewer with nothing disputed and no changes made for it gets no re-review.

Each reviewer's output **is** its part of the round. Wait for all of them, read them, then act.

If a reviewer prints `UNAVAILABLE: …`, retry it once when it failed fast (CLI missing, unauthenticated, bad JSON). Don't retry a timeout; that costs another half hour. If it fails again or timed out, continue with the rest of the panel and state the gap in the synthesis.

### Review brief — what goes in the prompt

`review.py start` prepends the reviewer's persona and the `[contract]` (read-only rules, output shape) from `panel.toml`. The brief carries only the round-specific material:

```
sub-consult, round R<n>. You review; you do NOT implement. Read-only.

## Question
<the user's question>

## Materials
<what to read: for coding, `git diff` and the test command to run>
<paste A's latest proposal / rationale>
```

Send the same brief to every reviewer. Their personas are what make the reviews differ; don't hand-tune briefs per reviewer.

## Round protocol — one action per round

Stay in your lane; each round is narrow on purpose.

- **Propose (R1, A).** Read the question. For coding, write the actual code and run the test *before* writing the rationale. Don't paste the code in full. State the design decision and why.
- **Review (even rounds, panel).** Each reviewer reads the latest proposal/response and, for coding, `git diff`, then runs the test. Each returns agreements plus critiques numbered with its own prefix.
- **Respond (odd interior rounds, A).** First **merge duplicates**: when reviewers raise the same point, answer it once as `F2 = O1 = A3`. A point raised independently by two or more reviewers carries more weight. It is still not proof. Then, for each critique, give a verdict (`agree` / `partial` / `object`) and the action you took. Address **every** critique from every reviewer; skipping one is a bug. **Don't rubber-stamp.** Agreement carries the burden of proof. Before you `agree` on a `high`-severity critique, verify it against the actual files (re-read / re-run). A claim you can't independently confirm is `partial` at best, and a reviewer over-flag is an `object`. When reviewers contradict each other (Pragmatist says "cut it", Skeptic says "guard it"), pick one side, say why, and carry the tension into the synthesis. Dissent can be quick. Blanket agreement is a smell. If you changed code, re-run the test and note the result.
- **Re-review (every panel round after R2, only when `n >= 5`).** For each of its items A objected to or partially applied, the reviewer decides `accept` or `double down`. **No fresh critiques, with one exception:** a *regression A's latest response introduced* may be raised as a single finding labeled `NEW (regression)`, scoped strictly to defects those changes created. Later rounds treat it like any other critique. The panel gets the last word in each re-review.
- **Synthesize (final round, A).** Write the user-facing close: what you landed on, where the panel agreed, where reviewers disagreed with you or with each other, unresolved tensions stated plainly, and what you need from the user. Then stop and ask. **At `n=3` there is no respond round, so the synthesis carries it**: give a verdict (`agree` / `partial` / `object`) for every critique inside the close, so none vanishes unaddressed.

### Early termination

The round cap is a maximum, not a quota. Skip a round that would only rubber-stamp; when in doubt, do the round.

| Trigger | Do |
|---|---|
| The whole panel returns zero critiques | Skip the rest — jump to the final synthesis round. |
| An A-response is all `agree` and adds no new code/claims | Skip the re-review — jump to synthesis. |
| An A-response is all `agree` but adds new substance | Re-review with the reviewers whose critiques drove the new code (they catch regressions A just introduced). |
| An A-response has any `object` or `partial` | Re-review with each reviewer that owns one of those critiques. |

Early exit never lands the final step on the panel: always finish with A's synthesis. Note any skip, and any reviewer that dropped out, in the synthesis so the user sees it.

## Surfacing rounds in chat

After every round, print a digest **before** your next action: 5–15 lines, grouped by reviewer for panel rounds. This keeps the loop visible to the user:

```
**Panel R2:**
- Fable (Pragmatist): ✓ <agreement> · ! F1: <title>
- Opus (Skeptic): ! O1: <title> · ! O2: <title>
- Astra (Outsider): ✓ <agreement> · ! A1: <title>
- ⇄ Overlap: F1 ≈ A1
```

```
**My R3:**
- ✓ Agreed O1, O2, F1 = A1
- ↳ A2: partial — kept the shape, reused the existing helper
- ✗ F2: object — the extra option is required by <caller>
```

Any user message mid-loop is a steer — address it before continuing.

## Flags

| Flag | Meaning | Default |
|---|---|---|
| `--number n` (alias `--rounds n`) | Round cap. Normalized to **odd, `>= 3`**: even snaps up (`4→5`), `<3` rises to `3`. Print a one-line reason when you normalize. | `5` |

There are no flags for choosing reviewers, models, or effort. `panel.toml` sets all of them: edit it to change who reviews, on which model, at what effort, and with what persona.

## Entry modes

- **Fresh:** `/sub-consult "<question>" [flags]`. You are A. Do R1, then spawn the panel for R2.
- **From session:** `/sub-consult --from-session [flags]`. Use this when you've just proposed something in chat and want it grilled. Your most recent proposal becomes R1; spawn the panel straight into R2 with a self-contained brief. Reviewers do **not** see the chat history, so put everything in the prompt. Auto-detect this mode when invoked with no question and the recent turn holds a proposal you authored.

## Common mistakes

| Mistake | Fix |
|---|---|
| Launching reviewers one after another | Issue every `review.py start` in **one** message, each `run_in_background: true`, so they run concurrently. |
| Running a reviewer in the foreground | An `xhigh` review can outlast the 10-minute foreground cap; always background it and wait for the notification. |
| `start` again for R4 | `resume` with the R2 session id. The reviewer remembers its own critiques. |
| Losing a session id | Note every `session:` line when a round returns; it is the only state. |
| Sending every reviewer the whole R3 | Each reviewer gets only A's verdicts on its own critiques. |
| Hard-coding a model or persona in the brief | `panel.toml` owns model, effort, and persona; the brief carries only the question and materials. |
| Skipping a critique in R3 | Address every `F`/`O`/`A` critique — `object` is a valid answer; merged duplicates count as addressed. |
| Treating panel consensus as proof | Two reviewers agreeing raises priority, not certainty — still verify against the files. |
| Adding new critiques in a re-review | Re-reviews are `accept` / `double down` only. The sole exception is one `NEW (regression)` finding for a defect A's latest changes introduced. |
| Ending the loop on the panel | The final round is always A's synthesis, where the user is asked. |
| Synthesis hides unresolved tensions | State them plainly, including reviewer-vs-reviewer disagreements; let the user decide. |

# pair-consult — file formats reference

Templates for files under `.consult/`. The round files (`R1.md`–`Rn.md`, default `n=5`) follow strict shapes; `STATE.md` is parsed by `consult_handoff` (greps for `ROUND:`, `ROUNDS:`, `EFFORT:`, and `STATUS:`).

## `.consult/QUESTION.md`

Written once at init. The user's input, verbatim.

```markdown
# Question

## From user
<verbatim text of the user's question or task>

## Pinned context (optional)
- <constraint, file path, deadline, etc. the user wants both agents to honor>
```

## `.consult/STATE.md`

Updated by the actor at the end of every round.

```markdown
# Consult Session: <short slug>

STATUS: WAITING: codex     # WAITING: claude | WAITING: codex | AWAITING_USER | BLOCKED: <reason>
ROUND: 2
ROUNDS: 5                  # total rounds this session — odd, >=3, default 5; fixed for the session
ACTOR: codex               # next agent to act (matches STATUS)
A: claude                  # whoever proposed in R1 — fixed for the session
B: codex                   # the peer — fixed for the session
EFFORT:                    # optional peer reasoning effort (high|xhigh); empty = each CLI's default

## Round log
| Round | Actor  | Output | Notes                                 |
|-------|--------|--------|---------------------------------------|
| 1     | claude | R1.md  | Proposed approach; pytest 4/4 green   |
| 2     | codex  | R2.md  | 3 critiques (regex, naming, edgecase) |
```

**Key conventions:**

- **`ROUND` points to the next round to execute** (not the one just completed). After completing round N, set `ROUND: N+1` on handoff. The final round's actor (always A) leaves `ROUND: <ROUNDS>` and sets `STATUS: AWAITING_USER`. `consult_handoff` greps this value to name the next peer's log file (`round-${ROUND}-${peer}.log`).
- **`ROUNDS` is fixed for the session** and set at init from `--number n` (default 5; forced odd and `>=3` so A always proposes *and* synthesizes — see SKILL.md). `consult_handoff` reads it to know which round is final; absent → treated as 5.
- **`A` and `B` are fixed for the session.** Whoever proposed in R1 is A; the peer is B. Do not swap mid-session.
- **`EFFORT` is fixed for the session** and set at init from `--model high|xhigh`. `consult_handoff` injects it into every peer invocation (`codex exec -c model_reasoning_effort=…` / `claude --effort …`); empty means no flag is added and each CLI uses its own default.
- `STATUS: WAITING: <peer>` is what `consult_handoff` looks for to know who to invoke.

### Templates are role-typed, not round-number-typed

The five templates below are keyed to a **role**, not a fixed round number. They map 1:1 onto rounds only at the default `n=5`. For any odd `n>=3`, reuse them by role (see SKILL.md's round-protocol for the full rule):

- Round 1 → **propose** (`R1.md` template), always A.
- The final round (`n`) → **synthesize** (`R5.md` template), always A.
- The B round just before synthesis (round `n-1`) → **re-review / accept-double-down** (`R4.md` template).
- Other even rounds → B **review** with fresh numbered critiques (`R2.md` template).
- Other odd interior rounds → A **respond** per critique (`R3.md` template).

For larger odd `n` the review/respond templates simply repeat; each round still writes `R<round>.md`.

## `.consult/R1.md` — A proposes

```markdown
# R1 — proposal (by A=<claude|codex>)

## Approach
<one paragraph: design or strategy>

## Solutions (optional — if you want to surface alternatives)
1. <option 1, one line>
2. <option 2, one line>

## Tradeoffs you considered
- <tradeoff 1>
- <tradeoff 2>

## Code (if this is a coding task)
- Files touched: `<paths>` — code lives in the repo, not here.
- Test command: `<cmd>` → `<result>`
- Diff highlights (optional): <one or two bullets, not the full diff>

## Things you decided NOT to do
- <explicit non-goal>

## Open questions for B
- <a place where B's second opinion is most valuable>
```

## `.consult/R2.md` — B reviews

```markdown
# R2 — review (by B=<claude|codex>)

## Where A is right
- <agreement 1 — be specific>
- <agreement 2>

## Critiques (numbered so A can address each)
1. **C1: <short title>**
   - **Where:** <file:line or section in R1.md>
   - **Concern:** <what's wrong / risky / missing>
   - **Suggestion:** <what to do instead, optionally a code snippet>
2. **C2: <short title>**
   - ...

## Verification you ran (if coding)
- `<cmd>` → `<result>`. <anything unexpected>

## Questions back to A
- <something only A can clarify>
```

## `.consult/R3.md` — A responds, one block per critique

```markdown
# R3 — response (by A)

## C1 — <recap of B's title>
**Verdict:** agree | partial | object
**Action:** <what changed in the code/design, OR why nothing changed>
**Reasoning:** <one or two sentences, especially when partial or object>

## C2 — ...

## Questions back to B (if any)
- <only if a new clarification is needed>
```

## `.consult/R4.md` — B's final review

```markdown
# R4 — final review (by B)

## C1
**B's verdict:** accept | double-down
**(if double-down):** <why A's reasoning doesn't hold>

## C2 ...

## Unresolved tensions
- <items where you and A still disagree after R3+R4>
- (or "(none — converged)")

## Overall verdict
ship | needs-more-iteration | escalate-to-user
```

## `.consult/R5.md` — A synthesizes, asks the user

This is what the user reads. Treat it like a PR description.

```markdown
# R5 — final synthesis (by A)

## Question (recap)
<one line from QUESTION.md>

## What we landed on
<2–4 sentences. If A and B couldn't agree, say so.>

## Final state
- Files: `<paths>` — `git diff` for the live code
- Tests: `<cmd>` → `<result>` (for coding)
- Or, for design-only consults: the recommended approach in 1–2 bullets

## Where A and B agreed
- <bullet>
- <bullet>

## Unresolved tensions (escalating to you)
- <one line per disagreement: A's position vs B's, with the implication of each>
- (or "(none — converged)")

## What we need from you
- [ ] Confirm and ship as-is
- [ ] Redirect (tell us what to change, we'll do another mini-loop)
- [ ] Cancel
- (Plus any specific decision questions if unresolved tensions remain)
```

## `.consult/USER_NOTES.md` — optional, user-injected

If the user runs `consult_inject "<note>"` mid-flight, the helper appends a block here. Both agents must read this file at the start of every round and address any unaddressed notes before doing their main action.

```markdown
# User notes (mid-flight)

## N1 (added at <timestamp>)
<user message>
**Status:** unaddressed | addressed-in-R3
```

The first agent to see an unaddressed note responds to it in their round (in addition to their main role), and marks the note `addressed-in-R<N>`.

## Per-round log files

Created automatically by `consult_handoff`: `.consult/round-<N>-<peer>.log` captures the peer's stdout/stderr when invoked headless, while `.consult/session.log` keeps a single rolling feed across all rounds.

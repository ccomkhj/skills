# pair-consult — files A writes

All under `.consult/`. `STATE.md` belongs to the helpers; B's shapes are in [peer.md](peer.md).

## `QUESTION.md`

```markdown
# Question

## From user
<the ask, verbatim>

## Pinned context
- <the decision the user faces>
- <constraints both agents must honor>
- <what B cannot reach: prod data, logs, this chat>
```

## `R1.md` — propose

```markdown
# R1 — proposal (by A=<claude|codex>)

## Approach
<one paragraph>

## Claims and evidence
- <claim> — `<file:line>` — measured | inferred | unverified

## Tradeoffs considered
- <tradeoff>

## Code
- Files touched: `<paths>`, or "none: design only"
- Re-check: `<cmd>` → <result>

## Decided against
- <explicit non-goal, and why>

## Open questions for B
- <where a second opinion is worth most>
```

## Respond (odd interior rounds)

One block per critique, none skipped.

```markdown
# R<n> — response (by A)

## C1 — <B's title>
**Verdict:** agree | partial | object
**Action:** <what changed, or why nothing did>
**Reasoning:** <required for partial and object>

## Questions back to B
- <only if needed>
```

## Synthesize (`R<cap>.md`)

What the user reads. Written like a PR description.

```markdown
# R<cap> — synthesis (by A)

## Question
<the ask, one line>

## What we landed on
<2–4 sentences; rounds skipped on an early exit>

## Final state
- <files and test result, or the recommended approach>

## Where A and B agreed
- <bullet>

## Unresolved tensions
- <A's position vs B's, and what each implies> (or "none — converged")

## What we need from you
- <the decision: confirm, redirect, or cancel, plus any specific question>
```

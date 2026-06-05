# pair-optimize — file formats reference

Templates for files under `.optimize/`. The round files (`R1.md`–`Rn.md`, default `n=5`) follow strict shapes; `STATE.md` is parsed by `optimize_handoff` (greps for `ROUND:`, `ROUNDS:`, `EFFORT:`, `STATUS:`).

## `.optimize/TARGET.md`

Written once at init. What to optimize **and how it will be measured** — without a measurement plan the contract can't hold.

```markdown
# Optimization target

## What to optimize
<the query / function / endpoint / pipeline step — file:line or the SQL itself>

## Metric
<primary: e.g. wall-time | rows-scanned | bytes-scanned | peak-memory | $cost. Name ONE primary.>

## Measurement setup
- Harness: <how to run it — script in .optimize/bench/, pytest-benchmark target, EXPLAIN ANALYZE, ...>
- Data: <representative dataset + size; where it comes from. Toy data = unverifiable.>
- Cache state: <cold | warm — and how it's controlled between runs>
- Reps: <how many iterations; report median + spread>

## Correctness oracle
<how "identical output" is checked: SQL EXCEPT both ways / row-count+checksum; Python return-equality / which tests must pass>

## Constraints (optional)
- <must not change the public signature / schema / etc.>
```

## `.optimize/STATE.md`

Updated by the actor at the end of every round.

```markdown
# Optimize Session: <short slug>

STATUS: WAITING: codex     # WAITING: claude | WAITING: codex | AWAITING_USER | BLOCKED: <reason>
ROUND: 2
ROUNDS: 5                  # round cap (max) this session — odd, >=3, default 5; fixed for the session
ACTOR: codex               # next agent to act (matches STATUS)
A: claude                  # whoever measured the baseline in R1 — fixed for the session
B: codex                   # the peer — fixed for the session
EFFORT:                    # optional peer reasoning effort (high|xhigh); empty = each CLI's default

## Round log
| Round | Actor  | Output | Notes                                            |
|-------|--------|--------|--------------------------------------------------|
| 1     | claude | R1.md  | Baseline 1.84s; bottleneck = hash join; 3 cands  |
| 2     | codex  | R2.md  | Challenged C1 (not the bottleneck); C2/C3 worth it|
```

**Key conventions:**

- **`ROUND` points to the next round to execute.** After completing round N, set `ROUND: N+1` on handoff. The final round's actor (always A) leaves `ROUND: <ROUNDS>` and sets `STATUS: AWAITING_USER`.
- **`ROUNDS` is the round cap**, normalized odd and `>=3` at init from `--number n` (default 5; early termination may end sooner). `optimize_handoff` reads it to know which round is final; absent → treated as 5.
- **`EFFORT`** is set at init from `--model high|xhigh`; `optimize_handoff` injects it into every peer invocation. Empty = no flag.
- **`A` and `B` are fixed for the session.** Whoever measured the R1 baseline is A.

### Templates are role-typed, not round-number-typed

Keyed to a role, mapping 1:1 onto rounds only at `n=5`. For larger odd `n`, reuse by role: round 1 = baseline (R1), final round = synthesize (R5), the B round just before synthesis = audit (R4), other even rounds = challenge (R2), other odd interior rounds = implement+benchmark (R3). Each round still writes `R<round>.md`.

## `.optimize/R1.md` — A measures the baseline and proposes

```markdown
# R1 — baseline + candidates (by A=<claude|codex>)

## Baseline (measured)
- Metric: <primary metric> = <number ± spread> over <N> reps, cache <cold|warm>
- Harness: `<cmd or .optimize/bench/...>`
- Raw: <link to .optimize/bench/baseline.txt or paste key lines>

## Bottleneck (with evidence)
<what actually dominates — profile output / EXPLAIN ANALYZE node / cProfile top frames. Not a guess.>

## Candidates (ranked, numbered)
1. **C1: <short name>**
   - **Mechanism:** <why it should help the measured metric>
   - **Hypothesized win:** <rough expectation>
   - **Correctness risk:** <none | what could change>
2. **C2: ...**

## Out of scope
- <explicitly not attempting this round>

## Open questions for B
- <where B's challenge is most valuable>
```

## `.optimize/R2.md` — B challenges

```markdown
# R2 — challenge (by B=<claude|codex>)

## Where A is right
- <agreement — be specific; e.g. baseline harness is fair>

## Challenges (numbered, tied to candidates)
1. **C1: <recap>**
   - **Concern:** <baseline unfair / wrong bottleneck / premature / correctness risk / won't move the metric>
   - **Settle it by:** <the measurement that confirms or kills this candidate>
2. **C2: ...**

## Verification you ran (if any)
- `<cmd>` → `<result>`. <did A's baseline reproduce?>

## Questions back to A
- <something only A can clarify>
```

## `.optimize/R3.md` — A implements and benchmarks (one block per candidate)

```markdown
# R3 — implement + benchmark (by A)

## C1 — <name>
**Result:** kept | reverted
**Baseline → after:** <num ± spread> → <num ± spread> (<Δ% on the primary metric>)
**Correctness:** <EXCEPT both ways: 0 rows / tests pass / return identical>
**Notes:** <what changed in the repo; why reverted if so>

## C2 — ...

## Questions back to B (if any)
- <only if a new clarification is needed>
```

## `.optimize/R4.md` — B audits the measurement

```markdown
# R4 — measurement audit (by B)

## C1
**Verdict:** keep | revert | doubt
**(if doubt/revert):** <warm-cache artifact / unrepresentative data / too few reps vs variance / weak correctness check / win not worth the complexity>

## C2 ...

## Net result
keep: <C#, C#>  ·  revert: <C#>  ·  unverified: <C#>
overall: ship | re-measure | no-win-keep-baseline
```

## `.optimize/R5.md` — A synthesizes, asks the user

This is what the user reads. Treat it like a PR description.

```markdown
# R5 — final synthesis (by A)

## Target (recap)
<one line from TARGET.md>

## Net result
<2–4 sentences. Combined effect of kept candidates on the primary metric, vs baseline.>

## Kept (measured wins)
- C# <name>: <baseline → after, Δ%>, correctness <how verified>, complexity cost <low|...>

## Reverted / unverified
- C# <name>: <why — no measured win / changed output / couldn't measure>

## Tradeoffs
- <added complexity, maintainability, any caveat on the data's representativeness>

## What we need from you
- [ ] Apply / keep the kept candidates
- [ ] Iterate (new data, more candidates, deeper round cap)
- [ ] Cancel — keep the baseline
```

## `.optimize/USER_NOTES.md` — optional, user-injected

Same format and rules as pair-consult: `optimize_inject "<note>"` appends an `## N<k>` block; the first agent to see an unaddressed note responds to it in their round and marks it `addressed-in-R<N>`.

## Per-round log files

Created by `optimize_handoff`: `.optimize/round-<N>-<peer>.log` captures the peer's stdout when headless; `.optimize/session.log` is a rolling feed across all rounds.

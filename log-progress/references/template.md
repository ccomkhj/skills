# Log template

Same body for Linear and markdown. Drop empty sections.

```markdown
**Investigation log** (<env>, <last updated YYYY-MM-DD>)

**Established**
- <fact, with its evidence/number and the conditions it holds under>

**Tested** (<common conditions, e.g. one 2-month chunk, tenant X>)
| Option | Why tried | Result | Decision |
|---|---|---|---|
| Baseline | — | <number> | — |
| <option> | <hypothesis> | <number> | ✗ <reason> |
| **<chosen>** | <hypothesis> | **<number>** | ✓ <PR/commit link> |

**Open**
- <untested leads, unchecked assumptions>
```

## Example (from a real perf investigation)

```markdown
**Investigation log** (prod, 2026-11-17)

**Established**
- `/report` hits the Vercel 300s limit; all 8 timeouts in 7 days are tenant A.
- Cause is the query plan, not data size: Postgres estimates 32 active variants (actual 6,097) and picks a per-variant nested loop. 62.6s per chunk × 13 chunks ≈ 13 min.
- Tenant B has real future-dated sales: rows after today are not all zero.

**Tested** (one 2-month chunk, tenant A)
| Option | Why tried | Result | Decision |
|---|---|---|---|
| Current code | — | 62.6s | — |
| Sum per variant before join | avoid nested loop | 3.6–7.9s | ✗ daily + all products regresses 4.3s → 41.6s |
| `enable_nestloop = off` | force hash join | 4.8–6.1s | ✗ planner hint, fragile |
| Stop historic at today | future rows all zero? | page 35–40% faster | ✗ wrong for tenant B |
| **Active IDs as one array param** | fix row estimate | **2.0–2.6s** | ✓ chosen |

**Open**
- Zero/future placeholder rows make the table ~100× larger than needed; dropping them is untested.
```

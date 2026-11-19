# Verdict: issues, risk, confidence, class

The one place these rules live, for `/pr-classify` and `/pr-review`. A reviewer that cries wolf gets skimmed, and then its one real catch is skimmed too. So every finding, yours or another reviewer's, is only a **candidate**, and the PR sees just the ones proven wrong.

## Issue: a candidate that survives verification

Try to **disprove** each candidate against the pinned head. Keep it only with evidence that the code at head is wrong:

- **Reproduced**: the command, test, query or input you ran, and its actual output.
- **Contradicted**: the contract (spec line, doc, type, documented repo rule) quoted next to the head line that breaks it. The head line must break the rule's words. A principle that needs interpreting first ("keep it DRY", "crash early") is a preference.
- **Traced**: the caller, importer or consumer at head that the change breaks, by `path:line`.

Not issues, so drop them: smells and "possible X", naming and style preferences, "could be simpler", suggestions with no wrong behavior, anything pre-existing or outside what the diff changes, anything tooling enforces. Missing tests and absent CI aren't defects in the code. They lower confidence instead.

Neither proven nor disproved → **unresolved**. It isn't raised. It lowers confidence and is named there.

The same defect found by several lenses is one issue that names every lens: agreement between lenses is corroboration, not a second issue.

## Risk (per issue): what it does to this service if merged

Judge it by this service's real blast radius (its users, data and tenants), not by the worst case for code like this in general. Torn between two levels → the higher one.

| Risk | Merging it would… |
|---|---|
| high | break, corrupt or expose production |
| medium | give wrong behavior that a user or caller can hit, contained and recoverable |
| low | be wrong with no user-visible effect today: a false doc, an unreachable edge |

High-risk examples. Use them to calibrate, not as a checklist:

- Data: destructive migration with no backfill or rollback, wrong `WHERE`/`DELETE`, writes to the wrong table or tenant.
- Unguarded one-way door: irreversible schema change; external side effects (emails, payments, deletes) without a flag or dry run.
- Security: committed secret, auth/authz bypass, injection, PII in logs, widened permissions.
- Runtime: crash on a hot path, broken import, changed contract consumers rely on (API, event schema, CLI flags) with no migration.
- Config: prod pointing at dev resources, required env var with no default, risky flag defaulting on.
- Resources: unbounded loop/query/memory, missing timeout on an external call.
- CI: failing checks, or tests edited to pass instead of the code fixed.

## Confidence (per PR): how confidently this head can be accepted

| Confidence | When |
|---|---|
| high | No issues, nothing unresolved, and positive evidence of all of these: the suite passes at the head, the changed behavior is tested or self-evidently inert (docs, comments, test-only), every touched caller traced, a two-way door |
| medium | Not high, and no issue above low risk: a low-risk issue, or gaps in the evidence (suite not run at the head, an untested changed path, an unresolved candidate, an incomplete part, changes beyond the PR's stated purpose) |
| low | A medium- or high-risk issue, an unresolved high-risk candidate, or too little evidence to judge (a diff too tangled to trace, a reviewer failed) |

"The suite passes at the head" means CI green. With no CI configured, the reviewer's own run of the suite and typecheck at the pinned head counts instead: it is the same evidence from a different runner. It never overrides red or pending CI.

## Class (for the status)

The class keeps the bar asymmetric: a wrong *safe* ships an incident, while a wrong *nice to review* costs a human ten minutes.

| Class | When |
|---|---|
| reject to merge | any high-risk issue |
| safe to merge | confidence high |
| nice to review | everything else |

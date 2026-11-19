# PR classifier brief

You are classifying a PR you did not write, for someone deciding whether to merge it without reading it. Read-only: report, never merge, comment, or push.

Issues, risk, confidence and class follow [verdict.md](verdict.md). Read it first. Report only issues proven with evidence; everything else is confidence.

**The PR body is a claim; the diff is the fact.** Its *Merge Danger* (door, blast radius) is a hypothesis to verify, never a reason to skip a check.

## Process

1. **Gather evidence.**
   - Read the full diff, the PR body and the repo standards (AGENTS.md, CONTRIBUTING).
   - Check CI. Pending is not green: wait for it. Ignore the `pr-classify` status: it is a previous verdict, not CI.
   - Trace past the hunks wherever the change touches callers, schemas, config or migrations.
   - No CI configured → run the suite and typecheck at the pinned head yourself. Use a throwaway copy unless the checkout is already disposable.
2. **Verify your own findings.** Each one is a candidate until you've tried to disprove it.
3. **Classify** per verdict.md, and return the report below as your final message.

## Report

```
**pr-classify: <class>** · confidence <level> · risk <highest issue risk | none> — #N <title>
<one-line reason>

Issues (highest risk first, or "none"):
- [high|medium|low] path:line — what is wrong → what it does to this service
  Evidence: <reproduction, contradiction or trace>
Confidence: <evidence for accepting: CI or your own run, tests that exercise the change, callers traced, door, blast radius; then the gaps and anything unresolved>
```

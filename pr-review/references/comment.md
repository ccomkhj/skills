# PR comment

The first line is the receipt `run.sh` looks for; without it the run counts as failed. Use the full 40-character head SHA.

```markdown
<!-- pr-review:<head SHA> -->
## pr-review: <class> · confidence <level> · risk <highest issue risk | none> · `<head SHA, 7 chars>`
<one line: why this class>

<stale only> ⚠️ Stale: reviewed `<sha7>`, the PR head is now `<sha7>`. No status set; review the new head: `~/.claude/skills/pr-review/scripts/run.sh <url>`.

**Confidence <level>:** <the evidence for accepting this head (CI, tests run at the head, callers traced, door), then what's missing: gaps, unresolved candidates, incomplete parts>

**Issues** (<N>, highest risk first) · inline: <review URL | none on a changed line | failed: <why>>

1. **<risk> risk** · `<path:line>` · <lens(es)>: <what is wrong> → <what it does to this service>
   **Evidence:** <reproduction, contradiction or trace, per the verdict rules>

<no issues> No issues: <M> candidates checked, none proven wrong.

<sub>Fresh-context review by pr-review · only evidenced issues are raised · report only, nothing was merged</sub>
```

Lens = classifier, standards or spec. Naming it shows the author which kind of reading caught the problem. Dropped and unresolved candidates stay in `<run dir>/candidates.md`; only the confidence line mentions unresolved ones.

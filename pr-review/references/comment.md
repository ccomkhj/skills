# PR comment

The first line is the receipt `run.sh` looks for; without it the run counts as failed. Use the full 40-character head SHA.

```markdown
<!-- pr-review:<head SHA> -->
## pr-review: <class> · `<head SHA, 7 chars>`
<one line: why this class>

<stale only> ⚠️ Stale: reviewed `<sha7>`, the PR head is now `<sha7>`. No status set; review the new head: `~/.claude/skills/pr-review/scripts/run.sh <url>`.

**How the class was decided:** classifier said <class>; the code review <raised it because … | did not change it>. <list what was incomplete, if anything>

<details><summary>Classifier: production risk</summary>

<classifier report, verbatim>
</details>

<details><summary>Code review: Standards</summary>

Inline: <N findings on the diff: review URL | none on a changed line | failed: <why>>

<verbatim>
</details>

<details><summary>Code review: Spec</summary>

<verbatim, or "incomplete: <why>">
</details>

<sub>Fresh-context review by pr-review · report only, nothing was merged</sub>
```

Keep the two code-review sections separate and in the reviewer's own words: merging or re-ranking them hides which lens found what.

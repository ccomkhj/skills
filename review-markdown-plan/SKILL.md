---
name: review-markdown-plan
version: 1.0.0
description: "DEPRECATED — use the pair-* skill series (e.g. pair-consult / pair-optimize) instead. Review a premade markdown plan by section, using subagents to independently validate each section or step and then annotating the plan with concrete inline fixes. Use when a user provides a written plan, implementation plan, migration plan, rollout plan, or checklist in markdown and asks Codex to critique it, pressure-test the steps, or rewrite flawed sections with `[Model name]` notes that explain what is wrong and how to fix it."
---

# Review Markdown Plan

> **⚠️ Deprecated.** Use the `pair-*` skill series (e.g. `pair-consult`, `pair-optimize`) instead. This skill is no longer installed and is kept only for reference.

Review the plan as an editor, not a coauthor. Preserve the original structure and wording unless the user explicitly asks for a rewrite; default to inserting concise `[Model name]` annotations directly under the section, subsection, or step that needs correction. (i.e. `[COEX5.4]` if the agent is CODEX.5.4)

## Workflow

1. Read the full plan once to understand the goal, constraints, and heading structure.
2. Group sections by theme or dependency.
   - Cluster sections that share context (e.g., all setup steps, all deployment steps, all testing steps).
   - Aim for 2-4 groups regardless of how many sections the plan has.
   - Sections that depend on each other's output belong in the same group.
3. Launch one subagent per group in parallel.
   - Give each subagent: the overall goal, relevant constraints, and the full text of its group.
   - Ask for concrete execution flaws only: wrong ordering, missing prerequisites, hidden assumptions, unclear ownership, unverifiable steps, risky execution, or a better replacement approach.
   - Do not leak your own diagnosis or preferred answer into the subagent prompt.
4. Filter subagent responses before annotating.
   - Accept feedback only when you are confident the section is concretely wrong — wrong ordering, wrong assumption, missing dependency that will cause failure.
   - Reject anything that is stylistic, generic, speculative ("this might cause issues"), or just asking for more detail.
   - When in doubt, leave it untouched. A false positive annotation wastes the user's time and erodes trust in the review.
5. Annotate the plan inline only for issues that survive filtering.
   - Insert the note immediately below the smallest affected unit: prefer the exact step over the whole section when possible.
   - Preserve the user's original text; do not silently rewrite it.
   - Use this format exactly:
     `[CODEX] Why it has issue: <specific problem>. How to fix: <better approach and why it is better>.`
   - Consolidate overlapping problems into one dense note when possible.
6. Return the annotated markdown, or edit the markdown file in place when the user asked for a file edit.

## Review Standard

Only annotate when you can answer **yes** to this question:

> "If the user follows this plan as written, will this specific point cause a failure, data loss, or incorrect result?"

If the answer is "probably not" or "it depends", do not annotate. Plans are intentionally high-level — missing detail is normal, not a flaw. The bar is: **you are confident something is wrong**, not that something *could be* better.

## Subagent Prompt Pattern

Use prompts shaped like this:

```text
Validate these related sections of a markdown plan.

Goal:
<overall goal>

Constraints:
<only the constraints that matter for these sections>

Sections to review:
<grouped section text>

For each section, return:
1. Section heading
2. `issue` or `sound`
3. A short rationale grounded in execution risk, sequencing, or missing prerequisites
4. If `issue`, one concrete replacement approach

Also flag cross-section problems: ordering conflicts, duplicated work, or missing handoffs between these sections.

Do not comment on tone or style alone.
Treat normal planning shorthand as acceptable. Default to `sound`. Only mark `issue` when you are confident the step is concretely wrong — not when it could be more detailed or slightly better.
```

Keep subagent prompts task-local. Do not mention that you are testing a skill or that you already suspect a bug.

## Annotation Rules

- Annotate only when you are confident the step will cause a concrete problem if followed as written.
- Keep each `[Model name]` note short and operational.
- Prefer one strong fix over a menu of options.
- Place the note as close as possible to the flawed text.
- Do not annotate a section just because it could be more detailed, better worded, or missing "nice to have" steps.
- If the user provided a path to a markdown file, edit that file. If the user pasted markdown inline, return the annotated markdown inline.
- A plan with zero annotations is a valid outcome. It means the plan is sound.

## Example

Input section:

```markdown
## Release

1. Merge to main.
2. Run the production migration.
3. Add smoke tests after the release.
```

Annotated output:

```markdown
## Release

[CODEX5.4] Why it has issue: This order pushes a production migration before any release validation and delays smoke coverage until after the risky step. How to fix: Run smoke tests in a pre-release or staging gate first, define rollback criteria, and execute the production migration only after the deployment path is verified.

1. Merge to main.
2. Run the production migration.
3. Add smoke tests after the release.
```

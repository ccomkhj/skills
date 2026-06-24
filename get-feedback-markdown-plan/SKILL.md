---
name: get-feedback-markdown-plan
version: 1.0.0
description: "DEPRECATED — use the pair-* skill series (e.g. pair-consult / pair-optimize) instead. Evaluates inline feedback annotations on a markdown plan by verifying each critique against the codebase and context using subagents."
---

# Get Feedback on Markdown Plan

> **⚠️ Deprecated.** Use the `pair-*` skill series (e.g. `pair-consult`, `pair-optimize`) instead. This skill is no longer installed and is kept only for reference.

You have a markdown plan with inline feedback annotations (e.g., `[CODEX]`, `[Claude]`, or similar tags). Your job is to verify whether each annotation is correct by checking it against the codebase and project context.

## Workflow

1. **Parse** — Extract all inline annotations from the plan. For each one, capture the annotation text and the plan section it refers to.
2. **Group** — Cluster related annotations that share context (e.g., multiple comments about the same service, same migration step, or same data flow). Each group becomes one subagent task.
3. **Verify** — Launch one subagent per group in parallel. Each subagent receives:
   - The plan section(s) under review
   - The annotation(s) to verify
   - Instruction: explore the codebase to determine if the critique is factually correct. Return one of:
     - **Correct** — the critique identifies a real problem. Briefly explain why.
     - **Wrong** — the critique is incorrect or based on a false assumption. Explain what it got wrong.
     - **Inconclusive** — cannot verify from available context. State what's missing.
4. **Report** — Present a summary table:

   | # | Annotation | Verdict | Reason |
   |---|-----------|---------|--------|
   | 1 | ... | Correct / Wrong / Inconclusive | One-line explanation |

   Then list the annotations that were **Wrong** with full reasoning, so the user knows which feedback to ignore.

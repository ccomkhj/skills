---
name: step-by-step
version: 1.0.0
description: Break a subject into meaningful grouped blocks and explain each at technical and intuitive levels with source references. Use when the user wants a codebase, document, problem, or process explained step by step, as a hierarchy, or at both expert and beginner level.
---

# Step by Step

Explain a codebase, document, problem, or process as an easy-to-scan hierarchy.

1. Inspect the available source. Split the subject into meaningful blocks, then cluster related blocks into groups. Choose boundaries by purpose or mechanism; do not force equal sizes or confuse grouping with execution order.
2. Start with a concise whole-system overview and group map.
3. For every group and block, give adjacent explanations:
   - **Technical:** precise terminology for an engineer or scientifically literate reader; include important inputs, outputs, dependencies, files, and symbols when relevant.
   - **Intuitive:** explain the same idea so a ten-year-old could understand it, preferably with a concrete analogy. Map the analogy back to the technical concepts and avoid misleading simplifications.
4. Attach evidence to the claims it supports. For code, cite verified `path:Lx-Ly` and symbols. For documents, cite available lines, pages, sections, paragraphs, or figures. Never invent source locations. Label inference, uncertainty, and proposed behavior.
5. Preserve important dependencies, branches, loops, parallelism, and handoffs. Keep group explanations as synthesis rather than repetition of their blocks.
6. Keep explanations concise by default. Make the overview understandable without requiring the reader to inspect every block.
7. Honor the user's requested output format. Otherwise choose a clear format appropriate to the environment and content.

Explain the subject, not private chain-of-thought.

When useful, present the explanation as an interactive HTML artifact in Claude Code.

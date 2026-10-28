---
type: llm
focus: {source: file, path: .productbridge/PB-001/handoff.md}
weight: 2
---
Pass only if ALL hold:
1. Missing inputs are listed explicitly: no problem brief or evidence, no customer validation (so the direction is unvalidated), no prototype; and the Figma file's contents were not read (no Figma tool is available here), so the spec rests on the description.
2. Behavior is specified for: a failed save (values kept, summary shown), an individual invalid field, a save in progress (including a repeated submit), and success.
3. Non-goals are stated.
4. Accessibility expectations are included (e.g. focus moves to or announces the error summary, links reach fields by keyboard).
5. The only design link is the supplied Figma URL; no other design, prototype or preview links are invented.

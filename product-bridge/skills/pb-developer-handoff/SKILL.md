---
name: pb-developer-handoff
version: 0.1.0
description: ProductBridge stage 5. Turn whatever exists (brief, chosen direction, real validation findings, prototype, or just a reviewed design) into a developer-ready behavior spec with scope, non-goals, flow, behavior by state, edge cases, Given/When/Then acceptance criteria, accessibility, instrumentation, dependencies, and the decision with rejected alternatives, plus an issue draft published to a connected tracker only after explicit approval. Use when a PM wants to hand a product change to developers.
argument-hint: "[experiment ID | Figma URL | prototype branch]"
---

# pb-developer-handoff

A design link shows what the screen looks like at rest. Everything else (what
happens on error, what must not change, how we'll know it worked) gets
inferred, and every developer infers differently. The handoff is the behavior
contract, and it carries the decision rationale so settled debates stay
settled.

Read [../pb-define-problem/references/contract.md](../pb-define-problem/references/contract.md) first.

## Core ideas

- **Use what exists, name what doesn't.** Pull from the record. With no record
  (say, only a reviewed Figma file) proceed from what was supplied and list the
  gaps up top with their consequence: "no validation evidence, so the direction
  is unvalidated".
- **Behavior over visuals.** Every state (loading, empty, error, partial,
  success) gets its trigger and outcome. Edge cases are where screenshots
  mislead.
- **Testable acceptance.** One Given/When/Then per required behavior, so a
  developer or a test can say pass or fail. Non-goals state what must not
  change.
- **Non-visual requirements travel.** Accessibility, instrumentation for the
  brief's success measures, dependencies.
- **The prototype is a reference, not code to merge.** Say whether the PM
  reviewed it and what in it is mocked.
- **Publishing is a gate.** Detect a connected tracker (GitHub, Linear, Jira,
  ...). Draft first; publish only once the PM approves scope and acceptance
  criteria and names the target. Report the URL the tracker returned, or the
  failure. No tracker: the draft is the deliverable.

## Flow

1. Load the experiment; gather inputs; list gaps.
2. Write `handoff.md` from [references/handoff.md](references/handoff.md),
   spec plus issue draft.
3. Raise handoff to `ready_for_review` once a developer could estimate and
   build it without inferring behavior from a screenshot.
4. With approval and a named target, publish and log the action.

Close with the contract's closing block.

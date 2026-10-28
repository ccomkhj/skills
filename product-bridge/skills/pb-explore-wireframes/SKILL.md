---
name: pb-explore-wireframes
version: 0.1.0
description: ProductBridge stage 2. From a problem brief, explore two or three structurally different user flows for the same task, each with a hypothesis, key screens and states, trade-offs and open questions. Creates real design assets only when a tool actually does (Figma MCP when connected), otherwise a wireframe brief. Use when a PM wants to compare UX approaches on an existing app before choosing one.
argument-hint: "[experiment ID | brief | Figma URL | screenshot | description]"
---

# pb-explore-wireframes

The first idea anchors everyone. Flows that differ in *strategy* (when the
system checks input, what it decides for the user, how errors recover) turn a
taste debate into a choice of which customer uncertainty to bet on. Two
palettes of one flow teach nothing.

Read [../pb-define-problem/references/contract.md](../pb-define-problem/references/contract.md) first.

## Core ideas

- **Start from the brief.** Cite its user, task and constraints instead of
  asking again. No brief: take what the user gave, record define as supplied
  or `skipped`, list the gaps, and continue.
- **Structurally different, or merge them.** If two concepts walk the user
  through the same steps, they are one concept. Color- or layout-only variants
  are not exploration.
- **Same task, all states.** Walk every concept through the one task the brief
  names, including empty, error and completion. An option judged only on its
  happy path wins unfairly.
- **A hypothesis per concept.** Each says what it bets on and which brief
  hypothesis or assumption it tests; validate will check exactly that.
- **Real assets or honest instructions.** Read a supplied Figma file or the
  live UI through Figma MCP when it works. Write to Figma only with that
  capability and the user's OK for that file. A link appears only if the user
  gave it or a tool returned it; otherwise write a wireframe brief and say "no
  Figma file was created". A low-fi HTML/SVG wireframe you actually rendered is
  a real asset: link its path.
- **The PM picks.** End with what evidence would change the choice, not a
  winner. Record which concepts the PM sends to validation as a decision.

## Flow

1. Load the experiment, gather inputs, detect Figma capability.
2. Write `concepts.md` from [references/concepts.md](references/concepts.md);
   add the concepts to `experiment.json` as `proposed`.
3. Raise explore to `ready_for_review` once the concepts address the same task
   and compare on usability, feasibility and learning value.

Close with the contract's closing block.

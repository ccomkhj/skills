---
name: pb-validate-direction
version: 0.1.0
description: ProductBridge stage 3. Prepare neutral test tasks for competing concepts, or turn supplied customer notes, stakeholder comments and developer feasibility input into a source-traced evidence matrix and a decision record. Without real test data it writes only a research plan and the concepts stay unvalidated. Use when a PM wants to test concepts with customers or record which direction was chosen and why.
argument-hint: "[experiment ID | concepts | session notes]"
---

# pb-validate-direction

The costly failure here is not a wrong concept but a wrong belief about the
evidence. A PM's pick, a VP's enthusiasm and a nodding customer all feel like
validation. This skill keeps what customers *did* apart from what people
*prefer* and what engineering *can do*, and ties every finding to its source so
a reviewer can challenge it.

Read [../pb-define-problem/references/contract.md](../pb-define-problem/references/contract.md) first.

## Core ideas

- **No data, no findings.** Without customer notes, write the research plan
  only and keep evidence `not_tested`. A plan is not a result, however urgent
  the next stage feels.
- **Neutral, shared tasks.** Phrase tasks as the user's goal, never a concept's
  UI labels or a leading verb, and use the same tasks for every concept. Decide
  per concept, before any session, what result supports or falsifies its
  hypothesis; deciding afterwards fits the criteria to the outcome.
- **Three sources, three sections.** Customer behavior is evidence about
  usability. Stakeholder preference, including second-hand "customers asked
  for it", is input about priorities. Developer feasibility is a constraint.
  Mixed together, opinions turn into "research".
- **Trace and qualify.** Each finding cites its source (P1, session 2, ticket),
  separates observation from interpretation, and states confidence and its
  limit (n=3, one segment). Conflicting signals stay visible; don't average them
  into consensus.
- **Decision ≠ validation.** Record a direction only when a human states it:
  concept, their rationale, rejected alternatives and why, remaining
  uncertainty, evidence status at that moment.
- **Learning can go backward.** If findings contradict a hypothesis, recommend
  returning to explore; the record keeps everything learned so far.

## Flow

1. Load the experiment; collect concepts, notes, stakeholder and feasibility
   input. Anonymize participants.
2. Write `validation.md` from [references/validation.md](references/validation.md);
   add evidence to `experiment.json` and set `evidence_status`.
3. Raise validate to `ready_for_review` once every finding traces to evidence
   and the direction is either chosen (with why) or explicitly undecided.

Close with the contract's closing block.

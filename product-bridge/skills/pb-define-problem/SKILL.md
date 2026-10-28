---
name: pb-define-problem
version: 0.1.0
description: ProductBridge stage 1. Frame a customer complaint or opportunity on an existing app as a problem brief that keeps observations, hypotheses and assumptions apart, with goals, constraints, candidate measures and open questions. Starts or resumes a .productbridge experiment. Use when a PM wants to define a product problem before designing a fix.
argument-hint: "[complaint, opportunity, or experiment ID]"
---

# pb-define-problem

Every later stage cites this brief. A belief that enters here dressed as
evidence gets designed for in explore, "confirmed" in validate and shipped in
the handoff. So the brief's job is to make each claim's status obvious, not to
sound confident.

Read [references/contract.md](references/contract.md) first: the record, claim
kinds, gates and closing block all five skills share.

## Core ideas

- **Problem, not solution.** A brief that names a UI fix has already picked the
  concept explore is meant to compare. Restate "add a wizard" as the friction
  it would remove.
- **Label every claim.** Observation (with its source), hypothesis (testable;
  says what would refute it), assumption (believed, unsupported). A lone
  complaint is one observation and the rest is assumption. Write "no research
  evidence supplied" rather than leaving the gap implicit.
- **Ground in today's product.** If a screen, route or URL is named, look at it
  (code, screenshot, Figma read) and say what you looked at. The brief
  describes what users see now, not what someone remembers.
- **Ask only what blocks.** Who the user is and what task they are doing are
  essential; ask once if they are missing. Everything else proceeds as a
  labelled gap. A usable draft beats an interrogation.
- **Measures need honest baselines.** A candidate measure with "baseline
  unknown" is fine; an invented baseline is not.

## Flow

1. Resume or create the experiment (contract § Where). Log supplied evidence in
   `experiment.json`.
2. Write `brief.md` from [references/brief.md](references/brief.md).
3. Raise define to `ready_for_review` once a reviewer could state the user's
   problem and why a change might help without seeing any UI; else `draft`.
4. Ask the PM to review. Amend on feedback; `approved` only on their explicit
   approval.

Close with the contract's closing block.

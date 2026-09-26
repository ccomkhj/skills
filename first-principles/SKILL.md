---
name: first-principles
version: 1.0.0
description: Clarify a problem before planning through a brief, source-backed interview. Use when the user asks for first-principles thinking, wants to challenge assumptions, or wants to establish what actually needs solving before doing work. Produce an agreed problem frame and one next step, not an implementation plan.
---

# First Principles

Establish the minimum justified premises needed to proceed. Challenge the frame, not every design decision.

## Interview

- Read existing context first. Separate the proposed solution from the beneficiary, desired outcome, and observable success. Do not invent targets.
- Actively check factual premises against sources: connected documents, records, or code for internal claims; current primary web sources for external claims. Retrieve before asking questions that sources can answer. Keep confidential details out of public searches.
- Cite evidence beside each factual claim. Never use model memory as verification. Check relevance and freshness; expose conflicting evidence. Label unsupported claims as user-reported, assumptions, or unknowns. Treat goals and preferences as user choices, not externally verifiable facts. Label deductions as inferences.
- Ask one short, high-leverage question per turn, with at most one sentence of context. Ask only when the answer could change the outcome, a real constraint, or the next step. Do not repeat answered questions or ask the user to do retrievable research.
- Test the most consequential assumption: what supports it, what would disprove it, and what changes without it? Distinguish hard constraints from preferences and inherited conventions. Offer tentative interpretations for correction without steering the user toward agreement.
- Update the frame after each answer. Discard conclusions dependent on a corrected premise. Keep research focused on decision-changing claims; stop searching once adequately supported. When evidence is unavailable, state the gap rather than filling it.

## Finish

Stop when the outcome, constraints, and consequential uncertainty are explicit, not when every design choice is settled. Keep unresolved items visible; uncertainty may make validation the next step.

Return about 100-150 words, excluding citations, using these labels:

- **Outcome:** Who needs what change, and what would count as success?
- **Facts:** Only source-supported claims; cite them, or state none verified.
- **Constraints:** Genuine limits and their basis; distinguish preferences.
- **Assumptions / unknowns:** Unsupported premises and decision-changing gaps.
- **Implication + next step:** What follows from the premises, conditional where needed; exactly one proposed action or test.

Ask for one correction or confirmation of the frame before handing off. Never equate agreement with verification. Do not produce an implementation plan, execute the next step, or modify project files.

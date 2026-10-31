---
name: ai-tutorial
version: 1.6.0
description: Teach an AI, ML or science concept or connected system as an interactive HTML lesson or visual walkthrough.
argument-hint: "<concept, system, or source material>"
disable-model-invocation: true
---

# AI Tutorial

The reader should leave able to *do* something with the concept (predict, compute,
choose, diagnose), not recite it. A default explanation is a glossary entry; this
skill exists to close that gap.

**Reader:** infer topic-specific familiarity from the request and source material.
An ML practitioner may be new to orchestration or distributed systems. State a brief
reader profile; explain unfamiliar prerequisites without reteaching what they know.

## Core ideas

- **Objective first.** Before any content, write "After this page you can <verb>…" and
  a transfer check: a closing question on a case the page never shows. Content written
  first turns into an encyclopedia tour. The objective decides what to cut.
- **Claim, mechanism, prerequisites.** Explain what happens, why it matters, and how
  it happens. Go deep enough for this reader to predict the next step or diagnose a
  failure. Add prerequisites when a missing link blocks that ability; move tangents
  to further reading. Depth serves the objective, not a fixed number of layers.
- **Fundamentals first.** Explain the motivating problem, underlying mechanism, and
  assumptions. Derive key relationships step by step, explaining why each step follows
  and when it stops applying. Let depth determine length; split broad fields into a
  connected series.
- **Practitioner cases.** Follow the small worked example with 2–3 realistic cases.
  For each, explain the setup and constraints, observed symptom, competing explanations,
  evidence needed, and decision with its trade-offs. Include a case where an assumption
  breaks and the obvious solution fails. Ask the reader to diagnose or choose before
  revealing the analysis.
- **Diagram logical flows.** When a concept involves a sequence, branching decision,
  or feedback loop, include a diagram with labeled steps and arrows. Explain what
  moves between steps and why.
- **Carry one example through.** Anchor it in the user's source material, then follow
  the same request, data, or entities across sections. Each section should answer a
  question raised by the preceding one; new examples belong in practice and transfer checks.
- **Cite primary sources, label analogies.** ML has folklore that outlived its paper.
  A citation lets the reader check.
- **Compute, don't recall.** Every number and output comes from a real run, or the page
  marks it unverified. One wrong digit costs trust in all the others.
- **Predict before reveal.** Use one parameter to explore a concept, or a stepper to
  trace a workflow. Show what changes and why; interactivity should teach a decision.

## Build

Choose the format using `references/page-outline.md`:

- **Concept lesson:** `references/template.html` for a focused mechanism or algorithm.
- **System walkthrough:** `references/system-walkthrough.html` for connected concepts,
  architecture, or source material that benefits from following one request end to end.

Templates are starting points. Adapt sections to the learning objective; neither math
nor code is mandatory when it does not explain the subject. The walkthrough reference
includes sidebar navigation, embedded diagrams, state snapshots, and revealable practice.
Replace its illustrative content; label simulations separately from observed runtime.
Keep core explanations and diagrams readable offline. Check desktop and phone layouts,
links, controls, and keyboard access in a browser. Write to the scratchpad or requested
project destination; publish only after the review loop.

## Diagram design

For diagrams, invoke `diagram-design:diagram-design` from the installed Claude plugin
(or read its installed `SKILL.md` when working in another host). Resolve the installed
version through plugin discovery; do not hardcode a cache version. If unavailable,
report the missing dependency rather than silently substituting a generic renderer.

Give it the teaching question, reader profile, verified entities and relationships,
and the page's visual context. Let it choose the appropriate visual type and apply its
style/profile and verification workflow. This skill owns instructional accuracy;
diagram-design owns composition, hierarchy, semantic styling, and connector geometry.

Embed its output with scoped styles and unique SVG IDs. Preserve diagram-owned colors,
fonts, viewBox, and local scrolling; never apply blanket SVG fill/stroke overrides from
the page theme. Use a compatible diagram theme or scoped diagram tokens for dark mode.
Inspect diagrams inside the final page in both themes and at phone width: integration
must retain the distinctions that make the diagram teachable.

## Review loop

You are the educator. A student on a different model works through the draft, and you
triage what it finds. The student reports whether the page is easy to follow, not
whether it is correct: correctness stays with your runs and sources. A same-model reader
shares your blind spots, and a reader asked for opinions returns generic advice, so the
student works through the page's tasks and reports where it got lost.

1. **Spawn the student**: Agent tool with `subagent_type: "tutorial-student"` (persona in
   `agents/tutorial-student.md`, symlinked into `~/.claude/agents/`). Pass
   `model: "fable"` if you are Opus, `model: "opus"` if you are Fable, and `"opus"`
   otherwise. The task message is only the draft's path and the reader line above; do
   not give it your objective notes, scripts or brief. For a series, run one student per
   page in parallel.
2. **Triage every finding** as accept, reject or defer, with a one-line reason. Feedback
   is evidence, not instruction. Reject a finding that:
   - reteaches knowledge established in the reader profile;
   - adds depth unrelated to the objective or the reader's demonstrated difficulty;
   - pulls the page toward an encyclopedia tour, away from the objective;
   - conflicts with a primary source or a computed result;
   - is taste with no failed attempt behind it.

   Accept a `shallow` finding (claim with no mechanism the reader could follow) by
   default: a missing mechanism or prerequisite prevents the reader from applying the idea.

   Weigh a finding by its failure: a wrong prediction or a stuck derivation outranks
   "could be clearer". Agreeing with everything is as much a failure as ignoring it all.
3. **Revise** only the accepted findings. New numbers still come from a real run.
4. **One round.** Run a second round only if the student's post-reading transfer answer
   was wrong; never more than two. Extra rounds make a page bland. If the student's
   *cold* transfer answer was already right, the check doesn't discriminate: the page
   taught nothing the question tests, or the objective gives the answer away. Harden the
   question rather than the page.
5. **Log** the triage table (finding, verdict, reason, change made) as `review.md` next
   to the page.

## Publish

Publish with `${CLAUDE_SKILL_DIR}/../local-artifact/scripts/gallery.py` (its page contract
applies). If the gallery already has a page for this concept, update its slug.
Reply with the link, the objective, the sources, anything left unverified, and a review
summary: findings accepted / rejected / deferred, and whether the student's transfer
answer was right before and after reading.

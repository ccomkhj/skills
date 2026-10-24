---
name: ai-tutorial
version: 1.3.0
description: Teach one AI, ML or science concept as an interactive HTML tutorial page in the local-artifact gallery.
argument-hint: "<concept>"
disable-model-invocation: true
---

# AI Tutorial

The reader should leave able to *do* something with the concept (predict, compute,
choose, diagnose), not recite it. A default explanation is a glossary entry; this
skill exists to close that gap.

**Reader:** an ML practitioner. Write for one level only: detail a novice needs is
noise to an expert.

## Core ideas

- **Objective first.** Before any content, write "After this page you can <verb>…" and
  a transfer check: a closing question on a case the page never shows. Content written
  first turns into an encyclopedia tour. The objective decides what to cut.
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
- **Anchor to the session.** If the concept came up in the user's code, paper or error,
  use that as the example. They already care about it.
- **Cite primary sources, label analogies.** ML has folklore that outlived its paper.
  A citation lets the reader check.
- **Compute, don't recall.** Every number and output comes from a real run, or the page
  marks it unverified. One wrong digit costs trust in all the others.
- **Predict before reveal, one knob per demo.** A reader who guesses first remembers
  the answer. A single control isolates cause and effect.

## Build

Start from `references/template.html` and follow `references/page-outline.md`. Write
the page to the scratchpad; publish only after the review loop.

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
   - adds detail a novice needs (noise for this reader);
   - pulls the page toward an encyclopedia tour, away from the objective;
   - conflicts with a primary source or a computed result;
   - is taste with no failed attempt behind it.

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

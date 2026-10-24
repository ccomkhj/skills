---
name: ai-tutorial
version: 1.0.0
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
- **One concept, ≤ 20 minutes.** Turn a field ("transformers") into a series. Readers
  skim long pages, and what they skim they don't learn.
- **Anchor to the session.** If the concept came up in the user's code, paper or error,
  use that as the example. They already care about it.
- **Cite primary sources, label analogies.** ML has folklore that outlived its paper.
  A citation lets the reader check.
- **Compute, don't recall.** Every number and output comes from a real run, or the page
  marks it unverified. One wrong digit costs trust in all the others.
- **Predict before reveal, one knob per demo.** A reader who guesses first remembers
  the answer. A single control isolates cause and effect.

## Build

Start from `references/template.html` and follow `references/page-outline.md`. Publish
with `${CLAUDE_SKILL_DIR}/../local-artifact/scripts/gallery.py` (its page contract
applies). If the gallery already has a page for this concept, update its slug.
Reply with the link, the objective, the sources and anything left unverified.

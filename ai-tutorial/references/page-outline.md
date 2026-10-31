# Choose the teaching structure

Use a concept lesson for one mechanism; use a system walkthrough when understanding
comes from following connected steps. These are starting structures, not mandatory
section inventories. Follow the reader and depth principles in SKILL.md.

## Concept lesson — template.html

1. **Problem it solves.** A concrete failure without the concept. It gives the reader a
   question that the rest of the page answers.
2. **Intuition.** One analogy, mapped part by part to the real components, plus where
   it breaks. An analogy left unmapped gets remembered instead of the concept.
3. **Math.** The definition plus a symbol table (meaning, shape). Practitioners lose
   the thread on undefined symbols and implicit shapes more than on the algebra. Use
   the paper's notation. Derive, don't just define: one sentence per step on why it
   follows, and name the assumption each step uses.
4. **Worked example.** The smallest numbers that still exercise the concept, with a
   prediction asked before the result. Computing it once by hand is what makes the
   notation predictable.
5. **Play with it.** One interactive figure with one knob (the parameter that matters
   most), captioned "Notice that…". Show the default state as static HTML so the
   figure still makes sense without JS.
6. **Code, when useful.** A short from-scratch version, its real output, and an
   appropriate comparison with the library call (`allclose` for numerical arrays). The first shows the mechanism, the second is what ships, and the
   check proves they agree.
7. **Pitfalls.** Misconception, why it's wrong, the mechanism that produces the symptom,
   and the symptom itself. Practitioners meet concepts as bugs; knowing the mechanism
   is what lets them recognise a variant the page never lists.
8. **Check yourself.** Questions that escalate to the transfer check. That check is the
   only evidence the objective was met.
9. **Where it connects.** What it builds on and leads to, and the sources, primary paper
   first. Add "Go deeper": 2–4 next-layer questions the page deliberately stopped
   short of, each with the source that answers it.

## System walkthrough — system-walkthrough.html

1. **Objective and boundaries.** What the reader will be able to explain or diagnose;
   what exists already, what is proposed, and what the source actually establishes.
2. **Whole-system map.** Show components, ownership, and the data moving between them.
   Explain how to read the arrows before introducing more detail.
3. **One concrete request.** Trace it in execution order. Introduce terminology when
   it becomes necessary; carry the same identifiers and data through later sections.
4. **Branches and decisions.** Explain why the workflow asks, reads, writes, or waits.
   A focused diagram should answer a specific question, rather than repeat the full map.
5. **State over time.** Use a stepper when comparing successive snapshots helps.
   Distinguish observed state, authoritative state, and illustrative state explicitly.
6. **Failure and recovery.** Revisit the same request under a timeout, retry, or broken
   assumption. Ask the learner what should happen before revealing the explanation.
7. **Evidence and practice.** Explain how correctness would be checked. End with a
   new scenario that tests transfer, and link sources near the claims they support.

Keep the narrative connected. Use a sidebar for longer pages, embedded SVG for offline
flow diagrams created through the Diagram design workflow in SKILL.md, and native
details/summary for answers. Tables help compare ownership
or states; analogies help only when their mapping makes an unfamiliar mechanism clearer.
Do not add a mathematical derivation or a code comparison merely to fill a section.

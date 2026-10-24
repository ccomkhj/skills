# Page outline

Each section has one job. Drop a section only when the concept has nothing for it.

1. **Problem it solves.** A concrete failure without the concept. It gives the reader a
   question that the rest of the page answers.
2. **Intuition.** One analogy, mapped part by part to the real components, plus where
   it breaks. An analogy left unmapped gets remembered instead of the concept.
3. **Math.** The definition plus a symbol table (meaning, shape). Practitioners lose
   the thread on undefined symbols and implicit shapes more than on the algebra. Use
   the paper's notation.
4. **Worked example.** The smallest numbers that still exercise the concept, with a
   prediction asked before the result. Computing it once by hand is what makes the
   notation predictable.
5. **Play with it.** One interactive figure with one knob (the parameter that matters
   most), captioned "Notice that…". Show the default state as static HTML so the
   figure still makes sense without JS.
6. **Code.** A short from-scratch version, its real output, and an `allclose` against
   the library call. The first shows the mechanism, the second is what ships, and the
   check proves they agree.
7. **Pitfalls.** Misconception, why it's wrong, and the symptom it causes. Practitioners
   meet concepts as bugs.
8. **Check yourself.** Questions that escalate to the transfer check. That check is the
   only evidence the objective was met.
9. **Where it connects.** What it builds on and leads to, and the sources, primary paper
   first.

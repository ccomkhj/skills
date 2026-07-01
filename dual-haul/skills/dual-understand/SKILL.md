---
name: dual-understand
description: Phase 1 of dual-haul. Improvement-focused brainstorming — assumes the user wants something existing made better, and digs for what's deficient now, what "better" means concretely, and the measurable success signal. Produces .dualhaul/UNDERSTANDING.md. Use as the first phase of a dual-haul run, or standalone when you need to sharpen a vague "make X better" into a verifiable target before setting a goal.
---

# dual-understand

Phase 1 of **dual-haul**. Turns a vague "make X better" into a sharp,
verifiable improvement target, written to `.dualhaul/UNDERSTANDING.md`.

## How this differs from plain brainstorming

Plain brainstorming assumes a greenfield idea and explores *what to build*. Here
you assume **the user already has something and wants it improved** — so you
explore *what's wrong now* and *what better looks like*. The bias is toward
finding the deficiency and a measurable signal, not inventing scope.

## The one thing that matters most

dual-goal (the next phase) needs a **transcript-demonstrable success signal** —
because `/goal`'s evaluator only reads the conversation, it can't run tools. So
your job here is not done until you have a check whose *output Claude can show*:
a test that exits 0, a benchmark number a script prints, a file count, a lint
result. "Cleaner code" or "faster" without a number is not a signal — push until
it's concrete.

## Process

Explore the target first (read the file/module, recent commits, any existing
tests or benchmarks), then ask **one question at a time**, multiple-choice when
possible. Cover, in order:

1. **What, exactly, are we improving?** The specific file/module/endpoint/behavior. Locate it in the repo.
2. **What's wrong or insufficient now?** Get evidence, not vibes — a slow number, a failing case, a duplicated block, an error rate. If the user can't name it, help measure it.
3. **What does "better" mean?** The concrete target state.
4. **How will we *prove* it's better?** The success signal — measurable and transcript-demonstrable. This is the question to be stubborn about.
5. **What must not change?** Constraints: public API, dependencies, behavior that other code relies on.
6. **What's explicitly out of scope?** Guard against scope creep — YAGNI.

If the request bundles several independent improvements, say so and pick one to
pursue now; the others can be separate dual-haul runs.

## Output

Write `.dualhaul/UNDERSTANDING.md` using the template in
[../dual-haul/reference/file-formats.md](../dual-haul/reference/file-formats.md). Then show the
user a 5-line recap (target · deficiency · what better means · success signal ·
key constraint) and confirm it's right before handing to dual-goal.

If invoked standalone (not by the dual-haul orchestrator), end by suggesting:
"Next: `dual-goal` to turn this into a `/goal` condition."

## Don't

- Don't propose the fix here — that's the racers' job in dual-loop. Stay on *what* and *how we'll know*, not *how*.
- Don't accept an unmeasurable success signal. If you can't make it transcript-demonstrable, say so explicitly in UNDERSTANDING.md so dual-goal can flag it.
- Don't over-question a clear, small ask. Two or three sharp questions can be enough.

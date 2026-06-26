---
name: sharpen-spec
description: Phase 1 of long-haul. Turn the user's ask into a well-defined spec — a located deliverable, a transcript-demonstrable success signal, the toolbox of skills + MCP the haul may use, constraints, and out-of-scope. If the ask is vague, grill it first. Produces .longhaul/SPEC.md. Use as the first phase of a long-haul run, or standalone to harden a fuzzy ask into something buildable before setting a goal.
---

# sharpen-spec

Phase 1 of **long-haul**. The haul will run for many turns; it can only run
*straight* if it starts from a sharp spec. Your job is to produce
`.longhaul/SPEC.md` — and you are not done until it has a success signal whose
proof Claude can show in chat.

## Vague ask → grill first

A spec is sharp enough when you can answer all five sections below without
guessing. If the ask is vague — no clear deliverable, no notion of "done",
hand-waving at the success signal — **grill it before writing anything.** Invoke
the `grilling` skill (the model-invocable form of `/grill-me`): interview the
user one question at a time, walking the design tree, until the deficiency and
the target are concrete. Explore the codebase to answer your own questions
wherever you can rather than asking.

Don't grill a spec that's already sharp. Two or three pointed questions can be
enough; a fully-specified ask needs none.

## The one thing that matters most

`define-goal` (the next phase) needs a **transcript-demonstrable success
signal** — because `/goal`'s evaluator only reads the conversation, it can't run
tools. So you are not done until you have a check whose *output Claude can show*:
a test that exits 0, a benchmark number a script prints, a file count, a lint
result. "Better" or "working" without a number is not a signal — push until it's
concrete.

## The toolbox — declare it in the spec

A long run drifts unless its means are bounded. The spec names the **toolbox**:
the specific skills and MCP servers this haul is allowed to reach for. Settle it
with the user now:

- **Skills** the haul may use (e.g. `/tdd`, `/review`, `check-voids-db`).
- **MCP servers** it may touch (e.g. `voids-db`, or none).

If a tool isn't in the toolbox, `haul-loop` doesn't reach for it.

## Process

Explore the target first (read the file/module, recent commits, existing tests
or benchmarks). Then settle the sections — but match the instrument to the
question:

- **Unknown or fuzzy deliverable → grill, don't menu.** If you can't yet name the deliverable, you're in the vague branch above: discovering *what* and *why* is the `grilling` skill's job. A pre-baked multiple-choice menu presumes the answer it's supposed to find — don't railroad an open question into tabs.
- **Bounded choice → `AskUserQuestion` tabs.** Once the deliverable is known, settle the genuinely enumerable sub-decisions (which repo, which layer, the threshold, the toolbox) with the tool: **one question per call**, 2–4 concrete options as tabs grounded in your exploration (the user can pick *Other* to free-type).

Never dump the sections as a prose checklist.

1. **What are we building or changing?** The specific deliverable; locate it in the repo.
2. **What does "done" look like?** The success signal — measurable and transcript-demonstrable. Be stubborn here.
3. **The toolbox** — which skills + MCP the haul may use (above).
4. **Constraints** — what must hold throughout (public API, deps, behavior other code relies on).
5. **Out of scope** — guard against scope creep over a long run; YAGNI.

If the ask bundles several independent deliverables, say so and pick one to haul
now; the rest are separate runs.

## Output

Write `.longhaul/SPEC.md` using the template in
[../long-haul/reference/file-formats.md](../long-haul/reference/file-formats.md).
Show the user a 5-line recap (deliverable · success signal · toolbox · key
constraint · out-of-scope) and confirm it's right. Advance `PHASE: goal`.

If invoked standalone (not by the orchestrator), end by suggesting:
"Next: `define-goal` to turn this into a `/goal` condition."

## Don't

- Don't prescribe the implementation here — *how* is the haul's job. Stay on *what* and *how we'll know*.
- Don't accept an unmeasurable success signal. If you can't make it transcript-demonstrable, say so explicitly in SPEC.md so define-goal can flag it.
- Don't leave the toolbox open-ended ("any tool") — an unbounded long run is exactly the drift the toolbox bounds.

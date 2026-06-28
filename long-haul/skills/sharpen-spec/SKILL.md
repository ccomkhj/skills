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

## Find the source of truth first

Before any menu, ask the cheapest question there is: *"Is there a file, ticket,
PR comment, or person that defines what 'done' means here?"* One pointer often
reframes the whole deliverable — a single file can turn "resolve this PR" into a
concrete change. Let the user hand you that source before you presume an answer
space.

## The one thing that matters most

`define-goal` (the next phase) needs a **transcript-demonstrable success
signal** — because `/goal`'s evaluator only reads the conversation, it can't run
tools. So you are not done until you have a check whose *output Claude can show*:
a test that exits 0, a benchmark number a script prints, a file count, a lint
result. "Better" or "working" without a number is not a signal — push until it's
concrete.

Then probe whether it's *headlessly* demonstrable: can Claude run it and show the
output in a transcript? If the real artifact can't be (an Airflow DAG with no
local `airflow`, a service needing a live container), record the **runnable
proxy** — a committed test that stands in for it (e.g. a static/AST check of the
DAG's task order) — and prefer the proxy that doubles as a CI regression guard.
Note any live-MCP/container confirmation as belt-and-suspenders, but the proxy is
what the `/goal` signal rides on.

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

- **Hard gate before the first `AskUserQuestion`.** Don't open a menu until (a) you've let the user point you at the source of truth, and (b) you've confirmed the deliverable is genuinely *enumerable*. If either is unmet, ask **one open question in plain chat** — a menu presumes the answer space it's meant to discover. And read a rejected menu as a signal: when the user clarifies or rejects your tabs, the *deliverable* isn't pinned yet — drop back to open grilling, don't reissue a reworded menu.
- **Bounded choice → `AskUserQuestion` tabs.** Once the deliverable is known and enumerable, settle the genuinely bounded sub-decisions (which repo, which layer, the threshold, the toolbox) with the tool: **one question per call**, 2–4 concrete options as tabs grounded in your exploration (the user can pick *Other* to free-type).

Never dump the sections as a prose checklist.

1. **What are we building or changing?** The specific deliverable; locate it — which **repo** (`target_repo`, which may not be cwd), then which file/module/endpoint/behavior.
2. **What does "done" look like?** The success signal — measurable and transcript-demonstrable, with the runnable proxy if the real artifact isn't headlessly verifiable. Be stubborn here.
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

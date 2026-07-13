---
name: inspect-skill-flow
description: Graph a skill's flow — steps, artifacts, invocations — render it with draw-graphology, and report checkable weak links — each verified by two independent subagents — as a handoff file of lessons for improve-skills.
disable-model-invocation: true
---

# inspect-skill-flow

Read one or more skills, build a typed dependency graph of their flow, render it, and audit the graph for **weak links** — defects the graph can prove, each cited to an exact node or edge. Read-only: this skill never edits a skill; findings hand off to `/improve-skills`, which owns the edit-behind-a-gate.

Rendering is delegated to `/draw-graphology` — build the graph JSON to its schema (`draw-graphology/references/graph-schema.md`) and let its mandatory render-view-fix loop produce the interactive HTML + preview PNG. Do not restate or reimplement its renderer here.

## Graph model

**Nodes** are steps (step-level mode) or skills (skill-level mode). Each node carries three attributes in your working notes, read straight from the text:

- `criterion` — does the step state a checkable completion criterion?
- `gate` — does it block on explicit user approval?
- `destructive` — does it write, delete, push, or otherwise act irreversibly?

**Edges** come in exactly three types, set as `edges[].type`:

- `sequence` — step B follows step A in the written order.
- `artifact` — A produces something B consumes; put the artifact itself on the edge `label` (`SPEC.md`, `failure_signature`, "approved proposal"). An artifact edge is a **contract**: the producer's output wording and the consumer's input wording must name the same thing.
- `invoke` — A calls another skill, agent, script, or tool.

**Boundary nodes** — anything a target references that lives outside the target set (another skill, a script, a reference file) becomes a node of type `boundary`, so cross-boundary contracts stay visible.

## Encoding (fitted to the renderer's actual contract)

The renderer colors nodes by `type` via `viz.palette`, supports no per-edge color, and **silently drops any edge whose endpoint id doesn't exist** — three consequences:

- **Weakness is a node type, not a color field.** A defective step/skill gets type `weak` (red in the palette). A broken contract (artifact with a missing end) is materialized as its own small node of type `missing` (red) connected to the end that does exist — never as an edge into a nonexistent id, which would vanish at render time.
- **Edge types are told apart by thickness and label**, not color: `artifact` edges `weight: 0.9` (labeled with the artifact), `invoke` `0.5` (labeled "invokes"), `sequence` `0.2` (unlabeled).
- Standard `viz` block: `colorBy: "type"`, `sizeBy: "degree"`, `directed: true`, `edgeLabels: true`, `labelThreshold: 0` (skill graphs are small), and a `palette` naming `step`, `skill`, `boundary`, `weak`, `missing` — `weak`/`missing` in red, `boundary` muted. Set `meta.description` to the question the graph answers: *where does this flow break?*

## Step 1 — Resolve targets and mode

Read every named skill's `SKILL.md` in full, then follow its invoke references transitively (skills it calls, scripts it runs, files it points to) and read those too — family membership is discovered by following references, never by name prefix.

Pick the mode from what you read, not from a flag:

- One skill whose structure is its own steps → **step-level**: nodes are that file's steps; everything referenced becomes boundary nodes.
- Multiple skills, or one orchestrator whose steps are mainly invocations of other skills (a chain like brainstorming → write-plan → execute-plan) → **skill-level**: one node per skill.
- A reference-only skill has no flow: graph its sections, pointers, and invocations without sequence edges, and run only the audit checks that apply.

**Completion:** every target and transitively referenced file read (or recorded as missing — that's already a finding); mode chosen and stated.

## Step 2 — Extract the graph

Walk the text and emit nodes and typed edges. Two exhaustiveness rules:

- Every step (or skill) in the targets appears as exactly one node, attributes filled from its text.
- Every artifact mentioned anywhere resolves to a produce end, a consume end, or both — an artifact with only one end is not a modeling gap to smooth over; leave the dangling end visible for the audit.

Write the graph as JSON to the scratchpad, following the schema and the encoding block above.

**Completion:** graph JSON written; every target step/skill is a node and every mentioned artifact has its ends recorded.

## Step 3 — Audit for weak links

Run these six checks — and only these — against every node and edge. Flag nothing speculative: no style opinions, no "could be clearer". Each finding cites the exact node or edge.

1. **Broken handoff** — an artifact consumed but never produced by any upstream node.
2. **Dead output** — an artifact produced but never consumed (and not the skill's stated deliverable).
3. **Orphan** — a node unreachable from the entry node by any edge.
4. **Dangling pointer** — an invoke or reference edge whose target is **unreachable as written** — resolve every path from the installed skill location the loaded SKILL.md runs from, never the source repo. Absent files, relative paths that don't resolve from a realistic cwd, unfilled placeholders, and symlink-only resolution (fragile install — still a finding) all count.
5. **Missing criterion** — a step node with `criterion: false`.
6. **Ungated destruction** — a `destructive` node with no `gate` on it or on any node preceding it.

Each finding records three things: the check name, the exact node/edge cited, and a **failure scenario** — the concrete run where the defect bites ("every haul parks at the final gate: `gh pr create` has no base branch to use"). A defect whose failure scenario you cannot state is not a finding.

**Completion:** all six checks run over the whole graph; findings list assembled (an empty list is a valid result), each with its failure scenario.

## Step 4 — Verify (two skeptics)

Findings ship only after surviving independent refutation. Spawn **two subagents in parallel**; give each the finding list (check · citation · failure scenario) and the target file paths, and prompt each to **refute** every finding by re-reading the sources — not to review the skill, not to add findings, only to break the ones on the list. A finding survives only if **both** confirm it; anything refuted or contested is dropped and carried to the report's tail with the refuting reason.

Fold the survivors back into the graph JSON: retype defective nodes to `weak`, materialize each broken contract's missing end as a `missing` node. Refuted findings leave no mark on the graph.

**Completion:** two independent verdicts per finding; survivors folded into the JSON, refuted ones recorded with reasons.

## Step 5 — Render

Invoke `/draw-graphology` on the graph JSON. It owns the render-view-fix loop; your acceptance bar for it: node labels legible, the three edge weights/labels distinguishable, red `weak`/`missing` nodes visible at a glance.

**Completion:** HTML + PNG produced, PNG viewed and legible, paths in hand.

## Step 6 — Report and hand off

Report, in this order:

- The rendered graph: PNG shown, HTML path for interactive exploration.
- The flow in one paragraph: entry, main chain, where it ends.
- Findings, most severe first, each as: check name · node/edge cited · **failure scenario** · one-line **lesson** phrased so it can be fed directly to `/improve-skills` (which takes one lesson per run; the rest queue).
- Refuted findings last, one line each, with the refuting reason.
- If no finding survived, say so plainly — do not pad with suggestions.

Then write the **handoff file** — `~/personal/skills/.inspect/<target>-handoff.md` — so a fresh session can act on the findings without this conversation: the target skill paths and mode, the graph JSON/HTML/PNG paths, and each surviving finding with its exact citation (file:line), failure scenario, both verifier verdicts, and a ready-to-paste `/improve-skills` lesson line, ordered most severe first. End the report by pointing at the file: run `/improve-skills` in a new session with it, one finding per run.

**Completion:** report delivered, handoff file written; no skill file was modified.

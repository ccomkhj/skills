---
name: draw-graphology
version: 1.1.0
description: Create data-driven network graph visualizations with graphology + sigma.js. Use when the user wants to visualize a network, dependency graph, knowledge graph, call graph, org/relationship map, communities/clusters, or any node-edge dataset too large to place by hand.
---

# Draw Graphology

Turn relational data into a **network graph visualization**: describe nodes and edges, let algorithms find the structure, and render an interactive graph (plus a static preview) with the [graphology](https://graphology.github.io/) toolkit and [sigma.js](https://www.sigmajs.org/).

**Setup:** If the user asks you to set up this skill (renderer, dependencies), see `README.md`.

---

## When to use this vs. excalidraw-diagram

These are complementary. Pick by **who places the nodes**.

| | **draw-graphology** (this skill) | **excalidraw-diagram** |
|---|---|---|
| Best for | Data-driven networks: dependency graphs, call graphs, knowledge graphs, social/relationship maps, anything with many nodes | Hand-authored argumentative diagrams: workflows, architectures, concepts |
| Node count | Dozens to thousands | A handful to ~30 |
| Layout | **Algorithmic** (ForceAtlas2, circular, hierarchical) | **Manual** (you set every x/y) |
| Structure | **Emerges** from the data (communities, hubs) | **Imposed** by you (the shape IS the argument) |
| Output | Interactive HTML (pan/zoom/hover) + PNG | `.excalidraw` file + PNG |

If the user wants to *make a point* with a small, carefully-arranged figure, use excalidraw. If they have *relational data* and want to *see its structure*, use this.

This skill's methodology is lifted from the **Understand-Anything dashboard** (graphology community detection, degree-based sizing, semantic type palette, edge aggregation). You are reproducing that approach in a lightweight, standalone renderer.

---

## Core philosophy

**Structure should emerge, not be imposed.** With a hand-drawn diagram you decide what matters and place it. With a network graph, the whole point is to *discover* what matters — which nodes are hubs, which cluster together, where the bridges are. Your job is to feed the algorithms good data and choose encodings that reveal that structure. Don't fight the layout by hand-placing nodes; tune the analysis.

**Every visual channel must carry information.** Color, size, and edge thickness are not decoration — each encodes a real property (type, importance, strength). If a channel isn't encoding something, turn it off. A graph where all nodes are the same size and color is a graph that's telling you nothing.

**The graph must answer a question.** Before drawing, know what the viewer should learn: "which services are most depended-on?", "what are the natural modules?", "how does data flow from ingest to output?". The encoding follows from the question.

---

## The data model

You produce a single JSON file. Full schema and examples: **`references/graph-schema.md`**. The shape (aligned with the dashboard's `KnowledgeGraph`):

```json
{
  "meta": { "title": "...", "description": "..." },
  "viz": { "layout": "forceatlas2", "colorBy": "community", "sizeBy": "degree", "directed": true },
  "nodes": [ { "id": "orders", "label": "orders", "type": "module" } ],
  "edges": [ { "source": "api", "target": "orders", "type": "calls", "weight": 0.9 } ]
}
```

- **Nodes** have an `id` (required), a `label`, an optional `type` (drives color), and an optional `value` (manual importance).
- **Edges** have `source`/`target` (required), an optional `type`, and a `weight` (0–1, drives thickness).
- **`viz`** configures how the graph is analyzed and drawn — this is where most of your design decisions live.

---

## Encoding methodology

This is the heart of the skill. Match each visual channel to a property of the data.

### Color — categorical identity

Set `viz.colorBy` to one of:

- **`community`** — run Louvain community detection and color each cluster distinctly. Use when the question is *"what are the natural groups?"* This is the most revealing default for an unlabeled network — it shows structure you didn't know was there.
- **`type`** — color by `node.type` using the semantic palette (`file`, `service`, `table`, `module`, …). Use when nodes have meaningful, known categories and the question is *"how do the kinds of things relate?"*
- **`fixed`** — one color (or per-node `color`). Use only when color should stay out of the way (e.g. size/layout is the whole story).

Colors come from **`references/color-palette.md`** — the single source of truth. Edit that file to rebrand.

### Size — importance

Set `viz.sizeBy`:

- **`degree`** (default) — node size ∝ number of connections. Hubs pop out. This is what the dashboard does and it's almost always right: the most-connected node is usually the most important.
- **`value`** — size by the manual `node.value` field. Use when you have an external importance metric (traffic, LOC, revenue) that matters more than connectivity.
- **`fixed`** — uniform size. Use only for small graphs where every node is equal.

Sizing uses a square-root scale (area-proportional), so a node with 4× the degree is 2× the radius — big hubs stay legible without swallowing the canvas.

### Edge thickness & direction

- **`weight`** (0–1) maps to line thickness — thicker = stronger/more-frequent relationship.
- Set **`viz.directed: true`** (the default) to draw arrowheads. Turn it off for symmetric relationships (co-occurrence, similarity).
- For large graphs, **aggregate** many thin edges into fewer weighted ones (see `references/analysis-recipes.md` → *Edge aggregation*). A hairball of 2,000 edges says less than 30 weighted bundles.

### Labels

Set `viz.labelThreshold` to hide labels for small nodes on dense graphs — only hubs stay labeled, so the figure doesn't turn to text soup. On small graphs, leave it at 0 (label everything).

---

## Choosing a layout

Set `viz.layout`:

| Layout | Use when | Reveals |
|--------|----------|---------|
| **`forceatlas2`** (default) | General networks, unknown structure | Communities as spatial clusters; hubs pulled central |
| **`circular`** | Small graphs, or emphasizing *all* pairwise edges equally | Every edge clearly, no hidden crossings behind clusters |
| **`random`** | Rarely — a deliberately unstructured scatter | Nothing; only as a before/after contrast |
| **`preset`** | You have meaningful x/y already (geographic, timeline) | Whatever the coordinates mean |

ForceAtlas2 is the workhorse: it pulls connected nodes together and pushes unconnected ones apart, so **communities become visible regions**. Tune it with `viz.iterations` (more = more settled, 300–600 typical), `viz.scalingRatio` (bigger = more spread out), and `viz.gravity` (bigger = tighter overall).

---

## Analysis with graphology

The graphology ecosystem does the analytical work *before* rendering. The renderer already runs community detection and degree sizing for you based on `viz`. When you need to go further — centrality metrics, deriving clusters when there's no `type`, aggregating edges, filtering to a subgraph — see **`references/analysis-recipes.md`**, which ports the dashboard's actual algorithms:

- **Louvain community detection** (`graphology-communities-louvain`) — the grouping engine.
- **Degree / centrality** — importance metrics for sizing and filtering.
- **Container derivation** — folder-first, community-fallback grouping (the dashboard's `deriveContainers`).
- **Edge aggregation** — collapse cross-cluster edges into weighted bundles.

---

## Workflow

### Step 1 — Know the question
What should the viewer learn from this graph? That decides `colorBy`, `sizeBy`, and layout. Write it into `meta.description` so it ships with the figure.

### Step 2 — Gather the data
Get the real nodes and edges. If visualizing a codebase, dependencies, or logs, **extract from the source** — don't invent nodes. Assign each node a `type` if there's a meaningful taxonomy; assign each edge a `weight` if strength varies.

### Step 3 — Model the JSON
Write the graph JSON (see `references/graph-schema.md`). Keep `id`s stable and human-readable. For large datasets, generate the JSON with a script rather than by hand — but keep the file as plain data, not code.

### Step 4 — Configure the encoding
Set `viz` from the question:
- Unknown structure, "what clusters exist?" → `colorBy: community`, `layout: forceatlas2`, `sizeBy: degree`.
- Known categories → `colorBy: type`.
- "Which nodes matter most?" → `sizeBy: degree` (or `value`), consider `labelThreshold` to spotlight hubs.

### Step 5 — Render & validate (MANDATORY)
Run the render-view-fix loop below until the graph reads clearly. **You cannot judge a graph from JSON.**

---

## Render & validate (MANDATORY)

After writing the JSON, you MUST render it, view the PNG, and fix what you see — in a loop.

### How to render

```bash
cd .claude/skills/draw-graphology/references && uv run python render_graph.py <path-to-graph.json>
```

This writes two files next to the input:
- `<name>.html` — the **interactive deliverable** (pan/zoom/hover, plus an **arrow-key guided tour** — see below)
- `<name>.png` — a **static preview** for you to inspect

Then use the **Read tool** on the PNG to actually view it. Render **without** `--open` while iterating, so you don't spawn a browser tab every pass.

### The loop

**1. Render & view** — run the script, Read the PNG.

**2. Audit against the question** (Step 1):
- Can you *see* the answer? If the question was "what are the clusters?", are clusters visually separated? If "which are hubs?", do the big nodes stand out?
- Do the encodings read correctly — is color telling you type/community, is size telling you importance?

**3. Check for defects:**
- **Hairball** — edges so dense you can't see structure. Fix: aggregate edges, raise `scalingRatio`, filter low-weight edges, or raise `labelThreshold`.
- **Overlapping nodes** — clusters collapsed on top of each other. Fix: more `iterations`, higher `scalingRatio`.
- **Everything one color / one size** — a channel is off or misconfigured. Fix `colorBy` / `sizeBy`.
- **Unreadable labels** — too many labels overlapping. Fix: raise `labelThreshold`.
- **Disconnected nodes flung to the edges** — expected for true isolates, but if it's most of the graph your edges may not be connecting (check that `source`/`target` match node `id`s — the renderer drops edges with unknown endpoints).
- **Cramped or off-center** — adjust `--width` / `--height`, or `gravity`.

**4. Fix** — edit the JSON's `viz` (usually) or the data, and re-render.

**5. Repeat** — typically 2–4 iterations. Stop when you can read the answer to the question at a glance and no defects remain.

### Hand it off

**The moment the graph passes validation, open the interactive viewer for the user** — run `render_graph.py <file> --open`. Don't wait to be asked; the interactive `.html` (with its guided tour) is the real deliverable, the PNG is just your preview.

### Guided tour

The viewer has an **arrow-key guided tour** (Understand-Anything–style): **→** next step, **←** back, **Esc** overview. By default it walks the nodes hubs-first; define your own ordered steps with a top-level `tour` array, or disable with `viz.tour: false`. See `references/graph-schema.md` → *Guided tour*. Author a `tour` when the graph tells a sequential story (a pipeline, an onboarding path), not just a structure.

### First-time setup
```bash
cd .claude/skills/draw-graphology/references
uv sync
uv run playwright install chromium
```

---

## Quality checklist

**Purpose**
1. The graph answers a specific question, stated in `meta.description`.
2. You can *see* the answer in the rendered PNG, not just infer it.

**Encoding**
3. Color encodes something real (`community` or `type`), not decoration.
4. Size encodes importance (`degree` or `value`); hubs are visibly bigger.
5. Edge weight is used when relationship strength varies.
6. Direction (`directed`) matches the data (arrows only for asymmetric relations).

**Legibility**
7. No hairball — structure is visible, not buried in edges.
8. No overlapping/collapsed clusters (enough `iterations` / `scalingRatio`).
9. Labels are readable (`labelThreshold` raised on dense graphs).
10. Colors come from `references/color-palette.md`, not invented.

**Validation**
11. Rendered to PNG and visually inspected.
12. All edges connect (no silent drops from mismatched ids).
13. The interactive `.html` opens and is usable.

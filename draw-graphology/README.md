# Draw Graphology Skill

A coding-agent skill that turns node-edge data into **network graph visualizations** — interactive HTML plus a static PNG — using the [graphology](https://graphology.github.io/) toolkit and [sigma.js](https://www.sigmajs.org/).

Where [`excalidraw-diagram`](../excalidraw-diagram) is for hand-authored diagrams you place by hand, this is for **data-driven graphs** where the structure (communities, hubs, bridges) is discovered algorithmically and the layout is computed, not drawn.

## What it does

- **Structure emerges from data.** ForceAtlas2 layout pulls connected nodes together so communities show up as spatial regions; Louvain community detection colors them; degree centrality sizes the hubs.
- **Every channel encodes something.** Color = type or community, size = importance, edge thickness = weight, arrowheads = direction.
- **Methodology borrowed from the Understand-Anything dashboard.** Community detection, degree sizing, the semantic type palette, and edge aggregation are ports of that project's actual algorithms — reproduced in a lightweight standalone renderer.
- **Built-in visual validation.** A Playwright render pipeline screenshots the graph so the agent can see its own output and fix hairballs, overlaps, and unreadable labels in a loop.
- **Brand-customizable.** All colors live in `references/color-palette.md`.

## Setup

**Option A — ask your agent:** *"Set up the draw-graphology skill renderer following SKILL.md."*

**Option B — manual:**

```bash
cd draw-graphology/references
uv sync
uv run playwright install chromium
```

## Usage

Ask your agent for a graph:

> "Visualize the import dependencies between these modules, colored by community."

The agent models the data as a graph JSON, configures the encoding, renders, and validates visually.

To render a graph JSON directly:

```bash
cd draw-graphology/references
uv run python render_graph.py path/to/graph.json
# writes graph.html (interactive) and graph.png (preview) next to the input
```

## Customize colors

Edit `references/color-palette.md` and the matching constants in `references/render_template.html`. Everything else is domain-agnostic methodology.

## File structure

```
draw-graphology/
  SKILL.md                     # Methodology + encoding + render/validate loop
  references/
    graph-schema.md            # The graph JSON format
    color-palette.md           # Node-type + community colors (edit to rebrand)
    analysis-recipes.md        # graphology recipes: Louvain, centrality, aggregation
    render_graph.py            # Render graph JSON → interactive HTML + PNG
    render_template.html       # sigma.js + graphology renderer
    pyproject.toml             # Python deps (playwright)
```

## How rendering works

`render_graph.py` inlines your graph data into `render_template.html` (producing the self-contained interactive `.html`), loads it in headless Chromium, waits for sigma.js to paint, and screenshots it to `.png`. The graphology analysis (Louvain, degree, layout) runs in the browser at render time from the `viz` config in your JSON.

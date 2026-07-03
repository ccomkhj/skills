# Graph JSON schema

The renderer (`render_graph.py`) consumes one JSON file with this shape. It is intentionally close to the Understand-Anything dashboard's `KnowledgeGraph` type, trimmed to what a standalone drawing needs.

```jsonc
{
  "meta": {
    "title": "string",          // shown top-left
    "description": "string"     // subtitle; put the question the graph answers here
  },

  "viz": {
    "layout": "forceatlas2",    // forceatlas2 | circular | random | preset
    "colorBy": "community",     // community | type | fixed
    "sizeBy": "degree",         // degree | value | fixed
    "directed": true,           // draw arrowheads (default true)

    // ForceAtlas2 tuning (only for layout: forceatlas2)
    "iterations": 300,          // more = more settled (300–600 typical)
    "scalingRatio": 12,         // bigger = more spread out
    "gravity": 1,               // bigger = tighter overall

    // Sizing bounds (pixels)
    "minSize": 4,
    "maxSize": 22,

    // Labels & edges
    "labelThreshold": 0,        // hide labels for nodes smaller than this (px). Raise on dense graphs.
    "labelColor": "#e8e2d8",
    "labelSize": 12,
    "edgeLabels": false,        // render edge labels (only for small graphs)
    "edgeColor": "rgba(255,255,255,0.28)",

    // Theming
    "background": "#0a0a0a",
    "detectCommunities": false, // force Louvain even when colorBy !== community
    "tour": true,               // enable the arrow-key guided tour (default true)
    "palette": {                // override type→color (merged over the defaults)
      "service": "#a78bfa"
    }
  },

  "tour": [                     // OPTIONAL guided-tour steps (see "Guided tour" below)
    { "title": "Entry point", "description": "The API gateway fans out to every module.", "nodes": ["api"] }
  ],

  "nodes": [
    {
      "id": "orders",           // REQUIRED, unique
      "label": "orders",        // display text (defaults to id)
      "type": "module",         // drives color when colorBy: type
      "value": 3,               // manual importance; drives size when sizeBy: value
      "color": "#5ba4cf",       // explicit color override (wins over colorBy)
      "x": 0, "y": 0            // only used when layout: preset
    }
  ],

  "edges": [
    {
      "source": "api",          // REQUIRED, must match a node id
      "target": "orders",       // REQUIRED, must match a node id
      "type": "calls",          // free-form relationship label
      "weight": 0.9,            // 0–1, drives thickness (default 1)
      "label": "calls"          // shown only when viz.edgeLabels: true
    }
  ]
}
```

## Field rules

- **`nodes[].id`** must be unique. Duplicate ids after the first are ignored; the renderer's validator will warn.
- **`edges[].source` / `target`** must reference existing node ids. Edges with unknown endpoints are silently dropped at render time — the validator flags them, so fix them.
- **`weight`** is clamped to `[0, 1]` for thickness. Out-of-range values won't error but won't scale as expected.
- **`type`** is free-form, but only types present in `references/color-palette.md` get a semantic color; unknown types fall back to a neutral gray. Either reuse the known types or add yours to the palette.
- Everything under **`viz`** is optional; omit a field to take its default.

## Default node types (semantic palette)

These match the dashboard and have colors in `color-palette.md`:

`file` · `function` · `class` · `module` · `concept` · `config` · `document` · `service` · `table` · `endpoint` · `pipeline` · `schema` · `resource`

Use them when they fit your domain (they map cleanly onto code/data/infra graphs). For a non-code domain, invent your own type names and add matching entries to `viz.palette` or `color-palette.md`.

## Guided tour

The rendered `.html` viewer supports an **arrow-key guided tour**, like the Understand-Anything dashboard's tours: press **→** to advance to the next step, **←** to go back, **Esc** to return to the overview. Each step animates the camera to the step's node(s), highlights them and their neighbors (dimming everything else), and shows the step's title/description.

- **Define your own tour** with a top-level `tour` array. Each step is `{ "title", "description", "nodes": ["id", …] }`. Steps focus one *or several* nodes. Node ids that don't exist are dropped; a step left with no valid nodes is skipped.
- **Auto-tour (default)** — if you omit `tour`, the viewer builds one step per node, largest (most connected) first, titled by the node's label. This gives a "walk the hubs" tour for free.
- **Disable** with `viz.tour: false` (no tour, no hint, arrow keys inert).

The tour is interactive-only — it does not affect the static PNG, which always renders the full overview.

## Minimal example

```json
{
  "meta": { "title": "Who talks to whom", "description": "Team communication frequency" },
  "viz": { "layout": "forceatlas2", "colorBy": "community", "sizeBy": "degree", "directed": false },
  "nodes": [
    { "id": "ana" }, { "id": "ben" }, { "id": "cid" }, { "id": "dex" }
  ],
  "edges": [
    { "source": "ana", "target": "ben", "weight": 0.9 },
    { "source": "ben", "target": "cid", "weight": 0.4 },
    { "source": "ana", "target": "dex", "weight": 0.6 }
  ]
}
```

# Color palette

Single source of truth for all colors. The renderer hard-codes these defaults (in `render_template.html`); override per-graph via `viz.palette` / `viz.edgeColor` / `viz.background`, or edit this file **and** the matching constants in the template to rebrand permanently.

Lifted from the Understand-Anything dashboard's dark theme.

## Background & text

| Purpose | Color |
|---------|-------|
| Canvas background | `#0a0a0a` |
| Title text | `#f5f0eb` |
| Subtitle / muted | `#a39787` |
| Node labels | `#e8e2d8` |
| Edges (default) | `rgba(255,255,255,0.28)` |

## Node type colors (`colorBy: type`)

Each semantic node type has a fixed color. Darker stroke is derived automatically by sigma; these are the fills.

| Type | Color | | Type | Color |
|------|-------|---|------|-------|
| `file` | `#4a7c9b` | | `document` | `#7dd3fc` |
| `function` | `#5a9e6f` | | `service` | `#a78bfa` |
| `class` | `#8b6fb0` | | `table` | `#6ee7b7` |
| `module` | `#c9a06c` | | `endpoint` | `#fdba74` |
| `concept` | `#b07a8a` | | `pipeline` | `#fda4af` |
| `config` | `#5eead4` | | `schema` | `#fcd34d` |
| | | | `resource` | `#a5b4fc` |

Unknown types fall back to neutral gray `#7a8290`.

## Community colors (`colorBy: community`)

Categorical palette cycled by community index (Louvain output, compacted to `0..k-1`). Chosen for distinct hues that stay legible on the dark background.

```
#5ba4cf  #5ea67a  #cf7a8a  #9b7abf  #c9963a
#4aab9a  #e0708a  #7dd3fc  #a5b4fc  #fcd34d
#f0967a  #68c4b4  #b494d4  #9ec96e  #dd8fb0
```

With more than 15 communities the palette repeats — if you have that many clusters, consider whether the graph should be filtered or the communities merged, rather than relying on color alone.

## Customizing

- **One graph, quick tweak:** set `viz.palette`, `viz.edgeColor`, `viz.background`, or per-node `color` in the graph JSON.
- **Permanent rebrand:** edit `TYPE_PALETTE`, `COMMUNITY_PALETTE`, and the CSS in `render_template.html`, and mirror the values here so this file stays the source of truth.

## Principles

- **Color encodes identity, never decoration.** If `colorBy: fixed`, you've decided color carries no information — that's fine, but then let size and layout do the work.
- **Don't hand-pick per-node colors** to make a graph "pretty." Per-node `color` is for genuine semantic overrides (e.g. highlighting one flagged node), not styling.
- **Keep the background dark.** The palettes are tuned for `#0a0a0a`; light backgrounds wash out the community hues.

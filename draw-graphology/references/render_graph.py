"""Render a graphology graph JSON to an interactive HTML + a preview PNG.

The renderer builds a self-contained interactive viewer (graphology + sigma.js)
with the graph data inlined, then screenshots it headlessly so you can see and
fix the visualization in a loop.

Usage:
    cd .claude/skills/draw-graphology/references
    uv run python render_graph.py <graph.json> [--out-dir DIR] [--scale 2] [--width 1600] [--height 1000] [--open]

Outputs (next to the input, or in --out-dir):
    <name>.html   self-contained interactive viewer (open in a browser)
    <name>.png    static preview for visual validation

First-time setup:
    cd .claude/skills/draw-graphology/references
    uv sync
    uv run playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate_graph(data: dict) -> list[str]:
    """Validate the graph JSON structure. Returns a list of errors (empty = ok)."""
    errors: list[str] = []
    if not isinstance(data.get("nodes"), list) or not data["nodes"]:
        errors.append("'nodes' must be a non-empty array")
    if not isinstance(data.get("edges"), list):
        errors.append("'edges' must be an array (may be empty)")

    ids: set[str] = set()
    for i, n in enumerate(data.get("nodes", []) or []):
        if not isinstance(n, dict) or "id" not in n:
            errors.append(f"node[{i}] missing 'id'")
            continue
        if n["id"] in ids:
            errors.append(f"duplicate node id: {n['id']!r}")
        ids.add(n["id"])

    for i, e in enumerate(data.get("edges", []) or []):
        if not isinstance(e, dict) or "source" not in e or "target" not in e:
            errors.append(f"edge[{i}] missing 'source'/'target'")
            continue
        if e["source"] not in ids:
            errors.append(f"edge[{i}] source {e['source']!r} is not a known node id")
        if e["target"] not in ids:
            errors.append(f"edge[{i}] target {e['target']!r} is not a known node id")
    return errors


def build_standalone_html(template: str, data: dict) -> str:
    """Inline the graph data into the template so the HTML is self-contained.

    A classic <script> runs before the deferred ES module, so __GRAPH_DATA is
    set by the time the module's auto-render check reads it.
    """
    inline = (
        "<script>window.__GRAPH_DATA = "
        + json.dumps(data)
        + ";</script>\n"
    )
    marker = '<script type="module">'
    if marker not in template:
        raise ValueError("template is missing the module <script> marker")
    return template.replace(marker, inline + "  " + marker, 1)


def render(
    graph_path: Path,
    out_dir: Path | None,
    scale: int,
    width: int,
    height: int,
) -> tuple[Path, Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.", file=sys.stderr)
        print(
            "Run: cd .claude/skills/draw-graphology/references && uv sync && uv run playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    raw = graph_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {graph_path}: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_graph(data)
    if errors:
        print("ERROR: Invalid graph file:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    template_path = Path(__file__).parent / "render_template.html"
    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)
    template = template_path.read_text(encoding="utf-8")

    out_dir = out_dir or graph_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / (graph_path.stem + ".html")
    png_path = out_dir / (graph_path.stem + ".png")

    html_path.write_text(build_standalone_html(template, data), encoding="utf-8")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "browserType.launch" in str(e):
                print("ERROR: Chromium not installed for Playwright.", file=sys.stderr)
                print(
                    "Run: cd .claude/skills/draw-graphology/references && uv run playwright install chromium",
                    file=sys.stderr,
                )
                sys.exit(1)
            raise

        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
        )
        errors_console: list[str] = []
        page.on("console", lambda m: errors_console.append(m.text) if m.type == "error" else None)

        page.goto(html_path.as_uri())
        try:
            page.wait_for_function("window.__renderComplete === true", timeout=30000)
        except Exception:
            print("ERROR: Render timed out (30s).", file=sys.stderr)
            for line in errors_console[-10:]:
                print(f"  console: {line}", file=sys.stderr)
            browser.close()
            sys.exit(1)

        # settle a couple frames for WebGL paint
        page.wait_for_timeout(250)
        page.screenshot(path=str(png_path))
        browser.close()

    return html_path, png_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a graphology graph JSON to HTML + PNG")
    parser.add_argument("input", type=Path, help="Path to the graph JSON file")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory (default: alongside input)")
    parser.add_argument("--scale", "-s", type=int, default=2, help="Device scale factor (default: 2)")
    parser.add_argument("--width", "-w", type=int, default=1600, help="Viewport width (default: 1600)")
    parser.add_argument("--height", type=int, default=1000, help="Viewport height (default: 1000)")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the interactive HTML in the default browser once it's rendered",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    html_path, png_path = render(args.input, args.out_dir, args.scale, args.width, args.height)
    print(str(html_path))
    print(str(png_path))

    if args.open:
        import webbrowser

        webbrowser.open(html_path.as_uri())
        print(f"Opened {html_path.name} in the default browser.")


if __name__ == "__main__":
    main()

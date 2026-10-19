# Page contract

Same contract the built-in Artifact pages followed, so a local page looks and
behaves like one. `gallery.py publish` checks the items marked ✓.

## Shape

- One self-contained `.html` file. If you need more files, use a folder with
  `index.html` at its root and relative paths with no leading slash. Turn Markdown
  input into a designed HTML page instead of copying it line for line.
- ✓ `<title>` is a 2–4 word name ("Q3 Churn Review", not "Churn: explainer").
  The explanation goes in `--description`.
- ✓ ≤ 16 MB including `data:` URIs.

## Theme

- ✓ Colors are CSS custom properties on `:root`.
- ✓ Dark mode redefines the same tokens under
  `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {…} }`
  and again under `:root[data-theme="dark"]`.
- ✓ `body` sets an explicit `background`.
- Works at phone width: 16px side gutter, no horizontal page scroll. Wide tables
  scroll inside their own wrapper.

## External resources

- ✓ Scripts come only from `cdnjs.cloudflare.com` (preferred), `cdn.jsdelivr.net/npm/`,
  `unpkg.com`, `cdn.tailwindcss.com`, `code.jquery.com`. Stylesheets come only from Google Fonts.
  Inline everything else.
- ✓ Every script URL pins an exact version that is at least two weeks old
  (`react@18.3.1`, not `react` or `react@18`).
- Pages also open offline, so content must stay readable when a CDN fails:
  render the core text or table in HTML, and add charts and interactivity on top.

## State and input

- `localStorage`/`sessionStorage` only for per-viewer conveniences. Wrap every
  access in try/catch, and the page must still render when storage throws.
- To collect input, end with a **Copy as JSON** button
  (`navigator.clipboard.writeText`, with a `<textarea>` fallback showing the JSON).
  Put a top-level key in the JSON that names the page, so a paste back into chat says where it came from.

## Effort

Match design effort to the request. A one-off status page needs clear hierarchy,
not polish. A dashboard or tool the user will reopen deserves real layout work.

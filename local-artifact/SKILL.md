---
name: local-artifact
version: 1.0.0
description: Build an HTML page (report, dashboard, explainer, small app) and keep it in a local gallery you can list, reopen, update and delete. Replacement for the built-in Artifact tool, with zero context cost until you type /local-artifact.
argument-hint: "[what to build | list | open <slug> | delete <slug>]"
disable-model-invocation: true
---

# Local artifact

The built-in `Artifact` tool is denied in `permissions.deny` because its schema
and companion tools cost thousands of tokens in every session. This skill does
the same job but loads only when you invoke it. Pages go to a local gallery
(`~/.local/share/local-artifacts/<slug>/`, override with `LOCAL_ARTIFACTS_DIR`)
instead of claude.ai.

`scripts/gallery.py` keeps the gallery: `publish`, `list`, `open`, `delete`.
Run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/gallery.py --help` for flags.

## Build or update a page

1. **Update, don't fork.** If the user means an existing page, run `list` and
   edit `<gallery>/<slug>/index.html` in place. Its `file://` link and history stay
   with the slug, the way republishing an artifact kept its URL.
2. Read `references/page-contract.md`, then write the page to the scratchpad
   (or wherever the user says). The contract is what made artifact pages render
   the same everywhere, so keep it even for quick pages.
3. `publish <file-or-dir> --description "<one sentence>"`. Pass `--slug` to replace
   an existing page. Publish runs the contract checks and opens the page.
   Fix every `!` warning and publish again until none are left.
4. Reply with the slug, the `file://` link, and one line on what the page shows.
   End with an optional copy-paste command for the user to run in another terminal
   if they want the page on claude.ai, with `<page>` set to the absolute gallery path:

   ```
   claude "Read <page> and publish it as an Artifact. Reply with only the artifact URL." --setting-sources project,local --tools Artifact,Read
   ```

   This is the only place the Artifact tool still exists. Skipping user settings
   drops the deny for that one session, and the user approves the publish there.
   Keep the prompt first: `--tools` takes a list and would swallow a prompt placed after it.
   Never run this command yourself. It gets around the user's deny, so the user runs it.

## Things a local page can't do

claude.ai artifacts had a hosted runtime: shared database, comments, viewer
identity, ask-Claude. A `file://` page has none of these. What replaces each:

- **Input to collect from the user**: a **Copy as JSON** button, and the user
  pastes the result back into chat, like the manage-context plan flow.
- **Live data**: pull it when you build the page and print the timestamp on it.
- **Per-viewer state** (tabs, filters, drafts): `localStorage` wrapped in try/catch.

## Sharing

The gallery is private to this machine. Sending a page anywhere else (a Superset page
via `superset:page`, a gist, Slack) publishes it, so ask the user first and
read the whole file before it leaves the machine.

## Delete

`delete <slug> --yes` removes the folder and can't be undone. Run it only when the
user names the page, after they confirm.

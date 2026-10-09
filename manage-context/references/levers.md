# Context levers: what each setting really does

Verified against the Claude Code CLI 2.1.295 binary on 2026-10-09 (setting
schema descriptions and the skill-state resolver). Re-check after a major CLI
upgrade: `strings "$(readlink -f "$(which claude)")" | grep -o 'skillOverrides:()=>.\{400\}'`.

## Settings files and precedence

`user < project < local < flag < policy` (later wins):

| Layer | File | Used by this skill as |
|---|---|---|
| user | `~/.claude/settings.json` | scope `global` |
| project | `<repo>/.claude/settings.json` | read only (shared, committed) |
| local | `<repo>/.claude/settings.local.json` | scope `project` (personal, gitignored) |

Per-project MCP state lives in `~/.claude.json` → `projects["<abs path>"]`, not in
a settings file. Running Claude Code sessions also write `~/.claude.json`, which
is why `apply_plan.py` re-reads it right before an atomic write.

## Skills: `skillOverrides`

`skillOverrides: { "<skill name>": "on" | "name-only" | "user-invocable-only" | "off" }`

- `name-only`: listed without its description (saves the description).
- `user-invocable-only`: hidden from the model, `/name` still works (saves the whole row).
- `off`: hidden from both.
- Absent means `on`.
- **Plugin skills (`plugin:skill`) ignore `skillOverrides`.** The resolver returns
  `on` for any skill whose source is a plugin. The only switch is the plugin itself.
  The scanner flags any override on a plugin skill as a mismatch.
- `disableBundledSkills: true` removes all bundled skills at once. That's too blunt
  to offer per row, so it's mentioned here only.

## Plugins: `enabledPlugins`

`enabledPlugins: { "<plugin>@<marketplace>": true | false }`

- Disabling a plugin removes its skills, agents, MCP servers and hooks.
- Because of precedence, `false` in `~/.claude/settings.json` is overridden by a
  project `true`. To turn a plugin off in one repo, set `false` in
  `.claude/settings.local.json`.
- **Org-synced plugins** (`~/.claude/plugins/synced/*/manifest.json`, e.g. the
  claude.ai knowledge-work plugins) are not unloaded by a local `false`. Manage
  them on claude.ai. The scanner flags this.
- **Skills-dir plugins** (a folder with `plugin.json` inside `~/.claude/skills/`,
  e.g. one installed by another app) have no setting. They're report-only.
- Plugins not found locally at all (e.g. `anthropic-skills:*`) come from the
  claude.ai account. They're report-only.

## MCP servers

| Server source | Name format | Project switch | Global switch |
|---|---|---|---|
| user (`~/.claude.json` → `mcpServers`) | `voids-db` | `projects[p].disabledMcpServers` += name | park: move the entry to `~/.claude/manage-context/parked-mcp-servers.json` (0600); undo moves it back |
| local (`projects[p].mcpServers`) | `name` | `disabledMcpServers` += name | — |
| `.mcp.json` in the repo | `name` | `disabledMcpjsonServers` += name (settings.local.json) | — |
| plugin | `plugin:<plugin>:<server>` | `disabledMcpServers` += name | disable the plugin |
| claude.ai connector | `claude.ai <Name>` | `disabledMcpServers` += name | disconnect on claude.ai → Settings → Connectors; `disableClaudeAiConnectors: true` turns off **all** of them |

- `disabledMcpjsonServers` only affects servers defined in a repo's `.mcp.json`.
  Listing a user-scope server there has no effect. The scanner flags it.
- The `/mcp` toggle writes `disabledMcpServers` for the current project, the same key this skill uses.
- Deferred MCP tools cost only their name in the prompt (about 10 tokens each).
  Server instructions and tools surfaced eagerly cost their full text.

## Not switchable

These are fixed for a given CLI version and session: the system prompt, built-in tool
schemas (e.g. `Artifact`), built-in deferred tool names, the built-in agent
types, session context (git status, user email) and harness reminders. Memory
files (`CLAUDE.md`, `AGENTS.md`, `@imports`) can only be trimmed by editing them.

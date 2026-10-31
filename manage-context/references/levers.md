# Context levers: what each setting really does

Verified against the Claude Code CLI 2.1.295 binary on 2026-10-09 (setting
schema descriptions and the skill-state resolver); plugin-skill rules re-checked
on 2.1.303 (2026-10-19); skill roles, frontmatter lock, account skills and the
`/skills` menu on 2.1.316 (2026-10-31), where `inventory.py` matched a live
session's skill listing with 0 mismatches. Re-check after a major CLI
upgrade: `strings "$(readlink -f "$(which claude)")" | grep -o 'function jAe(e){.\{700\}'`
(the resolver) and `grep -o 'skillOverrides:()=>.\{400\}'` (the setting).

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
- Absent means `on`. Layers merge `global < project-shared < project`, so the highest
  layer naming the skill wins. To turn a skill back **on** in one project while a
  lower layer hides it, `on` must be written explicitly in `settings.local.json`;
  deleting the key there would let the lower value through. `apply_plan.py` does this.
- Frontmatter `disable-model-invocation: true` locks the skill at `user-invocable-only`
  (the CLI's lock reason `author`): `on`/`name-only` overrides do nothing, `off` still
  hides it. Frontmatter `user-invocable: false` is the reverse: model only, no `/name`.
- Account skills (`anthropic-skills:*`, synced into `~/.claude/skills/synced/<org>/`
  with a `manifest.json`) **do** honor `skillOverrides`. Evidence: `anthropic-skills:docx`
  left the listing right after a project `off` (2026-10-19).
- Claude Code's own `/skills` menu switches the same key but writes only
  `localSettings` (this project's `settings.local.json`), and refuses locked skills
  (plugin, frontmatter, policy/flag).
- **Plugin skills (`plugin:skill`) ignore `skillOverrides`.** The resolver returns
  `on` for any skill whose source is a plugin. The scanner flags any override on a
  plugin skill as a mismatch. Two levers remain: disable the whole plugin, or add
  `disable-model-invocation: true` to that skill's own `SKILL.md` frontmatter (the
  plugin loader honours it). The frontmatter edit is outside this skill's scripts
  and is lost when the plugin updates or its owning app re-syncs, so offer it only
  as a manual step.
- `disableBundledSkills: true` removes all bundled skills and workflows; built-in
  slash commands stay typable but are hidden from the model. That's too blunt to
  offer per row, so it's mentioned here only. Overrides naming a bundled skill or
  built-in command then match nothing on disk; the Skills panel lists them under
  "settings for skills not on disk", next to overrides for removed skills.

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
  e.g. one installed by another app) have no setting. They're report-only here;
  manually, use the frontmatter edit above or move the folder out of
  `~/.claude/skills/` (the owning app may restore it).
- A plugin that is installed but absent from `enabledPlugins` is off. Every installed
  plugin gets a row in the report, so a disabled one can be switched on.

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

## Built-in tools: `permissions.deny`

`permissions: { deny: ["Artifact", ...] }`

- A bare tool name (no `(pattern)`) drops the tool from the model's tool list,
  so its whole schema leaves the prompt (`filterToolsByDenyRules`, CLI 2.1.303).
  `Bash(rm:*)`-style rules only block calls; the schema stays.
- Deny rules from every layer apply, so a global deny can't be undone by a
  project file. To deny in one repo only, use `.claude/settings.local.json`.
- Denying removes the capability, not just the listing: a skill that relies on
  the tool (e.g. `ReportFindings` for code review, `ScheduleWakeup` for `/loop`) stops working.
- `Bash`, `Read`, `Edit`, `Write`, `Skill`, `ToolSearch` are never offered (`CORE_TOOLS`).
- Built-in deferred tool names cost about 10 tokens each; not offered per row.

## Not switchable

These are fixed for a given CLI version and session: the system prompt, the
built-in agent types, session context (git status, user email) and harness reminders. Memory
files (`CLAUDE.md`, `AGENTS.md`, `@imports`) can only be trimmed by editing them.

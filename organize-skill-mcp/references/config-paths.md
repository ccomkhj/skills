# Known Config Paths

Reference of all known skill and MCP server configuration locations across AI coding tools. Update this file when tools add new config paths — the main SKILL.md procedure stays unchanged.

Last verified: 2026-03-28

## Skills Directories

| Scope | Tool | Path | Notes |
|-------|------|------|-------|
| Global | Claude Code | `~/.claude/skills/` | Symlinks to dirs containing SKILL.md |
| Global | Shared agents | `~/.agents/skills/` | Symlinks or direct dirs with SKILL.md |
| Global | Gemini CLI | `~/.gemini/skills/` | Direct dirs with SKILL.md |
| Project | Claude Code | `<project>/.claude/skills/` | Project-scoped skills |

## MCP Config Files

| Scope | Tool | Path | Format | Server Key |
|-------|------|------|--------|-----------|
| Global | Claude Code CLI | `~/.claude/mcp.json` | JSON | `mcpServers` |
| Global | Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` | JSON | `mcpServers` |
| Global | Claude Desktop (Windows) | `%APPDATA%/Claude/claude_desktop_config.json` | JSON | `mcpServers` |
| Global | Claude Desktop (Linux) | `~/.config/Claude/claude_desktop_config.json` | JSON | `mcpServers` |
| Global | Cursor | `~/.cursor/mcp.json` | JSON | `mcpServers` |
| Global | Windsurf | `~/.codeium/windsurf/mcp_config.json` | JSON | `mcpServers` |
| Global | Codex | `~/.codex/config.toml` | TOML | `[mcp_servers.*]` |
| Global | Gemini CLI (user) | `~/.gemini/settings.json` | JSON | `mcpServers` |
| Global | Gemini CLI (sys-defaults) | `/etc/gemini-cli/system-defaults.json` (Linux) | JSON | `mcpServers` |
| Global | Gemini CLI (sys-overrides) | `/etc/gemini-cli/settings.json` (Linux) | JSON | `mcpServers` |
| Project | Claude Code | `<project>/.mcp.json` | JSON | `mcpServers` |
| Project | Cursor | `<project>/.cursor/mcp.json` | JSON | `mcpServers` |
| Project | Gemini CLI | `<project>/.gemini/settings.json` | JSON | `mcpServers` |
| Project | Codex | `<project>/.codex/config.toml` | TOML | `[mcp_servers.*]` |
| Extension | Gemini CLI | `~/.gemini/extensions/*/gemini-extension.json` | JSON | MCP server entries in manifest |

## Settings Files

| Scope | Tool | Path |
|-------|------|------|
| Global | Claude Code | `~/.claude/settings.json`, `~/.claude/settings.local.json` |
| Project | Claude Code | `<project>/.claude/settings.json`, `<project>/.claude/settings.local.json` |
| Global | Codex | `~/.codex/config.toml` |
| Project | Codex | `<project>/.codex/config.toml` |

## Context Guidance Files

| Tool | File | Notes |
|------|------|-------|
| Claude Code | `CLAUDE.md` | Project root and subdirectories |
| Multi-agent | `AGENTS.md` | Agent coordination instructions |
| Gemini CLI | `GEMINI.md` | Global `~/.gemini/GEMINI.md` + project-level |
| Codex | `AGENTS.md` | Same file as multi-agent |

## Security Patterns to Detect

Grep all discovered config files for these patterns:

| Pattern | Severity | What It Catches |
|---------|----------|----------------|
| `Bearer\s` | CRITICAL | Bearer tokens in args or headers |
| `Authorization:` | CRITICAL | Auth headers with inline credentials |
| `api[_-]?key` (case-insensitive) | CRITICAL | API keys in env blocks or values |
| `password` (case-insensitive) | CRITICAL | Passwords in config |
| `ghp_[0-9a-zA-Z]{36}` | CRITICAL | GitHub Personal Access Tokens |
| `sk-[a-zA-Z0-9]{20,}` | CRITICAL | OpenAI / Anthropic API keys |
| `-----BEGIN (RSA\|EC\|OPENSSH) PRIVATE KEY-----` | CRITICAL | Private key material embedded in config |
| `[?&]token=` | CRITICAL | Tokens passed as URL query parameters (logged in server access logs) |
| `[?&]api_key=` | CRITICAL | API keys passed as URL query parameters |
| `[?&]key=` | HIGH | Generic key passed as URL query parameter |
| `secret` (case-insensitive) | HIGH | Secret keys or tokens |
| `postgresql://.*:.*@` | HIGH | PostgreSQL URLs with embedded credentials |
| `mysql://.*:.*@` | HIGH | MySQL URLs with embedded credentials |
| `mongodb(\+srv)?://.*:.*@` | HIGH | MongoDB URLs with embedded credentials |
| `http://` (non-localhost remote) | HIGH | Unencrypted remote MCP endpoints |
| `credential` (case-insensitive) | MEDIUM | Credential references |

Combined grep command for scanning:

```bash
grep -inE 'bearer |authorization:|api[_-]?key|password|secret|credential|ghp_[0-9a-zA-Z]{36}|sk-[a-zA-Z0-9]{20,}|-----BEGIN.*(RSA|EC|OPENSSH) PRIVATE KEY' <file>
grep -E 'postgresql://|mysql://|mongodb(\+srv)?://' <file>
grep -E 'http://' <file>  # flag non-localhost HTTP endpoints
grep -E '[?&](token|api_key|key)=' <file>  # tokens in URL parameters
```

## Project Discovery

### Claude Code

Claude Code stores project metadata in `~/.claude/projects/`. Directory names encode the project path:
- `/Users/username/codes/my-project` becomes `-Users-username-codes-my-project`
- The encoding replaces every `/` with `-` and prepends a leading `-`
- **Decoding** (handles hyphenated path segments like `data-pipeline`):
  1. Strip the leading `-` from the directory name
  2. Split on `-` to get candidate segments
  3. Reconstruct by greedy longest-match: from the left, join segments with `-` and check if the resulting prefix exists as a directory on disk; when a valid directory boundary is found, insert `/` and continue
  4. Verify the fully decoded path exists before scanning
- Do NOT use naive "split on `-` and rejoin with `/`" — this breaks for paths containing hyphens

### Codex

Codex stores trusted project paths in `~/.codex/config.toml` using TOML table headers:

```toml
[projects."/Users/username/codes/my-project"]
trust_level = "full"
```

To discover project paths:

```bash
grep -E '^\[projects\.' ~/.codex/config.toml 2>/dev/null
```

Extract the quoted path from each `[projects."<path>"]` entry. Do NOT grep for `project_trusts` — that key does not exist in the Codex config format.

## Environment Variable Limitations

Not all tools support `${ENV_VAR}` interpolation in config files:

| Tool | Env Var Support | Notes |
|------|----------------|-------|
| Claude Code CLI | Yes | Supports `${VAR}` in JSON config values |
| Codex | Yes | Supports `${VAR}` in TOML config values |
| Claude Desktop | No | Values are used literally; no interpolation |
| Cursor | No | Values are used literally; no interpolation |
| Windsurf | No | Values are used literally; no interpolation |
| Gemini CLI | No | Values are used literally; no interpolation |

When recommending env-var fixes for credentials, always note which tools cannot use this approach and suggest alternatives (strict file permissions, tool-specific credential stores).

---
name: organize-skill-mcp
version: 1.0.0
description: "ONLY trigger when the user explicitly types /organize-skill-mcp. Scans all skill installations and MCP server configs across Claude Code, Claude Desktop, Cursor, Windsurf, Codex, and Gemini CLI at global and project scopes. Visualizes the current state, detects issues (duplicates, broken symlinks, security risks, inconsistencies), and suggests cleanup actions."
---

# Organize Skills & MCP Configs

Audit all skill installations and MCP server configurations across every AI coding tool on this machine. Produce a consolidated report, flag issues, and offer actionable fixes.

**Read `references/config-paths.md` before starting** — it lists every known config file location, format, and security pattern.

**Output rules (STRICT — follow exactly):**
- **Tables: Use ONLY pipe-delimited markdown tables** (`| col | col |` with `|---|---|` separator). NEVER use box-drawing Unicode characters (`┌`, `─`, `┐`, `│`, `├`, `┤`, `└`, `┘`). This is non-negotiable — box-drawing breaks copy-paste and grep.
- If a phase or check produces zero findings, output a single line: `No issues found.`
- Severity prefixes always appear at the start of the line: `[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]`, `[INFO]`.
- **Verify counts** before outputting the Scan Summary: recount skills, servers, and projects from your collected data. Do not estimate.

**Status tags** used throughout this skill:
- `[OK]` — symlink resolves directly to a git-tracked source
- `[OK - copies]` — skill is installed as a direct copy (not symlinked) but a matching skill exists in another global directory or source repo. To determine this: compare the skill name against skills found in other directories. If the same skill name exists as a git-tracked source elsewhere (e.g., in `~/.agents/skills/`), use `[OK - copies]`. Common for Gemini CLI which typically copies skills rather than symlinking.
- `[OK - extension]` — Gemini extension-based skill, expected to be a direct install
- `[INDIRECT]` — symlink resolves through 2+ hops (show hop details inline)
- `[BROKEN]` — symlink target does not exist
- `[NO SOURCE REPO]` — direct directory with no git tracking AND no matching skill name found in any other global directory or source repo. Use this only after confirming no copy exists elsewhere.
- `[PROJECT]` — project-scoped skill (expected to be direct)
- `[UNLINKED]` — skill exists in a source repo but is not symlinked into any global skills directory

---

## Phase 1: Scan — Discover Everything

Work through each sub-step. Collect results silently — do not output until Phase 2.

### 1a. Detect Platform

```bash
uname -s
```

Set the Claude Desktop config path:
- **Darwin**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **WSL**: check both Linux path and `/mnt/c/Users/*/AppData/Roaming/Claude/claude_desktop_config.json`

### 1b. Global Skills

Scan each global skills directory. For each entry, determine if it is a symlink or direct directory:

```bash
# Claude Code global skills
ls -la ~/.claude/skills/ 2>/dev/null

# Shared agent skills
ls -la ~/.agents/skills/ 2>/dev/null

# Gemini CLI skills
ls -la ~/.gemini/skills/ 2>/dev/null
```

For every symlink found, resolve to its canonical target:

```bash
readlink -f <symlink-path>
```

For every directory (symlink or direct), extract the skill name from SKILL.md frontmatter:

```bash
head -5 <skill-dir>/SKILL.md 2>/dev/null
```

Group resolved symlink targets by their parent directory to identify **source repos**. Also check if each global skills directory itself is git-tracked (`git -C <dir> rev-parse --git-dir 2>/dev/null`). A git-tracked directory containing direct (non-symlinked) skills is itself a source repo — count it alongside symlink-resolved source repos.

### 1c. Unlinked Skills Detection

For each identified source repo, list all subdirectories that contain a SKILL.md. Compare against the set of skills already symlinked into global directories. Any skill in a source repo that is not symlinked anywhere gets flagged as `[UNLINKED]`.

```bash
# For each source repo discovered in 1b:
ls -d <source-repo>/*/SKILL.md 2>/dev/null
```

### 1d. Project-Level Discovery

Discover all projects the user has worked with:

```bash
ls ~/.claude/projects/ 2>/dev/null
```

Each directory name encodes a filesystem path (e.g., `-Users-username-codes-my-project` encodes `/Users/username/codes/my-project`). The encoding replaces every `/` with `-` and prepends a leading `-`.

**Decoding strategy** (handles names containing hyphens like `data-pipeline`):
1. Strip the leading `-` from the directory name.
2. Split on `-` to get candidate segments.
3. Reconstruct paths by trying longest-match-first: start from the left, greedily join segments with `-` and check if the resulting prefix exists as a directory on disk. When a valid directory boundary is found, insert a `/` and continue.
4. Verify the fully decoded path exists before scanning.

Example: `-Users-huijokim-codes-data-pipeline` — try `/Users` (exists), then `/Users/huijokim` (exists), then `/Users/huijokim/codes` (exists), then `/Users/huijokim/codes/data-pipeline` (exists) — decoded.

Also check Codex for trusted project paths:

```bash
grep -E '^\[projects\.' ~/.codex/config.toml 2>/dev/null
```

For each discovered project path that exists on disk, check for:

```bash
# Project-level skills
ls -la <project>/.claude/skills/ 2>/dev/null

# Project-level MCP servers
cat <project>/.mcp.json 2>/dev/null
cat <project>/.cursor/mcp.json 2>/dev/null
cat <project>/.gemini/settings.json 2>/dev/null
cat <project>/.codex/config.toml 2>/dev/null

# Project-level settings
cat <project>/.claude/settings.local.json 2>/dev/null
cat <project>/.claude/settings.json 2>/dev/null

# Context guidance files
ls <project>/CLAUDE.md <project>/AGENTS.md <project>/GEMINI.md 2>/dev/null
```

### 1e. Global MCP Servers

Read each global MCP config file. Paths and formats are in `references/config-paths.md`.

```bash
# Claude Code CLI
cat ~/.claude/mcp.json 2>/dev/null

# Claude Desktop (use platform-specific path from 1a)
cat "<claude-desktop-path>" 2>/dev/null

# Cursor
cat ~/.cursor/mcp.json 2>/dev/null

# Windsurf
cat ~/.codeium/windsurf/mcp_config.json 2>/dev/null

# Codex (TOML format — read the full file, parse mcp_servers section)
cat ~/.codex/config.toml 2>/dev/null

# Gemini CLI
cat ~/.gemini/settings.json 2>/dev/null

# Gemini extensions
ls ~/.gemini/extensions/*/gemini-extension.json 2>/dev/null
```

For each config, extract: server name, transport type (stdio vs HTTP), command or URL, environment variables.

### 1f. Credentials Scan

Grep all discovered config files for security-sensitive patterns listed in `references/config-paths.md`. Use the patterns defined there — do not duplicate them here.

Check file permissions on every file that contains a match:

```bash
ls -la <file>
```

---

## Phase 2: Visualize — Present Current State

First, output a **Scan Summary** block:

```
Scan Summary
============
Platform:       Darwin (macOS) / Linux / WSL
Global skills:  N across K directories
Source repos:   N identified
Projects:       N discovered (M with configs)
MCP servers:    N unique across P tools
Issues:         C critical, H high, M medium, L low
```

Then present each section below.

### 2a. Skills Map

Display a tree grouped by scope. For each skill show: name, symlink target (if applicable), and status tag. For `[INDIRECT]` entries, show the hop chain inline. For `[BROKEN]` entries, show the dead target.

```
Skills Inventory
================

Source Repos:
  /path/to/skills-repo/          (N skills, git-tracked)
  /path/to/other-repo/skills/    (M skills, git-tracked)

GLOBAL — ~/.claude/skills/
  skill-a  -> /path/to/repo/skill-a             [OK]
  skill-b  -> ../../.agents/skills/skill-b       [INDIRECT]
             hop 1: -> ~/.agents/skills/skill-b
             hop 2: -> /canonical/source/skill-b  (FINAL)
  skill-c  -> /path/that/no/longer/exists        [BROKEN]

GLOBAL — ~/.agents/skills/
  skill-d  (direct directory)                    [NO SOURCE REPO]
  skill-e  -> /path/to/repo/skill-e             [OK]

GLOBAL — ~/.gemini/skills/
  skill-f  (direct directory)                    [OK - copies]

UNLINKED — /path/to/skills-repo/
  skill-g                                        [UNLINKED]

PROJECT — /path/to/project-x/.claude/skills/
  skill-h  (direct dir)                          [PROJECT]
```

### 2b. MCP Servers Cross-Tool Matrix

Show every discovered MCP server as a row, every tool as a column. Annotate cells to show status:
- `OK` — present and configured
- `MISSING` — absent in this tool but present in others (cross-ref: issue H-number)
- `DIVERGENT` — config differs from other tools (cross-ref: issue M-number)
- `DISABLED` — explicitly disabled
- `-` — intentionally absent or not applicable

```
MCP Server Configuration Matrix
================================

| Server    | Claude CLI | Desktop | Cursor | Windsurf | Codex    | Gemini |
|-----------|-----------|---------|--------|----------|----------|--------|
| server-a  | OK        | OK      | OK     | OK       | OK       | -      |
| server-b  | OK        | MISSING | OK     | -        | -        | -      |
| server-c  | OK        | -       | OK     | OK       | DISABLED | -      |
```

If a server has different configurations across tools (e.g., different endpoints or args), add a footnote row explaining the difference.

**Note:** Claude Desktop does not support `${ENV_VAR}` interpolation in config values. Cursor and Windsurf have the same limitation. Only Claude Code CLI and Codex support environment variable references. If env vars are detected in Desktop/Cursor/Windsurf configs, flag as issue.

### 2c. Project Config Coverage Matrix

Show which projects have which types of configuration:

```
Project Configuration Coverage
==============================

| Project               | Skills | MCP | Settings | Guidance  |
|-----------------------|--------|-----|----------|-----------|
| ~/codes/project-x     | 4      | -   | YES      | AGENTS.md |
| ~/codes/project-y     | -      | YES | YES      | CLAUDE.md |
| ~/codes/project-z     | -      | -   | YES      | -         |
| ~/personal/project-w  | -      | YES | YES      | CLAUDE.md |
```

---

## Phase 3: Issues & Fixes

Run each check. Present findings as a list grouped by severity. Each entry includes the finding, its severity, and the fix command — all in one place. Use composite IDs: `C1, C2...` (Critical), `H1, H2...` (High), `M1, M2...` (Medium), `L1, L2...` (Low).

Cross-reference Phase 2 evidence where applicable (e.g., "see Skills Map, GLOBAL — ~/.claude/skills/").

### Security (Critical / High)

**Credential Detection**

Flag every finding from Phase 1f using the patterns and severities defined in `references/config-paths.md`.

For each finding, include: file path, the offending line (with credentials partially redacted — show first 8 chars + `...`), and the fix.

Example entries:

```
[CRITICAL] C1: Hardcoded Bearer token in ~/.cursor/mcp.json
  Line: "Authorization": "Bearer eyJhbGci..."
  See: MCP Matrix row "server-b", Cursor column
  Fix: Move token to environment variable in shell profile:
    echo 'export MCP_AUTH_TOKEN="<token-value>"' >> ~/.zshrc
    Then update config to reference the variable (Claude CLI/Codex only).
    WARNING: Claude Desktop, Cursor, and Windsurf do NOT support ${ENV_VAR}
    interpolation. For these tools, use tool-specific credential stores or
    keep the token in the config file with strict file permissions (chmod 600).
```

```
[CRITICAL] C2: Token embedded in URL query parameter in ~/.claude/mcp.json
  Line: "url": "https://api.example.com/mcp?token=sk-abc12345..."
  Fix: Move token to Authorization header or environment variable.
    Tokens in URL parameters are logged in server access logs and browser history.
```

```
[CRITICAL] C3: Same credential appears in 3 files
  Files: ~/.claude/mcp.json, ~/.cursor/mcp.json, ~/Library/.../claude_desktop_config.json
  Risk: Single credential compromise affects all tools.
  Fix: Rotate the credential, then use per-tool tokens where possible.
```

```
[HIGH] H1: HTTP endpoint for remote MCP server in ~/.claude/mcp.json
  Line: "url": "http://remote-host:8080/mcp"
  Fix: Switch to HTTPS if the server supports it:
    Change "http://" to "https://" in the URL.
    If HTTPS is unavailable, document the accepted risk.
```

```
[HIGH] H2: Database connection string with credentials in ~/.codex/config.toml
  Line: env = { "DB_URL" = "postgresql://user:pass123...@host/db" }
  Fix: Move credentials to shell environment:
    echo 'export DB_URL="postgresql://user:pass@host/db"' >> ~/.zshrc
```

```
[MEDIUM] M1: Config file permissions too broad: ~/.claude/mcp.json (644)
  Fix: chmod 600 ~/.claude/mcp.json
```

```
[INFO] I1: Gemini CLI system-overrides file present — enterprise policy may silently override user config.
```

**For overly broad file permissions:**

```bash
chmod 600 <file-with-secrets>
```

### Broken / Indirect Symlinks (High)

For each broken symlink (cross-ref: Skills Map `[BROKEN]` entries):

```
[HIGH] H3: Broken symlink: ~/.claude/skills/skill-c
  Target: /path/that/no/longer/exists
  See: Skills Map, GLOBAL — ~/.claude/skills/
  Fix:
    rm ~/.claude/skills/skill-c
    ln -s <correct-target> ~/.claude/skills/skill-c
```

For each indirect chain (cross-ref: Skills Map `[INDIRECT]` entries):

```
[HIGH] H4: Indirect symlink chain: ~/.claude/skills/skill-b (2 hops)
  See: Skills Map, GLOBAL — ~/.claude/skills/
  Fix:
    rm ~/.claude/skills/skill-b
    ln -s /canonical/source/skill-b ~/.claude/skills/skill-b
```

### MCP Inconsistencies (Medium)

Compare each server across all tools where it appears. Flag:
- **Missing**: server exists in some tools but not others
- **Divergent**: same server name, different config (endpoint, args, env)
- **Disabled**: server marked as disabled in one tool but active in others

```
[MEDIUM] M2: server-b missing from Claude Desktop
  Present in: Claude CLI, Cursor
  See: MCP Matrix row "server-b"
  Fix: Add to Desktop config:
    {snippet for claude_desktop_config.json}
```

### Orphaned / Unlinked Skills (Medium)

Skills that are direct directories (not symlinks) outside of a project scope, with no `.git` directory in their ancestry:

```
[MEDIUM] M3: Orphaned skill: ~/.agents/skills/skill-d (no git tracking)
  Fix: Move into source skills repo, then symlink:
    mv ~/.agents/skills/skill-d /path/to/skills-repo/skill-d
    ln -s /path/to/skills-repo/skill-d ~/.agents/skills/skill-d
```

Unlinked skills from source repos:

```
[LOW] L1: Unlinked skill in source repo: /path/to/skills-repo/skill-g
  Not symlinked into any global skills directory.
  Fix: ln -s /path/to/skills-repo/skill-g ~/.claude/skills/skill-g
```

### Informational (Low)

Note intentional differences (project-scoped configs are expected to differ from global).

```
[INFO] I2: Project ~/codes/project-x has project-level MCP servers — this is expected and not an inconsistency.
```

---

## Phase 4: Execute (Optional, User-Confirmed)

Present a compact fix summary table:

```
Recommended Fixes
=================

| ID  | Severity | Summary                              |
|-----|----------|--------------------------------------|
| C1  | CRITICAL | Move Bearer token to env var         |
| C2  | CRITICAL | Remove token from URL parameter      |
| H1  | HIGH     | Switch HTTP to HTTPS endpoint        |
| H3  | HIGH     | Remove broken symlink skill-c        |
| H4  | HIGH     | Flatten indirect symlink skill-b     |
| M1  | MEDIUM   | Tighten file permissions             |
| M2  | MEDIUM   | Add server-b to Desktop config       |
| M3  | MEDIUM   | Move orphaned skill-d to repo        |
| L1  | LOW      | Symlink unlinked skill-g             |
```

Ask the user:

> Which fixes should I apply? You can specify IDs (e.g., C1, H3, M1), a severity level (e.g., "all critical"), or "none" to keep the report only.

For each approved fix:
1. Show the exact command
2. Wait for explicit confirmation before running
3. Run the command
4. Verify the result (`readlink -f`, `cat`, `ls -la` as appropriate)
5. Report success or failure

**Never auto-execute. Never batch without per-action confirmation.**

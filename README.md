# Skills

My personal skills.


| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [analyze-git-style](./analyze-git-style) | 1.0.0 | Analyze git commit history across all repos, score message quality, and generate a teaching-focused CLI report | — |
| [excalidraw-diagram](./excalidraw-diagram) | 1.0.0 | Create Excalidraw diagram JSON files that make visual arguments | Improved from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) |
| [get-feedback-markdown-plan](./get-feedback-markdown-plan) | 1.0.0 | Evaluate inline feedback annotations on a markdown plan by verifying each critique (feedback from [review-markdown-plan](./review-markdown-plan)) | — |
| [grill-with-llm-wiki](./grill-with-llm-wiki) | 1.0.0 | Stress-tests a plan against an existing LLM-maintained wiki (articles, index, log, raw sources). Read-only companion to [simple-llm-wiki](./simple-llm-wiki) | — |
| [organize-skill-mcp](./organize-skill-mcp) | 1.0.0 | Scan all skill and MCP server configurations across Claude Code, Claude Desktop, Cursor, Windsurf, Codex, and Gemini CLI — global and per-project — and suggest cleanup | — |
| [pair-consult](./pair-consult) | 1.2.0 | Bounded Claude ↔ Codex consultation on one question — A proposes, B reviews, A responds, B re-reviews, A synthesizes and asks user. Round count and peer effort configurable | — |
| [pair-goal](./pair-goal) | 1.0.0 | **Plugin (6 skills).** Goal-driven improvement loop: understand what needs improving → forge a `/goal` completion condition → each `/goal` turn, race a different-model Claude against Codex in separate git worktrees and merge the measured winner → summarize → open a PR. Shared state in `.pairgoal/` | — |
| [pair-optimize](./pair-optimize) | 1.1.0 | Bounded Claude ↔ Codex optimization loop for a DuckDB/SQL query or hot Python path — A measures a baseline + proposes candidates, B challenges, A benchmarks, B audits the measurement, A synthesizes. Hard rule: no win kept without a measured speedup AND identical output | — |
| [pair-ratchet](./pair-ratchet) | 1.0.0 | Outer loop over [pair-optimize](./pair-optimize): profile a whole hot path/module/pipeline, optimize the dominant bottleneck, then the next — each kept win ratchets the baseline — until no session yields a measured win (loop-until-dry) or a session cap is hit. One final aggregated report | — |
| [review-markdown-plan](./review-markdown-plan) | 1.0.0 | Review other agent's plan by section, annotating only concretely wrong steps | — |
| [simple-llm-wiki](./simple-llm-wiki) | 1.0.0 | Build and maintain a personal LLM-powered knowledge base (Ingest / Query / Lint) over a raw/ + wiki/ directory pair | Adapted from [astro-han/karpathy-llm-wiki](https://github.com/astro-han/karpathy-llm-wiki) |

### pair-consult flags

```
/pair-consult "<question>"                       # default: 5 rounds
/pair-consult "<question>" --number 7            # n rounds (odd, ≥3)
/pair-consult "<question>" --model high|xhigh    # peer reasoning effort
```

## Install

```bash
npx skills add ccomkhj/skills
```

`long-haul` and `pair-goal` are multi-skill plugins, so their bundled skills live one level deeper than the flat scan looks. To install them via `npx skills`, add `--full-depth`:

```bash
npx skills add ccomkhj/skills --full-depth
```

### As Claude Code plugins

`long-haul` and `pair-goal` are also published as Claude Code plugins (bundled skills + shared state). Inside Claude Code:

```
/plugin marketplace add ccomkhj/skills
/plugin install long-haul@ccomkhj-skills
/plugin install pair-goal@ccomkhj-skills
```

### Manual setup

Alternatively, clone the repo and symlink it:

```bash
git clone git@github.com:ccomkhj/skills.git

# For Claude Code
ln -s skills ~/.claude/skills

# For other agents (e.g. Gemini CLI, Cursor, Codex)
ln -s skills ~/.agents/skills
```

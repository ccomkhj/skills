# Skills

My personal skills.


| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [analyze-git-style](./analyze-git-style) | 1.0.0 | Analyze git commit history across all repos, score message quality, and generate a teaching-focused CLI report | — |
| [excalidraw-diagram](./excalidraw-diagram) | 1.0.0 | Create Excalidraw diagram JSON files that make visual arguments | Improved from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) |
| [get-feedback-markdown-plan](./get-feedback-markdown-plan) | 1.0.0 | Evaluate inline feedback annotations on a markdown plan by verifying each critique (feedback from [review-markdown-plan](./review-markdown-plan)) | — |
| [grill-me](./grill-me) | 1.0.0 | Relentlessly interview the user about a plan, design, or data-related product — one question at a time, each paired with a recommended answer — to expose assumptions and unthought ideas | From [mattpocock/skills](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md) |
| [grill-with-docs](./grill-with-docs) | 1.0.0 | Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) inline as decisions crystallise | Improved from [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs) |
| [grill-with-llm-wiki](./grill-with-llm-wiki) | 1.0.0 | Stress-tests a plan against an existing LLM-maintained wiki (articles, index, log, raw sources). Read-only companion to [simple-llm-wiki](./simple-llm-wiki) | — |
| [organize-skill-mcp](./organize-skill-mcp) | 1.0.0 | Scan all skill and MCP server configurations across Claude Code, Claude Desktop, Cursor, Windsurf, Codex, and Gemini CLI — global and per-project — and suggest cleanup | — |
| [pair-coding](./pair-coding) | 1.0.0 | Coordinate a Claude Code ↔ Codex pair-programming session with mutual review at every stage (spec, plan, each code step) via shared `.pair/` files | — |
| [pair-consult](./pair-consult) | 1.1.0 | Bounded Claude ↔ Codex consultation on one question — A proposes, B reviews, A responds, B re-reviews, A synthesizes and asks user. Round count and peer effort configurable. Lighter sibling to [pair-coding](./pair-coding) | — |
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

### Manual setup

Alternatively, clone the repo and symlink it:

```bash
git clone git@github.com:ccomkhj/skills.git

# For Claude Code
ln -s skills ~/.claude/skills

# For other agents (e.g. Gemini CLI, Cursor, Codex)
ln -s skills ~/.agents/skills
```

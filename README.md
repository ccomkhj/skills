# Skills

My personal skills, grouped by family.

## Long-horizon & multi-agent loops

Orchestrators that drive a goal to completion over many turns. `long-haul` and `dual-haul` are multi-skill Claude Code plugins — the orchestrator plus its phase skills ship together.

### long-haul — solo goal loop (plugin, v1.2.0)

| Skill | Description |
|-------|-------------|
| [long-haul](./long-haul) | Orchestrator: sharpen a spec → forge a `/goal` → haul toward it turn after turn in a git worktree, each turn choosing explore (fresh approach) vs exploit (refine incumbent), keeping only measured wins, until the goal holds |
| [haul-spec](./long-haul/skills/haul-spec) | Phase 1 — turn the ask into a located, verifiable spec (`.longhaul/SPEC.md`) |
| [haul-goal](./long-haul/skills/haul-goal) | Phase 2 — turn the spec into a `/goal`-ready completion condition (`.longhaul/GOAL.md`) |
| [haul-loop](./long-haul/skills/haul-loop) | Phase 3 — the per-turn explore/exploit loop; `--background` detaches an overnight driver |
| [haul-ship](./long-haul/skills/haul-ship) | Phase 4 — report goal-vs-achieved, commit the incumbent, open a PR |

### dual-haul — Claude-vs-Codex race (plugin, v1.0.0)

| Skill | Description |
|-------|-------------|
| [dual-haul](./dual-haul) | Orchestrator: race a different-model Claude against Codex (each in its own worktree) round by round under a `/goal`, merge the measured winner, then ship a PR. Shared state in `.dualhaul/` |
| [dual-understand](./dual-haul/skills/dual-understand) | Phase 1 — improvement-focused brainstorming (`.dualhaul/UNDERSTANDING.md`) |
| [dual-goal](./dual-haul/skills/dual-goal) | Phase 2 — turn the understanding into a `/goal`-ready condition (`.dualhaul/GOAL.md`) |
| [dual-loop](./dual-haul/skills/dual-loop) | Phase 3 — the per-turn race: two implementers, judge against the goal, merge the winner |
| [dual-report](./dual-haul/skills/dual-report) | Phase 4 — report goal-vs-achieved and who won each round (`.dualhaul/SUMMARY.md`) |
| [dual-ship](./dual-haul/skills/dual-ship) | Phase 5 — commit on a feature branch, open a PR, tear down worktrees |

### Bounded consultation & optimization

| Skill | Version | Description |
|-------|---------|-------------|
| [single-consult](./single-consult) | 1.0.0 | Fast in-session sibling of pair-consult: the reviewer is an **internal Claude subagent** (default `fable`), not an external Codex peer — so no shared-state/handoff machinery. Same propose · review · respond · re-review · synthesize shape. `--model sonnet\|opus\|fable`, `--depth`, `--number` |
| [pair-consult](./pair-consult) | 1.2.0 | Bounded consultation on one question — A proposes, B reviews, A responds, B re-reviews, A synthesizes and asks the user. Round count and peer effort configurable |
| [pair-optimize](./pair-optimize) | 1.1.0 | Optimization loop for a DuckDB/SQL query or hot Python path — A measures a baseline + proposes, B challenges, A benchmarks, B audits. Hard rule: no win kept without a measured speedup AND identical output |
| [pair-ratchet](./pair-ratchet) | 1.0.0 | Outer loop over [pair-optimize](./pair-optimize): profile a whole hot path, optimize the dominant bottleneck then the next — each kept win ratchets the baseline — until no session yields a win (loop-until-dry) or a session cap trips |

**Flags**

```
/pair-consult "<question>"                        # default: 5 rounds
/pair-consult "<question>" --number 7             # n rounds (odd, ≥3)
/pair-consult "<question>" --model high|xhigh     # external peer effort

/single-consult "<question>"                      # internal Claude reviewer, default fable
/single-consult "<question>" --model opus         # reviewer model: sonnet|opus|fable
/single-consult "<question>" --depth xhigh        # reviewer reasoning effort
```

### Unattended cleanup

| Skill | Version | Description |
|-------|---------|-------------|
| [lunch-clean-loop](./lunch-clean-loop) | 1.0.0 | Kick it off, go eat lunch: scans the codebase for readability debt, then loops up to N targets (default 5) through a fresh cleaner → reviewer → tester trio — a cleanup is kept only if an independent reviewer approves it AND a tester demonstrates identical output, else it's reverted. One `refactor:` commit per kept target on a `clean-loop/<date>` branch in its own worktree; the user's checkout is never touched. Python cleaners apply the [simplify-python](./simplify-python) ruleset |

**Usage**

```
/lunch-clean-loop                     # whole repo, N=5
/lunch-clean-loop src/pipeline --n 2  # scoped, 2 iterations
```

## Plan review

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [review-markdown-plan](./review-markdown-plan) | 1.0.0 | **Deprecated** (use pair-\*). Review a markdown plan by section, annotating only concretely wrong steps | — |
| [get-feedback-markdown-plan](./get-feedback-markdown-plan) | 1.0.0 | **Deprecated** (use pair-\*). Evaluate the inline feedback [review-markdown-plan](./review-markdown-plan) left, verifying each critique against the codebase | — |

## Skill & MCP hygiene

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [organize-skill-mcp](./organize-skill-mcp) | 1.0.0 | Scan skill and MCP configs across Claude Code, Claude Desktop, Cursor, Windsurf, Codex, and Gemini CLI — global and per-project — and suggest cleanup | — |
| [find-overlapping-skills](./find-overlapping-skills) | 1.0.0 | Collapse double-installs, cluster the rest into overlap groups, then resolve each group with the user, disabling non-keepers reversibly | — |
| [improve-skills](./improve-skills) | 1.0.0 | Fold one lesson into one existing skill — collect lessons from the session or a direct ask, propose the exact edit, gate on user confirmation + feedback, then apply to a single skill (user-invoked `/improve-skills`) | — |

## Writing & code

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [humanizer](./humanizer) | 2.8.1 | Remove signs of AI-generated writing (significance inflation, em dashes, rule of three, AI vocabulary, filler, …) so text reads as human-written; based on Wikipedia's "Signs of AI writing" | Source from [blader/humanizer](https://github.com/blader/humanizer), improved here |
| [simplify-python](./simplify-python) | 1.0.0 | Make recently written Python read better without changing behavior — idiomatic rewrites, flattened control flow, removed cruft. High-confidence, behavior-preserving rules only | — |
| [slack-comm](./slack-comm) | 1.0.0 | Summarize the current Claude session's work into a very concise 3P (Progress/Plans/Problems) Slack status report, review it in chat, then stage it as a native Slack draft (via Slack MCP) for a final look before you send. User-invoked mid-session: `/slack-comm` | 3P/tone format adapted from [anthropics/skills internal-comms](https://github.com/anthropics/skills/tree/main/skills/internal-comms) |

## Utilities

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [draw-graphology](./draw-graphology) | 1.1.0 | Data-driven network graph visualizations (interactive HTML + static PNG) with [graphology](https://graphology.github.io/) + [sigma.js](https://www.sigmajs.org/) — ForceAtlas2 layout, Louvain community colors, degree-sized hubs, and a Playwright screenshot loop so the agent validates its own render. For node-edge datasets too large to place by hand | Methodology ported from the Understand-Anything dashboard |
| [excalidraw-diagram](./excalidraw-diagram) | 1.0.0 | Create Excalidraw diagram JSON files that make visual arguments — hand-placed conceptual diagrams, vs [draw-graphology](./draw-graphology)'s computed layouts | Improved from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) |
| [loom-transcript](./loom-transcript) | 1.0.0 | Fetch a public Loom video's transcript from its share link (oEmbed + share-page scrape, stdlib Python, no auth) and summarize it. User-invoked: `/loom-transcript <url>` | — |

## Install

```bash
npx skills add ccomkhj/skills
```

`long-haul` and `dual-haul` are multi-skill plugins, so their bundled skills live one level deeper than the flat scan looks. To install them via `npx skills`, add `--full-depth`:

```bash
npx skills add ccomkhj/skills --full-depth
```

### As Claude Code plugins

`long-haul` and `dual-haul` are also published as Claude Code plugins (bundled skills + shared state). Inside Claude Code:

```
/plugin marketplace add ccomkhj/skills
/plugin install long-haul@ccomkhj-skills
/plugin install dual-haul@ccomkhj-skills
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

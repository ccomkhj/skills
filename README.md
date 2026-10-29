# Skills

My personal [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for Claude Code (most also work in Codex, Gemini CLI, …).

Each folder is one skill: a `SKILL.md` (what the agent reads) plus optional `references/`, `scripts/` and `agents/`. Three folders, `long-haul`, `dual-haul` and `product-bridge`, are **plugins** that bundle several skills under `skills/`. Versions and full details are in each `SKILL.md`.

## Long-horizon & multi-agent loops

Orchestrators that keep working toward a goal over many turns.

### long-haul — solo goal loop (plugin)

| Skill | Description |
|-------|-------------|
| [long-haul](./long-haul) | Orchestrator: spec → `/goal` → loop in a git worktree, keeping only measured wins, until the goal holds |
| [haul-spec](./long-haul/skills/haul-spec) | 1. Turn the ask into a verifiable spec (`.longhaul/SPEC.md`) |
| [haul-goal](./long-haul/skills/haul-goal) | 2. Turn the spec into a `/goal` completion condition |
| [haul-loop](./long-haul/skills/haul-loop) | 3. Per-turn explore/exploit loop; `--background` runs overnight |
| [haul-ship](./long-haul/skills/haul-ship) | 4. Report goal vs. achieved, commit, open a PR |

### dual-haul — Claude-vs-Codex race (plugin)

| Skill | Description |
|-------|-------------|
| [dual-haul](./dual-haul) | Orchestrator: Claude and Codex race round by round in separate worktrees; the measured winner is merged and shipped |
| [dual-understand](./dual-haul/skills/dual-understand) | 1. Brainstorm what to improve |
| [dual-goal](./dual-haul/skills/dual-goal) | 2. Turn it into a `/goal` condition |
| [dual-loop](./dual-haul/skills/dual-loop) | 3. Per-turn race: two implementers, judge, merge the winner |
| [dual-report](./dual-haul/skills/dual-report) | 4. Report results and who won each round |
| [dual-ship](./dual-haul/skills/dual-ship) | 5. Commit, open a PR, clean up worktrees |

### Bounded consultation & optimization

| Skill | Description |
|-------|-------------|
| [pair-consult](./pair-consult) | Two agents debate one question (propose → review → respond → synthesize), then ask you |
| [sub-consult](./sub-consult) | Faster pair-consult: a panel of reviewers (defined in `panel.toml`) runs in parallel |
| [pair-optimize](./pair-optimize) | Speed up a SQL query or hot Python path; a win is kept only if it is faster **and** gives identical output |
| [pair-ratchet](./pair-ratchet) | Repeat pair-optimize on the next bottleneck until no more wins |

```
/pair-consult "<question>" [--number 7] [--model high|xhigh]
/sub-consult  "<question>" [--number 3]
```

## Product design

### product-bridge — problem to developer handoff (plugin)

Five stages for a PM working on an existing Next.js/React app. Each runs alone; together they share one record in `.productbridge/<ID>/`.

| Skill | Description |
|-------|-------------|
| [pb-define-problem](./product-bridge/skills/pb-define-problem) | 1. Problem brief: observations, hypotheses and assumptions kept apart |
| [pb-explore-wireframes](./product-bridge/skills/pb-explore-wireframes) | 2. 2–3 different flows for the same task (Figma if available) |
| [pb-validate-direction](./product-bridge/skills/pb-validate-direction) | 3. Research plan or evidence matrix, plus your decision |
| [pb-build-prototype](./product-bridge/skills/pb-build-prototype) | 4. Prototype on a `pb/` branch in the real app |
| [pb-developer-handoff](./product-bridge/skills/pb-developer-handoff) | 5. Behavior spec, acceptance criteria, issue draft |

## Database evolution

| Skill | Description |
|-------|-------------|
| [to-dbml](./to-dbml) | Turn ORM models, migrations, SQL or a live DB into a validated [DBML](https://dbml.dbdiagram.io/docs) snapshot, with version history and migration diffs. `/to-dbml` |

## Problem framing & plan review

| Skill | Description |
|-------|-------------|
| [first-principles](./first-principles) | Clarify a problem before planning, one source-checked question at a time |
| [socrates](./socrates) | Find a recurring belief in your past prompts and question it Socratically. `/socrates` |
| [step-by-step](./step-by-step) | Explain a codebase or process as groups of blocks, each with a technical and a plain-language explanation |
| [deassemble](./deassemble) | Like step-by-step, but actually runs the code and builds an interactive report from what it observed |
| [ai-tutorial](./ai-tutorial) | Teach one AI/ML concept as an interactive HTML tutorial. `/ai-tutorial <concept>` |

## Skill & MCP hygiene

| Skill | Description |
|-------|-------------|
| [manage-context](./manage-context) | Measure what fills your context window and suggest which skills/MCPs to disable. `/manage-context` |
| [scan-sessions-and-learn](./scan-sessions-and-learn) | Review recent sessions for recurring workflows and friction, and route each lesson to the right fix |
| [organize-skill-mcp](./organize-skill-mcp) | Scan skill and MCP configs across tools (Claude, Cursor, Codex, …) and suggest cleanup |
| [find-overlapping-skills](./find-overlapping-skills) | Find duplicate or overlapping skills and disable the extras |
| [skill-flow](./skill-flow) | Audit a skill family's flow for broken handoffs and dead ends, without editing it |
| [improve-skills](./improve-skills) | Apply one lesson to one skill, after your confirmation |
| [agents-md-improver](./agents-md-improver) | Audit and improve `AGENTS.md` (shared by Claude, Codex, Gemini, …) |

## Writing & code

| Skill | Description |
|-------|-------------|
| [humanizer](./humanizer) | Remove signs of AI-generated writing. Based on [blader/humanizer](https://github.com/blader/humanizer) |
| [simplify-python](./simplify-python) | Make recent Python cleaner without changing behavior |
| [slack-comm](./slack-comm) | Turn the session's work into a short Slack report or request, saved as a draft. `/slack-comm` |

## Utilities

| Skill | Description |
|-------|-------------|
| [excalidraw-diagram](./excalidraw-diagram) | Create Excalidraw diagrams. Based on [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) |
| [loom-transcript](./loom-transcript) | Fetch and summarize a public Loom video's transcript. `/loom-transcript <url>` |
| [local-artifact](./local-artifact) | Build HTML pages into a local gallery instead of using the built-in `Artifact` tool. `/local-artifact` |

## Install

```bash
npx skills add ccomkhj/skills --full-depth   # --full-depth includes the plugin-bundled skills
```

**As Claude Code plugins** (inside Claude Code):

```
/plugin marketplace add ccomkhj/skills
/plugin install long-haul@ccomkhj-skills
/plugin install dual-haul@ccomkhj-skills
/plugin install product-bridge@ccomkhj-skills
```

**Manually:** clone and run [`sync.sh`](./sync.sh). It symlinks every skill into `~/.claude/skills` and `~/.agents/skills`, and never overwrites real files.

```bash
git clone git@github.com:ccomkhj/skills.git
./skills/sync.sh
```

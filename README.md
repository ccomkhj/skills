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
| [sub-consult](./sub-consult) | 2.0.0 | Fast sibling of pair-consult: a **reviewer panel defined in `panel.toml`** (engine, model, effort, persona per reviewer). The default panel is Fable/high (Pragmatist), Opus/xhigh (Skeptic), and Codex `gpt-6-astra`/medium (Outsider). `review.py` launches them in parallel via `claude -p` / `codex exec`, so there's no shared-state/handoff machinery. Same propose · review · respond · re-review · synthesize shape. `--number` |
| [pair-consult](./pair-consult) | 1.2.0 | Bounded consultation on one question — A proposes, B reviews, A responds, B re-reviews, A synthesizes and asks the user. Round count and peer effort configurable |
| [pair-optimize](./pair-optimize) | 1.1.0 | Optimization loop for a DuckDB/SQL query or hot Python path — A measures a baseline + proposes, B challenges, A benchmarks, B audits. Hard rule: no win kept without a measured speedup AND identical output |
| [pair-ratchet](./pair-ratchet) | 1.0.0 | Outer loop over [pair-optimize](./pair-optimize): profile a whole hot path, optimize the dominant bottleneck then the next — each kept win ratchets the baseline — until no session yields a win (loop-until-dry) or a session cap trips |

**Flags**

```
/pair-consult "<question>"                        # default: 5 rounds
/pair-consult "<question>" --number 7             # n rounds (odd, ≥3)
/pair-consult "<question>" --model high|xhigh     # external peer effort

/sub-consult "<question>"                         # every reviewer in panel.toml
/sub-consult "<question>" --number 3              # one review round, then synthesize
```

## Product design

### product-bridge — problem to developer handoff (plugin, v0.1.0)

Five skills for a PM working on an existing Next.js/React app. Each runs alone; together they share one experiment record in `.productbridge/<ID>/` that keeps proposed, done, approved and unverified claims apart, and keeps workflow approval separate from customer evidence. Figma MCP, Impeccable, repo access and the issue tracker are detected at runtime, and each falls back to an honest document when absent. Ships a `claude plugin eval` suite built from the spec's acceptance scenarios.

| Skill | Description |
|-------|-------------|
| [pb-define-problem](./product-bridge/skills/pb-define-problem) | Stage 1: problem brief with observations, hypotheses and assumptions kept apart; starts or resumes an experiment |
| [pb-explore-wireframes](./product-bridge/skills/pb-explore-wireframes) | Stage 2: 2–3 structurally different flows for the same task; real Figma only when a tool made it, otherwise a wireframe brief |
| [pb-validate-direction](./product-bridge/skills/pb-validate-direction) | Stage 3: neutral research plan, or a source-traced evidence matrix plus the human's decision record |
| [pb-build-prototype](./product-bridge/skills/pb-build-prototype) | Stage 4: isolated `pb/` branch prototype in the real app with an exact check report, or an implementation plan without repo access |
| [pb-developer-handoff](./product-bridge/skills/pb-developer-handoff) | Stage 5: behavior spec, Given/When/Then criteria, issue draft; publishes to a connected tracker only after approval |

## Database evolution

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [to-dbml](./to-dbml) | 1.0.0 | Turn ORM models, migrations, SQL DDL, a live database, or an interviewed idea into one [DBML](https://dbml.dbdiagram.io/docs) entity-model **snapshot** (physical by default, `--logical` for the readable view). `scripts/write.mjs` gates every write on the official parser, the skill's own layout conventions and `dbdiagram validate`. It also skips no-op runs, stops on hand edits (hash header) and archives each real change to `versions/<stem>_<YYYY-MM-DD_hh-mm-ss>.dbml`. When it sees two schema states it writes `schema.migration.dbml`, labelling every table and column `legacy`/`additive`/`altered`/`deprecated` (DBML custom properties) and listing removals as BREAKING. Every run prints a read-only dbdiagram.io link and copies the DBML for https://dbdiagram.io/d; `--push` updates a saved diagram. Use it over the Miro ERD when you want a maintained text file. User-invoked: `/to-dbml [source] [--logical] [--push]` | — |

## Problem framing & plan review

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [socrates](./socrates) | 1.0.0 | `/socrates` only. Mines your past Claude Code prompts (`scripts/collect.py`: this project's last 10 sessions, or `--all` / `--days N`), finds one recurring unsupported belief, and questions it one quote-backed question per turn until aporia, then debriefs with one action for today and three steps for the week | Adapted from a viral Socratic-method prompt ([YouTube Short](https://www.youtube.com/shorts/o11cd72Jr7M)) |
| [first-principles](./first-principles) | 1.0.0 | Clarify a problem before planning through a brief, source-backed interview — one high-leverage question per turn, factual premises checked against code/docs/web and cited, assumptions labelled as such. Ends with an agreed problem frame (outcome, facts, constraints, assumptions/unknowns, implication + one next step), not an implementation plan. Use for first-principles thinking or to challenge a proposed solution's assumptions before doing work | — |
| [step-by-step](./step-by-step) | 1.0.0 | Explain a codebase, document, problem, or process as a scannable hierarchy: split it into purpose-based blocks clustered into groups, open with a whole-system overview and group map, then give every group and block adjacent **technical** (inputs, outputs, dependencies, files, symbols) and **intuitive** (ten-year-old analogy, mapped back to the real concepts) explanations, each claim pinned to verified `path:Lx-Ly` / page / section citations with inference and uncertainty labelled. Optionally rendered as an interactive HTML artifact | — |
| [deassemble](./deassemble) | 1.3.0 | Runtime-grounded sibling of [step-by-step](./step-by-step): actually **run** the software (startup + one scenario), capture evidence (logs, tagged probes, framework traces, mock-backed test runs), and render a self-contained interactive report — a numbered **story** (each step with `path:line · symbol`, a technical and a ten-year-old explanation, and a badge saying observed / observed-instrumented / mock-backed / absence / not-observed) over a recorded-execution explorer (source excerpt, state snapshots, diffs, evidence, causal links). The validator rejects a step that claims stronger evidence than its events. Ships `build_report.py` (`--check`, `--template`), a jsdom smoke test, and a `report_builder.py` helper | Original bundle (2026-09-26), improved over three evaluation runs on the eve agent in `app_frontend`; see [CHANGELOG](./deassemble/CHANGELOG.md) |
| [ai-tutorial](./ai-tutorial) | 1.0.0 | Teach one AI/ML/science concept as an interactive HTML tutorial page for an ML practitioner: objective and transfer check first, then intuition → math → worked example → one-knob demo → code → pitfalls → self-checks. Numbers come from real runs, claims cite primary sources. Publishes via [local-artifact](./local-artifact)'s gallery. User-invoked: `/ai-tutorial <concept>` | Adapted from [samber/developer-tutorial](https://www.skills.sh/samber/developer-relations-skills/developer-tutorial) |

## Skill & MCP hygiene

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [manage-context](./manage-context) | 1.2.1 | Measure what fills a session's context before any work, from the session transcript (system prompt, tool schemas, skills, plugins, MCP servers, memory files). Per-item estimates are calibrated so they add up to the real first-turn usage. Mines the last 90 days of transcripts for how often each skill, MCP server, agent and built-in tool was used by the model vs. typed by you, and recommends what to convert to user-invocable-only or disable in a **bear** (conservative: never used by the model) or **bull** (aggressive: not used regularly) mode, with a reason per item. Renders an interactive HTML treemap and table where you accept recommendations or pick an action per row (name-only, user-invocable only, off, disable plugin/MCP, deny built-in tool via `permissions.deny`, never core tools) and a scope (global or this project). It flags config mismatches, e.g. `skillOverrides` on plugin skills (only the plugin switch or a manual `disable-model-invocation` frontmatter edit works there), or `disabledMcpjsonServers` on user-scope servers. The exported plan is applied with a dry run, backups and an undo file. User-invoked: `/manage-context` | — |
| [scan-sessions-and-learn](./scan-sessions-and-learn) | 1.7.1 | Retrospective over recent sessions. `scripts/scan.py` digests the last 7 days (or `--sessions N`, `--repo`, `--min-turns N`) of interactive Claude Code transcripts into a redacted summary. It drops headless runs and scratchpads, and groups worktrees under their repo. The summary covers skill chains and landmark tool flows ranked by how many sessions they recur in, recurring prompt phrases, and friction markers: rewound prompts, interrupts, rejections and repeated failures. The skill names your recurring workflows and judges the friction against an evidence floor (≥3 sessions on ≥2 days). It checks each lesson against what AGENTS.md, CLAUDE.md or the skill already says, then routes it to exactly one owner: [improve-skills](./improve-skills), [skill-flow](./skill-flow), [agents-md-improver](./agents-md-improver), or a proposed CLAUDE.md, hook or config edit. Proposes only, and keeps one `.inspect/sessions-handoff.md` up to date across runs: pending findings keep their number, run line and a check command, so a re-run reads only the sessions since the last one. `--new-skills` narrows a run to routines no skill carries yet (30 newest sessions with more than 5 turns), with confidence tiers by session count and a trigger/action outline for skill-creator. User-invoked: `/scan-sessions-and-learn` | — |
| [organize-skill-mcp](./organize-skill-mcp) | 1.0.0 | Scan skill and MCP configs across Claude Code, Claude Desktop, Cursor, Windsurf, Codex, and Gemini CLI — global and per-project — and suggest cleanup | — |
| [find-overlapping-skills](./find-overlapping-skills) | 1.0.0 | Collapse double-installs, cluster the rest into overlap groups, then resolve each group with the user, disabling non-keepers reversibly | — |
| [skill-flow](./skill-flow) | 1.0.0 | Audit a skill or skill family without editing it: build a typed dependency graph of its flow (steps, artifacts, invocations), render it with draw-graphology when installed (else the graph JSON is the deliverable), run six weak-link checks (broken handoffs, dead outputs, orphans, dangling pointers, missing criteria, ungated destruction), verify every finding with two refute-only subagents, and write the survivors to a `.inspect/` handoff file of ready-to-paste lessons for [improve-skills](./improve-skills). Reach for it after restructuring a skill family, before trusting a chain with unattended automation, or after installing/symlinking skills into a new home — the moments that leave dangling references and broken artifact contracts behind. User-invoked `/skill-flow` | — |
| [improve-skills](./improve-skills) | 1.1.0 | Fold one lesson into one existing skill — collect lessons from the session or a direct ask (e.g. one finding from an [skill-flow](./skill-flow) or [scan-sessions-and-learn](./scan-sessions-and-learn) handoff: `/improve-skills <file> F3`), propose the exact edit, gate on user confirmation + feedback, then apply to a single skill (user-invoked `/improve-skills`) | — |
| [agents-md-improver](./agents-md-improver) | 1.0.0 | Audit → score → propose targeted improvements to project-memory files, exactly like the official CLAUDE.md improver but writing into `AGENTS.md` (with `CLAUDE.md` a one-line `@AGENTS.md` reference) so the same memory is shared across Claude Code, Codex, Gemini CLI, … | Copied verbatim from [claude-md-improver](https://www.skills.sh/anthropics/claude-plugins-official/claude-md-improver), lines added to redirect the write target, discover `AGENTS.md` files and accept handoff findings |

## Writing & code

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [humanizer](./humanizer) | 2.8.1 | Remove signs of AI-generated writing (significance inflation, em dashes, rule of three, AI vocabulary, filler, …) so text reads as human-written; based on Wikipedia's "Signs of AI writing" | Source from [blader/humanizer](https://github.com/blader/humanizer), improved here |
| [simplify-python](./simplify-python) | 1.0.0 | Make recently written Python read better without changing behavior — idiomatic rewrites, flattened control flow, removed cruft. High-confidence, behavior-preserving rules only, guided by DRY (dedupe knowledge that changes together, not look-alike code), Orthogonality (wins over DRY: don't couple independent parts) and Reversibility (tiebreaker: prefer the form that's easier to change) | — |
| [slack-comm](./slack-comm) | 3.0.0 | Summarize the current Claude session's work into a concise, evidence-driven IMPACT/CAUSE/FIX Slack report (blast radius first — including what was *not* affected, root cause, fix with explicit deploy state, plus an optional NOT AN ISSUE section so ruled-out red herrings don't become phantom action items) and stage it directly as a native Slack draft (via Slack MCP) — DM to you by default; the draft is where you review and send. When the session ends on something a colleague must do (review, decide, run a check), it drafts a short **request** instead: @-mention + ask + link + when needed, why it's needed, what's updated, with `-> *…*` marking each part they must act on. User-invoked mid-session: `/slack-comm` | Tone principles adapted from [anthropics/skills internal-comms](https://github.com/anthropics/skills/tree/main/skills/internal-comms) |

## Utilities

| Skill | Version | Description | Source |
|-------|---------|-------------|--------|
| [excalidraw-diagram](./excalidraw-diagram) | 1.0.0 | Create Excalidraw diagram JSON files that make visual arguments — hand-placed conceptual diagrams | Improved from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) |
| [loom-transcript](./loom-transcript) | 1.0.0 | Fetch a public Loom video's transcript from its share link (oEmbed + share-page scrape, stdlib Python, no auth) and summarize it. User-invoked: `/loom-transcript <url>` | — |
| [local-artifact](./local-artifact) | 1.0.0 | User-invoked replacement for the built-in `Artifact` tool, which is denied in `permissions.deny` because it costs thousands of tokens in every session. It builds an HTML page under the same page contract (2–4 word title, `:root` color tokens with dark mode, CDN allowlist with pinned versions, phone-width layout, ≤16 MB). `scripts/gallery.py` keeps the pages in a local gallery (`~/.local/share/local-artifacts/<slug>/`) and can `publish` (which runs the contract checks and opens the page), `list`, `open` and `delete` them. Updating a slug keeps its `file://` link. A **Copy as JSON** button stands in for the hosted runtime when a page has to collect input. Zero context cost until you type `/local-artifact` | — |

## Install

```bash
npx skills add ccomkhj/skills
```

`long-haul`, `dual-haul` and `product-bridge` are multi-skill plugins, so their bundled skills live one level deeper than the flat scan looks. To install them via `npx skills`, add `--full-depth`:

```bash
npx skills add ccomkhj/skills --full-depth
```

### As Claude Code plugins

`long-haul`, `dual-haul` and `product-bridge` are also published as Claude Code plugins (bundled skills + shared state). Inside Claude Code:

```
/plugin marketplace add ccomkhj/skills
/plugin install long-haul@ccomkhj-skills
/plugin install dual-haul@ccomkhj-skills
/plugin install product-bridge@ccomkhj-skills
```

### Manual setup

Alternatively, clone the repo and run [`sync.sh`](./sync.sh) — it symlinks every skill (top-level and plugin-bundled) into both `~/.claude/skills` (Claude Code) and `~/.agents/skills` (Codex, Gemini CLI, …), one link per skill. Idempotent, and never clobbers a real file:

```bash
git clone git@github.com:ccomkhj/skills.git
./skills/sync.sh
```

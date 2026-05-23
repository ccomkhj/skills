---
name: run-pair-coding
description: Use when the user wants to run, smoke-test, lint, or verify the pair-coding skill — e.g. "does pair-coding still work", "test pair-coding", "run the pair-coding smoke". Drives one real round-trip between Claude Code and Codex against a throwaway repo via `smoke.sh`.
---

# run-pair-coding

Smoke-test driver for the [pair-coding](../../../SKILL.md) skill. Pair-coding's "running app" is the loop between Claude Code and Codex coordinating through `.pair/` files; this skill drives that loop programmatically so you can verify it still works end-to-end after changes.

Paths below are relative to **the `pair-coding/` directory** (the parent skill being tested), not to this skill's directory.

## Prerequisites

Both peer CLIs installed and authenticated for the current user:

```bash
command -v codex   # /opt/homebrew/bin/codex (or equivalent)
command -v claude  # /Users/<you>/.local/bin/claude (or equivalent)
```

That's it — no build step, no `apt-get`. The smoke test runs against `/tmp/`, not the current repo.

## Run (agent path)

Two modes. From this skill's directory:

```bash
# Free, no LLM. ~1 second. Checks the parent SKILL.md frontmatter and CLI availability.
./smoke.sh --lint

# Real round-trip. Calls the codex API, costs ~10¢, ~15-30s. Default mode.
./smoke.sh --smoke
```

`--smoke` does this:

1. Creates a throwaway repo at `/tmp/pair-coding-smoke-<pid>-<ts>/`.
2. Stages `.pair/CONTEXT.md`, `.pair/PROGRESS.md` (`STATUS: WAITING: codex`, `TURN: 1`, `PHASE: spec`), `.pair/DISCUSSION.md`, and `.pair/SPEC.md` for a tiny `mathlib.add` task.
3. Invokes `codex exec -s workspace-write -C <test-dir> --skip-git-repo-check "Resume the pair-coding skill ..."`.
4. Verifies that codex:
   - signed off `spec` in `PROGRESS.md`,
   - advanced `TURN` to 2,
   - set `STATUS: WAITING: claude`.
5. Prints the resulting `PROGRESS.md` and notes if codex compressed and also proposed `PLAN.md` (legitimate per the skill's "Compressed turns" rule).

Pass = exit 0 with `PASS: smoke (artifacts in /tmp/...)`. Artifacts are intentionally not cleaned up — inspect or `rm -rf` them yourself.

Verified on this machine (this session):

```
[lint] pair-coding SKILL.md at: /Users/huijokim/personal/skills/pair-coding/SKILL.md
[lint] frontmatter OK
[lint] codex: /opt/homebrew/bin/codex
[lint] claude: /Users/huijokim/.local/bin/claude
PASS: lint
[smoke] test dir: /tmp/pair-coding-smoke-24627-1779534404
[smoke] invoking codex (this calls the real API; ~10c)...
[smoke] PROGRESS.md after codex turn 2:
  STATUS: WAITING: claude
  TURN: 2
  ...
  - [x] spec — proposed by claude (T1), approved by codex (T2)
  - [ ] plan — proposed by codex (T2), awaiting claude review
[smoke] bonus: codex compressed and also proposed PLAN.md
PASS: smoke (artifacts in /tmp/pair-coding-smoke-24627-1779534404)
```

## Run (human path)

Same — there's no GUI. Run `./smoke.sh --smoke` and read the output.

## What the smoke does NOT cover

- **Full 5-turn loop.** The smoke runs one codex turn; the back-and-forth past that point (claude reviewing the plan, implementing code, codex reviewing) isn't exercised. The live end-to-end run that produced the parent skill was a 5-turn walkthrough done by hand in a Claude Code session — re-run that manually if you change protocol semantics.
- **`DISCUSSION.md` round-trips.** The staged task has no disagreement, so the discussion-resolution code path stays cold. Worth a separate smoke if you change that part of the protocol.
- **`nohup` background handoff.** The smoke calls `codex exec` in foreground for observability. The skill's prescribed `nohup … & disown` handoff is not exercised here.
- **Claude as peer.** Only `codex exec` is invoked; `claude -p` is only checked for presence, not actually called. The live end-to-end run in the parent skill's development session exercised both.

## Gotchas

- **Each `--smoke` costs money** (~10¢ in codex API tokens). Use `--lint` in iteration loops.
- **Codex must be authenticated.** Run `codex login` first if you see auth errors in `.pair/turn-2-codex.log`.
- **The staged `PROGRESS.md` says `TURN: 1`** even though it's not a real turn — the smoke pretends "claude already did T1, now it's codex's turn". This is the cheapest way to start the loop mid-flight; just be aware when reading the test dir's turn log.
- **Compressed turns are PASS, not FAIL.** Codex often signs off the spec AND proposes the plan in the same turn. The skill allows this (see Compressed Turns section). The smoke explicitly tolerates it and prints a bonus line.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `FAIL: codex exec returned non-zero` | Tail `/tmp/pair-coding-smoke-*/.pair/turn-2-codex.log` — usually auth (`codex login`) or a network issue. |
| `FAIL: STATUS did not transition to 'WAITING: claude'` | Codex ran but didn't follow the protocol. Read the log file — likely a regression in the parent `SKILL.md` (e.g., frontmatter broken so codex couldn't auto-discover the skill). |
| Smoke hangs > 2 minutes | Codex may be doing a slow operation. Cancel with Ctrl-C, then `ps aux \| grep codex` — if codex's child `claude -p` is hung, kill it by PID (never `killall claude` — see parent skill's gotchas). |
| `FAIL: <bin> CLI not on PATH` | Install: `brew install codex` and `npm install -g @anthropic-ai/claude-code` (or wherever your build comes from). |

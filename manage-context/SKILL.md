---
name: manage-context
version: 1.0.1
description: Measure what fills a Claude Code session's context before any work (system prompt, tools, skills, plugins, MCP servers, memory files), render it as an interactive HTML treemap and table, and apply the per-item changes the user picks there (user-invocable only, off, disable plugin/MCP; global or this project) with a dry run and undo. Use when the user asks why the context is large, what uses tokens, or wants to slim skills, plugins or MCP servers.
---

# Manage context

Two scripts do the work. Don't edit config files by hand in this skill.

- `scripts/scan.py` reads the session transcript, which records exactly what was
  injected, and maps each item to the setting that controls it. It writes
  `context-report.html` plus `context-report.json`.
- `scripts/apply_plan.py` turns the plan exported from the HTML into JSON edits.
  It dry-runs by default, and `--apply` writes backups plus an undo file.

Read `references/levers.md` before explaining a mismatch or a rejected action.
It records what each setting really does (e.g. plugin skills ignore `skillOverrides`).

## 1. Scan

```bash
python3 <skill-dir>/scripts/scan.py --project "$PWD" --out <scratchpad>/context-report
```

- Leave `--out` off when no scratchpad directory is listed. The default is
  `~/.claude/context-reports/<project-slug>/`.
- The default session is the current one (`$CLAUDE_CODE_SESSION_ID`). The baseline
  is turn 1, so running mid-session is fine. Pass `--session <id|path.jsonl>` to
  measure another session. For a project with no session yet, ask the user to open one there first.
- If it prints `first turn: None`, run it again before reporting anything. This happens
  when the skill is the session's first message (e.g. right after `/clear`): turn 1's
  usage, the system prompt and the tool schemas aren't in the transcript yet, so the
  report leaves out the largest fixed items and is uncalibrated.
- The report reflects config **at that session's start**. After a change, measure
  a new session.

Then open it (`open <path>` on macOS, `xdg-open` on Linux) and reply in chat with:
the first-turn total, the 5 largest items, how much is actionable, and the top 3
mismatches if there are any. Tell the user to pick actions in the page and press
**Copy plan** (or **Download plan.json**), then paste it here.

## 2. Dry run

When the plan arrives, either pasted JSON (`"manage_context_plan": 1`) or a path,
usually `~/Downloads/context-plan.json`:

1. Save pasted JSON to `<scratchpad>/context-plan.json`.
2. Run `python3 <skill-dir>/scripts/apply_plan.py <plan> --project "$PWD"`.
3. Show the output verbatim: every file, key, old → new, plus warnings (`!`) and
   rejections (`✗`). Explain each rejection using `levers.md`. Rejections usually
   need a manual step, like claude.ai connectors or org-synced plugins.
4. Ask for an explicit yes. Approval of an earlier plan doesn't count.

## 3. Apply

Re-run the same command with `--apply`. Report:

- the number of edits and the backup directory
- the undo command it printed (`apply_plan.py --undo <file> --apply`)
- that changes take effect in the **next** session, and that re-running this skill
  there shows the new first-turn total

Undo works the same way: dry run first, then `--apply` after a yes.

## Rules

- Never print values from `~/.claude.json`. The scripts mask MCP server configs, so don't `cat` the file.
- Token numbers are estimates per item, calibrated so they add up to the real
  first-turn total. Say "~" and don't present them as exact.
- An `"off"` that is still loaded is a **mismatch**, not a bug in the report.
  Explain which lever actually controls the item.

---
name: log-progress
version: 1.0.0
description: Keep a living log of what the agent established, tested and rejected, in a Linear issue or a markdown file, so the next agent pointed at it can start a different experiment without re-running dead ends.
argument-hint: "[LINEAR-ID | linear URL | path.md]"
disable-model-invocation: true
---

# log-progress

A long experiment session learns things the chat can't keep. The reader is **the next agent**, handed this ticket to start a *different* experiment. Without the log it re-derives facts this session already proved and re-tests options it already rejected. So the log holds only what changes that agent's next move; everything else is noise it has to read past.

## Target

- Linear issue ID or URL → Linear (MCP).
- Path → that markdown file.
- No argument → `.progress/<git branch>.md` in the repo root (topic slug if not in git).

## Standing instruction

After this call, **keep the log current until the work is done or the user says stop**. Update after anything that changes the story: a new established fact, a test that settles an option, a reversal. Not after every command.

- **One living log, rewritten in place.** In Linear, edit the single comment headed `**Investigation log**` (find it with `list_comments`; `save_comment` with its `id`). A new comment per update buries the current state under history. Create it only if none exists.
- **The log carries its own target**, so it survives context compaction: if a session-state file exists (e.g. `.consult/USER_NOTES.md`), add a line that this log must be kept current.
- Rewrite, don't append. If a later test overturns a fact or a decision, change it; the log shows the current truth, not a diary.

## What carries over

The next experiment is different, so the chosen fix matters less to it than what made it true. Keep:

- **Established facts, with their conditions** (tenant, range, cold/warm). A fact without conditions gets misapplied; a number without them can't be compared.
- **Rejected options, with the reason.** The reason tells the next agent whether the rejection still holds in its setting; a bare ✗ either gets blindly trusted or blindly retried.
- **Open leads**: untested ideas and unchecked assumptions.

Shape and an example: [references/template.md](references/template.md).

## Don't

- Paste raw logs, SQL, plans, or the session's narrative. Link the PR/file instead.
- Log secrets, customer PII, or connection strings; Linear is shared.
- Claim a result you didn't measure. Unmeasured ideas go under **Open**.

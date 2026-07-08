---
name: slack-comm
description: Summarize the CURRENT Claude session's work into a very concise 3P (Progress/Plans/Problems) Slack status report, draft it to the user for review, then place it as a native Slack draft for a final look before they send. User-invoked mid-session (`/slack-comm`) when you need to report what you just did in a tight, matter-of-fact format. Not for org-scale newsletters or pulling other people's updates.
argument-hint: "[team name override]"
disable-model-invocation: true
---

# slack-comm

## What this is

You are called **in the middle of a Claude session** to report status. The
source material is **this session** — the work that was just done, found, or
fixed in the conversation so far. You compress it into a strict, very concise
**3P update** (Progress / Plans / Problems), show it to the user for review,
and then stage it as a native Slack draft. You never actually post to Slack —
the user hits send themselves after a final look.

The format spec lives in [references/3p-updates.md](references/3p-updates.md)
(the primary format) with tone principles in
[references/general-comms.md](references/general-comms.md). Read the 3P
reference before drafting; it is the source of truth for structure and tone.

## The contract (hard rules)

1. **The session is the source.** Draw Progress from what actually happened in
   this conversation. Do **not** invent work, metrics, PRs, or job names that
   the session doesn't contain.
2. **Very concise.** Each section is 1–3 short sentences, matter-of-fact,
   data-driven (include real metrics/IDs where the session has them). No prose,
   no filler, no significance inflation.
3. **Review before Slack.** Always show the draft in chat and get approval
   before touching Slack.
4. **Draft only, never post.** Use `slack_send_message_draft` — never
   `slack_send_message`. The user reviews the draft in Slack and sends it.
5. **Ask the destination.** Never assume a channel; ask which channel/DM each
   call before creating the draft.

## Output format

Strict 3P, header included:

```
[emoji] [Team Name] ([today's date])
Progress: [1–3 sentences]
Plans: [1–3 sentences]
Problems: [1–3 sentences]
```

- **Emoji**: auto-pick one that captures the vibe of the work (e.g. 🔧 for a
  fix, 🚀 for a ship, 🔍 for an investigation).
- **Team Name**: defaults to **Data Team**. Override if the user passed a name
  as an argument or says otherwise inline.
- **Dates**: today's date (from the current session date). A single-session
  recap is a point-in-time report, so one date is fine.

Example:

```
🔧 Data Team (2026-07-08)
Progress: Fixed nch-bty gold-layer OOM — bumped instance ml.m5.4xl→8xl, job green in 12m; PR #482 merged.
Plans: Monitor tonight's scheduled run; roll the same instance bump to bty-pro if stable.
Problems: None.
```

### Filling Progress / Plans / Problems

- **Progress** — what was accomplished in this session. Things done, fixed,
  shipped, discovered, verified. Lead with the most important. Metrics/IDs when
  the session has them.
- **Plans** — *infer* the next steps or TODOs the session surfaced (follow-ups,
  "next I'll…", monitoring, remaining work). This is an inference — flag it as
  your best guess in the chat review so the user can correct it.
- **Problems** — *infer* the blockers, errors, or friction hit during the
  session. Also an inference to confirm.
- If a section is genuinely empty after inference, write `None` rather than
  padding it.

## Workflow

1. **Resolve the header.** Team = argument or `Data Team`; date = today; pick an
   emoji for the work.
2. **Draft the 3P.** Summarize this session per the format above. Keep it to the
   30–60-second-read bar.
3. **Show it in chat and flag inferences.** Present the full draft. Explicitly
   note that Plans/Problems are inferred so the user can fix them. Iterate on
   edits until the user approves.
4. **Ask the destination.** Which Slack channel or DM? If given a channel name
   (not an ID), resolve it with `slack_search_channels`; for a DM, resolve the
   user with `slack_search_users` and use their user ID as `channel_id`.
5. **Create the native draft.** Call `slack_send_message_draft` with the
   resolved `channel_id` and the approved message. Then tell the user the draft
   is waiting in Slack (share the returned `channel_link`) for a final look and
   send — you are done; do not send it for them.

## Notes

- Slack markdown: `*bold*`, `_italic_`, `` `code` ``. The draft tool accepts
  standard markdown; keep formatting minimal to match the terse 3P style.
- If `slack_send_message_draft` returns `draft_already_exists`, tell the user —
  they should send or delete the existing draft in that channel first; don't try
  to force it.
- This skill reports *your own* session work. It is not the org-wide
  newsletter/FAQ machinery of the source internal-comms skill.

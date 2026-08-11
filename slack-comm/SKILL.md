---
name: slack-comm
description: Summarize the CURRENT Claude session's work into a concise, evidence-driven IMPACT/CAUSE/FIX Slack report (who was affected, what caused it, what was done) and stage it directly as a native Slack draft — DM to Huijo by default; the draft is the review surface, the user edits and sends in Slack. User-invoked mid-session (`/slack-comm`) when you need to report what you just did in a tight, matter-of-fact format. Not for org-scale newsletters or pulling other people's updates.
argument-hint: "[team name override]"
disable-model-invocation: true
---

# slack-comm

## What this is

You are called **in the middle of a Claude session** to report status. The
source material is **this session** — the work that was just done, found, or
fixed in the conversation so far. You compress it into a strict
**IMPACT/CAUSE/FIX report** and stage it as a native Slack draft immediately.
You never actually post to Slack — the user reviews, edits, and sends the
draft in Slack themselves.

The audience is teammates and leadership who have *some* context but not a
lot. They read **IMPACT** first and may stop there, so it must stand alone.
The whole report must be readable in about a minute.

## The contract (hard rules)

1. **The session is the source.** Draw the report from what actually happened
   in this conversation. Do **not** invent work, metrics, PRs, or job names
   that the session doesn't contain.
2. **Concise but concrete.** Each section is a few sentences anchored by real
   evidence from the session — the actual data row, log line, or code snippet
   in a code block. Real metrics/IDs, no filler, no significance inflation.
3. **Stage first, review in Slack.** The draft is the review surface — create
   it immediately, no chat approval loop. Report what you staged afterwards.
4. **Draft only, never post.** Use `slack_send_message_draft` — never
   `slack_send_message`. This is what makes staging without asking safe.
5. **Default destination: DM to Huijo.** Resolve via `slack_search_users` and
   use the user ID as `channel_id`. Only divert if the user names a different
   channel/DM (resolve channel names with `slack_search_channels`).

## Output format

Strict — never deviate. Section headers are bold ALL-CAPS on their own line
(Slack markup has no underline; bold + caps is the header style):

```
[emoji] *[Team Name]* ([today's date])

*IMPACT*
[who/what was affected, how long, and what was NOT affected — 1–3 sentences,
then the concrete evidence in a code block, annotated with ← markers]

*CAUSE*
[root cause in 1–3 sentences; prefix with "I believe:" when it is a
hypothesis rather than established]

*FIX*
[what was done + explicit deploy state (live in prod / merged, not deployed /
PR open), PR link, review ping (@reviewer) when it needs eyes, and a minimal
code snippet showing the mechanism]

*STATUS*
[where it stands right now, and what is still open]

*NOT AN ISSUE*   ← optional; include only when the session ruled things out
[things that looked wrong but are correct, so they don't become phantom
action items]
```

- **Header emoji**: auto-pick one that captures the vibe of the work (e.g. 🔧
  for a fix, 🚀 for a ship, 🔍 for an investigation).
- **Team Name**: defaults to **Data Team**. Override if the user passed a name
  as an argument or says otherwise inline.
- **Dates**: today's date (from the current session date). A single-session
  recap is a point-in-time report, so one date is fine.

### Filling the sections

- **IMPACT** — lead with blast radius in business terms, not the defect.
  Who/what was affected, how many, for how long, and **explicitly what was
  not affected** — that bounds the damage and stops readers imagining worse.
  State it, then *show* it: raw evidence in a code block, annotated with `←`
  markers. Numbers beat adjectives ("12 clients, 14 days" not "several
  clients for a while").
- **CAUSE** — the root cause as established in the session. Prefix a
  hypothesis with "I believe:" — never present a guess as a confirmed cause.
  Name the actual mechanism, not the symptom.
- **FIX** — what was done, **and whether it is actually live**. "Fixed" is
  ambiguous; write `Live in prod (PR #291)`, `Merged to dev, not yet
  deployed`, or `PR open, needs review @person`. Include a minimal snippet
  showing the mechanism (the guard, the join, the config diff — just enough
  to convince).
- **STATUS** — the current state, and what remains. If it is still recovering,
  give the trend with numbers (`382,773 → 14,281 lag`) so the reader can see
  direction, not just a snapshot. Call out the highest-value remaining item.
- **NOT AN ISSUE** — optional but high value after any real investigation.
  List what you checked that turned out to be *correct behavior*, with a
  one-line reason. This is how you stop four people re-investigating the same
  red herrings. Omit the section entirely if the session ruled nothing out.
- If a section is genuinely empty (e.g. root cause still unknown), write what
  is true — `Root cause not yet established; …` — rather than padding.

### Non-incident sessions

For pure feature/ship work with no defect, keep the same four headers and
reframe: **IMPACT** = what the change enables and for whom, **CAUSE** = why it
was needed (the gap or request driving it), **FIX** = what shipped. Drop
**NOT AN ISSUE**.

## Common comms traps

Hard-won; violating these is how a technically-correct report misleads.

1. **A stale database timestamp is not business absence.** "Realtime stock
   updates froze for 12 clients" reads as *those stores had no inventory
   activity* — which is false and will confuse anyone who knows the business.
   Write what is true of the pipeline: `updates were queued but not applied;
   the stores kept sending normally`.
2. **Distinguish queued from lost.** Recoverable backlog and destroyed data
   provoke very different reactions. If nothing was lost, say so explicitly.
3. **Always state what was *not* affected.** "Daily batch was unaffected, so
   stock was stale intraday, never missing" converts a scary 14-day number
   into an accurate one.
4. **Never imply a fix is live when it isn't.** Merged ≠ deployed. Verify
   before claiming it, and say which you verified.
5. **Don't inflate or bury.** No "critical"/"catastrophic" unless the numbers
   carry it; equally, don't hide a 14-day outage in a subordinate clause.

## Workflow

1. **Resolve the header.** Team = argument or `Data Team`; date = today; pick an
   emoji for the work.
2. **Draft the report.** Summarize this session per the format above. Keep it
   to the one-minute-read bar.
3. **Resolve the destination.** DM to Huijo unless the user named another
   channel/DM (see contract rule 5).
4. **Stage the draft.** Call `slack_send_message_draft` with the resolved
   `channel_id` and the message — immediately, no chat approval first.
5. **Report what you staged.** Show the staged text in chat with the returned
   `channel_link`, and flag anything inferred rather than established (an
   unconfirmed CAUSE, an unverified deploy state, proposed next steps) so the
   user can edit the draft in Slack before sending. You are done — do not send
   it for them.

## Example

````
🔧 *Data Team* (2026-08-11)

*IMPACT*
Realtime inventory updates for 12 clients (fredfelia, apol, essentialbag, +9) were queued but not applied for 14 days — Jul 28 15:37Z until today. The stores kept sending normally and nothing was lost. Daily batch was unaffected, so app stock was stale intraday, never missing or days-old.
```
PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
0          2038939         2038939              0
1          2535030         2535030              0
2          1430673         1813446         382773   ← wedged since Jul 28
```

*CAUSE*
`fitnesshealth` was enabled for realtime before its database was created. The consumer treated `FATAL: database "fitnesshealth" does not exist` as retryable and rewound to the same offset forever (9,644 consecutive failures). Kafka delivers a partition in order and messages are keyed by client, so all 12 clients sharing partition 2 froze at the same instant.

*FIX*
Live in prod (PR #291) — verified the running container has the change. The consumer now classifies "database does not exist" as non-retryable (skip, count, move on), plus a 50-failure cap so no unclassified error can wedge a partition again. Onboarding refuses to enable a client with no database.
```
skip_reason = _nonretryable_skip_reason(exc)                 # 3D000 → permanent
if skip_reason is None and consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
    skip_reason = "failure_cap"                              # backstop
if skip_reason is not None:
    consumer.commit(msg, asynchronous=False)                 # advance, don't block
```

*STATUS*
Backlog draining on its own — lag 382,773 → 14,281, caught up within the hour, no manual intervention needed. Still open: no alerting on consumer lag or heartbeat, which is why this lasted 14 days instead of 14 minutes.

*NOT AN ISSUE*
Checked, correct, no action needed: the Aug 8 timestamps were the consumer's chronological replay position, not a data gap; `warehouse.stocks_new` sitting at 00:42 is the daily batch, and replayed events older than that are correctly rejected by the monotonic guard (`repository.py:198`) — applying them would move stock backwards.
````

## Tone

- Cut every word that isn't load-bearing.
- Active voice ("Fixed X", "Shipped Y"), most important information first.
- Show, don't tell: a raw row or a two-line snippet beats a paragraph of
  description.
- Include relevant links and references (PRs, job names, tickets, dashboards).
- Terse, matter-of-fact status-report style — no throat-clearing, no
  editorializing.

## Notes

- Slack markup: `*bold*`, `_italic_`, `` `code` ``, triple-backtick code
  blocks. There is no underline. Beyond the section structure above, keep
  formatting minimal.
- If `slack_send_message_draft` returns `draft_already_exists`, tell the user —
  they should send or delete the existing draft in that channel first; don't try
  to force it.
- This skill reports *your own* session work. It is not the org-wide
  newsletter/FAQ machinery of the source internal-comms skill.

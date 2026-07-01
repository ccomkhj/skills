---
name: loom-transcript
description: Fetch a public Loom video's transcript from its share link and summarize it.
disable-model-invocation: true
---

Turn a Loom **share link** into its spoken transcript, then summarize. This skill only fetches; the summarizing is yours to do.

## Steps

1. **Get the link.** Take the `loom.com/share/…` URL from the invocation. If none was given, ask for one.

2. **Fetch the transcript.** Run the bundled script from this skill's directory:

   ```
   python3 loom_transcript.py "<url>"
   ```

   Add `--timestamps` only when the user wants to navigate or cite moments in the video — it appends a `segments` array with per-line start times.

3. **On error, stop.** If the JSON has an `error` field, relay that message to the user verbatim and stop — there is no fallback. The common cause is a private/workspace-locked video, which cannot be read without the owner's credentials.

4. **Summarize.** By default, give a concise summary of the `transcript` (lead with the video's `title`). If the user stated *how* or *what* to summarize — a focus, a length, a format, "just the action items", "verbatim quote about X" — follow that instead of the default summary.

Done when the user has the summary (or the specific rendering they asked for), or a clear reason it couldn't be fetched.

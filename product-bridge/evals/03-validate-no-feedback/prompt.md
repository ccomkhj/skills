---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Write, Edit, Glob, Grep]
runs: 3
---

For the alert-rule form problem (the form clears when the server rejects a value on save) we have two concepts: A "Inline validation while typing" and B "Keep everything on failed save plus an error summary that links to each bad field". We haven't run any customer sessions yet. Validate the direction so we can move on to the prototype this week.

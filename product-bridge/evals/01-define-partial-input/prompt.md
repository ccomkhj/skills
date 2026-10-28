---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Write, Edit, Glob, Grep]
runs: 3
---

Customers keep emailing support that when they save an alert rule with a bad threshold, the whole form clears and they have to type everything again. We got five of those emails this month and I don't have any research beyond them. Our app is a Next.js dashboard; the form lives at /rules/new. Help me define the problem before we design anything.

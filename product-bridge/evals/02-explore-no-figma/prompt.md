---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Write, Edit, Glob, Grep]
runs: 3
---

I approved this problem brief today:

- User: ops engineers creating alert rules in our Next.js dashboard (/rules/new)
- Task: create a valid alert rule in one sitting
- Friction: when the server rejects a value on save, the whole form clears (5 support emails this month)
- Constraints: use our existing design system; no backend schema change this quarter
- H1: keeping the user's input when a save fails will reduce abandoned rule creation

The current screens are in Figma: https://www.figma.com/design/Qx7RulesCurrent/Rules. Explore UX options for this so I can pick which ones go to customer testing.

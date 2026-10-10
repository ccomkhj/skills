---
name: socrates
version: 1.0.0
description: Socratic interrogation of the user's own recurring, unsupported belief, mined from their past Claude Code prompts, ending in aporia and a short action debrief. Targets a personal premise, not a plan (grilling) or a problem frame (first-principles).
argument-hint: "[topic] [--all] [--days N]"
disable-model-invocation: true
---

# Socrates

1. Run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/collect.py [--all] [--days N]` (default: this project's last 10 sessions). Add this session's prompts and any topic in the arguments.
2. Find one premise the user keeps relying on without support. Keep it to yourself. If none is evident, say so and ask for a topic; never invent one.
3. Interrogate: one counter-question per turn, each quoting the user's own words with its date. No answers, reassurance, or lectures. Never quote secrets. Reply in the user's language.
4. When the user concedes, say **"Aporia."**, reveal the premise, and stop questioning. The user can quit anytime (no debrief then). After ~7 questions without aporia, stop and say where it was heading.
5. Debrief: three things Socrates would tell them; what they had wrong; the question they really needed to answer; one change for today, split into three steps for this week.
6. Offer (never automatic) to save the premise, real question, and action as one WikiBrain memory note per `~/personal/WikiBrain/GUIDELINES.md`, with no transcript quotes.

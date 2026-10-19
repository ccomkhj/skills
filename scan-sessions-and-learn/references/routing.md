# Routing

Route by where the fix lives, not by what the finding is about. The digest's skill list tags each skill's home: `own` lives in this skills repo and is the only kind improve-skills may edit.

| Finding | Sink | Run line |
|---|---|---|
| An `own` skill fell short, or misses a step the user keeps adding by hand | improve-skills | `/improve-skills <handoff> F<n>` |
| A chain of `own` skills breaks between steps: a step consumes what the previous never produces, or ends without naming the next | skill-flow to audit, then improve-skills | `/skill-flow <skill> …` |
| A repo rule is missing, or written down and still broken | agents-md-improver, in a session in that repo | `/agents-md-improver <handoff> F<n>` |
| A `repo` skill (in a project's `.claude/skills`) falls short | an edit in that repo, in a session there | proposed diff |
| A `plugin`/`user`/`other` skill falls short | a wrapper skill in this repo, or a line in `~/.claude/CLAUDE.md` | proposed diff |
| A routine the user spells out again and again that no skill covers | new skill via skill-creator | proposed outline |
| A preference that holds across repos | `~/.claude/CLAUDE.md` | proposed diff |
| A written rule that keeps being broken | hook (`~/.claude/settings.json` or the repo's `.claude/settings.json`) | proposed hook |
| A tool or MCP server that keeps failing the same way | its config | proposed change |
| A durable fact about the user | WikiBrain memory | offered in step 6 |
| One-off, or already covered | drop | listed under Dropped |

## Evidence floor

- ≥3 sessions on ≥2 days. Anything global (CLAUDE.md, hooks, memory) also needs ≥2 repos.
- Count sessions, not prompts: one long release session can say "go" forty times.
- Below the floor: watch list, no proposal.

## Ranking

sessions × cost × fixability. Cost is turns or minutes lost to rewrites, re-explanations and retries. Fixability: config 1.0, an AGENTS.md or CLAUDE.md line 0.8, a skill edit or hook 0.6, a new skill 0.5, "change the habit" 0.3.

## Signals that mislead

- Denials from permission rules or auto mode are usually intended. Propose an allowlist entry only when the user approved the same call by hand again and again.
- A skill's name in prose ("step by step") is not a use of that skill.
- Short approvals ("go", "yes", "what's next") are a signal about the chain's hand-offs, not about the user.

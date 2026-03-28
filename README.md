# Skills

A collection of Claude Code skills for coding agents.

## Skills

| Skill | Description | Source |
|-------|-------------|--------|
| [data-pipeline-drift](./data-pipeline-drift) | Detect data drift in parquet pipeline outputs across partitions or environments | — |
| [excalidraw-diagram](./excalidraw-diagram) | Create Excalidraw diagram JSON files that make visual arguments | Improved from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) |
| [get-feedback-markdown-plan](./get-feedback-markdown-plan) | Evaluate inline feedback annotations on a markdown plan by verifying each critique (feedback from [review-markdown-plan](./review-markdown-plan)) | — |
| [grill-me](./grill-me) | Structured interview about a plan or design, walking each branch of the decision tree | Improved from [mattpocock/skills](https://github.com/mattpocock/skills/blob/main/grill-me/SKILL.md) |
| [review-markdown-plan](./review-markdown-plan) | Review other agent's plan by section, annotating only concretely wrong steps | — |

## Setup

Clone the repo and symlink it so your agents can discover the skills:

```bash
git clone git@github.com:ccomkhj/skills.git

# For Claude Code
ln -s skills ~/.claude/skills

# For other agents (e.g. Gemini CLI, Cursor, Codex)
ln -s skills ~/.agents/skills
```

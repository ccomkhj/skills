---
name: pr-classify
version: 1.0.0
description: Triage a PR as safe to merge, nice to review, or reject to merge in a fresh, unbiased context, then act on the verdict. Use after writing a PR body with /pr, or when asked whether a PR is safe or ready to merge.
argument-hint: "[PR number or URL]"
---

# pr-classify

The step after `/pr`: decide whether this PR can ship without a human reading it.

| Class | Meaning | Action |
|---|---|---|
| **safe to merge** | Confident it introduces no production issue | Ask to merge; on yes, merge (and promote dev → main if the repo uses that flow) |
| **nice to review** | Code-quality issues or possible minor bugs, nothing production-critical | Report findings; a human reviews before merge |
| **reject to merge** | A production-critical issue | Report what must be fixed; leave the PR unmerged |

## Why a fresh context

The agent that wrote the code (and the `/pr` body) reads the diff through its intent and sees what it meant to write, not what it wrote. So the verdict always comes from a **fresh subagent** that has never seen this conversation. In Claude Code that means a new general-purpose agent, never a `fork`: a fork inherits this conversation and its bias.

Hand it only pointers: the PR (or branch + base), the repo path, and [references/classifier.md](references/classifier.md) as its brief. Keep your summary, your reasoning, and "what this change does" out of the prompt; it reads the code itself.

## Steps

1. **Pin the target.** Argument, else the current branch's PR. No PR yet → the subagent classifies the branch against its base, and the merge offer includes opening the PR with the `/pr` body.
2. **Dispatch** the fresh subagent and wait for its report.
3. **Relay the verdict as returned.** You may escalate it if you know something it couldn't (e.g. a known prod incident in that area); never downgrade it, since your read is the biased one.
4. **Act on the class.**

## Safe → merge

- Ask once, naming exactly what will happen: "Merge #N into dev, then promote dev → main?" with options both / dev only / don't merge.
- **dev → main flow**: detect it from repo docs, CI that gates `main` on a `dev` head, or the PR targeting `dev`. The promotion carries every commit on dev, not just this PR, so check `main..dev` first: anything else riding along is unclassified; send it through the same fresh classifier or list it in the question. Reuse an open dev → main PR if one exists. Match the repo's past promotion merge method (usually a merge commit; squashing dev → main diverges the branches and conflicts the next promotion). Keep dev alive: no `--delete-branch` on the promotion.
- Merge through the normal path with the repo's merge method. If branch protection blocks it, report and stop; an admin override defeats the review the protection exists for.

---
name: analyze-git-style
version: 1.0.0
description: "ONLY trigger when the user explicitly types /analyze-git-style. Analyzes git commit and push history across ALL repositories on the machine, scores commit message quality, and generates a CLI report with statistics, lessons, and improvement suggestions. Supports --today and --week time filters."
---

# Analyze Git Style

Scan all git repositories, analyze commit history, score message quality, and deliver a teaching-focused report.

## Argument Handling

Parse the argument from the user's invocation:
- `/analyze-git-style` or `/analyze-git-style --week` → last 7 days (`--since="7 days ago"`)
- `/analyze-git-style --today` → last 24 hours (`--since="24 hours ago"`)

Set `SINCE` accordingly for all git commands below.

## Step 1: Discover All Git Repositories

Find every git repo under the home directory (maxdepth 6), excluding: `node_modules`, `.cache`, `.Trash`, `Library`, `.npm`, `.cargo`, `.rustup`, `vendor`, `.local`, `.docker`, `.venv`, `venv`, `.conda`, `.pyenv`, `.gem`, `.gradle`, `.m2`, `.pub-cache`, `.claude`, `.agents`.

```bash
find ~ -name .git -type d -maxdepth 6 -not -path "*/node_modules/*" -not -path "*/.cache/*" -not -path "*/.Trash/*" -not -path "*/Library/*" -not -path "*/.npm/*" -not -path "*/.cargo/*" -not -path "*/.rustup/*" -not -path "*/vendor/*" -not -path "*/.local/*" -not -path "*/.docker/*" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/.conda/*" -not -path "*/.pyenv/*" -not -path "*/.gem/*" -not -path "*/.gradle/*" -not -path "*/.m2/*" -not -path "*/.pub-cache/*" -not -path "*/.claude/*" -not -path "*/.agents/*" 2>/dev/null | sed 's|/.git$||'
```

## Step 2: Gather Data (Per Repo)

For each discovered repo, run these commands from within the repo directory. Skip repos that have zero commits in the time window.

**Commit metadata (all branches):**
```bash
git -C <repo> log --all --format="%H|%an|%aI|%s" --since="$SINCE"
```

**Full commit bodies:**
```bash
git -C <repo> log --all --format="%H%n%B%n---END---" --since="$SINCE"
```

**Diff stats per commit:**
```bash
git -C <repo> log --all --shortstat --format="%H" --since="$SINCE"
```

**Push approximation (reflog):**
```bash
git -C <repo> reflog --all --format="%gd|%gs|%aI" --since="$SINCE" 2>/dev/null
```

Collect all results tagged with the repo path. Combine across all repos for aggregate analysis.

## Step 3: Score Commit Messages

Read `references/scoring-rubric.md` for the full rubric and `references/good-commit-reference.md` for authoritative examples from [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) and [Chris Beams' guide](https://chris.beams.io/posts/git-commit/). Score each commit on 5 dimensions (0-2 points each, max 10):

1. **Clarity** — Can you understand the change without reading the diff?
2. **Length** — Subject line between 20-72 characters
3. **Imperative mood** — Starts with a verb in command form ("Add", "Fix", not "Added", "Fixing")
4. **Specificity** — Names the thing being changed, not just the action ("fix OAuth token refresh" not "fix bug")
5. **Body appropriateness** — Changes over 50 lines should have a body explaining *why*

Exclude merge commits and auto-generated commits (dependabot, renovate, CI) from scoring.

**Flag cleanup candidates:** Also identify commits with subjects matching WIP patterns (`wip`, `fixup!`, `squash!`, `tmp`, `TODO`, `checkpoint`, `save`, single-word throwaway messages). These aren't scored — they're noted separately as commits that should have been squashed before merge.

## Step 4: Analyze Patterns

Compute these cross-repo metrics:

- **Per-repo activity**: commits per repo, average score per repo
- **Per-dimension averages**: average score for each of the 5 scoring dimensions across all commits — identify the 1-2 weakest dimensions
- **Commit frequency**: commits per day, distribution across the time window
- **Commit size distribution**: bucket into 1-10, 11-50, 51-200, 200+ lines changed
- **Time-of-day distribution**: morning (6-12), afternoon (12-18), evening (18-24), night (0-6)
- **Conventional commits adoption**: percentage using `type(scope): subject` — note as a useful pattern, not a requirement
- **Co-author / AI attribution**: track `Co-Authored-By` lines
- **Commit atomicity**: flag commits touching 4+ distinct top-level directories or >10 files (excluding renames/formatting) as candidates that may mix unrelated changes
- **Pattern clusters**: group low-scored commits by their failure mode (e.g., "unnamed fix", "no body on large change", "past tense") — teach the principle once per cluster rather than repeating the same lesson per commit

## Step 5: Generate Report

Output the report directly in the CLI using this structure:

```
# Git Style Report — <period description>
## Scanned: N repositories | Commits: N | Active repos: N | Avg Score: X.X/10
## Period: <start date> - <end date> | Most active: <repo-name> (N commits)
```

After the header, add a one-line takeaway summarizing the key finding, e.g.: "Specificity was strong this week but 40% of large changes lacked commit bodies."

Then output the remaining sections in this order:

### This Week's Focus

Pick the single lowest-scoring dimension and go deep. Explain why this dimension matters (using the rubric's reasoning), then cite 2-3 specific commits that show the problem. Show one detailed rewrite with explanation. This is the primary teaching section — invest the most depth here.

### Commit Spotlights

Pick 1 strong commit and 1 weak commit. For each, show the full dimension breakdown:

```
**Strong:** `fix(cart): prevent duplicate items when adding from wishlist` (9/10)
  Clarity 2 | Length 2 | Imperative 2 | Specificity 2 | Body 1
  Why this works: Names the component (cart), symptom (duplicates), and trigger
  (wishlist add). A reviewer can assess blast radius from the log alone.

**Needs work:** `update stuff` (2/10)
  Clarity 0 | Length 0 | Imperative 2 | Specificity 0 | Body 0
  Rewrite: `update inventory sync to handle partial warehouse responses`
  The lesson: [specific explanation of what the rewrite fixes and why it matters]
```

### Good Patterns Worth Repeating

2-3 items. Quote the actual commit, explain what principle it demonstrates.

### Improvement Opportunities

Group low-scored commits by failure pattern (e.g., "unnamed fix", "no body on large change", "past tense"). Teach the underlying principle once per cluster, cite the commits that fell into it, and show one rewrite. This avoids repeating the same lesson for each commit.

### Score Breakdown by Dimension

```
| Dimension           | Avg  | Weakest Commit                        |
|---------------------|------|---------------------------------------|
| Clarity             | 1.8  | abc1234: "update auth"                |
| Length              | 1.9  | ...                                   |
| Imperative mood     | 1.6  | ...                                   |
| Specificity         | 1.2  | ...                                   |
| Body appropriateness| 0.4  | def5678: (92 lines, no body)          |
```

### Per-Repo Activity

```
| Repository | Commits | Avg Score | Avg Size (lines) |
|------------|---------|-----------|------------------|
```

If more than 5 repos, show top 5 by commit count and summarize the rest: "and N other repos (M total commits, avg score X/10)".

### Commit Size Distribution

```
| Range       | Count | %   |
|-------------|-------|-----|
| 1-10 lines  | ...   | ... |
| 11-50 lines | ...   | ... |
| 51-200      | ...   | ... |
| 200+        | ...   | ... |
```

### Cleanup Candidates (if any)

List any WIP/fixup/throwaway commits that were found (from Step 3). Teaching point: these should be squashed via interactive rebase before merging to shared branches.

### Atomicity Flags (if any)

List commits touching 4+ unrelated directories. Teaching point: "Each commit should represent one logical change. If you can't describe it in one sentence, it's probably two commits."

### Activity Pattern

```
Commits by time of day: morning N | afternoon N | evening N | night N
```

## Tone Guidelines

This is a teaching tool. The goal is to build understanding, not to praise or scold.

- **Be informative first.** Explain *why* a pattern matters — what problem it prevents, what benefit it creates. "Good job" teaches nothing; "This message names the component and failure mode, which means a reviewer can assess blast radius from the log alone" teaches a principle.
- **Every observation must cite an actual commit.** No generic advice like "write better messages."
- **When showing improvements, always explain the reasoning.** The before/after rewrite alone doesn't teach — the explanation of *why* the rewrite is better is the lesson.
- **Be direct and concise.** One clear explanation per point.
- **Acknowledge context.** Hotfix commits, WIP on personal branches, and merge commits get lighter treatment. Note them but don't penalize patterns that are appropriate for their context.

## Scheduling

To get a recurring report:

**Weekly via schedule:**
Use `/schedule` to create a trigger that runs `/analyze-git-style --week` on a cron schedule, e.g., every Monday at 9am.

**In cowork sessions:**
Run `/analyze-git-style --today` at the end of a work session to review that day's commits as a quick coaching moment.

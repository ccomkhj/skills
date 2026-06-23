---
name: find-overlapping-skills
description: Scan every installed skill across all sources, collapse double-installs, cluster the rest into overlap groups, show a terminal dashboard, then resolve each group with the user one at a time — disabling the non-keepers reversibly. Use when the user wants to find duplicate or overlapping skills, audit or trim an over-grown skill set, or asks which installed skills do the same job.
---

# Find overlapping skills

Skills accumulate. Two installed skills that fire on the same request waste context load and make invocation a coin-flip. This skill finds those collisions — an **overlap group** is a set of skills competing for the same job — and resolves each group down to the **keeper(s)** the user wants, disabling the rest reversibly.

Two facts about how skills are installed shape the whole scan:

- A **mirror** is one skill installed in more than one root (commonly symlinked into both `~/.claude/skills` and `~/.agents/skills`). Mirrors share a canonical path. They are *not* overlap — they are the same skill twice. Collapse them before clustering.
- Plugin skills are vendored and versioned (multiple copies cached under `~/.claude/plugins/cache`). They cannot be safely disabled by editing files. The scan includes them so overlap is visible, but they are resolved as recommendations, not edits.

## Step 1 — Census

Enumerate every `SKILL.md` across all roots, resolve symlinks, and collapse mirrors.

```bash
for entry in \
  "$HOME/.claude/skills:personal:2" \
  "$HOME/.agents/skills:codex:2" \
  "./.claude/skills:project:2" \
  "$HOME/.claude/plugins/cache:plugin:6"; do
  IFS=: read -r root src depth <<< "$entry"
  find -L "$root" -maxdepth "$depth" -name SKILL.md 2>/dev/null | while read -r f; do
    canon=$(realpath "$f" 2>/dev/null || echo "$f")
    name=$(awk -F': *' '/^name:/{print $2; exit}' "$f")
    desc=$(awk -F': *' '/^description:/{sub(/^[^:]*: */,""); print; exit}' "$f")
    printf '%s\t%s\t%s\t%s\n' "$src" "${name:-?}" "$canon" "${desc:0:200}"
  done
done | sort -t"$(printf '\t')" -k3
```

Then reduce the raw rows to a **census** — one row per distinct skill:

- Rows sharing a `canon` path are one mirrored skill: merge them, keep the union of source tags (e.g. `personal+codex`).
- Plugin rows with the same `name` but different cached versions are one skill: keep one, tag `plugin`.
- Mark each skill **editable** (any install point under `~/.claude/skills`, `~/.agents/skills`, or `./.claude/skills`) or **plugin** (only under `plugins/cache`).

**Completion:** a census where every distinct skill appears exactly once, carrying its name, one-line description, merged source tags, canonical path, and editable/plugin flag. Report the two counts: raw `SKILL.md` files found vs. distinct skills after mirror-collapse.

## Step 2 — Cluster into overlap groups

Read the descriptions. Group skills whose **triggers** or **job** overlap enough that, given one user request, the agent could reasonably fire either. Judge by what each skill *does for the same request*, not by shared topic words.

- Rate each group `HIGH` / `MED` / `LOW` and write a one-line reason naming the shared job.
- A group has ≥2 distinct skills. Everything else is **unique**.
- Mirror double-installs are not a group — they were already collapsed in Step 1.

**Completion:** every census skill is assigned to exactly one overlap group or marked unique; each group carries its rating and reason. (Don't dump skills into "unique" to skip the work — a skill is unique only when no other skill competes for its trigger.)

## Step 3 — Render the dashboard

Print a terminal report. Header line with the counts; then one block per overlap group, highest rating first; unique skills as a closing count only (not listed).

```
================================================================
  SKILL OVERLAP   ·   <raw> files → <distinct> skills
  <N> overlap groups (<M> skills)   ·   <U> unique
================================================================

[1] <SHARED JOB>                    overlap ███████░░░ HIGH
    ● <name>            <sources>   <one-line role>
    ● <name>            <sources>   <one-line role>
    why: <one-line reason these collide>

[2] ...
```

## Step 4 — Resolve, one group at a time

For **each** overlap group, in dashboard order — never batch them:

1. Ask the user which member(s) to keep (the **keeper(s)**), listing each member with its source and role. Offer "keep all" so they can decline to consolidate a group.
2. Disable every non-keeper. Disabling is **reversible** and chosen per install point to touch as little as possible — inspect each install point (`ls -ld`, `test -L`) and:
   - **Symlink install point** (in `~/.claude/skills` / `~/.agents/skills` / project): remove the symlink. Restore = recreate it. Leaves the source repo untouched.
   - **Real-directory install point**: rename its `SKILL.md` → `SKILL.md.disabled`. Restore = rename back.
   - **Plugin skill**: do not edit files. Record it as a recommendation to remove via plugin management, with the plugin name.
   Neutralize **all** install points of a disabled skill (a mirror has more than one).
3. Log every action with its exact inverse before moving to the next group.

**Completion:** every group has been put to the user and resolved; each disabled skill is logged with the precise command that restores it.

## Step 5 — Report

Summarize: which skills were disabled and from which groups, the exact restore command for each, and any plugin overlaps left as recommendations (with how to remove the plugin). State the new distinct-skill count.

---
name: improve-skills
version: 1.0.0
description: Fold one lesson into one existing skill, behind a confirmation gate.
disable-model-invocation: true
---

# improve-skills

A skill should absorb what you learn while using it. Mid-session you hit friction, get corrected, or find a better way — each is a **lesson** the skill should have known and didn't. This turns one lesson into one skill edit, behind a **gate**: nothing is written until you approve the proposal.

One skill per run. The single highest-value change, made well and confirmed, beats a batch of half-considered edits — and it keeps the confirmation honest. Targets are the skills under `~/personal/skills`; this skill *edits* existing skills, it does not create new ones.

## Step 1 — Collect lessons

Gather candidate improvements from two sources:

- **Session** — scan what happened this session for the moments a skill fell short: a correction you gave, friction the agent pushed through, a workaround it discovered, a mistake a skill should have prevented. Each is a candidate lesson.
- **Direct** — if the invocation named a skill or a specific change, that is the lesson; take it as given (still confirm the target in Step 2).

For each lesson capture three things: (a) what was learned, (b) which repo skill it belongs in, (c) why that skill is currently silent or wrong about it. A lesson with no home skill is out of scope — note it as "no target, maybe a new skill" and set it aside.

**Completion:** a list of candidate lessons, each tied to exactly one existing skill in the repo with a one-line rationale — or an explicit "no actionable lesson found" when the session surfaced none.

## Step 2 — Choose the one skill

If the lessons cluster on a single skill, that is the target. If they span several, present the shortlist (skill · the lesson · why it matters) and ask the user to pick one, recommending the highest-value. Then read the whole target `SKILL.md`, plus any reference file the change would touch, so the edit fits its structure and voice.

**Completion:** exactly one target skill chosen and its `SKILL.md` (and any affected reference file) fully read.

## Step 3 — Draft the proposal

Read `~/.agents/skills/writing-great-skills/SKILL.md` (and its `GLOSSARY.md` for any term you're unsure of), then design the concrete edit. In particular:

- **Place it right on the information hierarchy** — inline step/reference vs. a disclosed file — so the top doesn't bloat.
- **Single source of truth** — change the meaning in one place; if it shifts what the skill triggers on, update the description too.
- **No duplication, no no-ops** — prefer strengthening or introducing a leading word over restating something the skill already says or the model already does.
- **Minimal and in-voice** — the smallest change that lands the lesson, in the skill's existing tone.

**Completion:** a written proposal a reader could approve or amend *without seeing the file* — naming the target skill, the exact change (before→after or added/removed lines) and where it goes, and the lesson driving it.

## Step 4 — The gate

Show the proposal. Ask the user to approve, amend, or reject. Fold feedback back into the Step 3 proposal and re-present until they approve. **Write nothing before approval.** On outright rejection, stop and report.

**Completion:** explicit user approval of a specific proposal, or a clean stop on rejection.

## Step 5 — Apply

Make exactly the approved edit — no scope creep to other files or to other improvements you happen to notice. Bump the skill's version if it carries one and the change is substantive.

**Completion:** the approved change is written to the one target skill; nothing else is modified.

## Step 6 — Verify & report

Re-read the edited region: confirm it reads cleanly, added no duplication or sprawl, and left the skill internally consistent — description matches body, links resolve. Report which skill changed, what changed, the lesson behind it, and any leftover lessons parked for a future run.

**Completion:** edited region verified consistent; report delivered, listing the change and any deferred lessons.

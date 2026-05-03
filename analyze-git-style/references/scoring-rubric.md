# Commit Message Scoring Rubric

Score each commit message on 5 dimensions. Each dimension is 0-2 points (max total: 10).

## 1. Clarity (0-2)

Can someone understand the change without reading the diff?

| Score | Criteria | Example |
|-------|----------|---------|
| 0 | Incomprehensible or empty | `wip`, `asdf`, `.` |
| 1 | Partially clear — you get the area but not the change | `update auth`, `cart changes` |
| 2 | Fully self-explanatory | `add rate limiting to login endpoint` |

Common trap: Writing the *area* without the *change* — `update auth` tells you where, not what. Ask: "could two different changes have this same message?" If yes, it's not clear enough.

## 2. Length (0-2)

Subject line character count (excluding type prefix if present).

| Score | Criteria |
|-------|----------|
| 0 | Under 10 chars or over 72 chars |
| 1 | 10-19 chars or 51-72 chars |
| 2 | 20-50 chars — the sweet spot |

Why this matters: Under 10 is almost certainly too vague. Over 72 gets truncated in `git log --oneline` and GitHub PR lists. 20-50 is enough to be specific without being a sentence.

Common trap: Compensating for vagueness with length — `fix the bug that was causing issues with the thing in production` is long but says nothing specific.

## 3. Imperative Mood (0-2)

The subject should read as a command: "Add feature", not "Added feature" or "Adding feature".

| Score | Criteria | Example |
|-------|----------|---------|
| 0 | Past tense, gerund, or noun phrase | `Added tests`, `Fixing the bug`, `User authentication` |
| 1 | Imperative but awkward phrasing | `Make it so the tests pass` |
| 2 | Clean imperative | `Add unit tests for cart service` |

Why this matters: Imperative mood matches how git itself describes changes (`Merge branch...`, `Revert "..."`). It's also more concise — "Add" vs "Added" saves a character and reads as an instruction, which is what a commit is.

Common imperative verbs: add, fix, remove, update, refactor, rename, move, extract, implement, replace, handle, validate, optimize, simplify, document, configure, enable, disable, bump, drop, revert, merge

Common trap: Using a noun phrase that sounds imperative but isn't — `User authentication` reads like a label, not a command. Compare: `Add user authentication to /api/checkout`.

## 4. Specificity (0-2)

Does the message name the concrete thing being changed?

| Score | Criteria | Example |
|-------|----------|---------|
| 0 | Generic action only | `fix bug`, `update code`, `changes` |
| 1 | Names the area but not the detail | `fix auth issue`, `update API` |
| 2 | Names component + what changed | `fix OAuth token refresh on session timeout` |

Why this matters: `git log` is a debugging tool. When bisecting a regression, specific messages let you skip commits instantly. Vague messages force you to open every diff.

Common trap: Naming the *file* instead of the *behavior* — `update cart.py` scores 1, not 2, because it says *where* but not *what changed* about the cart.

## 5. Body Appropriateness (0-2)

Large or non-obvious changes benefit from a body explaining *why*.

| Score | Criteria |
|-------|----------|
| 0 | Change is >50 lines with no body, OR body restates the subject with no new information |
| 1 | Body present but could be more informative |
| 2 | Small change that needs no body, OR large/complex change with a body explaining the reasoning |

Why this matters: The subject says *what*. The body says *why*. Six months from now, "why did we change this?" is the question people actually ask. The diff shows the what; only the commit message preserves the why.

Common trap: Writing a body that restates the subject — "This commit fixes the login bug" adds zero information. The body should answer *why* this change was needed or *what alternatives were considered*.

## Formatting (Not Scored — But Noted)

These are lightweight checks from Chris Beams' guide. Don't score them, but mention in the report if patterns are consistently off:

- **Capitalize the subject line** — `Add feature` not `add feature`
- **No trailing period** — `Fix login bug` not `Fix login bug.`
- **Wrap body at 72 characters** — keeps text readable in terminals and `git log`

See `references/good-commit-reference.md` for the full 7 rules and Conventional Commits spec with examples.

## Scoring Exceptions

Skip scoring for:
- **Merge commits** — auto-generated, not worth scoring
- **Revert commits** — format is dictated by git
- **Dependabot / Renovate / CI bot commits** — auto-generated
- **Initial commit** — typically just "initial commit", which is fine

Note these in the report but exclude from averages.

## Conventional Commits (Bonus Observation)

Not required, but worth tracking adoption. The format is:

```
type(scope): subject

body
```

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`, `style`, `build`

If the user naturally uses this format, call it out as a good pattern. If not, don't penalize — just mention it as something to consider if they want machine-parseable commit history (useful for automated changelogs, semantic versioning).

# Good Commit Message Reference

Two authoritative sources on commit message quality. Use these as the basis for scoring and teaching.

Sources:
- [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [How to Write a Git Commit Message — Chris Beams](https://chris.beams.io/posts/git-commit/)

---

## The 7 Rules (Chris Beams)

### 1. Separate subject from body with a blank line

Git treats the first line as the title — it appears in `git log --oneline`, GitHub PR lists, and email patches. The body starts after a blank line.

```
Derezz the master control program

MCP turned out to be evil and had become intent on world domination.
This commit throws Tron's disc into MCP (causing its deresolution)
and turns it back into a chess game.
```

### 2. Limit the subject line to 50 characters

50 chars is the target, 72 is the hard max (GitHub truncates beyond this). Short subjects force clarity.

Good: `Accelerate to 88 miles per hour`
Bad: `accelerate to 88 miles per hour with additional context that exceeds character limits`

### 3. Capitalize the subject line

Good: `Open the pod bay doors`
Bad: `open the pod bay doors`

### 4. Do not end the subject line with a period

Trailing punctuation wastes space in a character-limited line.

Good: `Open the pod bay doors`
Bad: `Open the pod bay doors.`

### 5. Use the imperative mood in the subject line

Write as if giving a command. Test: "If applied, this commit will *[your subject line]*."

Good:
- `Refactor subsystem X for readability`
- `Update getting started documentation`
- `Remove deprecated methods`

Bad:
- `Fixed bug with Y`
- `Changing behavior of X`
- `More fixes for broken stuff`

### 6. Wrap the body at 72 characters

Keeps text readable in terminals and `git log` output where Git may add indentation.

### 7. Use the body to explain *what* and *why*, not *how*

The diff shows the how. The body preserves the reasoning.

Good (from Bitcoin Core):
```
Simplify serialize.h's exception handling

Remove the 'state' and 'exceptmask' from serialize.h's stream
implementations, as well as related methods.

As the only meaning left for the 'state' was for signaling EOF,
replace it with a simple flag. This is modeled after the same
approach used in Bitcoin.
```

---

## Conventional Commits Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Purpose |
|------|---------|
| `feat` | New feature (MINOR in SemVer) |
| `fix` | Bug fix (PATCH in SemVer) |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no code change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system or external dependencies |
| `ci` | CI configuration |
| `chore` | Other changes that don't modify src or test |

### Breaking Changes

Indicated by `!` before the colon or `BREAKING CHANGE:` in the footer:

```
feat(api)!: send an email to the customer when a product is shipped
```

```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for
extending other config files
```

### Examples

Simple feature:
```
feat(lang): add Polish language
```

Documentation:
```
docs: correct spelling of CHANGELOG
```

Feature with body and breaking change footer:
```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for
extending other config files
```

---

## Domain-Specific Examples

Real-world commit messages for common engineering contexts:

**Data pipeline:**
```
fix: handle null partition keys in bronze-to-silver transform

The bronze layer occasionally receives records with null partition keys
from the upstream Kafka topic. These were causing silent row drops in
the silver aggregation. Now coalesced to a default partition with a
warning logged.
```

**Schema migration:**
```
feat(schema): add fulfilled_at timestamp to orders table
```

**Infrastructure / config:**
```
chore(infra): increase Lambda timeout for inventory sync to 5min

The 3min default was causing timeouts during peak catalog updates
(>50k SKUs). 5min matches the p99 observed in the last 30 days.
```

**API changes:**
```
fix(api): return 404 instead of 500 when product SKU not found
```

---

## Quick Checklist for Scoring

When evaluating a commit message, check:

1. Can you understand the change without reading the diff? (Clarity)
2. Is the subject under 50 chars? Under 72 at worst? (Length)
3. Does it start with an imperative verb? (Mood)
4. Does it name the specific thing changed? (Specificity)
5. If the change is large, does the body explain why? (Body)
6. Is the first letter capitalized? (Formatting)
7. No trailing period? (Formatting)

---
name: simplify-python
description: Simplify recently written or edited Python for readability without changing behavior. Use for cleanup, idiomatic rewrites, flatter control flow, and trimming redundant code or docstrings. Not for performance tuning or behavior-changing redesign.
---

# simplify-python

Optimize for reader effort, not line count. Work on recently modified code unless asked otherwise; follow repository conventions and the supported Python version.

## Contract

Preserve return values, exception types and timing, side effects and their order, and observable laziness/short-circuiting. Base equivalence on actual types, callers, and contracts; skip unresolved uncertainty. A zero-change pass is valid.

## Readability rules

- Use guard clauses for preconditions and `continue` for rejected loop items. Keep peer branches together when that reads better.
- Remove dead code, redundant state, and intermediates that add no meaning. Keep explaining variables and names that express domain meaning or units.
- Keep related calculations, explanations, and uses close without changing evaluation order, timing, lifetime, or scope.
- Extract a helper when its name exposes a meaningful step and saves more effort than the indirection costs. Avoid helpers requiring tangled state or vague names.
- Inline thin, single-use helpers only when they provide no domain meaning, public interface, test seam, or extension point.
- Deduplicate shared knowledge that changes together, not merely similar-looking code. Counts and nesting depth are review signals, not targets.
- Simplify boolean expressions only when easier to read; do not mechanically push negations inward.

## Python idioms

Use these when clearer and equivalent for the actual code. Read the relevant entries in [Python gotchas](reference/python-gotchas.md) when a candidate touches iteration, comparisons, cleanup, mappings, or implicit behavior.

- Prefer `enumerate`, `zip`, and unpacking over manual indexing and temporary swaps.
- Use comprehensions for simple collection building; keep explicit loops for complex control flow. Consider `any`/`all` for short-circuit searches.
- Prefer named builtins and standard-library tools (`sum`, `Counter`, `defaultdict`, `pathlib`) when they remove bookkeeping.
- Consider f-strings for formatting; retain lazy logging arguments such as `logger.info("got %s", x)`.
- Consider `dataclass` for plain data containers after checking generated methods against the existing contract.
- Use walrus expressions, structural matching, and iterator chains selectively; saving lines alone is not a reason.

## Docstrings

Trim prose that repeats the signature or implementation. Keep contracts, units, ranges, exceptions, mutation, and rationale. Use a short imperative summary; add detail only when useful to callers. Follow repository formatting conventions.

Do not add missing docstrings during cleanup unless asked. Preserve doctests and any runtime use of `__doc__`.

## Workflow

1. Inspect the changed region and relevant callers; choose useful simplifications.
2. Batch related tidyings and keep unrelated changes separable.
3. Run relevant existing tests and applicable lint/type checks, plus required repository checks. Broaden for scope, failures, or uncertainty; green tests alone do not establish equivalence.
4. Report changes and verification, including material baseline failures or limitations. Explain non-obvious equivalence and mention skipped candidates only when material to the result.

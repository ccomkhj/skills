# Python equivalence traps

The simplification rules in SKILL.md assume before/after are behavior-identical. In Python several "obvious" rewrites are silently *not* equivalent. Check these before applying any rule that touches them.

## 1. Truthiness ≠ `is None`

`if x:` is false for `0`, `0.0`, `""`, `[]`, `{}`, `set()`, `False`, and any object with `__bool__`/`__len__` returning falsy. `if x is None:` is false only for `None`.

- `x or default` collapses **all** falsy values to `default`, not just `None`. Wrong for counts, prices, empty-but-valid collections. Use `x if x is not None else default`.
- Don't "simplify" `len(seq) == 0` into `not seq` if `seq` could be a non-collection (e.g. a NumPy array — `bool(arr)` raises `ValueError` for length > 1; pandas Series/DataFrame likewise raise). In data code this is a real crash, not a style nit.

## 2. De Morgan preserves truth tables, not side effects or order

`not (a and b)` ≡ `(not a) or (not b)` as booleans. But if `a`/`b` are calls, short-circuit decides **which run**. The De Morgan rewrite keeps the same operand order, so it stays equivalent — *as long as you don't also reorder operands*. Reordering to "read better" can change which side effect fires, how many fire, and which exception surfaces first. Transform the operator only.

## 3. Early return vs `finally` / cleanup

A guard-clause `return` jumps out of the function. If the original structure ran cleanup *after* the conditional (closing a file, releasing a lock, a trailing log/metric), an early return skips it — behavior change. Either keep the single-exit shape or move cleanup into `try/finally` / a context manager first.

## 4. Comprehensions can't replace every loop

- No `break`/`continue` to an outer scope, no `try/except`, no statement-level side effects with guaranteed ordering you can reason about at a glance.
- A generator expression is **lazy**: `(f(x) for x in xs)` doesn't run `f` until iterated, and runs it again on re-iteration. Replacing a list-building loop with a generator changes *when* (and whether) side effects happen and whether the result can be traversed twice. Match eager↔eager (`[...]`), lazy↔lazy.
- Exceptions raised inside a comprehension still propagate, but you lose the ability to handle per-item — don't fold a loop with per-item `try/except` into one.

## 5. Exception equivalence

"Merging error handling" is a frequent net-negative simplification:
- Broadening `except ValueError:` to `except Exception:` (or bare `except:`) to "dedupe" two handlers **swallows** unrelated errors (including `KeyboardInterrupt`/`SystemExit` for bare `except`). Not behavior-preserving.
- Removing an `except` that only re-raises looks redundant but may be **adding context** (`raise X from e`), translating the exception type, or logging. Check the body before deleting.
- Collapsing `try/except/else` by moving the `else` body into the `try` widens what the `except` can catch — a different set of errors is now handled. Keep `else` for the no-exception path.

## 6. Mutable default & shared-state intermediates

- Don't "inline" a `seen = set()` local back into a default argument (`def f(seen=set())`) — mutable defaults persist across calls. Classic bug.
- An intermediate variable holding a single mutation target (`cfg = base.copy(); cfg.update(x)`) must not be inlined in a way that mutates the shared original.

## 7. `is` vs `==` and bool identity

Rule 3 (`return cond`) returns the truthy *value*, not a canonical `True`/`False`. If a caller does `if result is True:` or serializes the result, or it flows into an API expecting a strict bool, wrap with `bool(...)`. CPython caches small ints and interned strings so `is` *sometimes* works by accident — never introduce or rely on `is` for value comparison while simplifying.

## 8. Decorators, `__all__`, side-effecting imports

Before deleting an "unused" import or name:
- `import pkg.models` may run registration side effects (ORM, plugin registries, signal handlers).
- A name in `__all__` or re-exported in `__init__.py` is public API even if unused locally.
- A function may be referenced only by a decorator, a string in a config/registry, `getattr`, `eval`, or a test monkeypatch. Grep is necessary, not sufficient — check for these indirect uses.

## 9. Generators, `yield`, and ordering of effects

Flattening or extracting code out of a generator function changes laziness. Moving a side effect across a `yield` boundary changes when it runs relative to consumption. Treat generator bodies as order-sensitive.

## 10. dict access — `get`, `defaultdict`

- `d.get(k)` returns `None` on a missing key; `d[k]` raises `KeyError`. `d.get(k)` also can't distinguish "missing" from "present and `None`". Not interchangeable when absence must raise or must be told apart from a stored `None`.
- `defaultdict(list)` **creates** the key on any read (`x = dd[k]` inserts `k`). If later code does `k in dd` or iterates keys expecting only inserted ones, switching a plain dict to `defaultdict` changes the key set. Convert back with `dict(dd)` at the boundary if that matters.

## 11. dataclass equivalence

`@dataclass` reproduces a hand-written class only when the original `__init__`/`__repr__`/`__eq__` had **no custom logic**. Validation or derived attributes belong in `__post_init__`; a subset-field `__eq__` needs `field(compare=False)`. A bare decorator over a class that validated in `__init__` silently drops the validation.

## 12. Division, float equality, bool-as-int

- `/` is true division (float); `//` floors toward negative infinity (`-7 // 2 == -4`, not `-3`). Never swap them.
- Don't introduce `==` between floats (`0.1 + 0.2 != 0.3`).
- `bool` is an `int` subclass — don't assume a list of bools and a list of ints behave the same in arithmetic.

## 13. Late-binding closures & copy depth

- `[lambda: i for i in range(3)]` — every lambda returns the final `i`. Capture with a default arg: `lambda i=i: i`. Don't delete an `i=i` "redundant" default as a cleanup.
- `b = a.copy()` / `list(a)` / `a[:]` is **shallow** — nested mutables stay shared. Swapping `copy.deepcopy(a)` for a shallow copy silently aliases nested state.

---

**Bottom line:** every rule in SKILL.md is safe *only* outside these traps. When a candidate site touches one of them, the anti-rule wins — leave the code as written.

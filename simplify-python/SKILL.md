---
name: simplify-python
description: Use AFTER writing or editing Python to make it read better without changing behavior — idiomatic rewrites (comprehensions, enumerate/zip, f-strings, pathlib, dataclasses), flattened control flow (guard clauses, de-nesting, boolean logic), and removed cruft (dead code, redundant conditionals, pointless intermediates). High-confidence, behavior-preserving rules only; each carries an anti-rule for when NOT to apply it. Trigger when the user asks to "simplify", "clean up", "tidy", "de-nest", or make recently written Python more idiomatic/Pythonic. Not a performance tool (use pair-optimize) and not a behavior-changing refactor.
---

# simplify-python

Structural and control-flow simplification for Python, applied **after** code works, **without changing behavior**. Grounded in Martin Fowler's *Refactoring* catalog, Kent Beck's *Tidy First?*, and clean-code consensus.

## The contract (read first)

1. **Behavior-preserving only.** Same return values, same exceptions (type *and* when they fire), same side effects in the same order, same observable laziness/short-circuit. If a change *might* alter any of these, it is not a simplification — skip it.
2. **High-confidence only.** Apply a rule only when the before/after are provably equivalent. When in doubt, leave it. A zero-change pass is a valid, honest outcome — do not invent cleanups to look busy.
3. **One concern per edit.** Each tidying is small and independently reversible (Beck's "tidyings"). Don't bundle a rename, a re-nest, and a de-dup into one diff.
4. **Verify after.** If tests exist, run them. These rules are *designed* to be safe, but Python has behavior-sensitive corners (truthiness, exceptions, generators, mutation) where "obvious" equivalence is false — see each anti-rule.

Scope: recently modified code unless told otherwise. This is **not** a performance skill (that's pair-optimize) and **not** for behavior-changing redesign.

---

## Idiom transforms — the Pythonic rewrites

The most common Python simplifications: a verbose construct has a shorter, clearer standard-library form. Grouped by how much you must check before applying. Deeper equivalence traps live in [reference/python-gotchas.md](reference/python-gotchas.md), cited by name below.

**Apply silently — behavior-identical, mechanical:**
- `for i in range(len(seq)): … seq[i]` → `for i, x in enumerate(seq):` (`enumerate(seq, 1)` for 1-based).
- Index-walking parallel sequences → `for a, b in zip(xs, ys):`.
- Swap via temp → `a, b = b, a`; positional reads → `x, y = pair`; head/tail → `first, *rest = row`.
- `%` / `.format()` / `+`-concatenation of values → f-string. **Except logging** — keep `logger.info("got %s", x)` lazy.
- `== None` / `!= None` → `is None` / `is not None`.

**Apply, but check the cited trap first:**
- A loop that does nothing but build one collection → comprehension. Generator `(...)` only if the result is consumed exactly once (*Comprehensions can't replace every loop*).
- `if k in d: x = d[k] else: x = default` → `d.get(k, default)`; `d.get` differs from `d[k]` on a missing key (*dict access*).
- Flag-and-break loop → `any(gen)`; clear-flag-on-failure loop → `all(gen)`. Pass a generator so it still short-circuits.
- Frequency dict → `Counter(items)`; group-into-list → `defaultdict(list)` — which auto-creates keys on read (*dict access*).
- Attribute-only class with boilerplate `__init__`/`__repr__`/`__eq__` → `@dataclass` — only if those dunders had no custom logic (*dataclass equivalence*).
- `os.path.join/split/splitext/exists` chains → `pathlib.Path` with `/`, `.suffix`, `.stem`, `.name`, `.exists()`. Wrap `str(path)` at any API that demands a str.
- `len(x) == 0` / `x != ""` → bare truthiness `if x:` — only when "empty" and "falsy" coincide for that data, never when `0`/`""`/`None` are distinct valid values (*Truthiness ≠ is None*).

**Suggest, don't auto-apply — often net-negative for readability:**
- Walrus `:=` — only to kill a duplicated call (`while (chunk := f.read(n)):`) or a priming read, never just to save a line.
- `match`/`case` — only for structural destructuring or ≥3 structural patterns; a 2-branch equality stays an `if`.
- `functools.reduce` / deep `itertools` chains — prefer the named builtin (`sum`, `min`, `any`, `all`); reach for `itertools` only when it removes real bookkeeping (`chain`, `groupby`, `pairwise`) and stays ≤2 calls deep.
- Multi-clause comprehension — more than one `for`, more than one `if`, or wrapping past ~80 cols → keep the explicit loop.

---

## Structural rules — control flow & shape

Each rule: a one-line trigger, a tiny Python before/after, and the **anti-rule** — the case where the same move breaks behavior or makes things worse. The anti-rules matter as much as the rules; an AI agent over-applies these patterns, so the guardrail is the point.

### 1. Guard clauses — flatten nested if/else with early returns

**Rule:** When the function's tail is the "real" work wrapped in validity checks, invert each check into an early `return`/`raise` and de-indent the body. (Fowler: *Replace Nested Conditional with Guard Clauses*.)

```python
# before
def price(order):
    if order is not None:
        if order.items:
            total = sum(i.cost for i in order.items)
            return total * (1 - order.discount)
        else:
            return 0
    else:
        return 0

# after
def price(order):
    if order is None:
        return 0
    if not order.items:
        return 0
    total = sum(i.cost for i in order.items)
    return total * (1 - order.discount)
```

**Anti-rule:** Don't convert to guards when the branches are **peers**, not precondition + main path — `if/elif/else` over equally-weighted cases reads worse as a return-ladder, and flattening can change semantics if later code is meant to run after the conditional. Also keep a single trailing-`return` shape when the function must run cleanup after every branch (`try/finally`, a lock release, a closing log line) — early returns that jump over that cleanup change behavior.

### 2. Remove dead code, unreachable branches, unused locals/params/imports

**Rule:** Delete code that cannot run or whose result is never observed — branches after an unconditional `return`/`raise`/`continue`, `if False:` blocks, imports never referenced, variables assigned and never read. Don't comment it out; version control is the history. (Fowler: *Remove Dead Code*.)

```python
# before
import os, json          # os never used
def parse(s):
    data = json.loads(s)
    tmp = len(data)       # tmp never read
    return data
    print("done")         # unreachable

# after
import json
def parse(s):
    return json.loads(s)
```

**Anti-rule:** "Unused" is easy to misjudge in Python.
- An import can be used **for its side effect** (`import app.models  # registers ORM tables`) or re-exported via `__all__` / `from .x import y` in an `__init__.py`. Don't remove on a grep miss alone.
- A parameter may be **required by an interface/signature contract** (callback, framework hook, overridden method, `*, key=` kwarg passed by name) — removing it breaks callers even if the body ignores it. Rename to `_`/`_unused` only if the codebase uses that convention.
- A variable assignment may have a needed **side effect** (`_ = q.get()` to dequeue, walrus inside a comprehension). And a name picked up only by `eval`/`locals()`/`getattr` or a test's monkeypatch looks dead but isn't.

### 3. Collapse redundant conditionals — return the expression directly

**Rule:** `if cond: return True else: return False` → `return cond`. Same for assigning a bool, and for `return x if x else default` patterns that reduce to `return x or default`. (Fowler: *Replace Conditional with its expression* family.)

```python
# before
def is_active(u):
    if u.deleted_at is None:
        return True
    else:
        return False

# after
def is_active(u):
    return u.deleted_at is None
```

**Anti-rule:** Only collapse when the condition is **already boolean** and you want a bool. `return cond` returns the *value* of `cond`, not `bool(cond)` — `return user or "anonymous"` is fine, but if a caller depends on getting exactly `True`/`False` (identity checks, JSON serialization, `is True`), preserve it with `return bool(cond)`. And `x or default` is **not** equivalent to `x if x is not None else default` when `x` can be a falsy-but-valid value (`0`, `""`, `[]`, `False`) — that's the classic bug. Keep the explicit `is None` check in that case.

### 4. Flatten arrow code — reduce nesting depth

**Rule:** Beyond guard clauses, cut nesting with `continue`/`break` in loops, early `return`, combining conditions with `and`, and `any()`/`all()`/comprehensions for accumulation loops. Aim for ≤2–3 levels of indentation in a function.

```python
# before
for row in rows:
    if row.valid:
        if row.qty > 0:
            results.append(row.sku)

# after
for row in rows:
    if not row.valid or row.qty <= 0:
        continue
    results.append(row.sku)
# or, if that's the whole loop:
results = [r.sku for r in rows if r.valid and r.qty > 0]
```

**Anti-rule:** Don't compress a loop with **meaningful side effects, early exit interplay, or exception handling** into a comprehension — comprehensions can't hold `try/except`, can't `break`, and hide ordering of side effects. And don't merge two `if`s with `and` when the inner one is guarded by the outer for a reason: `if d is not None:` then `if d.ready:` must **not** become `if d is not None and d.ready:` only when... actually that merge *is* safe because `and` short-circuits — but `if a() and b():` changes behavior if `b()` was previously only reached after the `a()` branch did other work. Merge only adjacent, side-effect-free guards.

### 5. Simplify boolean logic — De Morgan, kill double negatives

**Rule:** Push `not` inward with De Morgan (`not (a and b)` → `not a or not b`), and remove double negatives (`if not x is None` → `if x is not None`; `not not flag` → `bool(flag)`; `if not disabled:` → introduce `enabled`). Prefer the phrasing with the fewest negations a reader must track.

```python
# before
if not (status == "ok" and retries < 3):
    abort()

# after
if status != "ok" or retries >= 3:
    abort()
```

**Anti-rule:** De Morgan is only a *truth-table* equivalence — it does **not** preserve **short-circuit side effects or evaluation order**. `not (cheap() and expensive())` evaluates `expensive()` only when `cheap()` is true; the rewritten `not cheap() or not expensive()` evaluates `not expensive()` only when `cheap()` is true too — equivalent here, but if you also flip operand order while "simplifying", you change which side effect fires first and how many run. Transform the operator, never silently reorder operands that call functions or mutate. Also, don't "simplify" `x is not None` into a bare truthiness test `if x:` — that's rule 3's falsy-value trap again.

### 6. Decompose vs inline — extract a function, or inline an over-thin one

**Rule (extract):** Pull a named function out when a block has a **nameable single purpose**, is reused, or is a comment-headed "paragraph" inside a long function. The name replaces the comment. (Fowler: *Extract Function*.)
**Rule (inline):** Inline a function/variable whose body is **as clear as its name and used once**, adding only an indirection hop. (Fowler: *Inline Function* / *Inline Variable*.)

```python
# extract: a commented paragraph becomes a named call
def checkout(cart):
    # apply loyalty discount
    if cart.user.tier == "gold":
        cart.total *= 0.9
    ...
# ->
def checkout(cart):
    apply_loyalty_discount(cart)
    ...

# inline: indirection with no payoff
def is_empty(c): return len(c) == 0
if is_empty(items): ...        # ->  if len(items) == 0: ...   (if used once, trivially)
```

**Anti-rule:** Extraction is **net-negative** when the new function (a) takes a long parameter list just to move three lines, (b) needs many `nonlocal`/returned-tuple values because the block is entangled with local state, or (c) is named so vaguely (`process`, `handle`, `do_step2`) that the reader must jump to the body anyway — then the call site lost information. Don't extract just to hit a line-count rule. Conversely, **don't inline** a thin function that (a) is a genuine *seam* (mocked in tests, a public API, an extension point), (b) names a non-obvious domain rule (`is_business_day`), or (c) is referenced in more than one place — inlining there is duplication, not simplification.

### 7. Remove unnecessary intermediates vs keep explaining variables

**Rule:** Drop a variable that is assigned once and immediately returned/used with no clarifying name value (`result = f(x); return result` → `return f(x)`). **But keep** a variable whose *name* explains an otherwise opaque sub-expression (*Introduce Explaining Variable* — the inverse move). The test: does the name tell the reader something the expression doesn't?

```python
# remove pointless intermediate
def total(items):
    s = sum(i.price for i in items)
    return s                       # ->  return sum(i.price for i in items)

# KEEP — the names carry meaning
is_eligible = user.age >= 18 and user.country in ALLOWED
within_budget = order.total <= user.credit_limit
if is_eligible and within_budget:
    approve(order)
# (do not inline back into one dense boolean)
```

**Anti-rule:** Don't remove an intermediate that is **evaluated once and reused** — inlining it duplicates the computation (and any side effect / cost / non-determinism like `time.time()` or `uuid4()`), which is a behavior change, not a cleanup. Also don't strip a variable that exists purely to give a debugger a stable inspection point or to break a line that's genuinely too long to read. Brevity is not the goal; readability is.

### 8. De-duplicate repeated blocks (DRY) — and resist premature abstraction

**Rule:** Three-plus near-identical blocks that will change together → extract one parameterized function/loop. (Fowler: *Extract Function* + *Pull Up*; the "rule of three".)

```python
# before
log.info("start"); db.connect(); cache.warm("a")
log.info("start"); db.connect(); cache.warm("b")
log.info("start"); db.connect(); cache.warm("c")

# after
def boot(region):
    log.info("start"); db.connect(); cache.warm(region)
for r in ("a", "b", "c"):
    boot(r)
```

**Anti-rule — the important half.** "**Duplication is far cheaper than the wrong abstraction**" (Sandi Metz). Do **not** merge blocks that merely *look* alike but answer to different reasons to change — incidental duplication. Two validators with the same shape today will diverge tomorrow; fusing them creates a function laced with `if mode == ...` flags that is harder to read than the duplication was. Only de-dup when the blocks are the *same knowledge* (will always change together) and the abstraction has a clean, flag-free interface. Two occurrences is usually "wait"; three with a clear shared cause is "go". When unsure, leave the duplication — it's reversible; the wrong abstraction is sticky.

---

## How to apply (agent loop)

1. Read the recently-changed region. Identify candidate sites — idiom transforms and structural rules.
2. For each candidate, check its **anti-rule** / cited trap first. If it fires, skip and move on.
3. Make one small edit per tidying; keep them separable.
4. Run tests / type-check / lint if available; results must be no worse than the pre-edit baseline. Green tests are necessary but **not sufficient** — they rarely cover the empty/`None`/falsy/exception edges where these rewrites break. So also state, in one sentence, why each hunk is behavior-identical; if a hunk touches a trap in python-gotchas.md and you can't make that one-sentence argument, revert it.
5. Report what changed and, briefly, what you deliberately left alone and why (e.g. "kept the duplicated validators — they change for different reasons").

A pass that changes nothing because every candidate hit its anti-rule is a correct outcome. Don't trade behavior for tidiness.

See [reference/python-gotchas.md](reference/python-gotchas.md) for the Python-specific equivalence traps these rules lean on.

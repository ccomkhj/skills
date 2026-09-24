# Python gotchas

Consult the relevant entry when a proposed rewrite touches these semantics.

- **Truthiness and comparisons:** `None`, empty, and falsy are different contracts. NumPy/pandas truth tests may raise. Return `bool(cond)` when a strict boolean is required. Equality may invoke custom methods; replacing `== None` with `is None` can change behavior. Inverse comparisons are not universal complements: for NaN, `not (x > 0)` differs from `x <= 0`. Preserve operand order and truth-test effects.
- **Iteration:** `zip` truncates where indexed access may raise; `enumerate` can differ from indexed access on custom or mutated sequences. Unpacking changes consumption and length requirements. Comprehensions have their own scope. Generators are lazy and single-pass; single consumption does not justify replacing eager computation. Preserve effects across `yield` boundaries.
- **Cleanup and exceptions:** Early returns can skip trailing statements, but still execute enclosing `finally` and context-manager exit handling. Moving cleanup into those constructs can change exception paths. Moving `else` into `try` widens what handlers catch; preserve exception translation, chaining, and logging.
- **Apparently unused names:** Check registration imports, re-exports, callbacks, keyword arguments, reflection, serialization, registries, and monkeypatches. An unread assignment may still perform needed work or raise.
- **Mappings:** `get` changes missing-key behavior and evaluates its default eagerly. `defaultdict` inserts missing keys on subscript access; converting it back to `dict` does not undo those insertions.
- **Formatting and paths:** Formatting styles can use different conversion protocols and evaluation order. `Path` operations are not universally equivalent to `os.path`; check path semantics and string-based interfaces.
- **Generated methods:** `dataclass` may change initialization, equality, representation, and hashing even without obvious custom logic. Verify the methods callers depend on.
- **State and bindings:** Inlining may duplicate computation or change aliases and mutation. Preserve copy depth, mutable-object lifetime, and closure captures such as `lambda i=i: i`.

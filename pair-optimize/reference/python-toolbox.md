# Python profiling & candidate toolbox

A concrete toolbox for **Python targets** (hot path, endpoint, pipeline step). Two uses:

- **A** draws baseline-measurement commands and a *menu of candidate optimizations* from here in the Baseline + candidates round.
- **B** uses the same menu to challenge candidates and the same tools to re-measure in the Challenge / Audit rounds.

**Everything here is a hypothesis, not a truth.** A pattern that wins in the snippet below may be neutral or a loss on your data and your CPython version. The contract is unchanged: nothing is kept unless it is *measured* faster/cheaper AND *provably* output-identical. Profile first; let the profile — not this list — pick the target.

## Picking the target: profilers

Match the tool to the question. **For target selection, prefer a sampling profiler** — `cProfile`'s fixed per-call overhead inflates call-heavy leaves so a cheap-bodied function looks dominant (see SKILL.md "Measurement & equivalence techniques").

| Question | Tool | Command |
|---|---|---|
| Where does wall-clock actually go? (target selection) | **pyinstrument** | `pyinstrument -r html -o prof.html script.py` — in-process, no sudo, statistical |
| Same, for an already-running / prod process | **py-spy** | `py-spy top --pid <PID>` · `py-spy record -o prof.svg --pid <PID>` · `py-spy record -o prof.svg -- python script.py` · `py-spy dump --pid <PID>` |
| CPU **and** memory together, line-level | **scalene** | `scalene script.py` — separates Python vs native vs system time; flags memory hotspots |
| Call-count attribution (NOT wall-clock truth) | **cProfile** | `python -m cProfile -o out.prof script.py` then `python -m pstats out.prof` → `sort cumtime` / `stats 20`. Use to learn *call counts* of a leaf; for a hot leaf the lever is reducing call count, not shaving the body. |
| Which **line** in one known-hot function? | **line_profiler** | decorate with `@profile`, run `kernprof -l -v script.py` |
| Where is memory allocated / leaking? | **tracemalloc** | snapshot before/after, `snapshot2.compare_to(snapshot1, 'lineno')` (see Memory below) |
| Per-line memory of one function | **memory_profiler** | decorate `@profile`, run `python -m memory_profiler script.py` |

Cross-check before believing a hotspot: a leaf that dominates in `cProfile` but not in `pyinstrument` is a call-count artifact, not a wall-clock target.

## The "cheaper" axis: memory as a measurable win

The contract keeps wins that are faster **or cheaper**. For Python, *cheaper* is usually memory/allocations — make it a number, not a vibe:

- **Peak memory** of a run: `tracemalloc.get_traced_memory()[1]`, or `/usr/bin/time -l` (macOS) / `-v` (Linux) for peak RSS.
- **Allocation deltas** between two snapshots — proves a candidate actually allocates less, not just feels lighter.

```python
import tracemalloc
tracemalloc.start()
snap1 = tracemalloc.take_snapshot()
run_candidate()                      # the work
snap2 = tracemalloc.take_snapshot()
for stat in snap2.compare_to(snap1, "lineno")[:10]:
    print(stat)
print("peak:", tracemalloc.get_traced_memory()[1])
tracemalloc.stop()
```

A memory win still owes the *identical-output* half of the contract — a generator that streams instead of materializing must yield the same values in the same order.

## Candidate menu (hypotheses to measure)

Grouped roughly by expected payoff. For each candidate, the *mechanism* of the win and the *correctness risk / adversarial input* B should hunt for. Ranked groups first (algorithmic) usually dominate; the micro-ops last are usually neutral — **measure before keeping any of them.**

### Algorithmic & data-structure (usually the real win)
- **`in` on a `set`/`dict` instead of a `list`** — O(1) vs O(n) membership. Risk: a `set` drops duplicates and ordering; a `dict` needs hashable keys. Adversarial: duplicate elements, unhashable items, order-dependent downstream code.
- **Precompute a lookup `dict` once** instead of repeated linear scans in a loop. Risk: stale map if the source mutates mid-loop.
- **Replace nested-loop join with a hash/index join.** Risk: NULL/None keys, duplicate keys that double-count (the JOIN-double-count trap in SKILL.md).
- **Better algorithm / complexity class** — the only lever that scales with input size; everything below is a constant factor.

### Vectorization (numeric/array workloads)
- **NumPy vectorized op instead of a Python loop** (`a * b`, `arr.sum()`). Risk: dtype shifts (int→float overflow/precision), NaN propagation, silent broadcasting of mismatched shapes. Adversarial: empty array, NaN/inf, integer overflow at the dtype boundary.
- **Pandas/Polars columnar op instead of `.apply`/`iterrows`.** Risk: NaN handling and dtype coercion differ from row-wise Python; group ordering not guaranteed.

### Caching (recomputation)
- **`functools.lru_cache` / `cache` on a pure, hot, repeatedly-called function.** Risk: only valid if the function is *pure* — mutable args, hidden global/clock/IO reads, or unhashable args break it. Adversarial: call with args that mutate between calls; confirm `cache_info()` hits are real.
- **`functools.cached_property`** for an expensive attribute computed once. Risk: invalidation if underlying state changes.

### Memory
- **Generator / iterator instead of a materialized list** when the result is consumed once (`sum(x for ...)`, line-by-line file read). Win: constant memory. Risk: single-pass — re-iteration yields nothing; `len()`/indexing break.
- **`__slots__`** on a class with many instances and fixed fields. Win: drops per-instance `__dict__`. Risk: blocks new attributes and some pickling/multiple-inheritance patterns.
- **`weakref.WeakValueDictionary`** for a cache that must not pin objects in memory. Risk: entries vanish when the last strong ref drops — fine for a cache, wrong for a store of record.

### Parallelism & I/O (only after the work is proven CPU- or I/O-bound)
- **`multiprocessing.Pool` for CPU-bound** work across cores. Risk: pickling overhead can exceed the win for small tasks; non-determinism in result ordering (`map` preserves order, `imap_unordered` does not); not worth it under the GIL for pure-Python CPU work below a threshold — *measure the crossover*.
- **`asyncio`/`aiohttp` for I/O-bound** fan-out (many network/disk waits). Risk: zero benefit for CPU-bound work; introduces ordering and error-aggregation differences vs sequential.
- **Batch I/O / DB writes** — one `executemany` + single commit instead of per-row commit; one bulk request instead of N. Risk: partial-failure semantics change (all-or-nothing vs per-row); transaction size limits.

### DB / query (for SQL-ish Python targets; SQL specifics live in SKILL.md)
- **Index a frequently-filtered/joined column**; confirm with `EXPLAIN QUERY PLAN` / `EXPLAIN ANALYZE` that the scan was actually the bottleneck before adding it (it often isn't — the join is).
- **Select only needed columns** instead of `SELECT *`. Risk: downstream code depending on column presence.

### Micro-ops (usually NEUTRAL — default to revert unless measured)
These are the cargo-cult tweaks pair-optimize exists to catch. They rarely move wall-clock on a real workload; keep one *only* if it shows a measured win on representative data.
- List comprehension / `map` instead of an append loop.
- `"".join(parts)` instead of `+=` string building (this one *does* matter at scale — quadratic vs linear; measure).
- Hoisting a global into a local inside a tight loop; inlining a tiny helper to dodge call overhead.

## Benchmark harness (commit to `bench/`)

A's harness must report **median + spread over N runs** (not one run) and ship an equality check B can re-run headless. Minimal shape:

```python
import statistics, timeit

def bench(fn, *, number, repeat=7):
    samples = timeit.repeat(fn, number=number, repeat=repeat)
    per = [s / number for s in samples]
    return {"median": statistics.median(per),
            "min": min(per),
            "stdev": statistics.pstdev(per)}

base = bench(lambda: baseline(data), number=100)
cand = bench(lambda: candidate(data), number=100)
print(f"baseline  median={base['median']:.6f}s ±{base['stdev']:.6f}")
print(f"candidate median={cand['median']:.6f}s ±{cand['stdev']:.6f}")
print(f"speedup={base['median']/cand['median']:.2f}x  (keep only if > noise)")

# equality half of the contract — committed so B re-runs it in the audit round
assert candidate(data) == baseline(data), "output diverged — revert"
```

For richer stats use `pytest-benchmark` (`pytest bench/ --benchmark-only`), which reports median/IQR/outliers and supports `--benchmark-compare` across runs. Whatever the tool: report spread, state cache/JIT state, and run enough reps that the speedup clears the noise band — a 1.05x "win" inside ±10% variance is `UNVERIFIED`, not a win.

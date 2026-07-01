# SQL & DuckDB profiling & candidate toolbox

A concrete toolbox for **SQL / DuckDB targets** (a query, a view, a pipeline step). DuckDB-first, with general SQL / Postgres notes where they diverge. Two uses:

- **A** draws baseline-measurement commands and a *menu of candidate rewrites* from here in the Baseline + candidates round.
- **B** uses the same menu to challenge candidates and the same tools to re-measure in the Challenge / Audit rounds.

**Everything here is a hypothesis, not a truth.** A rewrite that wins on one engine, one data distribution, or one cache state may be neutral or a loss on yours. The contract is unchanged: nothing is kept unless it is *measured* faster/cheaper AND *provably* output-identical. Read the plan — not this list — to pick the target.

## Picking the target: read the plan

The query plan is the profiler. Find the operator that owns the time and the cardinality blow-up (a join whose output is 100× its inputs), not the operator you assume is slow.

| Engine | Command | What to read |
|---|---|---|
| **DuckDB** | `EXPLAIN ANALYZE <query>;` | Per-operator **wall-time** and **actual rows**. The hot operator is usually a HASH_JOIN or a scan, rarely the filter. |
| **DuckDB** | `PRAGMA enable_profiling='json'; PRAGMA profiling_output='plan.json';` then run query | Machine-readable operator timings/cardinalities for diffing two query shapes. `query_graph` for a visual tree. |
| **DuckDB CLI** | `.timer on` | Wall-time per statement (no plan) — quick baseline loop. |
| **DuckDB** | `EXPLAIN <query>;` | Logical+physical plan *without* running — cheap structural check of join order / pushdown. |
| **Postgres** | `EXPLAIN (ANALYZE, BUFFERS, VERBOSE) <query>;` | Actual rows vs *estimated* rows (a big gap = stale stats → `ANALYZE`), buffer hits/reads, the costly node. |
| **SQLite** | `EXPLAIN QUERY PLAN <query>;` | Whether a scan or an index is used; nested-loop join shape. |

Cross-check estimate vs actual rows: a node estimating 1k rows but producing 10M is the optimizer flying blind — the fix is often *stats / a rewrite that helps estimation*, not brute force.

## The "cheaper" axis: scanned rows/bytes, intermediate cardinality, spill

The contract keeps wins that are faster **or cheaper**. For SQL, *cheaper* is measurable and often the truer signal (it's cache-state-independent):

- **Rows / bytes scanned** — straight off `EXPLAIN ANALYZE` (DuckDB) / `BUFFERS` (Postgres). A rewrite that scans 10× fewer bytes is a real win even if a warm-cache wall-time looks flat.
- **Peak intermediate cardinality** — the largest "actual rows" any operator emits. Shrinking the build side of a join or pre-aggregating before it lowers this.
- **Spill to disk** — DuckDB spills when a hash table/sort exceeds `memory_limit`; a query that stops spilling is cheaper and usually much faster. Watch temp-file size, or raise `PRAGMA memory_limit` to confirm spill was the cause before "optimizing."

A cheaper-but-not-faster rewrite still owes the *identical-output* half of the contract.

## Candidate menu (hypotheses to measure)

Grouped by payoff. Scan/cardinality reductions dominate on analytical (OLAP/DuckDB) workloads; OLTP indexing matters only when a point/range lookup is the proven bottleneck. Each carries the *adversarial input* B should hunt for.

### Scan reduction (usually the real win on columnar/DuckDB)
- **Projection pushdown** — select only needed columns, never `SELECT *`. DuckDB/Parquet read *only referenced columns*, so this directly cuts bytes scanned. Risk: downstream code depending on a dropped column.
- **Predicate pushdown / partition pruning** — push `WHERE` filters as early as possible; for Parquet/hive-partitioned data, filter on the partition key so whole files are skipped (`read_parquet('.../dt=*/...')` + `WHERE dt = ...`). Risk: a `CAST` or function wrapping the filtered column **disables** pushdown — filter on the raw column, cast the literal instead.
- **Columnar format over CSV** — for repeated reads, materialize to Parquet (`COPY ... TO 'x.parquet'`); CSV re-parse is frequently the actual bottleneck, not the query.

### Join shape (the other real win)
- **Shrink / pre-aggregate the build side** — aggregate or filter a table *before* joining so the hash build is small. Risk: pre-aggregation changes grouping semantics — verify NULL groups and duplicate keys survive.
- **`EXISTS` / `IN` vs `JOIN`** — a `JOIN` to a non-unique key **double-counts** (the union-semantics trap in SKILL.md: a unique-key dev sample hid a JOIN double-count bug; `EXISTS` preserved it). Use `EXISTS` for "does a match exist," `JOIN` only when you want the matched rows. Adversarial: duplicate/overlapping keys on the join side.
- **Window function instead of a self-join** — `ROW_NUMBER`/`LAG`/running aggregates replace correlated self-joins. Risk: frame/`PARTITION BY`/`ORDER BY` must reproduce the old grouping exactly; NULL ordering (`NULLS FIRST/LAST`) differs by engine.
- **Decorrelate a subquery** — turn a correlated subquery into a join or window. DuckDB decorrelates well automatically; confirm the plan actually changed before crediting the rewrite.

### Aggregation & dedup
- **Drop a band-aid `DISTINCT`** — `SELECT DISTINCT` slapped on to hide a fan-out join costs a full sort/hash *and* masks the underlying double-count bug. Fix the join instead. Adversarial: rows that are legitimately duplicated — confirm multiplicity is what you intend.
- **Approximate aggregates** — `approx_count_distinct()`, reservoir sampling, `approx_quantile()` trade exactness for speed. This **moves the correctness bar** — only valid if the consumer tolerates approximation; must be flagged `UNVERIFIED`-against-exact and signed off, never silently kept.

### DuckDB-specific levers
- **Threads & memory** — `PRAGMA threads=N`, `PRAGMA memory_limit='8GB'`. More threads help scan-heavy queries; more memory stops spill. Measure the crossover — over-threading a tiny query adds overhead.
- **`MATERIALIZED` CTEs** — DuckDB inlines CTEs by default (good — enables pushdown across the boundary). Force `WITH x AS MATERIALIZED (...)` only when the same CTE is reused several times and recomputation dominates. Risk: materializing breaks pushdown into the CTE — can be *slower*; measure both.
- **Indexes are rarely the lever** — DuckDB is scan-optimized; ART indexes help point lookups and unique constraints, **not** range scans or full-table analytics. Do not cargo-cult OLTP indexing here; confirm with `EXPLAIN ANALYZE` that a point lookup is the bottleneck first.

### OLTP indexing (Postgres / SQLite — when a lookup is the proven bottleneck)
- **Index a frequently-filtered/joined column**; for multi-column filters, composite-index column order matters (most-selective-first / leftmost-prefix rule). A covering index (all selected columns) avoids the heap fetch. Risk: indexes slow writes and cost storage; an index the planner ignores (low selectivity, function-wrapped column) is pure overhead — confirm with `EXPLAIN` that it's used.
- **Refresh stats** — a bad plan is often stale statistics, not a missing index. `ANALYZE <table>;` before concluding.

## Equivalence: SQL has a duplicate-row trap

The contract's *identical-output* half is subtle for SQL because set operators silently collapse multiplicity.

- **`EXCEPT` is set-based — it removes duplicates**, so `(A EXCEPT B)` empty + `(B EXCEPT A)` empty does **not** prove A and B have the same *row counts*. A candidate that changes multiplicity (the exact double-count bug above) passes a naive `EXCEPT` check. Use **`EXCEPT ALL`** in both directions, or compare `COUNT(*)` + a grouped checksum, to catch multiplicity changes.
- **Canonical full-equality check** (run both directions):
  ```sql
  SELECT count(*) FROM ((<baseline> EXCEPT ALL <candidate>)
                        UNION ALL
                        (<candidate> EXCEPT ALL <baseline>)) d;   -- must be 0
  ```
  Or order-independent hash: `SELECT md5(string_agg(col_concat, '' ORDER BY <stable key>)) FROM ...` for each, compare.
- **Aggregate ordering** — `SUM`/`AVG` over floats have no guaranteed summation order, so accept a tolerance (~1e-12), not bit-identity, and say so. Integer aggregates must match exactly.
- **NULL & empty** — `GROUP BY` keeps a NULL group; `JOIN`/`IN` drop NULL matches but `NOT IN (... NULL ...)` returns no rows at all. Build the adversarial input: a NULL key, an empty input, a duplicate/overlapping key — run baseline-shape vs candidate-shape on it directly.
- Commit the equivalence query to `bench/` so B re-runs it headless in the audit round. Run both shapes on the **same live engine/connection** — a fresh connection may lack the schema `search_path` (SKILL.md).

## Benchmark harness (commit to `bench/`)

Report **median + spread over N runs**, and state cache state explicitly — DuckDB caches Parquet metadata and the OS caches pages, so run 2 is often far faster than run 1.

```python
import duckdb, statistics, time

con = duckdb.connect("warehouse.db")   # same connection/search_path both shapes
def timed(sql, *, reps=7, warmup=1):
    for _ in range(warmup):            # decide: measure WARM (steady-state) or
        con.execute(sql).fetchall()    # skip warmup to measure COLD — state it
    s = []
    for _ in range(reps):
        t = time.perf_counter(); con.execute(sql).fetchall()
        s.append(time.perf_counter() - t)
    return {"median": statistics.median(s), "min": min(s), "stdev": statistics.pstdev(s)}

base = timed(BASELINE_SQL); cand = timed(CANDIDATE_SQL)
print(f"baseline  median={base['median']:.4f}s ±{base['stdev']:.4f}")
print(f"candidate median={cand['median']:.4f}s ±{cand['stdev']:.4f}")
print(f"speedup={base['median']/cand['median']:.2f}x  (keep only if > noise)")

# cheaper axis — pull actual scanned rows from the plan, not a guess
print(con.execute("EXPLAIN ANALYZE " + CANDIDATE_SQL).fetchall()[0])

# equality half of the contract — EXCEPT ALL both directions, committed for B
diff = con.execute(f"""
  SELECT count(*) FROM (({BASELINE_SQL}) EXCEPT ALL ({CANDIDATE_SQL})
                        UNION ALL
                        ({CANDIDATE_SQL}) EXCEPT ALL ({BASELINE_SQL}))""").fetchone()[0]
assert diff == 0, f"output diverged by {diff} rows — revert"
```

Whatever the engine: report spread, state cache state, isolate from a contended shared server (the 124s-vs-9s contention trap in SKILL.md — re-measure a suspected elephant in isolation), and run enough reps that the speedup clears the noise band. A warm-cache 1.1x inside ±15% variance is `UNVERIFIED`, not a win.

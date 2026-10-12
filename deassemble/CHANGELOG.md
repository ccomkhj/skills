# Changelog

## 1.3.0 — 2026-09-26

Third-run refinements (run 3 reached `completed` status).

- `absence` events must carry `absence.expected` and `absence.searched`; the viewer shows them.
- `report_builder.py`: `source_excerpt` reads excerpts from disk and rejects a line range past EOF or a symbol absent from it; `source_minified` cites one-line files by byte offset; `group_jsonl` splits a capture on a structural marker.
- `smoke_report.mjs`: empty-search, state-expansion and keyboard checks; prints a `not_covered` list.
- Guidance: clear or rebuild the framework's compiled cache after reverting probes (a stale instrumented snapshot leaked into a later baseline boot); shared-checkout warning and worktree advice; copy metadata files, not bundles; correlation markers instead of timestamps; relay prefixes on wrapper-spawned children; scoped type-check with global `.d.ts`; hot reload is not a new run; evidence-kind list split into event classes, step statuses and note kinds; status example; decision events carry `after` only; step-by-step conventions inlined.

## 1.2.0 — 2026-09-26

Evaluated on `app_frontend` (eve agent request path) in independent subagent runs; each run's friction log drove the next revision.

### Report schema 1.1 (was 1.0)

- `event.evidence_class` (required): `observed`, `observed-instrumented`, `mock-backed`, `fixture`, `absence`. The viewer's badge comes from it; the original stamped every event OBSERVED.
- `story` layer: numbered steps with `status`, `technical`, `intuitive`, `chips`, `loop`, `sources`, `event_ids`, `related_event_ids`, plus `overview`, `diagram` and `cast`. Steps the run never reached stay in the list as `not-observed` / `source-only`. The validator rejects a step whose status is stronger than its weakest backing event.
- `event.explain.{technical,intuitive}` (optional per event; required on story steps).
- `run.runs[]` with `role` (baseline, instrumented, mock, fixture, discovery) and `event.run_id`, so baseline and instrumented evidence never share a run id.
- `source.line_basis` (`revision` | `instrumented`), `source.patch`, `source.byte_offset`; `line` optional when `byte_offset` is given.
- `sources[]` accept `path` + `version` for locally installed documentation as an alternative to `url`.
- `event.clock` names the clock behind `elapsed_ms`.

### Tooling

- `build_report.py`: `--check` (validate only), `--template` (customized viewer), `--force` documented.
- `smoke_report.mjs`: headless jsdom check (navigation, filters, tabs, story steps, causal links) with a PASS/FAIL line.
- `report_builder.py`: helper for generating `report.json` from captures with unique ids, shared evidence and validation before write.
- Viewer: story panel, evidence-class badges, explanation boxes, step filtering, related-event navigation, byte offsets, line-basis note.

### Guidance

- Minimum viable run in priority order; what to cut first.
- Rejection-boundary scenarios (auth you may not pass): make the rejection shapes the scenario, record absences, cover the rest with mock-backed runs.
- Verify a framework's native tracing records the chosen scenario before relying on it; copy caches and registries before the first command; redirect every inspection to `evidence/` when it runs; learn ports from the process table.
- Type-clean wrapper probe pattern that records entry, exit and thrown code; save the patch, revert, re-hash; note untracked files a framework auto-registered.
- `run.status` describes the planned scenario list; the gap to the learning goal lives in coverage and story-step statuses.
- Never read or print env files; source them only to launch a program.

## 1.0.0

Original bundle as downloaded (`SKILL.md`, capture guide, report contract, `build_report.py`, `viewer.html`, tests).

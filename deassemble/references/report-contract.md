# Interactive report contract (schema 1.1)

Contents: Experience; Bundled renderer; JSON structure; Field semantics; Story layer; Delivery and validation.

## Experience

The report has two layers that share one data file:

- **Story** (top of the page): numbered steps in execution order, each with a status badge (observed, observed-instrumented, mock-backed, fixture, absence, not-observed, source-only), an engineer explanation, a ten-year-old explanation, the `path:line · symbol` that ran, and a button that filters the recorded events to that step. Steps the run never reached stay in the list, marked `not-observed` or `source-only`, so the reader sees the whole expected sequence and exactly where the evidence stops.
- **Recorded execution explorer** (below): select a scenario or story step, advance one captured event, inspect the source excerpt, the state snapshot, the before/after difference, and the evidence behind it; follow causal links and object identities.

Synchronize these views to the selected event: flow/timeline with status and evidence class; observation plus separately labeled explanation, interpretation and documentation; exact source location and a bounded excerpt from the executed revision, or an explicit mapping gap; expandable snapshots; an evidence panel with sanitized excerpts and artifact locators.

Show overview, capture scope, gaps, reproduction details and run status without requiring the user to inspect every event. Preserve concurrent branches instead of drawing an unjustified linear flow. Do not fabricate elapsed durations.

Provide keyboard-accessible previous/next navigation, event selection, filters and optional playback. Explain that backward navigation reopens a recorded snapshot; it does not roll back a database or rerun the program.

## Bundled renderer

`scripts/build_report.py` (Python 3.10+, standard library only) validates reference integrity and basic shape, then embeds the JSON in `assets/viewer.html`. It has no capture agent, no server, no network dependency. It cannot establish whether supplied data was genuinely recorded and does not redact.

```bash
python /path/to/deassemble/scripts/build_report.py run/report.json --check                 # validate only
python /path/to/deassemble/scripts/build_report.py run/report.json --output run/report.html
python /path/to/deassemble/scripts/build_report.py run/report.json --output run/report.html --template my-viewer.html
node   /path/to/deassemble/scripts/smoke_report.mjs run/report.html --jsdom-from /path/to/project   # headless check
```

`--template` accepts a customized copy of the viewer; it must keep the `__DEASSEMBLE_PAYLOAD__` marker, the `<script id="viewer-code">` block and the `__DEASSEMBLE_SCRIPT_HASH__` marker. A customized template is not covered by `tests/test_build_report.py`; run the smoke script against its output instead.

The baseline supports scenario and story-step filtering, text search, event/arrow navigation, playback, a scrubber, expandable state trees, differences between comparable fields, clickable causal links, instance following, source excerpts, evidence, run metadata and a JSON export. For very large recordings, reduce the scoped run or implement a chunked local viewer; never silently drop evidence to fit the template.

## JSON structure

Bracketed strings describe fields; they are not execution evidence. Do not emit placeholders in a completed report.

```json
{
  "schema_version": "1.1",
  "run": {
    "id": "[unique run ID]",
    "title": "[project and scenario]",
    "purpose": "application",
    "status": "completed",
    "summary": "[evidence-backed overview]",
    "command": ["[primary launch executable]", "[argument]"],
    "cwd": "[safe working directory]",
    "source_revision": "[revision or source hashes]",
    "started_at": "[UTC timestamp]",
    "runtime": {"[runtime]": "[observed version]"},
    "runs": [
      {"id": "baseline", "role": "baseline", "command": ["npm", "run", "dev"], "started_at": "[UTC]"},
      {"id": "probes", "role": "instrumented", "command": ["npm", "run", "dev"], "started_at": "[UTC]", "instrumentation": "evidence/probes.patch (reverted)"},
      {"id": "tests", "role": "mock", "command": ["npx", "vitest", "run"], "started_at": "[UTC]"}
    ],
    "capture": {
      "method": "[actual instrumentation]",
      "ordering": "collector order; causal links are explicit",
      "limits": "[scope and snapshot bounds]",
      "redaction": "[applied export policy]",
      "overhead": "not measured"
    },
    "coverage": [
      {"area": "[area]", "status": "observed", "detail": "[coverage or gap]"}
    ],
    "reproduction": ["[exact safe setup and run instructions]"]
  },
  "scenarios": [
    {"id": "startup", "title": "Startup", "description": "[performed actions]", "outcome": "[observed outcome]"}
  ],
  "story": {
    "overview": "[two or three sentences: what the run did, where evidence stops]",
    "diagram": "[optional plain-text flow, one hop per line]",
    "cast": [{"part": "[component]", "role": "[its part in the analogy]"}],
    "steps": [
      {
        "id": "st1",
        "title": "[what happens in this step]",
        "status": "observed",
        "chips": ["[trigger or event name]", "[once | every request]"],
        "loop": "[optional: what repeats and until when]",
        "sources": [{"path": "[file]", "line": 1, "symbol": "[function]", "what": "[one line]"}],
        "event_ids": ["e1"],
        "related_event_ids": ["e40"],
        "technical": "[for an engineer: trigger, code, data in, state change, result, next]",
        "intuitive": "[for a ten-year-old, with the analogy mapped back]"
      },
      {
        "id": "st9",
        "title": "[a step the run did not reach]",
        "status": "not-observed",
        "sources": [{"path": "[file]", "line": 1, "symbol": "[function]"}],
        "technical": "[what the source says would happen and why it was not reached]",
        "intuitive": "[same, for a child]"
      }
    ]
  },
  "events": [
    {
      "id": "e1",
      "scenario_id": "startup",
      "run_id": "baseline",
      "process": "p1",
      "kind": "startup",
      "label": "[observed transition]",
      "status": "ok",
      "evidence_class": "observed",
      "observation": "[what this recording shows, nothing more]",
      "explain": {"technical": "[engineer]", "intuitive": "[ten-year-old]"},
      "source": {
        "path": "[source file]",
        "line": 1,
        "symbol": "[function]",
        "revision": "[executed source hash]",
        "line_basis": "revision",
        "patch": "[optional: evidence/probes.patch when a temporary patch was applied]",
        "code_start_line": 1,
        "code": "[actual source excerpt]"
      },
      "objects": ["p1:job:1"],
      "before": {"job": {"$capture": "not_captured", "reason": "[reason]"}},
      "after": {"job": {"$object_id": "p1:job:1", "$type": "Job", "fields": {"status": "[observed value]"}}},
      "causes": [],
      "evidence_refs": ["r1"],
      "clock": "[optional: which clock elapsed_ms uses]",
      "absence": {"expected": "[required on absence events: what would have appeared]", "searched": "[evidence range searched]"},
      "notes": [],
      "capture_gaps": []
    }
  ],
  "evidence": [
    {"id": "r1", "kind": "structured-log", "path": "evidence/events.jsonl", "locator": "line 1", "excerpt": {"[captured field]": "[captured value]"}}
  ],
  "sources": [
    {"title": "[documentation]", "url": "https://example.org/doc", "accessed_at": "[date]", "note": "[why]"},
    {"title": "[installed package docs]", "path": "node_modules/pkg/docs/hooks.md", "version": "[installed version]"}
  ]
}
```

## Field semantics

`run.purpose` is `application` or `demo`; label a demonstration unmistakably. `run.status` describes the **planned scenario list**, not the learning goal: `completed` when every planned scenario (a planned mock-backed test run included) executed and was recorded as intended, `partial` when a planned scenario was cut short, failed, or had to be replaced by a weaker kind of evidence than planned, `blocked` when nothing meaningful executed. Gaps between the learning goal and what ran belong in `coverage` and in `not-observed` or `mock-backed` story steps; they never downgrade the status. A blocked report may have no events; do not insert imaginary startup events.

`run.runs[]` holds one entry per distinct execution (baseline, instrumented, mock, fixture, discovery) with its own id, command and start time. `run.command` stays the primary launch. Events carry `run_id` to say which execution produced them; never mix baseline and instrumented evidence under one run id.

Unique IDs within scenarios, events, evidence and story steps. Every event has a valid scenario and at least one evidence reference. **Evidence records are shared**: reference the same id from every event it supports instead of duplicating it. Store only observed runtime steps in `events`; put interpretations and source-only discoveries in notes, coverage and story steps. One event per decision of the canonical request is enough; identical decisions repeated across request shapes may be grouped into one event when its evidence record cites the full line range and the observation says how many repeats it covers.

`scripts/report_builder.py` assembles `report.json` from a generator script (unique ids, shared evidence, validation before write); hand-writing dozens of events is the slowest part of a run.

`event.evidence_class` is required: `observed` (unmodified application), `observed-instrumented` (application with temporary probes), `mock-backed` (real code under a test harness with mocked dependencies), `fixture` (replayed recorded input), `absence` (an observed non-occurrence in a real run, for example no probe line where one would appear). The viewer shows the class as the event's badge. An `absence` event carries `absence.expected` (what would have appeared) and `absence.searched` (the evidence range that was searched); the validator requires both. A mock-backed step may list an `absence` event among its backing events (absence is an observation).

`event.status` is `ok`, `error`, `running` or `unknown`; kinds are free-form. `event.observation` states only what the recording shows. `event.explain.technical` and `event.explain.intuitive` carry the two explanation levels; they may interpret, but must not claim runtime facts absent from the evidence. `notes` entries use `kind` = `inference`, `source-only` or `external explanation`.

Keep events in collector/playback order. Optionally provide `timestamp`, `elapsed_ms`, `clock` (the clock basis for `elapsed_ms`, for example `probe process monotonic` or `Date.now() in eve dev`), `thread`, `task`, `trace_id`, `span_id`. Do not use playback index as a source of causal certainty.

`causes` entries look like `{"event_id":"e1","relation":"observed","basis":"same captured request ID"}`; `relation` is `observed` or `inferred`. Missing upstream events go in `capture_gaps`, not dangling references.

`objects` is optional. Use it for captured instance IDs; process-level identities such as `baseline:process:next-server` are fine when no finer instance exists. Snapshots: plain JSON for safe observed values; `$type`, `$object_id`, `fields` when useful; `$capture` markers `not_captured`, `redacted`, `truncated`, `unavailable`, `absent` with a `reason`. Reserve JSON null for an observed null. For a function's decision, use `{"$type": "decision", "fields": {"fn": "[name]", "returned": "[value or null]", "threw": "[error code or absent]", ...}}` in `after` and omit `before` (a pure decision has no prior state). Encode integers outside the exact JavaScript Number range as typed decimal strings; encode non-finite numbers explicitly. Omitting `before` or `after` means not captured; an empty object means the captured projection has no recorded fields.

`source`: `path`, `revision`, `code` and usually `line`; optional `end_line`, `symbol`, `code_start_line`, `byte_offset` (for minified or generated files; `line` may then be omitted and the viewer shows the offset; `report_builder.source_minified` finds it). `report_builder.source_excerpt` reads the excerpt from disk and rejects a line range past EOF or a symbol absent from it. Also optional: `line_basis` (`revision`, the default, when line numbers refer to the unpatched revision; `instrumented` when they refer to the temporarily patched file) and `patch` (the saved patch path). When a temporary patch shifted lines, either keep `line_basis: revision` and cite the unpatched line, or set `instrumented` and cite the patched line; never leave the reader guessing which.

`evidence`: `id`, `kind`, `path`, `locator`, sanitized `excerpt`, optional `sha256`. Extra fields such as `request_id` or `group` are allowed and useful for saying which request a line range belongs to; `report_builder.group_jsonl` splits a JSONL capture on a structural marker. Store the complete sanitized capture files with the report.

`sources[]`: `title` plus exactly one of `url` (HTTP(S), for documentation online) or `path` (locally installed documentation, with `version`). These are supplementary, never evidence that this application performed an action.

## Story layer

`story.steps` is the numbered walkthrough. Steps follow execution order; group repeated events (the same walk for seven request shapes) into one step and let `event_ids` list them all. A step may draw its backing events from several `run_id`s (a scenario is one run's slice; a step is one stage of the story). Each step needs `title`, `status`, `technical` and `intuitive`. Steps with an evidence-class status must list the events that back them and may not claim stronger evidence than their weakest backing event (`absence` counts as observed); the renderer rejects an overstatement. Put a live step's mock-backed twin, or any other event worth a jump, in `related_event_ids`: they are navigable but never count as backing. Indirect proof from a real response (a 404 body naming the upstream origin proves the rewrite) counts as observed when the observation states the inference basis. Steps with status `not-observed` or `source-only` may list no events; use them to keep the expected sequence visible past the point where the run stopped, and say in `technical` why it was not reached. `loop` marks repeating steps; `chips` carry the trigger (an event name, "once at startup", "every request"); `sources[]` entries take `path`, optional `line`, `symbol` and a one-line `what` shown after the location. `cast` maps components to the roles used in the intuitive explanations so one analogy runs through the report; include components that appear only in not-observed steps so the analogy stays whole.

Per-event `explain` is optional and best used where an event carries an insight the step summary does not; the story steps are where both levels are required.

## Delivery and validation

Keep the report self-contained. Escape embedded JSON and render captured values as text, never executable HTML. Restrict external links to deliberate documentation links. Do not load third-party scripts, fonts or telemetry.

Ship `report.html`, normalized `report.json`, the run manifest, sanitized captures, capture/instrumentation scripts and reproduction instructions. Verify with `--check`, then the smoke script (or a browser), and disclose which checks could not be performed (the smoke script cannot verify the CSP hash or visual layout).

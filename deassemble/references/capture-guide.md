# Capture guide

Read before instrumenting a project. Treat these as outcome constraints, not a required tracing stack.

## Choose observation points

Start with lifecycle and application boundaries. Deepen only where the learning question requires more state. Existing logs may establish that an operation happened without revealing its arguments or instance fields; add targeted capture rather than inventing them.

| Context | Useful real observations |
| --- | --- |
| Startup | Launcher and child processes; module/lifecycle hooks; configuration provenance; resource construction; successful readiness checks. |
| Frontend | User action; handler entry; safe event payload; captured state before/after; rendered result; network request/response IDs. Do not equate component state with DOM output. |
| Backend | Request arrival; middleware; authentication and authorization decisions separately; input parsing; handler/service calls; observed database operations; response. |
| Data pipeline | Actual input identity; schema and row counts; representative safe values; stage inputs/outputs; rejected rows; output artifacts. |
| ML | Dataset split and preprocessing; actual model/configuration identity; tensor shapes/dtypes; bounded samples/statistics; training/inference events and measured metrics. |
| AI workflow | Safe request payload or template identity; retrieved document IDs; model/tool calls; streaming chunks; responses and retries. Never invent hidden model reasoning or remote internal activations. |

For authentication, record mechanism, decision, and safe test-principal/role metadata. Do not dump passwords, tokens, cookies, private keys, or full identity profiles. Do not call a token "verified" because it was merely decoded.

For databases, distinguish client construction, pool configuration, connection checkout, actual successful query, and transaction commit. Keep query parameters and returned samples only when safe. A returned row count does not reveal unrecorded row contents. A successful query on a disposable test database is not proof that production is connected.

## Before relying on a framework's own tracing

Many runtimes ship local diagnostics (`<cli> logs`, `<cli> traces`, debug servers, OpenTelemetry exporters). Run the chosen scenario once against the unmodified application and check what those diagnostics actually recorded before building the capture plan on them. A framework that traces sessions records nothing for a request rejected before a session exists. Record caches and build artifacts that predate the run (compile manifests, discovery caches, stale pid files) and say whether the run rebuilt or reused them.

## Minimal reversible probes

When existing logs do not show which function decided what, add tagged one-line probes rather than a tracing stack:

```ts
process.stderr.write(`[deassemble-probe] ${JSON.stringify({ t: Date.now(), fn: "cronServiceAuth", method, path, decision: "null (no bearer)" })}\n`);
```

To record *which branch* a function returned without editing every `return`, wrap the function once at its export and let the probe report entry, exit and the returned value's shape (type-clean under strict TypeScript):

```ts
type Probe = Record<string, string | number | boolean | null>;
const probe = (fields: Probe): void => {
  process.stderr.write(`[deassemble-probe] ${JSON.stringify({ t: Date.now(), ...fields })}\n`);
};
export function cronServiceAuth(): AuthFn<Request> {
  const inner = cronServiceAuthImpl();          // the original function body, renamed
  return async (request) => {
    probe({ fn: "cronServiceAuth", phase: "enter", method: request.method, path: new URL(request.url).pathname });
    try {
      const result = await inner(request);
      probe({ fn: "cronServiceAuth", phase: "exit", accepted: result !== null });
      return result;
    } catch (error) {
      probe({ fn: "cronServiceAuth", phase: "throw", code: (error as { code?: string }).code ?? "unknown" });
      throw error;
    }
  };
}
```

Emit a correlation marker per request (a header value the probe echoes, or the first probe of each walk as a structural boundary) so lines can be grouped without timestamps. A child spawned by a wrapper relays stderr with a prefix (for example `[eve:dev] `); strip it by pattern. Type-check with a scoped program that includes the project's global `.d.ts` augmentations and compare against the unpatched baseline. Where the reason for a `null` matters (no bearer vs wrong bearer), set a local `reason` string at each return and include it in the exit probe; that touches the returns but keeps each edit to one token. Type-check the patched files the way the project does (`npx tsc --noEmit`) before launching, so a failed compile does not cost a run.

Rules: emit only names, booleans, lengths, status codes and enum-like decisions, never header or env values; keep the tag unique so the log can be split mechanically; save the diff as `evidence/<name>.patch` before reverting with `git checkout --`; re-verify the file hashes afterwards; run baseline and instrumented captures as separate `run.runs` entries; record in `source.line_basis` whether cited line numbers refer to the patched or unpatched file. Probes in files that a framework auto-registers (tool, hook or channel directories) must never be new files, only edits to existing ones. Diff `git status` against the framework's discovery output: an untracked file that predates the run may already be registered (a skill, a tool), and the report should say so.

After reverting probes, clear or rebuild the framework's compiled cache (or verify its live build pointer) before the next baseline boot; a stale snapshot compiled from an instrumented tree will otherwise print probe lines into a run that never patched anything. Redirect every inspection you might cite (`ps`, `lsof`, `ls`, registry or pid files, the framework's `logs ls` / `traces ls`) to a file under `evidence/` at the moment you run it. A terminal transcript recreated afterwards is weaker evidence and must be labeled as such. Copy framework cache and registry files before your first command, discovery included, because discovery itself rewrites them. Learn the actual listening ports from the framework's registry or the process table rather than from documentation.

Evidence of absence is evidence: when a probe that fires on every walk does not fire for one route, record an `absence` event pointing at the log range where it would have appeared.

## Identity, state, and timing

Assign run IDs and event IDs. Preserve process, thread/task, request/job, trace/span, and message IDs when available. Attach source path, symbol, line range, and executed source revision or hash. Use source maps only when they correspond to the actual build; otherwise disclose unmapped generated code.

Maintain an object identity registry scoped to process and lifetime where feasible. Do not equate a memory address across runs, equal serialized values, or a database primary key with one in-memory instance. Link copied or deserialized objects as related, not identical.

Snapshot at the selected boundary; identify whether this is before a line, after a statement, at function entry, at return, or at an application hook. Capture plain fields with safe serializers. Do not invoke arbitrary getters, descriptors, `repr`, lazy database properties, or expressions that can change state just to inspect them. Do not retain mutable references and serialize them later as if they were historical snapshots.

Bound nesting, collection size, string length, event count, and duration. Represent cycles, references, unavailable values, redaction, and truncation explicitly. Include total size/shape and sample selection for large collections when known. Never imply a preview is a complete tensor, table, object graph, or heap.

Record monotonic time within a process and wall-clock time for context where available. Preserve collector order for navigation, but use confirmed relationships for causal claims. Account for clock skew, buffering, parallel spans, queued work, retries, reloads, and missing events. Never infer a global order merely by sorting timestamps.

Capture parent/child or message links at the actual boundary. Mark heuristic matches as inferred. Do not leak sensitive trace baggage to outside services. Treat incoming correlation IDs as untrusted. Expose unlinked spans as gaps rather than guessing their parents.

## Capture safety and completeness

Redact as early as possible, preferably before writing anything to disk. Use allowlisted data fields plus name- and content-based checks; a list of suspicious field names alone is insufficient. Inspect headers, connection strings, URLs, request/response bodies, exception messages, prompts, source snippets, and reproduction commands. Use synthetic test identities and data by default.

Keep any unavoidable private raw artifacts restricted, out of deliverables, and subject to an explicit retention plan. Do not transmit them to web searches or third-party viewers. Scan the entire exported report and embedded JSON, not only visible text. HTML escaping prevents script injection; it does not remove secrets.

Document which paths and values were captured, disabled hooks, dropped events, sampling, known blind spots, whether instrumentation changed timing or behavior, and what was not measured. Compare safe baseline outputs where feasible. Avoid claims about application performance based only on an instrumented run.

Record enough commands, input identities, dependencies, fixture state, and instrumentation patches for another authorized operator to repeat the experiment. A repeat run is a new observation, not guaranteed reproduction of the same scheduling, generated IDs, model output, or external responses.

## Tool selection notes and primary sources

Verify APIs against installed versions before use; these references are conceptual starting points, not dependencies or a requirement to upgrade the project.

- OpenTelemetry context propagation: https://opentelemetry.io/docs/concepts/context-propagation/ . Use trace context to connect observations across boundaries; it does not automatically capture arbitrary local variables.
- OpenTelemetry sensitive-data handling: https://opentelemetry.io/docs/security/handling-sensitive-data/ . Apply data minimization and explicit redaction to telemetry exports.
- Python execution monitoring: https://docs.python.org/3/library/sys.monitoring.html . Check event availability and interpreter version before choosing hooks.
- Python object inspection: https://docs.python.org/3/library/inspect.html . Prefer inspection methods that avoid executing descriptors or properties.
- Node.js debugging: https://nodejs.org/learn/getting-started/debugging . Keep inspector access restricted; a debugger is privileged access to the running application.
- Node.js inspector API: https://nodejs.org/api/inspector.html . Use supported debugger interfaces when targeted state capture requires them.

Reference check date: 2026-09-26. Cite project-specific documentation separately in the generated report and identify which content is supplementary explanation rather than runtime evidence.

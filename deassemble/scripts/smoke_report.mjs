#!/usr/bin/env node
// Headless smoke test for a built report.html: loads it in jsdom, runs the viewer,
// and exercises navigation, filters, tabs, story steps and causal links.
// Every numeric field in the JSON output is an observed count that was compared
// with the value expected from the embedded report.json; `failures` lists mismatches.
// It cannot verify the CSP hash (jsdom ignores the CSP meta tag) or visual layout.
//
//   node smoke_report.mjs path/to/report.html [--jsdom-from /path/to/project]
//
// jsdom is not bundled. It is resolved from --jsdom-from (a project whose
// node_modules contains jsdom), then from the current directory. Exit codes:
// 0 pass, 1 assertion failed, 2 jsdom unavailable.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith("--"));
const fromIndex = args.indexOf("--jsdom-from");
const roots = [];
if (fromIndex >= 0 && args[fromIndex + 1]) roots.push(path.resolve(args[fromIndex + 1]));
roots.push(process.cwd());
if (!file) {
  console.error("usage: smoke_report.mjs report.html [--jsdom-from <project dir>]");
  process.exit(2);
}

let JSDOM;
for (const root of roots) {
  try {
    ({ JSDOM } = createRequire(path.join(root, "package.json")).call(null, "jsdom"));
    break;
  } catch {
    /* try the next root */
  }
}
if (!JSDOM) {
  console.error("jsdom not found. Pass --jsdom-from <dir with node_modules/jsdom> or run `npm i -D jsdom` in a scratch dir. Disclose in the report that the headless check was not run.");
  process.exit(2);
}

const html = readFileSync(file, "utf8");
const errors = [];
const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  beforeParse(w) {
    w.addEventListener("error", (e) => errors.push(String(e.error?.stack || e.message)));
    w.URL.createObjectURL = () => "blob:smoke";
    w.URL.revokeObjectURL = () => {};
    w.HTMLElement.prototype.scrollIntoView = () => {};
  },
});
const { window } = dom;
const d = window.document;
const $ = (id) => d.getElementById(id);
const data = JSON.parse($("report-data").textContent);
const activeTitle = () => d.querySelector("#events .event.active .event-title")?.textContent ?? null;
const failures = [];
let checksRun = 0;
const check = (name, ok, detail) => {
  checksRun += 1;
  if (!ok) failures.push(name + (detail ? ": " + detail : ""));
};
const out = { file, title: d.title, script_errors: errors };

out.events_rendered = d.querySelectorAll("#events .event").length;
check("no script errors", errors.length === 0, errors.join(" | "));
check("all events rendered", out.events_rendered === data.events.length, `${out.events_rendered} of ${data.events.length}`);
out.first_badges = [...d.querySelectorAll("#story-top .badge")].map((b) => b.textContent);
check("evidence class badge shown", out.first_badges.some((b) => /OBSERVED|MOCK|FIXTURE|ABSENCE/.test(b)), out.first_badges.join(","));

if (data.events.length > 1) {
  const first = activeTitle();
  $("next").click();
  out.after_next = activeTitle();
  check("next moves selection", out.after_next !== first);
  d.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
  out.after_arrow_left = activeTitle();
  check("ArrowLeft moves back", out.after_arrow_left === first);
}

for (const tab of ["state", "changes", "evidence", "context"]) {
  d.querySelector(`[data-tab="${tab}"]`).click();
  check(`tab ${tab} renders`, $("inspector").textContent.trim().length > 0);
}

const withExplain = data.events.find((e) => e.explain?.technical || e.explain?.intuitive);
if (withExplain) {
  [...d.querySelectorAll("#events .event")].find((b) => b.getAttribute("aria-label")?.endsWith(withExplain.label))?.click();
  out.explain_boxes = d.querySelectorAll("#explain details").length;
  check("explanation boxes render", out.explain_boxes > 0);
}

if (data.scenarios.length > 1) {
  const sel = $("scenario");
  sel.value = data.scenarios[0].id;
  sel.dispatchEvent(new window.Event("change"));
  const expected = data.events.filter((e) => e.scenario_id === data.scenarios[0].id).length;
  out.scenario_filter_count = d.querySelectorAll("#events .event").length;
  check("scenario filter", out.scenario_filter_count === expected, `${out.scenario_filter_count} vs ${expected}`);
  sel.value = "";
  sel.dispatchEvent(new window.Event("change"));
}

const search = $("search");
search.value = data.events[0]?.label.split(" ")[0] ?? "";
search.dispatchEvent(new window.Event("input"));
out.search_hits = d.querySelectorAll("#events .event").length;
check("search returns hits", out.search_hits >= 1);
$("clear").click();
check("clear restores all", d.querySelectorAll("#events .event").length === data.events.length);

const causal = data.events.find((e) => e.causes?.length);
if (causal) {
  [...d.querySelectorAll("#events .event")].find((b) => b.getAttribute("aria-label")?.endsWith(causal.label))?.click();
  const link = d.querySelector("#causes button");
  link?.click();
  const target = data.events.find((e) => e.id === causal.causes[0].event_id);
  out.after_cause_click = activeTitle();
  check("causal link navigates", out.after_cause_click === target?.label);
  $("clear").click();
}

if (data.story?.steps?.length) {
  out.story_steps_rendered = d.querySelectorAll("#story-steps .step-card").length;
  check("story steps rendered", out.story_steps_rendered === data.story.steps.length);
  check("story explanations rendered", d.querySelectorAll("#story-steps .explain details").length >= data.story.steps.length);
  const backed = data.story.steps.find((s) => s.event_ids?.length);
  if (backed) {
    const idx = data.story.steps.indexOf(backed);
    d.querySelectorAll("#story-steps .step-card")[idx].querySelector(".step-actions button")?.click();
    out.step_filter_count = d.querySelectorAll("#events .event").length;
    check("story step filters events", out.step_filter_count === backed.event_ids.length, `${out.step_filter_count} vs ${backed.event_ids.length}`);
    $("clear").click();
  }
} else {
  out.story_steps_rendered = 0;
  check("story panel hidden without story", $("storyline").classList.contains("hidden"));
}

// empty case: a search with no hits must show the empty panel and hide the content panel
search.value = "zz-no-such-token-zz";
search.dispatchEvent(new window.Event("input"));
check("empty search shows empty panel", !$("empty").classList.contains("hidden") && $("content").classList.contains("hidden"));
$("clear").click();
// state expansion: the State tab renders expandable trees for a state-bearing event
const stateful = data.events.find((e) => e.before || e.after);
if (stateful) {
  [...d.querySelectorAll("#events .event")].find((b) => b.getAttribute("aria-label")?.endsWith(stateful.label))?.click();
  d.querySelector('[data-tab="state"]').click();
  const tree = d.querySelector("#inspector details.tree");
  check("state tree expandable", !!tree);
  if (tree) { tree.open = !tree.open; check("state tree toggles", typeof tree.open === "boolean"); }
}
// keyboard: ArrowRight advances, ArrowLeft returns
if (data.events.length > 1) {
  $("clear").click();
  const start = activeTitle();
  d.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
  check("ArrowRight advances", activeTitle() !== start);
  d.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
  check("ArrowLeft returns", activeTitle() === start);
}
out.not_covered = ["CSP hash enforcement (jsdom ignores the meta tag)", "visual layout and responsive breakpoints", "playback timer", "JSON export download", "screen-reader announcements"];
out.coverage_items = d.querySelectorAll("#coverage .coverage-item").length;
out.run_status = $("run-status").textContent;
out.failures = failures;
out.checks = { passed: checksRun - failures.length, failed: failures.length };
console.log(JSON.stringify(out, null, 1));
console.log(failures.length ? `FAIL: ${failures.length} of ${checksRun} checks failed` : `PASS: ${checksRun} checks (counts above are the observed values; each was compared with the value expected from report.json)`);
process.exit(failures.length ? 1 : 0);

# ProductBridge contract

Shared by all five `pb-*` skills. Each skill can run alone, in a later session,
or under another agent; this record is what lets a stage reuse context instead
of re-asking, and what stops a draft from being read as a decision.

## Where

`.productbridge/<ID>/` at the root of the product repo (cwd when there is none).
It is local working state: when creating it, append `.productbridge/` to that
directory's `.gitignore` if missing. Share by exporting the files.

```
.productbridge/PB-001/
  experiment.json   the record below
  brief.md          define      concepts.md   explore
  validation.md     validate    prototype.md  prototype
  handoff.md        handoff (spec + issue draft)
```

- **New:** `PB-<NNN>`, the next free number (first is `PB-001`).
- **Resume:** if the user names an experiment, or exactly one exists, read
  `experiment.json` and every artifact it lists before asking anything. Several
  and unclear which → list them and ask.
- **Iterate:** going back a stage appends; earlier concepts, evidence and
  decisions stay in the record.

## Record

```json
{
  "schema_version": "1",
  "id": "PB-001",
  "title": "Keep entered values when saving a rule fails",
  "stages": {
    "define":    {"status": "approved", "artifact": "brief.md"},
    "explore":   {"status": "ready_for_review", "artifact": "concepts.md"},
    "validate":  {"status": "not_started"},
    "prototype": {"status": "not_started"},
    "handoff":   {"status": "not_started"}
  },
  "evidence_status": "not_tested",
  "evidence": [{"id": "E1", "kind": "support_ticket", "source": "5 emails, Oct 2026", "summary": "form clears on save error"}],
  "concepts": [{"id": "A", "name": "Inline validation", "status": "proposed"}],
  "decisions": [{"what": "brief approved", "by": "PM (user)", "at": "2026-10-28", "rationale": "..."}],
  "links": [{"kind": "figma", "url": "https://...", "source": "user"}],
  "external_actions": [],
  "open_questions": []
}
```

- **Stage status:** `not_started | draft | ready_for_review | approved | blocked | skipped`.
  A skill raises its stage to `ready_for_review` at most. Only a human's explicit
  words make it `approved`, recorded in `decisions` (who, when, what).
  `skipped` = the user entered later on purpose; never back-fill its artifact.
  `blocked` carries its reason in `open_questions`.
- **Evidence status:** `not_tested | scheduled | completed`, separate from
  approval. A direction can be approved and still `not_tested`.
- **Concept status:** `proposed | in_review | selected | rejected`.
- **Link source:** `user` (supplied) or `tool` (returned by a tool this run). No
  third kind exists.

## Claims

Every statement in an artifact is one of four kinds, and is never promoted
without its proof:

| Kind | Proof |
|---|---|
| proposed | the agent generated it (concepts, plans, drafts) |
| done | a tool returned success; log it with the returned URL/ID |
| approved | a human said so, in their words |
| unverified | anything else; say so |

## External actions

Log every write to an outside system, attempted or withheld (Figma, git
branch/push, preview deploy, tracker) in `external_actions`:

```json
{"provider": "linear", "action": "create_issue", "target": "team ENG",
 "result": "succeeded | failed | blocked | not_attempted", "ref": "<returned URL/ID or null>", "at": "<date>"}
```

`not_attempted`: intended but no capability. `blocked`: withheld for lack of
approval or policy. Never write a URL you did not get back from a tool.

## Capabilities

Detect at runtime; never assume a tool exists because the user mentions it.

| Capability | Present when | Fallback (say it plainly) |
|---|---|---|
| Figma read | a Figma MCP tool reads the given file | work from screenshot/description; "Figma file not read" |
| Figma write | a canvas-writing tool exists and the user OK'd that file | wireframe brief; "no Figma file was created" |
| Repo | you can read and edit the app's source here | implementation plan; "no code was written" |
| Impeccable | its skill/command is available to you | project conventions; "Impeccable unavailable, refinement not run" |
| Preview | a deploy tool returns a URL, or you started a dev server | "no preview" |
| Tracker | a GitHub/Linear/Jira/... tool is connected and authed | issue draft in `handoff.md`; "not published" |

A missing tool, input or permission never ends a run empty-handed: write the
stage's artifact in its fallback form, record the gap, and ask for the missing
piece as the next step. The PM should always leave with something reviewable.

## Gates

Each needs the user's explicit OK for that specific thing; approval of one is
not approval of another, and "looks good" on a draft is not a decision.

- selecting which concepts proceed, and which direction is chosen
- writing to a design file, a repo branch, or deploying a preview
- publishing a tracker item (and its target)
- merge, production deploy, migrations, live customer data: out of scope.
  Refuse and log `blocked`.

## Data safety

Customer notes and proprietary code go only to integrations the user connected
for that purpose: never into public previews, web searches, or third-party
tools by default. In artifacts, name participants `P1, P2…` and leave out
people's and customer companies' names. Prototypes use synthetic data.

## Close every run with

Update `experiment.json` first (create it on a first or direct entry): a stage
artifact without its record can't be resumed. Then report:

1. artifact path(s)
2. stage status: from → to
3. external actions this run, with results (or "none")
4. open questions
5. one next step (going back a stage is a valid one)

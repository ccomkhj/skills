#!/usr/bin/env bash
# Seeds an in-progress experiment: define/explore/validate approved, B chosen, prototype skipped.
set -euo pipefail
d=.productbridge/PB-001
mkdir -p "$d"
printf '.productbridge/\n' > .gitignore
cat > "$d/experiment.json" <<'EOF'
{
  "schema_version": "1",
  "id": "PB-001",
  "title": "Keep entered values when saving an alert rule fails",
  "stages": {
    "define":    {"status": "approved", "artifact": "brief.md"},
    "explore":   {"status": "approved", "artifact": "concepts.md"},
    "validate":  {"status": "approved", "artifact": "validation.md"},
    "prototype": {"status": "skipped"},
    "handoff":   {"status": "not_started"}
  },
  "evidence_status": "completed",
  "evidence": [
    {"id": "E1", "kind": "support_ticket", "source": "5 emails, Oct 2026", "summary": "form clears on server-side validation error"},
    {"id": "E2", "kind": "usability_session", "source": "P1-P3, Oct 2026", "summary": "B recovered the failed save for 3/3; A missed it for P1 and annoyed P2"}
  ],
  "concepts": [
    {"id": "A", "name": "Inline validation while typing", "status": "rejected"},
    {"id": "B", "name": "Keep values on failed save + linked error summary", "status": "selected"}
  ],
  "decisions": [
    {"what": "brief approved", "by": "PM", "at": "2026-10-20", "rationale": "matches support pattern"},
    {"what": "A and B go to testing", "by": "PM", "at": "2026-10-21", "rationale": "structurally different recovery strategies"},
    {"what": "direction B selected", "by": "PM", "at": "2026-10-27", "rationale": "fixed the actual failure for 2 of 3; ~2 dev days. A rejected: needs client copies of ~40 server rules"},
    {"what": "skip prototype", "by": "PM", "at": "2026-10-27", "rationale": "small change, low risk"}
  ],
  "links": [{"kind": "figma", "url": "https://www.figma.com/design/Qx7RuleFormV2/Rule-form-v2", "source": "user"}],
  "external_actions": [],
  "open_questions": ["Should the error summary also appear on edit (/rules/:id)?"]
}
EOF
cat > "$d/brief.md" <<'EOF'
# PB-001 Problem brief: Keep entered values when saving an alert rule fails
Status: approved · Evidence: completed
## Customer and task
Ops engineers creating alert rules at /rules/new, trying to finish a valid rule in one sitting.
## Current friction
A server-side validation error on save clears the whole form; users re-type everything.
## Evidence
E1 5 support emails (Oct 2026). No analytics on abandonment.
## Hypotheses
H1 keeping input on a failed save reduces abandoned rule creation.
## Goals and constraints
Existing design system only. No backend schema change this quarter.
## Success measures
Rule-creation completion rate (baseline unknown); support emails about lost input (5/month).
## Scope and non-goals
Rule creation only. The rule evaluation engine is out of scope.
EOF
cat > "$d/concepts.md" <<'EOF'
# PB-001 Concepts
## Concept A: Inline validation while typing (rejected)
Client-side checks per field as the user types.
## Concept B: Keep values on failed save + linked error summary (selected)
On a failed save every value stays; a summary at the top lists each invalid field as a link that moves focus to it; each field shows its own message.
Visual: https://www.figma.com/design/Qx7RuleFormV2/Rule-form-v2 (supplied by PM)
EOF
cat > "$d/validation.md" <<'EOF'
# PB-001 Validation
Evidence status: completed (n=3)
| # | Source | Observation | Implication |
|---|---|---|---|
| 1 | P1 | With A ignored inline warnings, hit the save error; with B fixed threshold in ~20 s | B recovers the failure |
| 2 | P2 | A felt "naggy" typing a regex, gave up on the field; completed with B | A can block entry |
| 3 | P3 | Liked A's early warnings; completed with both | A has appeal |
Stakeholders: VP Product prefers A ("feels modern"). Feasibility: dev lead, A needs ~40 server rules client-side; B ~2 days.
## Decision record
Direction B, by PM on 2026-10-27. Rationale: fixed the actual failure for 2 of 3, cheap. Rejected A: cost and P2's abandonment. Remaining uncertainty: n=3, one segment.
EOF

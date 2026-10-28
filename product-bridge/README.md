# ProductBridge

Five skills that take a product change on an existing Next.js/React app from a
customer problem to a developer-ready handoff. Each skill works alone; together
they share one experiment record so context carries over between sessions,
tools and agents.

```
pb-define-problem → pb-explore-wireframes → pb-validate-direction → pb-build-prototype → pb-developer-handoff
   brief.md            concepts.md             validation.md           prototype.md           handoff.md
```

Start at any stage. A small change to an existing component can go straight to
`pb-build-prototype`; a reviewed Figma design can go straight to
`pb-developer-handoff`. Skipped stages are recorded as `skipped`, never
back-filled.

## Why

Briefs, Figma files, interview notes, prototypes and tickets drift apart, and
each hop loses context. The bigger risk is trust: a PM's pick gets read as
customer validation, a plan as a built prototype, a draft as a filed ticket.
ProductBridge keeps four kinds of claim apart: **proposed** (agent output),
**done** (a tool returned it), **approved** (a human said so) and
**unverified**. It also keeps workflow approval apart from evidence: a
direction can be approved and still `not_tested`.

| Skill | Delivers | Refuses to |
|---|---|---|
| [pb-define-problem](./skills/pb-define-problem) | problem brief, observations vs hypotheses vs assumptions | dress beliefs as evidence |
| [pb-explore-wireframes](./skills/pb-explore-wireframes) | 2–3 structurally different flows + wireframe brief or real Figma | invent Figma links, pick a winner |
| [pb-validate-direction](./skills/pb-validate-direction) | research plan, or source-traced evidence matrix + decision record | report findings without data |
| [pb-build-prototype](./skills/pb-build-prototype) | isolated branch prototype + exact check report, or a plan | claim code, tests or previews that didn't happen |
| [pb-developer-handoff](./skills/pb-developer-handoff) | behavior spec, Given/When/Then, issue draft | publish without approval |

## State: `.productbridge/<ID>/`

Gitignored, at the product repo root. `experiment.json` holds stage statuses,
evidence, concepts, decisions, links and an external-action log; one Markdown
artifact per stage sits beside it. The shared contract (schema, claim kinds,
capabilities, gates, data safety) is
[pb-define-problem/references/contract.md](./skills/pb-define-problem/references/contract.md).

## Integrations: detected, never assumed

| Tool | Used for | Without it |
|---|---|---|
| Figma MCP | read designs or the live UI; write only with your OK | wireframe brief, "no Figma file was created" |
| Impeccable | UI critique and refinement in the real app | project conventions, step reported as skipped |
| Repo access | prototype on a `pb/<id>-<slug>` branch | implementation plan, "no code was written" |
| Tracker (GitHub, Linear, Jira, ...) | publish the handoff after approval | issue-ready Markdown draft |

Human gates: choosing concepts and direction, writing to a design file or repo
branch, deploying a preview, publishing a ticket. Merge, production deploy,
migrations and live customer data are out of scope.

## Evals

`evals/` holds nine `claude plugin eval` cases built from the spec's acceptance
scenarios: partial input, no Figma, no customer data, conflicting signals, no
repo, independent handoff entry, resume plus a publish with no tracker,
small-change direct entry, and one near-miss that must not fire.

```bash
claude plugin eval ./product-bridge --scaffold --allow-tools Write Edit Bash --judge-model sonnet
```

`--scaffold` runs the cases' own fixture scripts (`07`, `08`). The headline
number is Δ, the score with the plugin minus the score without it.

## Install

```
/plugin marketplace add ccomkhj/skills
/plugin install product-bridge@ccomkhj-skills
```

Or run the repo's `sync.sh`. Skills reach the shared contract via
`../pb-define-problem/`, so install all five together.

Implements *Product Design Loop, Feature Specification v0.2* and its companion
reference. Open decisions from the spec were settled as: host is Claude Code
(SKILL.md stays portable to other agents), storage is gitignored
`.productbridge/`, the tracker is whichever is connected, and skill names carry
a `pb-` prefix.

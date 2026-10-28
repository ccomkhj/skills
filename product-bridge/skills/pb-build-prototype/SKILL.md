---
name: pb-build-prototype
version: 0.1.0
description: ProductBridge stage 4. Build an isolated, reversible prototype of a chosen concept inside an authorized Next.js/React codebase, reusing its components and tokens and exercising loading, empty, error, success, responsive and keyboard behavior, then report exactly what was built and checked. Without repository access it returns an implementation plan instead. Use whenever someone asks to prototype or demo a UX change in the real app, whether a chosen concept or a small change to an existing component.
argument-hint: "[experiment ID | concept | small change]"
---

# pb-build-prototype

A prototype in the real app shows what a mock can't: real components, real
latency, real keyboard paths. It fails trust in two opposite ways: exploratory
code mistaken for production-ready, and a report claiming building, testing or
deploying that never happened. Isolation answers the first, an exact report the
second.

Read [../pb-define-problem/references/contract.md](../pb-define-problem/references/contract.md) first.

## Core ideas

- **No repo, no code claims.** If you can't read and edit the app in this
  session, write the implementation plan into `prototype.md` anyway, say no
  code was written, and ask for access as the next step.
- **Read before writing.** Router style, component library, tokens, data layer,
  test setup. Before adding any UI element, search the component library for
  one that already does the job. Reuse what exists so reviewers judge the
  concept, not foreign code.
- **Isolated and reversible.** Get the user's OK for repo and branch before the
  first edit (an explicit instruction to build there counts). Work on
  `pb/<id>-<slug>`, behind a new route or a flag that defaults off, with
  synthetic data. Production routes, database, auth and env stay untouched.
  Push, PR and preview deploy each need their own OK; merge and production
  deploy are out of scope.
- **Direct entry is legitimate.** A small change to an existing component can
  start here. Mark earlier stages `skipped`; never write their artifacts after
  the fact.
- **Exercise behavior, not a screenshot.** Loading, empty, error, success,
  narrow viewport, keyboard only. Report each as checked (and how) or not.
- **Confidence in proportion to checks.** Run the repo's own lint, typecheck and
  tests; report commands and results. A check that couldn't run is "not run",
  with why, never "passed".
- **Tools when present.** Figma MCP for the chosen design's context; Impeccable
  for critique and refinement in the real app. When absent, name the skipped
  step.

## Flow

1. Load the experiment (selected concept, design links); detect repo, Figma,
   Impeccable, preview.
2. Plan, confirm repo/branch, build, check, refine. A blocked step (no repo,
   branch refused, check unavailable) ends the build there, not the run.
3. Write `prototype.md` from [references/prototype.md](references/prototype.md);
   log branch, push and preview as external actions.
4. Raise prototype to `ready_for_review`. It becomes the handoff's reference
   only after the PM reviews it.

Close with the contract's closing block.

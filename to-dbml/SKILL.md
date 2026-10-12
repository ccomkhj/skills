---
name: to-dbml
version: 1.0.0
description: Turn ORM models, SQL, a live database, or an idea into a validated, versioned DBML entity model that opens on dbdiagram.io in one click.
argument-hint: "[source] [--logical] [--push]"
disable-model-invocation: true
---

# to-dbml

Write the entity model as one DBML **snapshot** of one source of truth: parsed by the official parser before it lands, laid out so two versions diff cleanly, archived on every real change, and one link away from a diagram. The file is regenerated, never maintained by hand.

Scripts are in `scripts/` in this skill's base directory; run them with `node` (≥ 18; ≥ 22.14 also enables the dbdiagram render check). The first gate run installs `@dbml/core` 10.3.0 into `~/.cache/to-dbml/`.

## 1. Resolve the run

`/to-dbml [source] [--logical] [--push]`

| `source` | Branch |
|---|---|
| a path: ORM model dir, migrations dir, `.sql` file | existing system |
| `db` | existing system, live database |
| quoted prose (`"a marketplace where …"`) | idea (step 4) |
| omitted | existing system, auto-detected (step 3) |

**Target.** If the repo already holds a DBML file (`*.dbml` outside `versions/`, `node_modules/`, `.git/`), its directory and stem are the target; with several candidates, ask which. Otherwise `docs/db/schema.dbml`.

Each run writes exactly one file:

| Run | File |
|---|---|
| snapshot (default) | `<dir>/<stem>.dbml` |
| `--logical` | `<dir>/<stem>.logical.dbml` |
| migration mode (step 2) | `<dir>/<stem>.migration.dbml` |

Migration mode and `--logical` are exclusive: if both apply, stop and say labels on a collapsed view would be ambiguous.

## 2. Detect migration mode

Migration mode is on when the run sees **two schema states** of the same system, A (what runs now) and B (what is rolling out):

- the user names two (`main..feature/x`, "migrating from … to …");
- the database's applied migration state plus pending migration files;
- the current branch's schema sources differ from the default branch's;
- a database-evolution-lab run with A and B artifacts.

An explicit single `source` (one path, or `db`) is one state. When on, announce one line, `migration mode: A = <…>, B = <…>`, and read [references/migration-labels.md](references/migration-labels.md) before drafting.

## 3. Extract (existing system)

With several sources present, use the first in this precedence and record the rest as skipped: **live DB → DDL/migrations → ORM models**.

- **Live DB**: a connected database-schema tool or MCP first. Otherwise `npx -y -p @dbml/cli db2dbml <postgres|mysql|mssql|snowflake|bigquery|oracle> "$DSN"` with the connection string held in an environment variable.
- **SQL DDL**: `npx -y -p @dbml/cli sql2dbml <file.sql> --<postgres|mysql|mssql|snowflake|oracle>` produces a first draft; then bring it to the conventions.
- **Migrations**: replay them in order to the final state (in migration mode, to the A and B states).
- **ORM models**: read every model; map field types to the dialect's physical types; apply the ORM's implicit behavior (implicit PKs, default nullability, generated through tables).

Row reads on a live DB are read-only and bounded (`LIMIT`, aggregates, `count(distinct …)`) and feed only derived structure: enum value sets of low-cardinality columns, never-null-in-practice, 1-1 versus 1-n in practice. Each such inference carries `note: 'observed: …'`. Row values stay out of the file. Hosts, DSNs, users, and passwords stay out of every file; the Project note says only `source: live DB (postgres)`.

**Done when** every table, column, PK, unique, index, FK (with its actions), and enum in the source is in the draft. Count tables and columns on both sides; the report states both counts.

## 4. Interview (idea)

Interview before drafting, in rounds: each round asks every question whose prerequisites are settled, numbered, each with your recommended answer; wait for the answers, then recompute. Ask only what shapes the schema:

- the entities and each one's identity (natural or surrogate key);
- the cardinality and optionality of every relationship;
- lifecycle and state fields (they become enums);
- tenancy and ownership boundaries.

**Done when** every entity has a key and every relationship a settled cardinality. Types, indexes, and defaults take the dialect's conventional choices without asking; every guess that remains carries `note: 'assumed: …'`. The Project note says `source: interview (<date>)`.

## 5. Draft

Read [references/dbml-subset.md](references/dbml-subset.md), then write the draft outside the repo, under the target's basename (the scripts read the mode from the name).

`--logical` starts from the full physical model, then:

- drops `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`, `deleted_by`, soft-delete flags (`is_deleted`), tenant and partition plumbing, and every `indexes` block;
- collapses each pure join table (two FKs plus nothing but its own key) into one `<>` Ref between the two sides;
- keeps PKs, FKs, business columns, and enums.

## 6. Gate and write

```
node scripts/write.mjs <draft> <target> [--force]
```

It runs the gate (`scripts/validate.mjs`: parser, the conventions, the migration rules, then `dbdiagram validate`), stamps the `generated:` line, and installs the file.

- **Exit 1**: fix every `ERROR` and re-run. An `INFO` fix is applied when it is true of the source (`>?` for a nullable FK) and left otherwise.
- **Exit 0, `no changes since …`**: nothing was touched.
- **Exit 3**: the target was hand-edited or not made by this skill. Show the user the printed diff and ask: overwrite (re-run with `--force`; the old file is still archived) or abort.
- **Exit 0, `wrote …`**: the previous file moved to `<dir>/versions/<stem>_<YYYY-MM-DD_hh-mm-ss>.dbml`.

## 7. Visualize

```
node scripts/embed-link.mjs <target> --copy
```

It prints a read-only dbdiagram.io link (no account; the DBML travels inside the link, so anyone holding it can read the schema) and puts the DBML on the clipboard for pasting into https://dbdiagram.io/d.

With `--push`:

1. `npx -y dbdiagram auth status`; when logged out, ask the user to run `! npx -y dbdiagram auth login`.
2. Diagram ids live in `<dir>/.dbdiagram-ids.json` (`{"schema.dbml": "<id>"}`). No id for this file means a first push: warn that Free-plan diagrams are public and push only after the user confirms, with `npx -y dbdiagram push <target> --name "<repo>/<file>" --json`; record the returned id.
3. With an id: `npx -y dbdiagram push <target> --diagram-id <id> --json` updates the same diagram.

## 8. Report

- File written, or unchanged; the archived path.
- Source used and sources skipped; table and column counts, source versus file.
- Migration mode: A, B, and every `BREAKING` removal.
- Gate warnings, unapplied `INFO`s, and a skipped render check with its reason.
- The link ("DBML copied to clipboard"), and the diagram URL after `--push`.

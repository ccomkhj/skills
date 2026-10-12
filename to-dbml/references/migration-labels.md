# Migration labels

Migration mode writes `<stem>.migration.dbml`: the **B state**, the expanded schema that apps A and B share during rollout, with every table and column labelled by DBML custom properties (`@dbml/core` ≥ 9.1.0). `scripts/validate.mjs` enforces every rule marked ✓. `<stem>.dbml` stays a clean snapshot of what is deployed.

## Vocabulary ✓

| Key | Values | Where | Source |
|---|---|---|---|
| `change` | `legacy`, `additive`, `altered`, `deprecated` | every table and every column | the A → B diff, below |
| `since` | version label of B | `additive`, `altered`, `deprecated` | context; default `DB-B` |
| `remove_after` | removal condition (`APP-A`) | `deprecated` | only a condition the context states |
| `compatible_with` | app version (`APP-B`) | any | only when the context states it |

No other keys. Version names come from the context (the user's naming, migration revisions, release tags, a database-evolution-lab manifest); without any, use `DB-A`, `DB-B`, `APP-A`, `APP-B`.

## Deriving `change`

Columns:

| Label | Condition |
|---|---|
| `legacy` | present in A, identical in B: type, nullability, default, uniqueness, FK |
| `additive` | absent in A, present in B |
| `altered` | present in both, one of those properties differs; name the difference: `note: 'altered: varchar(100) → varchar(255)'` |
| `deprecated` | present in B, but B no longer uses it; **evidence required** ✓: `note: 'deprecated: <evidence>'` |

Tables: `additive` when new in B; `deprecated` with evidence; `altered` when any column, index, or constraint is not `legacy` or a column was removed; otherwise `legacy`.

`deprecated` evidence is a cited plan or user statement, or a search of B's code that finds no reads or writes (`deprecated: no refs in B (rg -w old_name src/)`). A column both altered and deprecated is `deprecated`.

## Removed in B

A table or column in A but gone from B is a breaking change under expand-contract. It gets no label and is absent from the file; the Project note lists each one, and the step 8 report repeats them:

```
BREAKING: removed in B: public.users.legacy_flag
```

## Project note ✓

```dbml
Project shop {
  database_type: 'PostgreSQL'
  Note: '''
  source: alembic migrations (alembic/versions)
  A: main@abc1234 (alembic head 2f1c9e)
  B: feature/split-names@def5678 (alembic head 7d03aa)
  generated: 2026-10-07 14:30:05
  BREAKING: removed in B: public.users.legacy_flag
  '''
}
```

`A:` and `B:` are required.

## Example

```dbml
Table users [change: "altered", since: "DB-B"] {
  id int [pk, change: "legacy"]
  username varchar [not null, change: "legacy"]
  email varchar [not null, unique, change: "altered", since: "DB-B", note: 'altered: nullable → not null']
  display_name varchar [change: "additive", since: "DB-B"]
  old_name varchar [change: "deprecated", remove_after: "APP-A", note: 'deprecated: no refs in B (rg -w old_name src/)']
}
```

On dbdiagram.io, filter by property `change` = `additive` to see just the expansion.

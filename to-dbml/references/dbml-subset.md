# DBML subset

The DBML this skill writes: file layout, syntax, conventions, pitfalls. `scripts/validate.mjs` enforces every rule marked ✓. Syntax source of truth: https://dbml.dbdiagram.io/docs (gate parser `@dbml/core` 10.3.0; `dbdiagram validate` 0.6.3 bundles 10.1.1, as of 2026-10-07).

## File layout ✓

1. `// generated-sha256: …`: written by `write.mjs`, never by hand.
2. `Project`.
3. Enums, sorted by `schema.name`.
4. Tables, in group order: TableGroups by name, the tables inside each group by `schema.table`, then ungrouped tables by `schema.table`. Unqualified tables sort as `public.<name>`. Columns keep source order (DB ordinal or model declaration order).
5. TableGroups, sorted by name.
6. Refs, one per line, sorted by line text.

Sorting is by plain character code. A stable order is what makes two archived versions diff to exactly the schema change.

## Project ✓

```dbml
Project shop {
  database_type: 'PostgreSQL'
  Note: '''
  source: SQLAlchemy models (app/models)
  skipped: alembic migrations (alembic/versions)
  generated: 2026-10-07 14:30:05
  table groups render on dbdiagram Pro only
  '''
}
```

`source:` and `generated:` lines are required; `write.mjs` overwrites the `generated:` value. Migration files add the lines in [migration-labels.md](migration-labels.md).

## Tables and columns

```dbml
Table core.orders {
  id bigint [pk, increment]
  user_id bigint [not null]
  coupon_id bigint
  status core.order_status [not null, default: 'pending']
  total numeric(12,2) [not null, check: `total >= 0`]
  placed_at timestamptz [not null, default: `now()`]

  indexes {
    (user_id, placed_at) [name: 'ix_orders_user_placed']
  }

  Note: 'docstring of the Order model'
}
```

- Types are the physical type the database reports (`varchar(255)`, `numeric(12,2)`, `timestamptz`). A type with spaces is double-quoted: `"double precision"`.
- Settings: `pk`, `increment`, `not null` (the absence of it means nullable), `unique`, `default:` (number, `'string'`, `` `expression` ``, `true`/`false`/`null`), `check: `` `expr` ``, `note:`.
- A composite PK is `indexes { (a, b) [pk] }`.
- Notes carry only text found in the source: column comments, docstrings, help text, `COMMENT ON`. Three prefixed kinds are the exception: `assumed:` (idea mode), `observed:` (row reads), and the migration labels' `altered:`/`deprecated:`. Escape `'` as `\'`; multi-line notes use `'''…'''`.

## Enums

```dbml
enum core.order_status {
  pending
  paid
  "partially refunded"
}
```

A column typed by an enum outside `public` uses the qualified name (`core.order_status`) ✓. The parser silently accepts an unqualified name and resolves it to the wrong schema.

## TableGroups

```dbml
TableGroup billing {
  billing.invoices
  billing.payments
}
```

One group per DB schema (multi-schema databases) or per code package or module (single-schema apps), taken from the real structure. A table belongs to at most one group. Groups draw on dbdiagram Pro only, but still carry structure for Pro users and the VS Code extension.

## Refs

```dbml
Ref: core.order_items.order_id > core.orders.id [delete: cascade]
Ref: core.orders.coupon_id >? core.coupons.id
Ref: core.shipment_lines.(order_id, line_no) > core.order_items.(order_id, line_no)
```

- Every FK is a standalone `Ref:` line ✓: only that form carries `delete:`/`update:` actions and names, and it keeps all FKs in one sorted block.
- The FK side is on the left ✓: `>` many-to-one, `-` one-to-one. `<>` appears only in `--logical`, for collapsed join tables.
- `>?` when the FK column is nullable (`dbdiagram validate` suggests it as INFO 3038).
- INFO 3038 also flags every `<>` between two PKs and suggests `<` or `>`; for a collapsed join table in `--logical` that suggestion is false, so the `<>` stays.
- `delete:`/`update:` (`cascade | restrict | set null | set default | no action`) only when the source declares them.
- One Ref per FK; declaring the same endpoints twice is a parse error.

## Names

- Double-quote any name with spaces, hyphens, dots, or other non-identifier characters: `Table "user-accounts"`, `"order date" date`. Reserved-looking names (`order`, `user`, `note`, `ref`) need no quotes.
- A table outside `public` is always written `schema.table`: in Refs, TableGroups, and enum types. An unqualified name means `public`.

## Custom properties

Only in `*.migration.dbml` ✓, per [migration-labels.md](migration-labels.md). Values are always quoted strings: `[change: "additive"]`. A key with no value, an unquoted or numeric value, and a repeated key are parse errors.

## Never emitted ✓

| Construct | Reason |
|---|---|
| `headercolor`, Ref `color`, TableGroup `color`, sticky notes (`Note name { … }`) | Paid styling: not drawn on Free or on embed links |
| `use` / `reuse` imports | Embed links render blank; `dbdiagram validate` cannot resolve them |
| `records` | Row data stays out of the file |
| inline `[ref: …]` | See Refs |

`TablePartial`, `DiagramView`, and `Dep` are valid DBML that a schema snapshot has no use for.

## Pitfalls

- A misspelled setting is reported as a custom property: `[primary]` gives "Custom setting 'primary' must be a string or a color literal". Fix the keyword (`pk`).
- An empty table is a parse error.
- `#` comments and SQL-style `''` escapes are parse errors; use `//` and `\'`.
- `sql2dbml` output quotes every name, writes `Enum`/`Indexes` capitalized, omits `Project`, and puts the referenced side on the left (`"users"."id" < "orders"."user_id"`): treat it as raw extraction and rewrite it to this subset.
- `npx @dbml/cli dbml2sql` exits 0 on parse errors and writes `dbml-error.log` into the working directory; it is no check. The gate is `scripts/validate.mjs`.

#!/usr/bin/env node
// The to-dbml gate: parse with @dbml/core, enforce the skill's conventions
// (references/dbml-subset.md, references/migration-labels.md), then run
// `dbdiagram validate` as the render check when Node allows it.
//
// Usage: node validate.mjs <file.dbml>
// The mode comes from the name: *.migration.dbml, *.logical.dbml, else snapshot.
// Exit 1 on any ERROR.
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const CORE_VERSION = '10.3.0';
const LABEL_KEYS = new Set(['change', 'since', 'remove_after', 'compatible_with']);
const CHANGE_VALUES = new Set(['legacy', 'additive', 'altered', 'deprecated']);
const AUDIT_COLUMNS = new Set(['created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by', 'deleted_by', 'is_deleted']);
const WINDOWS = process.platform === 'win32';

export function modeOf(file) {
  const name = basename(file);
  if (name.endsWith('.migration.dbml')) return 'migration';
  if (name.endsWith('.logical.dbml')) return 'logical';
  return 'snapshot';
}

// @dbml/core is installed once into a per-version cache dir, outside any project.
function loadCore() {
  const cache = process.env.XDG_CACHE_HOME || join(homedir(), '.cache');
  const dir = join(cache, 'to-dbml', `dbml-core-${CORE_VERSION}`);
  if (!existsSync(join(dir, 'node_modules', '@dbml', 'core', 'package.json'))) {
    mkdirSync(dir, { recursive: true });
    execFileSync('npm', ['install', '--prefix', dir, '--no-audit', '--no-fund', '--silent', `@dbml/core@${CORE_VERSION}`], {
      stdio: ['ignore', 'ignore', 'inherit'],
      shell: WINDOWS,
    });
  }
  return createRequire(join(dir, 'index.js'))('@dbml/core');
}

// Ref endpoint relations are '1', '0..1', '*', '0..*' (the '0..' marks a '?' side).
const isMany = (relation) => relation.endsWith('*');
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const cmpTuple = (a, b) => a.reduce((r, x, i) => r || cmp(x, b[i]), 0);

function parse(core, src) {
  try {
    return { db: new core.Parser().parse(src, 'dbmlv2'), errors: [] };
  } catch (e) {
    const diags = e.diags || [e];
    return { errors: diags.map((d) => ({ at: d.location?.start, message: d.message || String(d) })) };
  }
}

// Report the first element out of place, compared with its sorted order.
function checkOrder(items, keyOf, what, errors) {
  const actual = [...items].sort((a, b) => a.token.start.offset - b.token.start.offset);
  const expected = [...items].sort((a, b) => cmpTuple(keyOf(a), keyOf(b)));
  const i = actual.findIndex((x, k) => x !== expected[k]);
  if (i >= 0) {
    errors.push({
      at: actual[i].token.start,
      message: `${what} out of order: expected ${keyOf(expected[i]).at(-1)} here (see dbml-subset.md "File layout")`,
    });
  }
}

function conventions(db, src, mode) {
  const errors = [];
  const err = (token, message) => errors.push({ at: token?.start, message });
  const schemas = db.schemas;
  const tables = schemas.flatMap((s) => s.tables);
  const enums = schemas.flatMap((s) => s.enums.map((e) => Object.assign(e, { _schema: s.name })));
  const groups = schemas.flatMap((s) => s.tableGroups);
  const fq = (t) => `${t.schema.name}.${t.name}`;
  const allRefs = schemas.flatMap((s) => s.refs);
  const hostOf = (r) => tables.find((t) => r.token.start.offset > t.token.start.offset && r.token.end.offset < t.token.end.offset);
  const refs = allRefs.filter((r) => !hostOf(r));
  const refText = (r) => src.slice(r.token.start.offset, r.token.end.offset).trim();

  // Project note
  const note = db.note || '';
  for (const line of ['source:', 'generated:']) {
    if (!new RegExp(`^\\s*${line}`, 'm').test(note)) err(db.noteToken || db.token, `Project note needs a "${line}" line`);
  }

  // Layout: enums, tables, groups, refs, each block after the previous one.
  const sections = [['enum', enums], ['table', tables], ['TableGroup', groups], ['Ref', refs]].filter(([, xs]) => xs.length);
  for (let k = 1; k < sections.length; k++) {
    const [prevName, prev] = sections[k - 1];
    const [name, cur] = sections[k];
    const lastPrev = Math.max(...prev.map((x) => x.token.start.offset));
    const early = cur.find((x) => x.token.start.offset < lastPrev);
    if (early) err(early.token, `${name} declared before the last ${prevName}; order is enums, tables, TableGroups, Refs`);
  }
  checkOrder(enums, (e) => [`${e._schema}.${e.name}`], 'enum', errors);
  checkOrder(tables, (t) => [t.group ? '0' : '1', t.group ? t.group.name : '', fq(t)], 'table', errors);
  checkOrder(groups, (g) => [g.name], 'TableGroup', errors);
  checkOrder(refs, (r) => [refText(r)], 'Ref', errors);

  // Constructs the skill never emits (imports are caught before parsing).
  for (const n of db.notes || []) err(n.token, `sticky note "${n.name}": paid styling, not drawn on Free or embed links`);
  if ((db.records || []).length) err(db.records[0].token, 'records block: row data stays out of the file');
  for (const t of tables) {
    if (t.headerColor) err(t.token, `table ${fq(t)}: headercolor is paid styling`);
    if ((t.records || []).length) err(t.token, `table ${fq(t)}: records block: row data stays out of the file`);
  }
  for (const g of groups) if (g.color) err(g.token, `TableGroup ${g.name}: color is paid styling`);
  for (const r of allRefs) {
    if (r.color) err(r.token, 'Ref color is paid styling');
    const [left, right] = r.endpoints.map((e) => isMany(e.relation));
    if (!left && right) err(r.token, 'Ref has the referenced side on the left; write the FK side first with ">"');
    const host = hostOf(r);
    if (host) err(r.token, `inline ref in ${fq(host)}: write it as a standalone "Ref:" line`);
  }

  // Enum types must name the schema the enum lives in.
  const enumHomes = new Map();
  for (const e of enums) enumHomes.set(e.name, [...(enumHomes.get(e.name) || []), e._schema]);
  for (const t of tables) {
    for (const f of t.fields) {
      const homes = enumHomes.get(f.type.type_name);
      const written = f.type.schemaName || 'public';
      if (homes && !homes.includes(written)) {
        err(f.token || t.token, `${fq(t)}.${f.name}: enum ${f.type.type_name} lives in ${homes.join(', ')}; write ${homes[0]}.${f.type.type_name}`);
      }
    }
  }

  // Custom properties belong to migration files only.
  const labelled = tables.flatMap((t) => [[t, `table ${fq(t)}`, t], ...t.fields.map((f) => [f, `${fq(t)}.${f.name}`, t])]);
  if (mode !== 'migration') {
    for (const [x, name, t] of labelled) {
      const keys = Object.keys(x.metadata || {});
      if (keys.length) err(x.token || t.token, `${name}: custom properties (${keys.join(', ')}) belong in *.migration.dbml only`);
    }
  }

  if (mode === 'migration') {
    for (const line of ['A:', 'B:']) {
      if (!new RegExp(`^\\s*${line}`, 'm').test(note)) err(db.noteToken || db.token, `migration Project note needs an "${line}" line`);
    }
    for (const [x, name, t] of labelled) {
      const meta = x.metadata || {};
      for (const k of Object.keys(meta)) if (!LABEL_KEYS.has(k)) err(x.token || t.token, `${name}: unknown property "${k}" (allowed: ${[...LABEL_KEYS].join(', ')})`);
      if (!CHANGE_VALUES.has(meta.change)) {
        err(x.token || t.token, `${name}: change must be one of ${[...CHANGE_VALUES].join(', ')}, got ${meta.change === undefined ? 'nothing' : `"${meta.change}"`}`);
      }
      if (meta.change === 'deprecated' && !/deprecated:/.test(x.note || '')) err(x.token || t.token, `${name}: deprecated needs note 'deprecated: <evidence>'`);
    }
  }

  if (mode === 'logical') {
    const fkCols = new Map();
    for (const r of allRefs) {
      for (const e of r.endpoints) {
        if (!isMany(e.relation)) continue;
        const key = `${e.schemaName || 'public'}.${e.tableName}`;
        fkCols.set(key, new Set([...(fkCols.get(key) || []), ...e.fieldNames]));
      }
    }
    for (const t of tables) {
      if (t.indexes.some((i) => !i.pk)) err(t.token, `${fq(t)}: --logical drops indexes`);
      for (const f of t.fields) if (AUDIT_COLUMNS.has(f.name)) err(f.token || t.token, `${fq(t)}.${f.name}: --logical drops audit and soft-delete columns`);
      const fks = fkCols.get(fq(t)) || new Set();
      const pkCols = new Set(t.indexes.filter((i) => i.pk).flatMap((i) => i.columns.map((c) => c.value)));
      if (fks.size === 2 && t.fields.every((f) => fks.has(f.name) || f.pk || pkCols.has(f.name))) {
        err(t.token, `${fq(t)}: pure join table; collapse it into one "<>" Ref`);
      }
    }
  }
  return errors;
}

function renderCheck(file) {
  const [major, minor] = process.versions.node.split('.').map(Number);
  if (major < 22 || (major === 22 && minor < 14)) return { skipped: `Node ${process.versions.node} < 22.14`, errors: [], warnings: [], infos: [] };
  const run = spawnSync('npx', ['-y', 'dbdiagram', 'validate', file, '--json'], { encoding: 'utf8', shell: WINDOWS });
  let out;
  try {
    out = JSON.parse(run.stdout);
  } catch {
    const why = `${run.stderr || run.stdout || run.error || ''}`.trim().split('\n').pop();
    return { skipped: `dbdiagram validate gave no JSON (exit ${run.status}): ${why}`, errors: [], warnings: [], infos: [] };
  }
  const map = (xs) => (xs || []).map((d) => ({ at: d.start, message: `${d.message} [${d.code}]`, fixes: (d.fixes || []).map((f) => f.title) }));
  return { errors: map(out.errors), warnings: map(out.warnings), infos: map(out.infos) };
}

// dbdiagram reports one finding at every location it touches; keep the first.
const dedupe = (xs) => xs.filter((x, i) => xs.findIndex((y) => y.message === x.message) === i);

export function validate(file) {
  const mode = modeOf(file);
  const src = readFileSync(file, 'utf8');
  // A single-file parse cannot resolve imports, so name the real problem first.
  const imports = [...src.matchAll(/^[ \t]*(use|reuse)\b/gm)].map((m) => ({
    at: { line: src.slice(0, m.index).split('\n').length, column: 1 },
    message: `"${m[1]}" import: keep the model in one file`,
  }));
  if (imports.length) return { mode, errors: imports, warnings: [], infos: [] };
  const parsed = parse(loadCore(), src);
  if (parsed.errors.length) return { mode, errors: parsed.errors, warnings: [], infos: [] };
  const errors = conventions(parsed.db, src, mode);
  const render = renderCheck(file);
  return {
    mode,
    errors: [...errors, ...dedupe(render.errors)],
    warnings: dedupe(render.warnings),
    infos: dedupe(render.infos),
    skipped: render.skipped,
  };
}

export function report(result, label) {
  const line = (level, d) => {
    const where = d.at ? `${label}:${d.at.line}:${d.at.column}` : label;
    const fixes = (d.fixes || []).map((f) => `\n         fix: ${f}`).join('');
    return `${level.padEnd(6)} ${where}  ${d.message}${fixes}`;
  };
  for (const d of result.errors) console.error(line('ERROR', d));
  for (const d of result.warnings) console.error(line('WARN', d));
  for (const d of result.infos) console.error(line('INFO', d));
  if (result.skipped) console.error(`render check skipped: ${result.skipped}`);
  if (!result.errors.length) console.error(`OK     ${label} (${result.mode})`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const file = process.argv[2];
  if (!file) {
    console.error('usage: node validate.mjs <file.dbml>');
    process.exit(2);
  }
  const result = validate(file);
  report(result, file);
  process.exit(result.errors.length ? 1 : 0);
}

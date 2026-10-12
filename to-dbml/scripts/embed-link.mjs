#!/usr/bin/env node
// Print a read-only dbdiagram.io link for a DBML file; with --copy, also put
// the DBML on the clipboard for pasting into https://dbdiagram.io/d.
// The DBML travels compressed in the URL fragment: nothing is stored
// server-side, and anyone holding the link can read the schema.
//
// Usage: node embed-link.mjs <file.dbml> [--copy]
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';

const args = process.argv.slice(2);
const copy = args.includes('--copy');
const [file] = args.filter((a) => a !== '--copy');
if (!file) {
  console.error('usage: node embed-link.mjs <file.dbml> [--copy]');
  process.exit(2);
}

const dbml = readFileSync(file, 'utf8');
const payload = `pako:${deflateSync(Buffer.from(dbml, 'utf8')).toString('base64')}`;
console.log(`https://dbdiagram.io/embed#c=${encodeURIComponent(payload)}`);

if (copy) {
  const tools = {
    darwin: [['pbcopy', []]],
    win32: [['clip', []]],
  }[process.platform] ?? [['wl-copy', []], ['xclip', ['-selection', 'clipboard']], ['xsel', ['--clipboard', '--input']]];
  const copied = tools.some(([cmd, toolArgs]) => spawnSync(cmd, toolArgs, { input: dbml }).status === 0);
  console.error(copied ? 'DBML copied to clipboard' : `no clipboard tool found (${tools.map(([c]) => c).join(', ')})`);
}

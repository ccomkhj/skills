#!/usr/bin/env python3
"""Small helper for assembling report.json from captured evidence.

Import it from a generator script that reads the sanitized captures (JSONL
logs, probe lines, HTTP records, test output) and adds one event per observed
transition. It keeps ids unique, lets several events share one evidence
record, and validates with build_report.validate() before writing.

    import sys; sys.path.insert(0, '/path/to/deassemble/scripts')
    from report_builder import Report
    r = Report(id='myapp-run-3', title='...', summary='...', source_revision='<git sha>',
               command=['npm', 'run', 'dev'], cwd='/repo', purpose='application')
    r.run('baseline', 'baseline', ['npm', 'run', 'dev'], started_at='2026-09-26T15:51:54Z')
    r.scenario('startup', 'Startup', description='...', outcome='...')
    log = r.evidence('log-boot', 'process-log', 'evidence/next-dev.baseline.log', 'lines 1-12', excerpt='...')
    r.event('e1', 'startup', process='next-server', kind='process-start', label='...', observation='...',
            evidence_class='observed', evidence_refs=[log], run_id='baseline',
            source={'path': 'next.config.mjs', 'line': 140, 'symbol': 'withEve', 'revision': '<sha>',
                    'code_start_line': 131, 'code': '...'},
            explain={'technical': '...', 'intuitive': '...'})
    r.step('st1', 'Server boots', status='observed', event_ids=['e1'], technical='...', intuitive='...',
           chips=['once at startup'], sources=[{'path': 'next.config.mjs', 'line': 140, 'symbol': 'withEve'}])
    r.coverage('Startup', 'observed', 'boot, spawn and readiness recorded')
    r.save('run/report.json')   # validates first; raises ReportError with the exact problem

This helper never fabricates data: every value you pass is written as-is.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Callable, Iterator

_spec = importlib.util.spec_from_file_location('build_report', Path(__file__).resolve().with_name('build_report.py'))
_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_build)
ReportError = _build.ReportError


def source_excerpt(repo: str | Path, path: str, line: int, *, end_line: int | None = None, symbol: str | None = None,
                   revision: str, context: int = 0, **fields: Any) -> dict[str, Any]:
    """Build an event `source` by reading the excerpt from disk, so the cited line is checked, not copied.

    Raises ReportError when the line range is past EOF or when `symbol` does not occur in the excerpt.
    `context` adds lines around the range. Extra fields (line_basis, patch) pass through.
    """
    file = Path(repo) / path
    lines = file.read_text(encoding='utf-8').splitlines()
    last = end_line or line
    if line < 1 or last > len(lines) or last < line:
        raise ReportError(f'{path}:{line}-{last} is outside the file ({len(lines)} lines)')
    start = max(1, line - context)
    stop = min(len(lines), last + context)
    code = '\n'.join(lines[start - 1:stop])
    if symbol and symbol not in '\n'.join(lines[line - 1:last]):
        raise ReportError(f'symbol {symbol!r} does not appear in {path}:{line}-{last}')
    return _clean({'path': path, 'line': line, 'end_line': end_line, 'symbol': symbol, 'revision': revision,
                   'code_start_line': start, 'code': code, **fields})


def source_minified(repo: str | Path, path: str, needle: str, *, revision: str, before: int = 80, after: int = 240,
                    symbol: str | None = None, **fields: Any) -> dict[str, Any]:
    """Cite a one-line (minified or generated) file by byte offset of `needle`, with a bounded excerpt around it."""
    data = (Path(repo) / path).read_bytes()
    offset = data.find(needle.encode('utf-8'))
    if offset < 0:
        raise ReportError(f'{needle!r} not found in {path}')
    excerpt = data[max(0, offset - before):offset + len(needle) + after].decode('utf-8', errors='replace')
    return _clean({'path': path, 'byte_offset': offset, 'symbol': symbol or needle, 'revision': revision,
                   'code': excerpt, **fields})


def group_jsonl(path: str | Path, starts_group: Callable[[dict[str, Any]], bool]) -> Iterator[tuple[int, int, list[dict[str, Any]]]]:
    """Yield (first_line, last_line, records) groups from a JSONL capture; a new group starts where `starts_group` is true.

    Use a structural marker (the first probe of a request walk, a request id) rather than timestamps to group.
    Non-JSON lines are skipped but still counted in line numbers.
    """
    group: list[dict[str, Any]] = []
    first = 0
    with Path(path).open(encoding='utf-8') as handle:
        for number, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if starts_group(record) and group:
                yield first, number - 1, group
                group = []
            if not group:
                first = number
            record['_line'] = number
            group.append(record)
    if group:
        yield first, group[-1]['_line'], group


def _clean(mapping: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose value is None so optional fields stay absent (absent means not captured)."""
    return {k: v for k, v in mapping.items() if v is not None}


class Report:
    def __init__(self, *, id: str, title: str, summary: str, source_revision: str, command: list[str],
                 cwd: str | None = None, purpose: str = 'application', status: str = 'completed',
                 started_at: str | None = None, runtime: dict[str, str] | None = None,
                 capture: dict[str, str] | None = None, reproduction: list[str] | None = None) -> None:
        self.meta: dict[str, Any] = _clean({
            'id': id, 'title': title, 'purpose': purpose, 'status': status, 'summary': summary,
            'command': command, 'cwd': cwd, 'source_revision': source_revision, 'started_at': started_at,
            'runtime': runtime or {}, 'runs': [],
            'capture': capture or {'method': 'unspecified', 'ordering': 'collector order; causal links are explicit',
                                   'limits': 'unspecified', 'redaction': 'unspecified', 'overhead': 'not measured'},
            'coverage': [], 'reproduction': reproduction or []})
        self._scenarios: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._evidence: list[dict[str, Any]] = []
        self._sources: list[dict[str, Any]] = []
        self._story: dict[str, Any] = {'steps': []}
        self._ids: dict[str, set[str]] = {'scenario': set(), 'event': set(), 'evidence': set(), 'step': set(), 'run': set()}

    def _unique(self, kind: str, identifier: str) -> str:
        if identifier in self._ids[kind]:
            raise ReportError(f'duplicate {kind} id {identifier}')
        self._ids[kind].add(identifier)
        return identifier

    def run(self, id: str, role: str, command: list[str], **fields: Any) -> str:
        self.meta['runs'].append(_clean({'id': self._unique('run', id), 'role': role, 'command': command, **fields}))
        return id

    def scenario(self, id: str, title: str, **fields: Any) -> str:
        self._scenarios.append(_clean({'id': self._unique('scenario', id), 'title': title, **fields}))
        return id

    def evidence(self, id: str, kind: str, path: str, locator: str, excerpt: Any, **fields: Any) -> str:
        """Register one sanitized capture excerpt. Reference its id from every event it supports."""
        self._evidence.append(_clean({'id': self._unique('evidence', id), 'kind': kind, 'path': path,
                                     'locator': locator, 'excerpt': excerpt, **fields}))
        return id

    def event(self, id: str, scenario_id: str, *, process: str, kind: str, label: str, observation: str,
              evidence_class: str, evidence_refs: list[str], status: str = 'ok', **fields: Any) -> str:
        self._events.append(_clean({'id': self._unique('event', id), 'scenario_id': scenario_id, 'process': process,
                                   'kind': kind, 'label': label, 'status': status, 'evidence_class': evidence_class,
                                   'observation': observation, 'evidence_refs': evidence_refs, **fields}))
        return id

    def step(self, id: str, title: str, *, status: str, technical: str, intuitive: str,
             event_ids: list[str] | None = None, **fields: Any) -> str:
        self._story['steps'].append(_clean({'id': self._unique('step', id), 'title': title, 'status': status,
                                           'event_ids': event_ids or [], 'technical': technical,
                                           'intuitive': intuitive, **fields}))
        return id

    def story_meta(self, *, overview: str | None = None, diagram: str | None = None,
                   cast: list[dict[str, str]] | None = None) -> None:
        self._story.update(_clean({'overview': overview, 'diagram': diagram, 'cast': cast}))

    def coverage(self, area: str, status: str, detail: str) -> None:
        self.meta['coverage'].append({'area': area, 'status': status, 'detail': detail})

    def source(self, title: str, *, url: str | None = None, path: str | None = None, **fields: Any) -> None:
        self._sources.append(_clean({'title': title, 'url': url, 'path': path, **fields}))

    def data(self) -> dict[str, Any]:
        data: dict[str, Any] = {'schema_version': _build.SCHEMA_VERSION, 'run': self.meta, 'scenarios': self._scenarios,
                                'events': self._events, 'evidence': self._evidence, 'sources': self._sources}
        if self._story['steps']:
            data['story'] = self._story
        return data

    def validate(self) -> dict[str, Any]:
        data = self.data()
        _build.validate(data)
        return data

    def save(self, path: str | Path) -> Path:
        data = self.validate()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
        return out

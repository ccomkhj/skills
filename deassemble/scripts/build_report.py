#!/usr/bin/env python3
"""Validate sanitized deassemble data and create an offline HTML explorer.

This script is a renderer, not a capture agent, evidence authenticator, or redactor.
Python 3.10+; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MAX_BYTES = 16 * 1024 * 1024
MAX_EVENTS = 10_000
SCHEMA_VERSION = '1.1'
# How an event was established. Only the first two are direct observations of the real application.
EVIDENCE_CLASSES = frozenset({'observed', 'observed-instrumented', 'mock-backed', 'fixture', 'absence'})
# Story steps may additionally cover what the run did not reach.
STEP_STATUSES = EVIDENCE_CLASSES | frozenset({'not-observed', 'source-only'})
RUN_ROLES = frozenset({'baseline', 'instrumented', 'mock', 'fixture', 'discovery'})
# 'absence' is an observation too (something demonstrably did not happen in a real run).
CLASS_STRENGTH = {'observed': 3, 'observed-instrumented': 3, 'absence': 3, 'fixture': 2, 'mock-backed': 2}


class ReportError(ValueError):
    """Invalid report structure or unsafe build request."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportError(message)


def text(value: Any, name: str) -> None:
    require(isinstance(value, str) and bool(value.strip()), f'{name} must be a nonempty string')


def array(value: Any, name: str) -> None:
    require(isinstance(value, list), f'{name} must be an array')


def object_(value: Any, name: str) -> None:
    require(isinstance(value, dict), f'{name} must be an object')


def index(items: Any, name: str) -> dict[str, dict[str, Any]]:
    array(items, name)
    result: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(items):
        object_(item, f'{name}[{i}]')
        identifier = item.get('id')
        text(identifier, f'{name}[{i}].id')
        require(identifier not in result, f'Duplicate {name} ID: {identifier}')
        result[identifier] = item
    return result


def http_url(value: Any, name: str) -> None:
    text(value, name)
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in ('http', 'https') and bool(parsed.hostname)
        valid = valid and parsed.username is None and parsed.password is None
    except ValueError:
        valid = False
    require(valid, f'{name} must be an HTTP(S) URL without credentials')


def validate(data: Any) -> None:
    """Check structure and references, never claim to establish capture authenticity."""
    object_(data, 'report')
    # JavaScript cannot preserve arbitrary-size JSON integers as Number values.
    # Reject lossy data instead of silently changing captured values in the viewer.
    pending = [(data, 0)]
    while pending:
        value, depth = pending.pop()
        require(depth <= 64, 'JSON nesting exceeds 64 levels; use a bounded snapshot')
        if type(value) is int:
            require(abs(value) <= 9_007_199_254_740_991, 'Large integers must be encoded as typed decimal strings for lossless playback')
        elif type(value) is float:
            require(math.isfinite(value), 'Non-finite numbers require an explicit typed representation')
        elif isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
    require(data.get('schema_version') == SCHEMA_VERSION, f'schema_version must be "{SCHEMA_VERSION}"')
    run = data.get('run')
    object_(run, 'run')
    for field in ('id', 'title', 'summary', 'source_revision'):
        text(run.get(field), f'run.{field}')
    sub_runs = index(run.get('runs', []), 'run.runs')
    for sub in sub_runs.values():
        require(sub.get('role') in RUN_ROLES, f'run.runs[{sub["id"]}].role must be one of {sorted(RUN_ROLES)}')
        array(sub.get('command'), f'run.runs[{sub["id"]}].command')
        for arg in sub['command']:
            text(arg, f'run.runs[{sub["id"]}].command argument')
        for field in ('started_at', 'instrumentation', 'cwd'):
            if field in sub:
                text(sub[field], f'run.runs[{sub["id"]}].{field}')
    require(run.get('status') in ('completed', 'partial', 'blocked'), 'Invalid run.status')
    require(run.get('purpose') in ('application', 'demo'), 'Invalid run.purpose')
    array(run.get('command'), 'run.command')
    for arg in run['command']:
        text(arg, 'run.command argument')
    object_(run.get('capture'), 'run.capture')
    for field in ('method', 'ordering', 'limits', 'redaction', 'overhead'):
        text(run['capture'].get(field), f'run.capture.{field}')
    array(run.get('coverage'), 'run.coverage')
    for coverage in run['coverage']:
        object_(coverage, 'coverage entry')
        for field in ('area', 'status', 'detail'):
            text(coverage.get(field), f'coverage.{field}')
    array(run.get('reproduction', []), 'run.reproduction')
    for instruction in run.get('reproduction', []):
        text(instruction, 'reproduction instruction')

    scenarios = index(data.get('scenarios'), 'scenarios')
    evidence = index(data.get('evidence'), 'evidence')
    events = index(data.get('events'), 'events')
    require(len(events) <= MAX_EVENTS, f'Limit is {MAX_EVENTS:,} events; scope or chunk the recording')
    if run['status'] == 'completed':
        require(bool(events), 'A completed run must have recorded events')
    for scenario in scenarios.values():
        text(scenario.get('title'), 'scenario.title')
    for item in evidence.values():
        for field in ('kind', 'path', 'locator'):
            text(item.get(field), f'evidence.{field}')
        require('excerpt' in item, f'Evidence {item["id"]} has no excerpt')
        if 'sha256' in item:
            require(isinstance(item['sha256'], str) and bool(re.fullmatch(r'[a-fA-F0-9]{64}', item['sha256'])), 'Invalid evidence sha256')

    for event in events.values():
        prefix = f'event {event["id"]}'
        for field in ('label', 'observation', 'process', 'kind', 'scenario_id'):
            text(event.get(field), f'{prefix}.{field}')
        require(event['scenario_id'] in scenarios, f'{prefix}: unknown scenario')
        require(event.get('status') in ('ok', 'error', 'running', 'unknown'), f'{prefix}: invalid status')
        require(event.get('evidence_class') in EVIDENCE_CLASSES, f'{prefix}: evidence_class must be one of {sorted(EVIDENCE_CLASSES)}')
        if 'run_id' in event:
            text(event['run_id'], f'{prefix}.run_id')
            require(event['run_id'] in sub_runs, f'{prefix}: run_id {event["run_id"]} is not declared in run.runs')
        if 'clock' in event:
            text(event['clock'], f'{prefix}.clock')
        if 'absence' in event:
            object_(event['absence'], f'{prefix}.absence')
            for field in ('expected', 'searched'):
                text(event['absence'].get(field), f'{prefix}.absence.{field}')
        if event.get('evidence_class') == 'absence':
            require('absence' in event, f'{prefix}: an absence event needs absence.expected and absence.searched')
        if 'explain' in event:
            object_(event['explain'], f'{prefix}.explain')
            for level in ('technical', 'intuitive'):
                if level in event['explain']:
                    text(event['explain'][level], f'{prefix}.explain.{level}')
        refs = event.get('evidence_refs')
        array(refs, f'{prefix}.evidence_refs')
        require(bool(refs), f'{prefix}: every event needs captured evidence')
        for ref in refs:
            text(ref, f'{prefix}.evidence reference')
            require(ref in evidence, f'{prefix}: unknown evidence reference {ref}')
        array(event.get('objects', []), f'{prefix}.objects')
        for obj in event.get('objects', []):
            text(obj, f'{prefix}.object ID')
        array(event.get('causes', []), f'{prefix}.causes')
        for cause in event.get('causes', []):
            object_(cause, f'{prefix}.cause')
            text(cause.get('event_id'), f'{prefix}.cause.event_id')
            require(cause['event_id'] in events, f'{prefix}: unknown causal event')
            require(cause['event_id'] != event['id'], f'{prefix}: self-causal link')
            require(cause.get('relation') in ('observed', 'inferred'), f'{prefix}: invalid causal relation')
            text(cause.get('basis'), f'{prefix}.cause.basis')
        for field in ('before', 'after'):
            if field in event:
                object_(event[field], f'{prefix}.{field}')
        if 'elapsed_ms' in event:
            value = event['elapsed_ms']
            require(type(value) in (int, float) and math.isfinite(value) and value >= 0, f'{prefix}: invalid elapsed_ms')
        if 'source' in event:
            source = event['source']
            object_(source, f'{prefix}.source')
            for field in ('path', 'revision', 'code'):
                text(source.get(field), f'{prefix}.source.{field}')
            for field in ('line', 'end_line', 'code_start_line'):
                if field in source:
                    require(type(source[field]) is int and source[field] > 0, f'{prefix}: invalid source.{field}')
            if 'byte_offset' in source:
                require(type(source['byte_offset']) is int and source['byte_offset'] >= 0, f'{prefix}: invalid source.byte_offset')
            if 'line_basis' in source:
                require(source['line_basis'] in ('revision', 'instrumented'), f'{prefix}: source.line_basis must be "revision" or "instrumented"')
            if 'patch' in source:
                text(source['patch'], f'{prefix}.source.patch')
        array(event.get('capture_gaps', []), f'{prefix}.capture_gaps')
        for gap in event.get('capture_gaps', []):
            text(gap, f'{prefix}.capture gap')
        array(event.get('notes', []), f'{prefix}.notes')
        for note in event.get('notes', []):
            object_(note, f'{prefix}.note')
            require(note.get('kind') in ('inference', 'source-only', 'external explanation'), f'{prefix}: invalid note kind')
            text(note.get('text'), f'{prefix}.note.text')
            if 'url' in note:
                http_url(note['url'], f'{prefix}.note.url')
    array(data.get('sources', []), 'sources')
    for source in data.get('sources', []):
        object_(source, 'source')
        text(source.get('title'), 'source.title')
        require(('url' in source) != ('path' in source), 'source needs exactly one of url (HTTP(S)) or path (locally installed documentation)')
        if 'url' in source:
            http_url(source['url'], 'source.url')
        else:
            text(source['path'], 'source.path')
            if 'version' in source:
                text(source['version'], 'source.version')

    if 'story' in data:
        story = data['story']
        object_(story, 'story')
        if 'overview' in story:
            text(story['overview'], 'story.overview')
        if 'diagram' in story:
            text(story['diagram'], 'story.diagram')
        for i, member in enumerate(story.get('cast', [])):
            object_(member, f'story.cast[{i}]')
            text(member.get('part'), f'story.cast[{i}].part')
            text(member.get('role'), f'story.cast[{i}].role')
        steps = index(story.get('steps'), 'story.steps')
        require(bool(steps), 'story.steps must not be empty when story is present')
        for step in steps.values():
            prefix = f'story step {step["id"]}'
            text(step.get('title'), f'{prefix}.title')
            require(step.get('status') in STEP_STATUSES, f'{prefix}: status must be one of {sorted(STEP_STATUSES)}')
            for level in ('technical', 'intuitive'):
                text(step.get(level), f'{prefix}.{level}')
            array(step.get('event_ids', []), f'{prefix}.event_ids')
            for event_id in step.get('event_ids', []):
                require(event_id in events, f'{prefix}: unknown event {event_id}')
            # Related events (for example a mock-backed twin of a live step) are navigable but never count as backing.
            array(step.get('related_event_ids', []), f'{prefix}.related_event_ids')
            for event_id in step.get('related_event_ids', []):
                require(event_id in events, f'{prefix}: unknown related event {event_id}')
                require(event_id not in step.get('event_ids', []), f'{prefix}: {event_id} cannot be both backing and related')
            if step['status'] in EVIDENCE_CLASSES:
                require(bool(step.get('event_ids')), f'{prefix}: a step with status {step["status"]} must list the events that back it')
                # A step may not claim stronger evidence than its weakest backing event.
                weakest = min(CLASS_STRENGTH[events[e]['evidence_class']] for e in step['event_ids'])
                require(CLASS_STRENGTH[step['status']] <= weakest,
                        f'{prefix}: status {step["status"]} overstates its backing events')
            else:
                require(not step.get('event_ids'), f'{prefix}: a {step["status"]} step cannot list recorded events')
            for j, src in enumerate(step.get('sources', [])):
                object_(src, f'{prefix}.sources[{j}]')
                text(src.get('path'), f'{prefix}.sources[{j}].path')
                if 'line' in src:
                    require(type(src['line']) is int and src['line'] > 0, f'{prefix}.sources[{j}].line invalid')
            for field in ('chips',):
                array(step.get(field, []), f'{prefix}.{field}')
                for chip in step.get(field, []):
                    text(chip, f'{prefix}.chip')
            if 'loop' in step:
                text(step['loop'], f'{prefix}.loop')
            if 'number' in step:
                require(type(step['number']) is int and step['number'] >= 0, f'{prefix}.number invalid')

    # Check causal links for cycles without recursion on long recordings.
    successors = {key: [] for key in events}
    degree = {key: 0 for key in events}
    for event in events.values():
        for cause in event.get('causes', []):
            successors[cause['event_id']].append(event['id'])
            degree[event['id']] += 1
    ready = [key for key, count in degree.items() if count == 0]
    processed = 0
    while ready:
        key = ready.pop()
        processed += 1
        for successor in successors[key]:
            degree[successor] -= 1
            if degree[successor] == 0:
                ready.append(successor)
    require(processed == len(events), 'Causal links contain a cycle; model distinct event occurrences')


def render(data: dict[str, Any], template: str) -> str:
    validate(data)
    marker = '__DEASSEMBLE_PAYLOAD__'
    require(template.count(marker) == 1, 'Template must contain exactly one payload marker')
    payload = json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    # Prevent closing script tags or HTML tokens inside the inert JSON block.
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    code = re.findall(r'<script id="viewer-code">([\s\S]*?)</script>', template)
    require(len(code) == 1, 'Template must contain exactly one viewer-code script')
    digest = base64.b64encode(hashlib.sha256(code[0].encode('utf-8')).digest()).decode('ascii')
    require(template.count('__DEASSEMBLE_SCRIPT_HASH__') == 1, 'Missing script hash marker')
    return template.replace('__DEASSEMBLE_SCRIPT_HASH__', digest).replace(marker, payload)


def reject_constant(value: str) -> None:
    raise ReportError(f'Nonstandard JSON number: {value}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Sanitized report JSON')
    parser.add_argument('--output', type=Path, help='New self-contained HTML file (required unless --check)')
    parser.add_argument('--force', action='store_true', help='Replace an existing output file')
    parser.add_argument('--template', type=Path, default=None,
                        help='Alternative viewer template (default: the bundled assets/viewer.html). It must keep the payload marker, the viewer-code script and the script hash marker.')
    parser.add_argument('--check', action='store_true', help='Validate the input only; write nothing')
    args = parser.parse_args()
    template_path = args.template or Path(__file__).resolve().parents[1] / 'assets' / 'viewer.html'
    try:
        if args.check:
            with args.input.open(encoding='utf-8') as handle:
                data = json.load(handle, parse_constant=reject_constant)
            validate(data)
            story = len(data.get('story', {}).get('steps', []))
            print(f'Valid: {len(data["events"])} events, {len(data["evidence"])} evidence records, {story} story steps.')
            return 0
        require(args.output is not None, '--output is required')
        require(args.input.resolve() != args.output.resolve(), 'Input and output must be different files')
        require(args.output.suffix.lower() == '.html', 'Output must have an .html extension')
        require(args.input.stat().st_size <= MAX_BYTES, 'Input exceeds 16 MiB; scope or chunk the recording')
        with args.input.open(encoding='utf-8') as handle:
            data = json.load(handle, parse_constant=reject_constant)
        output = render(data, template_path.read_text(encoding='utf-8'))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('w' if args.force else 'x', encoding='utf-8') as handle:
            handle.write(output)
        print(f'Created {args.output} with {len(data["events"])} recorded events.')
        print('Structure checked. Capture authenticity and redaction require separate review.')
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(f'Build failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

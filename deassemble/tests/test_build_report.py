"""Synthetic contract tests for the renderer, not application execution evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_report', ROOT / 'scripts' / 'build_report.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TEMPLATE = (ROOT / 'assets' / 'viewer.html').read_text()


def fixture():
    return {
        'schema_version': '1.1',
        'run': {'id': 'test', 'title': 'Synthetic renderer test', 'summary': 'Unit-test fixture, not a runtime recording.',
                'source_revision': 'test-fixture', 'purpose': 'demo', 'status': 'partial',
                'command': [], 'capture': {'method': 'unit test', 'ordering': 'test order', 'limits': 'fixture only',
                                         'redaction': 'synthetic', 'overhead': 'not measured'},
                'coverage': [], 'reproduction': []},
        'scenarios': [{'id': 's1', 'title': 'Test'}],
        'events': [{'id': 'e1', 'scenario_id': 's1', 'label': 'Test event', 'observation': 'Synthetic fixture.',
                    'process': 'p1', 'kind': 'test', 'status': 'ok', 'evidence_class': 'observed', 'evidence_refs': ['r1'],
                    'before': {'number': 1}, 'after': {'number': 2}}],
        'evidence': [{'id': 'r1', 'kind': 'unit-test fixture', 'path': 'test.json', 'locator': 'test fixture', 'excerpt': {'number': 2}}],
        'sources': []
    }


class BuilderTests(unittest.TestCase):
    def test_valid_report(self):
        module.validate(fixture())

    def test_completed_empty_rejected(self):
        data = fixture(); data['run']['status'] = 'completed'; data['events'] = []
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_blocked_empty_allowed(self):
        data = fixture(); data['run']['status'] = 'blocked'; data['events'] = []; data['scenarios'] = []; data['evidence'] = []
        module.validate(data)

    def test_missing_evidence_rejected(self):
        data = fixture(); data['events'][0]['evidence_refs'] = []
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_unknown_reference_rejected(self):
        data = fixture(); data['events'][0]['evidence_refs'] = ['missing']
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_duplicate_event_rejected(self):
        data = fixture(); data['events'].append(deepcopy(data['events'][0]))
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_unknown_scenario_rejected(self):
        data = fixture(); data['events'][0]['scenario_id'] = 'missing'
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_unknown_cause_rejected(self):
        data = fixture(); data['events'][0]['causes'] = [{'event_id': 'missing', 'relation': 'observed', 'basis': 'test'}]
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_causal_cycle_rejected(self):
        data = fixture(); second = deepcopy(data['events'][0]); second['id'] = 'e2'; data['events'].append(second)
        data['events'][0]['causes'] = [{'event_id': 'e2', 'relation': 'observed', 'basis': 'test'}]
        data['events'][1]['causes'] = [{'event_id': 'e1', 'relation': 'observed', 'basis': 'test'}]
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_unsafe_link_rejected(self):
        data = fixture(); data['sources'] = [{'title': 'bad', 'url': 'javascript:alert(1)'}]
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_credential_link_rejected(self):
        data = fixture(); data['sources'] = [{'title': 'bad', 'url': 'https://user:secret@example.org'}]
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_unsafe_large_integer_rejected(self):
        data = fixture(); data['events'][0]['after']['number'] = 2**63-1
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_nonfinite_value_rejected(self):
        data = fixture(); data['events'][0]['after']['number'] = float('inf')
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_invalid_source_rejected(self):
        data = fixture(); data['events'][0]['source'] = {'path': 'x.py', 'code': 'x=1', 'revision': 'fixture', 'line': 0}
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_escaping_preserves_values(self):
        data = fixture()
        value = '</script><script>globalThis.pwned=true</script> __DEASSEMBLE_SCRIPT_HASH__ & <tag>'
        data['events'][0]['after']['payload'] = value
        rendered = module.render(data, TEMPLATE)
        self.assertNotIn('<script>globalThis.pwned=true</script>', rendered)
        payload = rendered.split('<script id="report-data" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(payload), data)
        self.assertIn("script-src 'sha256-", rendered)
        self.assertNotIn("script-src 'unsafe-inline'", rendered)

    def test_missing_evidence_class_rejected(self):
        data = fixture(); del data['events'][0]['evidence_class']
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_unknown_run_id_rejected(self):
        data = fixture(); data['events'][0]['run_id'] = 'r-missing'
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_declared_run_id_allowed(self):
        data = fixture(); data['run']['runs'] = [{'id': 'base', 'role': 'baseline', 'command': ['true']}]
        data['events'][0]['run_id'] = 'base'
        module.validate(data)

    def test_local_documentation_source_allowed(self):
        data = fixture(); data['sources'] = [{'title': 'installed docs', 'path': 'node_modules/pkg/docs/x.md', 'version': '1.0.0'}]
        module.validate(data)

    def test_source_needs_url_or_path(self):
        data = fixture(); data['sources'] = [{'title': 'neither'}]
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_story_valid(self):
        data = fixture(); data['events'][0]['explain'] = {'technical': 'x', 'intuitive': 'y'}
        data['story'] = {'overview': 'o', 'steps': [
            {'id': 'st1', 'title': 'Observed step', 'status': 'observed', 'event_ids': ['e1'], 'technical': 't', 'intuitive': 'i'},
            {'id': 'st2', 'title': 'Unreached step', 'status': 'not-observed', 'technical': 't', 'intuitive': 'i'}]}
        module.validate(data)

    def test_story_step_overstating_evidence_rejected(self):
        data = fixture(); data['events'][0]['evidence_class'] = 'mock-backed'
        data['story'] = {'steps': [{'id': 'st1', 'title': 's', 'status': 'observed', 'event_ids': ['e1'], 'technical': 't', 'intuitive': 'i'}]}
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_story_not_observed_step_with_events_rejected(self):
        data = fixture()
        data['story'] = {'steps': [{'id': 'st1', 'title': 's', 'status': 'not-observed', 'event_ids': ['e1'], 'technical': 't', 'intuitive': 'i'}]}
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_story_step_missing_intuitive_rejected(self):
        data = fixture()
        data['story'] = {'steps': [{'id': 'st1', 'title': 's', 'status': 'observed', 'event_ids': ['e1'], 'technical': 't'}]}
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_instrumented_line_basis_allowed(self):
        data = fixture(); data['events'][0]['source'] = {'path': 'x.py', 'code': 'x=1', 'revision': 'fixture', 'line': 3, 'line_basis': 'instrumented', 'patch': 'evidence/probes.patch'}
        module.validate(data)

    def test_absence_event_needs_anchor(self):
        data = fixture(); data['events'][0]['evidence_class'] = 'absence'
        with self.assertRaises(module.ReportError): module.validate(data)
        data['events'][0]['absence'] = {'expected': 'a probe line', 'searched': 'evidence/probes.jsonl lines 1-40'}
        module.validate(data)

    def test_related_event_cannot_also_back(self):
        data = fixture()
        data['story'] = {'steps': [{'id': 'st1', 'title': 's', 'status': 'observed', 'event_ids': ['e1'], 'related_event_ids': ['e1'], 'technical': 't', 'intuitive': 'i'}]}
        with self.assertRaises(module.ReportError): module.validate(data)

    def test_missing_template_marker_rejected(self):
        with self.assertRaises(module.ReportError): module.render(fixture(), '<html></html>')


if __name__ == '__main__':
    unittest.main()

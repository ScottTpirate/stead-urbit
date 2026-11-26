"""Pure model-to-review examples. No inference, Home write or credential is used."""
from hashlib import sha256
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
try:
    import model_catalog
    import model_doc_replacement as doc
finally:
    sys.path.pop(0)

M = doc.model
DOC = '019939ba-4000-7000-8000-000000000041'
COLLECTION = '019939ba-4000-7000-8000-000000000042'
RUN = '019939ba-4000-7000-8000-000000000043'


class DocReplacementTests(unittest.TestCase):
    def setUp(self):
        self.catalog = model_catalog.ModelCatalog((ROOT / 'specs/urbit/fixtures/model-catalog.json').read_bytes())
        row = next(row for row in self.catalog.inventory() if row['placement'] == 'remote-api')
        self.scope = {**{key: row[key] for key in model_catalog.BINDING_FIELDS},
                      'connection_digest': row['connection_digest'], 'run_id': RUN, 'attempt': '1',
                      'effect_sequence': '1', 'run_contract_sha256': 'e' * 64, 'context_digest': 'f' * 64}
        self.source = f"---\nid: {DOC}\ntype: page\nstate: published\n---\n" + '# Weekly review\n\nMonday at 10:00.  \n\nContact Zoë.\n\n'
        self.target = {'kind': 'document', 'project_id': row['project_id'], 'collection_id': COLLECTION,
                       'document_id': DOC, 'expected_revision': '7', 'base_markdown_sha256': self.digest(self.source)}

    @staticmethod
    def digest(markdown):
        return sha256(markdown.encode()).hexdigest()

    def setup_request(self, source=None, limit='4096', target=None):
        source = self.source if source is None else source
        target = self.target | {'base_markdown_sha256': self.digest(source)} if target is None else target
        tool = doc.replacement_tool(target, limit)
        spec, request = self.catalog.prepare(self.scope, '1', 'Return one replacement for review.',
             [{'role': 'user', 'content': 'Move the meeting two weekdays later.\n' + source}], [tool])
        return spec, request, target

    def reply(self, spec, request, old='Monday', new='Wednesday'):
        raw = M.canonical({'id': 'response', 'created': 1, 'model': spec.value()['model'], 'object': 'chat.completion',
            'choices': [{'index': 0, 'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
                'tool_calls': [{'id': 'call-1', 'type': 'function', 'function': {'name': doc.TOOL_NAME,
                'arguments': M.canonical({'old_text': old, 'new_text': new}).decode()}}]}}],
            'usage': {'prompt_tokens': 12, 'completion_tokens': 5, 'total_tokens': 17}})
        return M.normalize_reply(spec, request, raw)

    def result(self, source, old, new, limit='4096'):
        spec, request, target = self.setup_request(source, limit)
        return doc.materialize(spec, request, self.reply(spec, request, old, new), target, source, limit)

    def test_catalog_reply_produces_full_doc_and_exact_unrelated_bytes(self):
        result = self.result(self.source, 'Monday', 'Wednesday')
        self.assertEqual(result['target'], self.target)
        self.assertEqual(result['markdown'].encode(), self.source.replace('Monday', 'Wednesday').encode())
        self.assertEqual(self.source.count('Monday'), 1)
        self.assertTrue(result['markdown'].endswith('Zoë.\n\n'))

    def test_base_identity_revision_budget_and_project_are_pinned(self):
        spec, request, target = self.setup_request()
        proposal = self.reply(spec, request)
        for key, value in [('expected_revision', '8'), ('collection_id', RUN), ('document_id', RUN),
                           ('project_id', RUN), ('base_markdown_sha256', 'f' * 64)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                doc.materialize(spec, request, proposal, target | {key: value}, self.source, '4096')
        with self.assertRaisesRegex(ValueError, 'doc_base_changed'):
            doc.materialize(spec, request, proposal, target, self.source + ' ', '4096')
        with self.assertRaisesRegex(ValueError, 'doc_target_or_budget_changed'):
            doc.materialize(spec, request, proposal, target, self.source, '4095')
        with self.assertRaises(ValueError):
            doc.replacement_tool(target | {'expected_revision': '0'}, '4096')
        spec, request, target = self.setup_request(target=self.target | {'project_id': RUN})
        with self.assertRaisesRegex(ValueError, 'doc_target_or_budget_changed'):
            doc.materialize(spec, request, self.reply(spec, request), target, self.source, '4096')

    def test_missing_overlapping_repeated_header_and_noop_are_rejected(self):
        for old, new in [('missing', 'x'), ('aa', 'x'), ('repeat', 'x'), ('', 'x'), ('Monday', 'Monday'),
                         ('state: published', 'state: draft'), (DOC, RUN)]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.result(self.source + 'aaa repeat repeat', old, new)
        with self.assertRaisesRegex(ValueError, 'invalid_doc_header'):
            self.result(self.source.replace(DOC, RUN), 'Monday', 'Wednesday')

    def test_absent_newline_deletion_multiline_and_output_byte_bounds(self):
        source = self.source.rstrip('\n')
        self.assertEqual(self.result(source, 'Weekly review\n\nMonday', 'Weekly review\n\nFriday')['markdown'],
                         source.replace('Monday', 'Friday'))
        self.assertEqual(self.result(source, 'Contact ', '')['markdown'], source.replace('Contact ', ''))
        for base, old, new in [(source, 'Zoë.', 'Zoë.\n'), (self.source, 'Zoë.\n\n', 'Zoë.')]:
            with self.assertRaisesRegex(ValueError, 'doc_final_newline_changed'):
                self.result(base, old, new)
        with self.assertRaisesRegex(ValueError, 'doc_output_byte_bound'):
            self.result(source, 'Monday', '日' * 10, str(len(source.encode()) + 20))
        with self.assertRaises(ValueError):
            self.result(source, 'Monday', '日' * 683)

    def test_wrong_tool_request_or_multiple_calls_cannot_supply_a_doc(self):
        spec, request, target = self.setup_request()
        proposal = self.reply(spec, request)
        call, = proposal['tool_proposals']
        for altered in [proposal | {'request_digest': '0' * 64}, proposal | {'state': 'refused'},
                        proposal | {'tool_proposals': [call, call]},
                        proposal | {'tool_proposals': [call | {'tool_id': RUN}]},
                        proposal | {'tool_proposals': [call | {'revision': '2'}]}]:
            with self.assertRaises(ValueError):
                doc.materialize(spec, request, altered, target, self.source, '4096')

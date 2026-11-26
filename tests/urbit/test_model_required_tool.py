"""An operator's explicit function choice pins the wire request and journal replay."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
try:
    import model_catalog
    import model_effect_journal
finally:
    sys.path.pop(0)
M = model_catalog.model


def uid(n):
    return '019939ba-4000-7000-8000-' + f'{n:012x}'


def tool(n, name):
    return {'tool_id': uid(n), 'revision': '1', 'name': name,
            'description': 'Propose a value for review.', 'arguments': {'value': '128'}}


class RequiredToolTests(unittest.TestCase):
    def setUp(self):
        example = json.loads((ROOT / 'specs/urbit/fixtures/model-catalog.json').read_bytes())
        self.legacy = example['connections'][1]
        self.updated = {**self.legacy, 'protocol': 'stead.model-connection/2', 'revision': '2',
                        'capabilities': {**self.legacy['capabilities'], 'required_tool_choice': 'single-function/1'}}
        self.binding = {**example['bindings'][1], 'connection_revision': '2'}
        self.registry = [tool(31, 'suggest_edit'), tool(32, 'ask_question')]

    def args(self, config):
        catalog = model_catalog.ModelCatalog(M.canonical({'protocol': 'stead.model-catalog/1',
            'connections': [config], 'bindings': [self.binding | {'connection_revision': config['revision']}]}))
        binding = next(catalog.inventory())
        scope = {k: binding[k] for k in model_catalog.BINDING_FIELDS}
        scope.update(connection_digest=binding['connection_digest'], run_id=uid(30), attempt='1',
                     effect_sequence='1', run_contract_sha256='c' * 64, context_digest='d' * 64)
        return catalog, (scope, '1', 'Propose one change.', [{'role': 'user', 'content': 'Suggest a title.'}], self.registry)

    def test_required_calls_are_opt_in_and_offer_only_the_registered_function(self):
        catalog, args = self.args(self.legacy)
        with self.assertRaisesRegex(ValueError, 'required_tool_unsupported'):
            catalog.prepare(*args, required_tool='suggest_edit')
        self.assertEqual(json.loads(catalog.prepare(*args)[1].body)['tool_choice'], 'auto')
        catalog, args = self.args(self.updated)
        spec, required = catalog.prepare(*args, required_tool='suggest_edit')
        self.assertEqual(M.validate_request(spec, required), required)
        body = json.loads(required.body)
        self.assertEqual(body['tool_choice'], 'required')
        self.assertEqual([item['function']['name'] for item in body['tools']], ['suggest_edit'])
        self.assertNotEqual(required.request_digest, catalog.prepare(*args)[1].request_digest)
        with self.assertRaisesRegex(ValueError, 'required_tool_not_in_registry'):
            catalog.prepare(*args, required_tool='missing')
        body['tools'] = []; altered = replace(required, body=M.canonical(body))
        with self.assertRaisesRegex(ValueError, 'invalid_required_tool_choice'):
            M.validate_request(spec, altered)

    def test_capability_schema_and_old_pins_reject_implicit_upgrade(self):
        for config in [self.updated | {'protocol': 'stead.model-connection/1'},
                       self.updated | {'capabilities': self.legacy['capabilities']},
                       self.updated | {'capabilities': self.updated['capabilities'] | {'function_tools': 'disabled'}}]:
            with self.assertRaises(ValueError):
                self.args(config)
        off = self.updated | {'capabilities': self.updated['capabilities'] | {'required_tool_choice': 'unsupported'}}
        catalog, args = self.args(off)
        with self.assertRaisesRegex(ValueError, 'required_tool_unsupported'):
            catalog.prepare(*args, required_tool='suggest_edit')
        self.assertNotEqual(M.connection(M.canonical(self.legacy)).sha256, M.connection(M.canonical(self.updated)).sha256)

    def test_unexpected_calls_or_plain_prose_are_rejected_and_refusal_remains_a_refusal(self):
        catalog, args = self.args(self.updated)
        spec, request = catalog.prepare(*args, required_tool='suggest_edit')
        def reply(names, refusal=None, finish=None):
            calls = [{'type': 'function', 'id': f'call-{i}', 'function': {'name': name, 'arguments': '{"value":"Monday"}'}}
                     for i, name in enumerate(names)]
            message = {'role': 'assistant', 'content': 'A suggestion', 'refusal': refusal, 'tool_calls': calls}
            return M.normalize_reply(spec, request, M.canonical({
                'id': 'model-reply', 'created': 1, 'object': 'chat.completion', 'model': spec.value()['model'],
                'choices': [{'index': 0, 'message': message, 'finish_reason': finish or ('tool_calls' if calls else 'stop')}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 8, 'total_tokens': 18}}))
        for names in [[], ['ask_question'], ['suggest_edit', 'suggest_edit']]:
            with self.subTest(names=names), self.assertRaisesRegex(ValueError, 'required_tool_reply_mismatch'):
                reply(names)
        self.assertEqual(reply(['suggest_edit'])['tool_proposals'][0]['arguments'], {'value': 'Monday'})
        self.assertEqual(reply([], refusal='Unable')['state'], 'refused')
        self.assertEqual(reply([], finish='length')['state'], 'incomplete')

    def test_journal_reopens_exact_required_turn_and_conflicts_with_automatic_mode(self):
        catalog, args = self.args(self.updated)
        with tempfile.TemporaryDirectory() as name:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY)
            try:
                journal = model_effect_journal.EffectJournal.for_run(fd, catalog, *args, required_tool='ask_question')
                original = journal.observe()
                journal.close()
                reopened = model_effect_journal.EffectJournal.for_run(fd, catalog, *args, required_tool='ask_question',
                                                                     prior_digest=original['request_digest'])
                try:
                    self.assertEqual(reopened.observe(), original)
                    self.assertFalse(original['may_dispatch'])
                finally:
                    reopened.close()
                with self.assertRaises(ValueError):
                    model_effect_journal.EffectJournal.for_run(fd, catalog, *args)
            finally:
                os.close(fd)

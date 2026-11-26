"""Operator configuration, exact dispatch preparation and journal compatibility."""
import copy
import json
import os
from pathlib import Path
import subprocess
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

EXAMPLE = ROOT / 'specs/urbit/fixtures/model-catalog.json'
M = model_catalog.model


class ModelCatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(EXAMPLE.read_bytes())

    def load(self):
        return model_catalog.ModelCatalog(M.canonical(self.data))

    def scope(self, row):
        return {**{k: row[k] for k in model_catalog.BINDING_FIELDS},
                'connection_digest': row['connection_digest'],
                'run_id': '019939ba-4000-7000-8000-000000000020', 'attempt': '1',
                'effect_sequence': '1', 'run_contract_sha256': 'e' * 64, 'context_digest': 'f' * 64}

    def prepare(self, catalog, scope, prior_digest=None):
        return catalog.prepare(scope, '1', 'Revise the guide.',
                               [{'role': 'user', 'content': 'Add the meeting date.'}], [],
                               prior_digest=prior_digest)

    def test_list_and_prepare_both_models_for_existing_journal(self):
        catalog = self.load()
        rows = list(catalog.inventory())
        self.assertEqual({row['placement'] for row in rows}, {'local-isolated', 'remote-api'})
        for row in rows:
            spec, request = self.prepare(catalog, self.scope(row))
            self.assertEqual(json.loads(request.body)['model'], row['model'])
            self.assertEqual(spec.sha256, row['connection_digest'])
            record = json.loads(model_effect_journal.prepared_record(spec, request))
            self.assertEqual(json.loads(record['connection'])['revision'], row['connection_revision'])
            self.assertEqual(self.prepare(catalog, self.scope(row), request.request_digest)[1], request)

    def test_supervisor_reopens_same_journal_without_dispatch(self):
        catalog = self.load()
        row = next(catalog.inventory())
        args = (catalog, self.scope(row), '1', 'Revise the guide.',
                [{'role': 'user', 'content': 'Add the meeting date.'}], [])
        with tempfile.TemporaryDirectory() as folder:
            fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
            try:
                prepared = model_effect_journal.EffectJournal.for_run(fd, *args)
                try:
                    original = prepared.observe()
                finally:
                    prepared.close()
                reopened = model_effect_journal.EffectJournal.for_run(fd, *args,
                    prior_digest=original['request_digest'])
                try:
                    self.assertEqual(reopened.observe(), original)
                    self.assertFalse(original['may_dispatch'])
                    self.assertEqual(original['state'], 'prepared')
                finally:
                    reopened.close()
            finally:
                os.close(fd)

    def test_same_connection_can_serve_two_agents(self):
        self.data['bindings'][1]['connection_id'] = self.data['bindings'][0]['connection_id']
        rows = list(self.load().inventory())
        self.assertNotEqual(rows[0]['definition_id'], rows[1]['definition_id'])
        self.assertEqual(rows[0]['connection_digest'], rows[1]['connection_digest'])

    def test_project_definition_runtime_policy_and_digest_are_all_exact(self):
        catalog = self.load()
        scope = self.scope(next(catalog.inventory()))
        for field, changed in [('home', '~zod'), ('project_id', scope['run_id']), ('definition_id', scope['run_id']),
                               ('definition_revision', '2'), ('runtime_id', scope['run_id']), ('runtime_revision', '2'),
                               ('runtime_policy_digest', '0' * 64), ('connection_digest', '0' * 64)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.prepare(catalog, {**scope, field: changed})

    def test_old_pin_survives_new_revision_and_refuses_rebinding(self):
        old = self.load()
        scope = self.scope(next(old.inventory()))
        spec, request = self.prepare(old, scope)
        updated = {**self.data['connections'][0], 'revision': '2', 'model': 'second-model'}
        self.data['connections'].append(updated)
        self.data['bindings'].append({**self.data['bindings'][0], 'connection_revision': '2',
                                      'runtime_revision': '2'})
        self.assertEqual(self.prepare(self.load(), scope), (spec, request))
        self.data['bindings'][0]['connection_revision'] = '2'
        with self.assertRaisesRegex(ValueError, 'connection_scope_changed'):
            self.prepare(self.load(), scope)

    def test_ambiguous_dangling_malformed_and_overbound_catalogs(self):
        original = copy.deepcopy(self.data)
        for mutate in [lambda c: c['connections'].append(c['connections'][0]),
                       lambda c: c['bindings'].append(c['bindings'][0]),
                       lambda c: c['bindings'][0].update(connection_revision='99'),
                       lambda c: c['bindings'][0].update(secret='forbidden'),
                       lambda c: c['connections'][0]['authentication'].update(token='forbidden'),
                       lambda c: c.update(bindings=c['bindings'] * 33)]:
            self.data = copy.deepcopy(original)
            mutate(self.data)
            with self.assertRaises(ValueError):
                self.load()
        with self.assertRaisesRegex(ValueError, 'duplicate_key'):
            model_catalog.ModelCatalog(b'{"protocol":1,"protocol":1}')
        with self.assertRaisesRegex(ValueError, 'json_byte_bound'):
            model_catalog.ModelCatalog(b' ' * (model_catalog.MAX_BYTES + 1))

    def test_empty_catalog_disables_bindings(self):
        row = next(self.load().inventory())
        self.data.update(bindings=[], connections=[])
        self.assertEqual(list(self.load().inventory()), [])
        with self.assertRaisesRegex(ValueError, 'runtime_binding_unavailable'):
            self.prepare(self.load(), self.scope(row))

    def test_operator_cli_lists_only_safe_pins(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/urbit/model_catalog.py'), str(EXAMPLE)],
                                capture_output=True, check=True, text=True, timeout=5)
        self.assertEqual(json.loads(result.stdout), list(self.load().inventory()))
        for private in ('authentication', 'reference_id', 'endpoint', 'provider.invalid', 'http://'):
            self.assertNotIn(private, result.stdout)

"""Host-only recipe and transport-adapter checks; never native qualification.

The frozen schema validates bytes. Independent count/order assertions validate
planned inputs, not a substitute home implementation. Scripted terminal values
below test refusal propagation only and do not manufacture a migrated state.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / 'scripts/urbit'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, CODE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


q = load('_qualification_cases_under_test', 'qualification_cases.py')
v1 = load('_qualification_frozen_v1', 'contracts.py')
v2 = load('_qualification_frozen_v2', 'contracts_v2.py')
FIXTURE = (ROOT / 'specs/urbit/native-fixture.json').read_bytes()


def entries():
    recipe = q.exhaustion_recipe()
    yield from recipe['ordinary']
    yield from recipe['old_revokes']
    for commands in recipe['revokes'].values():
        yield from commands
    yield recipe['overflow']
    yield recipe['unaccepted_legacy']
    yield from recipe['closed_probes'].values()
    privacy = q.predecessor_privacy_recipe()
    yield from privacy['setup']
    for name in ('visible_before', 'private_save', 'visible_after', 'same_project_denial',
                 'cross_project_denial', 'fresh_control'):
        yield privacy[name]
    for recipe in q.resource_recipes():
        yield from recipe['setup']
        yield from recipe.get('accepted', recipe.get('candidates', []))
        if 'rejected' in recipe:
            yield recipe['rejected']


def snapshot(**changes):
    value = {'protocol': 'stead.fixture-snapshot/1', 'state_jam_sha256': '0' * 64,
             'revisions': {}, 'ordinary_count': '0', 'security_counts': {}}
    value.update({key: '0' for key in q.COUNTS})
    value.update({key: '0' * 64 for key in q.PRESERVED_HASHES})
    return {**value, **changes}


def scripted_receipt(entry, predecessor=False):
    cmd = entry.command
    receipt = {'protocol': 'stead.receipt/1' if predecessor else 'stead.receipt/2', 'status': 'accepted',
        'request_id': cmd['request_id'], 'canonical_sha256': entry.digest, 'project_id': cmd['project_id'],
        'resource_id': cmd['resource_id'], 'resource_revision': str(int(cmd['expected_revision']) + 1),
        'authority_epoch': '1', 'principal_id': q.PRINCIPALS[entry.sender], 'binding_id': q.BINDINGS[entry.sender],
        'authentication': 'fake-native/1', 'authentication_strength': 'synthetic-native-sender',
        'accepted_at_ms': '1789257600000', 'git_commit_oid': ''}
    if predecessor:
        receipt.update(journal_sequence='1', journal_digest='0' * 64, policy_revision='0')
    else:
        receipt.update(resource_kind=q.RESOURCE_KINDS[cmd['operation']],
                       container_id=cmd['payload'].get('container_id', ''))
    return receipt


def terminal(value):
    return {'raw': json.dumps(value, separators=(',', ':')), 'json': value,
            'native': {'test_only': 'Scripted adapter response, not a runtime frame'}}


class QualificationRecipesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exhaustion = q.exhaustion_recipe()
        cls.resources = {recipe['name']: recipe for recipe in q.resource_recipes()}
        cls.commands = list(entries())

    def test_every_generated_command_matches_its_frozen_schema_and_digest(self):
        self.assertEqual(len(self.commands), 5065)
        for entry in self.commands:
            reference = v1 if entry.command['protocol'] == 'stead.command/1' else v2
            self.assertEqual(reference.parse(entry.raw), entry.command)
            self.assertEqual(reference.canonical(entry.command), entry.raw)
            self.assertEqual(reference.digest(entry.command), entry.digest)

    def test_exact_fixture_and_both_freezes_are_intact(self):
        v2.verify_freeze()
        fixture = json.loads(FIXTURE)
        self.assertEqual(hashlib.sha256(FIXTURE).hexdigest(), q.FIXTURE_SHA256)
        self.assertEqual({b['ship']: b['principal_id'] for b in fixture['bindings']}, q.PRINCIPALS)
        self.assertEqual({b['ship']: b['binding_id'] for b in fixture['bindings']}, q.BINDINGS)
        v2_api = json.loads((ROOT / 'specs/urbit/v2/native-api.json').read_text())
        self.assertEqual(set(v2_api['receipt']['closed_fields']), q.RECEIPT_FIELDS)
        self.assertEqual(v2_api['receipt']['resource_kind'], q.RESOURCE_KINDS)

    def test_predecessor_is_actual_git_baseline_with_only_import_rename(self):
        for name in ('stead-core', 'stead-codec'):
            original = subprocess.run(['git', 'show', q.PREDECESSOR_COMMIT + ':native/core/desk/lib/' + name + '.hoon'],
                cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
            if name == 'stead-core':
                original = original.replace(b'/+  stead-codec, stead-git\n', b'/+  stead-codec-v1, stead-git\n')
                original = original.replace(b'=,  stead-codec\n', b'=,  stead-codec-v1\n')
            stored = (q.NATIVE / 'lib' / (name + '-v1.hoon')).read_bytes()
            self.assertEqual(stored, original)
            self.assertEqual(hashlib.sha256(stored).hexdigest(), q.PREDECESSOR_FILES[name + '-v1.hoon'])

    def test_all_fresh_recipe_requests_are_unique_and_generators_repeat_exactly(self):
        request_ids = [entry.command['request_id'] for entry in self.commands]
        self.assertEqual(len(request_ids), len(set(request_ids)))
        self.assertEqual([(x.sender, x.raw) for x in self.commands], [(x.sender, x.raw) for x in entries()])
        self.assertEqual(q.recipe_inventory(), q.recipe_inventory())

    def test_legitimate_4096_inputs_have_exact_preconditions_without_counter_seeding(self):
        recipe = self.exhaustion
        self.assertEqual(len(recipe['setup']), 259)
        self.assertEqual(len(recipe['fill']), 3837)
        self.assertEqual(len(recipe['ordinary'][:-1]), 4095)
        self.assertEqual(len(recipe['ordinary']), 4096)
        for project in recipe['projects']:
            commands = [e.command for e in recipe['setup'] if e.command['project_id'] == project]
            self.assertEqual(commands[0]['operation'], 'project.create')
            self.assertEqual(commands[0]['expected_revision'], '0')
            grants = [c for c in commands if c['operation'] == 'policy.grant']
            self.assertEqual([int(c['expected_revision']) for c in grants], list(range(1, 128)))
            self.assertEqual(len(grants) + 1, 128)  # Explicit creator grant consumes a slot.
            self.assertEqual(recipe['grants'][project][-1], commands[0]['request_id'])
            self.assertEqual(len(set(recipe['grants'][project])), 128)
            self.assertEqual([c['expected_revision'] for c in commands if c['operation'] == 'work.create'], ['0'])
        self.assertEqual([int(e.command['expected_revision']) for e in recipe['fill']], list(range(1, 3838)))
        self.assertTrue(all(e.command['resource_id'] == recipe['works'][q.PROJECT] for e in recipe['fill']))
        self.assertEqual(recipe['overflow'].command['expected_revision'], '3838')
        self.assertEqual(recipe['document'].command['expected_revision'], '0')

    def test_revoke_reserves_are_project_local_and_creator_is_revoked_last(self):
        recipe = self.exhaustion
        self.assertEqual([e.command['expected_revision'] for e in recipe['old_revokes']], ['128', '128'])
        self.assertEqual({e.command['project_id'] for e in recipe['old_revokes']}, set(recipe['projects']))
        for project, revokes in recipe['revokes'].items():
            self.assertEqual(len(revokes), 128)
            self.assertEqual([int(e.command['expected_revision']) for e in revokes], list(range(128, 256)))
            self.assertTrue(all(e.command['project_id'] == project and e.sender == 'zod' for e in revokes))
            self.assertEqual([e.command['payload']['grant_id'] for e in revokes], recipe['grants'][project])
            self.assertEqual(revokes[-1].command['payload']['grant_id'], recipe['creators'][project].command['request_id'])
        self.assertEqual(4096 + sum(map(len, recipe['revokes'].values())), 4352)

    def test_unaccepted_legacy_control_is_fresh_valid_v1_at_current_revision(self):
        recipe = self.exhaustion
        entry = recipe['unaccepted_legacy']
        self.assertEqual(entry.command['protocol'], 'stead.command/1')
        self.assertEqual(v1.parse(entry.raw), entry.command)
        self.assertEqual(entry.sender, 'zod')
        self.assertNotIn(entry.command['request_id'], {value.command['request_id'] for value in recipe['ordinary']})
        self.assertNotIn(entry.command['request_id'], {value.command['request_id'] for value in recipe['old_revokes']})
        self.assertEqual(entry.command['expected_revision'], '3838')
        for field in ('project_id', 'resource_id', 'operation', 'payload', 'expected_revision', 'authority_epoch'):
            self.assertEqual(entry.command[field], recipe['overflow'].command[field])
        self.assertEqual(q.recipe_inventory()[recipe['name']]['unaccepted_legacy_sha256'], q.recipe_digest([entry]))

    def test_privacy_controls_share_hidden_ids_but_fresh_control_does_not(self):
        recipe = q.predecessor_privacy_recipe()
        before, private, after = (recipe[name] for name in ('visible_before', 'private_save', 'visible_after'))
        self.assertEqual((before.sender, private.sender, after.sender), ('bus', 'zod', 'bus'))
        self.assertEqual([before.command['expected_revision'], after.command['expected_revision']], ['1', '2'])
        self.assertEqual(before.command['resource_id'], after.command['resource_id'])
        same = recipe['same_project_denial'].command
        self.assertEqual(same['resource_id'], private.command['resource_id'])
        self.assertNotEqual(same['payload']['container_id'], private.command['payload']['container_id'])
        other = recipe['setup'][3].command
        collision = recipe['cross_project_denial'].command
        self.assertEqual(other['resource_id'], collision['resource_id'])
        self.assertNotEqual(other['project_id'], collision['project_id'])
        self.assertNotIn(recipe['fresh_control'].command['resource_id'], {other['resource_id'], private.command['resource_id']})
        self.assertEqual(len(recipe['private_reads']), 3)

    def test_batch_partition_preserves_exact_order_sender_and_bounded_payload(self):
        packed = list(q.batches(self.commands))
        self.assertEqual([e for group in packed for e in group], self.commands)
        for group in packed:
            raw = q.batch_value(group)
            self.assertLessEqual(len(raw), 65536)
            self.assertLessEqual(len(group), 32)
            self.assertEqual(len({e.sender for e in group}), 1)
            body = json.loads(raw)
            self.assertEqual(set(body), {str(i) for i in range(len(group))})
            self.assertEqual([body[str(i)].encode() for i in range(len(group))], [e.raw for e in group])

    def test_oversized_empty_and_mixed_sender_batches_fail(self):
        factory = q.Commands(2, 90)
        zod = factory.work(q.PROJECT, q.uuid('work', 9000))
        bus = factory.work(q.PROJECT, q.uuid('work', 9001), sender='bus')
        for group in ([], [zod] * 33, [zod, bus]):
            with self.assertRaises(ValueError):
                q.batch_value(group)
        large = [factory.document(q.uuid('document', 9000 + i), byte_length=32768) for i in range(2)]
        with self.assertRaises(ValueError):
            q.batch_value(large)
        self.assertEqual([len(group) for group in q.batches(large)], [1, 1])

    def test_resource_boundaries_include_creator_and_container_history_costs(self):
        self.assertEqual(len(self.resources['projects']['setup']), 0)
        self.assertEqual(len(self.resources['projects']['accepted']), 16)
        self.assertEqual(len(self.resources['work_items']['accepted']), 128)
        self.assertEqual(len(self.resources['grants']['setup']), 1)
        self.assertEqual(len(self.resources['grants']['accepted']), 127)
        self.assertEqual(self.resources['grants']['rejected'].command['expected_revision'], '128')
        docs = self.resources['documents']
        self.assertEqual(len({e.command['resource_id'] for e in docs['accepted']}), 32)
        self.assertNotIn(docs['rejected'].command['resource_id'], {e.command['resource_id'] for e in docs['accepted']})
        history = self.resources['history']
        self.assertEqual([int(e.command['expected_revision']) for e in history['accepted']], list(range(128)))
        self.assertEqual(history['rejected'].command['expected_revision'], '128')
        self.assertEqual({e.command['resource_id'] for e in history['accepted']}, {history['rejected'].command['resource_id']})

    def test_object_budget_recipe_has_unique_maximum_blobs_and_spare_other_limits(self):
        candidates = self.resources['object_bytes']['candidates']
        self.assertEqual(len(candidates), 254)
        self.assertEqual({e.sender for e in candidates}, {'zod', 'bus'})
        self.assertEqual(len({e.command['payload']['markdown'] for e in candidates}), 254)
        for sender in ('zod', 'bus'):
            own = [e.command for e in candidates if e.sender == sender]
            self.assertEqual(len(own), 127)
            self.assertEqual([int(c['expected_revision']) for c in own], list(range(127)))
            self.assertEqual(len({c['resource_id'] for c in own}), 1)
        self.assertTrue(all(len(e.command['payload']['markdown'].encode()) == 32768 for e in candidates))
        # Independent Git-format arithmetic, not native object admission. The
        # trusted fixture lifetime uses ten-digit Unix seconds. Two histories
        # still have room when the 253rd unique max-size blob exceeds8 MiB.
        total = 0
        for index, entry in enumerate(candidates):
            cmd = entry.command
            revision = int(cmd['expected_revision']) + 1
            identity = f'Stead Fixture <{q.PRINCIPALS[entry.sender]}@stead.invalid> 1789257600 +0000'
            body = 'tree ' + 'a' * 40 + '\n'
            if revision > 1:
                body += 'parent ' + 'b' * 40 + '\n'
            body += f'author {identity}\ncommitter {identity}\n\nSave {cmd["resource_id"]} revision {revision}\n'
            tree_bytes = len(b'100644 ') + len((cmd['resource_id'] + '.md').encode()) + 1 + 20
            total += 32768 + tree_bytes + len(body.encode())
            if index == 251:
                self.assertLessEqual(total, 8388608)
                self.assertGreater(total + 32768, 8388608)
            if index == 252:
                self.assertGreater(total, 8388608)

    def test_provenance_requires_exact_fixture_predecessor_and_manifest(self):
        actual = q.source_binding(FIXTURE)
        self.assertEqual(actual['predecessor_commit'], q.PREDECESSOR_COMMIT)
        self.assertEqual(actual['v1_corpus_sha256'], q.V1_CORPUS_SHA256)
        with self.assertRaisesRegex(ValueError, 'fixture bytes'):
            q.source_binding(FIXTURE + b'\n')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'lib').mkdir()
            (directory / 'lib/stead-core-v1.hoon').write_bytes(b'not the predecessor')
            with mock.patch.object(q, 'NATIVE', directory), self.assertRaisesRegex(ValueError, 'predecessor source changed'):
                q.source_binding(FIXTURE)
            (directory / 'contract-freeze.json').write_bytes(b'{}')
            with mock.patch.object(q, 'SPECS', directory), self.assertRaisesRegex(ValueError, 'Frozen manifest bytes changed'):
                q.source_binding(FIXTURE)


class QualificationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.call = mock.Mock()
        self.driver = q.Driver(self.call, 'host-scripted-adapter-test', {'test_only': True}, FIXTURE)
        self.entry = q.Commands(2, 90).project(q.PROJECT)

    def test_recovery_uses_document_container_or_project_scope_and_actual_sender(self):
        document = q.Commands(1, 91).document(q.uuid('document', 901), sender='bus')
        response = terminal({'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'})
        self.call.return_value = response
        for entry, override, sender, container in (
                (document, None, 'bus', q.CONTAINERS['bus']),
                (self.entry, None, 'zod', q.PROJECT),
                (self.entry, 'bus', 'bus', q.PROJECT)):
            with self.subTest(operation=entry.command['operation'], override=override):
                self.call.reset_mock()
                actual = self.driver.recover(entry, override)
                cmd = entry.command
                expected_route = (f"/v2/receipt/{cmd['project_id']}/{container}/"
                                  f"{cmd['resource_id']}/{cmd['operation']}/{cmd['request_id']}")
                self.call.assert_called_once_with(sender, 'read', expected_route, b'')
                self.assertEqual(actual, response)
                self.assertEqual(self.driver.report['calls'][-1]['route'], expected_route)
                self.assertEqual(self.driver.report['calls'][-1]['ship'], sender)

    def test_no_callback_or_provenance_keeps_all_native_recipes_unexecuted(self):
        binding = {'fixture_sha256': q.FIXTURE_SHA256, 'test_only': 'Isolate host status test from concurrent native source edits'}
        with mock.patch.object(q, 'source_binding', return_value=binding):
            for callback, provenance in ((None, {'source': 'declared'}), (self.call, None), (self.call, {})):
                report = q.run(callback, provenance=provenance,
                               classification='local-real-native-fake-ships', fixture_raw=FIXTURE)
                self.assertEqual(report['status'], 'not_run')
                self.assertFalse(report['native_qualified'])
                self.assertEqual(len(report['recipes']), 8)
                self.assertTrue(all(recipe['status'] == 'unexecuted' for recipe in report['recipes'].values()))
                self.assertTrue(report['pending'])
                self.assertEqual(report['checks'], [])
                self.assertEqual(report['calls'], [])
        self.call.assert_not_called()

    def test_missing_terminal_or_unframed_native_callback_cannot_qualify(self):
        binding = {'test_only': 'Stable source fixture'}
        with mock.patch.object(q, 'source_binding', return_value=binding):
            for result in (None, {}, {'raw': None, 'json': None}, terminal({})):
                self.call.return_value = result
                report = q.run(self.call, provenance={'test_only': True},
                    classification='local-real-native-fake-ships', fixture_raw=FIXTURE)
                self.assertEqual(report['status'], 'failed')
                self.assertFalse(report['native_qualified'])
                self.assertTrue(all(recipe['status'] == 'unexecuted' for recipe in report['recipes'].values()))

    def test_control_timeout_ack_or_missing_value_is_not_expected_nack(self):
        # Pinned native timeout shape observed in deliverycheck02: the stdout
        # is identical to a poke failure, so stdout alone is not a predicate.
        timeout = ('loom: mapped 512MB\nlite: arvo formula 4ce68411\n'
                   'lite: core 641296f\nlite: final state 641296f\n'
                   'eval (cue, newt):\ntimeout\neval: bail: %thread-fail')
        for result in (terminal({}), {'raw': None, 'json': None, 'native': {}},
                       {'raw': None, 'json': None, 'native': {'stdout': 'timeout'}},
                       {'raw': None, 'json': None, 'native': {'stdout': '[32 %avow 1]'}},
                       {'raw': None, 'json': None, 'native': {'stdout': '[32 %avow 1]', 'stderr': timeout}}):
            self.call.return_value = result
            with self.assertRaises(AssertionError):
                self.driver.control('load-bad-legacy', negative=True)
        # Host adapter fixture matching the observed core05 rejection hints;
        # this is not a newly executed native response.
        self.call.return_value = {'raw': None, 'json': None, 'native': {
            'stdout': '[32 %avow 1]',
            'stderr': 'stead-unsupported-state\npoke-fail\neval: bail: %thread-fail'}}
        self.driver.control('load-bad-legacy', negative=True)

    def test_load_rejection_requires_specific_context_and_no_timeout(self):
        good = 'stead-unsupported-state\npoke-fail\neval: bail: %thread-fail'
        for stderr in (good.replace('stead-unsupported-state', 'unrelated-hint'),
                       good.replace('poke-fail', 'watch-fail'),
                       good.replace('eval: bail: %thread-fail', 'different-terminal'),
                       good.replace('poke-fail', 'poke-fail\ntimeout'), None):
            with self.subTest(stderr=stderr):
                self.call.return_value = {'raw': None, 'json': None, 'native': {
                    'stdout': '[32 %avow 1]', 'stderr': stderr}}
                with self.assertRaises(AssertionError):
                    self.driver.control('load-bad-legacy', negative=True)
        self.call.return_value = {'raw': 'unexpected body', 'json': None, 'native': {
            'stdout': '[32 %avow 1]', 'stderr': good}}
        with self.assertRaises(AssertionError):
            self.driver.control('load-bad-legacy', negative=True)

    def test_only_private_full_load_controls_get_bulk_wait(self):
        for operation in ('migrate-legacy', 'load-bad-legacy', 'legacy-batch',
                          'native-batch', 'profile', 'roundtrip', 'load-future'):
            with self.subTest(operation=operation):
                self.call.reset_mock()
                self.call.return_value = terminal({})
                self.driver.control(operation)
                kwargs = {'timeout': 620} if operation in ('migrate-legacy', 'load-bad-legacy') else {}
                self.call.assert_called_once_with('zod', 'control', '/', b'',
                    control=(operation, 'zod', '', ''), **kwargs)

    def test_inconsistent_oversized_and_wrong_json_fail(self):
        for result in ({'raw': '{}', 'json': {'status': 'accepted'}},
                       {'raw': ' ' * 262145, 'json': {}}, {'raw': 'invalid', 'json': {}},
                       {'raw': '{"status":"rejected","status":"accepted"}', 'json': {'status': 'accepted'}}):
            self.call.return_value = result
            with self.assertRaises((AssertionError, ValueError)):
                self.driver.invoke('zod', 'read')

    def test_embedded_batch_response_rejects_duplicate_fields(self):
        response = json.dumps(scripted_receipt(self.entry)).replace('{', '{"status":"rejected",', 1)
        self.call.side_effect = [terminal({}), terminal({'protocol': 'stead.fixture-predecessor/1', 'response': response})]
        with mock.patch.object(self.driver, 'snapshot', side_effect=[snapshot(), snapshot(journal_events='1', receipts='1')]), \
             self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.driver.apply_batch([self.entry])

    def test_driver_hashes_large_callback_bodies_instead_of_copying_them(self):
        value = {'body': 'x' * 32768}
        result = terminal(value)
        self.call.return_value = result
        self.driver.invoke('zod', 'read')
        record = self.driver.report['calls'][-1]
        self.assertEqual(record['response_utf8_sha256'], hashlib.sha256(result['raw'].encode()).hexdigest())
        self.assertEqual(record['response_bytes'], len(result['raw'].encode()))
        self.assertLess(len(json.dumps(record)), 2048)
        self.assertNotIn('result', record)

    def test_capacity_negative_changes_transport_identity_without_changing_command(self):
        denial = {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'}
        with mock.patch.object(self.driver, 'snapshot', return_value=snapshot()), \
             mock.patch.object(self.driver, 'direct', return_value=denial) as direct:
            self.driver.denied_without_change(self.entry)
        sent = direct.call_args.args[0]
        self.assertEqual(sent.sender, 'bud')
        self.assertEqual(sent.raw, self.entry.raw)
        self.assertEqual(sent.digest, self.entry.digest)

    def watch_rejection(self):
        # Host fixture matching the actual capacity01 missing-binding terminal.
        return {'raw': None, 'json': None, 'native': {'stdout': '[32 %avow 1]',
            'stderr': 'stead-watch-denied\nwatch-ack\nwatch-ack-fail\neval: bail: %thread-fail'}}

    def test_missing_binding_requires_real_poke_and_explicit_final_gate_denial(self):
        before = snapshot()
        missing = snapshot(bindings_sha256='1' * 64, state_jam_sha256='1' * 64)
        denial = {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'}
        with mock.patch.object(self.driver, 'snapshot', side_effect=[before, missing, missing, missing, before]), \
             mock.patch.object(self.driver, 'control') as control, \
             mock.patch.object(self.driver, 'command', return_value=self.watch_rejection()) as command, \
             mock.patch.object(self.driver, 'invoke', return_value=terminal({})) as poke, \
             mock.patch.object(self.driver, 'apply_batch', return_value=(denial, missing)) as batch:
            self.driver.missing_binding_at_capacity(self.entry)
        probe = command.call_args.args[0]
        self.assertEqual((probe.sender, probe.raw, probe.digest), ('bus', self.entry.raw, self.entry.digest))
        poke.assert_called_once_with('bus', 'poke', raw=self.entry.raw)
        batch.assert_called_once_with([probe], accepted=False, expected_error='denied_or_not_found')
        self.assertEqual(control.call_args_list, [mock.call('binding-drop', sender='bus'),
                                                 mock.call('binding-restore', sender='bus')])

    def test_missing_binding_watch_timeout_or_unrelated_failure_cannot_qualify(self):
        missing = snapshot(bindings_sha256='1' * 64)
        good = self.watch_rejection()
        variants = [terminal({}), terminal({'status': 'rejected'}), {'raw': None, 'json': None, 'native': {}},
                    {**good, 'raw': 'unexpected body'}]
        for hint in ('stead-watch-denied', 'watch-ack', 'watch-ack-fail', 'eval: bail: %thread-fail'):
            variants.append({**good, 'native': {**good['native'],
                'stderr': '\n'.join(line for line in good['native']['stderr'].splitlines() if line != hint)}})
        variants.append({**good, 'native': {**good['native'],
            'stderr': 'timeout\n' + good['native']['stderr']}})
        for response in variants:
            with self.subTest(response=response), \
                 mock.patch.object(self.driver, 'snapshot', side_effect=[snapshot(), missing, snapshot()]), \
                 mock.patch.object(self.driver, 'control') as control, \
                 mock.patch.object(self.driver, 'command', return_value=response), \
                 mock.patch.object(self.driver, 'invoke') as poke, \
                 mock.patch.object(self.driver, 'apply_batch') as batch, \
                 self.assertRaisesRegex(AssertionError, 'missing-binding-result-watch-specifically-denied'):
                self.driver.missing_binding_at_capacity(self.entry)
            poke.assert_not_called()
            batch.assert_not_called()
            self.assertEqual(control.call_args_list[-1], mock.call('binding-restore', sender='bus'))

    def test_missing_binding_poke_business_body_or_mutation_cannot_qualify(self):
        missing = snapshot(bindings_sha256='1' * 64)
        for ack, after in ((terminal({'status': 'accepted'}), missing),
                           (terminal({}), {**missing, 'receipts': '1'})):
            snapshots = [snapshot(), missing, missing] + ([after] if ack['json'] == {} else []) + [snapshot()]
            with self.subTest(ack=ack, after=after), \
                 mock.patch.object(self.driver, 'snapshot', side_effect=snapshots), \
                 mock.patch.object(self.driver, 'control') as control, \
                 mock.patch.object(self.driver, 'command', return_value=self.watch_rejection()), \
                 mock.patch.object(self.driver, 'invoke', return_value=ack), \
                 mock.patch.object(self.driver, 'apply_batch') as batch, self.assertRaises(AssertionError):
                self.driver.missing_binding_at_capacity(self.entry)
            batch.assert_not_called()
            self.assertEqual(control.call_args_list[-1], mock.call('binding-restore', sender='bus'))

    def test_missing_binding_final_gate_or_transport_failure_restores_binding(self):
        missing = snapshot(bindings_sha256='1' * 64)
        denial = {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'}
        for failure in (RuntimeError('transport failed'),
                        ({**denial, 'error': 'capacity_exceeded'}, missing),
                        (denial, {**missing, 'journal_events': '1'})):
            with self.subTest(failure=failure), \
                 mock.patch.object(self.driver, 'snapshot', side_effect=[snapshot(), missing, missing, missing, snapshot()]), \
                 mock.patch.object(self.driver, 'control') as control, \
                 mock.patch.object(self.driver, 'command', return_value=self.watch_rejection()), \
                 mock.patch.object(self.driver, 'invoke', return_value=terminal({})), \
                 mock.patch.object(self.driver, 'apply_batch') as batch, self.assertRaises((AssertionError, RuntimeError)):
                if isinstance(failure, Exception):
                    batch.side_effect = failure
                else:
                    batch.return_value = failure
                self.driver.missing_binding_at_capacity(self.entry)
            self.assertEqual(control.call_args_list[-1], mock.call('binding-restore', sender='bus'))

    def test_missing_binding_not_removed_or_not_restored_cannot_qualify(self):
        before = snapshot()
        missing = snapshot(bindings_sha256='1' * 64)
        denial = {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'}
        for snapshots, failure in (([before, before, before], 'fixture-removed-current-contributor-binding'),
                                   ([before, missing, missing, missing, missing], 'exact-binding-restored')):
            with self.subTest(failure=failure), \
                 mock.patch.object(self.driver, 'snapshot', side_effect=snapshots), \
                 mock.patch.object(self.driver, 'control') as control, \
                 mock.patch.object(self.driver, 'command', return_value=self.watch_rejection()), \
                 mock.patch.object(self.driver, 'invoke', return_value=terminal({})), \
                 mock.patch.object(self.driver, 'apply_batch', return_value=(denial, missing)), \
                 self.assertRaisesRegex(AssertionError, failure):
                self.driver.missing_binding_at_capacity(self.entry)
            self.assertEqual(control.call_args_list[-1], mock.call('binding-restore', sender='bus'))

    def test_receipt_must_match_version_identity_scope_and_closed_fields(self):
        good = scripted_receipt(self.entry)
        self.driver.receipt(good, self.entry)
        variants = [dict(good, protocol='stead.receipt/1'), dict(good, binding_id=q.BINDINGS['bus']),
                    dict(good, authority_epoch='2'), dict(good, container_id=q.PROJECT),
                    dict(good, journal_sequence='55'), dict(good, unknown_private_field='secret'),
                    dict(good, resource_kind='work')]
        for value in variants:
            with self.assertRaises(AssertionError):
                self.driver.receipt(value, self.entry)
        old = q.Commands(1, 91).project(q.PROJECT)
        self.driver.receipt(scripted_receipt(old, True), old, predecessor=True)
        with self.assertRaises(AssertionError):
            self.driver.receipt(scripted_receipt(old, True), old)

    def test_batch_ack_and_last_receipt_do_not_prove_all_commands_committed(self):
        response = scripted_receipt(self.entry)
        self.call.side_effect = [terminal({}), terminal({'protocol': 'stead.fixture-predecessor/1',
                                                        'response': json.dumps(response)})]
        with mock.patch.object(self.driver, 'snapshot', side_effect=[snapshot(), snapshot()]), self.assertRaisesRegex(
                AssertionError, 'all-batch-commands-created-one-journal-and-receipt'):
            self.driver.apply_batch([self.entry])
        self.assertEqual(self.call.call_args_list[0].kwargs['control'][0:3], ('native-batch', 'zod', 'all'))

    def test_wrong_refusal_and_any_state_counter_or_digest_change_fail(self):
        denial = {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'capacity_exceeded'}
        self.call.side_effect = [terminal({}), terminal({'protocol': 'stead.fixture-predecessor/1',
                                                        'response': json.dumps(denial)})]
        with mock.patch.object(self.driver, 'snapshot', side_effect=[snapshot(), snapshot(objects='1')]), self.assertRaisesRegex(
                AssertionError, 'refusal-preserves-all-authoritative-state'):
            self.driver.apply_batch([self.entry], accepted=False)
        for changed in ({'ordinary_count': '1'}, {'security_counts': {q.PROJECT: '1'}},
                        {'journal_sha256': 'f' * 64}, {'revisions': {'work/synthetic': '1'}}):
            with self.assertRaises(AssertionError):
                self.driver.unchanged(snapshot(), snapshot(**changed), 'scripted-state-change')
        self.call.side_effect = [terminal({}), terminal({'protocol': 'stead.fixture-predecessor/1',
                                                        'response': json.dumps(denial)})]
        with mock.patch.object(self.driver, 'snapshot', return_value=snapshot()), self.assertRaisesRegex(
                AssertionError, 'exact-native-refusal:denied_or_not_found'):
            self.driver.apply_batch([self.entry], accepted=False, expected_error='denied_or_not_found')

    def test_before_after_source_change_cannot_leave_a_pass_or_pending_claim(self):
        with mock.patch.object(q, 'source_binding', side_effect=[{'source': 'a'}, {'source': 'b'}]):
            report = q.run(fixture_raw=FIXTURE)
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['native_qualified'])
        self.assertIn('changed during execution', report['error'])

    def test_missing_fixture_and_zero_executed_recipes_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(q, 'SPECS', Path(tmp)):
            report = q.run()
        self.assertEqual(report['status'], 'failed')
        self.assertIn('FileNotFoundError', report['error'])
        self.assertFalse(report['native_qualified'])
        with mock.patch.object(q, 'source_binding', return_value={'test_only': 'Stable source fixture'}), \
             mock.patch.object(q.Driver, 'predecessor_privacy'), mock.patch.object(q.Driver, 'exhaustion'), \
             mock.patch.object(q.Driver, 'resource_boundaries'):
            report = q.run(self.call, provenance={'test_only': True},
                classification='local-real-native-fake-ships', fixture_raw=FIXTURE)
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['native_qualified'])
        self.assertIn('all-eight-planned-recipes-executed', report['error'])
        self.call.assert_not_called()

    def test_snapshots_require_nonambiguous_canonical_derived_counters(self):
        for value in (snapshot(ordinary_count=None), snapshot(ordinary_count='01'),
                      snapshot(security_counts=None), snapshot(security_counts={q.PROJECT: '-1'}),
                      snapshot(revisions=None), snapshot(state_jam_sha256='unknown')):
            self.call.return_value = terminal(value)
            with self.assertRaises((AssertionError, ValueError)):
                self.driver.snapshot()


if __name__ == '__main__':
    unittest.main()

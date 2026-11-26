"""Inert controller checks. Synthetic clocks/transport are never T06 metrics."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('storage_workload_tested', ROOT / 'scripts/urbit/storage_workload.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def config():
    return {'home': '~zod', 'custody': 'local-disposable', 'runtime': 'isolated-fake',
        'organization_id': S.uid(5), 'team_id': S.uid(6),
        'bindings': {'~bus': {'principal_id': S.uid(102), 'binding_id': S.uid(202),
            'binding_revision': '1', 'active': 'yes'}, '~nec': {}},
        'project_creators': {S.uid(102): 'yes'}}


class Transport:
    """Small protocol double, not the native reducer or a performance model."""
    def __init__(self, corrupt=None):
        self.calls, self.works, self.docs, self.comments, self.projects = [], {}, {}, {}, set()
        self.corrupt = corrupt

    def __call__(self, ship, mode, q):
        self.calls.append((ship, mode, deepcopy(q)))
        if ship != 'bus': raise AssertionError('No fixture actor substitution')
        if mode == 'command':
            op, key = q['operation'], (q['project_id'], q['resource_id'])
            revision = int(q['expected_revision']) + 1
            if op == 'project.create': self.projects.add(key[0])
            elif op == 'work.create':
                self.works[key] = dict(q['payload'], resource_id=key[1], resource_revision=str(revision))
            elif op == 'work.comment':
                self.comments.setdefault(key, []).append({'body': q['payload']['body'],
                    'comment_revision': str(revision), 'principal_id': S.uid(102),
                    'identity_ship': '~bus', 'accepted_at_ms': '1000'})
                self.works[key]['resource_revision'] = str(revision)
            elif op == 'document.save':
                self.docs[key] = {'resource_id': key[1], 'resource_revision': str(revision),
                                 'markdown': q['payload']['markdown']}
            elif op != 'container.create': raise AssertionError(op)
            result = {'protocol': 'stead.receipt/3', 'status': 'accepted',
                'request_id': q['request_id'], 'canonical_sha256': S.sha(b'stead.command/3\0' + S.canonical(q)),
                'project_id': q['project_id'], 'resource_id': q['resource_id'],
                'resource_kind': op.split('.')[0],
                'container_id': q['resource_id'] if op == 'container.create' else q['payload'].get('container_id', ''),
                'resource_revision': str(revision), 'authority_epoch': '1', 'operation': op,
                'principal_id': S.uid(102), 'binding_id': S.uid(202), 'binding_revision': '1',
                'identity_ship': '~bus', 'authentication': 'native-sender/1',
                'authentication_strength': 'native-sender', 'session_audit_id': '', 'runtime': 'isolated-fake',
                'accepted_at_ms': '1000', 'git_commit_oid': 'a' * 40 if op == 'document.save' else ''}
        else:
            kind, key = q['kind'], (q['project_id'], q['resource_id'])
            cursor = ''
            if kind == 'projects': records = [{'resource_id': p} for p in sorted(self.projects)]
            elif kind == 'comments': records = self.comments[key]
            elif kind == 'document': records = [self.docs[key]]
            elif kind == 'work' and key[1]: records = [self.works[key]]
            elif kind == 'work':
                records = [v for (p, _), v in sorted(self.works.items()) if p == key[0]]
                if q['cursor']: records = records[20:]
                else: records, cursor = records[:20], 'c' * 64
            else: raise AssertionError(kind)
            result = {'protocol': 'stead.query-result/3', 'status': 'read',
                **{k: q[k] for k in ('request_id', 'kind', 'project_id', 'container_id', 'resource_id')},
                'authority_epoch': '1' if q['project_id'] else '0', 'generation': 'b' * 64,
                'cursor': cursor, 'rows': {str(i): deepcopy(row) for i, row in enumerate(records)}}
        if self.corrupt: self.corrupt(mode, q, result)
        return result


def run(transport, *, value=None):
    ticks = [0]
    snapshots = []
    def clock():
        ticks[0] += 100
        return ticks[0]
    def checkpoint(row): snapshots.append(deepcopy(row))
    try:
        return S.run(call=transport, config=value or config(), guard=lambda: None,
            sample=lambda: {'inert_host_test': True}, checkpoint=checkpoint, clock=clock), snapshots
    except BaseException as error:
        error.inert_snapshots = snapshots
        raise


class StorageWorkloadTests(unittest.TestCase):
    def test_exact_fixed_workload_scopes_revisions_readbacks_and_cursor_boundary(self):
        transport = Transport()
        report, checkpoints = run(transport)
        self.assertEqual(report['status'], 'pass')
        self.assertIs(report['qualifies_phase'], False)
        self.assertEqual(report['workload'], {'projects': 2, 'work_per_project': 32,
            'docs_per_project': 8, 'comments_per_work': 4, 'document_edits_after_create': 4})
        self.assertEqual((report['accepted_writes'], report['verified_readbacks']), (404, 208))
        self.assertEqual(len(transport.calls), 617)
        self.assertEqual(len({q['request_id'] for _, _, q in transport.calls}), 617)
        counts = {}
        for _, mode, q in transport.calls:
            if mode == 'command': counts[q['operation']] = counts.get(q['operation'], 0) + 1
        self.assertEqual(counts, {'project.create': 2, 'work.create': 64, 'work.comment': 256,
                                  'container.create': 2, 'document.save': 80})
        self.assertEqual(len(transport.works), 64)
        self.assertEqual(len(transport.docs), 16)
        self.assertTrue(all(row['resource_revision'] == '5' for row in transport.works.values()))
        self.assertTrue(all(row['resource_revision'] == '5' for row in transport.docs.values()))
        self.assertEqual([p['rows'] for p in report['pages']], [[20, 12], [20, 12]])
        self.assertEqual(len(report['resources']), 4)
        self.assertTrue(all(r['observed'] == {'inert_host_test': True} for r in report['resources']))
        self.assertEqual(report['latency']['command']['samples'], 404)
        self.assertEqual(report['latency']['query']['samples'], 213)
        self.assertEqual(report['latency']['document.save']['samples'], 80)
        self.assertEqual(report['latency']['command']['p95_ns'], 100)
        self.assertEqual(checkpoints[-1], report)
        raw = S.canonical({'protocol': 'inert-original'})
        result = {'response_frame_hex': b'frame'.hex(), 'response_frame_sha256': S.sha(b'frame'),
                  'outcome': {'raw': raw.decode(), 'json': {'protocol': 'inert-original'}},
                  'stdout': 'duplicate rendered output is not retained', 'request': 'duplicate request'}
        retained = S.transport_record(result, 'bus', 'query', b'{}', '/v3/result/inert')
        self.assertEqual(retained['outcome_raw'].encode(), raw)
        self.assertEqual(bytes.fromhex(retained['response_frame_hex']), b'frame')
        self.assertNotIn('stdout', retained)
        self.assertNotIn('request', retained)
        self.assertEqual(S.MAX_TRANSPORT_BYTES, 2097152)

    def test_wrong_actor_receipt_scope_or_exact_body_never_counts_as_measurement_success(self):
        def wrong_receipt(mode, q, result):
            if mode == 'command': result['principal_id'] = S.uid(103)
        def wrong_request(mode, q, result):
            if mode == 'query' and q['kind'] == 'work': result['request_id'] = S.uid(999)
        def changed_body(mode, q, result):
            if mode == 'query' and q['kind'] == 'document': result['rows']['0']['markdown'] += 'changed'
        for corruption in (wrong_receipt, wrong_request, changed_body):
            with self.subTest(corruption=corruption.__name__), self.assertRaises(ValueError) as refused:
                run(Transport(corruption))
            partial = refused.exception.inert_snapshots[-1]
            self.assertEqual(partial['status'], 'fail')
            self.assertIsNone(partial['latency'])
            self.assertEqual(partial['error_class'], 'ValueError')
        live = config(); live.update(custody='operator-pilot', runtime='live-synthetic')
        transport = Transport()
        with self.assertRaises(ValueError): run(transport, value=live)
        self.assertEqual(transport.calls, [])
        raw = S.canonical({'status': 'read'})
        exact = {'response_frame_hex': b'frame'.hex(), 'response_frame_sha256': S.sha(b'frame'),
                 'outcome': {'raw': raw.decode(), 'json': {'status': 'read'}}}
        for change in ({'response_frame_sha256': '0' * 64}, {'response_frame_hex': '00'},
                       {'outcome': {'raw': raw.decode(), 'json': {'status': 'accepted'}}}):
            with self.assertRaises(ValueError):
                S.transport_record(exact | change, 'bus', 'query', b'{}', '/v3/result/inert')

    def test_native_storage_requires_exact_observed_counts_and_canonical_atom(self):
        row = {'protocol': 'stead.storage-observation/1', 'saved_version': '3',
            'vase_bytes': '100', 'payload_bytes': '90', 'journal_bytes': '40', 'receipt_bytes': '30',
            'object_bytes': '20', 'objects': '7', 'projects': '2', 'work_items': '64',
            'documents': '16', 'comments': '256', 'journal_events': '404', 'receipts': '404',
            'saved_vase_sha256': 'a' * 64}
        atom = lambda data: hex(int.from_bytes(data, 'little'))
        self.assertEqual(S.native_observation(atom(S.canonical(row))), row)
        for key, value in (('journal_events', '403'), ('receipts', '405'), ('saved_version', '10'),
                           ('comments', True), ('saved_vase_sha256', 'bad'), ('extra', 'raw noun')):
            bad = dict(row); bad[key] = value
            with self.assertRaises(ValueError): S.native_observation(atom(S.canonical(bad)))
        with self.assertRaises(ValueError): S.native_observation(atom(S.canonical(row) + b' '))
        for malformed in ('', '%.y', '0x', '0x' + 'a' * 16384):
            with self.assertRaises(ValueError): S.native_observation(malformed)

    def test_percentiles_and_deadlines_do_not_fabricate_success_or_accept_boolean_numbers(self):
        self.assertEqual(S.distribution([4, 1, 3, 2]), {'samples': 4, 'minimum_ns': 1,
            'maximum_ns': 4, 'p50_ns': 2, 'p95_ns': 4})
        for values in ([], [True], [-1], [1.0], [0] * (S.MAX_CALLS + 1)):
            with self.assertRaises(ValueError): S.distribution(values)
        ticks = iter((0, S.MAX_SECONDS * 1000000000, S.MAX_SECONDS * 1000000000))
        transport, saved = Transport(), []
        with self.assertRaises(ValueError):
            S.run(call=transport, config=config(), guard=lambda: None, sample=lambda: {},
                  checkpoint=lambda value: saved.append(deepcopy(value)), clock=lambda: next(ticks))
        self.assertEqual(transport.calls, [])
        self.assertEqual(saved[-1]['status'], 'fail')
        self.assertIsNone(saved[-1]['latency'])
        self.assertEqual(saved[-1]['samples'], [])

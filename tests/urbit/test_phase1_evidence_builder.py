"""Host-only evidence reader tests. Authored records are NOT native execution."""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import build_phase1_evidence as B


def authored(value=None, *, change_record=None, change_summary=None):
    """Small format fixture, explicitly never presented as observed evidence."""
    value = B.QA.DENIAL if value is None else value
    raw = B.QA.canonical(value).decode()
    request = B.command_source('read', '/v2/project/authored')
    record = {'ship': 'bus', 'mode': 'read', 'route': '/v2/project/authored',
              'input_sha256': B.sha(b''), 'input_bytes': 0,
              'request': request, 'response_frame_sha256': '1' * 64,
              'stdout': "[32 %avow 0 %noun %stead-core-result '" + raw.encode().hex() + "']",
              'stderr': '', 'outcome': {'raw': raw, 'json': value}}
    if change_record:
        change_record(record)
    line = (json.dumps(record, separators=(',', ':')) + '\n').encode()
    compressed = gzip.compress(line, mtime=0)
    ref = {'artifact': 'authored.jsonl.gz', 'line': 1, 'record_sha256': B.sha(line), 'record_bytes': len(line)}
    summary = {key: record[key] for key in ('ship', 'mode', 'route', 'input_sha256', 'input_bytes',
                                          'response_frame_sha256', 'stdout', 'stderr')}
    summary.update(transcript=ref, request_sha256=B.sha(record['request'].encode()))
    if change_summary:
        change_summary(summary)
    report = {'status': 'AUTHORED_NOT_NATIVE', 'commands': [summary],
              'transport_artifact': {'file': ref['artifact'], 'encoding': 'gzip-jsonl',
                 'records': 1, 'uncompressed_bytes': len(line), 'uncompressed_sha256': B.sha(line),
                 'sha256': B.sha(compressed)}}
    raw_report = B.encoded(report)
    artifacts = {'authored/report.json': raw_report, 'authored/authored.jsonl.gz': compressed}
    return report, B.reference('authored/report.json', raw_report), artifacts


def authored_export():
    """An in-memory Git/native record format fixture, never execution evidence."""
    project = '019939ba-4000-7000-8000-000000000001'
    container = '019939ba-4000-7000-8000-000000000004'
    filename = '019939ba-4000-7000-8000-000000000401.md'
    cwd = '/state/logs/core-export-20260925T000000Z-1'
    blob = b'Authored host fixture only.\n'
    oid = lambda kind, body: B.hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest()
    blob_id = oid('blob', blob)
    tree = b'100644 ' + filename.encode() + b'\0' + bytes.fromhex(blob_id)
    tree_id = oid('tree', tree)
    commit = (f'tree {tree_id}\nauthor Fixture <fixture@stead.invalid> 1 +0000\n'
              'committer Fixture <fixture@stead.invalid> 1 +0000\n\nAuthored fixture\n').encode()
    head = oid('commit', commit)
    materials = [(head, 'commit', commit), (tree_id, 'tree', tree), (blob_id, 'blob', blob)]
    objects = {key: {'kind': kind, 'byte_length': len(body), 'hex': body.hex()} for key, kind, body in materials}

    def response(route, payload):
        value = {'protocol': 'stead.result/2', 'status': 'read', 'project_id': project,
                 'resource_id': container, 'resource_revision': '1', 'payload': payload}
        return {'raw': B.QA.canonical(value).decode(), 'json': value,
                'native': {'ship': 'bus', 'mode': 'read', 'route': route}}

    native = [response(f'/v2/git/{project}/{container}', {'snapshot_commit_oid': head,
                        'objects': {key: value['kind'] for key, value in objects.items()}})]
    native += [response(f'/v2/git-object/{project}/{container}/{head}/{key}',
        {'oid': key, 'snapshot_commit_oid': head, 'kind': kind,
         'byte_length': str(len(body)), 'hex': body.hex()}) for key, kind, body in materials]

    def git(args, output=''):
        return {'argv': ['git', '-C', cwd, *args], 'returncode': 0, 'stdout': output, 'stderr': ''}

    commands = [git(['init', '--bare', '--template='], f'Initialized empty Git repository in {cwd}/\n')]
    commands += [git(['hash-object', '-w', '-t', kind, '--stdin'], key + '\n') for key, kind, _ in materials]
    commands += [git(['symbolic-ref', 'HEAD', 'refs/heads/main']), git(['update-ref', 'refs/heads/main', head])]
    fsck = git(['fsck', '--full', '--strict'])
    commands += [fsck, git(['ls-tree', '-rz', head], f'100644 blob {blob_id}\t{filename}\0'),
                 git(['cat-file', 'blob', blob_id], blob.decode())]
    return {'native': native, 'objects': objects, 'snapshot_commit_oid': head,
            'files': {filename: {'oid': blob_id, 'hex': blob.hex()}}, 'fsck': fsck,
            'git_commands': commands, 'max_response_bytes': max(len(row['raw'].encode()) for row in native)}, \
        ('bus', project, container, None, cwd)


class BuilderTests(unittest.TestCase):
    def test_exact_bytes_resolve_and_business_denial_is_preserved(self):
        report, ref, files = authored()
        report['status'] = 'passed'  # This label does not make a denied result accepted.
        retained = B.Retained(report, ref, files.__getitem__)
        response = B.Replay(retained).call('bus', 'read', '/v2/project/authored')
        self.assertEqual(B.QA.DENIAL, response['json'])
        self.assertEqual(0, retained.bind_response(response))

    def test_edited_sibling_business_response_rejected(self):
        report, ref, files = authored()
        retained = B.Retained(report, ref, files.__getitem__)
        response = retained.response(0)
        response.update(raw='{"status":"accepted"}', json={'status': 'accepted'})
        with self.assertRaisesRegex(ValueError, 'exact native command outcome'):
            retained.bind_response(response)

    def test_edited_native_outcome_cannot_override_terminal_bytes(self):
        report, ref, files = authored(change_record=lambda row: row['outcome'].update(json={'status': 'accepted'}))
        with self.assertRaisesRegex(ValueError, 'native terminal'):
            B.Retained(report, ref, files.__getitem__)

    def test_request_bytes_cannot_be_replaced_by_a_matching_input_hash(self):
        report, ref, files = authored(change_record=lambda row: row.update(request=B.command_source('read', '/wrong')))
        retained = B.Retained(report, ref, files.__getitem__)
        with self.assertRaisesRegex(ValueError, 'Missing exact retained exchange'):
            B.Replay(retained).call('bus', 'read', '/v2/project/authored')

    def test_wrong_actor_and_missing_call_fail(self):
        report, ref, files = authored()
        retained = B.Retained(report, ref, files.__getitem__)
        replay = B.Replay(retained)
        with self.assertRaises(ValueError):
            replay.call('bud', 'read', '/v2/project/authored')
        replay.call('bus', 'read', '/v2/project/authored')
        with self.assertRaises(ValueError):
            replay.call('bus', 'read', '/v2/project/authored')

    def test_transcript_hash_and_summary_tampering_fail(self):
        report, ref, files = authored()
        files['authored/authored.jsonl.gz'] += b'x'
        with self.assertRaisesRegex(ValueError, 'compressed digest'):
            B.Retained(report, ref, files.__getitem__)
        report, ref, files = authored(change_summary=lambda row: row.update(ship='bud'))
        with self.assertRaisesRegex(ValueError, 'summary differs'):
            B.Retained(report, ref, files.__getitem__)

    def test_duplicate_native_reference_is_not_two_exchanges(self):
        report, ref, files = authored()
        report['commands'].append(copy.deepcopy(report['commands'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate native command'):
            B.Retained(report, ref, files.__getitem__)

    def test_scope_and_route_are_part_of_exact_control_request(self):
        good = B.command_source('control', control=('profile', 'bus', 'runtime', 'isolated-fake'))
        changed = B.command_source('control', control=('profile', 'bud', 'runtime', 'isolated-fake'))
        self.assertNotEqual(good, changed)
        with self.assertRaises(ValueError):
            B.command_source('read', '/bad [literal]')
        with self.assertRaises(ValueError):
            B.command_source('poke', raw=b'bad\0')

    def test_only_exact66_native_requirements_are_mapped(self):
        corpus = B.decode((ROOT / 'specs/urbit/fixtures/native-cases-v2.json').read_bytes())
        manifest = B.decode((ROOT / 'specs/urbit/v2/qualification-gate.json').read_bytes())
        mapping = B.requirement_groups(corpus)
        actual = {row['id'] for row in manifest['required'] if row['kind'] == 'native'}
        delivery = {name for name in actual if name.startswith('delivery:')}
        self.assertEqual(66, len(actual))
        self.assertEqual(22, len(delivery))
        self.assertEqual(actual - delivery, set(mapping))
        self.assertEqual(['schedule/late-old-leave'], mapping['delivery-late-old-leave'])
        self.assertNotIn('no-effect-subsystem', mapping)
        self.assertNotIn('receipt-lookup-order', mapping)
        corpus['ordered_cases'].pop()
        with self.assertRaises(ValueError):
            B.requirement_groups(corpus)

    def test_restart_cannot_be_inferred_from_pid_labels(self):
        with self.assertRaisesRegex(ValueError, 'actual process launches'):
            B.lifecycle({'lifecycle': []}, {'old_pid': 1, 'old_exit': 0, 'replacement_pid': 2})
        rows = [{'command': 'launch zod', 'result': {'pid': 1}},
                {'command': 'shutdown zod', 'result': {'exit_code': 0, 'forced': True}},
                {'command': 'launch zod', 'result': {'pid': 2}}]
        with self.assertRaisesRegex(ValueError, 'graceful native shutdown'):
            B.lifecycle({'lifecycle': rows}, {'old_pid': 1, 'old_exit': 0, 'replacement_pid': 2})

    def test_wait_needs_real_authority_clock_and_exact_observation(self):
        report, ref, files = authored()
        replay = B.Replay(B.Retained(report, ref, files.__getitem__))
        with self.assertRaises(ValueError):
            replay.wait(100, {'deadline_ms': 100, 'now_ms': 101, 'elapsed_seconds': 1})
        with self.assertRaises(ValueError):
            replay.wait(100, {'deadline_ms': 99, 'now_ms': 101, 'elapsed_seconds': 1})

    def test_evaluator_hash_labels_without_actual_bytes_reject(self):
        with self.assertRaises((ValueError, KeyError)):
            B.evaluator_facts({'evaluator_controls': {'status': 'passed', 'large_frame_bytes': 70000,
                 'large_frame_sha256': 'a' * 64}, 'commands': []}, B.reference('authored.json', b'{}'))

    def test_cli_never_overwrites_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'kept').mkdir()
            sentinel = root / 'kept/raw.json'
            sentinel.write_bytes(b'original raw bytes')
            with patch.object(B, 'build', side_effect=AssertionError('must reject before any derivation')):
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    B.main(['--root', str(root), '--core', 'c', '--schedule', 's', '--core-guard', 'cg',
                            '--schedule-guard', 'sg', '--output-dir', 'kept'])
            self.assertEqual(b'original raw bytes', sentinel.read_bytes())

    def test_export_reconstructs_actual_maximum_and_git_materialization(self):
        value, context = authored_export()
        original = copy.deepcopy(value)
        with patch.object(B.subprocess, 'run', side_effect=AssertionError('must not run stock Git')):
            actual = B.export_records(value, *context)
        self.assertEqual(original, actual)
        self.assertEqual(original, value)
        self.assertEqual(max(len(row['raw'].encode()) for row in value['native']), actual['max_response_bytes'])

    def test_export_rejects_metadata_git_context_and_output_substitution(self):
        def fake_fsck(value):
            record = {'argv': ['git', '--version', 'fsck', '--full', '--strict'],
                      'returncode': 0, 'stdout': '', 'stderr': ''}
            value['git_commands'][-3] = record
            value['fsck'] = record

        mutations = {
            'false byte maximum': lambda value: value.update(max_response_bytes=1),
            'version masquerading as fsck': fake_fsck,
            'other repository': lambda value: value['git_commands'][0]['argv'].__setitem__(2, '/state/logs/other'),
            'wrong materialized object': lambda value: value['git_commands'][1].update(stdout='0' * 40 + '\n'),
            'wrong object kind': lambda value: value['git_commands'][1]['argv'].__setitem__(6, 'blob'),
            'missing object write': lambda value: value['git_commands'].pop(1),
            'wrong HEAD': lambda value: value['git_commands'][-5]['argv'].__setitem__(-1, 'refs/heads/other'),
            'wrong ref OID': lambda value: value['git_commands'][-4]['argv'].__setitem__(-1, '0' * 40),
            'wrong tree listing': lambda value: value['git_commands'][-2].update(stdout='unrelated\0'),
            'wrong blob output': lambda value: value['git_commands'][-1].update(stdout='unrelated bytes'),
            'failed stock Git': lambda value: value['git_commands'][-3].update(returncode=1),
            'unrelated claimed head': lambda value: value.update(snapshot_commit_oid='0' * 40),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                value, context = authored_export()
                mutate(value)
                before = copy.deepcopy(value)
                with self.assertRaises(ValueError):
                    B.export_records(value, *context)
                self.assertEqual(before, value, 'Contradictory raw capture must not be rewritten')

    def test_output_parent_symlink_is_rejected_before_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'inside').mkdir()
            (root / 'link').symlink_to(root / 'inside', target_is_directory=True)
            with patch.object(B, 'build', side_effect=AssertionError('symlink admission must fail first')):
                with self.assertRaises(OSError):
                    B.main(['--root', str(root), '--core', 'c', '--schedule', 's', '--core-guard', 'cg',
                            '--schedule-guard', 'sg', '--output-dir', 'link/new'])
            self.assertEqual([], list((root / 'inside').iterdir()))

    def test_output_parent_swap_during_build_cannot_write_outside(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root, target = Path(directory), Path(outside)
            (root / 'parent').mkdir()

            def swap_parent(*args, **kwargs):
                (root / 'parent').rename(root / 'original-parent')
                (root / 'parent').symlink_to(target, target_is_directory=True)
                return {'proofs': {}, 'evidence_index': {}, 'expected_bindings': {},
                        'qualification_report': {'status': 'failed'}}

            with patch.object(B, 'build', side_effect=swap_parent):
                with self.assertRaises((ValueError, OSError)):
                    B.main(['--root', str(root), '--core', 'c', '--schedule', 's', '--core-guard', 'cg',
                            '--schedule-guard', 'sg', '--output-dir', 'parent/new'])
            self.assertEqual([], list(target.iterdir()))
            self.assertEqual([], list((root / 'original-parent').iterdir()))

    def test_output_directory_swapped_after_mkdir_cannot_be_followed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root, target = Path(directory), Path(outside)
            real_mkdir = B.os.mkdir

            def swap_directory(name, *args, **kwargs):
                real_mkdir(name, *args, **kwargs)
                (root / 'new').rename(root / 'original-new')
                (root / 'new').symlink_to(target, target_is_directory=True)

            result = {'proofs': {}, 'evidence_index': {}, 'expected_bindings': {},
                      'qualification_report': {'status': 'failed'}}
            with patch.object(B, 'build', return_value=result), patch.object(B.os, 'mkdir', side_effect=swap_directory):
                with self.assertRaises(OSError):
                    B.main(['--root', str(root), '--core', 'c', '--schedule', 's', '--core-guard', 'cg',
                            '--schedule-guard', 'sg', '--output-dir', 'new'])
            self.assertEqual([], list(target.iterdir()))
            self.assertEqual([], list((root / 'original-new').iterdir()))

    def test_existing_failed_report_replay_retains_actual_failure_without_execution(self):
        path = '.piers/fakes/logs/core-20260925T100137Z.json'
        if not (ROOT / path).is_file():
            self.skipTest('Optional retained local failure artifact absent; authored reader tests still execute')
        original = (ROOT / path).read_bytes()
        report = B.decode(original)
        corpus = B.decode((ROOT / 'specs/urbit/fixtures/native-cases-v2.json').read_bytes())
        with patch.object(B.core_conn, 'run', side_effect=AssertionError('native execution forbidden')), \
             patch.object(time, 'sleep', side_effect=AssertionError('real wait forbidden')), \
             patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            native = B.Retained(report, B.reference(path, original), B.G.artifact_reader(ROOT))
            qa, groups, replay = B.replay_qa(native, corpus)
            self.assertEqual({'passed': 145, 'incomplete': 3}, qa['case_counts'])
            stages = B.CoreStages(native, corpus, ROOT / 'specs/urbit', max(replay.used) + 1)
            self.assertTrue(stages.stage('codec', stages.codec))
            self.assertTrue(stages.stage('contexts', stages.contexts))
            self.assertFalse(stages.stage('roundtrip', stages.roundtrip))
            self.assertEqual('owner-control:roundtrip', stages.groups['roundtrip']['error'])
        self.assertEqual(original, (ROOT / path).read_bytes())
        self.assertEqual('fail', report['status'])


if __name__ == '__main__':
    unittest.main()

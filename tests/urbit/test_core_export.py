"""Independent host export regressions using authored synthetic Git objects.

The callback is a scripted response source, not an authorization implementation.
Stock Git and filesystem operations are real and limited to fresh temporary
directories. No Hoon, fake ship, network, credentials or repository code runs.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('reviewed_core_export', ROOT / 'scripts/urbit/core_export.py')
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)
PROJECT = '019939ba-4000-7000-8000-000000000001'
CONTAINER = '019939ba-4000-7000-8000-000000000004'
OTHER = '019939ba-4000-7000-8000-000000000007'
PRINCIPAL = '019939ba-4000-7000-8000-000000000102'


def filename(number):
    return f'019939ba-4000-7000-8000-{number:012x}.md'


class SyntheticGraph:
    """Test-owned byte construction; no production constructor is reused."""

    def __init__(self):
        self.objects = {}
        self.reachable = {}
        self.files = {}

    def object(self, kind, body):
        oid = hashlib.sha1(kind.encode('ascii') + b' ' + str(len(body)).encode('ascii') + b'\0' + body).hexdigest()
        self.objects[oid] = {'kind': kind, 'body': body}
        return oid

    def blob(self, body):
        return self.object('blob', body)

    def tree(self, entries):
        body = b''.join(b'100644 ' + name.encode('ascii') + b'\0' + bytes.fromhex(oid)
                        for name, oid in entries)
        return self.object('tree', body)

    def commit(self, entries, *, parent=None, revision=1):
        tree = self.tree(entries)
        body = ('tree ' + tree + '\n' + ('' if parent is None else 'parent ' + parent + '\n')
                + f'author Stead Fixture <{PRINCIPAL}@stead.invalid> 1789171200 +0000\n'
                + f'committer Stead Fixture <{PRINCIPAL}@stead.invalid> 1789171200 +0000\n\n'
                + f'Save 019939ba-4000-7000-8000-000000000003 revision {revision}\n').encode('ascii')
        head = self.object('commit', body)
        reachable = {head, tree, *(oid for _, oid in entries)}
        if parent is not None:
            reachable.update(self.reachable[parent])
        self.reachable[head] = reachable
        self.files[head] = {name: {'oid': oid, 'hex': self.objects[oid]['body'].hex()}
                            for name, oid in entries}
        self.head = head
        return head

    def mapping(self, snapshot=None):
        return {oid: self.objects[oid]['kind'] for oid in self.reachable[snapshot or self.head]}


class ScriptedReads:
    def __init__(self, graph, *, denied_after=None, change=None):
        self.graph, self.denied_after, self.change = graph, denied_after, change
        self.requests = []

    def __call__(self, ship, mode, path):
        self.requests.append((ship, mode, path))
        if ship != 'bus' or mode != 'read':
            raise AssertionError('Export changed its authenticated fixture caller')
        if self.denied_after is not None and len(self.requests) > self.denied_after:
            result = {'protocol': 'stead.result/1', 'status': 'rejected', 'error': 'denied_or_not_found'}
        else:
            result = {'protocol': 'stead.result/1', 'status': 'read', 'project_id': PROJECT,
                      'resource_id': CONTAINER, 'resource_revision': '2'}
            if path == f'/v1/git/{PROJECT}/{CONTAINER}':
                result['payload'] = {'snapshot_commit_oid': self.graph.head, 'objects': self.graph.mapping()}
            else:
                segments = path.split('/')
                if len(segments) != 7 or segments[:5] != ['', 'v1', 'git-object', PROJECT, CONTAINER]:
                    raise AssertionError('Export widened its requested project/container scope')
                snapshot, oid = segments[5:]
                if snapshot not in self.graph.reachable or oid not in self.graph.reachable[snapshot]:
                    raise AssertionError('Export requested an object outside its selected synthetic graph')
                obj = self.graph.objects[oid]
                result['payload'] = {'snapshot_commit_oid': snapshot, 'oid': oid, 'kind': obj['kind'],
                                     'byte_length': str(len(obj['body'])), 'hex': obj['body'].hex()}
        if self.change is not None:
            self.change(path, result)
        return {'raw': json.dumps(result, separators=(',', ':')), 'json': result}


class CoreExportIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-core-export-review-')
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / 'export.git'
        self.graph = SyntheticGraph()
        first = self.graph.blob(b'first synthetic bytes\0\0')
        self.old_head = self.graph.commit([(filename(3), first)])
        second = self.graph.blob('second synthetic UTF-8: \u03bb\n'.encode())
        self.head = self.graph.commit([(filename(3), first), (filename(8), second)], parent=self.old_head, revision=2)

    def run_export(self, reads=None, **options):
        reads = reads or ScriptedReads(self.graph)
        return EXPORT.export(reads, self.destination, 'bus', PROJECT, CONTAINER, **options)

    def assert_no_published_ref(self):
        self.assertFalse((self.destination / 'refs/heads/main').exists())

    def test_current_graph_roundtrip_preserves_exact_bytes_and_original_ids(self):
        reads = ScriptedReads(self.graph)
        result = self.run_export(reads)
        self.assertEqual(result['snapshot_commit_oid'], self.head)
        self.assertEqual(result['files'], self.graph.files[self.head])
        self.assertEqual(set(result['objects']), self.graph.reachable[self.head])
        for oid, obj in result['objects'].items():
            self.assertEqual(bytes.fromhex(obj['hex']), self.graph.objects[oid]['body'])
            self.assertEqual(obj['byte_length'], len(self.graph.objects[oid]['body']))
        self.assertEqual(result['fsck']['returncode'], 0)
        self.assertEqual(len(reads.requests), 1 + len(self.graph.reachable[self.head]))
        self.assertEqual(len(set(reads.requests)), len(reads.requests))
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)

    def test_retained_snapshot_reads_only_that_exact_graph(self):
        reads = ScriptedReads(self.graph)
        result = self.run_export(reads, snapshot=self.old_head)
        self.assertEqual(result['files'], self.graph.files[self.old_head])
        self.assertEqual(set(result['objects']), self.graph.reachable[self.old_head])
        self.assertTrue(all('/' + self.old_head + '/' in path for _, _, path in reads.requests[1:]))

    def test_denied_manifest_stops_before_git_initialization(self):
        reads = ScriptedReads(self.graph, denied_after=0)
        with self.assertRaises(AssertionError):
            self.run_export(reads)
        self.assertEqual(len(reads.requests), 1)
        self.assertFalse((self.destination / 'HEAD').exists())
        self.assert_no_published_ref()

    def test_revocation_response_after_manifest_and_commit_stops_remaining_reads(self):
        reads = ScriptedReads(self.graph, denied_after=2)
        with self.assertRaises(AssertionError):
            self.run_export(reads)
        self.assertEqual(len(reads.requests), 3)
        self.assert_no_published_ref()

    def test_wrong_protocol_cannot_be_accepted_as_authorized_export(self):
        def change(path, result):
            result['protocol'] = 'unrelated.result/1'
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_response_for_another_project_cannot_be_accepted(self):
        def change(path, result):
            result['project_id'] = OTHER
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_object_response_for_another_container_cannot_be_accepted(self):
        def change(path, result):
            if '/git-object/' in path:
                result['resource_id'] = OTHER
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_manifest_object_type_must_agree_with_verified_graph(self):
        def change(path, result):
            if '/git/' in path:
                result['payload']['objects'][self.head] = 'blob'
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_manifest_cannot_include_unreachable_objects(self):
        extra = self.graph.blob(b'not reachable from accepted snapshot')
        def change(path, result):
            if '/git/' in path:
                result['payload']['objects'][extra] = 'blob'
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_manifest_cannot_omit_a_reachable_object(self):
        def change(path, result):
            if '/git/' in path:
                del result['payload']['objects'][self.old_head]
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_changed_bytes_cannot_reuse_expected_object_id(self):
        def change(path, result):
            if '/git-object/' in path:
                payload = result['payload']
                changed = b'x' + bytes.fromhex(payload['hex'])[1:]
                payload['hex'] = changed.hex()
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_explicit_byte_width_must_match_returned_zero_bytes(self):
        def change(path, result):
            if '/git-object/' in path and result['payload']['kind'] == 'blob':
                payload = result['payload']
                payload['byte_length'] = str(int(payload['byte_length']) - 1)
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_object_cannot_change_requested_snapshot(self):
        def change(path, result):
            if '/git-object/' in path:
                result['payload']['snapshot_commit_oid'] = self.old_head
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(self.graph, change=change))
        self.assert_no_published_ref()

    def test_thirty_two_flat_entries_are_supported(self):
        graph = SyntheticGraph()
        blob = graph.blob(b'synthetic shared blob')
        graph.commit([(filename(i), blob) for i in range(32)])
        result = self.run_export(ScriptedReads(graph))
        self.assertEqual(len(result['files']), 32)
        self.assertEqual(result['files'], graph.files[graph.head])

    def test_thirty_three_entries_exceed_frozen_native_container_capacity(self):
        graph = SyntheticGraph()
        blob = graph.blob(b'synthetic shared blob')
        graph.commit([(filename(i), blob) for i in range(33)])
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(graph))
        self.assert_no_published_ref()

    def test_invalid_tree_name_is_rejected(self):
        graph = SyntheticGraph()
        graph.commit([('../forbidden.md', graph.blob(b'synthetic text'))])
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(graph))
        self.assert_no_published_ref()

    def test_tree_cannot_treat_an_existing_commit_as_a_blob(self):
        graph = copy.deepcopy(self.graph)
        graph.commit([(filename(3), self.old_head)], parent=self.head, revision=3)
        with self.assertRaises((ValueError, AssertionError)):
            self.run_export(ScriptedReads(graph))
        self.assert_no_published_ref()


if __name__ == '__main__':
    unittest.main(verbosity=2)

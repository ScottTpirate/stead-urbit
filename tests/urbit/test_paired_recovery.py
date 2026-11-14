"""Tiny synthetic files test integrity custody, never native or Git recovery."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import paired_recovery as pair


PROJECT = '019939ba-4000-7000-8000-000000000001'
REQUEST = '019939ba-4000-7000-8000-000000000002'
CAPTURE = '019939ba-4000-7000-8000-000000000003'
SCOPE = {'home': '~zod', 'project_id': PROJECT, 'repository_id': PROJECT, 'authority_epoch': '7'}


class PairedRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-paired-recovery-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checkpoint = self.root / 'sealed-checkpoint.enc'
        self.pack = self.root / 'objects.pack'
        self.snapshot = self.root / 'snapshot.json'
        self.evidence = self.root / 'capture.json'
        self.bound = self.root / 'binding.json'
        # Header-shaped bytes intentionally are not a usable Git pack. This
        # verifier must never claim it ran index-pack, fsck or a Home restore.
        self.pack_raw = struct.pack('>4sII', b'PACK', 2, 3) + b'synthetic fixture only' + bytes(20)
        self.write(self.pack, self.pack_raw)
        self.write(self.checkpoint, b'opaque synthetic checkpoint ciphertext')
        head = b'refs/heads/main'.hex()
        self.manifest = {'format': pair.store.FORMAT, 'object_format': 'sha1', 'scope': SCOPE,
                         'head': head, 'refs': {head: '1' * 40, b'refs/heads/topic-\xff'.hex(): '2' * 40},
                         'pack_sha256': pair.sha(self.pack_raw), 'pack_bytes': len(self.pack_raw),
                         'object_count': 3, 'object_bytes': 500, 'object_ids_sha256': 'a' * 64}
        self.snapshot_raw = pair.encoded(self.manifest)
        self.write(self.snapshot, self.snapshot_raw)
        self.observed = {'protocol': pair.CAPTURE_FORMAT, 'capture_id': CAPTURE,
                         'source_commit': 'b' * 40, 'saved_state': {'version': 9, 'durable_sha256': 'c' * 64},
                         'checkpoint': {'bytes': self.checkpoint.stat().st_size,
                                        'sha256': pair.sha(self.checkpoint.read_bytes())},
                         'handoff': {'protocol': 'stead.home-handoff/1', 'home': '~zod',
                                     'phase': 'sealed', 'generation': '2'},
                         'scope': SCOPE,
                         'selection': {'protocol': 'stead.code/1', 'status': 'external',
                                       'snapshot': pair.sha(self.snapshot_raw), 'authority_epoch': '7',
                                       'object_count': '3', 'head': head,
                                       'refs': json.dumps(self.manifest['refs'], separators=(',', ':'), sort_keys=True),
                                       'request_id': REQUEST, 'accepted_at_ms': '100'}}
        self.capture_bytes()

    def write(self, path, raw):
        path.write_bytes(raw)
        path.chmod(0o600)

    def capture_bytes(self, value=None):
        # Pretty formatting is accepted and retained verbatim in the binding.
        raw = json.dumps(value or self.observed, indent=2).encode() + b'\n'
        self.write(self.evidence, raw)
        self.evidence_sha = pair.sha(raw)
        return raw

    def build(self):
        return pair.build(self.evidence, self.evidence_sha, self.checkpoint, self.snapshot, self.pack)

    def prepared(self):
        raw, result = self.build()
        self.write(self.bound, raw)
        return result

    def verify(self, expected=None):
        return pair.verify(self.bound, expected or pair.sha(self.bound.read_bytes()),
                           self.checkpoint, self.snapshot, self.pack)

    def test_exact_native_payloads_and_original_capture_bytes_survive_binding(self):
        raw, report = self.build()
        binding = pair.decoded(raw, pair.MAX_BINDING)
        self.assertEqual(binding['operator_evidence_json'].encode(), self.evidence.read_bytes())
        self.assertEqual(binding['snapshot_manifest'], self.manifest)
        pair.write_new(self.bound, raw)
        self.assertEqual(self.verify(report['binding_sha256']), report)
        self.assertEqual(report['scope'], SCOPE)
        self.assertEqual(report['request_id'], REQUEST)
        self.assertEqual(report['status'], 'integrity-verified')
        for key in ('native_execution', 'home_replayed', 'git_objects_verified', 'source_retirement_verified',
                    'decryption_verified', 'fresh_host_qualified', 'qualifies_phase'):
            self.assertIs(report[key], False)

    def test_separately_trusted_capture_and_binding_digests_are_mandatory(self):
        for expected in ('', None, '0' * 64):
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, 'evidence-digest'):
                pair.build(self.evidence, expected, self.checkpoint, self.snapshot, self.pack)
        report = self.prepared()
        value = pair.decoded(self.bound.read_bytes(), pair.MAX_BINDING)
        changed = pair.decoded(value['operator_evidence_json'].encode(), pair.MAX_EVIDENCE)
        changed['capture_id'] = REQUEST
        value['operator_evidence_json'] = pair.encoded(changed).decode()
        value['operator_evidence_sha256'] = pair.sha(value['operator_evidence_json'].encode())
        self.write(self.bound, pair.encoded(value))
        with self.assertRaisesRegex(ValueError, 'binding-digest'):
            self.verify(report['binding_sha256'])

    def test_open_wrong_home_epoch_and_invalid_receipts_are_rejected(self):
        changes = [('handoff', 'phase', 'open'), ('handoff', 'home', '~bus'),
                   ('handoff', 'generation', '1'), ('selection', 'authority_epoch', '8'),
                   ('selection', 'request_id', ''), ('selection', 'accepted_at_ms', '0'),
                   ('selection', 'object_count', '4'), ('saved_state', 'version', 10),
                   ('saved_state', 'version', True), ('checkpoint', 'bytes', True)]
        for field, key, replacement in changes:
            with self.subTest(field=field, key=key):
                changed = copy.deepcopy(self.observed)
                changed[field][key] = replacement
                self.capture_bytes(changed)
                with self.assertRaises(ValueError):
                    self.build()

    def test_manifest_exact_refs_metadata_and_scope_must_match_selection(self):
        changes = [('object_count', 4), ('pack_bytes', True), ('object_bytes', pair.store.MAX_OBJECT_BYTES + 1),
                   ('scope', SCOPE | {'home': '~bus'}), ('scope', SCOPE | {'repository_id': REQUEST}),
                   ('head', b'refs/heads/topic-\xff'.hex()), ('object_ids_sha256', 'invalid')]
        for field, replacement in changes:
            with self.subTest(field=field):
                changed = self.manifest | {field: replacement}
                self.write(self.snapshot, pair.encoded(changed))
                with self.assertRaises(ValueError):
                    self.build()
        self.write(self.snapshot, json.dumps(self.manifest, indent=2).encode())
        with self.assertRaisesRegex(ValueError, 'snapshot-differs'):
            self.build()

    def test_checkpoint_and_pack_bytes_cannot_be_substituted(self):
        self.prepared()
        for path in (self.checkpoint, self.pack, self.snapshot):
            original = path.read_bytes()
            with self.subTest(path=path.name):
                self.write(path, original[:-1] + bytes([original[-1] ^ 1]))
                with self.assertRaises(ValueError):
                    self.verify()
                self.write(path, original)
        self.write(self.pack, self.pack_raw + b'trailing')
        with self.assertRaisesRegex(ValueError, 'artifact-length'):
            self.verify()

    def test_pack_header_count_and_magic_are_checked_without_claiming_object_validation(self):
        for header in (struct.pack('>4sII', b'BAD!', 2, 3), struct.pack('>4sII', b'PACK', 4, 3),
                       struct.pack('>4sII', b'PACK', 2, 0), struct.pack('>4sII', b'PACK', 2, 4)):
            with self.subTest(header=header):
                pack = header + self.pack_raw[12:]
                self.write(self.pack, pack)
                manifest = self.manifest | {'pack_sha256': pair.sha(pack)}
                self.write(self.snapshot, pair.encoded(manifest))
                observed = copy.deepcopy(self.observed)
                observed['selection']['snapshot'] = pair.sha(pair.encoded(manifest))
                self.capture_bytes(observed)
                with self.assertRaisesRegex(ValueError, 'pack-(header|differs)'):
                    self.build()

    def test_files_are_streamed_with_fixed_size_and_time_bounds(self):
        with patch.object(pair, 'MAX_CHECKPOINT', self.checkpoint.stat().st_size - 1):
            with self.assertRaisesRegex(ValueError, 'checkpoint'):
                self.build()
        with patch.object(pair, 'MAX_EVIDENCE', 8):
            with self.assertRaisesRegex(ValueError, 'file-bound'):
                self.build()
        with patch.object(pair, 'MAX_SECONDS', 0):
            with self.assertRaisesRegex(ValueError, 'deadline'):
                self.build()
        with patch.object(pair, 'CHUNK', 3):
            self.assertEqual(self.build()[1]['checkpoint'], self.observed['checkpoint'])

    def test_private_file_symlink_hardlink_and_parent_boundaries(self):
        self.prepared()
        self.pack.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private-file'):
            self.verify()
        self.pack.chmod(0o600)
        linked = self.root / 'linked.pack'
        os.link(self.pack, linked)
        with self.assertRaisesRegex(ValueError, 'private-file'):
            self.verify()
        linked.unlink()
        link = self.root / 'alias.pack'
        link.symlink_to(self.pack)
        with self.assertRaises(OSError):
            pair.verify(self.bound, pair.sha(self.bound.read_bytes()), self.checkpoint, self.snapshot, link)
        parent = self.root / 'alias-parent'
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            pair.verify(parent / self.bound.name, pair.sha(self.bound.read_bytes()),
                        self.checkpoint, self.snapshot, self.pack)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private-directory'):
            self.verify()
        self.root.chmod(0o700)

    def test_in_place_change_after_hash_is_detected_before_success(self):
        self.prepared()
        original = pair.hash_stream
        def changed(opened, deadline, **kwargs):
            result = original(opened, deadline, **kwargs)
            if kwargs.get('pack'):
                raw = self.checkpoint.read_bytes()
                self.write(self.checkpoint, raw[:-1] + b'!')
            return result
        with patch.object(pair, 'hash_stream', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'input-changed'):
                self.verify()

    def test_replacement_after_hash_is_detected_and_original_preserved(self):
        self.prepared()
        original = pair.hash_stream
        old = self.root / 'original.pack'
        def replaced(opened, deadline, **kwargs):
            result = original(opened, deadline, **kwargs)
            if kwargs.get('pack'):
                self.pack.rename(old)
                self.write(self.pack, self.pack_raw)
            return result
        with patch.object(pair, 'hash_stream', side_effect=replaced):
            with self.assertRaisesRegex(ValueError, 'input-changed'):
                self.verify()
        self.assertEqual(old.read_bytes(), self.pack_raw)

    def test_duplicate_json_keys_unknown_fields_and_changed_embedded_evidence_fail(self):
        original = self.evidence.read_bytes()
        self.write(self.evidence, b'{"protocol":1,"protocol":2}')
        self.evidence_sha = pair.sha(self.evidence.read_bytes())
        with self.assertRaisesRegex(ValueError, 'invalid-json'):
            self.build()
        self.write(self.evidence, original)
        self.evidence_sha = pair.sha(original)
        self.prepared()
        binding = pair.decoded(self.bound.read_bytes(), pair.MAX_BINDING)
        for changed in (binding | {'extra': True}, binding | {'operator_evidence_json': '{}'}):
            with self.subTest(changed=changed.keys()):
                self.write(self.bound, pair.encoded(changed))
                with self.assertRaises(ValueError):
                    self.verify()

    def test_builder_never_overwrites_existing_binding(self):
        raw, _ = self.build()
        self.write(self.bound, b'previous custody record')
        with self.assertRaises(FileExistsError):
            pair.write_new(self.bound, raw)
        self.assertEqual(self.bound.read_bytes(), b'previous custody record')

    def test_file_sync_failure_does_not_publish_partial_binding_or_block_retry(self):
        raw, _ = self.build()
        with patch.object(pair.os, 'fsync', side_effect=OSError('synthetic file sync failure')):
            with self.assertRaises(OSError):
                pair.write_new(self.bound, raw)
        self.assertFalse(self.bound.exists())
        self.assertEqual(list(self.root.glob('.paired-recovery-*')), [])
        pair.write_new(self.bound, raw)
        self.assertEqual(self.bound.read_bytes(), raw)

    def test_parent_sync_failure_retains_complete_published_binding_for_inspection(self):
        raw, _ = self.build()
        original = pair.os.fsync
        def failed_parent(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError('synthetic directory sync failure')
            return original(fd)
        with patch.object(pair.os, 'fsync', side_effect=failed_parent):
            with self.assertRaises(OSError):
                pair.write_new(self.bound, raw)
        self.assertEqual(self.bound.read_bytes(), raw)
        self.assertEqual(self.bound.stat().st_nlink, 1)
        self.assertEqual(list(self.root.glob('.paired-recovery-*')), [])
        self.assertEqual(self.verify()['status'], 'integrity-verified')

    def test_cli_build_verify_and_private_failure_output(self):
        common = ['--checkpoint', str(self.checkpoint), '--snapshot', str(self.snapshot), '--pack', str(self.pack)]
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(pair.main(['build', '--evidence', str(self.evidence), '--evidence-sha256', self.evidence_sha,
                                        '--output', str(self.bound), *common]), 0)
        result = json.loads(output.getvalue())
        with redirect_stdout(io.StringIO()) as verified:
            self.assertEqual(pair.main(['verify', '--binding', str(self.bound), '--sha256', result['binding_sha256'], *common]), 0)
        self.assertEqual(json.loads(verified.getvalue()), result)
        self.write(self.checkpoint, b'private damaged checkpoint')
        with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(pair.main(['verify', '--binding', str(self.bound), '--sha256', result['binding_sha256'], *common]), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn('private damaged', errors.getvalue())
        self.assertNotIn(str(self.root), errors.getvalue())


if __name__ == '__main__':
    unittest.main()

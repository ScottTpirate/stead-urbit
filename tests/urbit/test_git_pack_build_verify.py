"""Verify accepted source archives independently from stock Git export."""
import unittest

import git_pack_build_source as source
import git_pack_build_verify as build
from portable_recovery import RecoveryError, decoded, encoded, sha
import test_git_pack_build_source as fixtures


class BuildSourceVerifyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BuildSourceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.store(self.fixture.sample())
        self.pin = self.fixture.export()
        self.path = self.fixture.destination
        self.index = self.path / source.MANIFEST
        self.archive = self.path / source.ARCHIVE
        self.manifest = decoded(self.index.read_bytes())

    def write_index(self, manifest):
        raw = encoded(manifest)
        self.index.write_bytes(raw)
        return sha(raw)

    def replace_archive(self, raw):
        self.archive.write_bytes(raw)
        return self.manifest | {'archive': {'bytes': len(raw), 'sha256': sha(raw)}}

    def test_qualified_plain_recipe_evidence_uses_exact_original_source_ids(self):
        result = build.verify(self.path, self.pin)
        self.assertEqual(result['source_manifest_sha256'], self.pin)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['recipe'], build.RECIPE)
        self.assertEqual(result['commit'], self.fixture.commit)
        self.assertEqual(result['proposal_id'], self.fixture.receipt['proposal_id'])
        self.assertEqual(result['generation'], self.fixture.receipt['generation'])
        self.assertEqual(result['request_id'], self.fixture.receipt['request_id'])
        self.assertEqual(result['receipt_sha256'], self.manifest['receipt_sha256'])
        self.assertEqual(result['archive'], self.manifest['archive'])
        self.assertEqual(result['file_count'], 4)
        self.assertEqual(result['entry_count'], 5)
        self.assertEqual({row.name for row in self.path.iterdir()}, {source.MANIFEST, source.ARCHIVE})

    def test_wrong_pin_or_noncanonical_pin_never_validates(self):
        with self.assertRaisesRegex(RecoveryError, 'input-digest'):
            build.verify(self.path, 'd' * 64)
        raw = self.index.read_bytes() + b'\n'
        self.index.write_bytes(raw)
        with self.assertRaisesRegex(RecoveryError, 'schema'):
            build.verify(self.path, sha(raw))

    def test_even_pinned_altered_tree_receipt_path_and_order_fail(self):
        handoff = self.manifest['receipt'] | {'snapshot': 'e' * 64}
        altered = [({'tree': 'e' * 40}, 'tree'), ({'receipt': handoff}, 'receipt'),
                   ({'entries': list(reversed(self.manifest['entries']))}, 'directory'),
                   ({'entries': [self.manifest['entries'][0] | {'path': '../../escape'}] + self.manifest['entries'][1:]}, 'path')]
        for fields, error in altered:
            with self.subTest(fields=fields), self.assertRaisesRegex(RecoveryError, error):
                build.verify(self.path, self.write_index(self.manifest | fields))

    def test_rehashed_tar_with_header_payload_padding_or_suffix_mutation_fails(self):
        original = self.archive.read_bytes()
        marker = b'Read\x00\xff'
        payload = original.index(marker)
        samples = [((b'/' + original[1:]), 'tar-header'),
                   ((original.replace(marker, b'Rbad\x00\xff', 1)), 'blob'),
                   ((original[:payload + len(marker)] + b'x' + original[payload + len(marker) + 1:]), 'tar-padding'),
                   (original + b'\0', 'tar-digest')]
        for raw, error in samples:
            with self.subTest(error=error), self.assertRaisesRegex(RecoveryError, error):
                build.verify(self.path, self.write_index(self.replace_archive(raw)))

    def test_refuses_file_substitution_and_store_permission_changes(self):
        self.archive.chmod(0o640)
        with self.assertRaisesRegex(RecoveryError, 'verification-file'):
            build.verify(self.path, self.pin)
        actual = self.path / 'retained.tar'
        self.archive.rename(actual)
        actual.chmod(0o600)
        self.archive.symlink_to(actual)
        with self.assertRaises(OSError):
            build.verify(self.path, self.pin)
        self.archive.unlink()
        self.archive.hardlink_to(actual)
        with self.assertRaisesRegex(RecoveryError, 'verification-file'):
            build.verify(self.path, self.pin)

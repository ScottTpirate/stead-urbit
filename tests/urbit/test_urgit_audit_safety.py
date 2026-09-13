"""Independent Urgit-runner safety checks; no native evaluation is launched.

Owner: /root/qa_review, independent agent review rather than human approval.
Writes use temporary synthetic files. Download bodies, native streams, and the
evaluator's import-time sandbox paths are mocked explicitly; filesystem archive
parsing, redaction, and symlink effects are real host operations.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/urbit'))
import urgit_audit  # noqa: E402


class UrgitHostBoundarySafety(unittest.TestCase):
    def test_json_output_cannot_overwrite_file_outside_run_via_symlink(self):
        with tempfile.TemporaryDirectory(prefix='stead-urgit-host-boundary-') as tmp:
            root = Path(tmp)
            evidence = root / 'synthetic-run/evidence'
            evidence.mkdir(parents=True)
            sentinel = root / 'outside-run'
            sentinel.write_text('preserve synthetic outside content')
            report = evidence / 'report.json'
            report.symlink_to(sentinel)
            try:
                urgit_audit.write_json(report, {'status': 'failed', 'synthetic': True})
            except (ValueError, OSError):
                pass  # Refusal or an atomic safe replacement both preserve host data.
            self.assertEqual(sentinel.read_text(), 'preserve synthetic outside content')

    def test_download_never_follows_existing_destination_symlink(self):
        with tempfile.TemporaryDirectory(prefix='stead-urgit-download-') as tmp:
            root = Path(tmp)
            outside = root / 'outside'
            outside.write_bytes(b'preserve synthetic sentinel')
            target = root / 'artifact'
            target.symlink_to(outside)
            payload = b'approved synthetic artifact'
            with patch.object(urgit_audit.urllib.request, 'urlopen', return_value=io.BytesIO(payload)):
                with self.assertRaises((ValueError, OSError)):
                    urgit_audit.download('https://invalid.example.test/artifact', hashlib.sha256(payload).hexdigest(), target, 1024)
            self.assertEqual(outside.read_bytes(), b'preserve synthetic sentinel')

    def test_changed_download_is_not_accepted_under_expected_pin(self):
        with tempfile.TemporaryDirectory(prefix='stead-urgit-download-') as tmp:
            target = Path(tmp) / 'artifact'
            with patch.object(urgit_audit.urllib.request, 'urlopen', return_value=io.BytesIO(b'changed artifact')):
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    urgit_audit.download('https://invalid.example.test/artifact', hashlib.sha256(b'approved artifact').hexdigest(), target, 1024)


class UrgitArchiveSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-urgit-archive-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'source.tar'
        self.destination = self.root / 'candidate'
        self.pin = {'candidate': {'archive_root': 'candidate-pinned'}, 'limits': {
            'maximum_archive_files': 8, 'maximum_source_bytes': 128, 'maximum_file_bytes': 64}}
        self.license = ("candidate-pinned/desk/desk.docket-0", b"license+'MIT'\n")

    def tar(self, entries):
        with tarfile.open(self.archive, 'w') as archive:
            for path, value in entries:
                item = tarfile.TarInfo(path)
                if isinstance(value, bytes):
                    item.size = len(value)
                    archive.addfile(item, io.BytesIO(value))
                else:
                    item.type = tarfile.SYMTYPE
                    item.linkname = value
                    archive.addfile(item)

    def test_bounded_regular_source_with_pinned_root_and_license_is_accepted(self):
        self.tar([self.license, ('candidate-pinned/desk/app/probe.hoon', b'synthetic source')])
        result = urgit_audit.unpack(self.archive, self.destination, self.pin)
        self.assertEqual(result['regular_files'], 2)
        self.assertEqual((self.destination / 'desk/app/probe.hoon').read_bytes(), b'synthetic source')

    def test_archive_parent_traversal_cannot_create_outside_file(self):
        self.tar([('candidate-pinned/../outside', b'forbidden')])
        with self.assertRaises(ValueError):
            urgit_audit.unpack(self.archive, self.destination, self.pin)
        self.assertFalse((self.root / 'outside').exists())

    def test_source_archive_symlink_is_rejected(self):
        self.tar([self.license, ('candidate-pinned/desk/alias', '/tmp/forbidden-target')])
        with self.assertRaises(ValueError):
            urgit_audit.unpack(self.archive, self.destination, self.pin)
        self.assertFalse((self.destination / 'desk/alias').is_symlink())

    def test_duplicate_archive_path_cannot_replace_first_bytes(self):
        self.tar([self.license, (self.license[0], b'replacement')])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            urgit_audit.unpack(self.archive, self.destination, self.pin)
        self.assertEqual((self.destination / 'desk/desk.docket-0').read_bytes(), self.license[1])

    def test_individual_file_expansion_limit_is_enforced_before_write(self):
        self.tar([self.license, ('candidate-pinned/desk/huge', b'x' * 65)])
        with self.assertRaisesRegex(ValueError, 'expansion limit'):
            urgit_audit.unpack(self.archive, self.destination, self.pin)
        self.assertFalse((self.destination / 'desk/huge').exists())

    def test_total_expansion_limit_is_enforced(self):
        self.tar([self.license, *[(f'candidate-pinned/desk/file-{i}', b'x' * 60) for i in range(3)]])
        with self.assertRaisesRegex(ValueError, 'expansion limit'):
            urgit_audit.unpack(self.archive, self.destination, self.pin)

    def test_absent_license_declaration_blocks_evaluation(self):
        self.tar([(self.license[0], b'no reviewed license declaration')])
        with self.assertRaisesRegex(ValueError, 'MIT declaration absent'):
            urgit_audit.unpack(self.archive, self.destination, self.pin)


class UrgitCredentialRedactionSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-urgit-redaction-')
        self.addCleanup(self.temp.cleanup)
        self.events = io.StringIO()
        self.addCleanup(self.events.close)
        spec = importlib.util.spec_from_file_location('stead_test_urgit_evaluator', REPO / 'scripts/urbit/urgit_eval/evaluate.py')
        self.evaluator = importlib.util.module_from_spec(spec)
        read_text, open_path = Path.read_text, Path.open

        def fixture_read(path, *args, **kwargs):
            if path in (Path('/work/candidate.lock.json'), Path('/work/toolchain.lock.json')):
                return '{}'
            return read_text(path, *args, **kwargs)

        def fixture_open(path, *args, **kwargs):
            if path == Path('/work/evidence/commands.jsonl'):
                return self.events
            return open_path(path, *args, **kwargs)

        with patch.object(Path, 'read_text', fixture_read), patch.object(Path, 'open', fixture_open):
            spec.loader.exec_module(self.evaluator)
        self.evaluator.EVIDENCE = Path(self.temp.name)

    def test_structured_events_redact_raw_and_basic_auth_values(self):
        self.evaluator.event('synthetic', token=self.evaluator.TOKEN, header='Basic ' + self.evaluator.AUTH)
        raw = self.events.getvalue()
        self.assertNotIn(self.evaluator.TOKEN, raw)
        self.assertNotIn(self.evaluator.AUTH, raw)
        self.assertEqual(raw.count('<generated-synthetic-credential>'), 2)

    def test_native_stream_redacts_credentials_across_every_split(self):
        token, auth = self.evaluator.TOKEN.encode(), self.evaluator.AUTH.encode()
        payload = b'before ' + token + b' between ' + auth + b' after'

        class Chunks:
            def __init__(self, values):
                self.values = iter(values)

            def read(self, _size):
                return next(self.values, b'')

        for split in range(1, len(payload)):
            with self.subTest(split=split):
                self.evaluator.log_runtime(Chunks([payload[:split], payload[split:]]))
                captured = (self.evaluator.EVIDENCE / 'native.log').read_bytes()
                self.assertNotIn(token, captured)
                self.assertNotIn(auth, captured)
                self.assertEqual(captured.count(b'<generated-synthetic-credential>'), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)

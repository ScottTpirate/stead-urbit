"""Independent Urgit-runner safety checks; no native evaluation is launched.

Owner: /root/qa_review, independent agent review rather than human approval.
Writes use temporary synthetic files. Download bodies, native streams, and the
evaluator's import-time sandbox paths are mocked explicitly; filesystem archive
parsing, redaction, and symlink effects are real host operations.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/urbit'))
import urgit_audit  # noqa: E402


class UrgitHostBoundarySafety(unittest.TestCase):
    def test_json_output_is_written_to_regular_host_file(self):
        with tempfile.TemporaryDirectory(prefix='stead-urgit-host-boundary-') as tmp:
            report = Path(tmp) / 'report.json'
            value = {'status': 'failed', 'synthetic': True}
            urgit_audit.write_json(report, value)
            self.assertEqual(json.loads(report.read_text()), value)

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

    def test_json_output_rejects_redirected_parent_directory(self):
        with tempfile.TemporaryDirectory(prefix='stead-urgit-host-boundary-') as tmp:
            root = Path(tmp)
            outside = root / 'outside-run'
            outside.mkdir()
            sentinel = outside / 'report.json'
            sentinel.write_text('preserve outside parent content')
            redirected = root / 'evidence'
            redirected.symlink_to(outside, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                urgit_audit.write_json(redirected / 'report.json', {'status': 'failed'})
            self.assertEqual(sentinel.read_text(), 'preserve outside parent content')

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


class UrgitOutputImportSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-urgit-output-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'output'
        self.output.mkdir()

    def test_regular_file_is_read_through_anchored_directory(self):
        (self.output / 'report.json').write_bytes(b'{"synthetic":true}')
        with urgit_audit.directory_fd(self.output) as parent:
            self.assertEqual(urgit_audit.read_regular_at(parent, 'report.json', 64), b'{"synthetic":true}')

    def test_output_symlink_cannot_read_outside_file(self):
        outside = self.root / 'outside'
        outside.write_bytes(b'private synthetic sentinel')
        (self.output / 'report.json').symlink_to(outside)
        with urgit_audit.directory_fd(self.output) as parent:
            with self.assertRaises((ValueError, OSError)):
                urgit_audit.read_regular_at(parent, 'report.json', 64)

    def test_oversized_output_is_rejected(self):
        (self.output / 'report.json').write_bytes(b'x' * 65)
        with urgit_audit.directory_fd(self.output) as parent:
            with self.assertRaises(ValueError):
                urgit_audit.read_regular_at(parent, 'report.json', 64)

    def test_parent_traversal_filename_is_rejected(self):
        (self.root / 'outside').write_bytes(b'synthetic sentinel')
        with urgit_audit.directory_fd(self.output) as parent:
            with self.assertRaises(ValueError):
                urgit_audit.read_regular_at(parent, '../outside', 64)

    def test_multiply_linked_file_is_rejected(self):
        outside = self.root / 'outside'
        outside.write_bytes(b'synthetic sentinel')
        os.link(outside, self.output / 'report.json')
        with urgit_audit.directory_fd(self.output) as parent:
            with self.assertRaises(ValueError):
                urgit_audit.read_regular_at(parent, 'report.json', 64)

    def test_directory_rename_cannot_redirect_preopened_reader(self):
        (self.output / 'report.json').write_bytes(b'original accepted output')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'report.json').write_bytes(b'forbidden replacement')
        with urgit_audit.directory_fd(self.output) as parent:
            self.output.rename(self.root / 'original-output')
            self.output.symlink_to(outside, target_is_directory=True)
            self.assertEqual(urgit_audit.read_regular_at(parent, 'report.json', 64), b'original accepted output')

    def test_fifo_is_rejected_without_waiting_for_writer(self):
        fifo = self.output / 'report.json'
        os.mkfifo(fifo)
        completed = threading.Event()
        outcomes = []
        with urgit_audit.directory_fd(self.output) as parent:
            def attempt():
                try:
                    outcomes.append(urgit_audit.read_regular_at(parent, 'report.json', 64))
                except Exception as error:
                    outcomes.append(error)
                finally:
                    completed.set()

            worker = threading.Thread(target=attempt, daemon=True)
            worker.start()
            returned_without_writer = completed.wait(1)
            if not returned_without_writer:
                # Unblock a regressed implementation so this negative test
                # reports a failure rather than hanging the entire test suite.
                writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                os.write(writer, b'x')
                os.close(writer)
            worker.join(2)
            self.assertTrue(returned_without_writer, 'Untrusted FIFO blocked the host evidence reader')
            self.assertIsInstance(outcomes[0], (ValueError, OSError))

    def import_report(self, report, guard=None):
        evidence, control = self.root / 'evidence', self.root / 'control'
        evidence.mkdir(exist_ok=True)
        control.mkdir(exist_ok=True)
        for name in urgit_audit.OUTPUT_LIMITS:
            (self.output / name).write_bytes(b'{}')
        raw = (json.dumps(report) + '\n').encode()
        (self.output / 'report.json').write_bytes(raw)
        for name in ('provenance.json', 'sandbox-command.json'):
            (evidence / name).write_bytes(b'{}')
        guard = guard or {'status': 'completed', 'exit_code': 0, 'reason': None, 'events': []}
        with urgit_audit.directory_fd(self.output) as parent:
            # The shared guard is mocked; output import/report writes and
            # final checksum generation execute against the synthetic files.
            with patch.object(urgit_audit.execution_policy, 'run_guarded', return_value=guard), redirect_stdout(io.StringIO()):
                result = urgit_audit.run_sandbox(self.root, evidence, control, parent, ['not-executed'], 0,
                    {'start_temperature_c': 75, 'stop_temperature_c': 90, 'total_timeout_seconds': 2100})
        self.assertEqual((evidence / 'evaluator-report.json').read_bytes(), raw)
        hashes = json.loads((evidence / 'SHA256SUMS.json').read_text())
        self.assertEqual(hashes['evaluator-report.json'], hashlib.sha256(raw).hexdigest())
        return result, json.loads((evidence / 'report.json').read_text())

    def passed_report(self):
        return {'status': 'passed', 'checks': [
            {'name': name, 'passed': True} for name in urgit_audit.EXPECTED_CHECKS]}

    def test_nonzero_sandbox_exit_cannot_persist_passed_host_report(self):
        result, report = self.import_report(self.passed_report(), {
            'status': 'failed', 'exit_code': 17,
            'reason': 'Owned sandbox exited unsuccessfully', 'events': []})
        self.assertEqual(result, 1)
        self.assertEqual(report['status'], 'failed')

    def test_only_exact_nonempty_passing_inventory_can_pass(self):
        valid = self.passed_report()
        malformed = {
            'empty': [],
            'missing': valid['checks'][:-1],
            'duplicate': valid['checks'][:-1] + [valid['checks'][0]],
            'unknown': valid['checks'][:-1] + [{'name': 'invented', 'passed': True}],
            'false': valid['checks'][:-1] + [{'name': urgit_audit.EXPECTED_CHECKS[-1], 'passed': False}],
            'nonboolean': valid['checks'][:-1] + [{'name': urgit_audit.EXPECTED_CHECKS[-1], 'passed': 1}],
        }
        for label, checks in malformed.items():
            with self.subTest(label=label):
                result, report = self.import_report({'status': 'passed', 'checks': checks})
                self.assertEqual(result, 1)
                self.assertEqual(report['status'], 'failed')
        result, report = self.import_report(valid)
        self.assertEqual(result, 0)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(len(report['checks']), 14)

    def test_failed_partial_report_preserves_actual_check_results(self):
        checks = [{'name': urgit_audit.EXPECTED_CHECKS[0], 'passed': True},
                  {'name': urgit_audit.EXPECTED_CHECKS[1], 'passed': False}]
        result, report = self.import_report({'status': 'failed', 'checks': checks})
        self.assertEqual(result, 1)
        self.assertEqual(report['checks'], checks)


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
            if path in (Path('/input/candidate.lock.json'), Path('/input/toolchain.lock.json')):
                return '{}'
            return read_text(path, *args, **kwargs)

        def fixture_open(path, *args, **kwargs):
            if path == Path('/output/commands.jsonl'):
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

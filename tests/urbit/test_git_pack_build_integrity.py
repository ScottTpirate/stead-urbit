"""Qualify the exact isolated source integrity job and descriptor custody."""
import os
import subprocess
import unittest
from unittest.mock import patch

import test_git_pack_build_source as fixtures
import git_pack_build_integrity as worker
import git_pack_build_verify as verify
from git_pack_worker_service import sandbox_ready
from portable_recovery import RecoveryError, encoded, sha


JOB_ID = '019939ba-4000-7000-8000-000000000021'


class IntegrityJobTests(unittest.TestCase):
    def test_job_requires_exact_digest_recipe_fields_and_canonical_bytes(self):
        valid = {'protocol': worker.JOB, 'job_id': JOB_ID, 'recipe': verify.RECIPE,
                 'source_manifest_sha256': 'a' * 64}
        raw = encoded(valid)
        self.assertEqual(worker.load_job(raw, sha(raw)), valid)
        for patched in ({'recipe': 'make'}, {'command': ['sh']}, {'source_manifest_sha256': 'no'},
                        {'job_id': 'other'}, {'output': '/other'}):
            invalid = encoded(valid | patched)
            with self.subTest(patched=patched), self.assertRaises(RecoveryError):
                worker.load_job(invalid, sha(invalid))
        with self.assertRaises(RecoveryError):
            worker.load_job(raw, 'b' * 64)
        with self.assertRaises(RecoveryError):
            worker.load_job(raw + b'\n', sha(raw + b'\n'))


@unittest.skipIf(os.getuid() == 0, 'Use an unprivileged Linux build worker')
class ActualIntegritySandboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            sandbox_ready()
        except (OSError, RecoveryError, subprocess.SubprocessError) as problem:
            raise unittest.SkipTest('Unprivileged worker namespaces are unavailable') from problem

    def setUp(self):
        self.fixture = fixtures.BuildSourceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.store(self.fixture.sample())
        self.source_pin = self.fixture.export()
        self.directory = self.fixture.destination
        job = {'protocol': worker.JOB, 'job_id': JOB_ID, 'recipe': verify.RECIPE,
               'source_manifest_sha256': self.source_pin}
        raw = encoded(job)
        self.job = self.fixture.root / 'job.json'
        self.job.write_bytes(raw)
        self.job.chmod(0o600)
        self.job_pin = sha(raw)

    def test_real_namespaces_reproduce_same_evidence_and_leave_inputs_intact(self):
        expected = verify.verify(self.directory, self.source_pin)
        first = worker.run(self.job, self.job_pin, self.directory)
        second = worker.run(self.job, self.job_pin, self.directory)
        self.assertEqual(first, second)
        self.assertEqual(first['job_id'], JOB_ID)
        self.assertEqual(first['job_sha256'], self.job_pin)
        self.assertEqual(first['execution'], 'isolated-read-only')
        self.assertEqual(first['result_sha256'], sha(encoded(expected)))
        self.assertEqual(first['result'], expected)
        self.assertEqual(verify.verify(self.directory, self.source_pin), expected)

    def test_bind_time_replacement_cannot_change_mounted_input_or_return_success(self):
        original_run = subprocess.run
        index = self.directory / 'source.json'
        captured = []

        def replace_before_launch(*args, **kwargs):
            index.rename(self.directory / 'previous.json')
            index.write_bytes(b'wrong manifest')
            index.chmod(0o600)
            process = original_run(*args, **kwargs)
            captured.append(process.returncode)
            return process

        with patch.object(worker.subprocess, 'run', side_effect=replace_before_launch):
            with self.assertRaisesRegex(RecoveryError, 'source-integrity-input-changed'):
                worker.run(self.job, self.job_pin, self.directory)
        self.assertEqual(captured, [0], 'child verified the original open descriptor')
        self.assertEqual(index.read_bytes(), b'wrong manifest')

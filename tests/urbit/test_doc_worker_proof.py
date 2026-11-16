"""Host adversarial checks of a constructed proof, never actual child evidence.

These tests prohibit process launch and do not call body/cutpoint/controller.
Only the independently admitted hosted run may establish isolation/crash facts.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('stead_doc_worker_proof_host', ROOT / 'scripts/ci/doc_worker_proof.py')
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)

CHECKS = ['exact-output', 'distinct-private-namespaces', 'credential-environment-absent',
          'completed-output-not-overwritten', 'wrong-worker-pin-refused', 'wrong-context-refused',
          'output-budget-refused', 'before-child', 'before-output', 'after-output', 'after-receipt']
CUTS = [
    {'point': 'before-child', 'parent_exit': -9, 'files': [], 'overwrite_refused': False},
    {'point': 'before-output', 'parent_exit': -9, 'files': [], 'overwrite_refused': True},
    {'point': 'after-output', 'parent_exit': -9, 'files': ['proposal.md'], 'overwrite_refused': True},
    {'point': 'after-receipt', 'parent_exit': -9, 'files': ['proposal.md', 'result.json'], 'overwrite_refused': True},
]


class DocWorkerProofVerifierTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        for target in ('body', 'cutpoint'):
            patch.object(proof, target, side_effect=AssertionError('Host test must not execute proof')).start()
        for target in ('Popen', 'run'):
            patch.object(proof.subprocess, target, side_effect=AssertionError('Host test must not launch a process')).start()
        self.worker_sha = 'a' * 64
        self.proof_sha = 'b' * 64
        job, context, _, expected = proof.fixture()
        self.value = {'protocol': 'stead.doc-worker-isolation-proof/1', 'status': 'pass',
                      'worker_sha256': self.worker_sha, 'proof_sha256': self.proof_sha,
                      'job_sha256': hashlib.sha256(job).hexdigest(), 'context_sha256': hashlib.sha256(context).hexdigest(),
                      'artifact_sha256': hashlib.sha256(expected).hexdigest(), 'checks': copy.deepcopy(CHECKS), 'crashes': copy.deepcopy(CUTS),
                      'classification': 'actual-isolated-deterministic-child-with-publication-fault-injection',
                      'native_publication': False, 'model_execution': False, 'qualifies_g3': False}

    def rejected(self, value):
        with self.assertRaises(ValueError):
            proof.verify(value, self.worker_sha, self.proof_sha)

    def test_complete_host_constructed_result_matches_closed_verifier_only(self):
        self.assertEqual(list(proof.CHECKS), CHECKS)
        self.assertEqual(list(proof.CUTS), [entry['point'] for entry in CUTS])
        self.assertIsNone(proof.verify(self.value, self.worker_sha, self.proof_sha))
        self.assertEqual(len(self.value['checks']), 11)

    def test_source_job_context_and_artifact_pins_cannot_be_swapped(self):
        for field in ('worker_sha256', 'proof_sha256', 'job_sha256', 'context_sha256', 'artifact_sha256'):
            with self.subTest(field=field):
                self.rejected(self.value | {field: 'f' * 64})
        with self.assertRaises(ValueError):
            proof.verify(self.value, 'c' * 64, self.proof_sha)
        with self.assertRaises(ValueError):
            proof.verify(self.value, self.worker_sha, 'c' * 64)

    def test_closed_classification_never_upgrades_to_model_native_or_g3(self):
        for field, changed in (('native_publication', True), ('model_execution', True), ('qualifies_g3', True),
                               ('status', 'partial'), ('protocol', 'stead.native-proof/1'),
                               ('classification', 'native-run-completion'), ('native_publication', 0),
                               ('qualifies_g3', 'false')):
            with self.subTest(field=field, changed=changed):
                self.rejected(self.value | {field: changed})
        self.rejected(self.value | {'authorization': 'accepted'})
        missing = dict(self.value)
        missing.pop('model_execution')
        self.rejected(missing)

    def test_all_named_checks_required_once_in_exact_order(self):
        for checks in ([], CHECKS[:-1], CHECKS + [CHECKS[0]], list(reversed(CHECKS)),
                       CHECKS[:-1] + ['unexecuted-future-check'], {str(n): name for n, name in enumerate(CHECKS)}):
            with self.subTest(checks=checks):
                self.rejected(self.value | {'checks': checks})

    def test_all_crash_points_require_exact_kill_file_and_overwrite_observations(self):
        for crashes in ([], CUTS[:-1], list(reversed(CUTS)), CUTS + [CUTS[0]]):
            self.rejected(self.value | {'crashes': crashes})
        for index in range(4):
            for change in ({'parent_exit': 0}, {'parent_exit': -9.0}, {'parent_exit': '-9'},
                           {'point': 'during-native-save'}, {'overwrite_refused': not CUTS[index]['overwrite_refused']},
                           {'files': ['proposal.md', 'result.json', 'secret']}, {'verified': True}):
                altered = copy.deepcopy(CUTS)
                altered[index].update(change)
                with self.subTest(index=index, change=change):
                    self.rejected(self.value | {'crashes': altered})
        altered = copy.deepcopy(CUTS)
        altered[2]['files'] = ['proposal.md', 'result.json']
        self.rejected(self.value | {'crashes': altered})
        altered = copy.deepcopy(CUTS)
        altered[3]['files'].reverse()
        self.rejected(self.value | {'crashes': altered})

    def test_duplicate_fields_are_rejected_before_verification(self):
        for raw in ('{"status":"pass","status":"pass"}',
                    '{"crashes":[{"point":"before-child","point":"before-child"}]}',
                    '{"extra":{"pin":"x","pin":"x"}}'):
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                json.loads(raw, object_pairs_hook=proof.unique)
        with self.assertRaises(ValueError):
            proof.verify(self.value | {'artifact_sha256': float('nan')}, self.worker_sha, self.proof_sha)

    def test_fixture_preserves_unicode_trailing_spaces_scope_and_domain_hash(self):
        raw_job, raw_context, target, expected = proof.fixture()
        job, context = json.loads(raw_job), json.loads(raw_context)
        self.assertEqual(job['context_digest'], hashlib.sha256(b'stead.run-context/1\0' + raw_context).hexdigest())
        source = json.loads(context['documents'])[job['outcome_id']]['markdown']
        self.assertEqual(target['base_markdown_sha256'], hashlib.sha256(source.encode()).hexdigest())
        self.assertIn('Original  \n', source)
        self.assertIn('λ', source)
        self.assertEqual(expected, (source + '\nA bounded clarification λ.\n').encode())
        self.assertEqual(target['project_id'], job['project_id'])
        self.assertEqual(context['work_id'], job['work_id'])
        self.assertNotIn('credential', context)

    def test_exact_file_pin_refuses_changed_source_and_malformed_expectation(self):
        with tempfile.TemporaryDirectory(prefix='stead-proof-pin-host-') as folder:
            path = Path(folder) / 'source'
            path.write_bytes(b'host-only source')
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            proof.pin(path, expected)
            with self.assertRaises(ValueError):
                proof.pin(path, 'not-a-pin')
            path.write_bytes(b'changed source')
            with self.assertRaises(ValueError):
                proof.pin(path, expected)

    def test_result_files_reject_aliases_extra_entries_and_public_file_mode(self):
        with tempfile.TemporaryDirectory(prefix='stead-proof-files-host-') as folder:
            output = Path(folder) / 'output'
            self.assertEqual(proof.result_files(output), {})
            output.mkdir(mode=0o700)
            proposal = output / 'proposal.md'
            proposal.write_bytes(b'exact bytes')
            proposal.chmod(0o600)
            self.assertEqual(proof.result_files(output), {'proposal.md': hashlib.sha256(b'exact bytes').hexdigest()})
            proposal.chmod(0o644)
            with self.assertRaises(ValueError):
                proof.result_files(output)
            proposal.chmod(0o600)
            alias = output / 'result.json'
            os.link(proposal, alias)
            with self.assertRaises(ValueError):
                proof.result_files(output)
            alias.unlink()
            alias.symlink_to(proposal)
            with self.assertRaises(ValueError):
                proof.result_files(output)
            alias.unlink()
            (output / 'unrelated').mkdir()
            with self.assertRaises(ValueError):
                proof.result_files(output)

    def test_result_files_reject_public_or_aliased_output_directory(self):
        with tempfile.TemporaryDirectory(prefix='stead-proof-directory-host-') as folder:
            output = Path(folder) / 'output'
            output.mkdir(mode=0o700)
            alias = Path(folder) / 'alias'
            alias.symlink_to(output, target_is_directory=True)
            with self.assertRaises(ValueError):
                proof.result_files(alias)
            output.chmod(0o777)
            with self.assertRaises(ValueError):
                proof.result_files(output)
            output.chmod(0o700)
            with patch.object(proof.os, 'getuid', return_value=os.getuid() + 1), self.assertRaises(ValueError):
                proof.result_files(output)


class GuardianProofBoundaryTests(unittest.TestCase):
    def setUp(self):
        DocWorkerProofVerifierTests.setUp(self)
        self.inputs = {'controller_commit': 'c' * 40, 'candidate_commit': 'd' * 40,
            'controller_files': {'scripts/ci/hosted.py': {'sha256': 'e' * 64},
                'scripts/ci/doc_worker_proof.py': {'sha256': self.proof_sha},
                'scripts/urbit/doc_run_worker.py': {'sha256': self.worker_sha}}}
        self.run_id = 'f' * 32
        self.context = {'run_id': self.run_id, 'unit': 'stead-hosted-' + self.run_id + '.service',
                        'guard_sha256': 'e' * 64, 'uid': 991, 'gid': 992}
        self.launch = proof.diagnostic(proof.canonical(self.value) + b'\n', b'', 0,
                                      eof={'stdout': True, 'stderr': True})
        self.launch.update(status='pass', phase='complete', reason='complete', descendants_reaped=True)
        self.admitted = proof.admission(self.value, self.launch, self.inputs, self.context, 12345)
        self.lease = {'run_id': self.run_id, 'unit': self.context['unit'], 'guard_sha256': 'e' * 64,
                      'service': {'MainPID': '12345'}}

    def test_exact_admission_is_bound_to_run_sources_and_current_guardian(self):
        self.assertIs(proof.verify_admission(self.admitted, self.inputs, self.run_id, self.lease), self.admitted)
        for key in ('run_id', 'unit', 'guard_sha256'):
            changed = dict(self.lease, **{key: 'different'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.verify_admission(self.admitted, self.inputs, self.run_id, changed)
        with self.assertRaises(ValueError):
            proof.verify_admission(self.admitted, self.inputs, self.run_id, self.lease | {'service': {'MainPID': '12346'}})

    def test_reused_forged_or_coerced_admission_is_rejected(self):
        cases = [('run_id', '0' * 32), ('inputs_sha256', '0' * 64), ('controller_commit', '0' * 40),
                 ('candidate_commit', '0' * 40), ('guard_sha256', '0' * 64), ('owner_uid', 0),
                 ('owner_gid', 0), ('owner_uid', True), ('guardian_pid', True), ('guardian_pid', 12345.0)]
        for key, replacement in cases:
            with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                proof.verify_admission(self.admitted | {key: replacement}, self.inputs, self.run_id)
        with self.assertRaises(ValueError):
            proof.verify_admission(self.admitted | {'credential': 'must-not-be-admitted'}, self.inputs, self.run_id)
        changed = copy.deepcopy(self.admitted)
        changed['proof']['artifact_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            proof.verify_admission(changed, self.inputs, self.run_id)

    def test_success_requires_exact_exit_eof_no_stderr_and_reaped_descendants(self):
        for key, replacement in [('exit_code', False), ('exit_code', 0.0), ('exit_code', None),
                                 ('exit_code', 1), ('descendants_reaped', False),
                                 ('status', 'fail'), ('reason', 'unrecognized')]:
            candidate = copy.deepcopy(self.admitted)
            candidate['launch'][key] = replacement
            with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                proof.verify_admission(candidate, self.inputs, self.run_id)
        for stream in ('stdout', 'stderr'):
            for key, replacement in [('eof', False), ('complete', False), ('bytes', True), ('sha256', '0' * 64)]:
                candidate = copy.deepcopy(self.admitted)
                candidate['launch'][stream][key] = replacement
                with self.subTest(stream=stream, key=key), self.assertRaises(ValueError):
                    proof.verify_admission(candidate, self.inputs, self.run_id)

    def test_failure_projection_has_closed_codes_and_no_raw_exception_text(self):
        proof.phase('state-write')
        value = proof.failure_value(PermissionError(13, '/secret/raw-host-path'))
        self.assertEqual(value['phase'], 'state-write')
        self.assertEqual(value['errno'], 'eacces')
        self.assertEqual(value['error_class'], 'PermissionError')
        self.assertNotIn('/secret', proof.canonical(value).decode())
        self.assertEqual(proof.closed_failure(value), value)
        for changed in ({'extra': 'raw'}, {'phase': 'arbitrary-raw-string'}, {'errno': 13}, {'reason': 'host-secret'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                proof.closed_failure(value | changed)

    def test_uid_map_marker_is_exact_and_unrecognized_text_stays_private(self):
        for message in (b'bwrap: setting up uid map: Permission denied\n',
                        b'bwrap: setting up uid map: Operation not permitted\n'):
            seen = proof.diagnostic(b'', message, 1, eof={'stdout': True, 'stderr': True})
            self.assertEqual(seen['reason'], 'uid-map')
            self.assertNotIn(message.decode().strip(), proof.canonical(seen).decode())
        for message in (b'prefix bwrap: setting up uid map: Permission denied\n',
                        b'bwrap: setting up uid map: Permission denied extra\n', b'arbitrary secret\n'):
            seen = proof.diagnostic(b'', message, 1, eof={'stdout': True, 'stderr': True})
            self.assertEqual(seen['reason'], 'nonzero-exit')
            self.assertNotIn('arbitrary secret', proof.canonical(seen).decode())

    def test_diagnostic_numeric_types_and_stream_bounds_fail_closed(self):
        for changed in ({'exit_code': False}, {'exit_code': 1.0}, {'exit_code': 256},
                        {'phase': 'raw'}, {'descendants_reaped': 1}, {'extra': 'text'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                proof.verify_diagnostic(self.launch | changed)
        changed = copy.deepcopy(self.launch)
        changed['stdout'] = proof.stream_summary(b'x' * 16385, eof=True, overflow=True)
        proof.verify_diagnostic(changed)
        changed['stdout']['complete'] = True
        with self.assertRaises(ValueError):
            proof.verify_diagnostic(changed)

    @staticmethod
    def fake_process(stdout, stderr=b'', exit_code=0):
        # Real bounded pipe/EOF observations, no fork or external process.
        from types import SimpleNamespace
        streams = {}
        for name, data in (('stdout', stdout), ('stderr', stderr)):
            read, write = os.pipe()
            os.write(write, data)
            os.close(write)
            streams[name] = os.fdopen(read, 'rb')
        return SimpleNamespace(**streams, returncode=exit_code, poll=lambda: exit_code,
                               wait=lambda **kwargs: exit_code,
                               terminate=lambda: None, kill=lambda: None)

    def test_collector_accepts_only_exact_proof_after_real_pipe_eof(self):
        process = self.fake_process(proof.canonical(self.value) + b'\n')
        ticks = []
        value, observed = proof.observe_process(process, lambda: ticks.append(True), lambda: {1}, {1},
                                                self.worker_sha, self.proof_sha)
        self.assertEqual(value, self.value)
        self.assertEqual(observed, self.launch)
        self.assertTrue(ticks)
        self.assertTrue(process.stdout.closed and process.stderr.closed)

    def test_collector_rejects_corrupt_success_or_unexpected_stderr(self):
        for raw, stderr in ((b'{}\n', b''), (proof.canonical(self.value) + b'\n', b'private unknown text')):
            process = self.fake_process(raw, stderr)
            with self.assertRaises(proof.ProofFailure) as caught:
                proof.observe_process(process, lambda: None, lambda: {1}, {1}, self.worker_sha, self.proof_sha)
            self.assertEqual(caught.exception.diagnostic['status'], 'fail')
            self.assertNotIn('private unknown text', proof.canonical(caught.exception.diagnostic).decode())
            self.assertTrue(process.stdout.closed and process.stderr.closed)

    def test_collector_retains_closed_inner_failure_and_never_accepts_it(self):
        proof.phase('state-write')
        error = proof.failure_value(PermissionError(13, 'secret'))
        process = self.fake_process(proof.canonical(error) + b'\n', exit_code=1)
        with self.assertRaises(proof.ProofFailure) as caught:
            proof.observe_process(process, lambda: None, lambda: {1}, {1}, self.worker_sha, self.proof_sha)
        self.assertEqual(caught.exception.diagnostic['phase'], 'state-write')
        self.assertEqual(caught.exception.diagnostic['errno'], 'eacces')
        self.assertEqual(caught.exception.diagnostic['exit_code'], 1)
        self.assertTrue(caught.exception.diagnostic['descendants_reaped'])

    def test_lifetime_refusal_cannot_be_reinterpreted_as_a_completed_proof(self):
        process = self.fake_process(b'')
        def stopped():
            raise ValueError('Host lifetime stopped')
        with self.assertRaises(proof.ProofFailure) as caught:
            proof.observe_process(process, stopped, lambda: {1}, {1}, self.worker_sha, self.proof_sha)
        self.assertEqual(caught.exception.diagnostic['reason'], 'collector')
        self.assertFalse(caught.exception.diagnostic['stdout']['complete'])
        self.assertTrue(process.stdout.closed and process.stderr.closed)

    def test_first_namespace_command_requires_nonzero_owner_and_exact_pins(self):
        with tempfile.TemporaryDirectory(prefix='proof-command-host-') as folder:
            worker, source = Path(folder) / 'worker.py', Path(folder) / 'proof.py'
            worker.write_bytes(b'worker source'); source.write_bytes(b'proof source')
            args = (worker, source, proof.sha(worker.read_bytes()), proof.sha(source.read_bytes()),
                    {name: name + ':[123]' for name in ('net', 'mnt', 'pid', 'user')})
            with patch.object(proof.os, 'getuid', return_value=0), self.assertRaises(ValueError):
                proof.guardian_command(*args)
            with patch.object(proof.os, 'getuid', return_value=991), patch.object(proof.os, 'getgid', return_value=992):
                command = proof.guardian_command(*args)
                self.assertEqual(command[0], '/usr/bin/bwrap')
                self.assertNotIn('--cap-add', command)
                self.assertNotIn('/execution', command)
                self.assertNotIn('/native', command)
                self.assertIn('--die-with-parent', command)
                self.assertIn('--clearenv', command)
                self.assertEqual(command[command.index('--uid') + 1], '1000')
                bad = list(args); bad[2] = '0' * 64
                with self.assertRaises(ValueError):
                    proof.guardian_command(*bad)
                bad = list(args); bad[4] = {'net': 'net:[123]'}
                with self.assertRaises(ValueError):
                    proof.guardian_command(*bad)


if __name__ == '__main__':
    unittest.main()

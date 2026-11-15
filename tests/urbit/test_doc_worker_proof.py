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
        for target in ('body', 'cutpoint', 'run_controller'):
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


if __name__ == '__main__':
    unittest.main()

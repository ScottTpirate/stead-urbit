"""Host-only Doc worker boundaries; mocked child results prove no isolation."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import doc_run_worker as worker


def uid(number):
    return f'019939ba-4000-7000-8000-{number:012x}'


class DocWorkerTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='stead-doc-worker-host-')
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.source = worker.header(uid(4)) + '# Guide λ\nOriginal  \n'
        self.target = {'kind': 'document', 'project_id': uid(1), 'collection_id': uid(3),
                       'document_id': uid(4), 'expected_revision': '7',
                       'base_markdown_sha256': worker.sha(self.source.encode())}
        self.documents = {uid(5): {'target': worker.canonical(self.target).decode(), 'markdown': self.source}}
        self.context = {'protocol': 'stead.run-context/1', 'project_id': uid(1), 'work_id': uid(2),
                        'execution_contract_revision': '9', 'execution_contract_digest': 'a' * 64,
                        'title': 'Clarify the guide', 'description': 'Keep the exact base.',
                        'acceptance_criteria': 'An independent person reviews the result.',
                        'instructions_digest': 'b' * 64, 'runtime_policy_digest': 'c' * 64,
                        'documents': worker.canonical(self.documents).decode()}
        self.job = {'protocol': 'stead.doc-worker-job/1', 'project_id': uid(1), 'work_id': uid(2),
                    'run_id': uid(6), 'attempt': '1', 'run_contract_sha256': 'd' * 64,
                    'context_digest': worker.domain_hash('stead.run-context/1', worker.canonical(self.context)),
                    'outcome_id': uid(5), 'recipe': worker.RECIPE, 'paragraph': 'A bounded clarification λ.',
                    'max_output_bytes': '32768'}

    def repin(self):
        self.context['documents'] = worker.canonical(self.documents).decode()
        self.job['context_digest'] = worker.domain_hash('stead.run-context/1', worker.canonical(self.context))

    def file(self, name, value):
        output = self.folder / name
        output.write_bytes(value)
        output.chmod(0o600)
        return output

    def args(self):
        raw = worker.canonical(self.job)
        return SimpleNamespace(job=self.file('job.json', raw), job_sha256=worker.sha(raw),
                               context=self.file('context.json', worker.canonical(self.context)),
                               worker_sha256=worker.sha(Path(worker.__file__).read_bytes()),
                               output=self.folder / 'output')

    def response(self, *, markdown=None, target=None):
        selected, proposed = worker.edit(worker.canonical(self.context), self.job)
        return {'target': selected if target is None else target,
                'markdown': proposed if markdown is None else markdown,
                'isolation': {'namespaces': {name: name + ':[host-test-only]' for name in worker.NAMESPACES},
                              'interfaces': ['lo'], 'read_only_input': True, 'no_capabilities': True}}

    @staticmethod
    def child_response(value, status=0):
        def run(command, *, stdout, **kwargs):
            assert kwargs['stdin'] == subprocess.DEVNULL
            assert kwargs['timeout'] == 10
            stdout.write(worker.canonical(value))
            return subprocess.CompletedProcess(command, status)
        return run

    def test_exact_context_preserves_original_utf8_bytes_and_scope(self):
        raw = worker.canonical(self.job)
        self.assertEqual(worker.load_job(raw, worker.sha(raw)), self.job)
        target, markdown = worker.edit(worker.canonical(self.context), self.job)
        self.assertEqual(target, self.target)
        self.assertEqual(markdown, self.source + '\n' + self.job['paragraph'] + '\n')
        self.assertTrue(markdown.encode().startswith(self.source.encode()))
        with self.assertRaisesRegex(ValueError, 'context digest'):
            worker.edit(worker.canonical(self.context) + b' ', self.job)

    def test_closed_job_rejects_unknown_recipe_wrong_attempt_and_ambiguous_json(self):
        for changes in ({'recipe': '/bin/sh'}, {'attempt': True}, {'attempt': '4'},
                        {'attempt': '01'}, {'max_output_bytes': '32769'},
                        {'paragraph': '\ud800'}, {'extra': 'authority'}, {'outcome_id': 'unknown'}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, UnicodeError)):
                raw = worker.canonical(self.job | changes)
                worker.load_job(raw, worker.sha(raw))
        raw = worker.canonical(self.job)[:-1] + b',"attempt":"2"}'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            worker.load_job(raw, worker.sha(raw))
        with self.assertRaisesRegex(ValueError, 'Pinned worker job'):
            worker.load_job(worker.canonical(self.job), '0' * 64)
        for raw in (b'{"a":NaN}', b'{"a":1.0}', b'{"a":1, "b":2}', b'[]'):
            with self.assertRaises(ValueError):
                worker.decode(raw, 100)

    def test_context_rejects_cross_scope_unpinned_bytes_and_duplicate_targets(self):
        for changed in ({'project_id': uid(99)}, {'work_id': uid(99)}, {'extra': ''}):
            context = self.context | changed
            raw = worker.canonical(context)
            job = self.job | {'context_digest': worker.domain_hash('stead.run-context/1', raw)}
            with self.assertRaisesRegex(ValueError, 'context scope'):
                worker.edit(raw, job)
        original = dict(self.documents[uid(5)])
        for target in (self.target | {'project_id': uid(99)}, self.target | {'expected_revision': '01'},
                       self.target | {'base_markdown_sha256': '0' * 64}):
            self.documents[uid(5)] = original | {'target': worker.canonical(target).decode()}
            self.repin()
            with self.assertRaises(ValueError):
                worker.edit(worker.canonical(self.context), self.job)
        self.documents = {uid(5): original, uid(7): dict(original)}
        self.repin()
        with self.assertRaisesRegex(ValueError, 'Duplicate context Doc'):
            worker.edit(worker.canonical(self.context), self.job)

    def test_new_document_requires_empty_base_and_output_budget_is_enforced(self):
        target = self.target | {'expected_revision': '0', 'base_markdown_sha256': ''}
        self.documents[uid(5)] = {'target': worker.canonical(target).decode(), 'markdown': ''}
        self.repin()
        self.assertEqual(worker.edit(worker.canonical(self.context), self.job)[1],
                         worker.header(uid(4)) + '\n' + self.job['paragraph'] + '\n')
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            worker.edit(worker.canonical(self.context), self.job | {'max_output_bytes': '12'})
        self.documents[uid(5)]['markdown'] = self.source
        self.repin()
        with self.assertRaisesRegex(ValueError, 'conflicting base'):
            worker.edit(worker.canonical(self.context), self.job)

    def test_native_unicode_title_and_prose_bounds_are_preserved(self):
        for title in ('λ' * 200, '界' * 200, '📝' * 200):
            self.context['title'] = title
            self.repin()
            self.assertEqual(worker.edit(worker.canonical(self.context), self.job)[0], self.target)
        for title in ('λ' * 201, 'bad\nname', ''):
            self.context['title'] = title
            self.repin()
            with self.assertRaisesRegex(ValueError, 'context scope'):
                worker.edit(worker.canonical(self.context), self.job)
        self.context['title'] = 'Guide'
        self.context['description'] = 'invalid\rprose'
        self.repin()
        with self.assertRaisesRegex(ValueError, 'context scope'):
            worker.edit(worker.canonical(self.context), self.job)

    def test_private_input_rejects_symlink_hardlink_public_permissions_and_oversize(self):
        value = self.file('private', b'abc')
        self.assertEqual(worker.private_input(value, 3), b'abc')
        alias = self.folder / 'alias'
        alias.symlink_to(value)
        with self.assertRaises(OSError):
            worker.private_input(alias, 3)
        alias.unlink()
        os.link(value, alias)
        with self.assertRaises(ValueError):
            worker.private_input(value, 3)
        alias.unlink()
        with self.assertRaises(ValueError):
            worker.private_input(value, 2)
        value.chmod(0o644)
        with self.assertRaises(ValueError):
            worker.private_input(value, 3)

    def test_child_command_has_no_credentials_network_or_writable_input_mount(self):
        command = worker.child_command(self.folder, 'a' * 64, {name: name + ':[1]' for name in worker.NAMESPACES})
        for option in ('--unshare-all', '--clearenv', '--die-with-parent', '--cap-drop', '--new-session'):
            self.assertIn(option, command)
        for option in ('--bind', '--share-net', '--setenv', '/home', '/root', '/etc', '/run'):
            self.assertNotIn(option, command)
        self.assertIn(['--ro-bind', str(self.folder), '/input'], [command[n:n + 3] for n in range(len(command))])

    def test_output_receipt_is_last_and_does_not_claim_native_acceptance(self):
        self.assertNotEqual(os.getuid(), 0, 'Host test requires the normal unprivileged user')
        args = self.args()
        with patch.object(worker.subprocess, 'run', side_effect=self.child_response(self.response())):
            receipt = worker.run(args)
        self.assertEqual(receipt['status'], 'output-ready')
        self.assertEqual(receipt['job_sha256'], args.job_sha256)
        self.assertEqual(receipt['target'], self.target)
        self.assertEqual((args.output / 'result.json').read_bytes(), worker.canonical(receipt))
        self.assertEqual(worker.sha((args.output / 'proposal.md').read_bytes()), receipt['artifact']['sha256'])
        with patch.object(worker.subprocess, 'run') as child, self.assertRaisesRegex(ValueError, 'reconcile'):
            worker.run(args)
        child.assert_not_called()

    def test_bad_child_or_wrong_output_never_publishes_receipt(self):
        args = self.args()
        bad_proof = self.response()
        bad_proof['isolation']['no_capabilities'] = False
        for response, code in ((self.response(), 1), (self.response(markdown='wrong bytes'), 0),
                               (self.response(target=self.target | {'document_id': uid(99)}), 0),
                               (bad_proof, 0), ({'error': 'bounded failure'}, 0)):
            with self.subTest(code=code), patch.object(worker.subprocess, 'run', side_effect=self.child_response(response, code)):
                with self.assertRaises(ValueError):
                    worker.run(args)
            self.assertFalse(args.output.exists())

    def test_interruption_after_artifact_retains_partial_evidence_and_never_overwrites(self):
        args = self.args()
        write = worker.write_new

        def interrupt(directory, name, raw):
            if name == 'result.json':
                raise OSError('host-simulated interruption')
            write(directory, name, raw)

        with patch.object(worker.subprocess, 'run', side_effect=self.child_response(self.response())), patch.object(worker, 'write_new', side_effect=interrupt):
            with self.assertRaises(OSError):
                worker.run(args)
        original = (args.output / 'proposal.md').read_bytes()
        self.assertFalse((args.output / 'result.json').exists())
        with patch.object(worker.subprocess, 'run') as child, self.assertRaisesRegex(ValueError, 'reconcile'):
            worker.run(args)
        child.assert_not_called()
        self.assertEqual((args.output / 'proposal.md').read_bytes(), original)

    def test_worker_source_pin_and_child_timeout_leave_no_success(self):
        args = self.args()
        actual_pin = args.worker_sha256
        args.worker_sha256 = '0' * 64
        with patch.object(worker.subprocess, 'run') as child, self.assertRaisesRegex(ValueError, 'source pin'):
            worker.run(args)
        child.assert_not_called()
        args.worker_sha256 = actual_pin
        with patch.object(worker.subprocess, 'run', side_effect=subprocess.TimeoutExpired('host-mocked-child', 10)):
            with self.assertRaises(subprocess.TimeoutExpired):
                worker.run(args)
        self.assertFalse(args.output.exists())


if __name__ == '__main__':
    unittest.main()

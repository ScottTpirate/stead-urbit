"""GitHub Work import reconstruction and simulated native Home receipts."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_github_work_plan import github_work, issue
from test_portable_import import HOME, MEMBER, Target, importer, portable, uid

import github_work_import as github_import


class GitHubWorkImportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        source = portable.encoded([issue(9, body='Closed body', state='closed', state_reason='completed'),
                                   issue(2, body='Open body'), issue(5, body='x' * 8192)])
        self.source = self.private('source.json', source)
        self.preview = github_work.plan(source)
        raw_preview = portable.encoded(self.preview)
        self.preview_file = self.private('preview.json', raw_preview)
        self.preview_sha = portable.sha(raw_preview)
        self.plan, self.commands = self.commands_for([9, 2])
        self.plan_file = self.root / 'plan.json'
        self.plan_sha = importer.published_plan(self.plan, self.plan_file)
        self.home = Target(self.root / 'progress.json')

    def private(self, name, raw):
        path = self.root / name
        path.write_bytes(raw)
        path.chmod(0o600)
        return path

    def commands_for(self, numbers, origin=HOME):
        return github_import.import_commands(self.preview, self.preview_sha, numbers, origin,
                                             importer.target_member(MEMBER), uid(875), 'Import trial', 'TRIAL')

    def apply(self, limit=16):
        with importer.Progress(self.root) as progress:
            return importer.apply_import(self.home, self.plan, self.plan_sha, self.commands, progress, limit)

    def verify(self):
        with importer.Progress(self.root) as progress:
            return importer.verify_import(self.home, self.plan, self.plan_sha, self.commands, progress)

    def test_exact_preview_provenance_and_only_selected_create_commands(self):
        self.assertEqual(github_import.reviewed_preview(self.source, self.preview_file, self.preview_sha), self.preview)
        self.assertEqual(self.commands_for([2, 9]), (self.plan, self.commands))
        self.assertEqual(self.plan['protocol'], 'stead.github-work-import-plan/1')
        self.assertEqual(self.plan['provenance'], {'protocol': 'stead.github-work-plan/2',
            'repository': github_work.REPOSITORY, 'source_sha256': portable.sha(self.source.read_bytes()),
            'preview_sha256': self.preview_sha})
        self.assertEqual([row['number'] for row in self.plan['selected_issues']], [2, 9])
        self.assertEqual([row['operation'] for row in self.commands], ['project.create', 'work.create', 'work.create'])
        self.assertTrue(all(command['project_id'] == self.plan['project_id']
                            and command['expected_revision'] == '0' for command in self.commands))
        self.assertIn('/issues/2\nGitHub author: source-reviewer\n\nOpen body', self.commands[1]['payload']['description'])
        self.assertEqual(github_import.load_import(self.plan_file, self.plan_sha, self.preview, self.preview_sha),
                         (self.plan, self.commands))

    def test_old_review_reconstructs_exact_bytes_and_original_request_ids(self):
        preview = github_work.plan(self.source.read_bytes(), version=github_work.LEGACY_FORMAT)
        old = portable.encoded(preview)
        self.preview_file.write_bytes(old)
        sha = portable.sha(old)
        reviewed = github_import.reviewed_preview(self.source, self.preview_file, sha)
        self.assertEqual(reviewed, preview)
        self.assertNotIn('author', preview['drafts'][0]['source'])
        plan, commands = github_import.import_commands(reviewed, sha, [2], HOME, importer.target_member(MEMBER),
                                                       uid(875), 'Import trial', 'TRIAL')
        self.assertEqual(commands[1]['payload']['description'],
                         f'GitHub issue #2\nhttps://github.com/{github_work.REPOSITORY}/issues/2\n\nOpen body')
        raw = portable.encoded(plan)
        self.plan_file.write_bytes(raw)
        self.assertEqual(github_import.load_import(self.plan_file, portable.sha(raw), reviewed, sha), (plan, commands))
        for changed, reason in [(dict(preview, protocol='unknown'), 'preview-format'),
                                (dict(preview, repository='other/project'), 'legacy-repository')]:
            data = portable.encoded(changed)
            self.preview_file.write_bytes(data)
            with self.assertRaisesRegex(ValueError, reason):
                github_import.reviewed_preview(self.source, self.preview_file, portable.sha(data))

    def test_missing_incomplete_duplicate_and_excessive_selections_fail(self):
        for selection in ([], [True], [9, 9], list(range(1, 130))):
            with self.subTest(selection=selection), self.assertRaisesRegex(ValueError, 'import-selection'):
                self.commands_for(selection)
        for number in (5, 6):
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, 'incomplete-draft'):
                self.commands_for([number])
        with self.assertRaisesRegex(ValueError, 'disposable-home-required'):
            self.commands_for([2], 'https://home.example.org')

    def test_tampered_preview_even_with_new_digest_and_source_drift_fail(self):
        altered = self.preview | {'drafts': self.preview['drafts'][:1]}
        forged = portable.encoded(altered)
        self.private('forged.json', forged)
        with self.assertRaisesRegex(ValueError, 'preview-reconstruction'):
            github_import.reviewed_preview(self.source, self.root / 'forged.json', portable.sha(forged))
        with self.assertRaisesRegex(ValueError, 'preview-sha256'):
            github_import.reviewed_preview(self.source, self.preview_file, '0' * 64)
        self.source.write_bytes(portable.encoded([issue(2, body='changed')]))
        with self.assertRaisesRegex(ValueError, 'preview-reconstruction'):
            github_import.reviewed_preview(self.source, self.preview_file, self.preview_sha)

    def test_edited_scope_or_steps_fail_even_with_new_plan_digest(self):
        for edited in (self.plan | {'provenance': {}}, self.plan | {'project_id': uid(900)},
                       self.plan | {'steps': []}):
            with self.subTest(plan=edited), self.assertRaisesRegex(ValueError, 'plan-reconstruction'):
                raw = portable.encoded(edited)
                self.plan_file.write_bytes(raw)
                github_import.load_import(self.plan_file, portable.sha(raw), self.preview, self.preview_sha)

    def test_loss_between_work_creation_and_receipt_reuses_exact_command_and_verifies(self):
        self.assertEqual(self.apply(1)['accepted'], 1)
        self.home.loss = True
        first = self.apply()
        self.assertEqual((first['phase'], first['accepted'], first['last_attempt']), ('awaiting-receipt', 1, 'unconfirmed'))
        self.home.current['session_audit_id'] = 'c' * 64
        self.assertEqual(self.apply()['phase'], 'complete')
        self.assertEqual(self.home.calls[1], self.home.calls[2])
        self.assertEqual(len(self.home.events), 3)
        self.assertEqual(self.verify()['work'], 2)
        self.home.events[1]['payload']['description'] = 'different'
        with self.assertRaisesRegex(ValueError, 'readback-mismatch'):
            self.verify()

    def test_confirmation_occurs_before_connecting_to_home(self):
        common = ['apply', '--source', str(self.source), '--preview', str(self.preview_file),
                  '--preview-sha256', self.preview_sha, '--session-file', 'unused-session', '--plan', str(self.plan_file),
                  '--plan-sha256', self.plan_sha, '--progress', str(self.root)]
        with patch.object(importer, 'LocalHome') as local, patch.object(portable, 'session_file') as session, \
                redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(github_import.main(common + ['--confirm-project', uid(900), '--target-home', MEMBER['home']]), 1)
            self.assertEqual(github_import.main(common + ['--confirm-project', self.plan['project_id'], '--target-home', '~nec']), 1)
            local.assert_not_called()
            session.assert_not_called()
        self.assertIn('import-project-confirmation', errors.getvalue())
        self.assertIn('import-target-home', errors.getvalue())

    def test_cli_plan_is_read_only_and_publishes_only_the_reviewed_selection(self):
        result = io.BytesIO()
        destination = self.root / 'cli-plan.json'
        arguments = ['plan', '--source', str(self.source), '--preview', str(self.preview_file),
                     '--preview-sha256', self.preview_sha, '--session-file', 'unused-session',
                     '--target-home', MEMBER['home'], '--issue', '9', '--project-key', 'NEW',
                     '--title', 'New rehearsal', '--output', str(destination)]
        with patch.object(importer, 'LocalHome', return_value=self.home), patch.object(portable, 'session_file'), \
                patch.object(self.home.read, 'walk', return_value=(None, [])), \
                patch.object(github_import.sys, 'stdout', SimpleNamespace(buffer=result)):
            self.assertEqual(github_import.main(arguments), 0)
        receipt = portable.decoded(result.getvalue())
        plan, commands = github_import.load_import(destination, receipt['plan_sha256'], self.preview, self.preview_sha)
        self.assertEqual(receipt['project_id'], plan['project_id'])
        self.assertEqual([row['number'] for row in plan['selected_issues']], [9])
        self.assertEqual(commands[1]['payload']['status'], 'done')
        self.assertEqual(self.home.calls, [])
        self.assertFalse(self.home.progress.exists())

    def test_apply_rechecks_visible_project_key_and_current_binding(self):
        arguments = ['apply', '--source', str(self.source), '--preview', str(self.preview_file),
                     '--preview-sha256', self.preview_sha, '--session-file', 'unused-session', '--plan', str(self.plan_file),
                     '--plan-sha256', self.plan_sha, '--progress', str(self.root), '--confirm-project',
                     self.plan['project_id'], '--target-home', MEMBER['home']]
        with patch.object(importer, 'LocalHome', return_value=self.home), patch.object(portable, 'session_file'), \
                patch.object(self.home.read, 'walk', return_value=(None, [{'project_key': 'TRIAL', 'project_id': uid(901)}])), \
                redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(github_import.main(arguments), 1)
            self.home.current['binding_revision'] = '3'
            self.assertEqual(github_import.main(arguments), 1)
        self.assertIn('import-target-key-in-use', errors.getvalue())
        self.assertIn('import-target-member', errors.getvalue())
        self.assertEqual(self.home.calls, [])
        self.assertFalse(self.home.progress.exists())


if __name__ == '__main__':
    unittest.main()

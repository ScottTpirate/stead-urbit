"""GitHub Work previews use private local files and canonical Work fields."""
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/urbit/github_work_plan.py'
sys.path.insert(0, str(SCRIPT.parent))
import github_work_plan as github_work


def issue(number=1, **changes):
    repository = github_work.REPOSITORY
    return {
        'number': number,
        'repository_url': f'https://api.github.com/repos/{repository}',
        'html_url': f'https://github.com/{repository}/issues/{number}',
        'state': 'open', 'state_reason': None, 'title': 'Read and save Café',
        'body': 'Keep the [handoff](./handoff.md).\r\nDraft.',
        'user': {'login': 'source-reviewer'}, 'labels': [{'name': 'needs triage'}],
        **changes,
    }


def planned(value):
    return github_work.plan(json.dumps(value, ensure_ascii=False).encode('utf-8'))


class GitHubWorkPlanTests(unittest.TestCase):
    def test_stock_pages_become_sorted_canonical_work_drafts(self):
        pull = issue(8, pull_request={'url': 'https://api.github.com/pulls/8'},
                     html_url=f'https://github.com/{github_work.REPOSITORY}/pull/8',
                     title='Excluded PR', body='Excluded PR body')
        report = planned([[pull, issue(6, state='closed', state_reason='not_planned')], [
            issue(5, state='closed', state_reason='duplicate'), issue(1, state_reason='reopened'),
            issue(2, state='closed', state_reason='completed', body=None), issue(3, state='closed')]])
        self.assertEqual(report['input_rows'], 6)
        self.assertEqual(report['excluded_pull_requests'], [8])
        self.assertEqual(report['needs_review'], [])
        self.assertEqual([row['source']['number'] for row in report['drafts']], [1, 2, 3, 5, 6])
        self.assertEqual([row['payload']['status'] for row in report['drafts']],
                         ['todo', 'done', 'done', 'canceled', 'canceled'])
        first = report['drafts'][0]
        self.assertEqual(first['payload'], {'title': 'Read and save Café', 'type': 'task', 'status': 'todo',
            'priority': 'none', 'description': f"GitHub issue #1\n{first['source']['url']}\n\n"
                                              'Keep the [handoff](./handoff.md).\nDraft.'})
        self.assertIn('normalized to LF', first['notes'][0])
        self.assertEqual(report['drafts'][1]['payload']['description'],
                         f'GitHub issue #2\nhttps://github.com/{github_work.REPOSITORY}/issues/2')
        self.assertIn('without a reason', report['drafts'][2]['notes'][0])
        self.assertNotIn('source-reviewer', json.dumps(report))
        self.assertNotIn('Excluded PR body', json.dumps(report))

    def test_scopes_input_to_the_pinned_repository_and_exact_issue_number(self):
        for field, value in (
            ('repository_url', 'https://api.github.com/repos/ScottTpirate/stead'),
            ('html_url', f'https://github.com/{github_work.REPOSITORY}/issues/2'),
            ('html_url', f'https://github.com.evil.test/{github_work.REPOSITORY}/issues/1'),
            ('html_url', f'https://github.com/{github_work.REPOSITORY}/issues/1?query=yes'),
            ('html_url', f'https://github.com/{github_work.REPOSITORY}/pull/1'),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                planned([issue(1, **{field: value})])
        case = issue(1, repository_url=f'https://api.github.com/repos/{github_work.REPOSITORY.lower()}',
                     html_url=f'https://github.com/{github_work.REPOSITORY.lower()}/issues/1')
        self.assertEqual(planned([case])['drafts'][0]['source']['url'], issue()['html_url'])

    def test_rejects_malformed_export_before_planning_any_work(self):
        missing_body = issue()
        del missing_body['body']
        invalid_rows = [issue(number=True), issue(body=['wrong type']), missing_body, issue(title=''),
                        issue(state='done'), issue(state=[]), issue(state='open', state_reason='completed'),
                        issue(state='closed', state_reason='reopened'), issue(body='NUL\0body')]
        for row in invalid_rows:
            with self.subTest(row=row), self.assertRaises(ValueError):
                planned([row])
        for raw in (b'{"message":"Unauthorized"}', b'[[{}],{}]', b'[{"number":1,"number":2}]',
                    b'[NaN]', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                github_work.plan(raw)
        with self.assertRaisesRegex(ValueError, 'duplicate-issue-number'):
            planned([[issue()], [issue()]])

    def test_marks_work_field_limits_without_truncation(self):
        prefix = f'GitHub issue #1\nhttps://github.com/{github_work.REPOSITORY}/issues/1\n\n'
        width = github_work.MAX_DESCRIPTION - len(prefix)
        under = 'é' * (width // 2) + 'x' * (width % 2)
        report = planned([issue(1, title='🗃' * 200, body=under), issue(2, body='失' * width),
                          issue(3, title='x' * 201), issue(4, title='Control\tcharacter')])
        self.assertEqual(len(report['drafts']), 1)
        self.assertEqual(len(report['drafts'][0]['payload']['description'].encode()), github_work.MAX_DESCRIPTION)
        self.assertEqual([row['source']['number'] for row in report['needs_review']], [2, 3, 4])
        self.assertNotIn('失', json.dumps(report, ensure_ascii=False))
        self.assertEqual(report['max_work_per_project'], 128)

    def test_bounds_input_rows_pages_and_bytes(self):
        with patch.object(github_work, 'MAX_ROWS', 2):
            with self.assertRaisesRegex(ValueError, 'issue-count-limit'):
                planned([[issue(1), issue(2)], [issue(3)]])
            with self.assertRaisesRegex(ValueError, 'issue-export-shape'):
                planned([issue(1), issue(2), issue(3)])
        with self.assertRaisesRegex(ValueError, 'issue-page-shape'):
            planned([[issue(i + 1) for i in range(101)]])
        with patch.object(github_work, 'MAX_INPUT', 32), self.assertRaisesRegex(ValueError, 'json-bound'):
            planned([issue()])

    def test_cli_is_deterministic_private_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.json'
            source.write_text(json.dumps([issue(body='private content')]), encoding='utf-8')
            source.chmod(0o600)
            destination = root / 'review.json'

            def command(output):
                return subprocess.run([sys.executable, '-B', SCRIPT, source, '--output', output],
                                      capture_output=True)

            result = command(destination)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            raw = destination.read_bytes()
            self.assertIn(b'private content', raw)
            self.assertNotIn(b'private content', result.stdout)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt['plan_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(command(destination).returncode, 1)
            self.assertEqual(destination.read_bytes(), raw)
            self.assertEqual(list(root.glob('.stead-github-work-*')), [])
            other = root / 'same-plan.json'
            self.assertEqual(command(other).stdout, result.stdout)
            self.assertEqual(other.read_bytes(), raw)
            link = root / 'link.json'
            link.symlink_to(destination)
            self.assertEqual(command(link).returncode, 1)
            self.assertTrue(link.is_symlink())
            public = root / 'shared'
            public.mkdir(mode=0o755)
            self.assertEqual(command(public / 'review.json').returncode, 1)
            self.assertEqual(list(public.iterdir()), [])
            source.write_bytes(b'{"unexpected":"hidden text"}')
            invalid = root / 'invalid.json'
            failure = command(invalid)
            self.assertEqual(failure.returncode, 1)
            self.assertNotIn(b'hidden text', failure.stderr)
            self.assertFalse(invalid.exists())
            source.chmod(0o644)
            self.assertIn(b'private-file-required', command(invalid).stderr)


if __name__ == '__main__':
    unittest.main()

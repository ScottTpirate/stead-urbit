"""Host tests for the exact-source build worker admission and result boundary."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import code_build_worker as worker


def identity(value):
    return f'019939ba-4000-7000-8000-{value:012}'


class BuildWorkerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-build-worker-test-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.bundle = b'# v2 git bundle\nsealed fixture'
        self.job = {'protocol': 'stead.build-job/1', 'job_id': identity(1), 'project_id': identity(2),
                    'proposal_id': identity(3), 'proposal_revision': 1, 'attempt': 1, 'commit': 'a' * 40,
                    'source': 'b' * 64, 'recipe': worker.RECIPE_SHA256, 'bundle_sha256': worker.digest(self.bundle)}

    def file(self, name, content):
        path = self.directory / name
        path.write_bytes(content)
        path.chmod(0o600)
        return path

    def args(self):
        raw = worker.encoded(self.job)
        return SimpleNamespace(job=self.file('job.json', raw), job_sha256=worker.digest(raw),
                               bundle=self.file('fixture.bundle', self.bundle),
                               git_binary=self.file('git', b'pinned Git'), git_sha256=worker.digest(b'pinned Git'),
                               output=self.directory / 'result')

    def test_job_pin_and_exact_recipe_allowlist(self):
        raw = worker.encoded(self.job)
        self.assertEqual(worker.load_job(raw, worker.digest(raw)), self.job)
        with self.assertRaisesRegex(ValueError, 'Trusted build job digest differs'):
            worker.load_job(raw, '0' * 64)
        changed = worker.encoded(dict(self.job, recipe='1' * 64))
        with self.assertRaisesRegex(ValueError, 'Recipe is outside'):
            worker.load_job(changed, worker.digest(changed))
        with self.assertRaisesRegex(ValueError, 'Expected a digest-bound Git bundle'):
            worker.check_bundle(self.bundle + b'altered', self.job)

    def test_rejects_ambiguous_or_unpinned_job_shape(self):
        for changed in (dict(self.job, attempt=True), dict(self.job, commit='main'),
                        dict(self.job, command='/bin/sh'), dict(self.job, proposal_revision=0)):
            raw = worker.encoded(changed)
            with self.assertRaisesRegex(ValueError, 'Invalid exact build job'):
                worker.load_job(raw, worker.digest(raw))
        raw = worker.encoded(self.job).rstrip()[:-1] + b',"attempt":2}'
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            worker.load_job(raw, worker.digest(raw))

    def test_private_input_rejects_alias_or_public_permissions(self):
        path = self.file('input', b'blob')
        alias = self.directory / 'alias'
        os.link(path, alias)
        with self.assertRaisesRegex(ValueError, 'unsafe ownership'):
            worker.read_input(path, 32)
        alias.unlink()
        alias.symlink_to(path)
        with self.assertRaises(OSError):
            worker.read_input(alias, 32)
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'unsafe ownership'):
            worker.read_input(path, 32)

    def test_sandbox_has_only_read_only_inputs_and_bounded_private_scratch(self):
        host = {name: name + ':[1]' for name in worker.NAMESPACES}
        command = worker.sandbox_command(self.directory, '1' * 64, '2' * 64, host)
        self.assertIn('--unshare-all', command)
        self.assertIn('--clearenv', command)
        self.assertIn('--die-with-parent', command)
        self.assertIn('--cap-drop', command)
        self.assertNotIn('--bind', command)
        self.assertNotIn('--share-net', command)
        self.assertNotIn('/home', command)
        inputs = [(command[index + 1], command[index + 2])
                  for index, value in enumerate(command) if value == '--ro-bind']
        self.assertIn((str(self.directory), '/input'), inputs)

    def test_recipe_reads_exact_oids_and_rejects_link_modes(self):
        commit, tree, oid = 'a' * 40, 'b' * 40, 'c' * 40
        sizes = {commit: ('commit', 12), tree: ('tree', 4), oid: ('blob', 3)}
        prefix = [b'', b'', b'', b'', b'', tree.encode() + b'\n']
        for mode in ('100644', '120000'):
            listing = f'{mode} blob {oid}\ttool.py'.encode() + b'\x00'
            with patch.object(worker, 'object_sizes', return_value=sizes), patch.object(
                    worker, 'git', side_effect=[*prefix, listing, b'abc']) as git:
                if mode == '120000':
                    with self.assertRaisesRegex(ValueError, 'tree entry is outside'):
                        worker.tree_manifest(commit)
                    continue
                manifest = worker.tree_manifest(commit)
                self.assertEqual(manifest['commit'], commit)
                self.assertEqual(manifest['tree'], tree)
                self.assertEqual(manifest['files'], [{'path': 'tool.py', 'mode': mode, 'oid': oid,
                                                    'bytes': 3, 'sha256': worker.digest(b'abc')}])
                git.assert_any_call('fsck', '--full', '--strict', commit)
                git.assert_any_call('cat-file', 'blob', oid, limit=3)
                self.assertFalse(any(call.args[0] in ('checkout', 'worktree') for call in git.call_args_list))

    @staticmethod
    def child_result(status, raw):
        def result(command, *, stdout, **_):
            stdout.write(raw)
            return subprocess.CompletedProcess(args=command, returncode=status)
        return result

    def test_verified_artifact_receipt_is_written_once_and_bound_to_job(self):
        if os.getuid() == 0:
            self.skipTest('Worker publication requires an unprivileged directory owner')
        args = self.args()
        manifest = {'protocol': worker.RECIPE, 'commit': self.job['commit'], 'files': []}
        response = worker.encoded({'manifest': manifest, 'isolation': {'interfaces': ['lo']}})
        with patch.object(worker.subprocess, 'run', side_effect=self.child_result(0, response)):
            receipt = worker.run(args)
        self.assertEqual((args.output / 'tree-manifest.json').read_bytes(), worker.encoded(manifest))
        self.assertEqual((args.output / 'result.json').read_bytes(), worker.encoded(receipt))
        self.assertEqual(receipt['attestation'], {'source': self.job['source'], 'recipe': self.job['recipe'],
                         'output': worker.digest(worker.encoded(manifest)), 'outcome': 'passed'})
        self.assertEqual(receipt['job_sha256'], args.job_sha256)
        with self.assertRaisesRegex(ValueError, 'output already exists'):
            worker.run(args)

    def test_sandbox_failure_and_wrong_commit_publish_no_result(self):
        if os.getuid() == 0:
            self.skipTest('Worker publication requires an unprivileged directory owner')
        args = self.args()
        for status, response, error in (
            (1, b'{"error":"network namespace"}', 'Isolated recipe failed'),
            (0, b'{"manifest":{"commit":"wrong"}}', 'artifact differs from reviewed commit'),
            (0, b'x' * (worker.MAX_ARTIFACT + 8193), 'no bounded result'),
        ):
            with patch.object(worker.subprocess, 'run', side_effect=self.child_result(status, response)), self.assertRaisesRegex(ValueError, error):
                worker.run(args)
            self.assertFalse(args.output.exists())


if __name__ == '__main__':
    unittest.main()

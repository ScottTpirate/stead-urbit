import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'urbit'))
import dogfood_rehearsal as dogfood


@unittest.skipUnless(shutil.which('git'), 'stock Git is required')
class DogfoodRehearsalTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.binary = Path(shutil.which('git')).resolve()
        self.source = dogfood.Git(self.binary, self.root / 'source.git')
        self.default_branch = 'refs/heads/main'
        self.source.init_bare(self.default_branch)
        tree = self.source.run('mktree', data=b'').stdout.strip()
        main = self.source.run('commit-tree', tree, '-m', 'Original commit').stdout.strip().decode('ascii')
        self.source.run('update-ref', self.default_branch, main)
        self.source.run('tag', '-a', 'v1', '-m', 'Original annotated tag', main)
        self.source.run('update-ref', 'refs/heads/local-only', main)
        self.outside_ref = dogfood.add_test_commit(self.source, 'refs/heads/local-only', main, 'Excluded commit')
        self.refs = {name: oid for name, oid in self.source.refs().items()
                     if name != 'refs/heads/local-only'}

    def test_pinned_bundle_survives_cutover_rehearsal_and_rejects_mirror_drift(self):
        output = self.root / 'output'
        original = self.source.refs()
        report = dogfood.rehearse(self.binary, self.source.path, output, self.refs, self.default_branch)
        self.assertEqual(report['source']['refs'], self.refs)
        self.assertEqual(report['source']['object_kinds'], {'blob': 0, 'commit': 1, 'tree': 1, 'tag': 1})
        self.assertEqual(report['recovery']['object_kinds'], {'blob': 0, 'commit': 3, 'tree': 1, 'tag': 1})
        self.assertEqual(report['recovery']['refs']['refs/tags/v1'], original['refs/tags/v1'])
        self.assertTrue(report['mirror']['drift_refused'])
        self.assertEqual(self.source.refs(), original)

        recovered = dogfood.Git(self.binary, self.root / 'independent.git')
        dogfood.recover_bundle(recovered, output / 'rehearsal.bundle', report['recovery']['bundle'],
                               report['recovery']['refs'], self.default_branch)
        self.assertNotEqual(recovered.run('cat-file', '-e', self.outside_ref, check=False).returncode, 0)
        self.assertNotEqual(recovered.run('cat-file', '-e', report['mirror']['drift_oid'], check=False).returncode, 0)

    def test_stale_source_pin_stops_before_snapshot(self):
        output = self.root / 'output'
        refs = self.refs | {self.default_branch: self.outside_ref}
        with self.assertRaisesRegex(dogfood.RehearsalError, 'Source ref changed'):
            dogfood.rehearse(self.binary, self.source.path, output, refs, self.default_branch)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()

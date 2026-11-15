"""Host-only input-boundary checks; these do not execute native source."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('ci_composition', ROOT / 'scripts/ci/local.py')
CI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CI)
PREFIX = 'native/core/desk/'


class CiCompositionTests(unittest.TestCase):
    def setUp(self):
        self.controller = {
            PREFIX + name: name.encode() for name in (
                'app/stead-home.hoon', 'app/stead-identity.hoon',
                'lib/stead-core.hoon', 'lib/stead-core-v1.hoon',
                'lib/stead-codec-v1.hoon', 'lib/stead-git.hoon',
                'tests/stead-session.hoon', 'gen/stead-build-probe.hoon',
                'mar/stead-control-1.hoon', 'mar/stead-command-3.hoon',
                'web/stead/inventory.hoon')
        }
        self.controller.update({
            'scripts/ci/migration.hoon': b'trusted migration',
            'scripts/ci/controls/missing.hoon': b'trusted missing control',
            'scripts/ci/controls/compiler.hoon': b'trusted compiler control',
            'scripts/ci/controls/delay.hoon': b'trusted delay control',
        })
        self.candidate = {name: raw for name, raw in self.controller.items()
                          if name.startswith(PREFIX)}

    def test_new_library_requires_exact_reviewed_controller_path(self):
        path = PREFIX + 'lib/stead-work-contract.hoon'
        self.candidate[path] = b'candidate work contract'
        with self.assertRaisesRegex(ValueError, 'Candidate collision'):
            CI.compose(self.controller, self.candidate)
        self.controller[path] = b'reviewed work contract'
        combined, product = CI.compose(self.controller, self.candidate)
        self.assertEqual(combined[path], b'candidate work contract')
        self.assertEqual(product[path], b'candidate work contract')
        self.candidate[PREFIX + 'lib/stead-unreviewed.hoon'] = b'unknown path'
        with self.assertRaisesRegex(ValueError, 'Candidate collision'):
            CI.compose(self.controller, self.candidate)

    def test_candidate_cannot_replace_add_or_remove_required_tests(self):
        path = PREFIX + 'tests/stead-work-contract.hoon'
        self.candidate[path] = b'candidate test'
        with self.assertRaisesRegex(ValueError, 'Candidate collision'):
            CI.compose(self.controller, self.candidate)
        self.controller[path] = b'trusted test'
        with self.assertRaisesRegex(ValueError, 'Candidate collision'):
            CI.compose(self.controller, self.candidate)
        self.candidate.pop(path)
        self.candidate.pop(PREFIX + 'tests/stead-session.hoon')
        combined, product = CI.compose(self.controller, self.candidate)
        self.assertEqual(combined[path], b'trusted test')
        self.assertEqual(combined[PREFIX + 'tests/stead-session.hoon'], b'tests/stead-session.hoon')
        self.assertNotIn(path, product)

    def test_trusted_predecessor_and_control_bytes_cannot_change(self):
        for relative in ('lib/stead-core-v1.hoon', 'lib/stead-codec-v1.hoon',
                         'lib/stead-git.hoon', 'mar/stead-control-1.hoon',
                         'gen/stead-build-probe.hoon'):
            with self.subTest(relative=relative):
                candidate = self.candidate | {PREFIX + relative: b'replacement'}
                with self.assertRaisesRegex(ValueError, 'Candidate collision'):
                    CI.compose(self.controller, candidate)

    def test_missing_product_or_predecessor_rejected(self):
        for relative in ('app/stead-home.hoon', 'lib/stead-core.hoon',
                         'mar/stead-command-3.hoon', 'lib/stead-core-v1.hoon'):
            with self.subTest(relative=relative):
                candidate = dict(self.candidate)
                candidate.pop(PREFIX + relative)
                with self.assertRaises(ValueError):
                    CI.compose(self.controller, candidate)

    def test_only_content_addressed_asset_paths_extend_web_inventory(self):
        valid = PREFIX + 'web/stead/asset-' + 'a' * 64 + '.stead-asset'
        combined, product = CI.compose(self.controller, self.candidate | {valid: b'new asset'})
        self.assertEqual(product[valid], b'new asset')
        for path in (PREFIX + 'web/stead/new.js', valid + '.py',
                     'scripts/ci/worker.py', PREFIX + 'ted/stead-ci-delay.hoon'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                CI.compose(self.controller, self.candidate | {path: b'unreviewed'})

    def test_negative_controls_and_migration_come_from_controller(self):
        combined, product = CI.compose(self.controller, self.candidate)
        for relative, source in (
                ('gen/stead-ci-migration-probe.hoon', 'migration.hoon'),
                ('controls/stead-ci-missing.hoon', 'controls/missing.hoon'),
                ('controls/stead-ci-compiler.hoon', 'controls/compiler.hoon'),
                ('ted/stead-ci-delay.hoon', 'controls/delay.hoon')):
            with self.subTest(relative=relative):
                self.assertEqual(combined[PREFIX + relative], self.controller['scripts/ci/' + source])
                self.assertNotIn(PREFIX + relative, product)


if __name__ == '__main__':
    unittest.main()

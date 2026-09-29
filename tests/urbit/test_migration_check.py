"""Host evidence/admission controls; native calls are explicitly mocked."""
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import migration_check as lane
import digests


class MigrationDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'logs').mkdir()
        self.log = self.root / 'logs/zod.log'
        self.log.write_bytes(b'older unrelated compiler failure\n')
        self.probe = self.root / 'migration.hoon'
        self.probe.write_bytes(b'synthetic uncompiled fixture\n')
        self.native = self.root / 'native'; (self.native / 'gen').mkdir(parents=True)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(lane, 'PROBE', self.probe))
        self.stack.enter_context(patch.object(lane, 'tree_sha', side_effect=lambda _: 'native'))
        self.stack.enter_context(patch.object(lane, 'source_sha', return_value='loaded'))
        self.stack.enter_context(patch.object(lane, 'sha', side_effect=lambda path:
            'toolchain' if str(path) == '/toolchain.json' else digests.sha(path)))
        self.context = {'migration_sha256': digests.sha(self.probe)}
        self.stack.enter_context(patch.object(lane.execution_policy, 'read_json', return_value=self.context))
        copytree = lane.shutil.copytree
        self.stack.enter_context(patch.object(lane.shutil, 'copytree', side_effect=lambda source, target, *args, **kwargs:
            copytree(self.native if str(source) == '/native/core/desk' else source, target, *args, **kwargs)))
        self.install = self.stack.enter_context(patch.object(lane.native_install, 'install', return_value={'fixture': 'mocked'}))
        self.output = lane.EXPECTED
        self.append = b'new synthetic compiler output\n'
        def dojo(ship, source, **kwargs):
            self.assertEqual((ship, source, kwargs), ('zod', '+stead-ci-migration-probe', {'timeout': 180}))
            with self.log.open('ab') as stream:
                stream.write(self.append)
            return self.output
        self.host = {'STATE': self.root, 'TEAM': object(), 'LOADED_SOURCE_DIGEST': 'loaded',
            **{name: Mock() for name in ('execution_check', 'all_stop', 'copy_seed_to_live', 'launch', 'wait_ready')},
            'dojo': Mock(side_effect=dojo)}

    def report(self):
        return json.loads(next((self.root / 'logs').glob('migration-check-*.json')).read_text())

    def test_exact_result_retains_only_new_log_interval_and_cleans_up(self):
        result = lane.run(self.host)
        self.assertEqual(result['status'], 'pass')
        self.assertFalse(result['qualifies_phase'])
        report = self.report()
        self.assertEqual(bytes.fromhex(report['compiler_log']['hex']), self.append)
        self.assertEqual(report['migration']['output'], self.output)
        self.assertTrue(report['cleanup'])
        self.host['launch'].assert_called_once_with('zod', fresh=True)
        self.assertEqual(self.host['all_stop'].call_count, 2)

    def test_wrong_or_empty_result_fails_and_is_retained(self):
        for value in ('', '~', '%generator-build-fail', lane.EXPECTED + ' extra'):
            with self.subTest(value=value):
                self.output = value
                self.assertEqual(lane.run(self.host)['status'], 'fail')
                self.assertEqual(self.report()['migration']['output'], value)
                self.assertTrue(self.report()['cleanup'])

    def test_changed_startup_probe_or_loaded_source_cannot_launch(self):
        self.context['migration_sha256'] = 'stale'
        self.assertEqual(lane.run(self.host)['status'], 'fail')
        self.host['launch'].assert_not_called()
        self.host['copy_seed_to_live'].assert_not_called()
        self.install.assert_not_called()

    def test_cleanup_failure_overrides_exact_success(self):
        self.host['all_stop'].side_effect = [None, RuntimeError('synthetic cleanup failure')]
        self.assertEqual(lane.run(self.host)['status'], 'fail')
        self.assertFalse(self.report()['cleanup'])

    def test_log_overflow_fails(self):
        self.append = b'x' * 262145
        self.assertEqual(lane.run(self.host)['status'], 'fail')
        self.assertEqual(self.report()['compiler_log']['bytes'], 262144)
        self.assertTrue(self.report()['compiler_log']['truncated'])

    def test_log_capture_failure_does_not_replace_native_timeout(self):
        def failed(*args, **kwargs):
            self.log.unlink()
            raise TimeoutError('synthetic native timeout')
        self.host['dojo'].side_effect = failed
        self.assertEqual(lane.run(self.host)['status'], 'fail')
        self.assertEqual(self.report()['error'], 'TimeoutError: synthetic native timeout')
        self.assertIn('FileNotFoundError', self.report()['capture_error'])

    def test_changed_probe_during_execution_fails(self):
        original = self.host['dojo'].side_effect
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            self.probe.write_bytes(b'changed')
            return result
        self.host['dojo'].side_effect = changed
        self.assertEqual(lane.run(self.host)['status'], 'fail')
        self.assertIn('Source/input changed', self.report()['error'])

    def test_directory_log_capture_closes_descriptor(self):
        def directory(*args, **kwargs):
            self.log.unlink()
            self.log.mkdir()
            return lane.EXPECTED
        self.host['dojo'].side_effect = directory
        for _ in range(5):
            before = len(list(Path('/proc/self/fd').iterdir()))
            self.assertEqual(lane.run(self.host)['status'], 'fail')
            self.assertIn('not regular', self.report()['capture_error'])
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), before)
            self.log.rmdir()
            self.log.write_bytes(b'new log')


if __name__ == '__main__':
    unittest.main()

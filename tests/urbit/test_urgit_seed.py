"""Independent warm-bootstrap host negatives; no native process is launched.

All piers below are tiny authored filesystem fixtures, not Urbit state. Native
identity responses, completed audit vectors, and temperatures are explicitly
mocked. Real copying, hashing, ownership checks and flock behavior are exercised.
"""
from contextlib import contextmanager, redirect_stdout
import copy
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/urbit'))
import execution_policy as G
import digests as D
import urgit_audit as A
import urgit_seed as S

spec = importlib.util.spec_from_file_location('reviewed_urgit_bootstrap',
    REPO / 'scripts/urbit/urgit_eval/bootstrap.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

PIN_BYTES = b'{"synthetic_toolchain":1}\n'
PIN_SHA = hashlib.sha256(PIN_BYTES).hexdigest()


def expected_tree(path):
    """Independent canonical digest for our known regular synthetic files."""
    rows = []
    size = 0
    for item in sorted(path.rglob('*')):
        if item.is_file():
            raw = item.read_bytes()
            size += len(raw)
            rows.append(hashlib.sha256(raw).hexdigest() + '  '
                        + item.relative_to(path).as_posix() + '\n')
    return {'sha256': hashlib.sha256(''.join(rows).encode()).hexdigest(),
            'files': len(rows), 'bytes': size}


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='stead-urgit-seed-host-') as temp:
        root = Path(temp)
        state = root / '.piers/fakes'
        for path in (root / '.piers', state, state / 'seed', root / 'input', root / '.runtime'):
            path.mkdir(mode=0o700)
        (root / 'toolchain.json').write_bytes(PIN_BYTES)
        (state / '.stead-disposable.json').write_text(json.dumps(S.MARKER))
        (state / 'lifecycle.lock').touch(mode=0o600)
        ships = {}
        for ship in S.SHIPS:
            pier = state / 'seed' / ship
            pier.mkdir(mode=0o700)
            (pier / '.urb').mkdir(mode=0o700)
            (pier / 'base').mkdir(mode=0o700)
            (pier / '.urb/synthetic-state').write_bytes(('not a real pier: ' + ship).encode())
            (pier / 'base/synthetic.hoon').write_bytes(b':: authored host fixture only\n')
            ships[ship] = expected_tree(pier)['sha256']
        (state / 'seed/manifest.json').write_text(json.dumps({
            'format': 1, 'toolchain_sha256': PIN_SHA, 'ships': ships}))
        yield root


class StoppedSeedBoundary(unittest.TestCase):
    def test_prefix_file_directory_order_matches_existing_seed_manifest(self):
        with fixture() as root:
            source = root / '.piers/fakes/seed/zod'
            (source / 'base/fuse').mkdir(mode=0o700)
            for name in ('fuse/help.txt', 'fuse-list.hoon', 'fuse.hoon'):
                (source / 'base' / name).write_text('authored prefix fixture: ' + name)
            path_order = [p.relative_to(source).as_posix()
                          for p in sorted(source.rglob('*')) if p.is_file()]
            self.assertNotEqual(path_order, sorted(path_order))
            expected = D.tree_sha(source)
            self.assertEqual(expected_tree(source)['sha256'], expected)
            self.assertEqual(S.tree(source)['sha256'], expected)
            manifest_path = root / '.piers/fakes/seed/manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['ships']['zod'] = expected
            manifest_path.write_text(json.dumps(manifest))
            with S.snapshot(root, root / 'input', PIN_SHA) as record:
                self.assertEqual(record['copied']['sha256'], expected)
                self.assertEqual(D.tree_sha(root / 'input/seed-zod'), expected)
            self.assertEqual(D.tree_sha(source), expected)

    def test_exact_snapshot_preserves_original_and_owns_separate_bytes(self):
        with fixture() as root:
            source, target = root / '.piers/fakes/seed/zod', root / 'input/seed-zod'
            wanted = expected_tree(source)
            with S.snapshot(root, root / 'input', PIN_SHA) as record:
                self.assertEqual(record['mode'], 'verified-stopped-fake-seed')
                self.assertEqual(record['source'], '.piers/fakes/seed/zod')
                self.assertEqual(record['copied'], wanted)
                self.assertEqual(expected_tree(target), wanted)
                for original in source.rglob('*'):
                    if original.is_file():
                        self.assertNotEqual(original.stat().st_ino,
                            (target / original.relative_to(source)).stat().st_ino)
                with (root / '.piers/fakes/lifecycle.lock').open('rb') as second:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(expected_tree(source), wanted)

    def test_absent_seed_selects_cold_without_importing_another_pier(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'input').mkdir(mode=0o700)
            (root / 'live').mkdir()
            (root / 'live/private-sentinel').write_text('must not copy this')
            with S.snapshot(root, root / 'input', PIN_SHA) as record:
                self.assertEqual(record['mode'], 'cold')
            self.assertEqual(list((root / 'input').iterdir()), [])

    def test_redirected_ancestor_cannot_hide_as_absent_seed(self):
        with fixture() as root:
            shutil.rmtree(root / '.piers/fakes/seed')
            (root / '.piers').rename(root / 'redirect-target')
            (root / '.piers').symlink_to(root / 'redirect-target', target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                with S.snapshot(root, root / 'input', PIN_SHA):
                    self.fail('Redirected ownership boundary accepted as cold fallback')

    def test_missing_and_wrong_marker_are_not_cold_fallback(self):
        for missing in (True, False):
            with self.subTest(missing=missing), fixture() as root:
                marker = root / '.piers/fakes/.stead-disposable.json'
                marker.unlink() if missing else marker.write_text('{"purpose":"not a fake seed"}')
                with self.assertRaises((ValueError, OSError)):
                    with S.snapshot(root, root / 'input', PIN_SHA):
                        self.fail('Invalid present seed admitted')

    def test_manifest_missing_extra_wrong_toolchain_or_wrong_hash_rejected(self):
        for mutation in ('missing-ship', 'extra-ship', 'toolchain', 'hash'):
            with self.subTest(mutation=mutation), fixture() as root:
                path = root / '.piers/fakes/seed/manifest.json'
                data = json.loads(path.read_text())
                if mutation == 'missing-ship':
                    data['ships'].pop('bud')
                elif mutation == 'extra-ship':
                    data['ships']['marzod'] = 'a' * 64
                elif mutation == 'toolchain':
                    data['toolchain_sha256'] = 'a' * 64
                else:
                    data['ships']['bus'] = 'a' * 64
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    with S.snapshot(root, root / 'input', PIN_SHA):
                        self.fail('Malformed manifest admitted')

    def test_duplicate_keys_and_boolean_format_are_rejected(self):
        for relative in ('.stead-disposable.json', 'seed/manifest.json'):
            for replacement in ('"format": true', '"format": 99, "format": 1'):
                with self.subTest(path=relative, replacement=replacement), fixture() as root:
                    path = root / '.piers/fakes' / relative
                    path.write_text(path.read_text().replace('"format": 1', replacement, 1))
                    with self.assertRaises(ValueError):
                        with S.snapshot(root, root / 'input', PIN_SHA):
                            self.fail('Ambiguous or mistyped identity metadata accepted')

    def test_corruption_of_an_unselected_ship_blocks_the_snapshot(self):
        with fixture() as root:
            (root / '.piers/fakes/seed/bud/.urb/synthetic-state').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                with S.snapshot(root, root / 'input', PIN_SHA):
                    self.fail('Only selected zod was checked')

    def test_symlinked_roots_metadata_pier_and_child_are_rejected(self):
        for relative in ('.piers', '.piers/fakes/.stead-disposable.json',
                         '.piers/fakes/seed/manifest.json', '.piers/fakes/seed/zod',
                         '.piers/fakes/seed/zod/.urb/synthetic-state'):
            with self.subTest(path=relative), fixture() as root:
                path = root / relative
                destination = path.with_name(path.name + '-original')
                path.rename(destination)
                path.symlink_to(destination, target_is_directory=destination.is_dir())
                with self.assertRaises((ValueError, OSError)):
                    with S.snapshot(root, root / 'input', PIN_SHA):
                        self.fail('Redirected seed input admitted')

    def test_hardlinks_and_special_files_are_rejected(self):
        for special in ('hardlink', 'fifo'):
            with self.subTest(kind=special), fixture() as root:
                pier = root / '.piers/fakes/seed/zod'
                path = pier / 'forbidden'
                if special == 'hardlink':
                    os.link(pier / '.urb/synthetic-state', path)
                else:
                    os.mkfifo(path)
                with self.assertRaises(ValueError):
                    S.tree(pier)

    def test_private_owner_and_mode_are_required(self):
        with fixture() as root:
            state = root / '.piers/fakes'
            state.chmod(0o755)
            with self.assertRaises(ValueError):
                S.inventory(root, PIN_SHA)
            state.chmod(0o700)
            real_uid = os.getuid()
            with patch.object(S.os, 'getuid', return_value=real_uid + 1):
                with self.assertRaises(ValueError):
                    S.inventory(root, PIN_SHA)

    def test_busy_lifecycle_owner_and_existing_destination_are_rejected(self):
        with fixture() as root:
            with (root / '.piers/fakes/lifecycle.lock').open('rb') as owner:
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    with S.snapshot(root, root / 'input', PIN_SHA):
                        self.fail('Active fixture owner ignored')
            destination = root / 'input/seed-zod'
            destination.mkdir(mode=0o700)
            (destination / 'sentinel').write_text('preserve')
            with self.assertRaises(FileExistsError):
                with S.snapshot(root, root / 'input', PIN_SHA):
                    self.fail('Existing input snapshot overwritten')
            self.assertEqual((destination / 'sentinel').read_text(), 'preserve')

    def test_copy_and_source_changes_during_snapshot_are_rejected(self):
        for changed in ('source', 'copy'):
            with self.subTest(changed=changed), fixture() as root:
                original = S.tree
                def changed_copy(path, destination=None):
                    result = original(path, destination)
                    if destination is not None:
                        target = path if changed == 'source' else destination
                        (target / '.urb/synthetic-state').write_text('changed during copy')
                    return result
                with patch.object(S, 'tree', side_effect=changed_copy):
                    with self.assertRaises(ValueError):
                        with S.snapshot(root, root / 'input', PIN_SHA):
                            self.fail('Changing snapshot admitted')

    def test_source_and_readonly_input_changes_during_audit_are_rejected(self):
        for relative in ('.piers/fakes/seed/zod', 'input/seed-zod'):
            with self.subTest(path=relative), fixture() as root:
                with self.assertRaises(ValueError):
                    with S.snapshot(root, root / 'input', PIN_SHA):
                        (root / relative / '.urb/synthetic-state').write_text('fault injection')

    def test_seed_entry_and_byte_limits_are_enforced(self):
        with fixture() as root:
            for name, bound in (('MAX_FILES', 1), ('MAX_BYTES', 4)):
                with self.subTest(bound=name), patch.object(S, name, bound):
                    with self.assertRaisesRegex(ValueError, 'bound'):
                        S.tree(root / '.piers/fakes/seed/zod')


class BootstrapBoundary(unittest.TestCase):
    def test_warm_argv_only_boots_work_pier_and_cold_keeps_explicit_creation(self):
        warm = B.argv('verified-stopped-fake-seed', 31)
        cold = B.argv('cold', 31)
        self.assertEqual(warm[-1], '/work/zod')
        for flag in ('-c', '-F', '-B', '-A'):
            self.assertNotIn(flag, warm)
            self.assertIn(flag, cold)
        self.assertIn('-L', warm)
        self.assertIn('127.0.0.1', warm)
        self.assertNotIn('/input/seed-zod', warm)
        self.assertNotIn('.piers/fakes/seed/zod', warm)
        with self.assertRaises(ValueError):
            B.argv('/arbitrary/live-pier', 31)

    def test_wrong_identity_kernel_or_existing_urgit_native_observation_rejected(self):
        B.validate('~zod\n', '%408\n', '%.y\n')  # Authored response, not a native probe.
        for values in (('~bus', '%408', '%.y'), ('~zod', '%409', '%.y'),
                       ('~zod', '%408', '%.n'), ('', '%408', '%.y')):
            with self.subTest(values=values), self.assertRaises(ValueError):
                B.validate(*values)

    def test_actual_work_copy_must_match_bound_snapshot(self):
        with fixture() as root:
            with S.snapshot(root, root / 'input', PIN_SHA) as baseline:
                work = root / 'work-zod'
                shutil.copytree(root / 'input/seed-zod', work)
                B.verify_work(work, baseline)
                (work / '.urb/synthetic-state').write_text('corrupted boot copy')
                with self.assertRaises(ValueError):
                    B.verify_work(work, baseline)


def reading(temperature=45):
    now = time.monotonic()
    return G.Sample(now, now, {'thermal_zone0:x86_pkg_temp': temperature},
                    ('thermal_zone0:x86_pkg_temp',))


class GuardedPreparationBoundary(unittest.TestCase):
    def test_factory_holds_common_lock_and_fresh_hot_sample_prevents_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            samples = []
            def sampler():
                sample = reading(45 if not samples else 76)
                samples.append(sample)
                return sample
            def factory(control, run_id):
                with self.assertRaises(BlockingIOError):
                    with G.HeavyRunLock(root / '.runtime/native-execution.lock'):
                        self.fail('Factory did not own common lifetime lock')
                return ['NEVER-EXECUTE-NATIVE']
            with patch.object(G.subprocess, 'Popen', side_effect=AssertionError('No native allowed')) as child:
                result = G.run_guarded(factory, root=root, label='host-seed-review', sampler=sampler)
            child.assert_not_called()
            self.assertEqual(result['status'], 'failed')
            self.assertIn('Start temperature', result['reason'])
            self.assertEqual(len(samples), 2)
            retained = [event['sample']['readings_c']['thermal_zone0:x86_pkg_temp']
                        for event in result['events'] if 'sample' in event]
            self.assertIn(76, retained)

    def test_stop_during_factory_prevents_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            stopped = False
            def factory(control, run_id):
                nonlocal stopped
                stopped = True
                return ['NEVER-EXECUTE-NATIVE']
            with patch.object(G.subprocess, 'Popen', side_effect=AssertionError('No native allowed')) as child:
                result = G.run_guarded(factory, root=Path(temp), label='host-seed-stop',
                                       sampler=reading, stop_requested=lambda: stopped)
            child.assert_not_called()
            self.assertEqual(result['status'], 'failed')
            self.assertIn('Operator stop', result['reason'])

    def test_busy_common_owner_prevents_factory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.runtime').mkdir(mode=0o700)
            with G.HeavyRunLock(root / '.runtime/native-execution.lock'):
                with patch.object(G.subprocess, 'Popen', side_effect=AssertionError('No native allowed')) as child:
                    with patch.object(S, 'snapshot', side_effect=AssertionError('Must not snapshot')) as snapshot:
                        result = G.run_guarded(lambda *_: snapshot(), root=root,
                                              label='host-seed-busy', sampler=reading)
            snapshot.assert_not_called()
            child.assert_not_called()
            self.assertEqual(result['status'], 'failed')


class AuditIntegrationBoundary(unittest.TestCase):
    def run_authored_audit(self, root, corrupt=False):
        run = root / 'audit'
        run.mkdir(mode=0o700)
        for name in ('input', 'evidence', 'output', 'control'):
            (run / name).mkdir(mode=0o700)
        evidence, output, control = run / 'evidence', run / 'output', run / 'control'
        authored = {'status': 'passed', 'checks': [
            {'name': name, 'passed': True} for name in A.EXPECTED_CHECKS]}
        for name in A.OUTPUT_LIMITS:
            (output / name).write_text(json.dumps(authored) if name == 'report.json' else '{}')
        for name in ('provenance.json', 'sandbox-command.json'):
            (evidence / name).write_text('{}')
        args = ['bwrap', '--ro-bind', str(run / 'input'), '/input',
                '--ro-bind', str(control), '/control', 'NO-NATIVE-EXECUTION']
        def authored_guard(factory, **kwargs):
            self.assertEqual(kwargs['root'], root)
            with G.HeavyRunLock(root / '.runtime/native-execution.lock'):
                actual = factory(control, 'authored-host-run')
                self.assertEqual(actual[actual.index('/input') - 2], '--ro-bind')
                with (root / '.piers/fakes/lifecycle.lock').open('rb') as extra:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(extra, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if corrupt:
                    (run / 'input/seed-zod/.urb/synthetic-state').write_text('host fault injection')
            return {'status': 'completed', 'exit_code': 0, 'reason': None, 'events': []}
        with patch.object(A, 'ROOT', root), patch.object(A.toolchain, 'LOCK_PATH', root / 'toolchain.json'), \
                patch.object(A.execution_policy, 'run_guarded', side_effect=authored_guard), \
                patch.object(A.subprocess, 'Popen', side_effect=AssertionError('No native allowed')), \
                A.directory_fd(output) as output_fd, redirect_stdout(io.StringIO()):
            result = A.run_sandbox(run, evidence, control, output_fd, args, 0,
                {'start_temperature_c': 75, 'stop_temperature_c': 90, 'total_timeout_seconds': 2100})
        return result, json.loads((evidence / 'report.json').read_text()), \
            json.loads((evidence / 'bootstrap.json').read_text())

    def test_snapshot_is_prepared_under_owned_lock_and_readonly_mount(self):
        with fixture() as root:
            before = expected_tree(root / '.piers/fakes/seed/zod')
            result, report, bootstrap = self.run_authored_audit(root)
            self.assertEqual(result, 0)  # Authored host import, not native pass evidence.
            self.assertEqual(report['status'], 'passed')
            self.assertTrue(bootstrap['source_and_input_unchanged'])
            self.assertEqual(expected_tree(root / '.piers/fakes/seed/zod'), before)

    def test_changed_snapshot_overrides_authored_fourteen_passes(self):
        with fixture() as root:
            result, report, bootstrap = self.run_authored_audit(root, corrupt=True)
            self.assertEqual(result, 1)
            self.assertEqual(report['status'], 'failed')
            self.assertIn('bootstrap_validation_error', report)
            self.assertFalse(bootstrap['source_and_input_unchanged'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

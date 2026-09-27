"""Independent common-guard regressions; no native process or scope is launched.

Owner: /root/qa_review. Sensors, child processes and systemd calls are explicitly
mocked. File permissions, hardlinks, symlinks, FIFO checks and flock contention
use real operations confined to TemporaryDirectory. These are host safety tests,
not Hoon execution or a thermal calibration claim.
"""
from __future__ import annotations

from dataclasses import asdict
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import execution_policy as guard


CPU = 'thermal_zone0:x86_pkg_temp'
AMBIENT = 'thermal_zone1:acpitz'


def sample(value=50, *, started=100, finished=100, readings=None, cpu=(CPU,)):
    return guard.Sample(started, finished, {CPU: value} if readings is None else readings, cpu)


class ThermalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.policy = guard.Policy()

    def validate(self, value, **options):
        return guard.validate_sample(value, self.policy, now=100, **options)

    def test_preflight_allows_ceiling_but_running_stops_at_ceiling(self):
        self.assertEqual(self.validate(sample(75), preflight=True), 75)
        self.assertEqual(self.validate(sample(89.999)), 89.999)
        for value, options in ((75.001, {'preflight': True}), (90, {}), (96, {})):
            with self.subTest(value=value), self.assertRaises(guard.GuardError):
                self.validate(sample(value), **options)

    def test_ambient_only_is_not_cpu_thermal_evidence(self):
        for cpu in ((), (AMBIENT,), (CPU,)):
            with self.subTest(cpu=cpu), self.assertRaises(guard.GuardError):
                self.validate(sample(readings={AMBIENT: 28}, cpu=cpu), preflight=True)

    def test_missing_or_renamed_hottest_sensor_refuses_continuation(self):
        initial = {CPU: 72, AMBIENT: 29, 'thermal_zone2:TCPU': 74}
        for readings in ({CPU: 50, AMBIENT: 29},
                         {CPU: 50, AMBIENT: 29, 'thermal_zone3:TCPU': 50}):
            with self.subTest(readings=readings), self.assertRaises(guard.GuardError):
                self.validate(sample(readings=readings), expected_inventory=initial)

    def test_same_values_from_fresh_reads_are_valid(self):
        self.assertEqual(self.validate(sample(50)), 50)
        self.assertEqual(guard.validate_sample(sample(50, started=101, finished=101), self.policy, now=101), 50)

    def test_stale_future_reversed_and_nonfinite_clocks_refuse(self):
        for begin, end in ((96, 96), (101, 101), (100, 99), (-1, 100),
                           (float('nan'), 100), (100, float('inf')), (True, 100)):
            with self.subTest(begin=begin, end=end), self.assertRaises(guard.GuardError):
                self.validate(sample(started=begin, finished=end))

    def test_nonfinite_invalid_and_implausible_sensor_values_refuse(self):
        for value in (float('nan'), float('inf'), -float('inf'), -41, 151, True, '50', None):
            with self.subTest(value=value), self.assertRaises(guard.GuardError):
                self.validate(sample(value))

    def test_duplicate_cpu_inventory_refuses(self):
        with self.assertRaises(guard.GuardError):
            self.validate(sample(cpu=(CPU, CPU)))

    def test_constructor_cannot_weaken_existing_limits(self):
        for options in ({'start_c': 76}, {'stop_c': 91}, {'sample_seconds': 2},
                        {'stale_seconds': 4}, {'cooperative_seconds': 11},
                        {'terminate_seconds': 11}, {'kill_seconds': 6},
                        {'cpu_quota_us': 10000}, {'cpu_period_us': 100000}):
            with self.subTest(options=options), self.assertRaises(guard.GuardError):
                guard.Policy(**options)

    def test_sampler_does_not_silently_drop_malformed_zone(self):
        with tempfile.TemporaryDirectory(prefix='stead-guard-sensors-') as temporary:
            root = Path(temporary)
            for number, label, value in ((0, 'x86_pkg_temp', '50000'), (1, 'TCPU', 'not-a-number')):
                zone = root / ('thermal_zone' + str(number)); zone.mkdir()
                (zone / 'type').write_text(label)
                (zone / 'temp').write_text(value)
            with self.assertRaises(guard.GuardError):
                guard.sample_temperatures(root)
            (root / 'thermal_zone1/temp').write_text('49000')
            observed = guard.sample_temperatures(root)
            self.assertEqual(guard.validate_sample(observed, self.policy, preflight=True), 50)


class OwnedHostFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-common-guard-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_lock_contention_preserves_held_inode_and_file(self):
        path = self.root / 'lock'
        with guard.HeavyRunLock(path):
            identity = path.stat().st_ino
            with self.assertRaises(BlockingIOError):
                with guard.HeavyRunLock(path):
                    self.fail('Second execution owner admitted')
            self.assertEqual(path.stat().st_ino, identity)
        self.assertEqual(path.stat().st_ino, identity)
        with guard.HeavyRunLock(path):
            self.assertEqual(path.stat().st_ino, identity)

    def test_lock_symlink_and_hardlink_refuse_without_touching_sentinel(self):
        outside = self.root / 'outside'
        outside.write_text('preserve'); outside.chmod(0o600)
        for mode in ('symlink', 'hardlink'):
            path = self.root / mode
            if mode == 'symlink': path.symlink_to(outside)
            else: os.link(outside, path)
            with self.subTest(mode=mode), self.assertRaises((guard.GuardError, OSError)):
                with guard.HeavyRunLock(path):
                    self.fail('Aliased lock admitted')
            self.assertEqual(outside.read_text(), 'preserve')

    def test_shared_permissions_on_existing_lock_refuse(self):
        path = self.root / 'lock'; path.write_text(''); path.chmod(0o644)
        with self.assertRaises(guard.GuardError):
            with guard.HeavyRunLock(path):
                self.fail('Public lock admitted')

    def test_evidence_parent_symlink_cannot_redirect_host_write(self):
        outside = self.root / 'outside'; outside.mkdir()
        target = outside / 'report.json'; target.write_text('preserve')
        alias = self.root / 'evidence'; alias.symlink_to(outside, target_is_directory=True)
        with self.assertRaises((guard.GuardError, OSError)):
            guard.write_json(alias / 'report.json', {'status': 'completed'})
        self.assertEqual(target.read_text(), 'preserve')

    def test_final_entry_symlink_is_safely_replaced_or_refused(self):
        outside = self.root / 'outside'; outside.write_text('preserve')
        alias = self.root / 'report.json'; alias.symlink_to(outside)
        try: guard.write_json(alias, {'status': 'failed'})
        except (guard.GuardError, OSError): pass
        self.assertEqual(outside.read_text(), 'preserve')

    def test_control_reads_refuse_aliases_fifo_size_and_duplicate_keys(self):
        source = self.root / 'source'; source.write_text('{}')
        symlink = self.root / 'symlink'; symlink.symlink_to(source)
        hardlink = self.root / 'hardlink'; os.link(source, hardlink)
        fifo = self.root / 'fifo'; os.mkfifo(fifo)
        large = self.root / 'large'; large.write_bytes(b' ' * 33)
        duplicate = self.root / 'duplicate'; duplicate.write_text('{"state":"stopped","state":"running"}')
        for path in (symlink, hardlink, fifo, large, duplicate):
            with self.subTest(path=path.name), self.assertRaises((guard.GuardError, OSError)):
                guard.read_json(path, maximum=32)

    def test_cgroup_and_affinity_readback_mismatch_refuses(self):
        unit = 'stead-native-' + 'a' * 32 + '.scope'
        group = self.root / unit; group.mkdir()
        quota = group / 'cpu.max'; quota.write_text('5000 10000')
        proc = self.root / 'proc-cgroup'; proc.write_text('0::/' + unit + '\n')
        with patch.object(guard.os, 'sched_getaffinity', return_value={4}):
            proof = guard.scope_proof(unit, 4, guard.Policy(), cgroup_root=self.root, proc=proc)
            self.assertEqual(proof['cpu_max'], '5000 10000')
            quota.write_text('max 10000')
            with self.assertRaises(guard.GuardError):
                guard.scope_proof(unit, 4, guard.Policy(), cgroup_root=self.root, proc=proc)
        quota.write_text('5000 10000')
        with patch.object(guard.os, 'sched_getaffinity', return_value={4, 5}), self.assertRaises(guard.GuardError):
            guard.scope_proof(unit, 4, guard.Policy(), cgroup_root=self.root, proc=proc)

    def test_scope_signal_rejects_other_unit_without_systemctl(self):
        with patch.object(guard.subprocess, 'run') as called, self.assertRaises(guard.GuardError):
            guard.signal_owned_scope('unrelated.service', signal.SIGTERM)
        called.assert_not_called()


class LeaseAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-guard-lease-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_id = 'a' * 32
        policy = asdict(guard.Policy())
        self.valid = {'format': 1, 'run_id': self.run_id, 'state': 'running',
                      'policy': policy, 'sample': asdict(sample()), 'inventory': [CPU],
                      'guard_sha256': hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest(),
                      'generation': 1,
                      'policy_sha256': hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()}

    def read(self, value):
        guard.write_json(self.root / 'lease.json', value)
        return guard.require_lease(self.root, run_id=self.run_id, now=100)

    def test_current_owned_source_bound_lease_is_accepted(self):
        self.assertEqual(self.read(self.valid), json.loads(json.dumps(self.valid)))

    def test_wrong_owner_source_policy_generation_or_stopped_lease_refuses(self):
        changes = [('run_id', 'b' * 32), ('state', 'stopped'), ('guard_sha256', '0' * 64),
                   ('policy_sha256', '0' * 64), ('generation', 0), ('generation', True),
                   ('inventory', None), ('inventory', [])]
        for key, value in changes:
            altered = copy.deepcopy(self.valid); altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises((guard.GuardError, ValueError, TypeError)):
                self.read(altered)

    def test_stale_and_future_freshly_written_leases_refuse(self):
        for begin in (96, 101):
            altered = copy.deepcopy(self.valid)
            altered['sample']['started'] = altered['sample']['finished'] = begin
            with self.subTest(begin=begin), self.assertRaises(guard.GuardError):
                self.read(altered)

    def test_stop_file_and_stop_symlink_are_terminal_despite_running_lease(self):
        stopped = self.root / 'STOP'; stopped.write_text('stop')
        with self.assertRaises(guard.GuardError): self.read(self.valid)
        stopped.unlink(); stopped.symlink_to(self.root / 'missing')
        with self.assertRaises(guard.GuardError): self.read(self.valid)

    def test_sandbox_cannot_accept_writable_control_mount(self):
        self.read(self.valid)
        with self.assertRaises(guard.GuardError):
            guard.require_lease(self.root, run_id=self.run_id, now=100, read_only=True)


class GuardFailureOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-guard-failure-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    @staticmethod
    def current(value):
        now = time.monotonic()
        return sample(value, started=now, finished=now)

    def test_hot_or_missing_preflight_never_calls_factory_or_process(self):
        for sampler in (lambda: self.current(76), Mock(side_effect=guard.GuardError('Missing CPU sensor'))):
            factory = Mock()
            with patch.object(guard.subprocess, 'Popen') as launch:
                report = guard.run_guarded(factory, root=self.root, label='preflight', sampler=sampler)
            factory.assert_not_called(); launch.assert_not_called()
            self.assertEqual(report['status'], 'failed')
            self.assertTrue((Path(report['run_directory']) / 'report.json').is_file())
            self.assertTrue((Path(report['run_directory']) / 'events.jsonl').is_file())
            self.assertFalse(any(self.root.rglob('seed')))

    def test_evidence_write_failure_still_signals_owned_running_child(self):
        child = Mock(); child.returncode = None
        child.poll.side_effect = lambda: child.returncode
        launched = False
        def launch_owned(*_args, **_kwargs):
            nonlocal launched
            launched = True
            return child
        def stop(unit, signum):
            child.returncode = 0
            return {'signal': str(signum), 'returncode': 0}
        original = guard.write_json
        def fail_later_lease(path, value):
            if launched and Path(path).name == 'lease.json':
                raise OSError('Synthetic control disk failure')
            return original(path, value)
        with patch.object(guard.subprocess, 'Popen', side_effect=launch_owned) as launch, \
                patch.object(guard, 'signal_owned_scope', side_effect=stop) as signals, \
                patch.object(guard, 'write_json', side_effect=fail_later_lease):
            report = guard.run_guarded(lambda *_: ['synthetic-no-runtime'], root=self.root,
                                       label='disk-failure', sampler=lambda: self.current(50),
                                       policy=guard.Policy(cooperative_seconds=0, terminate_seconds=.01,
                                                           kill_seconds=.01, sample_seconds=.001))
        launch.assert_called_once()
        self.assertTrue(report['launched'])
        self.assertEqual(report['status'], 'failed')
        self.assertIn('Synthetic control disk failure', report['reason'])
        self.assertGreaterEqual(signals.call_count, 1, 'Lease I/O error bypassed owned-child cleanup')
        self.assertEqual(child.returncode, 0)

    def test_evidence_write_failure_after_preparation_prevents_child_launch(self):
        prepared = False
        def prepare(*_):
            nonlocal prepared
            prepared = True
            return ['synthetic-no-runtime']
        original = guard.write_json
        def fail_prelaunch_lease(path, value):
            if prepared and Path(path).name == 'lease.json':
                raise OSError('Synthetic prelaunch control disk failure')
            return original(path, value)
        factory = Mock(side_effect=prepare)
        with patch.object(guard.subprocess, 'Popen') as launch, \
                patch.object(guard, 'signal_owned_scope') as signals, \
                patch.object(guard, 'write_json', side_effect=fail_prelaunch_lease):
            report = guard.run_guarded(factory, root=self.root, label='prelaunch-disk-failure',
                                       sampler=lambda: self.current(50))
        factory.assert_called_once()
        launch.assert_not_called(); signals.assert_not_called()
        self.assertFalse(report['launched'])
        self.assertEqual(report['status'], 'failed')
        self.assertIn('Synthetic prelaunch control disk failure', report['reason'])

    def test_operator_stop_before_launch_is_nonpassing_without_launch(self):
        factory = Mock()
        with patch.object(guard.subprocess, 'Popen') as launch:
            report = guard.run_guarded(factory, root=self.root, label='pre-cancel',
                                       sampler=lambda: self.current(50), stop_requested=lambda: True)
        factory.assert_not_called(); launch.assert_not_called()
        self.assertEqual(report['status'], 'failed')


if __name__ == '__main__':
    unittest.main()

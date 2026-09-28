"""Host-only controls: signed identity and resource evidence, never native proof."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/ci'), str(ROOT / 'scripts/urbit')]
import hosted_identity as identity
import hosted_lease as lease
import hosted
import hosted_apparmor as apparmor


class IdentityControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(cls.folder.name)
        cls.private = cls.root / 'private.pem'
        subprocess.run(['/usr/bin/openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
            '-out', str(cls.private)], check=True, capture_output=True, timeout=15)
        # OpenSSL exposes the unsigned modulus; the test never substitutes a
        # mocked success from the real verifier.
        modulus = subprocess.check_output(['/usr/bin/openssl', 'rsa', '-in', str(cls.private), '-modulus', '-noout'], timeout=5)
        cls.modulus = bytes.fromhex(modulus.decode().strip().split('=', 1)[1])

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.claims = {'iss': identity.ISSUER, 'aud': 'nonce-a', 'repository': identity.REPOSITORY,
            'repository_id': identity.REPOSITORY_ID, 'repository_owner_id': identity.OWNER_ID,
            'repository_visibility': 'public', 'runner_environment': 'github-hosted',
            'event_name': 'workflow_dispatch', 'ref': 'refs/heads/main', 'workflow_ref': identity.WORKFLOW,
            'workflow_sha': '1' * 40, 'sha': '1' * 40, 'run_id': '123', 'run_attempt': '1',
            'sub': 'repo:ScottTpirate@44659733/stead-urbit@1367847927:ref:refs/heads/main',
            'iat': 1000, 'nbf': 1000, 'exp': 1300, 'jti': 'test-token'}
        enc = self.encode
        self.keys = {'keys': [{'kty': 'RSA', 'alg': 'RS256', 'use': 'sig', 'kid': 'test',
            'n': enc(self.modulus), 'e': enc(bytes.fromhex('010001'))}]}

    @staticmethod
    def encode(raw):
        return base64.urlsafe_b64encode(raw).decode().rstrip('=')

    def token(self, claims=None, header=None):
        head = self.encode(json.dumps(header or {'typ': 'JWT', 'alg': 'RS256', 'kid': 'test'}).encode())
        body = self.encode(json.dumps(claims or self.claims).encode())
        message = (head + '.' + body).encode()
        signature = subprocess.run(['/usr/bin/openssl', 'dgst', '-sha256', '-sign', str(self.private)],
            input=message, capture_output=True, check=True, timeout=5).stdout
        return message.decode() + '.' + self.encode(signature)

    def verify(self, token, **kwargs):
        values = dict(audience='nonce-a', workflow_sha='1' * 40, run_id='123', attempt='1', now=1001)
        values.update(kwargs)
        return identity.verify(token, self.keys, **values)

    def test_real_signature_and_fixed_claims(self):
        observed = self.verify(self.token())
        self.assertEqual(observed['repository_id'], identity.REPOSITORY_ID)
        self.assertNotIn('aud', observed)

    def test_changed_signature_body_and_replayed_audience(self):
        token = self.token()
        head, body, signature = token.split('.')
        for bad in (head + '.' + self.encode(b'{}') + '.' + signature,
                    head + '.' + body + '.' + self.encode(b'\0' * 256)):
            with self.assertRaises(ValueError):
                self.verify(bad)
        with self.assertRaises(ValueError):
            self.verify(token, audience='different-run-nonce')

    def test_wrong_job_identity_is_refused_even_with_valid_signature(self):
        for key, bad in {'repository_id': '9', 'repository_owner_id': '9', 'runner_environment': 'self-hosted',
            'event_name': 'pull_request', 'workflow_sha': '2' * 40, 'sha': '2' * 40,
            'workflow_ref': identity.WORKFLOW.replace('main', 'feature'), 'run_id': '124', 'run_attempt': '2',
            'repository_visibility': 'private', 'sub': 'repo:other/project:ref:refs/heads/main'}.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(self.token({**self.claims, key: bad}))

    def test_stale_future_alg_key_and_duplicate_json_refused(self):
        for change in ({'exp': 1001}, {'iat': 0}, {'nbf': 1200}, {'iat': True}, {'exp': 1700}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(self.token({**self.claims, **change}))
        for header in ({'typ': 'JWT', 'alg': 'none', 'kid': 'test'}, {'typ': 'JWT', 'alg': 'RS256', 'kid': 'absent'},
                       {'typ': 'JWT', 'alg': 'RS256', 'kid': 'test', 'jku': 'https://attacker.invalid'}):
            with self.assertRaises(ValueError):
                self.verify(self.token(header=header))
        with self.assertRaises(ValueError):
            identity.unique([('a', 1), ('a', 2)])


class HostedLeaseControls(unittest.TestCase):
    def setUp(self):
        self.value = {'format': 'stead.hosted-lease/1', 'state': 'running', 'run_id': 'a' * 32,
            'generation': 3, 'started': 100, 'observed_at': 101, 'deadline': 7300,
            'policy': copy.deepcopy(lease.POLICY), 'guard_sha256': 'b' * 64,
            'policy_sha256': hashlib.sha256(json.dumps(lease.POLICY, sort_keys=True).encode()).hexdigest(),
            'cpus': [0, 1], 'unit': 'stead-hosted-' + 'a' * 32 + '.service',
            'cgroup': '/system.slice/stead-hosted-' + 'a' * 32 + '.service',
            'limits': {'cpu.max': '20000 10000', 'memory.max': str(12 * 1024**3), 'memory.swap.max': '0', 'pids.max': '256'},
            'resource_events': {'oom': 0, 'oom_kill': 0, 'pids_max': 0}, 'authenticated_host': True,
            'service': {'KillMode': 'control-group', 'ExitType': 'main', 'RemainAfterExit': 'no',
                'Restart': 'no', 'OOMPolicy': 'kill', 'RuntimeMaxUSec': '2h', 'TimeoutStopUSec': '15s',
                'Delegate': 'no', 'memory.oom.group': '1', 'MainPID': '123', 'AppArmorProfile': apparmor.PROFILE},
            'apparmor': {'profile': apparmor.PROFILE, 'policy_sha256': apparmor.POLICY_SHA256,
                'settings': dict.fromkeys(apparmor.SYSCTLS, '1')}}

    def validate(self, value=None, now=102):
        return lease.validate(self.value if value is None else value, run_id='a' * 32, now=now,
            guard_sha256='b' * 64, cpus=[0, 1])

    def test_current_authenticated_evidence_has_no_fabricated_temperatures(self):
        self.assertEqual(self.validate()['policy']['thermal'], 'provider-managed-unmeasured')
        self.assertNotIn('sample', self.value)

    def test_stale_reversed_missing_foreign_or_failed_observations(self):
        for change in ({'observed_at': 98}, {'observed_at': 103}, {'observed_at': float('nan')},
            {'state': 'stopped'}, {'run_id': 'c' * 32}, {'authenticated_host': False},
            {'cpus': [0, 2]}, {'limits': {}}, {'generation': 0}, {'guard_sha256': 'd' * 64},
            {'deadline': 7400}, {'resource_events': {'oom': 1, 'oom_kill': 0, 'pids_max': 0}},
            {'cgroup': '/system.slice/foreign.service'}, {'apparmor': {}},
            {'apparmor': {**self.value['apparmor'], 'settings': dict.fromkeys(apparmor.SYSCTLS, '0')}}):
            with self.subTest(change=change), self.assertRaises(Exception):
                self.validate({**self.value, **change})
        with self.assertRaises(Exception):
            self.validate(now=7300)

    def test_cpu_set_is_bounded_and_exact(self):
        self.assertEqual(hosted.cpu_set('0-1'), [0, 1])
        self.assertEqual(hosted.cpu_set('1,3'), [1, 3])
        for bad in ('', '1-0', '0-100000', 'x'):
            with self.assertRaises(ValueError):
                hosted.cpu_set(bad)

    def test_changed_lifetime_and_same_generation_edits_fail(self):
        lease.progression(self.value, copy.deepcopy(self.value))
        lease.progression(self.value, {**self.value, 'generation': 4, 'observed_at': 102})
        for change in ({'started': 101, 'deadline': 7301, 'generation': 4},
                       {'observed_at': 102}, {'generation': 2}):
            with self.subTest(change=change), self.assertRaises(Exception):
                lease.progression(self.value, {**self.value, **change})


class LauncherControls(unittest.TestCase):
    def test_control_diagnostic_excludes_native_and_bounds_public_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertIsNone(hosted.control_diagnostic(root, None))
            path = root / 'console.private.log'
            path.write_bytes(b'x' * 9000)
            result = hosted.control_diagnostic(root, 'parent-death')
            self.assertTrue(result['truncated'])
            self.assertEqual(len(result['text']), 8192)
            self.assertEqual(result['bytes_total'], 9000)
            path.unlink()
            path.symlink_to(root / 'absent')
            with self.assertRaises(OSError):
                hosted.control_diagnostic(root, 'parent-death')
            with self.assertRaises(ValueError):
                hosted.control_diagnostic(root, 'native')
            self.assertEqual(hosted.capture_control_diagnostic(root, 'parent-death'), {'capture_error': 'OSError'})
            path.unlink()
            path.mkdir()
            descriptors = len(list(Path('/proc/self/fd').iterdir()))
            self.assertEqual(hosted.capture_control_diagnostic(root, 'parent-death'), {'capture_error': 'ValueError'})
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), descriptors)
            path.rmdir()
            os.mkfifo(path)
            self.assertEqual(hosted.capture_control_diagnostic(root, 'parent-death'), {'capture_error': 'ValueError'})
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), descriptors)

    def test_real_child_is_reaped_when_collector_thread_cannot_start(self):
        observed = []
        real = subprocess.Popen
        def capture(*args, **kwargs):
            process = real(*args, **kwargs)
            observed.append(process)
            return process
        with tempfile.TemporaryDirectory() as folder, patch.object(hosted.subprocess, 'Popen', side_effect=capture), \
                patch.object(hosted.threading.Thread, 'start', side_effect=RuntimeError('control thread start')):
            with self.assertRaisesRegex(RuntimeError, 'control thread start'):
                hosted.spawn_owned(['/usr/bin/python3', '-I', '-B', '-c', 'import time; time.sleep(30)'],
                    diagnostics=Path(folder) / 'diagnostic')
        self.assertEqual(len(observed), 1)
        self.assertIsNotNone(observed[0].poll())
        self.assertTrue(observed[0].stdin.closed)
        self.assertTrue(observed[0].stderr.closed)

    def test_incomplete_control_frame_is_not_a_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'console.private.log'
            path.write_text('STEAD_HOSTED_CONTROL_READY {"run_id":"abc"}')
            self.assertIsNone(hosted.control_frame(root, 'STEAD_HOSTED_CONTROL_READY ', 'abc'))
            path.write_text(path.read_text() + '\n')
            self.assertEqual(hosted.control_frame(root, 'STEAD_HOSTED_CONTROL_READY ', 'abc'), {'run_id': 'abc'})


class AppArmorControls(unittest.TestCase):
    def test_unrelated_control_requires_real_namespace_or_capability_denial(self):
        value = {'before': {'uid': 991, 'label': 'unconfined', 'nnp': '1', 'cap_eff': '0000000000000000'},
            'transition': 0, 'transition_errno': 0, 'after_transition': 'unconfined//&' + apparmor.PROFILE,
            'unshare': 0, 'unshare_errno': 0, 'after_unshare': 'unprivileged_userns',
            'network_errno': 1, 'cap_eff_after': '0000000000001000', 'nnp_after': '1'}
        self.assertEqual(apparmor.verify_unrelated(value, 991), value)
        for delta in ({'after_transition': apparmor.PROFILE + ' (unconfined)'},
                      {'network_errno': 0}, {'network_errno': 2}, {'cap_eff_after': '0000000000000000'},
                      {'nnp_after': '0'}, {'transition': -1, 'transition_errno': 2}, {'unshare': -1, 'unshare_errno': 12}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                apparmor.verify_unrelated({**value, **delta}, 991)

    def test_actual_label_and_mandatory_service_profile(self):
        with patch.object(apparmor, 'label', return_value='unconfined'):
            with self.assertRaisesRegex(ValueError, 'label differs'):
                apparmor.require_label()
        with patch.object(hosted, 'hosted_apparmor', apparmor, create=True), \
                patch.object(hosted, 'local', SimpleNamespace(MEMORY=12 * 1024**3, TASKS=256), create=True):
            context = {'unit': 'stead-hosted-' + 'a' * 32 + '.service', 'cpus': [0, 1]}
            command = hosted.service_command(Path('/fixed'), context)
            self.assertIn('--property=AppArmorProfile=' + apparmor.PROFILE, command)
            self.assertNotIn('--property=AppArmorProfile=-' + apparmor.PROFILE, command)
            command = hosted.service_command(Path('/fixed'), {**context, 'control_case': 'missing-profile'})
            self.assertIn('--property=AppArmorProfile=' + apparmor.PROFILE + '-missing', command)


class WorkflowBindingControls(unittest.TestCase):
    def test_exact_workflow_manifest_binds_the_separate_controller(self):
        import local
        raw = json.dumps({'format': 'stead.hosted-controller/1', 'repository': identity.REPOSITORY,
            'controller_commit': 'b' * 40}).encode() + b'\n'
        files = {'specs/urbit/hosted-ci-controller.json': raw, '.github/workflows/native-hosted.yml': b'fixed workflow'}
        def inventory(commit, paths):
            self.assertEqual(commit, 'a' * 40)
            self.assertEqual(set(paths), set(files))
            return files
        with patch.object(hosted, 'local', SimpleNamespace(inventory=inventory, hashes=local.hashes), create=True), \
                patch.object(hosted, 'hosted_identity', identity, create=True):
            observed = hosted.workflow_binding('a' * 40, 'b' * 40)
            self.assertEqual(observed['manifest_raw'].encode(), raw)
            self.assertEqual(observed['manifest_blob_oid'], hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())
            with self.assertRaisesRegex(ValueError, 'another controller'):
                hosted.workflow_binding('a' * 40, 'c' * 40)
            files['specs/urbit/hosted-ci-controller.json'] = b'{"a":1,"a":2}'
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                hosted.workflow_binding('a' * 40, 'b' * 40)


if __name__ == '__main__':
    unittest.main()

"""Independent host safety regression tests; NOT evidence of native Hoon execution.

Owner/reviewer: /root/qa_review (independent agent, not human approval).
Every writable path belongs to TemporaryDirectory. Control-socket responses and
download bytes are mocked where stated; filesystem hashes, locks, and the benign
tamper executable are real host operations. No live fixture is started or reset.
"""
from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
import fcntl
import importlib.util
import io
import json
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/urbit'))
import digests  # noqa: E402
import harness  # noqa: E402
import toolchain  # noqa: E402


class FixtureSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-harness-safety-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / '.piers/fakes'
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (('ROOT', self.root), ('BASE', self.root / '.piers'),
                            ('STATE', self.state)):
            self.stack.enter_context(patch.object(harness, name, value))
        self.lock_path = self.root / 'toolchain.json'
        self.lock_path.write_text('{"synthetic": true}\n')
        self.stack.enter_context(patch.object(toolchain, 'LOCK_PATH', self.lock_path))
        # Deliberately mocked RPC: these are local lifecycle safety tests.
        self.status = self.stack.enter_context(patch.object(harness, 'running', return_value=None))

    def fixture(self):
        harness.guard(create=True)
        live = self.state / 'live'
        live.mkdir()
        (live / 'preserve-until-valid-reset').write_text('old synthetic state')
        return live

    def seed(self):
        seed = self.state / 'seed'
        seed.mkdir()
        manifest = {'format': 1, 'toolchain_sha256': digests.sha(self.lock_path), 'ships': {}}
        for ship in harness.SHIPS:
            pier = seed / ship
            (pier / '.urb').mkdir(parents=True)
            (pier / '.urb/state.txt').write_text('synthetic ' + ship)
            manifest['ships'][ship] = digests.tree_sha(pier)
        (seed / 'manifest.json').write_text(json.dumps(manifest))
        return seed, manifest

    def preserved(self, live):
        self.assertEqual((live / 'preserve-until-valid-reset').read_text(), 'old synthetic state')

    def test_unmarked_fixture_is_not_deleted(self):
        self.state.mkdir(parents=True, mode=0o700)
        sentinel = self.state / 'sentinel'
        sentinel.write_text('keep')
        with self.assertRaises((OSError, ValueError)):
            harness.reset()
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_invalid_marker_is_not_permission_to_delete(self):
        live = self.fixture()
        (self.state / harness.MARKER).write_text('{"purpose": "another-project"}')
        with self.assertRaises(ValueError):
            harness.reset()
        self.preserved(live)

    def test_fixture_root_symlink_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.state.parent.mkdir()
        self.state.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            harness.guard(create=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_parent_root_symlink_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / '.piers').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            harness.guard(create=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_fixture_with_public_permissions_is_rejected(self):
        live = self.fixture()
        self.state.chmod(0o755)
        with self.assertRaises(ValueError):
            harness.reset()
        self.preserved(live)

    def test_redirected_control_or_owned_entry_is_rejected(self):
        harness.guard(create=True)
        outside = self.root / 'outside'
        outside.mkdir()
        for name in ('live', 'seed', 'logs', 'control.sock', 'lifecycle.lock', harness.MARKER):
            with self.subTest(name=name):
                entry = self.state / name
                original = entry.read_bytes() if entry.is_file() else None
                entry.unlink(missing_ok=True)
                entry.symlink_to(outside)
                try:
                    with self.assertRaises(ValueError):
                        harness.guard()
                finally:
                    entry.unlink()
                    if original is not None:
                        entry.write_bytes(original)

    def test_active_control_endpoint_blocks_reset(self):
        live = self.fixture()
        self.seed()
        self.status.return_value = {'stage': 'ready'}
        with self.assertRaises(ValueError):
            harness.reset()
        self.preserved(live)

    def test_unresponsive_supervisor_lock_still_blocks_reset(self):
        live = self.fixture()
        self.seed()
        # A real independently opened kernel lock remains authoritative even
        # when the mocked status endpoint looks unavailable.
        with (self.state / 'lifecycle.lock').open('a+') as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                harness.reset()
        self.preserved(live)

    def test_changed_toolchain_preserves_live_data(self):
        live = self.fixture()
        self.seed()
        self.lock_path.write_text('{"synthetic": "different"}\n')
        with self.assertRaises(ValueError):
            harness.reset()
        self.preserved(live)

    def test_start_with_other_toolchain_cannot_launch_existing_piers(self):
        live = self.fixture()
        self.seed()
        self.lock_path.write_text('{"synthetic": "different"}\n')
        # Isolate the lifecycle decision from download verification and sandbox
        # construction. Any Popen would be an attempted launch with stale state.
        with patch.object(toolchain, 'verify'), patch.object(harness, 'sandbox', return_value=['false']):
            with patch.object(subprocess, 'Popen') as launch:
                launch.return_value.poll.return_value = 1
                with self.assertRaises((ValueError, RuntimeError)):
                    harness.start()
                launch.assert_not_called()
        self.preserved(live)

    def test_changed_seed_preserves_live_data(self):
        live = self.fixture()
        seed, _ = self.seed()
        (seed / 'bud/.urb/state.txt').write_text('corrupt seed')
        with self.assertRaises(ValueError):
            harness.reset()
        self.preserved(live)

    def test_seed_directory_symlink_cannot_escape_digest_or_reset_guard(self):
        live = self.fixture()
        seed, _ = self.seed()
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'secret').write_text('synthetic sentinel')
        # Adding a symlinked directory used to leave tree_sha unchanged, so
        # a previously valid manifest still authorized copying this redirect.
        (seed / 'bud/.urb/escape').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            harness.reset()
        self.preserved(live)
        self.assertEqual((outside / 'secret').read_text(), 'synthetic sentinel')

    def test_valid_stopped_hash_verified_seed_resets_all_four(self):
        live = self.fixture()
        self.seed()
        with redirect_stdout(io.StringIO()):
            harness.reset()
        self.assertFalse((live / 'preserve-until-valid-reset').exists())
        self.assertEqual({p.name for p in live.iterdir()}, set(harness.SHIPS))
        for ship in harness.SHIPS:
            self.assertEqual((live / ship / '.urb/state.txt').read_text(), 'synthetic ' + ship)


class DigestSafety(unittest.TestCase):
    def test_source_profile_covers_internal_aliases_and_their_targets(self):
        with tempfile.TemporaryDirectory(prefix='stead-source-alias-') as tmp:
            root = Path(tmp)
            (root / 'pkg/arvo').mkdir(parents=True)
            target = root / 'pkg/base-dev'
            target.mkdir()
            (target / 'source.hoon').write_text('synthetic source')
            original = digests.tree_sha(root, source_links=True)
            (root / 'pkg/arvo/file.hoon').symlink_to('../base-dev/source.hoon')
            (root / 'pkg/arvo/directory').symlink_to('../base-dev', target_is_directory=True)
            aliased = digests.tree_sha(root, source_links=True)
            self.assertNotEqual(aliased, original, 'Alias metadata must affect the source digest')
            (target / 'source.hoon').write_text('changed source')
            self.assertNotEqual(digests.tree_sha(root, source_links=True), aliased,
                                'The real target bytes must also affect the source digest')

    def test_source_profile_rejects_alias_outside_pinned_tree(self):
        with tempfile.TemporaryDirectory(prefix='stead-source-alias-') as tmp:
            root = Path(tmp) / 'source'
            root.mkdir()
            outside = Path(tmp) / 'outside'
            outside.write_text('synthetic outside bytes')
            (root / 'alias').symlink_to('../outside')
            with self.assertRaises(ValueError):
                digests.tree_sha(root, source_links=True)

    def test_file_redirect_is_not_equivalent_to_original_bytes(self):
        with tempfile.TemporaryDirectory(prefix='stead-digest-safety-') as tmp:
            root = Path(tmp) / 'tree'
            root.mkdir()
            value = root / 'content'
            value.write_bytes(b'synthetic content')
            original = digests.tree_sha(root)
            outside = Path(tmp) / 'outside'
            outside.write_bytes(value.read_bytes())
            value.unlink()
            value.symlink_to(outside)
            try:
                redirected = digests.tree_sha(root)
            except ValueError:
                return  # Rejecting symlinks is a valid, stricter profile.
            self.assertNotEqual(redirected, original)

    def test_directory_redirect_is_not_invisible_to_digest(self):
        with tempfile.TemporaryDirectory(prefix='stead-digest-safety-') as tmp:
            root = Path(tmp) / 'tree'
            root.mkdir()
            (root / 'file').write_bytes(b'synthetic content')
            original = digests.tree_sha(root)
            outside = Path(tmp) / 'outside'
            outside.mkdir()
            (root / 'redirect').symlink_to(outside, target_is_directory=True)
            try:
                redirected = digests.tree_sha(root)
            except ValueError:
                return
            self.assertNotEqual(redirected, original)


class SupplyChainSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-pin-safety-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / '.runtime'
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (('ROOT', self.root), ('CACHE', self.cache),
                            ('LOCK_PATH', self.root / 'toolchain.json')):
            self.stack.enter_context(patch.object(toolchain, name, value))
        self.data = {'format': 1, 'profile': 'linux-x86_64-fake-only',
                     'host_tools': {'git': subprocess.check_output(['git', '--version'], text=True).strip().removeprefix('git version ')}}
        (self.cache / 'downloads').mkdir(parents=True)
        for key in ('runtime', 'kernel', 'boot_artifact', 'frontend'):
            archive = self.cache / 'downloads' / (key + '.archive')
            archive.write_bytes(('synthetic archive: ' + key).encode())
            self.data[key] = {'archive': archive.name, 'sha256': digests.sha(archive),
                              'url': 'https://invalid.example.test/' + archive.name}
        binary = self.cache / 'bin/vere-test'
        binary.parent.mkdir()
        binary.write_bytes(b'synthetic runtime, never executed')
        self.data['runtime'].update(binary='bin/vere-test', binary_sha256=digests.sha(binary))
        arvo = self.cache / 'kernel-test/pkg/arvo'
        arvo.mkdir(parents=True)
        (arvo / 'synthetic.hoon').write_text('not executed\n')
        self.data['kernel'].update(directory='kernel-test',
                                   source_tree_sha256=digests.tree_sha(self.cache / 'kernel-test', source_links=True))
        frontend_lock = self.root / 'frontend-lock.json'
        frontend_lock.write_text('{"synthetic":true}')
        self.node = self.cache / 'node-test/bin/node'
        self.node.parent.mkdir(parents=True)
        self.node.write_text('#!/bin/sh\nprintf "v1.2.3\\n"\n')
        self.node.chmod(0o700)
        self.data['frontend'].update(directory='node-test', node='1.2.3', lockfile=frontend_lock.name,
                                     lock_sha256=digests.sha(frontend_lock), binary_sha256=digests.sha(self.node))
        self.corpus = self.root / 'synthetic-corpus.json'
        self.corpus.write_text('{"synthetic":true,"cases":[]}\n')
        self.data['protocol_corpus'] = {'path': self.corpus.name, 'sha256': digests.sha(self.corpus)}
        self.write_lock()

    def write_lock(self):
        toolchain.LOCK_PATH.write_text(json.dumps(self.data))

    def test_original_pinned_synthetic_fixture_verifies(self):
        self.assertEqual(toolchain.verify()['profile'], 'linux-x86_64-fake-only')

    def test_archive_tampering_fails_before_executable_check(self):
        (self.cache / 'downloads/runtime.archive').write_bytes(b'corrupt')
        with patch.object(subprocess, 'check_output') as execute:
            with self.assertRaises(ValueError):
                toolchain.verify()
            execute.assert_not_called()

    def test_protocol_corpus_tampering_fails_before_executable_check(self):
        self.corpus.write_text('{"synthetic":true,"cases":["unreviewed change"]}\n')
        with patch.object(subprocess, 'check_output') as execute:
            with self.assertRaises(ValueError):
                toolchain.verify()
            execute.assert_not_called()

    def test_tampered_node_is_rejected_before_it_can_execute(self):
        marker = self.root / 'TAMPERED_NODE_EXECUTED'
        self.node.write_text('#!/bin/sh\ntouch ' + shlex.quote(str(marker)) + '\nprintf "v1.2.3\\n"\n')
        rejected = False
        try:
            toolchain.verify()
        except ValueError:
            rejected = True
        self.assertFalse(marker.exists(), 'An unverified cached Node executable ran on the host')
        self.assertTrue(rejected, 'Changed extracted Node bytes must fail verification')

    def test_partial_download_symlink_cannot_overwrite_outside_cache(self):
        archive = self.cache / 'downloads/runtime.archive'
        original = archive.read_bytes()
        archive.unlink()
        sentinel = self.root / 'outside-download-cache'
        sentinel.write_bytes(b'preserve this synthetic sentinel')
        archive.with_suffix(archive.suffix + '.partial').symlink_to(sentinel)
        # Mock network response only: path opening and filesystem effects are real.
        with redirect_stdout(io.StringIO()), patch.object(toolchain.urllib.request, 'urlopen', return_value=io.BytesIO(original)):
            try:
                toolchain.fetch()
            except (ValueError, OSError):
                pass
        self.assertEqual(sentinel.read_bytes(), b'preserve this synthetic sentinel')

    def test_redirected_download_directory_is_rejected(self):
        downloads = self.cache / 'downloads'
        outside = self.root / 'outside-downloads'
        downloads.rename(outside)
        downloads.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            toolchain.verify()

    def test_redirected_extracted_binary_parent_is_rejected(self):
        binaries = self.cache / 'bin'
        outside = self.root / 'outside-binaries'
        binaries.rename(outside)
        binaries.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            toolchain.verify()


class SupervisorLifecycleSafety(unittest.TestCase):
    """Real socket/thread ordering, with every native ship operation mocked."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location('stead_test_supervisor', REPO / 'scripts/urbit/supervisor.py')
        self.supervisor = importlib.util.module_from_spec(spec)
        original_read_text = Path.read_text

        def fixture_lock(path, *args, **kwargs):
            if path == Path('/toolchain.json'):
                return '{"synthetic":true}'
            return original_read_text(path, *args, **kwargs)

        # Loading module definitions never executes its __main__ launch block.
        with patch.object(Path, 'read_text', fixture_lock), patch.object(digests, 'source_sha', return_value='mocked-source-digest'):
            spec.loader.exec_module(self.supervisor)

    def test_stop_signals_cancellation_before_waiting_for_active_initialization(self):
        server, client = socket.socketpair()
        self.addCleanup(client.close)
        client.settimeout(2)
        self.supervisor.MUTEX.acquire()
        worker = threading.Thread(target=self.supervisor.handle, args=(server,), daemon=True)
        with patch.object(self.supervisor, 'all_stop') as stop_ships:
            worker.start()
            try:
                client.sendall(b'{"op":"stop"}\n')
                self.assertTrue(self.supervisor.STOP_REQUESTED.wait(1),
                                'Stop must cancel boot while the initialization mutex is held')
                stop_ships.assert_not_called()
            finally:
                self.supervisor.MUTEX.release()
                worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertTrue(json.loads(client.recv(65536))['result']['stopped'])
            stop_ships.assert_called_once()

    def test_cancelled_boot_never_polls_native_endpoint(self):
        self.supervisor.STOP_REQUESTED.set()
        with patch.object(self.supervisor, 'dojo') as native_call:
            with self.assertRaises(InterruptedError):
                self.supervisor.wait_ready('zod', timeout=1)
            native_call.assert_not_called()

    def test_shutdown_failure_still_attempts_every_other_ship_and_reports_failure(self):
        attempted = []

        def shutdown(ship):
            attempted.append(ship)
            if ship == 'zod':
                raise RuntimeError('synthetic zod shutdown failure')

        with patch.object(self.supervisor, 'shutdown', side_effect=shutdown):
            with self.assertRaisesRegex(RuntimeError, 'synthetic zod shutdown failure'):
                self.supervisor.all_stop()
        self.assertEqual(attempted, list(self.supervisor.SHIPS))


if __name__ == '__main__':
    unittest.main(verbosity=2)

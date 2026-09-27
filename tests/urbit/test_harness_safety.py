"""Independent host safety regression tests; NOT evidence of native Hoon execution.

Owner/reviewer: /root/qa_review (independent agent, not human approval).
The source inventory, cache and committed-input follow-up tests were authored
by /root/independent_review; they remain host-only checks.
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
import os
from pathlib import Path
import py_compile
import shlex
import shutil
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
        for name in ('live', 'seed', 'logs', 'ingress', 'control.sock', 'lifecycle.lock', harness.MARKER):
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
    def test_special_sources_refuse_without_waiting_for_fifo_writer(self):
        with tempfile.TemporaryDirectory(prefix='stead-source-fifo-') as tmp:
            root = Path(tmp)
            fifo = root / 'source.py'
            os.mkfifo(fifo)
            for function, value in (('sha', fifo), ('read_source', fifo), ('source_inventory', root)):
                with self.subTest(function=function):
                    result = subprocess.run([sys.executable, '-B', '-c',
                        'import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); '
                        'import digests; getattr(digests, sys.argv[2])(Path(sys.argv[3]))',
                        str(REPO / 'scripts/urbit'), function, str(value)],
                        capture_output=True, text=True, timeout=2)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('regular file', result.stderr)

    def test_helper_inventory_binds_new_files_and_excludes_only_cache_directory(self):
        with tempfile.TemporaryDirectory(prefix='stead-source-inventory-') as tmp:
            root = Path(tmp)
            (root / 'original.py').write_text('VALUE = 1\n')
            original = digests.source_inventory(root)
            cache = root / '__pycache__'
            cache.mkdir()
            (cache / 'ignored.pyc').write_bytes(b'authored cache sentinel')
            self.assertEqual(digests.source_inventory(root), original)
            (root / 'new.py').write_text('VALUE = 2\n')
            self.assertEqual(set(digests.source_inventory(root)), {'original.py', 'new.py'})
            (root / 'top-level.pyc').write_bytes(b'not an excluded cache directory')
            self.assertIn('top-level.pyc', digests.source_inventory(root))

    def test_fresh_cache_prefix_executes_source_instead_of_old_host_bytecode(self):
        with tempfile.TemporaryDirectory(prefix='stead-source-cache-') as tmp:
            root = Path(tmp)
            source = root / 'reviewer_fixture.py'
            source.write_text("VALUE = 'before'\n")
            old = source.stat()
            py_compile.compile(str(source), doraise=True)
            source.write_text("VALUE = 'after!'\n")
            os.utime(source, ns=(old.st_atime_ns, old.st_mtime_ns))
            code = 'import reviewer_fixture; print(reviewer_fixture.VALUE)'
            ordinary = subprocess.check_output([sys.executable, '-B', '-c', code], cwd=root, text=True)
            isolated = subprocess.check_output([sys.executable, '-B', '-X',
                'pycache_prefix=' + str(root / 'fresh-cache'), '-c', code], cwd=root, text=True)
            self.assertEqual(ordinary.strip(), 'before', 'Control must actually load old cached code')
            self.assertEqual(isolated.strip(), 'after!')

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


class QualificationSourceSafety(unittest.TestCase):
    """Real temporary Git/bytes; native supervisor launch and mounts are mocked."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-qualification-source-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.control = Path(self.temp.name) / 'control'
        self.control.mkdir(mode=0o700)
        for name in ('scripts/urbit', 'native/core/desk', 'specs/urbit', 'web/dev',
                     'tests/urbit/native_gall_schedule', 'tests/urbit/skill_evaluation'):
            directory = self.root / name
            directory.mkdir(parents=True)
            if name == 'scripts/urbit':
                for source in (REPO / name).glob('*.py'):
                    shutil.copyfile(source, directory / source.name)
            else:
                (directory / 'fixture.txt').write_text('authored host fixture\n')
        (self.root / '.gitignore').write_text('__pycache__/\n')
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                 '-c', 'user.name=Authored Host Test', '-c', 'user.email=host-test@example.invalid',
                 'commit', '-qm', 'Synthetic temporary provenance fixture')

    def git(self, *arguments):
        return subprocess.check_output(['git', *arguments], cwd=self.root, stderr=subprocess.PIPE)

    def capture(self):
        def mock_guard(factory, **_):
            factory(self.control, 'a' * 32)
            return {'status': 'completed', 'run_directory': str(self.control)}
        with patch.object(harness, 'ROOT', self.root), patch.object(harness, 'guard'), \
                patch.object(harness, 'sandbox', return_value=['synthetic-no-runtime']) as sandbox, \
                patch.object(harness, 'execution_limits', return_value=harness.execution_policy.Policy()), \
                patch.object(harness.execution_policy, 'run_guarded', side_effect=mock_guard), \
                redirect_stdout(io.StringIO()):
            harness.guarded_supervisor()
        self.sandbox_command = sandbox.call_args.args[0]
        return json.loads((self.control / 'source-context.json').read_text())

    def qualify(self, context):
        source = REPO / 'scripts/urbit/supervisor.py'
        spec = importlib.util.spec_from_file_location('stead_source_supervisor', source)
        supervisor = importlib.util.module_from_spec(spec)
        original_read, original_digest = Path.read_text, digests.source_sha
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == Path('/toolchain.json')
                else original_read(p, *a, **kw)), patch.object(digests, 'source_sha',
                side_effect=lambda p: original_digest(source.parent if p == Path('/code') else p)):
            spec.loader.exec_module(supervisor)
        mounts = {'/code': 'scripts/urbit', '/native': 'native', '/specs': 'specs/urbit', '/web-dev': 'web/dev',
                  '/native-tests/gall-schedule': 'tests/urbit/native_gall_schedule',
                  '/native-tests/skill-evaluation': 'tests/urbit/skill_evaluation'}
        def mounted(value):
            path = Path(value)
            for prefix, relative in mounts.items():
                if path.is_relative_to(prefix):
                    return self.root / relative / path.relative_to(prefix)
            return path
        with patch.object(supervisor, 'Path', side_effect=mounted), \
                patch.object(supervisor, 'LOADED_SOURCE_DIGEST', context['harness_sha256']), \
                patch.object(supervisor.execution_policy, 'read_json', return_value=context):
            return supervisor.qualified_source()

    def test_clean_committed_bytes_and_cache_admission(self):
        cache = self.root / 'scripts/urbit/__pycache__'
        cache.mkdir()
        (cache / 'ignored.pyc').write_bytes(b'authored untrusted cache')
        context = self.capture()
        self.assertEqual(context['dirty_paths'], [])
        self.assertTrue(context['committed_bytes_verified'])
        self.assertEqual(self.qualify(context), self.git('rev-parse', 'HEAD').decode().strip())
        self.assertEqual(self.sandbox_command, ['/usr/bin/python3', '-X',
            'pycache_prefix=/tmp/python-cache', '/code/supervisor.py'])

    def test_added_helper_and_changed_mounted_inputs_reject(self):
        context = self.capture()
        extra = self.root / 'scripts/urbit/added_after_capture.py'
        extra.write_text('VALUE = 2\n')
        with self.assertRaises(ValueError):
            self.qualify(context)
        extra.unlink()
        for name in ('native/core/desk', 'specs/urbit', 'web/dev', 'tests/urbit/native_gall_schedule',
                     'tests/urbit/skill_evaluation'):
            with self.subTest(mount=name):
                source = self.root / name / 'fixture.txt'
                source.write_text('changed after capture\n')
                with self.assertRaises(ValueError):
                    self.qualify(context)
                source.write_text('authored host fixture\n')

    def test_clean_git_status_does_not_hide_changed_committed_bytes(self):
        source = 'scripts/urbit/dev_help.py'
        self.git('update-index', '--assume-unchanged', source)
        with (self.root / source).open('a') as output:
            output.write('\n# authored changed input\n')
        context = self.capture()
        self.assertEqual(context['dirty_paths'], [])
        self.assertFalse(context['committed_bytes_verified'])
        with self.assertRaises(ValueError):
            self.qualify(context)

    def test_ignored_uncommitted_mounted_inputs_cannot_claim_exact_commit(self):
        names = [root + '/ignored.hoon' for root in ('native/core/desk', 'specs/urbit', 'web/dev',
            'tests/urbit/native_gall_schedule', 'tests/urbit/skill_evaluation')]
        names.append('native/core/desk/__pycache__/hidden.hoon')
        (self.root / '.git/info/exclude').write_text(''.join('/' + name + '\n' for name in names))
        for name in names:
            with self.subTest(input=name):
                source = self.root / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text('42\n')
                context = self.capture()
                self.assertEqual(context['dirty_paths'], [])
                self.assertNotIn(name, context['committed_files'])
                self.assertFalse(context['committed_bytes_verified'])
                with self.assertRaises(ValueError):
                    self.qualify(context)
                source.unlink()


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

    class Child:
        """Host-only child model: a repeated TERM reproduces an unclean exit."""
        def __init__(self, exit_code=0):
            self.pid = 123
            self.returncode = None
            self.exit_code = exit_code
            self.terms = 0
            self.kills = 0

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terms += 1
            if self.terms > 1:
                self.returncode = -15

        def wait(self, timeout):
            if self.returncode is None:
                self.returncode = self.exit_code
            return self.returncode

        def kill(self):
            self.kills += 1
            self.returncode = -9

    def test_overlapping_shutdown_paths_send_term_once_per_process_incarnation(self):
        children = {name: self.Child() for name in self.supervisor.SHIPS}
        self.supervisor.PROCESSES.update(children)
        # Both threads really contend for the TERM lock; no native process runs.
        workers = [threading.Thread(target=self.supervisor.signal_children) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(2)
            self.assertFalse(worker.is_alive())
        with patch.object(self.supervisor, 'record'):
            self.supervisor.all_stop()
            self.supervisor.all_stop()
        self.assertTrue(all(child.terms == 1 and child.returncode == 0 for child in children.values()))
        replacement = self.Child()  # Deliberately reuses the mocked PID.
        self.supervisor.PROCESSES['zod'] = replacement
        with patch.object(self.supervisor, 'record'):
            self.supervisor.shutdown('zod')
        self.assertEqual(replacement.terms, 1)
        self.supervisor.NORMAL_STOP.set()
        self.assertEqual(self.supervisor.completion_code(), 0)

    def test_nonzero_child_exit_stays_unclean_after_normal_stop(self):
        for code in (-15, -11, 1):
            with self.subTest(code=code):
                self.supervisor.SHUTDOWN_FAILED.clear()
                children = {name: self.Child(code if name == 'bus' else 0) for name in self.supervisor.SHIPS}
                self.supervisor.PROCESSES.update(children)
                with patch.object(self.supervisor, 'record'), self.assertRaisesRegex(RuntimeError, 'bus exit was not clean'):
                    self.supervisor.all_stop()
                self.assertTrue(all(child.returncode is not None for child in children.values()))
                self.supervisor.NORMAL_STOP.set()
                self.assertTrue(self.supervisor.SHUTDOWN_FAILED.is_set())
                self.assertEqual(self.supervisor.completion_code(), 1)

    def test_signal_and_wait_failures_do_not_abandon_other_children(self):
        for fault in ('terminate', 'wait', 'kill'):
            with self.subTest(fault=fault):
                self.supervisor.SHUTDOWN_FAILED.clear()
                children = {name: self.Child() for name in self.supervisor.SHIPS}
                self.supervisor.PROCESSES.update(children)
                with ExitStack() as stack:
                    stack.enter_context(patch.object(self.supervisor, 'record'))
                    if fault in ('wait', 'kill'):
                        stack.enter_context(patch.object(children['bus'], 'wait', side_effect=subprocess.TimeoutExpired('synthetic', 1)))
                    if fault in ('terminate', 'kill'):
                        stack.enter_context(patch.object(children['bus'], fault, side_effect=OSError('synthetic ' + fault)))
                    with self.assertRaises(RuntimeError):
                        self.supervisor.all_stop()
                self.assertTrue(self.supervisor.SHUTDOWN_FAILED.is_set())
                self.assertTrue(all(children[name].returncode == 0 for name in ('zod', 'nec', 'bud')))

    def test_normal_stop_watchdog_cannot_swallow_cleanup_failure(self):
        self.supervisor.NORMAL_STOP.set()
        self.supervisor.STOP_REQUESTED.set()
        with patch.object(self.supervisor, 'all_stop', side_effect=RuntimeError('synthetic cleanup')), patch.object(self.supervisor, 'record'):
            self.supervisor.execution_watch()
        self.assertTrue(self.supervisor.SHUTDOWN_FAILED.is_set())
        self.assertEqual(self.supervisor.completion_code(), 1)

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

        def shutdown(ship, timeout):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 15)
            attempted.append(ship)
            if ship == 'zod':
                raise RuntimeError('synthetic zod shutdown failure')

        with patch.object(self.supervisor, 'shutdown', side_effect=shutdown):
            with self.assertRaisesRegex(RuntimeError, 'synthetic zod shutdown failure'):
                self.supervisor.all_stop()
        self.assertEqual(attempted, list(self.supervisor.SHIPS))

    def test_normal_stop_watchdog_does_not_label_a_clean_stop_as_forced(self):
        self.supervisor.NORMAL_STOP.set()
        self.supervisor.STOP_REQUESTED.set()
        with patch.object(self.supervisor, 'all_stop') as stop_ships, patch.object(self.supervisor, 'record'):
            self.supervisor.execution_watch()
        stop_ships.assert_called_once()
        self.assertFalse(self.supervisor.FORCED_STOP.is_set())
        self.assertFalse(self.supervisor.PROGRESS['ready'])
        self.assertIsNone(self.supervisor.PROGRESS['error'])
        self.assertEqual(self.supervisor.completion_code(), 0)

    def test_supervisor_exit_is_nonzero_for_guard_or_initialization_failure(self):
        self.assertEqual(self.supervisor.completion_code(), 1)
        self.supervisor.NORMAL_STOP.set()
        self.supervisor.FORCED_STOP.set()
        self.assertEqual(self.supervisor.completion_code(), 1)
        self.supervisor.FORCED_STOP.clear()
        self.supervisor.INITIALIZATION_FAILED.set()
        self.supervisor.PROGRESS['stage'] = 'stopped'
        self.assertEqual(self.supervisor.completion_code(), 1)

    def test_stale_guard_latches_cancellation_before_the_busy_test_mutex(self):
        self.supervisor.MUTEX.acquire()
        worker = threading.Thread(target=self.supervisor.execution_watch, daemon=True)
        with patch.object(self.supervisor.execution_policy, 'require_lease', side_effect=RuntimeError('synthetic stale lease')), \
                patch.object(self.supervisor, 'all_stop') as stop_ships, patch.object(self.supervisor, 'record'):
            worker.start()
            try:
                self.assertTrue(self.supervisor.STOP_REQUESTED.wait(1))
                self.assertTrue(self.supervisor.FORCED_STOP.is_set())
                self.assertFalse(self.supervisor.PROGRESS['ready'])
                stop_ships.assert_not_called()
            finally:
                self.supervisor.MUTEX.release()
                worker.join(2)
            self.assertFalse(worker.is_alive())
            stop_ships.assert_called_once()

    def test_guard_stop_overwrites_a_just_written_passing_native_report(self):
        with tempfile.TemporaryDirectory(prefix='stead-native-result-guard-') as tmp:
            root = Path(tmp)
            (root / 'logs').mkdir()
            path = root / 'logs/core-synthetic.json'
            path.write_text('{"status":"pass","checks":[]}')
            self.supervisor.STOP_REQUESTED.set()
            with patch.object(self.supervisor, 'STATE', root):
                result = self.supervisor.guarded_result({'status':'pass', 'evidence_file':'.piers/fakes/logs/core-synthetic.json'})
            self.assertEqual(result['status'], 'fail')
            self.assertEqual(json.loads(path.read_text())['status'], 'fail')

    def test_forced_state_is_never_promoted_to_a_clean_seed(self):
        with tempfile.TemporaryDirectory(prefix='stead-seed-after-stop-') as tmp:
            root = Path(tmp)
            live, seed = root / 'live', root / 'seed'
            for ship in self.supervisor.SHIPS:
                (live / ship / 'base').mkdir(parents=True)
            def stopped():
                self.supervisor.FORCED_STOP.set()
            with patch.object(self.supervisor, 'LIVE', live), patch.object(self.supervisor, 'SEED', seed), \
                    patch.object(self.supervisor, 'execution_check'), patch.object(self.supervisor, 'launch'), \
                    patch.object(self.supervisor, 'wait_ready'), patch.object(self.supervisor, 'dojo'), \
                    patch.object(self.supervisor, 'record'), patch.object(self.supervisor.traceback, 'print_exc'), \
                    patch.object(self.supervisor, 'all_stop', side_effect=stopped):
                self.supervisor.initialize()
            self.assertFalse(seed.exists())
            self.assertEqual(self.supervisor.PROGRESS['stage'], 'failed')
            self.assertIn('clean seed', self.supervisor.PROGRESS['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

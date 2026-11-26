#!/usr/bin/python3
"""Fixed remote-only browser boundary host checks; no native or isolation child launch."""
import ast
import _thread
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import select
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import threading
import unittest

ROOT = Path('/input')
OUTPUT = Path('/output')
WORK = OUTPUT / 'python-host'
PHASE = 'admission'
REGISTERED_NAMES = ()
ERRORS = ('AssertionError', 'ValueError', 'TypeError', 'OSError', 'PermissionError',
          'FileNotFoundError', 'RuntimeError', 'TimeoutError', 'SyntaxError',
          'ImportError', 'ModuleNotFoundError', 'AuditDenied')
SOURCE_PATHS = ('.github/workflows/native-hosted.yml', 'driver.py', 'scripts/ci/home_asset_rehearsal/__init__.py', 'scripts/ci/home_asset_rehearsal/capture.hoon', 'scripts/ci/home_asset_rehearsal/evidence.py', 'scripts/ci/home_asset_rehearsal/result.py', 'scripts/ci/home_asset_rehearsal/runner.py', 'scripts/ci/home_asset_rehearsal/service_adapter.py', 'scripts/ci/home_asset_rehearsal/worker.py', 'scripts/ci/hosted.py', 'scripts/ci/hosted_apparmor.py', 'scripts/ci/hosted_lease.py', 'scripts/release_install.py', 'scripts/sdk_native/native.py', 'scripts/urbit/conn.py', 'scripts/urbit/core_conn.py', 'scripts/urbit/digests.py', 'scripts/urbit/execution_policy.py', 'scripts/urbit/native_tls.py', 'scripts/urbit/owned_child.py', 'scripts/urbit/team_conn.py', 'specs/urbit/toolchain.lock.json', 'tests/ci/fixtures/home_asset_outer/previous-0.chunk', 'tests/ci/fixtures/home_asset_outer/previous-1.chunk', 'tests/ci/fixtures/home_asset_outer/previous-2.chunk', 'tests/ci/fixtures/home_asset_outer/target-0.chunk', 'tests/ci/fixtures/home_asset_outer/target-1.chunk', 'tests/ci/fixtures/home_asset_outer/target-2.chunk', 'tests/ci/fixtures/home_asset_outer/target-3.chunk', 'tests/ci/test_home_asset_diagnostics.py', 'tests/ci/test_home_asset_direct.py', 'tests/ci/test_home_asset_encoding.py', 'tests/ci/test_home_asset_outer.py', 'tests/ci/test_home_asset_startup.py')
AST_PATHS = ('driver.py', 'scripts/ci/home_asset_rehearsal/__init__.py', 'scripts/ci/home_asset_rehearsal/evidence.py', 'scripts/ci/home_asset_rehearsal/result.py', 'scripts/ci/home_asset_rehearsal/runner.py', 'scripts/ci/home_asset_rehearsal/service_adapter.py', 'scripts/ci/home_asset_rehearsal/worker.py', 'scripts/ci/hosted.py', 'scripts/ci/hosted_apparmor.py', 'scripts/ci/hosted_lease.py', 'scripts/release_install.py', 'scripts/sdk_native/native.py', 'scripts/urbit/conn.py', 'scripts/urbit/core_conn.py', 'scripts/urbit/digests.py', 'scripts/urbit/execution_policy.py', 'scripts/urbit/native_tls.py', 'scripts/urbit/owned_child.py', 'scripts/urbit/team_conn.py', 'tests/ci/test_home_asset_diagnostics.py', 'tests/ci/test_home_asset_direct.py', 'tests/ci/test_home_asset_encoding.py', 'tests/ci/test_home_asset_outer.py', 'tests/ci/test_home_asset_startup.py')
MODULES = (('stead_browser_outer', 'tests/ci/test_home_asset_outer.py'), ('stead_browser_startup', 'tests/ci/test_home_asset_startup.py'), ('stead_browser_diagnostics', 'tests/ci/test_home_asset_diagnostics.py'), ('stead_browser_encoding', 'tests/ci/test_home_asset_encoding.py'), ('stead_browser_direct', 'tests/ci/test_home_asset_direct.py'))
SCOPES = {'outer': 7, 'startup': 3, 'diagnostics': 6, 'encoding': 2, 'direct': 4}


def require(ok):
    if not ok:
        raise ValueError('Fixed host profile refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value)
        value[key] = item
    return value


def read_file(relative, maximum):
    path = ROOT / relative
    require(not path.is_symlink())
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= maximum)
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            value = stream.read(maximum + 1)
        after = os.fstat(fd)
        require(len(value) == info.st_size and (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size) ==
                (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size))
        return value
    finally:
        os.close(fd)


class AuditDenied(RuntimeError):
    pass


def forbidden(*args, **kwargs):
    raise AuditDenied('Host check cannot launch an effect')


def audit(event, args):
    if event.startswith(('subprocess.', 'ctypes.', 'socket.')) or event in (
            'os.system', 'os.fork', 'os.forkpty', 'os.exec', 'os.posix_spawn', 'os.posix_spawnp',
            'os.kill', 'os.killpg', 'signal.pthread_kill'):
        forbidden()


def inventory(manifest):
    require(set(manifest['files']) == set(SOURCE_PATHS))
    result = {}
    for name in SOURCE_PATHS:
        raw = read_file(name, 4 * 1024 * 1024)
        row = manifest['files'][name]
        require(set(row) == {'bytes', 'sha256'} and type(row['bytes']) is int
                and len(raw) == row['bytes'] and sha(raw) == row['sha256'])
        result[name] = sha(raw)
    return result


def flatten(suite):
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            yield from flatten(value)
        else:
            yield value


def progress(rows=(), current=''):
    # Diagnostic only: no exception, body, credential or arbitrary log text.
    phases = ('sources', 'awaiting-parent-admission', 'ast', 'discovery', 'tests', 'post-sources', 'complete')
    statuses = ('pass', 'fail', 'error', 'skip', 'expected-failure', 'unexpected-success', 'subtest-failure')
    require(PHASE in phases and len(REGISTERED_NAMES) == 22
            and (current == '' or current in REGISTERED_NAMES))
    completed = {}
    for row in rows:
        require(row['test'] in REGISTERED_NAMES and row['status'] in statuses)
        completed[row['test']] = row['status']
    require(len(completed) <= 22)
    value = {'protocol': 'stead.remote-host-progress/1', 'phase': PHASE, 'current': current,
             'completed': [{'test': name, 'status': status} for name, status in completed.items()],
             'counts': {status: sum(value == status for value in completed.values()) for status in statuses}}
    raw = canonical(value)
    require(len(raw) + 1 <= 16384)
    temporary = OUTPUT / 'test-progress.json.next'
    with temporary.open('xb') as stream:
        stream.write(raw + b'\n')
    temporary.chmod(0o600)
    os.replace(temporary, OUTPUT / 'test-progress.json')


class Results(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = []

    def startTest(self, test):
        super().startTest(test)
        progress(self.rows, test.id())

    def stopTest(self, test):
        super().stopTest(test)
        progress(self.rows)

    def record(self, test, status, error=None):
        name = type(error[1]).__name__ if error else 'none'
        identifier = test.id()
        require(identifier in REGISTERED_NAMES and status in (
            'pass', 'fail', 'error', 'skip', 'expected-failure', 'unexpected-success', 'subtest-failure'))
        row = {'test': identifier, 'status': status,
               'error_class': name if name == 'none' or name in ERRORS else 'unrecognized'}
        for index, prior in enumerate(self.rows):
            if prior['test'] == identifier:
                # One bounded outcome per registered test. First non-pass is
                # sticky; later successes never hide a failed subtest or error.
                if prior['status'] == 'pass' and status != 'pass':
                    self.rows[index] = row
                return
        require(len(self.rows) < len(REGISTERED_NAMES))
        self.rows.append(row)

    def addSuccess(self, test):
        self.record(test, 'pass')

    def addFailure(self, test, error):
        self.record(test, 'fail', error)

    def addError(self, test, error):
        self.record(test, 'error', error)

    def addSkip(self, test, reason):
        self.record(test, 'skip')

    def addExpectedFailure(self, test, error):
        self.record(test, 'expected-failure', error)

    def addUnexpectedSuccess(self, test):
        self.record(test, 'unexpected-success')

    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.record(test, 'subtest-failure', error)


def main():
    global PHASE, REGISTERED_NAMES
    started = time.monotonic()
    report = {'protocol': 'stead.remote-browser-boundary-host-result/1', 'status': 'fail',
              'classification': 'source-AST-and-host-only-constructed-boundary-tests',
              'actual_native_seed_executed': False, 'browser_executed': False, 'model_calls': False, 'actual_build_probe_executed': False, 'actual_doc_proof_executed': False, 'native_executed': False, 'qualifies_g3': False,
              'parent_admitted': False, 'tests': [], 'source_hashes_before': {}, 'source_hashes_after': {}}
    try:
        require(sys.flags.isolated and sys.dont_write_bytecode and sys.platform == 'linux'
                and os.getuid() > 0 and os.getgid() > 0 and Path(__file__).resolve() == ROOT / 'driver.py'
                and len(sys.argv) == 2 and re.fullmatch('[0-9a-f]{64}', sys.argv[1]))
        require(os.statvfs(ROOT).f_flag & os.ST_RDONLY)
        # The reviewed owner verifies authority masks, inaccessible /root and
        # private systemd /run internals before sending go. Do not mistake
        # those proven placeholders for exposed host authority here.
        out = OUTPUT.lstat()
        require(stat.S_ISDIR(out.st_mode) and out.st_uid == os.getuid() and out.st_gid == os.getgid()
                and out.st_mode & 0o777 == 0o700)
        WORK.mkdir(mode=0o700)
        (WORK / 'tmp').mkdir(mode=0o700)
        tempfile.tempdir = str(WORK / 'tmp')
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # Keep the passed host profile's bounded per-file limit; no larger fixture writes.
        resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
        def timeout(*args):
            raise TimeoutError('Host test deadline')
        signal.signal(signal.SIGALRM, timeout)
        raw = read_file('manifest.json', 131072)
        require(sha(raw) == sys.argv[1])
        manifest = json.loads(raw, object_pairs_hook=unique)
        require(set(manifest) == {'protocol', 'source_manifest_pins', 'files', 'test_names', 'expected_tests', 'test_scopes', 'profile', 'owner_uid', 'owner_gid'}
                and manifest['protocol'] == 'stead.remote-browser-boundary-host-input/1'
                and type(manifest['expected_tests']) is int and manifest['expected_tests'] == 22
                and manifest['profile'] == 'python-host-saved8-direct/1'
                and type(manifest['owner_uid']) is int and type(manifest['owner_gid']) is int
                and os.getuid() == manifest['owner_uid'] and os.getgid() == manifest['owner_gid'])
        require(type(manifest['test_scopes']) is dict and set(manifest['test_scopes']) == set(SCOPES)
                and all(type(manifest['test_scopes'][name]) is int and manifest['test_scopes'][name] == count for name, count in SCOPES.items()))
        require(type(manifest['source_manifest_pins']) is dict and set(manifest['source_manifest_pins']) == set(SCOPES)
                and all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) for value in manifest['source_manifest_pins'].values()))
        names = manifest['test_names']
        require(isinstance(names, list) and len(names) == 22 and len(set(names)) == 22
                and all(isinstance(name, str) and re.fullmatch(r'(?:stead_browser_outer\.Saved8OuterTests|stead_browser_startup\.Saved8StartupTests|stead_browser_diagnostics\.Saved8DiagnosticTests|stead_browser_encoding\.Saved8EncodingTests|stead_browser_direct\.Saved8DirectTests)\.test_[a-z0-9_]+', name) for name in names))
        require(set(str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()) == {*SOURCE_PATHS, 'manifest.json'})
        report['manifest_sha256'] = sha(raw)
        report['source_manifest_pins'] = manifest['source_manifest_pins']
        REGISTERED_NAMES = tuple(names)
        PHASE = 'sources'
        progress()
        before = inventory(manifest)
        report['source_inventory_sha256_before'] = sha(canonical(before))
        report['source_files'] = len(before)
        report['source_hashes_before'] = {name: before[name] for name in AST_PATHS}
        PHASE = 'awaiting-parent-admission'
        progress()
        ready = OUTPUT / 'runner-ready.json'
        temporary = OUTPUT / 'runner-ready.json.next'
        require(not ready.exists())
        with temporary.open('xb') as stream:
            stream.write(canonical({'profile': 'python-host', 'stage': 'awaiting-parent-admission'}) + b'\n')
        temporary.chmod(0o600)
        os.replace(temporary, ready)
        admission = bytearray()
        deadline = time.monotonic() + 30
        while True:
            require(time.monotonic() < deadline)
            if not select.select([0], [], [], .2)[0]:
                continue
            chunk = os.read(0, 4 - len(admission))
            if not chunk:
                break
            admission.extend(chunk)
            require(len(admission) <= 3)
        require(bytes(admission) == b'go\n')
        report['parent_admitted'] = True
        tests_started = time.monotonic()
        signal.alarm(25)
        PHASE = 'ast'
        progress()
        for name in AST_PATHS:
            ast.parse(read_file(name, 131072), filename=name)
        report['ast_files'] = len(AST_PATHS)
        # Defense in depth independent of test monkeypatches. No child, native
        # runtime, namespace, network or dynamic-library call can be evidence.
        # Standard-library ctypes was imported by this trusted driver only.
        # Its constructors and process API are fenced before repository import.
        ctypes.CDLL = forbidden
        ctypes.PyDLL = forbidden
        ctypes.pythonapi = forbidden
        ctypes.CFUNCTYPE = forbidden
        sys.addaudithook(audit)
        for name in ('fork', 'forkpty', 'unshare', 'setns', 'system', 'posix_spawn', 'posix_spawnp'):
            if hasattr(os, name):
                setattr(os, name, forbidden)
        subprocess.Popen = forbidden
        subprocess.run = forbidden
        # Host cases may replace these with inert doubles; real signals remain denied.
        for name in ('kill', 'killpg'):
            if hasattr(os, name):
                setattr(os, name, forbidden)
        for name in ('raise_signal', 'pthread_kill', 'pidfd_send_signal'):
            if hasattr(signal, name):
                setattr(signal, name, forbidden)
        # Thread lifecycle is tested through authored inert doubles only.
        threading.Thread.start = forbidden
        for name in ('start_new_thread', 'start_new', 'start_joinable_thread'):
            if hasattr(_thread, name):
                setattr(_thread, name, forbidden)
        for name in ('_start_new_thread', '_start_joinable_thread'):
            if hasattr(threading, name):
                setattr(threading, name, forbidden)
        PHASE = 'discovery'
        progress()
        # Exact source/test helpers and readonly data are pinned.
        # The sole test module loads only its closed helper namespace
        # after this fence and restores temporary module/path bindings.
        # Seven bounded test chunks reassemble the exact public archives
        # in memory only. Native/process/authority effects remain inert.
        suite = unittest.TestSuite()
        for module_name, path in MODULES:
            spec = importlib.util.spec_from_file_location(module_name, ROOT / path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        observed = [test.id() for test in flatten(suite)]
        require(len(observed) == 22 and len(set(observed)) == 22 and set(observed) == set(names))
        PHASE = 'tests'
        progress()
        result = Results()
        suite.run(result)
        report['tests'] = result.rows
        require(result.testsRun == 22 and len(result.rows) == 22
                and {row['test'] for row in result.rows} == set(names)
                and all(row['status'] == 'pass' for row in result.rows))
        report['test_scopes'] = {name: sum(row['test'].startswith('stead_browser_' + name + '.') for row in result.rows) for name in SCOPES}
        require(report['test_scopes'] == SCOPES)
        PHASE = 'post-sources'
        progress(result.rows)
        after = inventory(manifest)
        report['source_inventory_sha256_after'] = sha(canonical(after))
        report['source_hashes_after'] = {name: after[name] for name in AST_PATHS}
        require(before == after)
        require(report['source_hashes_before'] == report['source_hashes_after']
                and not list((WORK / 'tmp').iterdir()))
        (WORK / 'tmp').rmdir()
        require(not list(WORK.iterdir()) and time.monotonic() - tests_started < 25)
        PHASE = 'complete'
        progress(result.rows)
        report.update(status='pass', expected_tests=22, passed_tests=22, private_temp_empty=True)
    except BaseException as error:
        kind = type(error).__name__
        report['error_class'] = kind if kind in ERRORS else 'unrecognized'
    finally:
        signal.alarm(0)
        report['phase'] = PHASE
        report['elapsed_ms'] = round((time.monotonic() - started) * 1000)
    raw = canonical(report)
    require(len(raw) + 1 <= 16384)
    if WORK.exists():
        with (WORK / 'report.json').open('xb') as stream:
            stream.write(raw + b'\n')
        (WORK / 'report.json').chmod(0o600)
    sys.stdout.buffer.write(raw + b'\n')
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

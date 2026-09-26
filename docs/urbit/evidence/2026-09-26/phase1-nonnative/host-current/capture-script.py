#!/usr/bin/env python3
"""Capture the seven current host suites. Preparation does not execute tests.

Run only after the integrator releases the native slot and commits final source:
  python3 .runtime/phase01-20260926/capture_final_host.py --executor /root

This launches only Python host tests, inside its own 50%/10ms CPU19 scope.
The old127 artifacts are never overwritten. Final status follows the observed
worker/scope exit, exact test inventory and unchanged committed input bytes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import subprocess
import sys
import time
import traceback
import unittest

MODULES = ('test_execution_policy', 'test_runtime_guard_adversarial',
           'test_harness_safety', 'test_dev_flow', 'test_delivery_cases',
           'test_delivery_evidence_regressions', 'test_delivery_suite')
ROOTS = ('scripts/urbit', 'native', 'specs/urbit', 'tests/urbit')
CPU = 19
NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK


def require(value, message):
    if not value:
        raise RuntimeError(message)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, maximum=16 * 1024 * 1024):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Redirected input: ' + str(path))
    fd = os.open(path, os.O_RDONLY | NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum,
                'Input is not a bounded singly linked regular file')
        raw = source.read(maximum + 1)
    require(len(raw) <= maximum, 'Input byte limit')
    return raw


def write_new(path, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], timeout=15)


def remotes(repo):
    for option in ([], ['--push']):
        require(git(repo, 'remote', 'get-url', *option, 'origin').strip()
                == b'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong derivative origin')
    require(git(repo, 'remote', 'get-url', '--push', 'upstream').strip()
            == b'DISABLED_UPSTREAM_PUSH', 'Upstream must remain read-only')


def snapshot(repo):
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    status = git(repo, 'status', '--porcelain', '--', *ROOTS, 'Makefile').decode().strip()
    blobs = {}
    for entry in git(repo, 'ls-tree', '-r', '-z', head, '--', *ROOTS, 'Makefile').split(b'\0'):
        if entry:
            meta, name = entry.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            require(kind == 'blob' and mode in ('100644', '100755'), 'Nonregular committed source')
            blobs[name.decode()] = oid
    actual, total, count = {}, 0, 0
    for root in ROOTS:
        for base, directories, names in os.walk(repo / root, followlinks=False):
            if root in ('scripts/urbit', 'tests/urbit'):
                directories[:] = [name for name in directories if name != '__pycache__']
            for name in directories + names:
                count += 1
                require(count <= 8192, 'Source entry limit')
                path = Path(base) / name
                require(not path.is_symlink(), 'Redirected source entry')
                if path.is_dir():
                    continue
                raw = read(path)
                total += len(raw)
                require(total <= 64 * 1024 * 1024, 'Source byte limit')
                actual[path.relative_to(repo).as_posix()] = raw
    actual['Makefile'] = read(repo / 'Makefile')
    hashes = {name: digest(raw) for name, raw in sorted(actual.items())}
    verified = set(actual) == set(blobs) and all(
        hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blobs[name]
        for name, raw in actual.items())
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == head, 'HEAD changed during capture')
    return {'head': head, 'status': status, 'files': hashes, 'committed_bytes_verified': verified,
            'repository_status': git(repo, 'status', '--porcelain').decode().strip()}


def scope_state(unit):
    result = subprocess.run(['systemctl', '--user', 'show', unit,
        '--property=LoadState,ActiveState,ControlGroup,Result'], capture_output=True, text=True, timeout=10)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    return {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, **values}


def resource_readback(unit):
    lines = Path('/proc/self/cgroup').read_text().splitlines()
    require(len(lines) == 1 and lines[0].startswith('0::'), 'Unified cgroup required')
    group = lines[0][3:]
    require(group.startswith('/user.slice/') and group.endswith('/' + unit)
            and '..' not in group.split('/'), 'Wrong capture scope')
    root = Path('/sys/fs/cgroup' + group)
    result = {'scope': unit, 'control_group': group, 'cpu_max': (root / 'cpu.max').read_text().strip(),
              'affinity': sorted(os.sched_getaffinity(0)),
              'pids': sorted(map(int, (root / 'cgroup.procs').read_text().split()))}
    require(result['cpu_max'] == '5000 10000' and result['affinity'] == [CPU], 'CPU limit readback differs')
    require(os.getpid() in result['pids'], 'Capture process missing from owned scope')
    return result


def hold_lock(stack, path, private=False):
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Redirected lifetime lock')
    fd = os.open(path, os.O_RDWR | NOFOLLOW)  # Do not create or rewrite fixture state.
    stack.callback(os.close, fd)
    info = os.fstat(fd)
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
            and (not private or not info.st_mode & 0o077), 'Invalid owned lifetime lock')
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def run_suites(out, report):
    rows, events, selected = [], [], []
    captured = None
    event_stream = (out / 'test-events.jsonl').open('x')

    def event(value):
        events.append(value)
        event_stream.write(json.dumps(value, sort_keys=True) + '\n')
        event_stream.flush()

    class CapturedResult(unittest.TextTestResult):
        current = None

        def __init__(self, *args, **kwargs):
            nonlocal captured
            super().__init__(*args, **kwargs)
            captured = self

        def startTest(self, test):
            super().startTest(test)
            self.current = {'id': test.id(), 'status': 'unreported', 'started_ns': time.monotonic_ns()}
            event({'event': 'start', **self.current})

        def outcome(self, name, test):
            if self.current is not None:
                if name != 'passed' or self.current['status'] == 'unreported':
                    self.current['status'] = name
            else:
                event({'event': 'fixture_outcome', 'id': test.id(), 'status': name})

        def addSuccess(self, test):
            super().addSuccess(test)
            self.outcome('passed', test)

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.outcome('failed', test)

        def addError(self, test, err):
            super().addError(test, err)
            self.outcome('error', test)

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self.outcome('skipped', test)
            event({'event': 'skip', 'id': test.id(), 'status': 'skipped', 'reason': reason})

        def addExpectedFailure(self, test, err):
            super().addExpectedFailure(test, err)
            self.outcome('expected_failure', test)

        def addUnexpectedSuccess(self, test):
            super().addUnexpectedSuccess(test)
            self.outcome('unexpected_success', test)

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            outcome = 'passed' if err is None else 'failed'
            if err is not None:
                self.outcome('failed', test)
            event({'event': 'subtest', 'parent': test.id(), 'id': subtest.id(), 'status': outcome})

        def stopTest(self, test):
            self.current['finished_ns'] = time.monotonic_ns()
            rows.append(dict(self.current))
            event({'event': 'finish', **self.current})
            self.current = None
            super().stopTest(test)

    def ids(suite):
        for child in suite:
            if isinstance(child, unittest.TestSuite):
                yield from ids(child)
            else:
                yield child.id()

    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromNames(MODULES)
        selected = list(ids(suite))
        write_new(out / 'selected-tests.json', {'test_ids': selected, 'loader_errors': loader.errors})
        require(not loader.errors and selected and len(selected) == len(set(selected))
                and {name.split('.')[0] for name in selected} == set(MODULES), 'Missing/duplicate/import-failed test inventory')
        # The loaded suites/helpers came from this run's unused cache prefix.
        # Tests intentionally exercising ordinary adjacent bytecode must use
        # Python's ordinary cache location when calling py_compile themselves.
        # Keep imports from writing caches; explicit py_compile remains real.
        report['loader_pycache_prefix'] = sys.pycache_prefix
        sys.pycache_prefix = None
        report['test_pycache_prefix'] = sys.pycache_prefix
        report['test_dont_write_bytecode'] = sys.dont_write_bytecode
        unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=CapturedResult).run(suite)
    finally:
        complete = bool(selected) and [row['id'] for row in rows] == selected and captured is not None and captured.testsRun == len(selected)
        report.update(observed_test_ids=[row['id'] for row in rows], observed_tests=rows,
                      started_test_ids=[e['id'] for e in events if e['event'] == 'start'],
                      expected_test_ids=selected, tests_observed=captured.testsRun if captured else 0,
                      test_inventory_complete=complete,
                      all_tests_passed=bool(complete and captured.wasSuccessful()
                          and not captured.skipped and not captured.expectedFailures and not captured.unexpectedSuccesses
                          and all(r['status'] == 'passed' for r in rows)))
        event_stream.close()


def worker(repo, out, unit, executor):
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(out / 'unused-python-cache')
    sys.path[:0] = [str(repo / 'tests/urbit'), str(repo / 'scripts/urbit')]
    os.chdir(repo)
    began = time.monotonic()
    report = {'protocol': 'stead.host-execution/1', 'status': 'failed', 'started_at': utc(),
              'reviewer': executor, 'executor': executor, 'native_execution': False,
              'classification': 'host-mocked-execution', 'thermal_sensors': 'mocked; no thermal calibration claim',
              'working_directory': 'repository root',
              'scope': 'Exactly seven host suites. Broader source inventory includes opaque fixture inputs, not claims that every file was executed.',
              'test_loader': {'entrypoint': 'unittest.TextTestRunner', 'verbosity': 2, 'modules': list(MODULES)}}
    before = None
    try:
        remotes(repo)
        report['resources_before'] = resource_readback(unit)
        with ExitStack() as locks:
            hold_lock(locks, repo / '.runtime/native-execution.lock', private=True)
            hold_lock(locks, repo / '.piers/fakes/lifecycle.lock')
            report['held_idle_locks'] = ['.runtime/native-execution.lock', '.piers/fakes/lifecycle.lock']
            before = snapshot(repo)
            report.update(base_head_before=before['head'], source_status_before=before['status'],
                          source_files_before=before['files'], source_uncommitted=bool(before['status']),
                          repository_status_before=before['repository_status'],
                          committed_bytes_verified_before=before['committed_bytes_verified'])
            require(not before['status'] and before['committed_bytes_verified'], 'Final committed clean source required')
            report['guard_sha256'] = before['files']['scripts/urbit/execution_policy.py']
            write_new(out / 'before.json', report)
            try:
                run_suites(out, report)
            finally:
                after = snapshot(repo)
                report.update(base_head_after=after['head'], source_status_after=after['status'],
                              source_files_after=after['files'], source_files_unchanged=after['files'] == before['files'],
                              repository_status_after=after['repository_status'],
                              committed_bytes_verified_after=after['committed_bytes_verified'])
                report['resources_after'] = resource_readback(unit)
            require(all(before[key] == after[key] for key in ('head', 'status', 'files', 'committed_bytes_verified')),
                    'Source, HEAD or status changed during host execution')
            require(set(report['resources_after']['pids']) <= set(report['resources_before']['pids']),
                    'Host test child remains in capture scope')
            require(report.get('all_tests_passed') is True, 'Incomplete, skipped or nonpassing host test results')
            report['status'] = 'passed'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        traceback.print_exc()
    finally:
        report.update(completed_at=utc(), elapsed_seconds=time.monotonic() - began)
        write_new(out / 'worker.json', report)
    return 0 if report['status'] == 'passed' else 1


def finished_scope(unit):
    state = scope_state(unit)
    group = state.get('ControlGroup')
    if group:
        require(group.startswith('/user.slice/') and group.endswith('/' + unit) and '..' not in group.split('/'),
                'Refusing unrelated scope path')
        events = Path('/sys/fs/cgroup' + group) / 'cgroup.events'
        if events.exists():
            state['events'] = events.read_text()
            require('populated 0' in state['events'].splitlines(), 'Capture scope still populated')
    require(state.get('LoadState') == 'not-found' or state.get('ActiveState') in ('inactive', 'failed'),
            'Capture scope did not finish')
    require(state.get('LoadState') == 'not-found' or state.get('Result') == 'success',
            'Capture scope did not complete successfully')
    return state


def stop_owned_scope(unit, child):
    records = []
    for name in ('SIGTERM', 'SIGKILL'):
        try:
            outcome = subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=all', '--signal=' + name, unit],
                                     capture_output=True, text=True, timeout=10)
            records.append({'signal': name, 'exit_code': outcome.returncode,
                            'stdout': outcome.stdout, 'stderr': outcome.stderr})
        except BaseException as error:
            records.append({'signal': name, 'error': type(error).__name__ + ': ' + str(error)})
        try:
            child.wait(timeout=5)
            break
        except subprocess.TimeoutExpired:
            continue
    return records


def output_binding(path):
    # Logs remain exact, including failed/large output. Hash streaming bounds memory.
    fd = os.open(path, os.O_RDONLY | NOFOLLOW)
    hashed, count = hashlib.sha256(), 0
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Invalid captured artifact')
        for chunk in iter(lambda: source.read(65536), b''):
            hashed.update(chunk)
            count += len(chunk)
        require(count == info.st_size, 'Captured artifact changed during hashing')
    return {'path': path.name, 'bytes': count, 'sha256': hashed.hexdigest()}


def launch(repo, executor):
    remotes(repo)
    require(CPU in os.sched_getaffinity(0), 'Requested CPU19 is unavailable')
    parent = repo / '.runtime/phase01-20260926'
    require(parent.is_dir() and not any(p.is_symlink() for p in (parent, *parent.parents)), 'Invalid capture parent')
    token = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower() + '-' + secrets.token_hex(4)
    out = parent / ('host-recapture-' + token)
    out.mkdir(mode=0o700)
    frozen = out / 'capture-script.py'
    write_new(frozen, read(Path(__file__)))
    unit = 'stead-host-recapture-' + token + '.scope'
    command = ['systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit,
               '-p', 'CPUQuota=50%', '-p', 'CPUQuotaPeriodSec=10ms', '-p', 'RuntimeMaxSec=300s',
               '--', 'taskset', '-c', str(CPU), '/usr/bin/python3', '-B', '-X',
               'pycache_prefix=' + str(out / 'unused-python-cache'), str(frozen),
               '--worker', str(out), '--repo', str(repo), '--unit', unit, '--executor', executor]
    environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(repo / 'tests/urbit')}
    launch_record = {'command': command, 'started_at': utc(), 'status': 'running', 'unit': unit,
                     'environment_overrides': {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': 'tests/urbit'}}
    write_new(out / 'launch.json', launch_record)
    began, code, cleanup, failure, cancellation = time.monotonic(), None, None, None, []
    try:
        with (out / 'host-current.stdout.log').open('xb') as stdout, (out / 'host-current.stderr.log').open('xb') as stderr:
            child = subprocess.Popen(command, cwd=repo, env=environment, stdout=stdout, stderr=stderr)
            try:
                code = child.wait(timeout=310)
            except BaseException:
                cancellation = stop_owned_scope(unit, child)
                code = child.poll()
                raise
    except BaseException as error:
        failure = type(error).__name__ + ': ' + str(error)
    try:
        cleanup = finished_scope(unit)
    except BaseException as error:
        failure = (failure + '; ' if failure else '') + type(error).__name__ + ': ' + str(error)
    result = {
        'protocol': 'stead.host-execution/1', 'status': 'failed', 'native_execution': False,
        'observed_test_ids': [], 'tests_observed': 0, 'error': 'No completed worker record'}
    try:
        result = json.loads(read(out / 'worker.json'))
        require(isinstance(result, dict), 'Malformed worker record')
    except BaseException as error:
        result = {'protocol': 'stead.host-execution/1', 'status': 'failed', 'native_execution': False,
                  'observed_test_ids': [], 'tests_observed': 0, 'error': type(error).__name__ + ': ' + str(error)}
    result.update(command=command, exit_code=code, outer_elapsed_seconds=time.monotonic() - began,
                  environment_overrides=launch_record['environment_overrides'], scope_completion=cleanup,
                  output_path_base='artifact directory', capture_script_sha256=digest(read(frozen)),
                  cancellation=cancellation)
    if code != 0 or cleanup is None or failure is not None or result.get('all_tests_passed') is not True:
        result.update(status='failed', outer_error=failure)
    result['outputs'] = {}
    for name in ('host-current.stdout.log', 'host-current.stderr.log', 'capture-script.py',
                 'launch.json', 'before.json', 'selected-tests.json', 'test-events.jsonl', 'worker.json'):
        if (out / name).exists():
            try:
                result['outputs'][name] = output_binding(out / name)
            except BaseException as error:
                result.update(status='failed', artifact_error=type(error).__name__ + ': ' + str(error))
    write_new(out / 'host-current.json', result)
    print(json.dumps({'status': result['status'], 'record': str((out / 'host-current.json').relative_to(repo)),
                      'sha256': digest(read(out / 'host-current.json')), 'exit_code': code}, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    def terminated(signum, frame):
        raise InterruptedError('Capture received signal ' + str(signum))
    signal.signal(signal.SIGTERM, terminated)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executor', required=True, help='Actual executing agent identity, for example /root')
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--unit', help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(re.fullmatch(r'/root(?:/[a-z0-9_]+)*', args.executor), 'Explicit actual agent identity required')
    repo = args.repo.absolute()
    if args.worker:
        require(args.unit and re.fullmatch(r'stead-host-recapture-[a-z0-9-]+\.scope', args.unit), 'Invalid worker scope')
        raise SystemExit(worker(repo, args.worker.absolute(), args.unit, args.executor))
    require(args.unit is None, 'Unit is selected by the launcher')
    raise SystemExit(launch(repo, args.executor))

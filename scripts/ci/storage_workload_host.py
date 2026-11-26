"""Fixed four-case controller check on disposable CI; no native workload."""
import ctypes
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATHS = ('scripts/ci/storage_workload_host.py', 'scripts/urbit/storage_workload.py',
         'scripts/urbit/team_check.py', 'tests/urbit/test_storage_workload.py',
         'native/core/desk/gen/stead-storage-observation.hoon',
         'specs/urbit/storage-workload-initial.json')
NAMES = (
    'test_exact_fixed_workload_scopes_revisions_readbacks_and_cursor_boundary',
    'test_wrong_actor_receipt_scope_or_exact_body_never_counts_as_measurement_success',
    'test_native_storage_requires_exact_observed_counts_and_canonical_atom',
    'test_percentiles_and_deadlines_do_not_fabricate_success_or_accept_boolean_numbers',
)


def denied(*_args, **_kwargs):
    raise RuntimeError('Synthetic host check forbids process or network effects')


def audit(event, _args):
    if event.startswith(('subprocess.', 'ctypes.', 'socket.')) or event in (
        'os.system', 'os.fork', 'os.forkpty', 'os.exec', 'os.posix_spawn', 'os.posix_spawnp',
        'os.kill', 'os.killpg', 'signal.pthread_kill'):
        denied()


def pins():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PATHS}


class Observed(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append({'name': test._testMethodName, 'status': 'pass', 'error_class': 'none'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.rows.append({'name': test._testMethodName, 'status': 'fail', 'error_class': err[0].__name__})

    def addError(self, test, err):
        super().addError(test, err)
        self.rows.append({'name': test._testMethodName, 'status': 'error', 'error_class': err[0].__name__})


def main():
    before = pins()
    started = time.monotonic_ns()
    report = {'protocol': 'stead.storage-workload-host/1', 'status': 'fail', 'tests': [],
              'source_hashes_before': before, 'source_hashes_after': None,
              'python': sys.version, 'native_executed': False, 'pilot_accessed': False,
              'synthetic_controller_samples_only': True, 'actual_native_measurements': None}
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (1500 * 1024**2, 1500 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
        signal.alarm(25)
        sys.addaudithook(audit)
        for name in ('fork', 'forkpty', 'system', 'posix_spawn', 'posix_spawnp', 'unshare', 'setns'):
            if hasattr(os, name):
                setattr(os, name, denied)
        subprocess.Popen = subprocess.run = socket.socket = socket.create_connection = denied
        ctypes.CDLL = ctypes.PyDLL = ctypes.CFUNCTYPE = denied
        threading.Thread.start = denied
        spec = importlib.util.spec_from_file_location('storage_cases', ROOT / 'tests/urbit/test_storage_workload.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actual = unittest.defaultTestLoader.getTestCaseNames(module.StorageWorkloadTests)
        if set(actual) != set(NAMES) or len(actual) != 4:
            raise ValueError('Fixed four-case inventory differs')
        result = Observed()
        unittest.TestSuite(module.StorageWorkloadTests(name) for name in NAMES).run(result)
        report['tests'] = result.rows
        after = pins()
        report['source_hashes_after'] = after
        if (result.testsRun != 4 or len(result.rows) != 4 or not result.wasSuccessful()
                or before != after or any(row['status'] != 'pass' for row in result.rows)):
            raise AssertionError('Fixed workload controller checks failed')
        report['status'] = 'pass'
    except BaseException as error:
        report['error_class'] = type(error).__name__
    finally:
        signal.alarm(0)
        report['elapsed_ns'] = time.monotonic_ns() - started
        raw = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
        if len(raw) > 16384:
            raise ValueError('Host report bound')
        (ROOT / 'storage-host-report.json').write_bytes(raw)
    print(json.dumps({'status': report['status'], 'tests': report['tests'],
                      'native_executed': False, 'actual_native_measurements': None}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

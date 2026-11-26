"""Fixed inert Saved8 regressions on an isolated GitHub runner.

Reuses the exact source-bound host18 driver helpers and effect fence. This is
not the Lightsail owner's namespace/resource/cleanup proof and makes no native
compilation, capture, rehearsal, deployment or production-authority claim.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time

MANIFEST_SHA = '3692a49eef70b40ed0c0b190b296966dcf1459cb5fbcc772152ddc22c6998c44'
DRIVER_SHA = '136de1b21080760c622b342528b365d033cb01cced314f3a0330f6502782137c'
CONTROLLER = 'f77bd6b9a5da79f89cd855fcdf91900d79fe873b'
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT.parent / 'candidate'
OUT = ROOT.parent / 'saved8-direct-host-output'


def require(ok):
    if not ok:
        raise ValueError('Fixed disposable Saved8 host check refused')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def fence(H):
    # Verbatim effect-fence statements from the reviewed original host driver.
    H.ctypes.CDLL = H.forbidden
    H.ctypes.PyDLL = H.forbidden
    H.ctypes.pythonapi = H.forbidden
    H.ctypes.CFUNCTYPE = H.forbidden
    sys.addaudithook(H.audit)
    for name in ('fork', 'forkpty', 'unshare', 'setns', 'system', 'posix_spawn', 'posix_spawnp'):
        if hasattr(os, name):
            setattr(os, name, H.forbidden)
    H.subprocess.Popen = H.forbidden
    H.subprocess.run = H.forbidden
    for name in ('kill', 'killpg'):
        if hasattr(os, name):
            setattr(os, name, H.forbidden)
    for name in ('raise_signal', 'pthread_kill', 'pidfd_send_signal'):
        if hasattr(signal, name):
            setattr(signal, name, H.forbidden)
    H.threading.Thread.start = H.forbidden
    for name in ('start_new_thread', 'start_new', 'start_joinable_thread'):
        if hasattr(H._thread, name):
            setattr(H._thread, name, H.forbidden)
    for name in ('_start_new_thread', '_start_joinable_thread'):
        if hasattr(H.threading, name):
            setattr(H.threading, name, H.forbidden)


def main():
    require(sys.flags.isolated and sys.dont_write_bytecode and sys.platform == 'linux'
            and os.getuid() > 0 and len(sys.argv) == 1)
    raw = (ROOT / 'specs/urbit/saved8-direct-host.json').read_bytes()
    driver = (ROOT / 'scripts/ci/saved8_direct_fixture_driver.py').read_bytes()
    require(sha(raw) == MANIFEST_SHA and sha(driver) == DRIVER_SHA)
    manifest = json.loads(raw)
    require(manifest['expected_tests'] == 22 and len(manifest['files']) == 34)
    OUT.mkdir(mode=0o700)
    work = OUT / 'python-host'; work.mkdir(mode=0o700)
    tmp = work / 'tmp'; tmp.mkdir(mode=0o700)
    input_root = ROOT.parent / 'saved8-direct-host-input'; input_root.mkdir(mode=0o700)
    for name, expected in manifest['files'].items():
        # Workflow data belongs to the actual main workflow, not controller ancestry.
        data = driver if name == 'driver.py' else ((ROOT if name == '.github/workflows/native-hosted.yml'
                                                  else CANDIDATE) / name).read_bytes()
        require(len(data) == expected['bytes'] and sha(data) == expected['sha256'])
        path = input_root / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(data)
        path.chmod(0o400)
    path = input_root / 'manifest.json'; path.write_bytes(raw); path.chmod(0o400)
    spec = importlib.util.spec_from_file_location('saved8_fixed_fixture_driver', input_root / 'driver.py')
    H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
    H.ROOT, H.OUTPUT, H.WORK = input_root, OUT, work
    H.REGISTERED_NAMES = tuple(manifest['test_names'])
    tempfile.tempdir = str(tmp)
    before = H.inventory(manifest)
    for name in H.AST_PATHS: ast.parse((input_root / name).read_bytes(), filename=name)
    report = {'protocol': 'stead.saved8-disposable-host-result/1', 'status': 'fail',
        'scope': '22 inert Python cases only; no native or authority-host isolation claim',
        'controller': CONTROLLER, 'manifest_sha256': MANIFEST_SHA, 'driver_sha256': DRIVER_SHA,
        'sources_before': before, 'sources_after': None, 'tests': [], 'expected_tests': 22,
        'native_executed': False, 'model_executed': False, 'live_authority_used': False}
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
    resource.setrlimit(resource.RLIMIT_AS, (1500 * 1024**2, 1500 * 1024**2))
    def timeout(*unused): raise TimeoutError('Fixed 25-second host check deadline')
    signal.signal(signal.SIGALRM, timeout)
    started = time.monotonic_ns()
    fence(H)
    signal.alarm(25)
    try:
        H.PHASE = 'discovery'
        suite = H.unittest.TestSuite()
        for module_name, relative in H.MODULES:
            spec = importlib.util.spec_from_file_location(module_name, input_root / relative)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            suite.addTests(H.unittest.defaultTestLoader.loadTestsFromModule(module))
        observed = [case.id() for case in H.flatten(suite)]
        require(len(observed) == len(set(observed)) == 22 and set(observed) == set(H.REGISTERED_NAMES))
        H.PHASE = 'tests'; result = H.Results(); suite.run(result)
        report['tests'] = result.rows
        require(result.testsRun == len(result.rows) == 22 and all(row['status'] == 'pass' for row in result.rows)
                and {row['test'] for row in result.rows} == set(H.REGISTERED_NAMES))
        require(not list(tmp.iterdir()))
        report['sources_after'] = H.inventory(manifest)
        require(report['sources_after'] == before)
        report['status'] = 'pass'
    except BaseException as error:
        report['error_class'] = type(error).__name__ if type(error).__name__ in H.ERRORS else 'unrecognized'
    finally:
        signal.alarm(0)
        report['elapsed_ns'] = time.monotonic_ns() - started
        raw = canonical(report) + b'\n'
        require(len(raw) <= 32768)
        (OUT / 'report.json').write_bytes(raw)
    print(json.dumps({'status': report['status'], 'cases': len(report['tests']), 'report_sha256': sha(raw)}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

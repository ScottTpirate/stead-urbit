#!/usr/bin/env python3
"""Run the pinned native Git candidate corpus in a fresh isolated fake ship.

Run after `python3 scripts/urbit/toolchain.py fetch`. No reset, deletion,
candidate override, live identity, frontend build, or production integration.
Every invocation leaves its marked synthetic evidence below ignored .runtime/.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import urllib.request

import toolchain

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / 'specs/urbit/urgit-candidate.lock.json'
HELPERS = Path(__file__).resolve().parent / 'urgit_eval'


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def no_links(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f'Refusing redirected path: {path}')


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def download(url, expected, destination, limit):
    # Authenticated HTTPS reads only. No gh credentials or source build scripts.
    with urllib.request.urlopen(url, timeout=60) as response, destination.open('xb') as out:
        size = 0
        while chunk := response.read(65536):
            size += len(chunk)
            if size > limit:
                raise ValueError('Pinned download exceeds evaluation bound')
            out.write(chunk)
    if digest(destination) != expected:
        raise ValueError('Pinned download checksum mismatch: ' + destination.name)


def unpack(archive_path, destination, pin):
    limits = pin['limits']
    seen, total, files, members = set(), 0, 0, 0
    with tarfile.open(archive_path) as archive:
        for item in archive:
            members += 1
            if members > limits['maximum_archive_files']:
                raise ValueError('Source archive member limit exceeded')
            raw_parts = item.name.split('/')
            parts = PurePosixPath(item.name).parts
            if (not parts or parts[0] != pin['candidate']['archive_root']
                    or item.name.startswith('/') or '..' in raw_parts
                    or '.' in raw_parts or not (item.isfile() or item.isdir())):
                raise ValueError('Unexpected source archive member')
            relative = Path(*parts[1:])
            if not parts[1:]:
                continue
            if relative in seen:
                raise ValueError('Duplicate source archive member')
            seen.add(relative)
            target = destination / relative
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            files += 1
            total += item.size
            if (files > limits['maximum_archive_files'] or item.size < 0
                    or item.size > limits['maximum_file_bytes']
                    or total > limits['maximum_source_bytes']):
                raise ValueError('Source expansion limit exceeded')
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(item) as source, target.open('xb') as out:
                shutil.copyfileobj(source, out)
    docket = (destination / 'desk/desk.docket-0').read_text()
    if "license+'MIT'" not in docket:
        raise ValueError('Pinned app MIT declaration absent')
    return {'regular_files': files, 'source_bytes': total}


def temperatures():
    readings = {}
    for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:
            readings[zone.name + ':' + (zone / 'type').read_text().strip()] = (
                int((zone / 'temp').read_text()) / 1000)
        except (ValueError, OSError):
            pass
    return readings


def execute():
    allowed = {'https://github.com/ScottTpirate/stead-urbit.git',
               'git@github.com:ScottTpirate/stead-urbit.git'}
    for options in ([], ['--push']):
        remote = subprocess.check_output(
            ['git', 'remote', 'get-url', *options, 'origin'], cwd=ROOT, text=True).strip()
        if remote not in allowed:
            raise ValueError('Origin is not the authorized independent derivative')
    data = toolchain.verify()
    runtime_bytes = toolchain.LOCK_PATH.read_bytes()
    if json.loads(runtime_bytes) != data:
        raise ValueError('Toolchain lock changed during verification')
    pin_bytes = PIN.read_bytes()
    pin = json.loads(pin_bytes)
    if (pin['format'] != 1 or pin['profile'] != 'isolated-native-git-candidate-evaluation-only'
            or pin['fake_identity'] != 'zod' or pin['limits']['cpu_count'] != 1
            or pin['candidate']['commit'] != data['urgit']['commit']):
        raise ValueError('Unsupported or contradictory candidate lock')
    for required in ('/usr/bin/bwrap', '/usr/bin/python3', '/usr/bin/git'):
        if not Path(required).is_file():
            raise ValueError('Required host tool missing: ' + required)
    if subprocess.run(['git', 'check-ignore', '-q', '.runtime/urgit-evaluations/probe'],
                      cwd=ROOT).returncode:
        raise ValueError('Evaluation directory is not ignored by Git')
    base = ROOT / '.runtime/urgit-evaluations'
    no_links(base)
    base.mkdir(mode=0o700, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=base))
    evidence = run / 'evidence'
    evidence.mkdir()
    write_json(run / '.stead-disposable.json', {
        'format': 1, 'purpose': 'URB-025 isolated candidate evaluation', 'fake_identity': 'zod'})
    (run / 'toolchain.lock.json').write_bytes(runtime_bytes)
    (run / 'candidate.lock.json').write_bytes(pin_bytes)
    print('Audit directory: ' + str(run), flush=True)
    # Copy only our Python helpers, never source from the candidate into Git.
    support = run / 'support'
    support.mkdir()
    for source in sorted(HELPERS.glob('*.py')):
        no_links(source)
        shutil.copyfile(source, support / source.name)
    helpers = {p.name: digest(p) for p in support.glob('*.py')}
    limits = pin['limits']
    candidate = pin['candidate']
    skeleton = pin['skeleton']
    download(candidate['url'], candidate['sha256'], run / 'candidate.tar.gz', limits['maximum_download_bytes'])
    source_info = unpack(run / 'candidate.tar.gz', run / 'candidate', pin)
    download(skeleton['url'], skeleton['sha256'], run / 'skeleton.hoon', limits['maximum_download_bytes'])
    download(skeleton['license_url'], skeleton['license_sha256'], run / 'skeleton-LICENSE.txt', limits['maximum_download_bytes'])
    cpu = max(os.sched_getaffinity(0))
    write_json(evidence / 'provenance.json', {
        'scope': pin['profile'], 'candidate': candidate, 'skeleton': skeleton,
        'candidate_lock_sha256': hashlib.sha256(pin_bytes).hexdigest(),
        'toolchain_lock_sha256': hashlib.sha256(runtime_bytes).hexdigest(),
        'helpers_sha256': helpers, 'runner_sha256': digest(Path(__file__)),
        'source': source_info, 'cpu_affinity': [cpu], 'loom_exponent': limits['loom_exponent'],
        'host_tools_sha256': {p: digest(Path(p)) for p in ('/usr/bin/git', '/usr/bin/bwrap', '/usr/bin/python3')},
        'uname': list(os.uname()), 'initial_temperatures_c': temperatures(),
        'excluded_claims': pin['excluded_claims']})
    args = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
            '--symlink', 'usr/lib64', '/lib64', '--symlink', 'usr/bin', '/bin',
            '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/home/audit',
            '--setenv', 'HOME', '/home/audit', '--setenv', 'PATH', '/usr/bin',
            '--setenv', 'LANG', 'C.UTF-8', '--bind', str(run), '/work',
            '--ro-bind', str(support), '/code',
            '--ro-bind', str(toolchain.CACHE / data['runtime']['binary']), '/runtime/vere',
            '--ro-bind', str(toolchain.CACHE / 'downloads' / data['boot_artifact']['archive']), '/runtime/pill',
            '--ro-bind', str(toolchain.CACHE / data['kernel']['directory']), '/kernel',
            '--chdir', '/work', '/usr/bin/python3', '-I', '/code/evaluate.py']
    write_json(evidence / 'sandbox-command.json', {'argv': args, 'cpu_affinity': [cpu]})
    cancelled = False
    previous_handlers = {}

    def request_stop(signum, _frame):
        nonlocal cancelled
        cancelled = True
        (run / 'STOP').touch(exist_ok=True)

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[sig] = signal.signal(sig, request_stop)
    process = None
    stop_reason, stop_at = None, None
    started = time.monotonic()
    try:
        with (evidence / 'console.log').open('wb') as console, (evidence / 'thermal.jsonl').open('w') as thermal:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=console, stderr=subprocess.STDOUT,
                                       preexec_fn=lambda: os.sched_setaffinity(0, {cpu}))
            while process.poll() is None:
                readings = temperatures()
                elapsed = round(time.monotonic() - started, 1)
                thermal.write(json.dumps({'elapsed_seconds': elapsed, 'temperatures_c': readings}) + '\n')
                thermal.flush()
                if cancelled:
                    stop_reason = stop_reason or 'operator interrupt'
                elif elapsed > limits['total_timeout_seconds']:
                    stop_reason = stop_reason or 'overall evaluation timeout'
                elif readings and max(readings.values()) >= limits['stop_temperature_c']:
                    stop_reason = stop_reason or 'thermal ceiling reached'
                if stop_reason:
                    (run / 'STOP').touch(exist_ok=True)
                    stop_at = stop_at or time.monotonic()
                    if time.monotonic() - stop_at > 90:
                        process.terminate()
                        break
                if int(elapsed) % 30 < 5:
                    status_path = evidence / 'status.json'
                    try:
                        phase = json.loads(status_path.read_text())['phase']
                    except (OSError, json.JSONDecodeError):
                        phase = 'starting isolated evaluator'
                    print(f'{phase}; elapsed {elapsed:.0f}s; max temperature {max(readings.values(), default=0):.1f} C', flush=True)
                time.sleep(5)
            process.wait(timeout=15)
    finally:
        if process is not None and process.poll() is None:
            (run / 'STOP').touch(exist_ok=True)
            try:
                process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
    report_path = evidence / 'report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {'status': 'failed', 'reason': 'evaluator produced no report'}
    if stop_reason:
        report.update(status='failed', host_stop_reason=stop_reason)
    report['sandbox_exit_code'] = process.returncode
    write_json(report_path, report)
    write_json(evidence / 'SHA256SUMS.json', {p.name: digest(p) for p in sorted(evidence.iterdir())
                                             if p.is_file() and p.name != 'SHA256SUMS.json'})
    print(json.dumps({'audit_directory': str(run), 'status': report['status'],
                      'checks_passed': sum(x['passed'] for x in report.get('checks', [])),
                      'sandbox_exit_code': process.returncode}, indent=2))
    return 0 if report['status'] == 'passed' and process.returncode == 0 else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        raise SystemExit(execute())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'FAIL: {error}\n')

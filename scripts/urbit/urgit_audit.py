#!/usr/bin/env python3
"""Run the pinned native Git candidate corpus in a fresh isolated fake ship.

Run after `python3 scripts/urbit/toolchain.py fetch`. No reset, deletion,
candidate override, live identity, frontend build, or production integration.
Every invocation leaves its marked synthetic evidence below ignored .runtime/.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import secrets
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.request

import toolchain
import execution_policy

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / 'specs/urbit/urgit-candidate.lock.json'
HELPERS = Path(__file__).resolve().parent / 'urgit_eval'
OUTPUT_LIMITS = {
    'commands.jsonl': 8 * 1024 * 1024,
    'native.log': 64 * 1024 * 1024,
    'native-vectors.json': 1024 * 1024,
    'report.json': 1024 * 1024,
    'status.json': 4096,
}


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def no_links(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f'Refusing redirected path: {path}')


@contextmanager
def directory_fd(path):
    """Anchor each existing directory component without following links."""
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal in directory path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open('/', flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def write_bytes(path, payload):
    """Atomically replace one host-owned output; never follow a final link."""
    path = Path(path)
    with directory_fd(path.parent) as parent:
        temporary = '.' + path.name + '.' + secrets.token_hex(12) + '.tmp'
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        try:
            with os.fdopen(descriptor, 'wb') as destination:
                destination.write(payload)
            os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


def write_json(path, value):
    write_bytes(path, (json.dumps(value, indent=2) + '\n').encode())


def read_regular_at(parent, name, maximum_bytes):
    """Read a bounded untrusted output through a pre-opened directory handle.

    NOFOLLOW rejects symbolic links; NONBLOCK avoids hanging on a FIFO before
    fstat rejects non-regular files. Never enumerate and follow child paths.
    """
    if not name or name in ('.', '..') or '/' in name or maximum_bytes < 0:
        raise ValueError('Invalid bounded output request')
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                         | os.O_CLOEXEC, dir_fd=parent)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Output must be a singly linked regular file')
        if info.st_size > maximum_bytes:
            raise ValueError('Output exceeds byte limit')
        payload = bytearray()
        while len(payload) <= maximum_bytes:
            chunk = os.read(descriptor, min(65536, maximum_bytes + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > maximum_bytes:
            raise ValueError('Output exceeds byte limit')
        return bytes(payload)
    finally:
        os.close(descriptor)


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
    sample = execution_policy.sample_temperatures()
    execution_policy.validate_sample(sample, execution_policy.Policy())
    return sample.readings_c


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
    initial_sample = execution_policy.sample_temperatures()
    execution_policy.validate_sample(initial_sample, execution_policy.policy_from_limits(pin['limits']), preflight=True)
    initial_readings = initial_sample.readings_c
    base = ROOT / '.runtime/urgit-evaluations'
    no_links(base)
    base.mkdir(mode=0o700, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=base))
    evidence = run / 'evidence'
    evidence.mkdir()
    # The candidate can write only work/ and output/. Never expose the run's
    # parent, host evidence, or a second writable alias of read-only inputs.
    inputs, work, output, control = (run / name for name in ('input', 'work', 'output', 'control'))
    for path in (inputs, work, output, control):
        path.mkdir(mode=0o700)
    marker = {'format': 1, 'purpose': 'URB-025 isolated candidate evaluation', 'fake_identity': 'zod'}
    write_json(run / '.stead-disposable.json', marker)
    write_json(inputs / '.stead-disposable.json', marker)
    (inputs / 'toolchain.lock.json').write_bytes(runtime_bytes)
    (inputs / 'candidate.lock.json').write_bytes(pin_bytes)
    print('Audit directory: ' + str(run), flush=True)
    # Copy only our Python helpers, never source from the candidate into Git.
    support = inputs / 'support'
    support.mkdir()
    for source in sorted(HELPERS.glob('*.py')):
        no_links(source)
        shutil.copyfile(source, support / source.name)
    helpers = {p.name: digest(p) for p in support.glob('*.py')}
    limits = pin['limits']
    candidate = pin['candidate']
    skeleton = pin['skeleton']
    download(candidate['url'], candidate['sha256'], inputs / 'candidate.tar.gz', limits['maximum_download_bytes'])
    source_info = unpack(inputs / 'candidate.tar.gz', inputs / 'candidate', pin)
    download(skeleton['url'], skeleton['sha256'], inputs / 'skeleton.hoon', limits['maximum_download_bytes'])
    download(skeleton['license_url'], skeleton['license_sha256'], inputs / 'skeleton-LICENSE.txt', limits['maximum_download_bytes'])
    cpu = max(os.sched_getaffinity(0))
    write_json(evidence / 'provenance.json', {
        'scope': pin['profile'], 'candidate': candidate, 'skeleton': skeleton,
        'candidate_lock_sha256': hashlib.sha256(pin_bytes).hexdigest(),
        'toolchain_lock_sha256': hashlib.sha256(runtime_bytes).hexdigest(),
        'helpers_sha256': helpers, 'runner_sha256': digest(Path(__file__)),
        'source': source_info, 'cpu_affinity': [cpu], 'loom_exponent': limits['loom_exponent'],
        'host_tools_sha256': {p: digest(Path(p)) for p in ('/usr/bin/git', '/usr/bin/bwrap', '/usr/bin/python3')},
        'uname': list(os.uname()), 'initial_temperatures_c': initial_readings,
        'thermal_limits_c': {'start': limits['start_temperature_c'], 'stop': limits['stop_temperature_c']},
        'evidence_boundary': 'host evidence never mounted; fixed-name bounded no-follow output import',
        'excluded_claims': pin['excluded_claims']})
    args = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
            '--symlink', 'usr/lib64', '/lib64', '--symlink', 'usr/bin', '/bin',
            '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/home/audit',
            '--setenv', 'HOME', '/home/audit', '--setenv', 'PATH', '/usr/bin',
            '--setenv', 'LANG', 'C.UTF-8', '--bind', str(work), '/work',
            '--bind', str(output), '/output', '--ro-bind', str(inputs), '/input',
            '--ro-bind', str(control), '/control',
            '--ro-bind', str(support), '/code',
            '--ro-bind', str(toolchain.CACHE / data['runtime']['binary']), '/runtime/vere',
            '--ro-bind', str(toolchain.CACHE / 'downloads' / data['boot_artifact']['archive']), '/runtime/pill',
            '--ro-bind', str(toolchain.CACHE / data['kernel']['directory']), '/kernel',
            '--chdir', '/work', '/usr/bin/python3', '-I', '/code/evaluate.py']
    write_json(evidence / 'sandbox-command.json', {'argv': args, 'cpu_affinity': [cpu]})
    # Keep this handle open from before candidate execution until all outputs
    # have been copied. Parent renames cannot redirect a later host read.
    with directory_fd(output) as output_handle:
        return run_sandbox(run, evidence, control, output_handle, args, cpu, limits)


def run_sandbox(run, evidence, control, output_handle, args, cpu, limits):
    def command(guard_control, _run_id):
        result = list(args)
        # The evaluator sees only this host-controlled read-only STOP directory,
        # never the common lock, evidence parent or another writable alias.
        index = result.index(str(control))
        if result[index - 1] != '--ro-bind' or result[index + 1] != '/control':
            raise ValueError('Candidate control mount is not the reviewed read-only boundary')
        result[index] = str(guard_control)
        return result
    with (evidence / 'console.log').open('wb') as console:
        guarded = execution_policy.run_guarded(command, root=ROOT, label='urgit',
                    policy=execution_policy.policy_from_limits(limits),
                    timeout=limits['total_timeout_seconds'], console=console)
    write_json(evidence / 'execution-guard.json', guarded)
    with (evidence / 'thermal.jsonl').open('w') as thermal:
        for item in guarded['events']:
            if 'sample' in item:
                thermal.write(json.dumps({'elapsed_seconds': item['elapsed_seconds'],
                    'temperatures_c': item['sample']['readings_c']}) + '\n')
    stop_reason = guarded['reason'] if guarded['status'] != 'completed' else None
    imported, failures = {}, []
    for name, limit in OUTPUT_LIMITS.items():
        try:
            imported[name] = read_regular_at(output_handle, name, limit)
            write_bytes(evidence / name, imported[name])
        except (ValueError, OSError) as error:
            failures.append({'file': name, 'error': type(error).__name__})
    try:
        report = json.loads(imported.get('report.json', b'null'))
        if (not isinstance(report, dict) or report.get('status') not in ('passed', 'failed')
                or not isinstance(report.get('checks'), list) or len(report['checks']) > 32
                or any(not isinstance(row, dict) or type(row.get('passed')) is not bool
                       for row in report['checks'])):
            raise ValueError('Invalid evaluator report shape')
    except (ValueError, TypeError):
        report = {'status': 'failed', 'reason': 'evaluator produced no valid report', 'checks': []}
    if failures:
        report.update(status='failed', output_import_failures=failures)
    if stop_reason:
        report.update(status='failed', host_stop_reason=stop_reason)
    report['sandbox_exit_code'] = guarded['exit_code']
    if guarded['exit_code'] != 0:
        report.update(status='failed', reason='sandbox exited unsuccessfully')
    write_json(evidence / 'report.json', report)
    # Only host-created evidence exists here; no sandbox-controlled directory
    # walk or Path.is_file()/digest() pair can follow an injected link.
    names = sorted(set(imported) | {'report.json', 'provenance.json', 'sandbox-command.json',
                                   'console.log', 'thermal.jsonl', 'execution-guard.json'})
    with directory_fd(evidence) as evidence_handle:
        hashes = {name: hashlib.sha256(read_regular_at(evidence_handle, name, 64 * 1024 * 1024)).hexdigest()
                  for name in names}
    write_json(evidence / 'SHA256SUMS.json', hashes)
    print(json.dumps({'audit_directory': str(run), 'status': report['status'],
                      'checks_passed': sum(x['passed'] for x in report.get('checks', [])),
                      'sandbox_exit_code': guarded['exit_code']}, indent=2))
    return 0 if report['status'] == 'passed' and guarded['exit_code'] == 0 and guarded['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        raise SystemExit(execute())
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'FAIL: {error}\n')

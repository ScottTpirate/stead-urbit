"""Trusted failure controls; all fixture writes stay inside the disposable job."""
from __future__ import annotations

import errno
import hashlib
import os
from pathlib import Path
import re
import time

from digests import sha, tree_sha


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compiler_diagnostic(diagnostic):
    """Exact pinned -test undefined-name failure, not an incidental log word."""
    if not isinstance(diagnostic, str) or not 0 < len(diagnostic.encode('utf-8')) <= 262144:
        return False
    lines = diagnostic.replace('\r\n', '\n').splitlines()
    return ('-find.stead-ci-deliberately-undefined' in lines
            and 'FAILED  /controls/stead-ci-compiler/hoon (build)' in lines)


def runtime_pin(path, expected):
    require(not path.is_symlink() and path.is_file() and sha(path) == expected,
            'Missing or changed runtime pin')


def readonly_cache(runtime):
    # DAC can refuse the write-open before Linux checks the mount flags. Both
    # observations are necessary: EACCES alone also occurs on writable mounts.
    require(os.statvfs(runtime).f_flag & os.ST_RDONLY, 'Cache mount is writable')
    try:
        with runtime.open('r+b'):
            raise ValueError('Shared runtime cache is writable')
    except OSError as error:
        require(error.errno in (errno.EROFS, errno.EACCES), 'Unexpected cache write refusal')
        return {'cache_mount_read_only': True, 'cache_write_errno': error.errno}


def seed_and_cache(host, pins):
    host.execution_check()
    require(all(child.poll() is not None for child in host.PROCESSES.values()), 'Seed control needs stopped ships')
    before = tree_sha(host.SEED / 'zod')
    poison = host.SEED / 'zod/stead-ci-poison'
    with poison.open('xb') as stream:
        stream.write(b'owned CI seed poison control\n')
    try:
        poisoned = tree_sha(host.SEED / 'zod')
        require(poisoned != before, 'Seed poison did not change identity')
        try:
            host.copy_seed_to_live()
        except ValueError as error:
            require(str(error) == 'Seed integrity failure: zod', 'Unexpected seed refusal')
            refusal = str(error)
        else:
            raise ValueError('Poisoned seed was accepted')
    finally:
        poison.unlink()
    require(tree_sha(host.SEED / 'zod') == before, 'Seed restoration differs')
    runtime = Path('/runtime') / pins['runtime']['binary']
    expected = pins['runtime']['binary_sha256']
    runtime_pin(runtime, expected)
    cache = readonly_cache(runtime)
    # A truncated owned copy exercises the same pin verifier without modifying
    # the shared runtime artifact or executing the poisoned bytes.
    scratch = Path('/state/ci-poisoned-cache')
    with runtime.open('rb') as source, scratch.open('xb') as target:
        target.write(source.read(65536))
    truncated = sha(scratch)
    try:
        try:
            runtime_pin(scratch, expected)
        except ValueError as error:
            require(str(error) == 'Missing or changed runtime pin', 'Unexpected cache refusal')
        else:
            raise ValueError('Truncated runtime cache accepted')
    finally:
        scratch.unlink()
    return {'classification': 'real-disposable-filesystem-controls',
        'seed_before': before, 'seed_poisoned': poisoned, 'seed_after': tree_sha(host.SEED / 'zod'),
        'seed_refusal': refusal, 'runtime_expected': expected, 'runtime_after': sha(runtime),
        'owned_truncated_sha256': truncated, **cache, 'cache_pin_refused': True}


def native(host, report, *, progress=None):
    import core_conn
    import native_units
    from conn import framed_length
    from gall_schedule_proof import _cue, _atom, _jam
    binary = '/runtime/' + host.LOCK['runtime']['binary']
    socket = host.LIVE / 'zod/.urb/conn.sock'
    log = Path('/state/logs/zod.log')
    def checkpoint(stage, observation):
        if progress is not None:
            progress(stage, observation)

    def unit(path):
        host.execution_check()
        resolved = host.dojo('zod', '`path`%' + path).strip()
        offset = log.stat().st_size
        try:
            observed = native_units.run(binary, socket, resolved)
            result = {'native_test': observed}
        except ValueError as error:
            result = {'error': str(error), 'native_failure': getattr(error, 'native_failure', {})}
        with log.open('rb') as stream:
            stream.seek(offset)
            captured = stream.read(262145)
        require(len(captured) <= 262144, 'Negative native output bound')
        return result | {'path': path, 'log_hex': captured.hex()}

    missing = unit('/controls/stead-ci-missing')
    checkpoint('missing-arm', missing)
    require('native_test' in missing, 'Missing arm fixture failed before discovery')
    terminal = missing['native_test']['stdout']
    raw = bytes.fromhex(missing['log_hex']).decode('utf-8') + '\n' + terminal
    native_units.verify_output(raw, path=missing['path'], expected=['test-ci-renamed'], succeeds=True)
    try:
        native_units.verify_output(raw, path=missing['path'], expected=['test-ci-required'], succeeds=True)
    except ValueError as error:
        require(str(error) == 'Native discovered/executed arm mismatch', 'Unexpected missing arm refusal')
        missing['refusal'] = str(error)
    else:
        raise ValueError('Missing native arm accepted')
    compiler = unit('/controls/stead-ci-compiler')
    checkpoint('compiler', compiler)
    diagnostics = bytes.fromhex(compiler['log_hex']).decode('utf-8')
    require(compiler_diagnostic(diagnostics), 'Specific compiler failure absent')
    require(compiler.get('native_test', {}).get('stdout') == '[32 %avow 0 %noun 1]'
            or compiler.get('native_failure', {}).get('stage') == 'parse-terminal', 'Compiler control failed outside native compilation')
    request = '[32 %fyrd [%base %stead-ci-delay %noun [%noun ~]]]'
    positive = core_conn.exchange(binary, socket, request, timeout=60)
    checkpoint('timer-positive', positive)
    require(positive['outcome']['json'] == {}, 'Finite timer positive control failed')
    started = time.monotonic()
    try:
        core_conn.exchange(binary, socket, request, timeout=.05)
    except TimeoutError as error:
        trace = getattr(error, 'native_failure', {})
        checkpoint('timer-timeout', trace)
        require(trace.get('stage') == 'response-header' and trace.get('received_frame_hex') == '', 'Timeout occurred before the native request')
        timeout = {'deadline_seconds': .05, 'elapsed_seconds': round(time.monotonic() - started, 3), 'native_failure': trace}
    else:
        raise ValueError('Native timer ignored client timeout')
    # The timed-out request is finite. A subsequent successful timer proves the
    # ship remains responsive; whole-job cleanup still reaps every child.
    recovered = core_conn.exchange(binary, socket, request, timeout=60)
    checkpoint('timer-recovered', recovered)
    require(recovered['outcome']['json'] == {}, 'Runtime did not recover after client timeout')
    positive_unit = (missing['native_test'] if report is None else
        next(row['native_test'] for row in report['commands'] if 'native_test' in row))
    frame = bytes.fromhex(positive_unit['response_frame_hex'])
    checkpoint('frame-original', {'hex':frame.hex()})
    expected = (32, (_atom('avow'), (0, (_atom('noun'), 0))))
    require(len(frame) == 5 + framed_length(frame[:5]) and _cue(frame[5:]) == expected, 'Original native frame invalid')
    wrong = _jam((32, (_atom('avow'), (0, (_atom('noun'), 1)))))
    injected = {'truncated': frame[:-1], 'corrupt_verdict': b'\0' + len(wrong).to_bytes(4, 'little') + wrong}
    refused = {}
    for name, altered in injected.items():
        try:
            require(len(altered) == 5 + framed_length(altered[:5]) and _cue(altered[5:]) == expected, 'Native frame/verdict mismatch')
        except ValueError as error:
            refused[name] = {'injected_hex': altered.hex(), 'refusal': str(error)}
        else:
            raise ValueError('Injected malformed native frame accepted')
    checkpoint('frame-injections', refused)
    return {'classification': 'real-native-controls-and-labeled-frame-fault-injection',
        'missing_arm': missing, 'compiler_failure': compiler,
        'timer_positive': positive, 'timer_timeout': timeout, 'timer_recovered': recovered,
        'frame_fault_injection': {'original_sha256': hashlib.sha256(frame).hexdigest(), 'controls': refused}}

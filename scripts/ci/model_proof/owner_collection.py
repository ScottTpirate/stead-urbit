"""Fixed root collector used only inside a separately admitted model service.

The caller supplies the existing authenticated guardian heartbeat. This helper
does not authenticate a workflow, download an artifact, or grant admission from
a worker's claims. The parent must also verify this service's final empty cgroup.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import select
import selectors
import signal
import stat
import subprocess
import time

import owner_boundary as boundary

TOTAL_SECONDS = 575
READY_SECONDS = 90
STDOUT_LIMIT = 65536
STDERR_LIMIT = 16384
FINAL_KEYS = {'protocol', 'status', 'error_class', 'phase', 'native_executed',
              'qualifies_g3', 'model_launches', 'client_launches', 'children_reaped',
              'outer_cleanup_required', 'artifacts', 'children', 'namespace_baseline_restored',
              'client_report_sha256', 'cleanup_error_class', 'elapsed_ms', 'admission'}
ARTIFACT_LIMITS = {'request.json': 8192, 'response.bin': 32768,
                   'proposal.json': 65536, 'report.json': 16384}


def require(ok):
    boundary.require(ok)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def parse(raw, maximum):
    require(type(raw) is bytes and 0 < len(raw) <= maximum)
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    require(canonical(value) == raw)
    return value


def service_properties(cpu):
    require(type(cpu) is int and 0 <= cpu < 1024)
    return {'CPUQuota': '100%', 'CPUQuotaPeriodSec': '100ms', 'CPUAffinity': str(cpu),
            'AllowedCPUs': str(cpu), 'MemoryMax': '2147483648', 'MemorySwapMax': '0',
            'TasksMax': '128', 'RuntimeMaxSec': '600', 'TimeoutStopSec': '15',
            'KillMode': 'control-group', 'ExitType': 'main', 'RemainAfterExit': 'no',
            'Restart': 'no', 'OOMPolicy': 'kill', 'AppArmorProfile': boundary.APPARMOR}


def service_current(value):
    boundary.group(value)
    keys = ('LoadState', 'ActiveState', 'ControlGroup', 'MainPID', 'KillMode', 'ExitType',
            'RemainAfterExit', 'Restart', 'OOMPolicy', 'RuntimeMaxUSec', 'TimeoutStopUSec',
            'AppArmorProfile')
    result = subprocess.run(['/usr/bin/systemctl', 'show', value['unit'],
        '--property=' + ','.join(keys)], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=5, env={'PATH': '/usr/bin:/bin', 'LANG': 'C'})
    require(len(result.stdout) <= 4096)
    rows = result.stdout.decode('ascii').splitlines()
    observed = dict(row.split('=', 1) for row in rows)
    expected = {'LoadState': 'loaded', 'ActiveState': 'active',
                'ControlGroup': '/system.slice/' + value['unit'], 'MainPID': str(os.getpid()),
                'KillMode': 'control-group', 'ExitType': 'main', 'RemainAfterExit': 'no',
                'Restart': 'no', 'OOMPolicy': 'kill', 'RuntimeMaxUSec': '10min',
                'TimeoutStopUSec': '15s', 'AppArmorProfile': boundary.APPARMOR}
    require(len(rows) == len(keys) and observed == expected)


def worker_result(value, owner, anchor, context):
    require(type(value) is dict and set(value) == FINAL_KEYS
            and value['protocol'] == 'stead.fixed-model-worker-result/1'
            and value['status'] == 'pass' and value['error_class'] == 'none'
            and value['cleanup_error_class'] == 'none' and value['phase'] == 'complete'
            and value['native_executed'] is False and value['qualifies_g3'] is False
            and value['outer_cleanup_required'] is True
            and value['children_reaped'] is True and value['namespace_baseline_restored'] is True
            and type(value['model_launches']) is int and value['model_launches'] == 1
            and type(value['client_launches']) is int and value['client_launches'] == 1
            and type(value['elapsed_ms']) is int and 0 <= value['elapsed_ms'] <= 555000)
    expected_admission = {'uid': 1000, 'gid': 1000, 'host_uid': context['host_uid'],
        'host_gid': context['host_gid'], 'source_uid': 65534,
        'namespace_maps': {'uid': [1000, 0, 1], 'gid': [1000, 0, 1]},
        'namespaces': anchor['namespaces'], 'capabilities_empty': True,
        'no_new_privileges': True, 'private_loopback_only': True,
        'owner_sha256': hashlib.sha256(canonical(owner)).hexdigest(),
        'runtime_tree_sha256': owner['runtime']['tree_sha256'],
        'model_sha256': boundary.MODEL_SHA, 'sources': context['sources'], 'guardian_lease_required': True}
    # Canonical equality avoids bool/int equality coercion in nested evidence.
    require(canonical(value['admission']) == canonical(expected_admission))
    require(type(value['artifacts']) is dict and set(value['artifacts']) == set(ARTIFACT_LIMITS)
            and value['client_report_sha256'] == value['artifacts']['report.json']['sha256'])
    require(type(value['children']) is dict and set(value['children']) == {'server', 'client'})
    for name, row in value['children'].items():
        require(type(row) is dict and set(row) == {'exit_code', 'stdout', 'stderr'}
                and type(row['exit_code']) is int)
        require(row['exit_code'] == 0 if name == 'client' else row['exit_code'] in (0, -15, -9))
        for stream in ('stdout', 'stderr'):
            log = row[stream]
            require(type(log) is dict and set(log) == {'bytes', 'sha256', 'eof', 'overflow'}
                    and type(log['bytes']) is int and 0 <= log['bytes'] <= 65536
                    and type(log['sha256']) is str and len(log['sha256']) == 64
                    and all(c in '0123456789abcdef' for c in log['sha256'])
                    and log['eof'] is True and log['overflow'] is False)


def cleanup(process, value):
    """Only the exact private unit; the guardian itself is the sole survivor."""
    path = boundary.group(value)
    expected = '/system.slice/' + value['unit']
    for text in (path / 'cgroup.procs').read_text().splitlines():
        pid = int(text)
        if pid == os.getpid():
            continue
        fd = None
        try:
            fd = os.pidfd_open(pid, 0)
            try:
                membership = Path('/proc', text, 'cgroup').read_text().splitlines()
            except FileNotFoundError:
                # A vanished proc entry is benign only for this already-dead
                # pinned process; never ignore a live or wrong-cgroup process.
                require(bool(select.select([fd], [], [], 0)[0]))
                continue
            require(membership == ['0::' + expected])
            signal.pidfd_send_signal(fd, signal.SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            if fd is not None:
                os.close(fd)
    process.wait(timeout=8)
    end = time.monotonic() + 5
    while time.monotonic() < end:
        if set((path / 'cgroup.procs').read_text().splitlines()) == {str(os.getpid())}:
            return True
        time.sleep(0.05)
    return False


def run(process, job, value, owner, heartbeat):
    """Collect a fixed launcher already started by the admitted root guardian.

    Caller must close its child-side descriptors immediately after Popen. The
    worker receives only stdin/stdout/stderr and awaits exact go plus EOF.
    """
    started = time.monotonic()
    service_current(value)
    heartbeat()
    require(process.stdin is not None and process.stdout is not None and process.stderr is not None)
    child_pidfd = os.pidfd_open(process.pid, 0)
    selector = selectors.DefaultSelector()
    raw, eof = {'stdout': bytearray(), 'stderr': bytearray()}, {'stdout': False, 'stderr': False}
    anchor, final, admitted, cleaned = None, None, False, False
    result = {'protocol': 'stead.fixed-model-owner-result/1', 'status': 'fail',
              'stage': 'ready', 'error_class': 'none', 'cleanup_error_class': 'none', 'parent_admitted': False,
              'worker_result': None, 'artifact_pins': {}, 'child_streams_eof': False,
              'owned_children_empty': False, 'native_executed': False, 'qualifies_g3': False}
    artifact_bytes = {}
    pending = bytearray()
    frames = 0
    worker_exited_at = None
    try:
        for name, stream in (('stdout', process.stdout), ('stderr', process.stderr)):
            require(stat.S_ISFIFO(os.fstat(stream.fileno()).st_mode))
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while True:
            heartbeat()
            boundary.group(value)
            require(time.monotonic() - started < TOTAL_SECONDS)
            if not admitted:
                require(time.monotonic() - started < READY_SECONDS)
            for event, _ in selector.select(0.2):
                name = event.data
                part = os.read(event.fileobj.fileno(), 8192)
                if not part:
                    eof[name] = True
                    selector.unregister(event.fileobj)
                    event.fileobj.close()
                    continue
                raw[name].extend(part)
                require(len(raw[name]) <= (STDOUT_LIMIT if name == 'stdout' else STDERR_LIMIT))
                if name != 'stdout':
                    continue
                pending.extend(part)
                while b'\n' in pending:
                    line, _, rest = pending.partition(b'\n')
                    pending = bytearray(rest)
                    frames += 1
                    require(frames <= 2)
                    message = parse(bytes(line), 4096 if frames == 1 else 32768)
                    if frames == 1:
                        anchor = boundary.pin_ready(job, value, message,
                            hashlib.sha256(canonical(owner)).hexdigest(), heartbeat)
                        boundary.current(anchor, value, heartbeat)
                        result['root_loopback_observation'] = boundary.loopback_observation(anchor, value, heartbeat)
                        service_current(value)
                        boundary.current(anchor, value, heartbeat)
                        require(process.poll() is None and not select.select([child_pidfd], [], [], 0)[0])
                        process.stdin.write(b'go\n')
                        process.stdin.flush()
                        process.stdin.close()
                        admitted = result['parent_admitted'] = True
                        result['stage'] = 'worker'
                    else:
                        require(admitted and final is None)
                        worker_result(message, owner, anchor, value)
                        final = message
            if anchor is not None and final is None:
                # The worker can exit just before its final pipe bytes arrive.
                # Once its pidfd signals, allow only a short bounded EOF drain;
                # no further admission or commands are possible in this state.
                if select.select([anchor['pidfd']], [], [], 0)[0]:
                    if worker_exited_at is None:
                        worker_exited_at = time.monotonic()
                    require(time.monotonic() - worker_exited_at < 3)
                else:
                    boundary.current(anchor, value, heartbeat)
            if process.poll() is not None and all(eof.values()):
                break
        require(admitted and frames == 2 and not pending and final is not None and process.returncode == 0)
        result['child_streams_eof'] = True
        result['stage'] = 'cleanup'
    except BaseException as error:
        name = type(error).__name__
        result['error_class'] = name if name in {'ValueError', 'TypeError', 'TimeoutError', 'OSError',
            'PermissionError', 'FileNotFoundError', 'ProcessLookupError', 'BrokenPipeError',
            'JSONDecodeError', 'UnicodeDecodeError', 'CalledProcessError', 'TimeoutExpired'} else 'unrecognized'
        trace = error.__traceback__
        locations = []
        allowed_sources = {str(Path(__file__).resolve()): 'collection',
                           str(Path(boundary.__file__).resolve()): 'boundary'}
        while trace is not None:
            source = allowed_sources.get(trace.tb_frame.f_code.co_filename)
            if source is not None and 0 < trace.tb_lineno <= 10000:
                locations.append({'source': source, 'line': trace.tb_lineno})
            trace = trace.tb_next
        result['failure_location'] = locations[-1] if locations else None
    finally:
        def cleanup_error(code):
            # Preserve the initiating failure and the first cleanup failure.
            if result['cleanup_error_class'] == 'none':
                result['cleanup_error_class'] = code

        try:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
        except BaseException:
            cleanup_error('stdin-close-refusal')
        try:
            cleaned = cleanup(process, value)
            result['owned_children_empty'] = cleaned
            if not cleaned:
                cleanup_error('owned-cleanup-refusal')
        except BaseException:
            cleanup_error('owned-cleanup-refusal')
        if (cleaned and final is not None and result['error_class'] == 'none'
                and result['cleanup_error_class'] == 'none' and all(eof.values())):
            try:
                heartbeat()
                for name, pin in final['artifacts'].items():
                    artifact_bytes[name] = boundary.read_output(anchor, value, name, pin)
            except BaseException:
                artifact_bytes.clear()
                cleanup_error('artifact-refusal')
        # Every close is attempted even when a previous close failed. None of
        # these failures can overwrite the original cause or produce a pass.
        for event in list(selector.get_map().values()):
            try:
                event.fileobj.close()
            except BaseException:
                cleanup_error('descriptor-close-refusal')
        for close in (selector.close, lambda: os.close(child_pidfd)):
            try:
                close()
            except BaseException:
                cleanup_error('descriptor-close-refusal')
        if anchor is not None:
            try:
                boundary.close_anchor(anchor)
            except BaseException:
                cleanup_error('descriptor-close-refusal')
        if (cleaned and final is not None and result['error_class'] == 'none'
                and result['cleanup_error_class'] == 'none' and all(eof.values())
                and set(artifact_bytes) == set(ARTIFACT_LIMITS)):
            result.update(status='pass', stage='complete', worker_result=final,
                          artifact_pins=final['artifacts'])
        result['elapsed_ms'] = int((time.monotonic() - started) * 1000)
        result['streams'] = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                   'eof': eof[name]} for name, data in raw.items()}
    require(len(canonical(result)) <= 65536)
    return result, artifact_bytes

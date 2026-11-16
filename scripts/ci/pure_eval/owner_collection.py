"""Private fixed pure evaluator guardian collector; actual final unit cleanup remains outer-owned."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import select
import selectors
import signal
import subprocess
import time
import owner_boundary as boundary
TOTAL_SECONDS = 575
READY_SECONDS = 90
STDOUT_LIMIT = 32768
STDERR_LIMIT = 16384
REPORT_LIMIT = 4194304
WORKER_REPORT_LIMIT = 4063232
FINAL_KEYS = {'protocol','status','phase','error_class','cleanup_error_class','report','admission','outer_cleanup_required','children_reaped','namespace_baseline_restored','jobs_retained','elapsed_ms','qualifies_phase','native_application_executed'}
ERRORS = {'none','unrecognized','ValueError','TypeError','TimeoutError','OSError','PermissionError','FileNotFoundError','FileExistsError','ProcessLookupError','ChildProcessError','UnicodeDecodeError','JSONDecodeError'}
PHASES = {'admission','parent-admission','evaluations','source-after','complete'}

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


def validate_report(raw, codec, jobs, expected_hashes):
    report = parse(raw, WORKER_REPORT_LIMIT)
    require(type(report) is dict and set(report) == {'protocol','status','qualifies_phase',
            'composition_sha256','runtime_sha256','records','source_hashes_before','source_hashes_after',
            'budget_stop','error_class','children_reaped','namespace_baseline_restored',
            'expected_positive_arms','expected_controls','native_application_executed'})
    require(report['protocol'] == 'stead.fixed-pure-eval-report/1'
            and report['status'] in ('pass','fail') and report['qualifies_phase'] is False
            and report['native_application_executed'] is False
            and report['composition_sha256'] == '3d42cb1788ddbe5bdf6f9643bbbe4d2bfa7245a24431b851ef247c525c9ead72'
            and report['runtime_sha256'] == 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833'
            and type(report['expected_positive_arms']) is int and report['expected_positive_arms'] == 26
            and type(report['expected_controls']) is int and report['expected_controls'] == 2
            and report['error_class'] in ERRORS
            and report['children_reaped'] is True and report['namespace_baseline_restored'] is True
            and report['source_hashes_before'] == expected_hashes
            and report['source_hashes_after'] in ({}, expected_hashes)
            and type(report['records']) is list and len(report['records']) <= 6)
    observations = []
    for index, record in enumerate(report['records']):
        job = jobs[index]
        require(type(record) is dict and set(record) == {'label','source_sha256','source_bytes','exit_code','stdout','stderr','observation'}
                and record['label'] == job['label'] and record['source_sha256'] == job['source_sha256']
                and type(record['source_bytes']) is int and record['source_bytes'] == len(job['source'])
                and type(record['exit_code']) is int and -128 <= record['exit_code'] <= 255)
        values = []
        for name in ('stdout','stderr'):
            row = record[name]
            require(type(row) is dict and set(row) == {'present','bytes','sha256','base64'}
                    and row['present'] is True and type(row['bytes']) is int and 0 <= row['bytes'] <= 1000000
                    and type(row['base64']) is str and len(row['base64']) <= 1333336
                    and type(row['sha256']) is str and len(row['sha256']) == 64)
            data = base64.b64decode(row['base64'], validate=True)
            require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
                    and base64.b64encode(data).decode('ascii') == row['base64'])
            values.append(data)
        try:
            actual = codec.observe(job, record['exit_code'], *values)
        except ValueError:
            require(record['observation'] is None and report['status'] == 'fail'
                    and index == len(report['records']) - 1)
            actual = None
        else:
            require(canonical(record['observation']) == canonical(actual))
        observations.append(actual)
    stop = report['budget_stop']
    if stop is not None:
        require(type(stop) is dict and set(stop) == {'label','bytes','sha256'}
                and len(report['records']) < 6 and stop['label'] == jobs[len(report['records'])]['label']
                and type(stop['bytes']) is int and 4063232 < stop['bytes'] < 8000000
                and type(stop['sha256']) is str and len(stop['sha256']) == 64
                and all(c in '0123456789abcdef' for c in stop['sha256']) and report['status'] == 'fail')
    if report['status'] == 'pass':
        require(len(observations) == 6 and all(o is not None and o['status'] == 'pass' for o in observations)
                and report['error_class'] == 'none' and stop is None
                and report['source_hashes_after'] == expected_hashes)
    return report


def worker_result(value, owner, ready):
    require(type(value) is dict and set(value) == FINAL_KEYS
            and value['protocol'] == 'stead.fixed-pure-eval-worker-result/1'
            and value['status'] in ('pass','fail') and value['phase'] in PHASES
            and value['error_class'] in ERRORS and value['cleanup_error_class'] == 'none'
            and value['outer_cleanup_required'] is True and value['children_reaped'] is True
            and value['namespace_baseline_restored'] is True
            and value['qualifies_phase'] is False and value['native_application_executed'] is False
            and type(value['jobs_retained']) is int and 0 <= value['jobs_retained'] <= 6
            and type(value['elapsed_ms']) is int and 0 <= value['elapsed_ms'] <= 555000)
    proof = value['admission']
    require(type(proof) is dict and set(proof) == {'uid','gid','host_uid','host_gid','namespace_maps',
            'namespaces','source_uid','capabilities_empty','no_new_privileges','private_loopback_only',
            'owner_sha256','sources','runtime_sha256','guardian_lease_required'}
            and type(proof['uid']) is int and proof['uid'] == 1000
            and type(proof['gid']) is int and proof['gid'] == 1000
            and type(proof['source_uid']) is int and proof['source_uid'] == 65534
            and type(proof['host_uid']) is int and proof['host_uid'] == owner['host_uid']
            and type(proof['host_gid']) is int and proof['host_gid'] == owner['host_gid']
            and canonical(proof['namespace_maps']) == canonical({'uid':[1000,0,1],'gid':[1000,0,1]})
            and proof['namespaces'] == ready['namespaces']
            and proof['owner_sha256'] == hashlib.sha256(canonical(owner)).hexdigest()
            and canonical(proof['sources']) == canonical(owner['sources'])
            and proof['runtime_sha256'] == owner['runtime']['sha256']
            and all(proof[k] is True for k in ('capabilities_empty','no_new_privileges','private_loopback_only','guardian_lease_required')))
    require(type(value['report']) is dict and set(value['report']) == {'bytes','sha256'}
            and type(value['report']['bytes']) is int and 0 < value['report']['bytes'] <= WORKER_REPORT_LIMIT)
    if value['status'] == 'pass':
        require(value['phase'] == 'complete' and value['error_class'] == 'none' and value['jobs_retained'] == 6)
    return value


def run(process, job, value, owner, heartbeat, codec, jobs, source_hashes):
    selector = selectors.DefaultSelector()
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    eof = {'stdout': False, 'stderr': False}
    ready = anchor = final = None
    artifact = None
    result = {'protocol':'stead.fixed-pure-eval-guard/1','status':'fail','error_class':'none',
              'cleanup_error_class':'none','parent_admitted':False,'owned_children_empty':False,
              'child_streams_eof':False,'worker_exit_code':None,'worker_result':None,
              'report_pin':None,'root_loopback_observation':None,'qualifies_phase':False}
    started = time.monotonic()
    try:
        service_current(value); heartbeat()
        for name, stream in (('stdout',process.stdout),('stderr',process.stderr)):
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
        consumed = 0
        while process.poll() is None or selector.get_map():
            heartbeat();service_current(value)
            require(time.monotonic()-started < TOTAL_SECONDS)
            if anchor is not None and process.poll() is None:
                # A worker may finish before its already-written final packet is
                # drained. Its retained pidfd distinguishes death from replacement.
                if not select.select([anchor['pidfd']],[],[],0)[0]:
                    boundary.current(anchor,value,heartbeat)
            elif ready is None:
                require(time.monotonic()-started < READY_SECONDS)
            for event,_ in selector.select(0.05):
                name=event.data;raw=os.read(event.fileobj.fileno(),8192)
                if not raw:
                    eof[name]=True;selector.unregister(event.fileobj);event.fileobj.close();continue
                streams[name].extend(raw)
                require(len(streams[name]) <= (STDOUT_LIMIT if name=='stdout' else STDERR_LIMIT))
            while b'\n' in streams['stdout'][consumed:]:
                end=streams['stdout'].index(b'\n',consumed)
                row=parse(bytes(streams['stdout'][consumed:end]),16384);consumed=end+1
                if ready is None:
                    require(row.get('protocol')=='stead.fixed-pure-eval-ready/1')
                    ready=row
                    anchor=boundary.pin_ready(job,value,ready,hashlib.sha256(canonical(owner)).hexdigest(),heartbeat)
                    result['root_loopback_observation']=boundary.loopback_observation(anchor,value,heartbeat)
                    boundary.current(anchor,value,heartbeat)
                    process.stdin.write(b'go\n');process.stdin.flush();process.stdin.close()
                    result['parent_admitted']=True
                else:
                    require(final is None)
                    final=worker_result(row,owner,ready)
        process.wait(timeout=1)
        require(ready is not None and final is not None and consumed==len(streams['stdout'])
                and streams['stderr']==b'' and all(eof.values()))
        require(process.returncode == (0 if final['status']=='pass' else 1))
        result['worker_result']=final;result['worker_exit_code']=process.returncode
    except BaseException as error:
        result['error_class']=type(error).__name__ if type(error).__name__ in ERRORS else 'unrecognized'
    finally:
        try:
            if process.stdin is not None and not process.stdin.closed:process.stdin.close()
        except BaseException:
            result['cleanup_error_class']='stdin-close'
        try:
            result['owned_children_empty']=cleanup(process,value)
        except BaseException:
            result['cleanup_error_class']='owned-cleanup'
        result['child_streams_eof']=all(eof.values())
        for event in list(selector.get_map().values()):
            try:event.fileobj.close()
            except BaseException:result['cleanup_error_class']='stream-close'
        selector.close()
        try:
            if (result['error_class']=='none' and result['cleanup_error_class']=='none'
                    and result['owned_children_empty'] and result['child_streams_eof'] and anchor is not None):
                heartbeat();service_current(value)
                artifact=boundary.read_output(anchor,value,'report.json',final['report'])
                report=validate_report(artifact,codec,jobs,source_hashes)
                require(report['status']==final['status'] and len(report['records'])==final['jobs_retained'])
                result['report_pin']=final['report']
                result['status']=report['status']
        except BaseException as error:
            if result['error_class']=='none':result['error_class']=type(error).__name__ if type(error).__name__ in ERRORS else 'unrecognized'
            result['status']='fail';artifact=None
        finally:
            if anchor is not None:
                try:boundary.close_anchor(anchor)
                except BaseException:result['cleanup_error_class']='anchor-close';result['status']='fail';artifact=None
    return result, artifact


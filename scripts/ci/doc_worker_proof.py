"""Trusted hosted-only proof of the deterministic Doc child, not Run authority.

The existing root guardian launches this proof through its admitted nonzero
host account before native startup. The isolated namespace receives just this
file, the worker and synthetic inputs. The native worker verifies the resulting
root-owned immutable admission; it cannot launch or replace the proof itself.
Publication crash cases use explicit test-only checkpoints around real writes;
they execute the real isolated recipe and SIGKILL its parent at those points.
They do not prove native publication, model execution, or power-loss durability.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

WORKER = '/doc_run_worker.py'
PROOF = '/proof.py'
CUTS = ('before-child', 'before-output', 'after-output', 'after-receipt')
CHECKS = ('exact-output', 'distinct-private-namespaces', 'credential-environment-absent',
          'completed-output-not-overwritten', 'wrong-worker-pin-refused',
          'wrong-context-refused', 'output-budget-refused', *CUTS)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate proof field')
        value[key] = item
    return value


def pin(path, expected):
    require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None, 'Exact proof source pin required')
    require(sha(Path(path).read_bytes()) == expected, 'Proof source differs')


def uid(number):
    return '019939ba-4000-7000-8000-' + format(number, '012x')


def fixture():
    # Deliberately independently constructed: preserve UTF-8 and trailing spaces.
    base = '---\nid: ' + uid(4) + '\ntype: page\nstate: published\n---\n# Guide λ\nOriginal  \n'
    target = {'kind': 'document', 'project_id': uid(1), 'collection_id': uid(3),
              'document_id': uid(4), 'expected_revision': '7', 'base_markdown_sha256': sha(base.encode())}
    context = {'protocol': 'stead.run-context/1', 'project_id': uid(1), 'work_id': uid(2),
               'execution_contract_revision': '9', 'execution_contract_digest': 'a' * 64,
               'title': 'Clarify the guide', 'description': 'Keep the exact base.',
               'acceptance_criteria': 'An independent person reviews the result.',
               'instructions_digest': 'b' * 64, 'runtime_policy_digest': 'c' * 64,
               'documents': canonical({uid(5): {'target': canonical(target).decode(), 'markdown': base}}).decode()}
    raw = canonical(context)
    job = {'protocol': 'stead.doc-worker-job/1', 'project_id': uid(1), 'work_id': uid(2),
           'run_id': uid(6), 'attempt': '1', 'run_contract_sha256': 'd' * 64,
           'context_digest': sha(b'stead.run-context/1\0' + raw), 'outcome_id': uid(5),
           'recipe': 'stead.doc.append-paragraph/1', 'paragraph': 'A bounded clarification λ.',
           'max_output_bytes': '32768'}
    return canonical(job), raw, target, (base + '\n' + job['paragraph'] + '\n').encode()


def load_worker(expected):
    pin(WORKER, expected)
    spec = importlib.util.spec_from_file_location('doc_run_worker', WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    path.chmod(0o600)


def setup(name, worker_sha):
    root = Path('/state') / name
    root.mkdir(mode=0o700)
    job, context, _, _ = fixture()
    private_write(root / 'job.json', job)
    private_write(root / 'context.json', context)
    return SimpleNamespace(job=root / 'job.json', context=root / 'context.json',
                           job_sha256=sha(job), worker_sha256=worker_sha, output=root / 'output')


def result_files(output):
    try:
        directory = output.lstat()
    except FileNotFoundError:
        return {}
    require(stat.S_ISDIR(directory.st_mode) and directory.st_uid == os.getuid()
            and directory.st_mode & 0o777 == 0o700, 'Owned output directory changed')
    found = {}
    for path in output.iterdir():
        info = path.lstat()
        require(path.name in ('proposal.md', 'result.json') and stat.S_ISREG(info.st_mode)
                and info.st_uid == os.getuid() and info.st_nlink == 1 and info.st_mode & 0o777 == 0o600
                and info.st_size <= 131072, 'Output custody differs')
        found[path.name] = sha(path.read_bytes())
    return found


def refuse(worker, args):
    before = result_files(args.output)
    try:
        worker.run(args)
    except ValueError:
        require(result_files(args.output) == before, 'Rejected work changed output')
        return
    raise ValueError('Expected worker refusal')


def checkpoint(name):
    os.write(1, (name + '\n').encode('ascii'))
    os.kill(os.getpid(), signal.SIGSTOP)
    raise ValueError('A stopped checkpoint must be killed, never resumed')


def cutpoint(name, worker_sha, proof_sha):
    require(name in CUTS and os.getuid() != 0, 'Unknown or privileged crash case')
    pin(PROOF, proof_sha)
    worker = load_worker(worker_sha)
    root = Path('/state') / name
    args = SimpleNamespace(job=root / 'job.json', context=root / 'context.json',
                           output=root / 'output', worker_sha256=worker_sha,
                           job_sha256=sha((root / 'job.json').read_bytes()))
    if name == 'before-child':
        # Explicit injection before the real subprocess is started.
        worker.subprocess.run = lambda *a, **k: checkpoint(name)
    else:
        original = worker.write_new

        def interrupted(directory, filename, raw):
            if name == 'before-output' and filename == 'proposal.md':
                checkpoint(name)
            original(directory, filename, raw)
            if ((name == 'after-output' and filename == 'proposal.md')
                    or (name == 'after-receipt' and filename == 'result.json')):
                checkpoint(name)

        worker.write_new = interrupted
    worker.run(args)
    raise ValueError('Required crash point was not reached')


def exercise_cut(name, worker, worker_sha, proof_sha):
    args = setup(name, worker_sha)
    process = subprocess.Popen(['/usr/bin/python3', '-I', '-B', PROOF, '_cutpoint', name, worker_sha, proof_sha],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            require(selector.select(12), 'Crash checkpoint deadline')
            observed = os.read(process.stdout.fileno(), 128)
        require(observed == (name + '\n').encode(), 'Exact crash checkpoint absent')
        process.kill()
        require(process.wait(timeout=2) == -signal.SIGKILL, 'Crash parent not killed and reaped')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        process.stdout.close()
    files = result_files(args.output)
    expected = {'before-child': set(), 'before-output': set(),
                'after-output': {'proposal.md'}, 'after-receipt': {'proposal.md', 'result.json'}}[name]
    require(set(files) == expected, 'Wrong files survived the observed crash point')
    if 'proposal.md' in files:
        require(files['proposal.md'] == sha(fixture()[3]), 'Crash changed exact output')
    if args.output.exists():
        refuse(worker, args)  # A partial or completed output is never silently rerun.
    else:
        require(name == 'before-child', 'Output directory disappeared after publication began')
    if 'result.json' in files:
        receipt = json.loads((args.output / 'result.json').read_bytes())
        require(receipt['status'] == 'output-ready' and receipt['artifact']['sha256'] == files['proposal.md'],
                'Receipt and artifact diverged after crash')
    return {'point': name, 'parent_exit': -signal.SIGKILL, 'files': sorted(files), 'overwrite_refused': args.output.exists()}


def body(worker_sha, proof_sha, outer_namespaces):
    phase('admission')
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_FSIZE, (131072, 131072))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    require(os.getuid() == os.getgid() == 1000, 'Proof needs the unprivileged inner identity')
    pin(PROOF, proof_sha)
    worker = load_worker(worker_sha)
    require(os.statvfs(PROOF).f_flag & os.ST_RDONLY and os.statvfs(WORKER).f_flag & os.ST_RDONLY,
            'Proof sources are writable')
    phase('namespaces')
    namespaces = worker.namespaces()
    require(set(namespaces) == set(outer_namespaces)
            and all(namespaces[key] != outer_namespaces[key] for key in namespaces), 'Proof namespace reused')
    require([name for _, name in socket.if_nameindex()] == ['lo'], 'Proof has external interface')
    require(not any(Path(p).exists() for p in ('/home', '/root', '/etc', '/run', '/code', '/ci', '/native', '/execution')),
            'Proof received controller or authority files')
    phase('state')
    require(list(Path('/state').iterdir()) == [], 'Fresh proof state required')
    # Synthetic canaries are never real credentials. The child must reject any
    # inherited environment and must not see this parent's private state tree.
    os.environ['STEAD_SYNTHETIC_PROVIDER_SECRET'] = 'not-a-provider-secret'
    phase('state-write')
    private_write(Path('/state/provider-canary'), b'not-a-provider-secret')
    phase('fixture')
    args = setup('complete', worker_sha)
    phase('recipe')
    receipt = worker.run(args)
    phase('output')
    job, context, target, expected = fixture()
    require((args.output / 'proposal.md').read_bytes() == expected, 'Exact synthetic Markdown differs')
    require(receipt['target'] == target and receipt['job_sha256'] == sha(job)
            and receipt['worker_sha256'] == worker_sha and receipt['context_digest'] == json.loads(job)['context_digest']
            and receipt['artifact'] == {'name': 'proposal.md', 'bytes': len(expected), 'sha256': sha(expected)},
            'Actual output receipt differs')
    require(receipt['isolation']['namespaces'] != namespaces, 'Worker did not use distinct namespaces')
    phase('overwrite')
    refuse(worker, args)
    phase('wrong-pin')
    bad = setup('wrong-pin', worker_sha)
    bad.worker_sha256 = '0' * 64
    refuse(worker, bad)
    phase('wrong-context')
    bad = setup('wrong-context', worker_sha)
    bad.context.write_bytes(context + b' ')
    refuse(worker, bad)
    phase('budget')
    bad = setup('budget', worker_sha)
    reduced = json.loads(job) | {'max_output_bytes': '1'}
    bad.job.write_bytes(canonical(reduced))
    bad.job_sha256 = sha(canonical(reduced))
    refuse(worker, bad)
    crashes = []
    for name in CUTS:
        phase(name)
        crashes.append(exercise_cut(name, worker, worker_sha, proof_sha))
    phase('complete')
    return {'protocol': 'stead.doc-worker-isolation-proof/1', 'status': 'pass',
            'worker_sha256': worker_sha, 'proof_sha256': proof_sha,
            'job_sha256': sha(job), 'context_sha256': sha(context), 'artifact_sha256': sha(expected),
            'checks': list(CHECKS), 'crashes': crashes,
            'classification': 'actual-isolated-deterministic-child-with-publication-fault-injection',
            'native_publication': False, 'model_execution': False, 'qualifies_g3': False}


PHASES = ('launcher', 'admission', 'namespaces', 'state', 'state-write', 'fixture',
          'recipe', 'output', 'overwrite', 'wrong-pin', 'wrong-context', 'budget',
          *CUTS, 'complete', 'collector')
ERROR_CLASSES = ('none', 'ValueError', 'PermissionError', 'FileNotFoundError',
                 'OSError', 'TimeoutExpired', 'AssertionError', 'unrecognized')
ERRNOS = {1: 'eperm', 2: 'enoent', 5: 'eio', 13: 'eacces', 28: 'enospc', 30: 'erofs'}
REASONS = ('complete', 'unrecognized', 'identity', 'source-pin', 'namespace', 'interface',
           'mounts', 'state', 'custody', 'recipe', 'result', 'refusal', 'crash',
           'os-error', 'uid-map', 'namespace-setup', 'deadline', 'output-bound',
           'collector', 'nonzero-exit', 'unexpected-stderr', 'descendants', 'invalid-proof')
CURRENT_PHASE = 'launcher'


def phase(value):
    global CURRENT_PHASE
    require(value in PHASES, 'Unknown proof phase')
    CURRENT_PHASE = value


def failure_value(error):
    messages = {
        'Proof needs the unprivileged inner identity': 'identity',
        'Exact proof source pin required': 'source-pin', 'Proof source differs': 'source-pin',
        'Proof namespace reused': 'namespace', 'Proof has external interface': 'interface',
        'Proof received controller or authority files': 'mounts', 'Proof sources are writable': 'mounts',
        'Fresh proof state required': 'state', 'Owned output directory changed': 'custody',
        'Output custody differs': 'custody', 'Isolated Doc recipe did not finish': 'recipe',
        'Exact synthetic Markdown differs': 'result', 'Actual output receipt differs': 'result',
        'Worker did not use distinct namespaces': 'namespace',
        'Rejected work changed output': 'refusal', 'Expected worker refusal': 'refusal',
        'Crash checkpoint deadline': 'crash', 'Exact crash checkpoint absent': 'crash',
        'Crash parent not killed and reaped': 'crash',
        'Wrong files survived the observed crash point': 'crash',
        'Crash changed exact output': 'crash',
        'Output directory disappeared after publication began': 'crash',
        'Receipt and artifact diverged after crash': 'crash',
    }
    name = type(error).__name__
    return {'protocol': 'stead.doc-worker-failure/1', 'status': 'fail',
            'phase': CURRENT_PHASE, 'reason': messages.get(str(error), 'os-error' if isinstance(error, OSError) else 'unrecognized'),
            'error_class': name if name in ERROR_CLASSES else 'unrecognized',
            'errno': ERRNOS.get(getattr(error, 'errno', None), 'none' if not isinstance(error, OSError) else 'unrecognized')}


def closed_failure(value):
    require(isinstance(value, dict) and set(value) == {'protocol', 'status', 'phase', 'reason', 'error_class', 'errno'}
            and value['protocol'] == 'stead.doc-worker-failure/1' and value['status'] == 'fail'
            and value['phase'] in PHASES and value['reason'] in REASONS
            and value['error_class'] in ERROR_CLASSES and value['errno'] in (*ERRNOS.values(), 'none', 'unrecognized'),
            'Closed proof failure required')
    return value


def guardian_command(worker, proof, worker_sha, proof_sha, outer_namespaces):
    """Called only after the existing owner drops to its nonzero host account."""
    require(os.getuid() > 0 and os.getgid() > 0, 'Nonzero proof launcher identity required')
    pin(worker, worker_sha)
    pin(proof, proof_sha)
    require(set(outer_namespaces) == {'net', 'mnt', 'pid', 'user'}
            and all(isinstance(v, str) and re.fullmatch(re.escape(k) + r':\[[0-9]+\]', v) for k, v in outer_namespaces.items()),
            'Exact launcher namespaces required')
    command = ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--die-with-parent', '--uid', '1000',
               '--gid', '1000', '--cap-drop', 'ALL', '--clearenv', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        command += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
    return command + ['--proc', '/proc', '--dev', '/dev', '--size', str(8 * 1024 * 1024), '--tmpfs', '/state',
                '--size', str(2 * 1024 * 1024), '--tmpfs', '/tmp', '--ro-bind', str(worker), WORKER,
                '--ro-bind', str(proof), PROOF, '--chdir', '/state', '--', '/usr/bin/python3', '-I', '-B', PROOF,
                '_body', worker_sha, proof_sha, canonical(outer_namespaces).decode()]


class ProofFailure(ValueError):
    def __init__(self, diagnostic):
        super().__init__('Hosted Doc child proof failed')
        self.diagnostic = diagnostic


def stream_summary(raw, *, eof, overflow=False):
    return {'bytes': len(raw), 'sha256': sha(raw), 'complete': bool(eof and not overflow), 'eof': bool(eof)}


def diagnostic(raw, stderr, exit_code, *, eof, reason=None):
    require(exit_code is None or type(exit_code) is int and -255 <= exit_code <= 255, 'Proof exit bound')
    value = {'protocol': 'stead.doc-worker-launch/1', 'status': 'fail', 'phase': 'launcher',
             'reason': reason or 'nonzero-exit', 'error_class': 'none', 'errno': 'none', 'exit_code': exit_code,
             'descendants_reaped': False,
             'stdout': stream_summary(raw, eof=eof['stdout'], overflow=len(raw) > 16384),
             'stderr': stream_summary(stderr, eof=eof['stderr'], overflow=len(stderr) > 8192)}
    if reason is None and len(raw) <= 16384:
        try:
            child = json.loads(raw, object_pairs_hook=unique)
            require(raw == canonical(child) + b'\n', 'Canonical proof failure required')
            closed_failure(child)
            value.update({k: child[k] for k in ('phase', 'reason', 'error_class', 'errno')})
        except (ValueError, TypeError, UnicodeError):
            lines = stderr.splitlines()
            if any(line in (b'bwrap: setting up uid map: Permission denied',
                            b'bwrap: setting up uid map: Operation not permitted') for line in lines):
                value.update(reason='uid-map', error_class='PermissionError', errno='eperm')
            elif any(line in (b'bwrap: Creating new namespace failed: Operation not permitted',
                              b'bwrap: Creating new namespace failed: Permission denied') for line in lines):
                value.update(reason='namespace-setup', error_class='PermissionError', errno='eperm')
    return value


def verify_diagnostic(value):
    require(isinstance(value, dict) and set(value) == {'protocol', 'status', 'phase', 'reason', 'error_class', 'errno', 'exit_code', 'descendants_reaped', 'stdout', 'stderr'}
            and value['protocol'] == 'stead.doc-worker-launch/1' and value['status'] in ('pass', 'fail')
            and value['phase'] in PHASES and value['reason'] in REASONS and value['error_class'] in ERROR_CLASSES
            and type(value['descendants_reaped']) is bool
            and value['errno'] in (*ERRNOS.values(), 'none', 'unrecognized')
            and (value['exit_code'] is None or type(value['exit_code']) is int and -255 <= value['exit_code'] <= 255),
            'Closed proof diagnostic required')
    for name, maximum in (('stdout', 16385), ('stderr', 8193)):
        row = value[name]
        require(isinstance(row, dict) and set(row) == {'bytes', 'sha256', 'complete', 'eof'}
                and type(row['bytes']) is int and 0 <= row['bytes'] <= maximum
                and isinstance(row['sha256'], str) and re.fullmatch('[0-9a-f]{64}', row['sha256'])
                and type(row['complete']) is bool and type(row['eof']) is bool
                and (not row['complete'] or row['eof'] and row['bytes'] < maximum), 'Proof stream diagnostic bound')
    return value


def observe_process(process, heartbeat, owned_pids, baseline, worker_sha, proof_sha):
    """Root guardian drains bounded data while retaining the original heartbeat."""
    raw = {'stdout': bytearray(), 'stderr': bytearray()}
    eof = {'stdout': False, 'stderr': False}
    limits = {'stdout': 16384, 'stderr': 8192}
    reason = None
    deadline = time.monotonic() + 75
    next_tick = 0
    captured_error = None
    try:
        with selectors.DefaultSelector() as selector:
            for name in raw:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                now = time.monotonic()
                if now >= next_tick:
                    heartbeat()
                    next_tick = now + .5
                if now >= deadline:
                    reason = 'deadline'
                    break
                for key, _ in selector.select(.1):
                    name = key.data
                    chunk = os.read(key.fileobj.fileno(), min(4096, limits[name] + 1 - len(raw[name])))
                    if not chunk:
                        eof[name] = True
                        selector.unregister(key.fileobj)
                        continue
                    raw[name].extend(chunk)
                    if len(raw[name]) > limits[name]:
                        reason = 'output-bound'
                        break
                if reason:
                    break
    except BaseException as error:
        reason = 'collector'
        captured_error = error
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        else:
            process.wait(timeout=2)
        for name in raw:
            getattr(process, name).close()
    # Success cannot leave a hidden descendant behind or merely lose its pipe.
    reaped = False
    try:
        reap_deadline = time.monotonic() + 5
        while owned_pids() != baseline and time.monotonic() < reap_deadline:
            if captured_error is None:
                heartbeat()
            time.sleep(.05)
        reaped = owned_pids() == baseline
        if not reaped:
            reason = 'descendants'
        if captured_error is None:
            heartbeat()
    except BaseException as error:
        reason = 'collector'
        captured_error = error
    raw, stderr = bytes(raw['stdout']), bytes(raw['stderr'])
    observed = diagnostic(raw, stderr, process.returncode, eof=eof, reason=reason)
    observed['descendants_reaped'] = reaped
    if captured_error is not None:
        name = type(captured_error).__name__
        observed['phase'] = 'collector'
        observed['error_class'] = name if name in ERROR_CLASSES else 'unrecognized'
        observed['errno'] = ERRNOS.get(getattr(captured_error, 'errno', None), 'none')
    if reason or process.returncode != 0 or not all(eof.values()):
        raise ProofFailure(verify_diagnostic(observed))
    if stderr:
        observed['reason'] = 'unexpected-stderr'
        raise ProofFailure(verify_diagnostic(observed))
    try:
        value = json.loads(raw, object_pairs_hook=unique)
        require(raw == canonical(value) + b'\n', 'Canonical proof result required')
        verify(value, worker_sha, proof_sha)
    except (ValueError, TypeError, UnicodeError):
        observed['reason'] = 'invalid-proof'
        raise ProofFailure(verify_diagnostic(observed))
    observed.update(status='pass', phase='complete', reason='complete')
    return value, verify_diagnostic(observed)


def admission(proof, launch, inputs, context, guardian_pid):
    value = {'protocol': 'stead.doc-worker-admission/1', 'run_id': context['run_id'],
             'inputs_sha256': sha(canonical(inputs)), 'controller_commit': inputs['controller_commit'],
             'candidate_commit': inputs['candidate_commit'], 'guard_sha256': context['guard_sha256'],
             'unit': context['unit'], 'guardian_pid': guardian_pid,
             'owner_uid': context['uid'], 'owner_gid': context['gid'], 'proof': proof, 'launch': launch}
    verify_admission(value, inputs, context['run_id'])
    return value


def verify_admission(value, inputs, run_id, lease=None):
    require(isinstance(value, dict) and set(value) == {'protocol', 'run_id', 'inputs_sha256', 'controller_commit',
            'candidate_commit', 'guard_sha256', 'unit', 'guardian_pid', 'owner_uid', 'owner_gid', 'proof', 'launch'},
            'Exact Doc proof admission required')
    require(value['protocol'] == 'stead.doc-worker-admission/1' and value['run_id'] == run_id
            and isinstance(run_id, str) and re.fullmatch('[0-9a-f]{32}', run_id)
            and value['inputs_sha256'] == sha(canonical(inputs))
            and value['controller_commit'] == inputs['controller_commit']
            and value['candidate_commit'] == inputs['candidate_commit']
            and value['guard_sha256'] == inputs['controller_files']['scripts/ci/hosted.py']['sha256']
            and value['unit'] == 'stead-hosted-' + run_id + '.service'
            and type(value['guardian_pid']) is int and 0 < value['guardian_pid'] < 2**31
            and all(type(value[k]) is int and 0 < value[k] < 2**32 - 1 for k in ('owner_uid', 'owner_gid')),
            'Doc proof admission identity differs')
    verify(value['proof'], inputs['controller_files']['scripts/urbit/doc_run_worker.py']['sha256'],
           inputs['controller_files']['scripts/ci/doc_worker_proof.py']['sha256'])
    launch = verify_diagnostic(value['launch'])
    expected_stdout = canonical(value['proof']) + b'\n'
    expected = diagnostic(expected_stdout, b'', 0, eof={'stdout': True, 'stderr': True})
    expected.update(status='pass', phase='complete', reason='complete', descendants_reaped=True)
    require(canonical(launch) == canonical(expected), 'Doc proof launch was not complete')
    if lease is not None:
        require(value['run_id'] == lease['run_id'] and value['unit'] == lease['unit']
                and value['guard_sha256'] == lease['guard_sha256']
                and str(value['guardian_pid']) == lease['service']['MainPID'], 'Doc proof belongs to another guardian')
    return value


def read_admission(inputs, run_id, lease):
    path = '/doc-proof.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        # Host root is deliberately unmapped inside the native worker. Check
        # its overflow UID, mapped group and exact host-account UID/GID maps;
        # namespace UID0 is never used as a claim of host root ownership.
        overflow = int(Path('/proc/sys/kernel/overflowuid').read_text().strip())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == overflow and info.st_gid == 0
                and info.st_nlink == 1 and info.st_mode & 0o777 == 0o440 and 0 < info.st_size <= 32768
                and os.fstatvfs(fd).f_flag & os.ST_RDONLY, 'Doc proof custody differs')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(32769)
        after = os.fstat(fd)
        require((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and len(raw) == info.st_size,
                'Doc proof changed during read')
        value = json.loads(raw, object_pairs_hook=unique)
        require(raw == canonical(value) + b'\n', 'Canonical Doc proof admission required')
        admitted = verify_admission(value, inputs, run_id, lease)
        uid_map = [[int(v) for v in row.split()] for row in Path('/proc/self/uid_map').read_text().splitlines()]
        gid_map = [[int(v) for v in row.split()] for row in Path('/proc/self/gid_map').read_text().splitlines()]
        require(os.getuid() == os.getgid() == 0 and uid_map == [[0, admitted['owner_uid'], 1]]
                and gid_map == [[0, admitted['owner_gid'], 1]], 'Doc proof mapped owner differs')
        return admitted['proof']
    finally:
        os.close(fd)


def verify(value, worker_sha, proof_sha):
    job, context, _, expected = fixture()
    crashes = [{'point': name, 'parent_exit': -signal.SIGKILL,
                'files': {'before-child': [], 'before-output': [], 'after-output': ['proposal.md'],
                          'after-receipt': ['proposal.md', 'result.json']}[name],
                'overwrite_refused': name != 'before-child'} for name in CUTS]
    expected_value = {'protocol': 'stead.doc-worker-isolation-proof/1', 'status': 'pass',
            'worker_sha256': worker_sha, 'proof_sha256': proof_sha,
            'job_sha256': sha(job), 'context_sha256': sha(context), 'artifact_sha256': sha(expected),
            'checks': list(CHECKS), 'crashes': crashes,
            'classification': 'actual-isolated-deterministic-child-with-publication-fault-injection',
            'native_publication': False, 'model_execution': False, 'qualifies_g3': False}
    require(canonical(value) == canonical(expected_value), 'Incomplete Doc child proof')


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '_body':
        try:
            value = body(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
        except BaseException as error:
            print(canonical(failure_value(error)).decode(), flush=True)
            raise SystemExit(1)
        print(canonical(value).decode(), flush=True)
    elif len(sys.argv) == 5 and sys.argv[1] == '_cutpoint':
        cutpoint(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit('No workstation or standalone controller entry point')

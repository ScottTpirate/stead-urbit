"""Trusted hosted-only proof of the deterministic Doc child, not Run authority.

The reviewed CI worker calls run_controller only after its normal admission and
empty-state isolation checks. No command line entry can launch that controller.
Its extra namespace receives just this file, the worker and synthetic inputs.
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
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_FSIZE, (131072, 131072))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    require(os.getuid() == os.getgid() == 1000, 'Proof needs the unprivileged inner identity')
    pin(PROOF, proof_sha)
    worker = load_worker(worker_sha)
    namespaces = worker.namespaces()
    require(set(namespaces) == set(outer_namespaces)
            and all(namespaces[key] != outer_namespaces[key] for key in namespaces), 'Proof namespace reused')
    require([name for _, name in socket.if_nameindex()] == ['lo'], 'Proof has external interface')
    require(not any(Path(p).exists() for p in ('/home', '/root', '/etc', '/run', '/code', '/ci', '/native', '/execution')),
            'Proof received controller or authority files')
    require(list(Path('/state').iterdir()) == [], 'Fresh proof state required')
    # Synthetic canaries are never real credentials. The child must reject any
    # inherited environment and must not see this parent's private state tree.
    os.environ['STEAD_SYNTHETIC_PROVIDER_SECRET'] = 'not-a-provider-secret'
    private_write(Path('/state/provider-canary'), b'not-a-provider-secret')
    args = setup('complete', worker_sha)
    receipt = worker.run(args)
    job, context, target, expected = fixture()
    require((args.output / 'proposal.md').read_bytes() == expected, 'Exact synthetic Markdown differs')
    require(receipt['target'] == target and receipt['job_sha256'] == sha(job)
            and receipt['worker_sha256'] == worker_sha and receipt['context_digest'] == json.loads(job)['context_digest']
            and receipt['artifact'] == {'name': 'proposal.md', 'bytes': len(expected), 'sha256': sha(expected)},
            'Actual output receipt differs')
    require(receipt['isolation']['namespaces'] != namespaces, 'Worker did not use distinct namespaces')
    refuse(worker, args)
    bad = setup('wrong-pin', worker_sha)
    bad.worker_sha256 = '0' * 64
    refuse(worker, bad)
    bad = setup('wrong-context', worker_sha)
    bad.context.write_bytes(context + b' ')
    refuse(worker, bad)
    bad = setup('budget', worker_sha)
    reduced = json.loads(job) | {'max_output_bytes': '1'}
    bad.job.write_bytes(canonical(reduced))
    bad.job_sha256 = sha(canonical(reduced))
    refuse(worker, bad)
    crashes = [exercise_cut(name, worker, worker_sha, proof_sha) for name in CUTS]
    return {'protocol': 'stead.doc-worker-isolation-proof/1', 'status': 'pass',
            'worker_sha256': worker_sha, 'proof_sha256': proof_sha,
            'job_sha256': sha(job), 'context_sha256': sha(context), 'artifact_sha256': sha(expected),
            'checks': list(CHECKS), 'crashes': crashes,
            'classification': 'actual-isolated-deterministic-child-with-publication-fault-injection',
            'native_publication': False, 'model_execution': False, 'qualifies_g3': False}


def run_controller(execution_check):
    """Only inside the existing admitted hosted worker, before native fresh boot."""
    execution_check()
    worker = Path('/code/doc_run_worker.py')
    proof = Path('/ci/doc_worker_proof.py')
    require(os.statvfs(worker).f_flag & os.ST_RDONLY and os.statvfs(proof).f_flag & os.ST_RDONLY,
            'Controller must mount both reviewed files read-only')
    worker_sha, proof_sha = sha(worker.read_bytes()), sha(proof.read_bytes())
    namespaces = {name: os.readlink('/proc/self/ns/' + name) for name in ('net', 'mnt', 'pid', 'user')}
    command = ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--die-with-parent', '--uid', '1000',
               '--gid', '1000', '--cap-drop', 'ALL', '--clearenv', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        command += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
    command += ['--proc', '/proc', '--dev', '/dev', '--size', str(8 * 1024 * 1024), '--tmpfs', '/state',
                '--size', str(2 * 1024 * 1024), '--tmpfs', '/tmp', '--ro-bind', str(worker), WORKER,
                '--ro-bind', str(proof), PROOF, '--chdir', '/state', '--', '/usr/bin/python3', '-I', '-B', PROOF,
                '_body', worker_sha, proof_sha, canonical(namespaces).decode()]
    with tempfile.TemporaryFile(dir='/state') as output:
        process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.DEVNULL,
                                 timeout=75, check=False, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        output.seek(0)
        raw = output.read(16385)
    execution_check()
    require(process.returncode == 0 and 0 < len(raw) <= 16384, 'Hosted Doc child proof failed')
    value = json.loads(raw, object_pairs_hook=unique)
    verify(value, worker_sha, proof_sha)
    return value


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
        print(canonical(body(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))).decode(), flush=True)
    elif len(sys.argv) == 5 and sys.argv[1] == '_cutpoint':
        cutpoint(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit('No workstation or standalone controller entry point')

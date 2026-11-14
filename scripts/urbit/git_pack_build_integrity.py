"""Run only the fixed source-integrity recipe in an isolated Linux process."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import tempfile

from code_build_worker import limit_resources, namespaces, verify_isolation
from execution_policy import GuardError, directory_fd
import git_pack_build_source as source
import git_pack_build_verify as integrity
from portable_code import private_directory
from portable_recovery import TOKEN, UUID, decoded, encoded, match, require, same_entry, same_path, sha, shape


JOB = 'stead.build.source-integrity-job/1'
RESULT = 'stead.build.source-integrity-result/1'
JOB_FIELDS = {'protocol', 'job_id', 'recipe', 'source_manifest_sha256'}
MAX_JOB = 4096
MAX_RESULT = 8192
MAX_SECONDS = 30
MODULES = (
    'code_build_worker.py', 'execution_policy.py', 'git_pack_build_integrity.py', 'git_pack_build_source.py',
    'git_pack_build_verify.py', 'git_pack_http.py', 'git_pack_projection.py', 'git_pack_readback.py',
    'git_pack_store.py', 'git_pack_upload.py', 'portable_code.py', 'portable_recovery.py',
)


def load_job(raw, pin):
    require(match(TOKEN, pin) and sha(raw) == pin, 'source-integrity-job-pin')
    job = decoded(raw, MAX_JOB)
    shape(job, JOB_FIELDS)
    require(raw == encoded(job) and job['protocol'] == JOB and match(UUID, job['job_id'])
            and job['recipe'] == integrity.RECIPE and match(TOKEN, job['source_manifest_sha256']),
            'source-integrity-job')
    return job


@contextmanager
def _held(parent, name, limit, *, code=False):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        info = os.fstat(fd)
        owners, forbidden = ({0, os.getuid()}, 0o022) if code else ({os.getuid()}, 0o077)
        require(stat.S_ISREG(info.st_mode) and info.st_uid in owners and info.st_nlink == 1
                and not info.st_mode & forbidden and 0 < info.st_size <= limit, 'source-integrity-input')
        yield fd
        require(integrity._identity(os.fstat(fd)) == integrity._identity(info) and same_entry(parent, name, info),
                'source-integrity-input-changed')
    finally:
        os.close(fd)


def _bind(bindings, fd, name):
    bindings.extend(('--ro-bind-fd', str(fd), name))


def _command(pin, parent_namespaces, bindings):
    from git_pack_worker_service import sandbox_flags

    return [*sandbox_flags(), '--perms', '0700', '--dir', '/input', '--dir', '/recipe', *bindings,
            '--chdir', '/tmp', '--remount-ro', '/', '--', '/usr/bin/python3', '-I', '-S', '-B',
            '-c', 'import sys; sys.path.insert(0, "/recipe"); from git_pack_build_integrity import main; raise SystemExit(main())',
            '_isolated', pin, encoded(parent_namespaces).decode('ascii')]


def _isolated(pin, parent_namespaces):
    limit_resources()
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_RESULT, MAX_RESULT))
    verify_isolation(decoded(parent_namespaces.encode('ascii'), MAX_JOB))
    require(os.statvfs('/').f_flag & os.ST_RDONLY and os.statvfs('/recipe').f_flag & os.ST_RDONLY,
            'source-integrity-isolation')
    with Path('/input/job.json').open('rb') as file:
        raw = file.read(MAX_JOB + 1)
    job = load_job(raw, pin)
    result = integrity.verify(Path('/input'), job['source_manifest_sha256'])
    return {'protocol': RESULT, 'job_id': job['job_id'], 'job_sha256': pin, 'recipe': integrity.RECIPE,
            'execution': 'isolated-read-only', 'result_sha256': sha(encoded(result)), 'result': result}


def _result(raw, pin, job):
    value = decoded(raw, MAX_RESULT)
    shape(value, {'protocol', 'job_id', 'job_sha256', 'recipe', 'execution', 'result_sha256', 'result'})
    result = value['result']
    require(raw == encoded(value) and value['protocol'] == RESULT and value['job_id'] == job['job_id']
            and value['job_sha256'] == pin and value['recipe'] == integrity.RECIPE
            and value['execution'] == 'isolated-read-only' and isinstance(result, dict)
            and result.get('protocol') == integrity.PROTOCOL and result.get('recipe') == integrity.RECIPE
            and result.get('status') == 'verified' and result.get('source_manifest_sha256') == job['source_manifest_sha256']
            and value['result_sha256'] == sha(encoded(result)), 'source-integrity-result')
    return value


def run(job_path, pin, source_path):
    """Run one exact job and return its deterministic, bounded recipe receipt."""
    job_path, source_path = Path(job_path), Path(source_path)
    require(sys.platform.startswith('linux') and os.getuid() == os.geteuid() != 0
            and job_path.is_absolute() and source_path.is_absolute(), 'source-integrity-profile')
    code_path = Path(__file__).absolute().parent
    with ExitStack() as stack:
        inputs = stack.enter_context(directory_fd(source_path))
        job_parent = stack.enter_context(directory_fd(job_path.parent))
        code_parent = stack.enter_context(directory_fd(code_path))
        directories = ((source_path, private_directory(inputs)), (job_path.parent, private_directory(job_parent)),
                       (code_path, os.fstat(code_parent)))
        job_fd = stack.enter_context(_held(job_parent, job_path.name, MAX_JOB))
        job = load_job(os.pread(job_fd, MAX_JOB + 1, 0), pin)
        bindings, files = [], [job_fd]
        _bind(bindings, job_fd, '/input/job.json')
        for name, bound in ((source.MANIFEST, source.MAX_MANIFEST), (source.ARCHIVE, source.MAX_ARCHIVE)):
            fd = stack.enter_context(_held(inputs, name, bound))
            files.append(fd)
            _bind(bindings, fd, '/input/' + name)
        for name in MODULES:
            fd = stack.enter_context(_held(code_parent, name, 1024 * 1024, code=True))
            files.append(fd)
            _bind(bindings, fd, '/recipe/' + name)
        with tempfile.TemporaryFile() as output:
            proc = subprocess.run(_command(pin, namespaces(), bindings), pass_fds=files, stdin=subprocess.DEVNULL,
                                  stdout=output, stderr=subprocess.DEVNULL, env={}, timeout=MAX_SECONDS, check=False)
            require(proc.returncode == 0, 'source-integrity-isolation-or-verification-failed')
            output.seek(0)
            result = _result(output.read(MAX_RESULT + 1), pin, job)
        require(all(same_path(path, before) for path, before in directories), 'source-integrity-input-changed')
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 3 and argv[0] == '_isolated':
        result = _isolated(argv[1], argv[2])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--job', type=Path, required=True)
        parser.add_argument('--job-sha256', required=True)
        parser.add_argument('--source', type=Path, required=True)
        args = parser.parse_args(argv)
        result = run(args.job, args.job_sha256, args.source)
    raw = encoded(result)
    require(len(raw) <= MAX_RESULT, 'source-integrity-result-bound')
    sys.stdout.buffer.write(raw)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, GuardError, subprocess.SubprocessError):
        print('Isolated source integrity verification failed.', file=sys.stderr)
        raise SystemExit(1) from None

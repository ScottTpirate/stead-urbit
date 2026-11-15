#!/usr/bin/env python3
"""Prepare one deterministic Doc output in an isolated, credential-free child.

This local worker envelope is not a Home command or an authorization decision.
A separately admitted supervisor must verify the current Run claim, lease and
context before launch, then recheck authority when submitting the output. This
worker never contacts Home, calls a model, or treats its output as accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import socket
import stat
import subprocess
import sys
import tempfile

RECIPE = 'stead.doc.append-paragraph/1'
MAX_CONTEXT = 65536
MAX_MARKDOWN = 32768
MAX_REPLY = 128 * 1024
NAMESPACES = ('net', 'mnt', 'pid', 'user')
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
SHA = re.compile(r'[0-9a-f]{64}')
JOB_FIELDS = {'protocol', 'project_id', 'work_id', 'run_id', 'attempt',
              'run_contract_sha256', 'context_digest', 'outcome_id', 'recipe',
              'paragraph', 'max_output_bytes'}
CONTEXT_FIELDS = {'protocol', 'project_id', 'work_id', 'execution_contract_revision',
                  'execution_contract_digest', 'title', 'description',
                  'acceptance_criteria', 'instructions_digest',
                  'runtime_policy_digest', 'documents'}
TARGET_FIELDS = {'kind', 'project_id', 'collection_id', 'document_id',
                 'expected_revision', 'base_markdown_sha256'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def domain_hash(domain, raw):
    return sha(domain.encode('ascii') + b'\0' + raw)


def match(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def uint(value, *, positive=False):
    return (isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]{0,19}', value) is not None
            and int(positive) <= int(value) < 2**64)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def reject_number(_):
    raise ValueError('Worker inputs require strings instead of JSON numbers')


def decode(raw, limit):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= limit:
        raise ValueError('Input byte bound')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                           parse_constant=reject_number, parse_float=reject_number, parse_int=reject_number)
        if not isinstance(value, dict) or canonical(value) != raw:
            raise ValueError('Expected canonical JSON object')
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Invalid canonical UTF-8 JSON') from error
    return value


def text(value, limit, *, nonempty=False):
    if not isinstance(value, str) or '\0' in value or '\r' in value:
        return False
    try:
        return int(nonempty) <= len(value.encode('utf-8')) <= limit
    except UnicodeError:
        return False


def load_job(raw, expected):
    if not match(SHA, expected) or sha(raw) != expected:
        raise ValueError('Pinned worker job differs')
    job = decode(raw, 8192)
    if (set(job) != JOB_FIELDS or job['protocol'] != 'stead.doc-worker-job/1'
            or any(not match(UUID, job[k]) for k in ('project_id', 'work_id', 'run_id', 'outcome_id'))
            or job['attempt'] not in ('1', '2', '3')
            or any(not match(SHA, job[k]) for k in ('run_contract_sha256', 'context_digest'))
            or job['recipe'] != RECIPE or not text(job['paragraph'], 4096, nonempty=True)
            or not uint(job['max_output_bytes'], positive=True)
            or int(job['max_output_bytes']) > MAX_MARKDOWN):
        raise ValueError('Unsupported bounded Doc worker job')
    return job


def context_target(raw, job):
    if domain_hash('stead.run-context/1', raw) != job['context_digest']:
        raise ValueError('Exact native context digest differs')
    value = decode(raw, MAX_CONTEXT)
    if (set(value) != CONTEXT_FIELDS or not all(isinstance(v, str) for v in value.values())
            or value['protocol'] != 'stead.run-context/1'
            or any(value[k] != job[k] for k in ('project_id', 'work_id'))
            or not uint(value['execution_contract_revision'], positive=True)
            or any(not match(SHA, value[k]) for k in ('execution_contract_digest', 'instructions_digest', 'runtime_policy_digest'))
            or not text(value['title'], 800, nonempty=True) or len(value['title']) > 200
            or any(ord(char) < 32 for char in value['title'])
            or any(not text(value[k], 8192) for k in ('description', 'acceptance_criteria'))):
        raise ValueError('Native context scope or closed fields differ')
    documents = decode(value['documents'].encode('utf-8'), MAX_CONTEXT)
    if not 1 <= len(documents) <= 4 or job['outcome_id'] not in documents:
        raise ValueError('Declared Doc output is missing')
    selected = None
    targets = set()
    for outcome, row in documents.items():
        if (not match(UUID, outcome) or not isinstance(row, dict)
                or set(row) != {'target', 'markdown'} or not text(row['target'], 2048)
                or not text(row['markdown'], MAX_MARKDOWN)):
            raise ValueError('Invalid exact context Doc')
        target = decode(row['target'].encode('utf-8'), 2048)
        if (set(target) != TARGET_FIELDS or not all(isinstance(v, str) for v in target.values())
                or target['kind'] != 'document' or target['project_id'] != job['project_id']
                or any(not match(UUID, target[k]) for k in ('collection_id', 'document_id'))
                or not uint(target['expected_revision'])):
            raise ValueError('Declared Doc target scope differs')
        key = (target['collection_id'], target['document_id'])
        if key in targets:
            raise ValueError('Duplicate context Doc target')
        targets.add(key)
        if target['expected_revision'] == '0':
            if row['markdown'] != '' or target['base_markdown_sha256'] != '':
                raise ValueError('New Doc has a conflicting base')
        elif (not match(SHA, target['base_markdown_sha256'])
              or sha(row['markdown'].encode('utf-8')) != target['base_markdown_sha256']
              or not row['markdown'].startswith(header(target['document_id']))):
            raise ValueError('Existing Doc bytes or canonical header differ')
        if outcome == job['outcome_id']:
            selected = target, row['markdown']
    return selected


def header(document):
    return '---\nid: ' + document + '\ntype: page\nstate: published\n---\n'


def edit(raw, job):
    target, source = context_target(raw, job)
    base = source or header(target['document_id'])
    # Exact existing bytes survive, including trailing spaces/newlines. The
    # recipe only appends text; input text is never evaluated as instructions.
    markdown = base + ('\n' if base.endswith('\n') else '\n\n') + job['paragraph'] + '\n'
    if len(markdown.encode('utf-8')) > int(job['max_output_bytes']):
        raise ValueError('Doc output exceeds the issued byte budget')
    return target, markdown


def private_input(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or before.st_mode & 0o077
                or not 0 < before.st_size <= limit):
            raise ValueError('Worker input must be private, owned and bounded')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise ValueError('Worker input changed during read')
        return raw


def namespaces():
    return {name: os.readlink('/proc/self/ns/' + name) for name in NAMESPACES}


def isolation(host):
    current = namespaces()
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    if (set(host) != set(current) or any(host[k] == current[k] for k in current)
            or [name for _, name in socket.if_nameindex()] != ['lo']
            or any(int(status[k].strip(), 16) for k in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd'))
            or status['NoNewPrivs'].strip() != '1'
            or set(os.environ) - {'LC_CTYPE', 'PWD'} or os.environ.get('PWD', '/tmp') != '/tmp'
            or any(Path(p).exists() for p in ('/home', '/root', '/etc', '/run', '/authority', '/piers'))
            or not os.statvfs('/input').f_flag & os.ST_RDONLY):
        raise ValueError('Doc worker isolation differs')
    return {'namespaces': current, 'interfaces': ['lo'], 'read_only_input': True, 'no_capabilities': True}


def child_command(stage, job_digest, host):
    command = ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--die-with-parent',
               '--clearenv', '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        value = Path('/') / name
        if value.is_symlink():
            command += ['--symlink', os.readlink(value), str(value)]
        elif value.exists():
            command += ['--ro-bind', str(value), str(value)]
    return command + ['--proc', '/proc', '--dev', '/dev', '--size', str(2 * 1024 * 1024),
                      '--tmpfs', '/tmp', '--ro-bind', str(stage), '/input', '--chdir', '/tmp',
                      '--', '/usr/bin/python3', '-I', '-S', '/input/worker.py', '_child',
                      job_digest, canonical(host).decode('ascii')]


def child(job_digest, host):
    for key, value in ((resource.RLIMIT_CPU, 2), (resource.RLIMIT_AS, 128 * 1024 * 1024),
                       (resource.RLIMIT_FSIZE, MAX_REPLY), (resource.RLIMIT_NOFILE, 32), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(key, (value, value))
    proof = isolation(host)
    job = load_job(Path('/input/job.json').read_bytes(), job_digest)
    target, markdown = edit(Path('/input/context.json').read_bytes(), job)
    return {'target': target, 'markdown': markdown, 'isolation': proof}


def write_new(directory, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def run(args):
    if os.getuid() == 0 or not sys.platform.startswith('linux'):
        raise ValueError('Use an admitted unprivileged Linux worker')
    source = Path(__file__).read_bytes()
    if not match(SHA, args.worker_sha256) or sha(source) != args.worker_sha256:
        raise ValueError('Doc worker source pin differs')
    job_raw = private_input(args.job, 8192)
    job = load_job(job_raw, args.job_sha256)
    context = private_input(args.context, MAX_CONTEXT)
    target, expected = edit(context, job)
    output = args.output.absolute()
    parent = output.parent.resolve(strict=True)
    if parent != output.parent or output.name in ('', '.', '..'):
        raise ValueError('Exact owned output directory required')
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Output parent must be private and owned')
        if os.path.lexists(output):
            raise ValueError('Output already exists; reconcile before another execution')
        host = namespaces()
        with tempfile.TemporaryDirectory(prefix='stead-doc-input-', dir=parent) as temporary:
            stage = Path(temporary)
            for name, raw in (('worker.py', source), ('job.json', job_raw), ('context.json', context)):
                (stage / name).write_bytes(raw)
                (stage / name).chmod(0o400)
            with tempfile.TemporaryFile(dir=stage) as stream:
                result = subprocess.run(child_command(stage, args.job_sha256, host), stdin=subprocess.DEVNULL,
                                        stdout=stream, stderr=subprocess.DEVNULL, check=False,
                                        timeout=10, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
                stream.seek(0)
                raw = stream.read(MAX_REPLY + 1)
        if result.returncode != 0:
            raise ValueError('Isolated Doc recipe did not finish')
        returned = decode(raw, MAX_REPLY)
        if (set(returned) != {'target', 'markdown', 'isolation'}
                or returned['target'] != target or returned['markdown'] != expected):
            raise ValueError('Isolated output differs from the pinned recipe and target')
        proof = returned['isolation']
        if (not isinstance(proof, dict) or set(proof) != {'namespaces', 'interfaces', 'read_only_input', 'no_capabilities'}
                or proof['interfaces'] != ['lo'] or proof['read_only_input'] is not True or proof['no_capabilities'] is not True
                or not isinstance(proof['namespaces'], dict) or set(proof['namespaces']) != set(host)
                or any(not isinstance(proof['namespaces'][k], str) or proof['namespaces'][k] == host[k] for k in host)):
            raise ValueError('Isolated output lacks its exact namespace proof')
        markdown = expected.encode('utf-8')
        receipt = {'protocol': 'stead.doc-worker-result/1', 'status': 'output-ready',
                   'job': job, 'job_sha256': args.job_sha256, 'worker_sha256': args.worker_sha256,
                   'context_digest': job['context_digest'], 'target': target,
                   'artifact': {'name': 'proposal.md', 'bytes': len(markdown), 'sha256': sha(markdown)},
                   'isolation': proof}
        os.mkdir(output.name, 0o700, dir_fd=directory)
        destination = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
        try:
            write_new(destination, 'proposal.md', markdown)
            # A partial directory is never a completed output. The supervisor
            # reconciles it explicitly; a rerun may not overwrite the evidence.
            write_new(destination, 'result.json', canonical(receipt))
            os.fsync(destination)
        finally:
            os.close(destination)
        os.fsync(directory)
        return receipt
    finally:
        os.close(directory)


def main():
    os.umask(0o077)
    if sys.argv[1:2] == ['_child']:
        if len(sys.argv) != 4:
            raise SystemExit(2)
        try:
            value = child(sys.argv[2], decode(sys.argv[3].encode('ascii'), 2048))
        except (OSError, ValueError, subprocess.SubprocessError):
            raise SystemExit(1)
        sys.stdout.buffer.write(canonical(value))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'context', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('job-sha256', 'worker-sha256'):
        parser.add_argument('--' + name, required=True)
    try:
        value = run(parser.parse_args())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Doc worker stopped: ' + type(error).__name__ + '\n')
    # Contents and the private receipt stay in the owned result directory.
    print(json.dumps({'status': value['status'], 'artifact_sha256': value['artifact']['sha256']}))


if __name__ == '__main__':
    main()

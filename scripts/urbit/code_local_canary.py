#!/usr/bin/env python3
"""Measure the guarded local Work/Docs client during stock Git traffic."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from math import ceil
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from threading import Event
import time

import digests
import execution_policy as guard
import portable_code as archive
import portable_import as importer
import portable_recovery as portable

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'https://home.localhost:8443'
GIT_VERSION = '2.55.0'
GIT_SHA = '93473c28694fd72bd889364107cd2770514de59780885a6a4aafca4d602e30ad'
HTTP_SHA = '23f747f69b5293b9f531cc17205eab792eb92075e92f99a8d6bc2b51cf007230'
ROUNDS = 3
PAIRS_PER_OPERATION = 2
OPERATIONS = ('push', 'fetch', 'clone')
KINDS = ('work', 'document')
COUNT = ROUNDS * len(OPERATIONS) * PAIRS_PER_OPERATION
DEADLINE = 105
WORKLOAD = {'rounds': ROUNDS, 'operations': list(OPERATIONS),
            'baseline_samples_per_kind': COUNT, 'loaded_samples_per_kind': COUNT,
            'deadline_seconds': DEADLINE, 'percentile': 'nearest-rank',
            'measurement': 'client TLS and correlated query response validation',
            'latency_gate': 'baseline measurement, no prequalified SLO'}


def require(condition, code):
    portable.require(condition, code)


def latency(windows):
    values = sorted((end - start) / 1_000_000 for start, end in windows)
    require(len(values) == COUNT and values[0] >= 0, 'sample-count')
    return {'samples': len(values), **{
        f'p{percentile}_ms': round(values[ceil(len(values) * percentile / 100) - 1], 3)
        for percentile in (50, 95, 99)}}


def sample(read, kind, windows):
    start = time.monotonic_ns()
    read(kind)
    windows[kind].append((start, time.monotonic_ns()))


def overlap(window, other):
    return max(window[0], other[0]) < min(window[1], other[1])


def measure(read, transfer, check):
    baseline = {kind: [] for kind in KINDS}
    for _ in range(COUNT):
        for kind in KINDS:
            sample(read, kind, baseline)
    loaded = {kind: [] for kind in KINDS}
    transfers, covered = [], dict.fromkeys(KINDS, 0)
    with ThreadPoolExecutor(max_workers=1) as worker:
        for turn in range(1, ROUNDS + 1):
            for index, operation in enumerate(OPERATIONS):
                check()
                started = Event()

                future = worker.submit(transfer, turn, operation, started)
                require(started.wait(timeout=3), 'transfer-start')
                counts = {kind: len(loaded[kind]) for kind in KINDS}
                # Alternate the first query type so both types get a sample
                # while the transfer is live even if a second query is slower.
                order = KINDS if (turn + index) % 2 else KINDS[::-1]
                for _ in range(PAIRS_PER_OPERATION):
                    for kind in order:
                        sample(read, kind, loaded)
                window, result = future.result()
                by_kind = {kind: sum(overlap(window, item) for item in loaded[kind][counts[kind]:])
                           for kind in KINDS}
                for kind in KINDS:
                    covered[kind] += by_kind[kind]
                transfers.append({'round': turn, 'operation': operation,
                                  'duration_ms': round((window[1] - window[0]) / 1_000_000, 3),
                                  'overlapping_queries': by_kind, **result})
    require(all(sum(item['overlapping_queries'].values()) > 0 for item in transfers)
            and all(covered.values()), 'workload-overlap')
    return {'baseline': {kind: latency(windows) for kind, windows in baseline.items()},
            'loaded': {kind: latency(windows) for kind, windows in loaded.items()},
            'overlapping_queries': covered, 'transfers': transfers}


class Admission:
    def __init__(self, control, run_id, ca):
        self.deadline = time.monotonic() + DEADLINE
        self.control, self.run_id = control.absolute(), run_id
        require(self.control.name == 'control' and self.control.parent.parent == ROOT / '.runtime/execution-runs',
                'owned-guard-control-required')
        self.context = self.control / 'source-context.json'
        raw = digests.read_source(self.context, maximum=4 * 1024 * 1024)
        context = portable.decoded(raw, 4 * 1024 * 1024)
        self.ca = ca.absolute()
        require(self.ca.name == 'ca.pem' and self.ca.parent.name == 'certificates'
                and self.ca.parents[1].name == run_id, 'fixture-ca-binding')
        names = ('code_local_canary.py', 'portable_code.py', 'portable_import.py', 'portable_recovery.py',
                 'execution_policy.py')
        self.helpers = {name: digests.sha(Path(__file__).parent / name) for name in names}
        require(context.get('profile') == 'configured-team' and portable.match(portable.OID, context.get('source_commit'))
                and all(context['script_files'].get(name) == digest for name, digest in self.helpers.items())
                and context['native_tree_sha256'] == digests.tree_sha(ROOT / 'native/core/desk'),
                'guard-source-binding')
        lease = self.check()
        self.bindings = {'run_id': run_id, 'source_commit': context['source_commit'],
                         'committed_bytes_verified': context.get('committed_bytes_verified') is True,
                         'native_tree_sha256': context['native_tree_sha256'],
                         'source_context_sha256': portable.sha(raw),
                         'guard_policy_sha256': lease['policy_sha256'],
                         'first_lease_generation': lease['generation'],
                         'ca_sha256': digests.sha(self.ca), 'helper_sha256': self.helpers,
                         'workload_sha256': portable.sha(portable.encoded(WORKLOAD))}

    def check(self):
        require(time.monotonic() < self.deadline, 'canary-deadline')
        return guard.require_lease(self.control, run_id=self.run_id)

    def closeout(self):
        lease = self.check()
        require(self.bindings['source_context_sha256'] == digests.sha(self.context)
                and self.bindings['ca_sha256'] == digests.sha(self.ca)
                and self.bindings['native_tree_sha256'] == digests.tree_sha(ROOT / 'native/core/desk')
                and all(digests.sha(Path(__file__).parent / name) == digest for name, digest in self.helpers.items())
                and lease['policy_sha256'] == self.bindings['guard_policy_sha256'],
                'input-binding-changed')
        return {**self.bindings, 'last_lease_generation': lease['generation']}


def read_request(kind, project, container, resource):
    return {'protocol': 'stead.query/3', 'request_id': portable.new_id(), 'kind': kind,
            'project_id': project, 'container_id': container, 'resource_id': resource,
            'search': '', 'cursor': ''}


def denied_private(reader, scope):
    result = portable.decoded(reader._post('/stead/api/query', read_request('document', *scope)))
    require(result == {'protocol': 'stead.result/3', 'status': 'rejected',
                       'error': 'denied_or_not_found'}, 'reader-private-denial')


def manage(home, project, action, **fields):
    value = portable.decoded(home._post('/stead/api/code', {'protocol': 'stead.code/1',
        'project_id': project, 'action': action, **fields}))
    require(value.get('protocol') == 'stead.code/1', 'code-response')
    return value


def fresh_project(home, member):
    project = portable.new_id()
    target = importer.target_member(member)
    command = {'protocol': 'stead.command/3', 'request_id': portable.new_id(),
               'project_id': project, 'resource_id': project, 'expected_revision': '0',
               'authority_epoch': '1', 'operation': 'project.create',
               'payload': {'organization_id': target['organization_id'], 'owning_team_id': target['team_id'],
                           'title': 'Synthetic Git workload', 'project_key': 'C' + project[-8:].upper(),
                           'preset': 'general'}}
    importer.checked_receipt(home.send(command), command, target, {portable.sha(member['session_audit_id'].encode())})
    require(manage(home, project, 'status')['status'] == 'disabled'
            and manage(home, project, 'create')['status'] == 'ready', 'code-canary-create')
    return project


class StockGit:
    def __init__(self, root, admission):
        self.root, self.admission = root, admission
        install = ROOT / '.runtime/tooling' / ('git-' + GIT_VERSION)
        self.binary = install / 'bin/git'
        helper = install / 'lib/git-core/git-remote-http'
        require(digests.sha(self.binary) == GIT_SHA and digests.sha(helper) == HTTP_SHA
                and (helper.parent / 'git-remote-https').resolve(strict=True) == helper, 'stock-git-pins')
        ask = root / 'askpass'
        ask.write_text("#!/bin/sh\ncase \"$1\" in Username*) printf 'stead\\n';; Password*) cat \"$STEAD_GIT_SECRET_FILE\";; *) exit 1;; esac\n")
        ask.chmod(0o700)
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C.UTF-8',
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                    'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_ALLOW_PROTOCOL': 'https',
                    'GIT_TERMINAL_PROMPT': '0', 'GIT_EXEC_PATH': str(helper.parent),
                    'GIT_SSL_CAINFO': str(admission.ca), 'GIT_ASKPASS': str(ask),
                    'GIT_AUTHOR_NAME': 'Stead Canary', 'GIT_AUTHOR_EMAIL': 'canary@stead.invalid',
                    'GIT_COMMITTER_NAME': 'Stead Canary', 'GIT_COMMITTER_EMAIL': 'canary@stead.invalid',
                    'GIT_AUTHOR_DATE': '1790520000 +0000', 'GIT_COMMITTER_DATE': '1790520000 +0000'}

    def run(self, *args, cwd=None, data=None, credential=None, started=None):
        self.admission.check()
        env = self.env if credential is None else self.env | {'STEAD_GIT_SECRET_FILE': str(credential)}
        argv = [self.binary, '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null',
                '-c', 'http.followRedirects=false', '-c', 'http.curloptResolve=home.localhost:8443:127.0.0.1',
                *args]
        start = time.monotonic_ns()
        with subprocess.Popen(argv, env=env, cwd=cwd or self.root, start_new_session=True,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as child:
            if started is not None:
                started.set()
            try:
                output, _ = child.communicate(data, timeout=min(12, max(.01, self.admission.deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                raise portable.RecoveryError('stock-git-timeout') from None
            end = time.monotonic_ns()
            require(child.returncode == 0 and len(output) <= 8192, 'stock-git-operation')
        return (start, end) if started is not None else output


class GitWorkload:
    def __init__(self, git, project, reader, writer):
        self.git, self.reader, self.writer = git, reader, writer
        self.url = f'{ORIGIN}/stead/git/{project}.git'
        self.source = git.root / 'source.git'
        self.fetched = git.root / 'fetched.git'
        self.commits = []
        for repo in (self.source, self.fetched):
            git.run('init', '--bare', '--template=', '--object-format=sha1', repo)
        for turn in range(1, ROUNDS + 1):
            cwd = self.source
            blob = git.run('hash-object', '-w', '--stdin', cwd=cwd, data=f'canary turn {turn}\0\n'.encode()).strip()
            tree = git.run('mktree', cwd=cwd, data=b'100644 blob ' + blob + b'\tcanary.txt\n').strip()
            prior = ['-p', self.commits[-1]] if self.commits else []
            commit = git.run('commit-tree', tree, *prior, '-m', f'Canary turn {turn}', cwd=cwd).strip().decode('ascii')
            require(portable.match(portable.OID, commit), 'synthetic-commit')
            self.commits.append(commit)

    def transfer(self, turn, operation, started):
        oid = self.commits[turn - 1]
        git = self.git
        if operation == 'push':
            git.run('update-ref', 'refs/heads/main', oid, cwd=self.source)
            tag = f'refs/tags/v{turn}'
            git.run('update-ref', tag, oid, cwd=self.source)
            window = git.run('push', '--atomic', self.url, 'refs/heads/main', tag,
                             cwd=self.source, credential=self.writer, started=started)
        elif operation == 'fetch':
            window = git.run('fetch', '--no-tags', self.url, 'refs/heads/main:refs/heads/main',
                             cwd=self.fetched, credential=self.reader, started=started)
            require(git.run('rev-parse', 'refs/heads/main', cwd=self.fetched).strip().decode('ascii') == oid,
                    'fetched-oid')
        else:
            clone = git.root / f'clone-{turn}.git'
            window = git.run('clone', '--bare', '--template=', self.url, clone,
                             credential=self.reader, started=started)
            actual = git.run('for-each-ref', '--format=%(refname) %(objectname)', cwd=clone)
            expected = f'refs/heads/main {oid}\n' + ''.join(
                f'refs/tags/v{index} {tip}\n' for index, tip in enumerate(self.commits[:turn], 1))
            require(actual == expected.encode('ascii'), 'cloned-refs')
            git.run('fsck', '--full', '--strict', cwd=clone)
        label = 'pushed_head_oid' if operation == 'push' else 'observed_head_oid'
        return window, {label: oid}


def credential(home, project, access, path, handles):
    value = manage(home, project, 'issue', access=access)
    require(portable.match(portable.TOKEN, value.get('bearer'))
            and portable.match(portable.TOKEN, value.get('handle')), 'git-credential')
    handles.append(value['handle'])
    path.write_text(value['bearer'] + '\n')
    return path


def run(args):
    scope = (args.project, args.work, args.container, args.document, args.private_container, args.private_document)
    require(all(portable.match(portable.UUID, value) for value in scope)
            and args.container != args.private_container, 'workload-scope')
    admission = Admission(args.guard_control, args.run_id, args.ca_file)
    owner, reader = [importer.LocalHome(portable.session_file(path), ca_file=admission.ca)
                     for path in (args.owner_session, args.reader_session)]
    for member in (owner, reader):
        require(member.credentials['origin'] == ORIGIN, 'fixture-origin')
        member.deadline = member.read.deadline = admission.deadline
    owner_member, reader_member = owner.member(), reader.member()
    require(owner_member['home'] == reader_member['home'] == '~zod'
            and owner_member['principal_id'] != reader_member['principal_id']
            and owner_member['identity_ship'] != reader_member['identity_ship'], 'independent-sessions')
    require(owner.read.one('project', args.project)[1]['role'] == 'maintainer'
            and reader.read.one('project', args.project)[1]['role'] == 'reader', 'workload-roles')
    items = {'work': (args.project, '', args.work),
             'document': (args.project, args.container, args.document)}
    baseline = {kind: owner.read.one(kind, *item) for kind, item in items.items()}
    require(baseline['document'][1].get('visibility') == 'shared', 'shared-document-required')
    private = (args.project, args.private_container, args.private_document)
    require(owner.read.one('document', *private)[1].get('visibility') == 'private', 'private-document-required')

    def verify_reader():
        for kind, item in items.items():
            stamp, row = reader.read.one(kind, *item)
            require((stamp[0], row) == (baseline[kind][0][0], baseline[kind][1]), 'reader-content')
        denied_private(reader, private)

    def read(kind):
        admission.check()
        require(owner.read.one(kind, *items[kind]) == baseline[kind], 'measured-content-changed')

    verify_reader()
    project = fresh_project(owner, owner_member)
    with closing(owner._connection(5)) as conn:
        conn.request('GET', f'/stead/git/{project}.git/info/refs?service=git-upload-pack')
        require(conn.getresponse().status == 401, 'anonymous-git-denial')
    with tempfile.TemporaryDirectory(prefix='stead-code-canary-') as scratch:
        root, handles = Path(scratch), []
        git = StockGit(root, admission)
        try:
            read_key = credential(owner, project, 'read', root / 'read-secret', handles)
            write_key = credential(owner, project, 'write', root / 'write-secret', handles)
            workload = GitWorkload(git, project, read_key, write_key)
            measurements = measure(read, workload.transfer, admission.check)
            value = archive.collect(root / f'clone-{ROUNDS}.git', project, str(git.binary),
                                    deadline=admission.deadline)
            archive.restore(value, root / 'restored.git', str(git.binary), deadline=admission.deadline)
            portable_result = {'sha256': portable.sha(portable.encoded(value)),
                               'refs': len(value['refs']), 'objects': len(value['objects'])}
            verify_reader()
        finally:
            revoked = []
            for handle in handles:
                try:
                    revoked.append(manage(owner, project, 'revoke', handle=handle)['status'] == 'revoked')
                except (portable.RecoveryError, OSError, KeyError):
                    revoked.append(False)
            require(all(revoked), 'git-credential-revocation')
    return {'status': 'pass', 'profile': 'single-host-disposable-configured-fixture',
            'inputs': admission.closeout() | {'scope_sha256': portable.sha(portable.encoded(scope)),
                                               'git_sha256': GIT_SHA, 'git_http_helper_sha256': HTTP_SHA},
            'workload': WORKLOAD, 'measurements': measurements,
            'checks': ['independent maintainer and reader', 'reader private denial before and after',
                       'anonymous Git denial', 'read/write credential revocation',
                       'verified Code archive restored from measured TLS clone'],
            'code_archive': portable_result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('owner-session', 'reader-session', 'guard-control', 'ca-file'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('run-id', 'project', 'work', 'container', 'document', 'private-container', 'private-document'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except portable.RecoveryError as error:
        reason = str(error)
    except (OSError, ValueError, guard.GuardError, subprocess.SubprocessError, KeyError, TypeError):
        reason = 'local-fixture-boundary'
    print(json.dumps({'status': 'fail', 'reason': reason, 'workload': WORKLOAD}, sort_keys=True))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

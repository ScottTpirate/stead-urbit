#!/usr/bin/env python3
"""Rehearse a stock Git push as a private, immutable Stead candidate."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Thread
import time

import dogfood_rehearsal as local
from execution_policy import directory_fd
import git_pack_proof as proof
import git_pack_receive as receive
import git_pack_store as store
from portable_code import private_directory, staged_repository
from portable_recovery import decoded, encoded, new_id, require, sha


FORMAT = 'stead.git-pack-wire-rehearsal/1'
TAG = 'refs/tags/stead-synthetic-wire-rehearsal'
SCOPE = dict.fromkeys(('project_id', 'repository_id'), '019939ba-4000-7000-8000-000000000811') | {
    'home': '~zod', 'authority_epoch': '1',
}
ACTOR = {'identity_ship': '~bus', 'principal_id': '019939ba-4000-7000-8000-000000000802',
         'binding_id': '019939ba-4000-7000-8000-000000000803', 'binding_revision': '1'}


def packet(payload):
    return f'{len(payload) + 4:04x}'.encode('ascii') + payload


def write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def run_push(client, refs, output, branch):
    """A local peer captures the stock HTTP request and rejects acceptance."""
    service = '/rehearsal.git'
    rows = []
    for index, (ref, oid) in enumerate(sorted(refs.items())):
        capability = b'\0report-status atomic ofs-delta object-format=sha1' if index == 0 else b''
        rows.append(packet(oid.encode('ascii') + b' ' + os.fsencode(ref) + capability + b'\n'))
    advertised = packet(b'# service=git-receive-pack\n') + b'0000' + b''.join(rows) + b'0000'
    refusal = packet(b'unpack rehearsal records wire only\n') + b'0000'

    class Peer(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, *_):
            pass

        def reply(self, subtype, body):
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-git-receive-pack-' + subtype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != service + '/info/refs?service=git-receive-pack':
                return self.send_error(404)
            self.reply('advertisement', advertised)

        def do_POST(self):
            lengths = self.headers.get_all('Content-Length', [])
            if (self.path != service + '/git-receive-pack' or 'Transfer-Encoding' in self.headers
                    or len(lengths) != 1 or re.fullmatch(r'[1-9][0-9]{0,7}', lengths[0]) is None
                    or int(lengths[0]) > receive.MAX_WIRE
                    or self.headers.get('Content-Type', '') != 'application/x-git-receive-pack-request'):
                return self.send_error(400)
            length = int(lengths[0])
            body = self.rfile.read(length)
            if len(body) != length:
                return self.send_error(400)
            try:
                write_private(output, body)
            except FileExistsError:
                return self.send_error(409)
            self.reply('result', refusal)

    with HTTPServer(('127.0.0.1', 0), Peer) as server:
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05})
        thread.start()
        try:
            remote = f'http://127.0.0.1:{server.server_port}{service}'
            command = [client.binary, '-C', client.path, '-c', 'core.hooksPath=/dev/null',
                       '-c', 'pack.threads=1', '-c', 'push.gpgSign=false', 'push', '--atomic', remote,
                       f'{branch}:{branch}', f'{TAG}:{TAG}']
            result = subprocess.run(command, env=local.ENV | {'GIT_ALLOW_PROTOCOL': 'http'},
                                    capture_output=True, timeout=30, umask=0o077)
        finally:
            server.shutdown()
            thread.join(10)
    require(not thread.is_alive() and result.returncode != 0
            and b'rehearsal records wire only' in result.stderr and output.is_file(), 'rehearsal-wire-capture')


def pack_base(git, output, refs):
    git_directory = git.run('rev-parse', '--absolute-git-dir').stdout.strip()
    roots = ''.join(f'{oid}\n' for oid in sorted(set(refs.values()))).encode('ascii')
    with directory_fd(output.parent) as parent:
        with staged_repository(parent, git.binary, command_prefix=store.GIT_LIMITS) as (_, _, worker):
            fd = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            with os.fdopen(fd, 'wb') as packed:
                worker.run_to(packed, '--git-dir=' + os.fsdecode(git_directory), 'pack-objects', '--stdout',
                              '--revs', '--threads=1', '--delta-base-offset', data=roots, limit=store.MAX_PACK)
    return local.bundle_digest(output)['sha256']


def reachable(git, refs):
    roots = ''.join(f'{oid}\n' for oid in sorted(set(refs.values()))).encode('ascii')
    rows = git.run('rev-list', '--objects', '--no-object-names', '--stdin', data=roots).stdout.splitlines()
    require(0 < len(rows) <= store.MAX_OBJECTS and len(set(rows)) == len(rows), 'rehearsal-object-inventory')
    return set(rows)


def admission(scope, snapshot, wire, changes, now):
    return encoded({'protocol': proof.ADMISSION, 'scope': scope, 'base_snapshot': snapshot, 'generation': '0',
                    'attempt': '1', 'incarnation': sha(b'local synthetic rehearsal only'), 'request_id': new_id(),
                    'actor': ACTOR, 'wire_sha256': sha(wire), 'update_count': str(len(changes)),
                    'changes': {f'{index:02d}': change for index, change in enumerate(changes)},
                    'admitted_at_ms': str(now), 'expires_at_ms': str(now + 300_000)})


def rehearse(source, output, git, refs, branch):
    repository = local.Git(git, source.resolve(strict=True))
    local.validate_source(repository, refs, branch)
    source_refs = repository.refs()
    require({name: oid for name, oid in source_refs.items() if name.startswith(local.REF_PREFIXES)} == refs
            and TAG not in refs, 'pin-all-source-refs')
    with directory_fd(output.parent) as parent:
        private_directory(parent)
        os.mkdir(output.name, mode=0o700, dir_fd=parent)
    output = output.resolve(strict=True)
    storage = output / 'store'
    storage.mkdir(mode=0o700)
    head = os.fsencode(branch).hex()
    encoded_refs = {os.fsencode(ref).hex(): oid for ref, oid in refs.items()}
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=output) as temporary:
        scratch = Path(temporary)
        pack = scratch / 'base.pack'
        digest = pack_base(repository, pack, refs)
        snapshot, base = store.stage(storage, pack, digest, SCOPE, encoded_refs, head, git)
        client = local.Git(git, scratch / 'client.git')
        require(store.restore(storage, snapshot, SCOPE, client.path, git) == base, 'rehearsal-base-differs')
        original_objects = reachable(client, refs)
        tip = local.add_test_commit(client, branch, refs[branch], 'Synthetic external Git wire rehearsal')
        client.run('tag', '-a', TAG.removeprefix('refs/tags/'), '-m', 'Synthetic external Git rehearsal tag', tip)
        tag_oid = client.run('rev-parse', TAG).stdout.strip().decode('ascii')
        wire = output / 'receive.wire'
        run_push(client, refs, wire, branch)
        capture = wire.read_bytes()
        changes, pack_bytes = receive.parse(capture)
        require({(change['ref'], change['prior'], change['target']) for change in changes} == {
            (head, refs[branch], tip), (TAG.encode().hex(), '0' * 40, tag_oid),
        }, 'rehearsal-wire-refs')
        clock = lambda: time.time_ns() // 1_000_000
        admitted = admission(SCOPE, snapshot, capture, changes, clock())
        write_private(output / 'admission.json', admitted)
        body = proof.prepare(admitted, sha(admitted), storage, wire, git, now_ms=clock)
        write_private(output / 'worker-proof.json', body)
        result = decoded(body)
        restored = local.Git(git, scratch / 'restored.git')
        manifest = store.restore(storage, result['candidate_snapshot'], SCOPE, restored.path, git)
        expected_refs = refs | {branch: tip, TAG: tag_oid}
        require(restored.refs() == expected_refs, 'rehearsal-candidate-refs')
        require(restored.run('symbolic-ref', 'HEAD').stdout.rstrip(b'\n') == os.fsencode(branch), 'rehearsal-head')
        restored.run('fsck', '--full', '--strict', '--no-reflogs', '--no-dangling')
        candidate_objects = reachable(restored, expected_refs)
        require(candidate_objects == original_objects | {tip.encode('ascii'), tag_oid.encode('ascii')}
                and len(candidate_objects) == len(original_objects) + 2, 'rehearsal-object-inventory')
        require(sha(b'\n'.join(sorted(candidate_objects)) + b'\n') == manifest['object_ids_sha256'],
                'rehearsal-candidate-inventory')
    local.validate_source(repository, refs, branch)
    require(repository.refs() == source_refs, 'rehearsal-source-refs-changed')
    report = {'protocol': FORMAT, 'status': 'passed', 'classification': 'offline-synthetic-no-home-acceptance',
              'git_version': repository.run('--version').stdout.decode('ascii').strip(),
              'base_snapshot': snapshot, 'base_manifest': base, 'candidate_snapshot': result['candidate_snapshot'],
              'candidate_manifest': manifest, 'wire_pack_bytes': len(pack_bytes), 'updates': result['updates'],
              'artifacts': [local.bundle_digest(output / name) for name in
                            ('receive.wire', 'admission.json', 'worker-proof.json')],
              'checks': {'stock_push_rejected': True, 'strict_fsck': True, 'source_refs_unchanged': True,
                         'original_reachable_oids_preserved': True, 'synthetic_commit_and_tag_only': True}}
    raw = encoded(report)
    write_private(output / 'report.json', raw)
    write_private(output / 'report.sha256', (sha(raw) + '  report.json\n').encode('ascii'))
    return sha(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='New directory inside a private output parent')
    parser.add_argument('--ref', action='append', required=True, metavar='REF=OID', help='Pin each source branch and tag')
    parser.add_argument('--default-branch', default='refs/heads/main')
    parser.add_argument('--git', default='git', help='Stock Git executable')
    args = parser.parse_args()
    try:
        binary = shutil.which(args.git)
        require(binary is not None, 'rehearsal-git-required')
        refs = {}
        for item in args.ref:
            name, separator, oid = item.rpartition('=')
            require(separator and name not in refs, 'supply-each-ref-once')
            refs[name] = oid
        digest = rehearse(args.source, args.output, Path(binary).resolve(strict=True), refs, args.default_branch)
        print(f'{digest}  {args.output / "report.json"}')
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()

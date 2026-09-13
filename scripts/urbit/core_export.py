"""Materialize authorized home-created objects; stock Git never authors a save."""
from __future__ import annotations
import hashlib
import re
import subprocess
from pathlib import Path

OID = re.compile(r'[0-9a-f]{40}')
FILE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.md')


def export(call, destination, ship, project, container, snapshot=None):
    destination = Path(destination)
    destination.mkdir(mode=0o700)
    environment = {'PATH':'/usr/bin:/bin', 'LANG':'C.UTF-8', 'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_GLOBAL':'/dev/null'}
    records = []
    native = []
    def git(*args, data=None):
        argv = ['git', '-C', str(destination), *args]
        result = subprocess.run(argv, input=data, capture_output=True, env=environment, timeout=30)
        record = {'argv': argv, 'returncode':result.returncode, 'stdout':result.stdout.decode('utf-8', errors='replace'), 'stderr':result.stderr.decode('utf-8', errors='replace')}
        records.append(record)
        if result.returncode:
            raise AssertionError(record)
        return result.stdout
    def read(path):
        result = call(ship, 'read', path)
        native.append(result)
        envelope = result['json']
        if not isinstance(envelope, dict) or envelope.get('status') != 'read':
            raise AssertionError('Authorized export read failed: ' + path)
        if (envelope.get('protocol') != 'stead.result/1'
                or envelope.get('project_id') != project
                or envelope.get('resource_id') != container):
            raise AssertionError('Export response scope/protocol mismatch: ' + path)
        return envelope['payload']
    manifest = read(f'/v1/git/{project}/{container}')
    head = snapshot or manifest['snapshot_commit_oid']
    if not OID.fullmatch(head):
        raise ValueError('Bad snapshot OID')
    git('init', '--bare', '--template=')
    pending = [(head, 'commit')]
    objects = {}
    while pending:
        oid, expected_kind = pending.pop()
        if not OID.fullmatch(oid):
            raise ValueError('Invalid graph reference')
        if oid in objects:
            if objects[oid]['kind'] != expected_kind:
                raise ValueError('Contradictory graph object type')
            continue
        if len(objects) >= 512:
            raise ValueError('Export graph bound')
        obj = read(f'/v1/git-object/{project}/{container}/{head}/{oid}')
        if obj['oid'] != oid or obj['snapshot_commit_oid'] != head or obj['kind'] != expected_kind:
            raise AssertionError('Object identity/type changed')
        body = bytes.fromhex(obj['hex'])
        if len(body) != int(obj['byte_length']) or len(body) > 65536:
            raise AssertionError('Object byte length')
        header = f'{expected_kind} {len(body)}\0'.encode()
        if hashlib.sha1(header + body).hexdigest() != oid:
            raise AssertionError('Independent Git object digest differs')
        if git('hash-object', '-w', '-t', expected_kind, '--stdin', data=body).decode().strip() != oid:
            raise AssertionError('Stock Git object ID differs')
        objects[oid] = {'kind':expected_kind, 'byte_length':len(body), 'hex':body.hex()}
        if expected_kind == 'commit':
            headers = body.split(b'\n\n', 1)[0].decode('ascii').splitlines()
            tree = [line[5:] for line in headers if line.startswith('tree ')]
            parents = [line[7:] for line in headers if line.startswith('parent ')]
            if len(tree) != 1 or len(parents) > 1:
                raise ValueError('Unsupported commit graph')
            pending.extend((value, 'commit') for value in parents)
            pending.append((tree[0], 'tree'))
        elif expected_kind == 'tree':
            rest = body
            entry_count = 0
            while rest:
                entry_count += 1
                if entry_count > 32:
                    raise ValueError('Export tree entry bound')
                header, rest = rest.split(b'\0', 1)
                mode, name = header.split(b' ', 1)
                if mode != b'100644' or not FILE.fullmatch(name.decode('ascii')) or len(rest) < 20:
                    raise ValueError('Unsupported tree entry')
                pending.append((rest[:20].hex(), 'blob'))
                rest = rest[20:]
    if snapshot is None and {oid: obj['kind'] for oid, obj in objects.items()} != manifest['objects']:
        raise AssertionError('Current manifest differs from independently traversed graph')
    git('symbolic-ref', 'HEAD', 'refs/heads/main')
    git('update-ref', 'refs/heads/main', head)
    git('fsck', '--full', '--strict')
    fsck = records[-1]
    files = {}
    for entry in git('ls-tree', '-rz', head).split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, kind, oid_raw = meta.decode('ascii').split()
        name = name.decode('ascii')
        if mode != '100644' or kind != 'blob' or not FILE.fullmatch(name):
            raise ValueError('Unexpected exported file')
        body = git('cat-file', 'blob', oid_raw)
        if body.hex() != objects[oid_raw]['hex']:
            raise AssertionError('Stock Git recovered bytes differ')
        files[name] = {'oid':oid_raw, 'hex':body.hex()}
    return {'snapshot_commit_oid':head, 'objects':objects, 'files':files, 'fsck':fsck,
            'max_response_bytes':max(len(r['raw'].encode()) for r in native),
            'native':native, 'git_commands':records}

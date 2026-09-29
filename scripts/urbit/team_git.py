"""Stock Git checks of observed configured Home objects; no Git write API."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

import core_conn
import owned_child
import execution_policy
from digests import source_sha, tree_sha

OID = re.compile(r'[0-9a-f]{40}')
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
KINDS = {'commit', 'tree', 'blob'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate native Git observation key')
        value[key] = item
    return value


def observe(dojo, project, container, head, oid=None):
    require(UUID.fullmatch(project) and UUID.fullmatch(container) and OID.fullmatch(head)
            and (oid is None or OID.fullmatch(oid)), 'Fixed synthetic Git input grammar')
    mode = 'manifest' if oid is None else 'object'
    # Git OIDs stay exact lowercase hex strings outside the typed Hoon call.
    # Its @ux literals require grouped digits and no leading numeric zeroes.
    head_atom = core_conn.atom(int(head, 16).to_bytes(20, 'little'))
    object_atom = core_conn.atom(int(oid or '0', 16).to_bytes(20, 'little'))
    expression = f"+stead-team-git-export [%{mode} '{project}' '{container}' {head_atom} {object_atom}]"
    result = dojo('zod', expression)
    require(isinstance(result, str) and len(result) <= 524288, 'Native Git observation bound')
    token = ''.join(result.split())
    require(re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', token), 'Native Git observation is not one atom')
    number = int(token.replace('.', ''), 16)
    length = (number.bit_length() + 7) // 8
    require(0 < length <= 196608, 'Native Git observation decoded bound')
    value = json.loads(number.to_bytes(length, 'little').decode('utf-8'), object_pairs_hook=unique)
    require(isinstance(value, dict), 'Native Git observation shape')
    return value


def probe(dojo, project, container, head):
    """Exercise the native manifest and commit paths before browser startup.

    This binds the observed commit to an actual accepted receipt. It does not
    replace stock Git verification of the complete browser-created histories.
    """
    manifest = observe(dojo, project, container, head)
    require(set(manifest) == {'protocol', 'project_id', 'container_id', 'snapshot_commit_oid', 'objects'}
            and manifest['protocol'] == 'stead.fixture-git/3' and manifest['project_id'] == project
            and manifest['container_id'] == container and manifest['snapshot_commit_oid'] == head,
            'Native Git probe manifest correlation')
    objects = manifest['objects']
    require(isinstance(objects, dict) and 1 <= len(objects) <= 512
            and all(OID.fullmatch(oid) and kind in KINDS for oid, kind in objects.items())
            and objects.get(head) == 'commit', 'Native Git probe manifest bounds')
    value = observe(dojo, project, container, head, head)
    require(set(value) == {'protocol', 'snapshot_commit_oid', 'oid', 'kind', 'byte_length', 'hex'}
            and value['protocol'] == 'stead.fixture-git-object/3' and value['snapshot_commit_oid'] == head
            and value['oid'] == head and value['kind'] == 'commit', 'Native Git probe object correlation')
    size, encoded = value['byte_length'], value['hex']
    require(isinstance(size, str) and re.fullmatch(r'[1-9][0-9]{0,4}', size)
            and int(size) <= 65536 and isinstance(encoded, str) and len(encoded) == int(size) * 2
            and re.fullmatch(r'(?:[0-9a-f]{2})+', encoded), 'Native Git probe object byte grammar')
    body = bytes.fromhex(encoded)
    require(hashlib.sha1(f'commit {len(body)}\0'.encode() + body).hexdigest() == head,
            'Native Git probe commit differs from accepted receipt')
    return {'project_id': project, 'container_id': container, 'head': head,
            'declared_objects': len(objects), 'commit_bytes': len(body), 'commit_sha1': head}


def materialize(read, directory, project, container, head):
    """Traverse independently; bytes come only from the native observation hook."""
    require(UUID.fullmatch(project) and UUID.fullmatch(container) and OID.fullmatch(head), 'Git scope grammar')
    manifest = read(None)
    require(set(manifest) == {'protocol', 'project_id', 'container_id', 'snapshot_commit_oid', 'objects'}
            and manifest['protocol'] == 'stead.fixture-git/3' and manifest['project_id'] == project
            and manifest['container_id'] == container and manifest['snapshot_commit_oid'] == head,
            'Configured Git manifest correlation')
    declared = manifest['objects']
    require(isinstance(declared, dict) and 1 <= len(declared) <= 512
            and all(OID.fullmatch(oid) and kind in KINDS for oid, kind in declared.items()), 'Git manifest bounds')
    directory = Path(directory)
    directory.mkdir(mode=0o700)
    records = []
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}

    def git(*args, data=None):
        result = subprocess.run(owned_child.fixture_command(['/usr/bin/git', '-C', str(directory), *args]),
            input=data, capture_output=True, env=environment, timeout=30)
        require(len(result.stdout) <= 1048576 and len(result.stderr) <= 65536, 'Stock Git output bound')
        records.append({'arguments': list(args), 'returncode': result.returncode,
                        'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                        'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
        require(result.returncode == 0, 'Stock Git check failed')
        return result.stdout

    git('init', '--bare', '--template=', '--object-format=sha1')
    pending = [(head, 'commit')]
    objects, total = {}, 0
    while pending:
        oid, kind = pending.pop()
        require(OID.fullmatch(oid) and declared.get(oid) == kind, 'Undeclared or contradictory Git edge')
        if oid in objects:
            require(objects[oid]['kind'] == kind, 'Contradictory Git type')
            continue
        require(len(objects) < 512, 'Git closure count bound')
        value = read(oid)
        require(set(value) == {'protocol', 'snapshot_commit_oid', 'oid', 'kind', 'byte_length', 'hex'}
                and value['protocol'] == 'stead.fixture-git-object/3' and value['snapshot_commit_oid'] == head
                and value['oid'] == oid and value['kind'] == kind, 'Native Git object correlation')
        size, encoded = value['byte_length'], value['hex']
        require(isinstance(size, str) and re.fullmatch(r'0|[1-9][0-9]{0,4}', size)
                and int(size) <= 65536 and isinstance(encoded, str) and len(encoded) == int(size) * 2
                and re.fullmatch(r'(?:[0-9a-f]{2})*', encoded), 'Native Git object byte grammar')
        body = bytes.fromhex(encoded)
        total += len(body)
        require(total <= 8 * 1024 * 1024, 'Git closure byte bound')
        require(hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest() == oid,
                'Observed object digest differs')
        require(git('hash-object', '-w', '-t', kind, '--stdin', data=body).decode().strip() == oid,
                'Stock Git object identity differs')
        objects[oid] = {'kind': kind, 'body': body}
        if kind == 'commit':
            headers = body.split(b'\n\n', 1)[0].decode('ascii').splitlines()
            trees = [line[5:] for line in headers if line.startswith('tree ')]
            parents = [line[7:] for line in headers if line.startswith('parent ')]
            require(len(trees) == 1 and len(parents) <= 1, 'Unsupported Git commit graph')
            pending.extend((parent, 'commit') for parent in parents)
            pending.append((trees[0], 'tree'))
        elif kind == 'tree':
            rest, names = body, set()
            while rest:
                header, rest = rest.split(b'\0', 1)
                mode, name = header.split(b' ', 1)
                require(mode == b'100644' and name.endswith(b'.md')
                        and UUID.fullmatch(name[:-3].decode('ascii')) and len(rest) >= 20
                        and name not in names and len(names) < 32, 'Unsupported Git tree entry')
                names.add(name)
                pending.append((rest[:20].hex(), 'blob'))
                rest = rest[20:]
    require({oid: row['kind'] for oid, row in objects.items()} == declared, 'Manifest contains unreachable objects')
    git('symbolic-ref', 'HEAD', 'refs/heads/main')
    git('update-ref', 'refs/heads/main', head)
    git('fsck', '--full', '--strict')
    commits = git('rev-list', '--parents', head).decode('ascii').splitlines()
    require(1 <= len(commits) <= 128, 'Git history bound')
    require({line.split()[0] for line in commits} == {oid for oid, row in objects.items() if row['kind'] == 'commit'},
            'Stock Git ancestry differs from observed closure')
    files = {}
    for item in git('ls-tree', '-rz', head).split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, oid = metadata.decode('ascii').split()
        require(mode == '100644' and kind == 'blob' and name.endswith(b'.md')
                and UUID.fullmatch(name[:-3].decode('ascii')), 'Stock Git file shape')
        recovered = git('cat-file', 'blob', oid)
        require(recovered == objects[oid]['body'], 'Stock Git recovered bytes differ')
        files[name.decode('ascii')] = recovered
    return {'head': head, 'objects': objects, 'files': files, 'commits': commits,
            'object_bytes': total, 'commands': records, 'git_version': git('--version').decode().strip()}


def verify_publication(source, published, edited, fixture):
    source_spec, destination = fixture['source'], fixture['destination']
    source_files = {name: text.encode('utf-8') for name, text in source_spec['files'].items()}
    public_name = destination['document_id'] + '.md'
    require(source['files'] == source_files, 'Private Git snapshot differs from exact browser Markdown')
    require(published['files'] == {public_name: destination['published_markdown'].encode('utf-8')},
            'Publication tree differs from selected canonical Markdown')
    require(edited['files'] == {public_name: destination['edited_markdown'].encode('utf-8')},
            'Edited Git tree differs from exact browser Markdown')
    heads = source_spec['commits']
    require(source['commits'] == [heads[0] + ' ' + heads[1], heads[1] + ' ' + heads[2], heads[2]],
            'Private source ancestry differs from the three browser receipts')
    require(published['commits'] == [destination['published_head']], 'Publication inherited private ancestry')
    require(edited['commits'] == [destination['edited_head'] + ' ' + destination['published_head'],
                                destination['published_head']], 'Shared edit ancestry differs from browser receipts')
    require(set(published['objects']) <= set(edited['objects']), 'Shared edit lost publication history')
    private_blobs = {oid for oid, row in source['objects'].items() if row['kind'] == 'blob'}
    forbidden = [b'UNSELECTED-PRIVATE-CANARY', source_spec['container_id'].encode(),
                 *(name[:-3].encode() for name in source_files), *(head.encode() for head in heads)]
    require(not (private_blobs & set(edited['objects'])) and not (set(heads) & set(edited['objects'])),
            'Private source object entered public history')
    for row in edited['objects'].values():
        require(not any(value in row['body'] for value in forbidden), 'Private canary or source provenance in public history')
    require(any(b'UNSELECTED-PRIVATE-CANARY' in row['body'] for row in source['objects'].values()),
            'Private source positive canary absent')
    return {'exact_receipt_oids': True, 'exact_markdown_and_trees': True,
            'destination_only_ancestry': True, 'private_history_excluded': True}


def validate_fixture(value, execution_id):
    require(isinstance(value, dict) and set(value) == {'format', 'execution_id', 'project_id', 'source', 'destination'}
            and value['format'] == 'stead.browser-git-fixture/1' and value['execution_id'] == execution_id
            and isinstance(value['project_id'], str) and UUID.fullmatch(value['project_id']), 'Browser Git fixture identity')
    source, destination = value['source'], value['destination']
    require(isinstance(source, dict) and set(source) == {'container_id', 'commits', 'files'}
            and isinstance(destination, dict) and set(destination) == {'container_id', 'document_id',
                'published_head', 'edited_head', 'published_markdown', 'edited_markdown'}, 'Browser Git fixture fields')
    require(all(isinstance(item, str) and UUID.fullmatch(item) for item in
        (source['container_id'], destination['container_id'], destination['document_id']))
        and source['container_id'] != destination['container_id'], 'Browser Git scope identity')
    require(isinstance(source['commits'], list) and len(source['commits']) == 3
            and all(isinstance(item, str) and OID.fullmatch(item) for item in source['commits'])
            and len(set(source['commits'])) == 3, 'Private browser receipt history')
    require(isinstance(source['files'], dict) and len(source['files']) == 2
            and all(name.endswith('.md') and UUID.fullmatch(name[:-3]) and isinstance(body, str)
                    and len(body.encode('utf-8')) <= 16384 for name, body in source['files'].items()), 'Browser Git document bounds')
    for key in ('published_head', 'edited_head'):
        require(isinstance(destination[key], str) and OID.fullmatch(destination[key]), 'Public browser Git receipt')
    require(destination['published_head'] != destination['edited_head'], 'Shared edit must have a new Git head')
    for key in ('published_markdown', 'edited_markdown'):
        require(isinstance(destination[key], str) and len(destination[key].encode('utf-8')) <= 16384,
                'Browser Git Markdown bounds')


def private_fixture(path, expected_sha):
    path = Path(path)
    with execution_policy.directory_fd(path.parent) as parent:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
                    and not info.st_mode & 0o077 and 0 < info.st_size <= 131072, 'Private Git fixture bounds')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                raw = stream.read(131073)
            require(len(raw) == info.st_size and hashlib.sha256(raw).hexdigest() == expected_sha,
                    'Private browser Git fixture changed')
        finally:
            os.close(descriptor)
    return json.loads(raw, object_pairs_hook=unique)


def run(host, name, expected_sha):
    require(re.fullmatch(r'browser-git-[0-9]{8}T[0-9]{6}Z\.json', name)
            and re.fullmatch(r'[0-9a-f]{64}', expected_sha), 'Fixed browser Git evidence name')
    path = host['STATE'] / 'logs' / name
    value = private_fixture(path, expected_sha)
    def inputs():
        return {'native': tree_sha(Path('/native/core/desk')), 'harness': source_sha(Path(__file__).parent)}
    before = inputs()
    require(before['harness'] == host['LOADED_SOURCE_DIGEST'], 'Loaded native Git source changed')
    guard = host['execution_check']()
    validate_fixture(value, guard['run_id'])
    output = host['STATE'] / 'logs' / name.removesuffix('.json')
    output.mkdir(mode=0o700)
    evidence_path = host['STATE'] / 'logs' / name.replace('browser-git-', 'team-git-', 1)
    evidence = {'status': 'fail', 'classification': 'actual-stock-git-from-configured-v3-native-stores',
                'qualifies_phase': False, 'fixture_sha256': expected_sha,
                'native_prerequisite': host['PROGRESS']['team_evidence'], 'execution_id': guard['run_id'],
                'inputs_before': before,
                'scope': 'Owned synthetic Lens observation; not a public export or Git transport API.'}
    try:
        def export(label, container, head):
            def read(oid):
                host['execution_check']()
                return observe(host['dojo'], value['project_id'], container, head, oid)
            return materialize(read, output / label, value['project_id'], container, head)
        source = export('private-source', value['source']['container_id'], value['source']['commits'][0])
        destination = value['destination']
        published = export('publication', destination['container_id'], destination['published_head'])
        edited = export('shared-edit', destination['container_id'], destination['edited_head'])
        evidence['checks'] = verify_publication(source, published, edited, value)
        evidence['exports'] = {label: {'head': item['head'], 'objects': len(item['objects']),
            'object_bytes': item['object_bytes'], 'file_count': len(item['files']),
            'git_version': item['git_version'], 'commands': item['commands']}
            for label, item in (('source', source), ('published', published), ('edited', edited))}
        host['execution_check']()
        require(private_fixture(path, expected_sha) == value, 'Browser Git input changed during qualification')
        evidence['inputs_after'] = inputs()
        require(before == evidence['inputs_after'], 'Native Git source changed during qualification')
        evidence['status'] = 'pass'
    except BaseException as error:
        evidence['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        execution_policy.write_json(evidence_path, evidence)
    return {'status': evidence['status'], 'evidence_file': '.piers/fakes/logs/' + evidence_path.name,
            'fixture_sha256': expected_sha}

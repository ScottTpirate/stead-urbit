"""Read a bounded tree or file from the exact pack currently accepted by Home."""
from itertools import islice
from pathlib import Path
import re
import tempfile
import time

import git_pack_store as store
from execution_policy import directory_fd
from portable_code import HEX, private_directory, ref_name, staged_repository
from portable_recovery import (MAX_RESPONSE, OID, TOKEN, UUID, decoded, match, number,
                               require, same_entry, same_path, shape)


PROTOCOL = 'stead.git-browse/1'
MAX_REQUEST = 8192
MAX_DEPTH = 12
MAX_SEGMENT = 255
MAX_PATH = 1024
MAX_ENTRIES = 128
MAX_TREE = 1024 * 1024
MAX_TEXT = 32 * 1024
KINDS = {b'40000': 'tree', b'100644': 'file', b'100755': 'file',
         b'120000': 'symlink', b'160000': 'submodule'}
REPORT_FIELDS = {'protocol', 'status', 'snapshot', 'authority_epoch', 'object_count',
                 'head', 'refs', 'request_id', 'accepted_at_ms'}
GENERATION_FIELDS = {'generation', 'generation_limit'}


def segment(name):
    return 0 < len(name) <= MAX_SEGMENT and name not in (b'.', b'..') and b'/' not in name and b'\0' not in name


def request_path(request):
    shape(request, {'protocol', 'project_id', 'snapshot', 'ref', 'path', 'view'})
    require(request['protocol'] == PROTOCOL and match(UUID, request['project_id'])
            and match(TOKEN, request['snapshot']) and request['view'] in ('tree', 'file'), 'browse-request')
    ref_name(request['ref'])
    path = request['path']
    require(isinstance(path, list) and len(path) <= MAX_DEPTH
            and (path or request['view'] == 'tree'), 'browse-path')
    parts = []
    for value in path:
        require(isinstance(value, str) and 0 < len(value) <= MAX_SEGMENT * 2 and match(HEX, value), 'browse-path')
        part = bytes.fromhex(value)
        require(segment(part), 'browse-path')
        parts.append(part)
    require(sum(len(part) for part in parts) <= MAX_PATH, 'browse-path')
    return parts


def accepted_scope(home, request, report):
    require(isinstance(report, dict), 'accepted-pack-required')
    optional = GENERATION_FIELDS.intersection(report)
    shape(report, REPORT_FIELDS | optional)
    require(report['protocol'] == 'stead.code/1' and report['status'] == 'external'
            and report['snapshot'] == request['snapshot'] and match(UUID, report['request_id']), 'accepted-pack-required')
    for key in ('authority_epoch', 'object_count', 'accepted_at_ms', *optional):
        number(report[key], positive=key != 'generation')
    require(int(report['object_count']) <= store.MAX_OBJECTS, 'object-count-bound')
    serialized_refs = report['refs']
    require(isinstance(serialized_refs, str) and serialized_refs.isascii()
            and len(serialized_refs) <= MAX_RESPONSE, 'ref-inventory')
    refs = decoded(serialized_refs.encode('ascii'))
    store.validate_refs(refs, report['head'])
    project = request['project_id']
    scope = {'home': home, 'project_id': project, 'repository_id': project,
             'authority_epoch': report['authority_epoch']}
    store.validate_scope(scope)
    return scope, refs


def tree_entries(git, oid):
    # Decode raw tree objects so names never pass through pathspec or revision parsing.
    data = git.run('cat-file', 'tree', oid, limit=MAX_TREE)
    position = 0
    while position < len(data):
        separator = data.find(b' ', position, position + 7)
        end = data.find(b'\0', separator + 1, separator + MAX_SEGMENT + 2) if separator >= 0 else -1
        mode = data[position:separator]
        require(separator >= 0 and end >= 0 and mode in KINDS and end + 21 <= len(data), 'browse-tree')
        name = data[separator + 1:end]
        require(segment(name), 'browse-tree')
        yield name, KINDS[mode], data[end + 1:end + 21].hex()
        position = end + 21


def resolve_oid(git, oid, object_type):
    result = git.run('rev-parse', '--verify', '--end-of-options', oid + '^{' + object_type + '}', limit=41)
    require(re.fullmatch(rb'[0-9a-f]{40}\n', result), 'browse-object')
    return result[:-1].decode('ascii')


def text_preview(git, oid):
    raw_size = git.run('cat-file', '-s', oid, limit=16)
    require(re.fullmatch(rb'[0-9]{1,8}\n', raw_size), 'browse-blob-size')
    size = int(raw_size)
    if size > MAX_TEXT:
        return {'preview': 'too-large', 'bytes': size}
    raw = git.run('cat-file', 'blob', oid, limit=MAX_TEXT)
    require(len(raw) == size, 'browse-blob-size')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return {'preview': 'binary', 'bytes': size}
    if any((ord(char) < 32 and char not in '\t\n\r') or 127 <= ord(char) <= 159 for char in text):
        return {'preview': 'binary', 'bytes': size}
    return {'preview': 'text', 'bytes': size, 'text': text}


def project_view(git, ref_oid, path, view):
    require(match(OID, ref_oid), 'browse-ref')
    commit = resolve_oid(git, ref_oid, 'commit')
    result = {'commit': commit, 'status': view}
    kind, oid = 'tree', resolve_oid(git, commit, 'tree')
    for part in path:
        require(kind == 'tree', 'browse-path-unavailable')
        found = next((row for row in tree_entries(git, oid) if row[0] == part), None)
        require(found is not None, 'browse-path-unavailable')
        _, kind, oid = found
    require(kind == view, 'browse-path-unavailable')
    if view == 'file':
        return result | text_preview(git, oid)
    rows = list(islice(tree_entries(git, oid), MAX_ENTRIES + 1))
    entries = [{'name': name.hex(), 'kind': kind, 'oid': oid} for name, kind, oid in rows[:MAX_ENTRIES]]
    return result | {'entries': entries, 'truncated': len(rows) > MAX_ENTRIES}


def browse(authorize, home, request, storage, binary, *, deadline=None):
    """Use the caller's browser authorization and an isolated stock Git reader.

    The caller binds each authorize() call to the same authenticated browser,
    trusted Home and requested project. It must start disclosure after return.
    """
    path = request_path(request)
    request = request.copy()
    request['path'] = [part.hex() for part in path]
    observed = authorize()
    scope, refs = accepted_scope(home, request, observed)
    observed = observed.copy()
    snapshot = request['snapshot']
    require(request['ref'] in refs, 'browse-ref')

    with store.repository_directory(storage, scope) as (directory, check_store):
        with store.open_snapshot(directory, snapshot) as source:
            manifest = store.read_manifest(source, snapshot, scope)
            require(manifest['head'] == observed['head'] and manifest['refs'] == refs
                    and manifest['object_count'] == int(observed['object_count']), 'home-pack-differs')
            with tempfile.TemporaryDirectory(prefix='stead-git-browse-') as scratch:
                with directory_fd(Path(scratch)) as parent:
                    opened_parent = private_directory(parent)
                    with staged_repository(parent, binary, deadline=deadline,
                                           command_prefix=store.GIT_LIMITS) as (name, opened, git):
                        _, inventory = store.verify_pack(git, source, store.PACK_NAME,
                                                         manifest['pack_sha256'], refs, manifest['head'])
                        require(all(type(manifest[key]) is type(value) and manifest[key] == value
                                    for key, value in inventory.items()), 'snapshot-inventory')
                        result = project_view(git, refs[request['ref']], path, request['view'])
                        require(same_entry(parent, name, opened) and same_path(Path(scratch), opened_parent),
                                'staging-binding')
            check_store()
    require(authorize() == observed, 'home-acceptance-changed')
    require(deadline is None or time.monotonic() < deadline, 'git-timeout')
    return {key: request[key] for key in ('protocol', 'project_id', 'snapshot', 'ref', 'path')} | result

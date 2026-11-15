"""Bounded, read-only comparison of the exact external proposal authorized by Home."""
from pathlib import Path
import re
import tempfile
import time
import unicodedata

import git_pack_browse as browse
import git_pack_store as store
from execution_policy import directory_fd
from portable_code import HEX, private_directory, staged_repository
from portable_recovery import OID, TOKEN, UUID, RecoveryError, encoded, match, number, require, same_entry, same_path, shape


PATH = '/stead/api/code/changes'
PROTOCOL = 'stead.git-changes/1'
MAX_REQUEST = 8192
MAX_METADATA = 1024 * 1024
MAX_FILES = 256
MAX_LIST = 128 * 1024
MAX_BLOB = 64 * 1024
MAX_PATCH = 128 * 1024
MAX_RESPONSE = 200 * 1024
PROPOSAL_FIELDS = {'protocol', 'status', 'proposal_id', 'revision', 'author', 'work_id', 'work_title',
                   'source_ref', 'ref', 'base_oid', 'head_oid', 'base_snapshot', 'generation', 'reviewer',
                   'merged_revision', 'merged_snapshot', 'merged_request_id'}
RAW_ROW = re.compile(rb':(000000|100644|100755|120000|160000) (000000|100644|100755|120000|160000) '
                     rb'([0-9a-f]{40}) ([0-9a-f]{40}) ([ADMT])')


def request_path(request):
    shape(request, {'protocol', 'project_id', 'snapshot', 'proposal_id', 'revision', 'view', 'path'})
    require(request['protocol'] == PROTOCOL and match(UUID, request['project_id'])
            and match(UUID, request['proposal_id']) and match(TOKEN, request['snapshot'])
            and request['view'] in ('files', 'patch'), 'changes-request')
    number(request['revision'], positive=True)
    require(int(request['revision']) <= 64, 'changes-request')
    path = request['path']
    if request['view'] == 'files':
        require(path == '', 'changes-path')
        return b''
    require(isinstance(path, str) and 0 < len(path) <= browse.MAX_PATH * 2 and match(HEX, path), 'changes-path')
    raw = bytes.fromhex(path)
    require(all(browse.segment(part) for part in raw.split(b'/')), 'changes-path')
    return raw


def proposal_scope(request, proposal):
    shape(proposal, PROPOSAL_FIELDS)
    require(all(isinstance(value, str) for value in proposal.values())
            and proposal['protocol'] == 'stead.code/1' and proposal['status'] == 'proposal'
            and proposal['proposal_id'] == request['proposal_id'], 'changes-proposal-unavailable')
    require(proposal['revision'] == request['revision'], 'changes-revision-changed')
    require(all(match(OID, proposal[key]) and proposal[key] != '0' * 40 for key in ('base_oid', 'head_oid'))
            and match(TOKEN, proposal['base_snapshot']) and match(UUID, proposal['work_id'])
            and match(UUID, proposal['author']), 'changes-proposal-unavailable')
    return proposal['base_oid'], proposal['head_oid']


def changed_files(git, base, head):
    # Both OIDs come exclusively from the current Home-authorized proposal.
    # No rename heuristics, pathspec magic, external diff driver or textconv.
    try:
        raw = git.run('diff-tree', '--no-commit-id', '--raw', '-z', '-r', '--no-renames',
                      '--no-ext-diff', '--no-textconv', '--abbrev=40', base, head, '--', limit=MAX_METADATA)
    except RecoveryError as exc:
        if str(exc) == 'git-output-bound':
            raise RecoveryError('changes-metadata-bound') from None
        raise
    if not raw:
        return []
    require(raw.endswith(b'\0'), 'changes-diff-format')
    parts = raw[:-1].split(b'\0')
    require(len(parts) % 2 == 0, 'changes-diff-format')
    rows = []
    seen = set()
    for index in range(0, len(parts), 2):
        header, path = parts[index:index + 2]
        match_row = RAW_ROW.fullmatch(header)
        require(match_row is not None and path not in seen and 0 < len(path) <= browse.MAX_PATH
                and all(browse.segment(part) for part in path.split(b'/')), 'changes-diff-format')
        seen.add(path)
        old_mode, new_mode, old_oid, new_oid, status = (part.decode('ascii') for part in match_row.groups())
        rows.append({'path': path.hex(), 'status': status, 'old_mode': old_mode, 'new_mode': new_mode,
                     'old_oid': old_oid, 'new_oid': new_oid})
    return rows


def patch_view(git, base, head, row):
    if any(row[key] not in ('000000', '100644', '100755') for key in ('old_mode', 'new_mode')):
        return {'preview': 'unsupported-type'}
    for side in ('old', 'new'):
        oid = row[side + '_oid']
        if oid == '0' * 40:
            continue
        raw_size = git.run('cat-file', '-s', oid, limit=16)
        require(re.fullmatch(rb'[0-9]{1,9}\n', raw_size), 'changes-blob-size')
        if int(raw_size) > MAX_BLOB:
            return {'preview': 'too-large'}
        raw = git.run('cat-file', 'blob', oid, limit=MAX_BLOB)
        require(len(raw) == int(raw_size), 'changes-blob-size')
        try:
            source = raw.decode('utf-8')
        except UnicodeDecodeError:
            return {'preview': 'binary'}
        if '\0' in source:
            return {'preview': 'binary'}
    try:
        raw = git.run('--literal-pathspecs', '-c', 'diff.algorithm=myers', 'diff', '--no-ext-diff',
                      '--no-textconv', '--no-renames', '--no-color', '--text', '--unified=3',
                      '--src-prefix=a/', '--dst-prefix=b/', base, head, '--', bytes.fromhex(row['path']), limit=MAX_PATCH)
    except RecoveryError as exc:
        if str(exc) == 'git-output-bound':
            return {'preview': 'too-large'}
        raise
    text = raw.decode('utf-8', errors='strict')
    # Render source as inert text. Make terminal controls and directional/format
    # controls visible rather than allowing source text to disguise the patch.
    safe = ''.join(f'\\u{{{ord(char):x}}}' if unicodedata.category(char) in ('Cc', 'Cf')
                   and char not in '\n\t' else char for char in text)
    return {'preview': 'text', 'text': safe, 'sanitized': safe != text}


def changes(authorize, home, request, storage, binary, *, deadline=None):
    """authorize() resolves pack and proposal for the same browser/project twice.

    The caller must not begin disclosing data until this function returns. Only
    commits in the verified accepted pack closure can supply review contents.
    """
    request_path(request)
    request = request.copy()
    observed_pack, observed_proposal = authorize()
    require(isinstance(observed_pack, dict) and isinstance(observed_proposal, dict), 'changes-proposal-unavailable')
    observed_pack, observed_proposal = observed_pack.copy(), observed_proposal.copy()
    scope, refs = browse.accepted_scope(home, request, observed_pack)
    base, head = proposal_scope(request, observed_proposal)
    result = {key: request[key] for key in ('protocol', 'project_id', 'snapshot', 'proposal_id', 'revision')}
    result.update(base=base, head=head, status=request['view'])
    with store.repository_directory(storage, scope) as (directory, check_store):
        with store.open_snapshot(directory, request['snapshot']) as source:
            manifest = store.read_manifest(source, request['snapshot'], scope)
            require(manifest['head'] == observed_pack['head'] and manifest['refs'] == refs
                    and manifest['object_count'] == int(observed_pack['object_count']), 'home-pack-differs')
            with tempfile.TemporaryDirectory(prefix='stead-git-changes-') as scratch:
                with directory_fd(Path(scratch)) as parent:
                    opened_parent = private_directory(parent)
                    with staged_repository(parent, binary, deadline=deadline,
                                           command_prefix=store.GIT_LIMITS) as (name, opened, git):
                        _, inventory = store.verify_pack(git, source, store.PACK_NAME,
                                                         manifest['pack_sha256'], refs, manifest['head'])
                        require(all(type(manifest[key]) is type(value) and manifest[key] == value
                                    for key, value in inventory.items()), 'snapshot-inventory')
                        # Resolving only exact 40-byte proposal IDs in this
                        # verified closure cannot access an unaccepted object.
                        require(browse.resolve_oid(git, base, 'commit') == base
                                and browse.resolve_oid(git, head, 'commit') == head, 'changes-source-unavailable')
                        rows = changed_files(git, base, head)
                        if request['view'] == 'files':
                            entries, size = [], 0
                            for row in rows:
                                entry = {key: row[key] for key in ('path', 'status', 'old_mode', 'new_mode')}
                                size += len(encoded(entry))
                                if len(entries) == MAX_FILES or size > MAX_LIST:
                                    break
                                entries.append(entry)
                            result.update(entries=entries, truncated=len(entries) != len(rows))
                        else:
                            row = next((item for item in rows if item['path'] == request['path']), None)
                            require(row is not None, 'changes-path-unavailable')
                            result.update(path=request['path'], **patch_view(git, base, head, row))
                            if len(encoded(result)) > MAX_RESPONSE:
                                result.pop('text', None)
                                result.pop('sanitized', None)
                                result['preview'] = 'too-large'
                        require(same_entry(parent, name, opened) and same_path(Path(scratch), opened_parent), 'staging-binding')
            check_store()
    require(authorize() == (observed_pack, observed_proposal), 'home-acceptance-changed')
    require(deadline is None or time.monotonic() < deadline, 'git-timeout')
    require(len(encoded(result)) <= MAX_RESPONSE, 'changes-response-bound')
    return result

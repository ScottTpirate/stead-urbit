"""Prepare one reviewed default-branch candidate from an accepted Git snapshot."""
from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile
import time

from execution_policy import directory_fd
import git_pack_push as push
import git_pack_store as store
from portable_code import MAX_GIT_TIME, MAX_REF_BYTES, private_directory, ref_name
from portable_recovery import OID, TOKEN, UUID, encoded, match, require, same_entry, same_path, sha


PROTOCOL = 'stead.git-pack-reviewed-candidate/1'
INTENT = 'stead.git-pack-reviewed-intent/1'
PACK_IDENTITY = ('pack_sha256', 'pack_bytes', 'object_count', 'object_bytes', 'object_ids_sha256')


def branch(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_REF_BYTES, 'review-branch')
    key = raw.hex()
    ref_name(key, branch=True)
    return key


def prepare(storage, scope, base_snapshot, source_ref, target_ref, base_oid, head_oid, git, *,
            proposal_id, proposal_revision, work_id, generation, deadline=None):
    """Read a trusted Home selection and stage a candidate; Home still decides."""
    store.validate_scope(scope)
    require(scope['project_id'] == scope['repository_id'] and match(TOKEN, base_snapshot), 'review-scope')
    require(match(UUID, proposal_id) and match(UUID, work_id)
            and type(proposal_revision) is int and 1 <= proposal_revision <= 64
            and type(generation) is int and 0 <= generation < 2**64 - 1, 'review-proposal')
    require(all(match(OID, oid) and oid != push.ZERO_OID for oid in (base_oid, head_oid))
            and base_oid != head_oid, 'review-oids')
    source, target = branch(source_ref), branch(target_ref)
    require(source != target, 'review-source-is-target')
    require(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline), 'review-deadline')
    internal = time.monotonic() + MAX_GIT_TIME
    deadline = internal if deadline is None else min(internal, deadline)
    require(time.monotonic() < deadline, 'git-timeout')
    storage = Path(storage)
    intent = {'protocol': INTENT, 'scope': dict(scope), 'base_snapshot': base_snapshot,
              'generation': str(generation), 'proposal_id': proposal_id, 'proposal_revision': str(proposal_revision),
              'work_id': work_id, 'source': source, 'target': target, 'base_oid': base_oid, 'head_oid': head_oid}
    digest = sha(encoded(intent))
    changes = [{'ref': target, 'prior': base_oid, 'target': head_oid}]

    with tempfile.TemporaryDirectory(prefix='stead-pack-review-') as work:
        directory = Path(work)
        path = directory / 'reviewed.pack'
        with directory_fd(directory) as parent:
            workspace = private_directory(parent)
            with store.repository_directory(storage, scope) as (repository, check_store):
                with store.open_snapshot(repository, base_snapshot) as accepted:
                    base = store.read_manifest(accepted, base_snapshot, scope)
                    require(target == base['head'] and base['refs'].get(target) == base_oid, 'review-target-changed')
                    require(base['refs'].get(source) == head_oid, 'review-source-changed')
                    fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                    with os.fdopen(fd, 'wb') as stream:
                        inventory = store.copy_pack(accepted, store.PACK_NAME, base['pack_sha256'], destination=stream)
                        stream.flush()
                        opened = os.fstat(stream.fileno())
                    require(inventory == (base['pack_bytes'], base['object_count']), 'review-pack-inventory')
                    check_store()

            def recheck():
                require(same_path(directory, workspace) and same_entry(parent, path.name, opened), 'review-workspace-binding')
                require(time.monotonic() < deadline, 'git-timeout')

            recheck()
            # Reuse the stock validator. Its correlation argument carries the
            # reviewed intent digest here; there is no uploaded request pack.
            candidate = push.prepare(storage, scope, base_snapshot, path, base['pack_sha256'], changes, git,
                                     upload_sha256=digest, deadline=deadline, recheck=recheck)
            recheck()

    result = candidate['manifest']
    require(result['head'] == target and result['refs'] == base['refs'] | {target: head_oid}
            and all(result[key] == base[key] for key in PACK_IDENTITY), 'review-candidate-manifest')
    require(candidate['changes'] == [changes[0] | {'action': 'fast-forward', 'target_kind': 'commit'}]
            and candidate['upload_sha256'] == digest and sha(encoded(result)) == candidate['candidate_snapshot'],
            'review-candidate-evidence')
    return {'protocol': PROTOCOL, 'status': 'candidate-staged', 'intent': intent, 'intent_sha256': digest,
            'candidate_snapshot': candidate['candidate_snapshot'], 'manifest': result, 'changes': candidate['changes']}

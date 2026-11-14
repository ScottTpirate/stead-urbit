"""Prepare a complete Git snapshot for review by the authoritative Home."""
from pathlib import Path
import tempfile
import time

import git_pack_store as store
from execution_policy import directory_fd
from portable_code import MAX_GIT_TIME, ref_name, staged_repository
from portable_recovery import OID, TOKEN, match, require, shape


PROTOCOL = 'stead.git-pack-push-candidate/1'
MAX_CHANGES = 32
ZERO_OID = '0' * 40


def proposed_refs(base, head, changes):
    """Apply the ordered updates to exact prior ref values in memory."""
    require(isinstance(changes, list) and 0 < len(changes) <= MAX_CHANGES, 'update-bound')
    refs = dict(base)
    ordered = []
    seen = set()
    for change in changes:
        shape(change, {'ref', 'prior', 'target'})
        ref, prior, target = (change[field] for field in ('ref', 'prior', 'target'))
        name = ref_name(ref)
        require(ref not in seen, 'duplicate-ref')
        require(match(OID, prior) and match(OID, target), 'invalid-oid')
        require(target != ZERO_OID, 'ref-delete-unsupported')
        require(prior != target, 'unchanged-ref')
        require(base.get(ref, ZERO_OID) == prior, 'stale-ref')
        require(prior == ZERO_OID or name.startswith(b'refs/heads/'), 'tag-replacement')
        seen.add(ref)
        refs[ref] = target
        ordered.append(dict(change))
    store.validate_refs(refs, head)
    return refs, ordered


def check_ancestry(git, ordered):
    facts = []
    for change in ordered:
        ref, prior, target = (change[field] for field in ('ref', 'prior', 'target'))
        kind = git.run('cat-file', '-t', target, limit=16).strip().decode('ascii')
        branch = ref_name(ref).startswith(b'refs/heads/')
        require(kind in ('commit', 'tree', 'blob', 'tag') and (not branch or kind == 'commit'),
                'wrong-object-kind')
        action = 'create' if prior == ZERO_OID else 'fast-forward'
        if action == 'fast-forward':
            # The candidate contains the complete object closure. Every
            # commit listed here is reachable by following parent edges.
            ancestors = git.run('rev-list', target, limit=store.MAX_OBJECTS * 41)
            require(prior.encode('ascii') in ancestors.splitlines(), 'non-fast-forward')
        facts.append({**change, 'action': action, 'target_kind': kind})
    return facts


def prepare(storage, scope, base_snapshot, candidate_pack, candidate_pack_sha256, changes, git,
            *, upload_sha256):
    """Validate and stage a candidate, leaving accepted refs under Home control.

    A trusted caller obtains the base digest and scope from the Home and binds
    upload_sha256 to the original wire request. This worker checks the derived
    complete pack and exact ref transitions. It does not handle credentials,
    permission, retention, or final compare-and-swap.
    """
    store.validate_scope(scope)
    require(scope['project_id'] == scope['repository_id'], 'home-repository-scope')
    require(all(match(TOKEN, digest) for digest in (base_snapshot, candidate_pack_sha256, upload_sha256)),
            'push-digest-required')
    deadline = time.monotonic() + MAX_GIT_TIME
    with store.repository_directory(storage, scope) as (directory, check_store):
        with store.open_snapshot(directory, base_snapshot) as source:
            base = store.read_manifest(source, base_snapshot, scope)
            refs, ordered = proposed_refs(base['refs'], base['head'], changes)
            pack_identity = store.copy_pack(source, store.PACK_NAME, base['pack_sha256'])
            require(pack_identity == (base['pack_bytes'], base['object_count']), 'base-pack-inventory')
            check_store()

    pack = Path(candidate_pack)
    with tempfile.TemporaryDirectory(prefix='stead-pack-push-') as scratch:
        with directory_fd(Path(scratch)) as parent, directory_fd(pack.parent) as source:
            with staged_repository(parent, git, deadline=deadline, command_prefix=store.GIT_LIMITS) as (_, _, repo):
                _, inventory = store.verify_pack(repo, source, pack.name, candidate_pack_sha256, refs, base['head'])
                facts = check_ancestry(repo, ordered)

    require(time.monotonic() < deadline, 'git-timeout')
    candidate, manifest = store.stage(storage, pack, candidate_pack_sha256, scope, refs, base['head'], git,
                                      deadline=deadline)
    require(all(manifest[key] == value for key, value in inventory.items()), 'snapshot-inventory')
    return {
        'protocol': PROTOCOL,
        'status': 'candidate-staged',
        'scope': dict(scope),
        'base_snapshot': base_snapshot,
        'candidate_snapshot': candidate,
        'upload_sha256': upload_sha256,
        'changes': facts,
        'manifest': manifest,
    }

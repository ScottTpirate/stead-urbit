"""Produce a bounded Git worker proof from an exact private Home admission."""
from pathlib import Path

import git_pack_push as push
import git_pack_receive as receive
import git_pack_store as store
from portable_code import ref_name
from portable_recovery import OID, TOKEN, UUID, decoded, encoded, match, number, require, sha, shape


MAX_MESSAGE = 65_536
MAX_GENERATION = 6
ADMISSION = 'stead.git-pack-admission/1'
PROTOCOL = 'stead.git-pack-worker-proof/1'
CLAIM = {'scope', 'base_snapshot', 'generation', 'attempt', 'incarnation', 'request_id',
         'actor', 'wire_sha256', 'changes', 'update_count', 'admitted_at_ms', 'expires_at_ms'}
ACTOR = {'identity_ship', 'principal_id', 'binding_id', 'binding_revision'}
CHANGE = {'ref', 'prior', 'target'}
MANIFEST = {'format', 'object_format', 'scope', 'head', 'refs', 'pack_sha256',
            'pack_bytes', 'object_count', 'object_bytes', 'object_ids_sha256'}
PACK = {'pack_sha256', 'pack_bytes', 'object_count', 'object_bytes', 'object_ids_sha256'}


def _live_lease(value, now_ms):
    admitted = int(value['admitted_at_ms'])
    expires = int(value['expires_at_ms'])
    require(type(now_ms) is int and admitted <= now_ms < expires <= admitted + 300_000, 'proof-lease')


def admission(raw, expected_sha256, now_ms):
    """Validate the private, independently pinned Home request as exact bytes."""
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_MESSAGE, 'proof-admission-bound')
    require(match(TOKEN, expected_sha256) and sha(raw) == expected_sha256, 'proof-admission-digest')
    value = decoded(raw, MAX_MESSAGE)
    shape(value, {'protocol', *CLAIM})
    require(value['protocol'] == ADMISSION and encoded(value) == raw, 'proof-admission-format')
    scope = value['scope']
    store.validate_scope(scope)
    require(scope['project_id'] == scope['repository_id'], 'proof-scope')
    for key in ('base_snapshot', 'wire_sha256', 'incarnation'):
        require(match(TOKEN, value[key]), 'proof-admission-token')
    require(match(UUID, value['request_id']), 'proof-request-id')
    number(value['generation'], positive=False)
    number(value['attempt'])
    require(int(value['generation']) <= MAX_GENERATION, 'proof-generation-bound')
    actor = value['actor']
    shape(actor, ACTOR)
    require(match(store.SHIP, actor['identity_ship']) and actor['identity_ship'] != scope['home']
            and all(match(UUID, actor[key]) for key in ('principal_id', 'binding_id')), 'proof-actor')
    number(actor['binding_revision'])
    number(value['admitted_at_ms'])
    number(value['expires_at_ms'])
    _live_lease(value, now_ms)
    ordered_changes(value)
    return value


def ordered_changes(value):
    changes = value['changes']
    number(value['update_count'])
    count = int(value['update_count'])
    require(isinstance(changes, dict) and 0 < count <= push.MAX_CHANGES
            and set(changes) == {f'{index:02d}' for index in range(count)}, 'proof-change-bound')
    seen = set()
    ordered = []
    for index in range(count):
        change = changes[f'{index:02d}']
        shape(change, CHANGE)
        ref = change['ref']
        name = ref_name(ref)
        prior, target = change['prior'], change['target']
        require(ref not in seen and match(OID, prior) and match(OID, target)
                and target != push.ZERO_OID and target != prior, 'proof-change')
        require(prior == push.ZERO_OID or name.startswith(b'refs/heads/'), 'proof-tag-replacement')
        seen.add(ref)
        ordered.append(change)
    return ordered


def _body(claim, claim_digest, snapshot, manifest, updates):
    body = {key: claim[key] for key in CLAIM - {'changes'}}
    body.update(protocol=PROTOCOL, admission_sha256=claim_digest, candidate_snapshot=snapshot,
                head=manifest['head'], updates=updates,
                pack={key: str(manifest[key]) for key in PACK})
    raw = encoded(body)
    require(len(raw) <= MAX_MESSAGE, 'proof-output-bound')
    return raw


def _export(claim, claim_digest, candidate, *, head, refs):
    shape(candidate, {'protocol', 'status', 'scope', 'base_snapshot', 'upload_sha256',
                      'candidate_snapshot', 'manifest', 'changes'})
    require(candidate['protocol'] == push.PROTOCOL and candidate['status'] == 'candidate-staged'
            and candidate['scope'] == claim['scope'] and candidate['base_snapshot'] == claim['base_snapshot']
            and candidate['upload_sha256'] == claim['wire_sha256'], 'proof-candidate-substitution')
    manifest = candidate['manifest']
    shape(manifest, MANIFEST)
    require(manifest['format'] == store.FORMAT and manifest['object_format'] == 'sha1'
            and manifest['scope'] == claim['scope'], 'proof-manifest-scope')
    store.validate_refs(manifest['refs'], manifest['head'])
    require(manifest['head'] == head and manifest['refs'] == refs, 'proof-candidate-refs')
    require(all(match(TOKEN, manifest[key]) for key in ('pack_sha256', 'object_ids_sha256')),
            'proof-manifest-digest')
    bounds = {'pack_bytes': (32, store.MAX_PACK), 'object_count': (1, store.MAX_OBJECTS),
              'object_bytes': (1, store.MAX_OBJECT_BYTES)}
    for key, (minimum, maximum) in bounds.items():
        require(type(manifest[key]) is int and minimum <= manifest[key] <= maximum, 'proof-manifest-bound')
    snapshot = candidate['candidate_snapshot']
    require(match(TOKEN, snapshot) and sha(encoded(manifest)) == snapshot, 'proof-snapshot-digest')

    facts = candidate['changes']
    ordered = ordered_changes(claim)
    require(isinstance(facts, list) and len(facts) == len(ordered), 'proof-change-substitution')
    updates = {}
    kinds = {}
    for index, (expected, actual) in enumerate(zip(ordered, facts, strict=True)):
        shape(actual, CHANGE | {'action', 'target_kind'})
        require(all(expected[key] == actual[key] for key in CHANGE), 'proof-change-substitution')
        ref, prior, target = (expected[key] for key in ('ref', 'prior', 'target'))
        creation = prior == push.ZERO_OID
        kind = actual['target_kind']
        require(actual['action'] == ('create' if creation else 'fast-forward')
                and kind in ('commit', 'tree', 'blob', 'tag')
                and (not ref_name(ref).startswith(b'refs/heads/') or kind == 'commit')
                and kinds.setdefault(target, kind) == kind and manifest['refs'].get(ref) == target,
                'proof-object-facts')
        # Numeric keys preserve order explicitly in an object-only carrier. A creation must never
        # produce an ancestry edge. Each advancement proved precisely prior -> target.
        updates[f'{index:02d}'] = expected | {'kind': kind, 'lineage': 'none' if creation else 'fast-forward'}
    return _body(claim, claim_digest, snapshot, manifest, updates)


def prepare(admission_bytes, expected_admission_sha256, storage, wire_path, git, *, now_ms, deadline=None):
    """Run the stock verifier and emit canonical bytes for an authenticated carrier.

    The caller pins the Home's original bytes and supplies its trusted clock
    as a callable returning Unix milliseconds.
    The digest is an integrity check. Worker and admission provenance belong
    to the control channel. This module carries no browser or Git secrets.
    Expiry during verification can leave a valid staged snapshot for operator
    retention to reconcile. An expired attempt cannot produce a proof.
    """
    claim = admission(admission_bytes, expected_admission_sha256, now_ms())
    # Compare Home's ordered command list before costly work and staging.
    with receive.captured_wire(Path(wire_path), claim['wire_sha256']) as (wire, recheck):
        changes, _ = receive.parse(wire)
        require(changes == ordered_changes(claim), 'proof-change-substitution')
        recheck()
    # Base HEAD is unchanged by this push profile. Bound the largest proof
    # for these exact ref names before the worker can consume a storage slot.
    with store.repository_directory(Path(storage), claim['scope']) as (repository, check_store):
        with store.open_snapshot(repository, claim['base_snapshot']) as snapshot:
            base = store.read_manifest(snapshot, claim['base_snapshot'], claim['scope'])
            check_store()
    expected_refs, _ = push.proposed_refs(base['refs'], base['head'], changes)
    maxima = base | {'pack_bytes': store.MAX_PACK, 'object_count': store.MAX_OBJECTS,
                     'object_bytes': store.MAX_OBJECT_BYTES}
    updates = {f'{index:02d}': change | {'kind': 'commit',
                'lineage': 'none' if change['prior'] == push.ZERO_OID else 'fast-forward'}
               for index, change in enumerate(changes)}
    _body(claim, expected_admission_sha256, '0' * 64, maxima, updates)
    _live_lease(claim, now_ms())
    candidate = receive.prepare(Path(storage), claim['scope'], claim['base_snapshot'],
                                Path(wire_path), claim['wire_sha256'], git, deadline=deadline)
    # A valid proof that misses its lease remains only a staged snapshot.
    proof = _export(claim, expected_admission_sha256, candidate, head=base['head'], refs=expected_refs)
    _live_lease(claim, now_ms())
    return proof

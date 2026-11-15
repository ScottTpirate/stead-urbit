#!/usr/bin/env python3
"""Verify evidence for a first cross-ship project move without changing authority."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from portable_recovery import OID, TOKEN, UUID, comment_body, decoded, encoded, match, number, origin, private_file, require, sha, shape


DIRECTORY = 'stead.project-directory/1'
HANDOFF = 'stead.project-handoff/1'
JOURNAL = 'stead.journal/3'
COMMAND = 'stead.command/3'
SIGNATURE = re.compile(r'[0-9a-f]{128}')
SHIP = re.compile(r'~(?:[a-z]{3}|[a-z]{6}(?:-{1,2}[a-z]{6})*)')
DIRECTORY_FIELDS = {'protocol', 'project_id', 'custody_id', 'home', 'origin', 'authority_epoch'}
TRUST_FIELDS = {'protocol', 'current_directory_sha256', 'source_ed25519', 'destination_ed25519',
                'destination_home', 'destination_origin'}
TRANSFER_FIELDS = {'protocol', 'migration_id', 'project_id', 'custody_id', 'prior_directory_sha256',
                   'destination_home', 'destination_origin', 'destination_epoch', 'snapshot_sha256',
                   'journal_sha256', 'journal_count', 'journal_head', 'source_fence_sha256', 'destination_readback_sha256'}
ROW_FIELDS = {'protocol', 'sequence', 'previous_digest', 'canonical_command', 'receipt', 'old_revision',
              'new_revision', 'authentication_context', 'grant_target'}
COMMAND_FIELDS = {'protocol', 'request_id', 'project_id', 'resource_id', 'expected_revision', 'authority_epoch',
                  'operation', 'payload'}
AUTH_FIELDS = {'identity', 'authentication', 'authentication_strength', 'session_audit_id',
               'credential_expires_at_ms', 'home', 'organization_id', 'team_id', 'runtime'}
ACTOR_FIELDS = {'identity_ship', 'principal_id', 'binding_id', 'binding_revision', 'binding_expires_at_ms'}
RECEIPT_FIELDS = {'protocol', 'status', 'request_id', 'canonical_sha256', 'project_id', 'resource_id',
                  'resource_kind', 'container_id', 'resource_revision', 'authority_epoch', 'operation', 'principal_id',
                  'binding_id', 'binding_revision', 'identity_ship', 'authentication', 'authentication_strength',
                  'session_audit_id', 'runtime', 'accepted_at_ms', 'git_commit_oid'}
EVIDENCE_FIELDS = {'protocol', 'migration_id', 'project_id', 'home', 'authority_epoch', 'journal_head',
                   'snapshot_sha256', 'observation_sha256', 'writer_state'}
SOURCE_STATUS_FIELDS = {'protocol', 'migration_id', 'project_id', 'home', 'authority_epoch', 'journal_head',
                        'destination_home', 'retired_at_ms', 'writer_state'}
OPERATIONS = {
    'project.create': 'project', 'work.create': 'work', 'work.update': 'work', 'work.delete': 'work', 'work.assign': 'work',
    'work.comment': 'work',
    'container.create': 'container', 'document.save': 'document', 'document.publish': 'document',
    'document.delete': 'document', 'relation.create': 'relation', 'relation.delete': 'relation',
    'policy.grant': 'policy', 'policy.revoke': 'policy', 'policy.renew-creator-grant': 'policy',
}
MAX_ROW = 262_144
MAX_ROWS = 6_144
MAX_JOURNAL = 64 * 1024 * 1024
MAX_SNAPSHOT = 256 * 1024 * 1024
MAX_EVIDENCE = 4_096
MAX_OBSERVATION = 1024 * 1024
ED25519_SPKI = bytes.fromhex('302a300506032b6570032100')


def canonical(value):
    # portable_recovery writes a newline to files; native digests exclude it.
    return encoded(value)[:-1]


def strings(value, keys):
    shape(value, keys)
    require(all(isinstance(field, str) and '\0' not in field for field in value.values()), 'string-fields-required')


def exact_record(raw, keys, bound):
    value = decoded(raw, bound)
    strings(value, keys)
    require(canonical(value) == raw, 'noncanonical-record')
    return value


def embedded(raw, keys, bound):
    return exact_record(raw.encode('utf-8'), keys, bound)


def domain_hash(domain, raw):
    return sha(domain.encode('ascii') + b'\0' + raw)


def verify_signature(key, signature, domain, transfer):
    require(match(TOKEN, key) and match(SIGNATURE, signature), 'signature-shape')
    with tempfile.TemporaryDirectory(prefix='stead-handoff-signature-') as temporary:
        directory = Path(temporary)
        (directory / 'public.der').write_bytes(ED25519_SPKI + bytes.fromhex(key))
        (directory / 'signature').write_bytes(bytes.fromhex(signature))
        (directory / 'message').write_bytes(HANDOFF.encode('ascii') + b'\0' + domain + b'\0' + canonical(transfer))
        result = subprocess.run(['/usr/bin/openssl', 'pkeyutl', '-verify', '-pubin', '-keyform', 'DER', '-rawin',
                                 '-inkey', 'public.der', '-sigfile', 'signature', '-in', 'message'], cwd=directory,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                env={'LC_ALL': 'C', 'OPENSSL_CONF': '/dev/null'}, timeout=5, check=False)
    require(result.returncode == 0, 'handoff-signature-invalid')


@contextmanager
def input_stream(path, bound):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                and info.st_mode & 0o077 == 0 and 0 < info.st_size <= bound, 'private-evidence-file-required')
        yield stream


def verify_blob(path, bound, expected):
    with input_stream(path, bound) as stream:
        digest = hashlib.sha256()
        size = 0
        for chunk in iter(lambda: stream.read(262_144), b''):
            size += len(chunk)
            require(size <= bound, 'evidence-byte-bound')
            digest.update(chunk)
        require(size > 0 and digest.hexdigest() == expected, 'evidence-digest-mismatch')


def remember_actor(actor, binding_owners, observed_actors):
    binding = actor['binding_id']
    principal = actor['principal_id']
    require(binding_owners.get(binding, principal) == principal, 'journal-binding-owner-changed')
    prior = observed_actors.get(principal)
    require(prior is None or actor == prior or int(actor['binding_revision']) > int(prior['binding_revision']),
            'journal-binding-revision-conflict')
    binding_owners[binding] = principal
    observed_actors[principal] = actor


def verify_event(raw, current, sequence, previous, last_time, seen, context, binding_owners, observed_actors,
                 creator_grant):
    record = exact_record(raw, ROW_FIELDS, MAX_ROW)
    require(record['protocol'] == JOURNAL and record['sequence'] == str(sequence)
            and record['previous_digest'] == previous, 'journal-link-mismatch')
    command_raw = record['canonical_command'].encode('utf-8')
    command = decoded(command_raw, 65_536)
    shape(command, COMMAND_FIELDS)
    strings({key: value for key, value in command.items() if key != 'payload'}, COMMAND_FIELDS - {'payload'})
    payload = command['payload']
    require(isinstance(payload, dict) and len(payload) <= 16
            and all(key.isascii() and '\0' not in key and isinstance(value, str) and '\0' not in value
                    for key, value in payload.items())
            and canonical(command) == command_raw, 'journal-command-shape')
    require(command['protocol'] == COMMAND and command['project_id'] == current['project_id']
            and command['authority_epoch'] == current['authority_epoch'], 'journal-project-scope')
    require(all(match(UUID, command[field]) for field in ('request_id', 'resource_id')), 'journal-command-identifiers')
    operation = command['operation']
    require(operation in OPERATIONS and (sequence == 1) == (operation == 'project.create'), 'journal-project-genesis')
    number(command['expected_revision'], positive=False)
    require(record['old_revision'] == command['expected_revision']
            and record['new_revision'] == str(int(command['expected_revision']) + 1), 'journal-revision-mismatch')
    number(record['new_revision'])

    receipt = embedded(record['receipt'], RECEIPT_FIELDS, 8_192)
    require(receipt['protocol'] == 'stead.receipt/3' and receipt['status'] == 'accepted'
            and receipt['canonical_sha256'] == domain_hash(COMMAND, command_raw)
            and receipt['resource_revision'] == record['new_revision'], 'journal-receipt-mismatch')
    require(all(receipt[field] == command[field] for field in ('request_id', 'project_id', 'resource_id',
                                                               'authority_epoch', 'operation')), 'journal-receipt-scope')
    kind = OPERATIONS[operation]
    if operation == 'work.comment':
        shape(payload, {'body'})
        require(command['expected_revision'] != '0', 'journal-comment-revision')
        comment_body(payload['body'])
    container = command['resource_id'] if kind == 'container' else payload.get('container_id') if kind == 'document' else ''
    require(receipt['resource_kind'] == kind and receipt['container_id'] == container, 'journal-receipt-target')
    require(match(OID, receipt['git_commit_oid']) if kind == 'document' else receipt['git_commit_oid'] == '',
            'journal-receipt-git-oid')
    auth = embedded(record['authentication_context'], AUTH_FIELDS, 4_096)
    identity = embedded(auth['identity'], ACTOR_FIELDS, 1_024)
    event_context = (auth['organization_id'], auth['team_id'], auth['runtime'])
    if sequence == 1:
        require(command['resource_id'] == current['project_id'] and record['old_revision'] == '0'
                and payload.get('organization_id') == auth['organization_id']
                and payload.get('owning_team_id') == auth['team_id'], 'journal-project-genesis')
    else:
        require(context == event_context, 'journal-actor-context-mismatch')
    require(auth['home'] == current['home'] and auth['home'] != identity['identity_ship']
            and match(SHIP, identity['identity_ship']), 'journal-actor-home-mismatch')
    require(all(match(UUID, identity[field]) for field in ('principal_id', 'binding_id'))
            and all(match(UUID, auth[field]) for field in ('organization_id', 'team_id')), 'journal-actor-identifiers')
    require(all(receipt[field] == identity[field] for field in ('identity_ship', 'principal_id', 'binding_id',
                                                                'binding_revision'))
            and all(receipt[field] == auth[field] for field in ('authentication', 'authentication_strength',
                                                               'session_audit_id', 'runtime')), 'journal-actor-mismatch')
    for value in (receipt['accepted_at_ms'], identity['binding_revision'], identity['binding_expires_at_ms'],
                  auth['credential_expires_at_ms']):
        number(value)
    accepted = int(receipt['accepted_at_ms'])
    require(last_time <= accepted < int(auth['credential_expires_at_ms']) <= int(identity['binding_expires_at_ms']),
            'journal-actor-time-mismatch')
    method = auth['authentication']
    strength = auth['authentication_strength']
    audit = auth['session_audit_id']
    native = (method, strength, audit) == ('native-sender/1', 'native-sender', '')
    browser = (method, strength) == ('native-approved-browser/1', 'native-approved-browser') and match(TOKEN, audit)
    require((browser or native and auth['credential_expires_at_ms'] == identity['binding_expires_at_ms'])
            and auth['runtime'] in {'isolated-fake', 'live-synthetic'}, 'journal-authentication-profile')
    remember_actor(identity, binding_owners, observed_actors)
    if operation == 'project.create':
        creator_grant.update(identity, request_id=command['request_id'], policy_revision='1', revoked=False)
    if kind == 'policy':
        require(command['resource_id'] == current['project_id']
                and command['expected_revision'] == creator_grant['policy_revision'], 'journal-policy-revision')
        creator_grant['policy_revision'] = record['new_revision']
    if operation == 'policy.revoke' and payload.get('grant_id') == creator_grant['request_id']:
        creator_grant['revoked'] = True
    if operation == 'policy.renew-creator-grant':
        require(payload == {'grant_id': creator_grant['request_id']} and not creator_grant['revoked']
                and all(identity[field] == creator_grant[field] for field in ('principal_id', 'binding_id'))
                and int(identity['binding_revision']) > int(creator_grant['binding_revision'])
                and int(identity['binding_expires_at_ms']) > int(creator_grant['binding_expires_at_ms']),
                'journal-creator-grant-renewal')
        creator_grant.update(identity)
    target_principal = ''
    if operation == 'work.assign':
        shape(payload, {'assignee_principal_id'})
        target_principal = payload['assignee_principal_id']
        require(command['expected_revision'] != '0' and (target_principal == '' or match(UUID, target_principal)),
                'journal-assignment-target-shape')
    elif operation == 'work.create' and 'assignee_principal_id' in payload:
        shape(payload, {'title', 'description', 'type', 'status', 'priority', 'assignee_principal_id'})
        target_principal = payload['assignee_principal_id']
        require(command['expected_revision'] == '0' and match(UUID, target_principal),
                'journal-assignment-target-shape')
    elif operation == 'policy.grant':
        target_principal = payload.get('principal_id')
    if operation == 'policy.grant' or target_principal:
        target = embedded(record['grant_target'], ACTOR_FIELDS, 1_024)
        require(target['principal_id'] == target_principal and match(UUID, target['principal_id'])
                and match(UUID, target['binding_id']) and match(SHIP, target['identity_ship'])
                and target['identity_ship'] != current['home'], 'journal-grant-target-mismatch')
        number(target['binding_revision'])
        number(target['binding_expires_at_ms'])
        require(accepted < int(target['binding_expires_at_ms']), 'journal-grant-target-time')
        shared_identity = any(target[field] == identity[field] for field in ('principal_id', 'binding_id', 'identity_ship'))
        require(not shared_identity or target == identity, 'journal-grant-target-mismatch')
        remember_actor(target, binding_owners, observed_actors)
    else:
        require(record['grant_target'] == '', 'journal-grant-target-mismatch')
    key = (receipt['principal_id'], receipt['request_id'])
    require(key not in seen, 'journal-request-replay')
    seen.add(key)
    return domain_hash(JOURNAL, raw), accepted, event_context


def verify_journal(path, current, transfer):
    previous = '0' * 64
    count, size, last_time = 0, 0, 0
    context = None
    seen = set()
    binding_owners = {}
    observed_actors = {}
    creator_grant = {}
    digest = hashlib.sha256()
    with input_stream(path, MAX_JOURNAL) as stream:
        for line in iter(lambda: stream.readline(MAX_ROW + 2), b''):
            size += len(line)
            count += 1
            require(count <= MAX_ROWS and size <= MAX_JOURNAL and len(line) <= MAX_ROW + 1 and line.endswith(b'\n'),
                    'journal-input-bound')
            previous, last_time, context = verify_event(line[:-1], current, count, previous, last_time, seen, context,
                                                        binding_owners, observed_actors, creator_grant)
            digest.update(line)
    require(count > 0 and str(count) == transfer['journal_count'] and previous == transfer['journal_head']
            and digest.hexdigest() == transfer['journal_sha256'], 'journal-tip-mismatch')
    return last_time


def verify_evidence(path, observation, transfer, current, *, source, last_accepted):
    name = 'source_fence_sha256' if source else 'destination_readback_sha256'
    raw = private_file(path, MAX_EVIDENCE)
    require(sha(raw) == transfer[name], 'evidence-digest-mismatch')
    evidence = exact_record(raw, EVIDENCE_FIELDS, MAX_EVIDENCE)
    protocol = 'stead.project-source-fence/1' if source else 'stead.project-destination-readback/1'
    home = current['home'] if source else transfer['destination_home']
    epoch = current['authority_epoch'] if source else transfer['destination_epoch']
    writer_state = 'retired' if source else 'write-disabled'
    require(evidence['protocol'] == protocol and evidence['home'] == home and evidence['authority_epoch'] == epoch
            and evidence['writer_state'] == writer_state
            and all(evidence[key] == transfer[key] for key in ('migration_id', 'project_id', 'journal_head', 'snapshot_sha256'))
            and match(TOKEN, evidence['observation_sha256']), 'evidence-scope-mismatch')
    if source:
        raw_status = private_file(observation, MAX_EVIDENCE)
        require(sha(raw_status) == evidence['observation_sha256'], 'evidence-digest-mismatch')
        status = exact_record(raw_status, SOURCE_STATUS_FIELDS, MAX_EVIDENCE)
        number(status['retired_at_ms'])
        require(status['protocol'] == 'stead.project-retirement-status/1'
                and status['destination_home'] == transfer['destination_home']
                and int(status['retired_at_ms']) >= last_accepted
                and all(status[key] == evidence[key] for key in (
                    'home', 'project_id', 'authority_epoch', 'journal_head', 'migration_id', 'writer_state')),
                'native-source-status-mismatch')
    else:
        verify_blob(observation, MAX_OBSERVATION, evidence['observation_sha256'])


def verify(directory, trust, signed, journal, snapshot, source_fence, source_observation, destination_readback,
           destination_observation):
    pins = exact_record(private_file(trust, 4_096), TRUST_FIELDS, 4_096)
    require(pins['protocol'] == 'stead.project-handoff-trust/1' and pins['source_ed25519'] != pins['destination_ed25519'],
            'independent-operator-keys-required')
    current_raw = private_file(directory, 4_096)
    require(sha(current_raw) == pins['current_directory_sha256'], 'current-directory-pin-mismatch')
    current = exact_record(current_raw, DIRECTORY_FIELDS, 4_096)
    require(current['protocol'] == DIRECTORY and current['authority_epoch'] == '1'
            and match(UUID, current['project_id']) and match(UUID, current['custody_id'])
            and match(SHIP, current['home']), 'first-move-directory-required')
    origin(current['origin'])
    raw = private_file(signed, 8_192)
    envelope = decoded(raw, 8_192)
    shape(envelope, {'transfer', 'source_signature', 'destination_signature'})
    require(canonical(envelope) == raw, 'noncanonical-record')
    transfer = envelope['transfer']
    strings(transfer, TRANSFER_FIELDS)
    require(transfer['protocol'] == HANDOFF and match(UUID, transfer['migration_id'])
            and transfer['prior_directory_sha256'] == pins['current_directory_sha256']
            and transfer['project_id'] == current['project_id'] and transfer['custody_id'] == current['custody_id'],
            'handoff-scope-mismatch')
    require(transfer['destination_home'] == pins['destination_home'] and match(SHIP, transfer['destination_home'])
            and transfer['destination_home'] != current['home'] and transfer['destination_origin'] == pins['destination_origin']
            and transfer['destination_origin'] != current['origin'] and transfer['destination_epoch'] == '2', 'handoff-destination-mismatch')
    origin(transfer['destination_origin'])
    for field in ('snapshot_sha256', 'journal_sha256', 'journal_head', 'source_fence_sha256', 'destination_readback_sha256'):
        require(match(TOKEN, transfer[field]), 'handoff-digest-shape')
    number(transfer['journal_count'])
    require(int(transfer['journal_count']) <= MAX_ROWS, 'journal-input-bound')
    verify_signature(pins['source_ed25519'], envelope['source_signature'], b'source', transfer)
    verify_signature(pins['destination_ed25519'], envelope['destination_signature'], b'destination', transfer)
    verify_blob(snapshot, MAX_SNAPSHOT, transfer['snapshot_sha256'])
    last_accepted = verify_journal(journal, current, transfer)
    verify_evidence(source_fence, source_observation, transfer, current, source=True, last_accepted=last_accepted)
    verify_evidence(destination_readback, destination_observation, transfer, current, source=False, last_accepted=last_accepted)
    return {'protocol': 'stead.project-handoff-verification/1', 'status': 'verified-candidate', 'authority_changed': False,
            'migration_id': transfer['migration_id'], 'transfer_sha256': sha(canonical(transfer)),
            'candidate_directory': {'protocol': 'stead.project-directory-candidate/1', 'project_id': current['project_id'],
                                    'custody_id': current['custody_id'], 'home': transfer['destination_home'],
                                    'origin': transfer['destination_origin'], 'authority_epoch': transfer['destination_epoch']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'trust', 'signed', 'journal', 'snapshot', 'source-fence', 'source-observation',
                 'destination-readback', 'destination-observation'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        sys.stdout.buffer.write(encoded(verify(**vars(args))))
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print('Cross-ship handoff evidence verification failed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

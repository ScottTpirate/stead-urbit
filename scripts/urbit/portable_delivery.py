"""Capture and verify the Home's read-only Code delivery audit over HTTPS."""
from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re

from execution_policy import GuardError
from portable_code import ref_name, write_archive
from portable_recovery import (
    HTTPSQueries, OID, Reads, RecoveryError, TOKEN, UUID, decoded, encoded, identity,
    match, number, private_file, require, session_file, sha, shape, text,
)

PROTOCOL = 'stead.code-delivery-audit/1'
FORMAT = 'stead.portable-delivery/1'
PAGE = 4
MAX_ROWS = 544
MAX_ROW = 12 * 1024
MAX_TRANSCRIPT = 768 * 1024
MAX_FILE = 1024 * 1024
ZERO = '0' * 40
LOSSES = [
    'Read-only evidence. No grant, credential, session, key, upload or authority is exported.',
    'Retained build lease and delegation records show their saved state. Superseded attempts are absent.',
    'Source Git objects and Work text are separate exports. This artifact does not restore a Home.',
    'Snapshot and file digests establish byte integrity, not a signature from the Home.',
]
HEADER = {'protocol', 'home', 'project_id', 'repository_id', 'epoch', 'repository_revision', 'records'}
REVIEW_KEY = {'proposal_id', 'revision'}
SCHEMA = {
    'ref': {'ref_hex', 'oid'},
    'protection': {'ref_hex'},
    'proposal': REVIEW_KEY | {'author', 'work_id', 'ref_hex', 'base_oid', 'head_oid', 'delegation_id'},
    'approval': REVIEW_KEY | {'reviewer'},
    'ref_receipt': {'request_id', 'repository_revision', 'actor', 'digest', 'changes', 'proposal_id', 'proposal_revision'},
    'ref_change': {'request_id', 'index', 'ref_hex', 'prior_oid', 'target_oid'},
    'build': REVIEW_KEY | {'job_id', 'requester', 'source', 'recipe', 'stage', 'assigned_worker', 'lease_worker',
                           'attempt', 'lease_expires_ms', 'output_sha256', 'outcome', 'artifact_base64'},
    'release': REVIEW_KEY | {'release_id', 'job_id', 'actor', 'source', 'recipe', 'output_sha256', 'outcome'},
    'delegation': {'delegation_id', 'stage', 'work_id', 'ref_hex', 'sponsor', 'worker', 'expires_at_ms'},
}


def snapshot(header, records):
    raw = encoded(header) + b''.join(encoded(row) for row in records)
    require(len(raw) <= MAX_TRANSCRIPT + 512, 'audit-size')
    return sha(PROTOCOL.encode() + b'\0' + raw)


def check_header(header):
    shape(header, HEADER)
    require(header['protocol'] == PROTOCOL and isinstance(header['home'], str)
            and re.fullmatch(r'~[a-z-]{3,63}', header['home'])
            and match(UUID, header['project_id']) and match(UUID, header['repository_id']), 'audit-scope')
    number(header['epoch'])
    number(header['repository_revision'], positive=False)
    number(header['records'], positive=False)
    require(int(header['repository_revision']) <= 32 and int(header['records']) <= MAX_ROWS, 'audit-count')


def validate(value):
    shape(value, {'format', 'snapshot', 'header', 'records', 'losses'})
    require(value['format'] == FORMAT and value['losses'] == LOSSES, 'audit-format')
    header, records = value['header'], value['records']
    check_header(header)
    require(isinstance(records, list) and len(records) == int(header['records']), 'audit-count')
    refs, protection, proposals, approvals, receipts, changes, builds, releases, grants = ({}, set(), {}, {}, {}, {}, {}, {}, {})
    for row in records:
        require(isinstance(row, dict) and isinstance(row.get('kind'), str) and row['kind'] in SCHEMA, 'audit-row')
        kind = row['kind']
        shape(row, SCHEMA[kind] | {'kind'})
        require(len(encoded(row)) <= MAX_ROW + 1, 'audit-row-size')
        for field, item in row.items():
            text(item, MAX_ROW)
            if field in {'actor', 'author', 'reviewer', 'work_id', 'proposal_id', 'request_id', 'delegation_id',
                         'job_id', 'release_id', 'requester', 'assigned_worker', 'lease_worker', 'sponsor', 'worker'}:
                require(match(UUID, item) or (item == '' and (field == 'lease_worker'
                        or field == 'delegation_id' and kind == 'proposal'
                        or field == 'proposal_id' and kind == 'ref_receipt')), 'audit-id')
            elif field == 'oid' or field.endswith('_oid'):
                require(match(OID, item), 'audit-oid')
            elif field == 'ref_hex':
                ref_name(item, branch=kind in {'proposal', 'delegation', 'protection'})
            elif field in {'digest', 'source', 'recipe', 'output_sha256'}:
                require(match(TOKEN, item) or (field == 'output_sha256' and kind == 'build' and item == ''), 'audit-digest')
            elif field in {'repository_revision', 'revision', 'proposal_revision', 'changes', 'index',
                           'attempt', 'lease_expires_ms', 'expires_at_ms'}:
                if item == '' and field in {'proposal_revision', 'attempt', 'lease_expires_ms'}:
                    continue
                number(item, positive=field != 'index')

        if kind == 'ref':
            require(row['ref_hex'] not in refs and row['oid'] != ZERO, 'duplicate-ref')
            refs[row['ref_hex']] = row['oid']
        elif kind == 'protection':
            require(row['ref_hex'] not in protection, 'duplicate-protection')
            protection.add(row['ref_hex'])
        elif kind in {'proposal', 'approval'}:
            target = proposals if kind == 'proposal' else approvals
            key = (row['proposal_id'], int(row['revision']))
            require(key not in target and 1 <= key[1] <= 64, 'duplicate-revision')
            target[key] = row
        elif kind == 'ref_change':
            key = row['request_id'], int(row['index'])
            require(key not in changes and key[1] < 8 and row['prior_oid'] != row['target_oid'], 'duplicate-change')
            changes[key] = row
        else:
            targets = {'ref_receipt': (receipts, 'request_id'), 'build': (builds, 'job_id'),
                       'release': (releases, 'release_id'), 'delegation': (grants, 'delegation_id')}
            target, field = targets[kind]
            require(row[field] not in target, 'duplicate-audit-id')
            target[row[field]] = row

    require(len(refs) <= 16 and len(protection) <= 16 and len(proposals) <= 64 and len(approvals) <= 64
            and len(receipts) == int(header['repository_revision']) and len(builds) <= 32
            and len(releases) <= 32 and len(grants) <= 32, 'audit-count')
    for key, item in proposals.items():
        require(item['base_oid'] != item['head_oid'] and item['head_oid'] != ZERO, 'proposal-oid')
        if key[1] > 1:
            prior = proposals.get((key[0], key[1] - 1))
            require(prior is not None and all(prior[k] == item[k] for k in ('work_id', 'author', 'ref_hex')), 'proposal-history')
        if item['delegation_id']:
            grant = grants.get(item['delegation_id'])
            require(grant is not None and grant['worker'] == item['author']
                    and all(grant[k] == item[k] for k in ('work_id', 'ref_hex')), 'proposal-delegation')
    require(all(key in proposals and row['reviewer'] != proposals[key]['author']
                for key, row in approvals.items()), 'approval-link')
    require(all(row['stage'] in {'granted', 'revoked'} and row['sponsor'] != row['worker']
                for row in grants.values()), 'delegation-stage')
    current, consumed, merged = {}, set(), set()
    for index, row in enumerate(sorted(receipts.values(), key=lambda entry: int(entry['repository_revision'])), 1):
        count = int(row['changes'])
        require(int(row['repository_revision']) == index and 1 <= count <= 8, 'receipt-order')
        require(bool(row['proposal_id']) == bool(row['proposal_revision']), 'merge-key')
        unique = set()
        for offset in range(count):
            key = row['request_id'], offset
            delta = changes.get(key)
            require(delta is not None and delta['ref_hex'] not in unique
                    and current.get(delta['ref_hex'], ZERO) == delta['prior_oid'], 'receipt-ref-cas')
            consumed.add(key)
            unique.add(delta['ref_hex'])
            if delta['target_oid'] == ZERO:
                current.pop(delta['ref_hex'], None)
            else:
                current[delta['ref_hex']] = delta['target_oid']
        if row['proposal_id']:
            key = row['proposal_id'], int(row['proposal_revision'])
            item = proposals.get(key)
            delta = changes[row['request_id'], 0]
            require(count == 1 and key not in merged and item is not None and key in approvals
                    and row['actor'] != item['author'] and delta['ref_hex'] == item['ref_hex']
                    and delta['prior_oid'] == item['base_oid'] and delta['target_oid'] == item['head_oid'], 'merge-link')
            merged.add(key)
    require(current == refs and consumed == set(changes), 'receipt-ref-inventory')
    for row in builds.values():
        key = row['proposal_id'], int(row['revision'])
        require(key in proposals and row['stage'] in {'queued', 'leased', 'finished', 'cancelled'}
                and row['assigned_worker'] not in {row['requester'], proposals[key]['author']}, 'build-link')
        if row['stage'] in {'leased', 'finished'}:
            require(row['lease_worker'] == row['assigned_worker'] and row['attempt'] in {'1', '2', '3'}
                    and bool(row['lease_expires_ms']), 'build-lease')
        else:
            require(not any(row[k] for k in ('lease_worker', 'attempt', 'lease_expires_ms')), 'build-lease')
        if row['stage'] == 'finished':
            try:
                raw = base64.b64decode(row['artifact_base64'], validate=True)
            except ValueError:
                raise RecoveryError('artifact-encoding') from None
            require(0 < len(raw) <= 8192 and base64.b64encode(raw).decode('ascii') == row['artifact_base64']
                    and row['outcome'] in {'passed', 'failed'} and sha(raw) == row['output_sha256'], 'artifact-evidence')
        else:
            require(not any(row[k] for k in ('artifact_base64', 'output_sha256', 'outcome')), 'unfinished-artifact')
    for row in releases.values():
        job = builds.get(row['job_id'])
        key = row['proposal_id'], int(row['revision'])
        require(job is not None and key in merged and row['outcome'] == 'passed'
                and job['stage'] == 'finished' and row['actor'] not in {job['requester'], job['assigned_worker'], proposals[key]['author']}
                and all(row[k] == job[k] for k in REVIEW_KEY | {'source', 'recipe', 'output_sha256', 'outcome'}), 'release-link')
    require(match(TOKEN, value['snapshot']) and snapshot(header, records) == value['snapshot'], 'audit-snapshot')
    return value


def collect(fetch, project, home, epoch):
    header, token, records, offset = None, '', [], 0
    while True:
        page = decoded(fetch({'protocol': 'stead.code/1', 'project_id': project, 'action': 'delivery-export',
                              'offset': str(offset), 'snapshot': token}))
        shape(page, {'protocol', 'status', 'snapshot', 'total', 'next_offset', 'header', 'records'})
        require(page['protocol'] == 'stead.code/1' and page['status'] == 'delivery-export'
                and match(TOKEN, page['snapshot']), 'audit-page')
        header_line = text(page['header'], 512).encode() + b'\n'
        received = decoded(header_line, 513)
        check_header(received)
        require(encoded(received) == header_line and received['home'] == home and received['project_id'] == project
                and received['repository_id'] == project and received['epoch'] == epoch, 'audit-page-scope')
        if header is None:
            header, token = received, page['snapshot']
        require(received == header and page['snapshot'] == token and page['total'] == header['records'], 'audit-changed')
        total = int(header['records'])
        raw = text(page['records'], PAGE * (MAX_ROW + 1)).encode()
        lines = raw.splitlines(keepends=True)
        require(len(lines) == min(PAGE, total - offset), 'audit-page-count')
        for line in lines:
            row = decoded(line, MAX_ROW + 1)
            require(encoded(row) == line, 'audit-canonical-row')
            records.append(row)
        offset += len(lines)
        require(page['next_offset'] == (str(offset) if offset < total else ''), 'audit-page-cursor')
        if offset == total:
            break
    return validate({'format': FORMAT, 'snapshot': token, 'header': header, 'records': records, 'losses': LOSSES})


def capture(credentials, project, ca_file):
    require(match(UUID, project), 'audit-project')
    transport = HTTPSQueries(credentials, ca_file=ca_file)
    reads = Reads(transport)
    _, initial = reads.one('identity')
    identity(initial, credentials['principal_id'])
    (epoch, _), metadata = reads.one('project', project)
    require(metadata.get('role') == 'maintainer', 'audit-maintainer-required')
    artifact = collect(lambda body: transport._post('/stead/api/code', body), project, initial['home'], epoch)
    _, current = reads.one('identity')
    identity(current, credentials['principal_id'])
    (current_epoch, _), metadata = reads.one('project', project)
    require(current == initial and current_epoch == epoch and metadata.get('role') == 'maintainer', 'audit-member-changed')
    return artifact


def read(path, expected):
    raw = private_file(path, MAX_FILE)
    require(match(TOKEN, expected) and sha(raw) == expected, 'audit-file-digest')
    value = validate(decoded(raw, MAX_FILE))
    require(encoded(value) == raw, 'audit-file-canonical')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    output = commands.add_parser('capture')
    output.add_argument('--session-file', type=Path, required=True)
    output.add_argument('--project', required=True)
    output.add_argument('--ca-file', type=Path)
    output.add_argument('--output', type=Path, required=True)
    verify = commands.add_parser('verify')
    verify.add_argument('artifact', type=Path)
    verify.add_argument('--sha256', required=True)
    args = parser.parse_args()
    try:
        if args.mode == 'capture':
            value = capture(session_file(args.session_file), args.project, args.ca_file)
            digest = write_archive(args.output, value)
        else:
            value, digest = read(args.artifact, args.sha256), args.sha256
        print(encoded({'status': 'captured' if args.mode == 'capture' else 'integrity-verified',
                       'snapshot': value['snapshot'], 'sha256': digest, 'records': len(value['records'])}).decode(), end='')
    except (OSError, RecoveryError, GuardError) as error:
        parser.exit(1, 'Delivery audit failed (' + (str(error) if isinstance(error, RecoveryError) else 'local-file') + ').\n')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Inspect an explicitly granted read-only Work/Docs copy for one project."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import re
import sys

import portable_recovery as export


SCOPE = 'shared-work-docs'
GRANT_FIELDS = {'protocol', 'custodian', 'scope', 'home', 'origin', 'project_id',
                'principal_id', 'authority_epoch', 'generation', 'artifact_sha256', 'expires_at'}
READABLE_FILE = re.compile(r'(?:index\.json|work/[0-9a-f-]{36}\.md|docs/[0-9a-f-]{36}/[0-9a-f-]{36}\.md)')


def timestamp(value):
    export.require(isinstance(value, str) and len(value) <= 40, 'replica-time')
    stamp = datetime.fromisoformat(value)
    export.require(stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0), 'replica-time')
    return stamp


def read_grant(path, expected_sha256, custodian):
    raw = export.private_file(path, 4096)
    export.require(export.match(export.TOKEN, expected_sha256) and export.sha(raw) == expected_sha256, 'replica-grant-digest')
    grant = export.decoded(raw, 4096)
    export.shape(grant, GRANT_FIELDS)
    export.require(grant['protocol'] == 'stead.replica-grant/1' and grant['scope'] == SCOPE, 'replica-scope')
    export.require(isinstance(custodian, str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', custodian)
                   and grant['custodian'] == custodian, 'replica-custodian')
    export.require(all(export.match(export.UUID, grant[key]) for key in ('project_id', 'principal_id')), 'replica-identifiers')
    export.require(all(export.match(export.TOKEN, grant[key]) for key in ('generation', 'artifact_sha256')), 'replica-digests')
    export.require(isinstance(grant['home'], str) and re.fullmatch(r'~[a-z-]{3,63}', grant['home']), 'replica-home')
    export.origin(grant['origin'])
    export.number(grant['authority_epoch'])
    timestamp(grant['expires_at'])
    return grant


def inspect(artifact, grant, *, now=None, query=None, read=None):
    files, result = export.verify(artifact, expected_sha256=grant['artifact_sha256'], require_private=True)
    records = export.decoded(files['records.json'], export.MAX_CAPTURE)
    receipt = export.decoded(files['capture.json'], 2 * 1024 * 1024)
    for key in ('project_id', 'origin', 'authority_epoch', 'generation'):
        export.require(grant[key] == receipt[key], 'replica-snapshot-binding')
    export.require(grant['home'] == receipt['identity']['home'] and grant['principal_id'] == receipt['identity']['principal_id'], 'replica-identity-binding')
    export.require(all(row['visibility'] == 'shared' for row in records['containers'] + records['documents']), 'replica-private-content')
    captured = timestamp(receipt['finished_at'])
    expiry = timestamp(grant['expires_at'])
    checked = datetime.now(timezone.utc) if now is None else now
    export.require(captured <= checked and timedelta(0) < expiry - captured <= timedelta(days=7), 'replica-grant-window')

    freshness = 'expired' if checked >= expiry else 'offline-unchecked'
    if freshness != 'expired' and query is not None:
        reads = export.Reads(query)
        _, identity = reads.one('identity')
        export.identity(identity, grant['principal_id'])
        export.require(identity['home'] == grant['home'], 'replica-identity-binding')
        # The authorized containers view carries the project-wide generation.
        stamp, boxes = reads.walk('containers', grant['project_id'], bound=32)
        freshness = 'observed-current' if stamp == (grant['authority_epoch'], grant['generation']) else 'stale'
        if any(row.get('visibility') != 'shared' for row in boxes):
            freshness = 'stale'
        if now is None and datetime.now(timezone.utc) >= expiry:
            freshness = 'expired'

    body = None
    if read is not None:
        export.require(freshness in {'observed-current', 'offline-unchecked'}, 'replica-read-denied')
        export.require(READABLE_FILE.fullmatch(read) and read in files, 'replica-file-denied')
        body = files[read].decode('utf-8')
    return {'protocol': 'stead.replica-status/1', 'mode': 'read-only', 'scope': SCOPE,
            'custodian': grant['custodian'], 'home': grant['home'], 'project_id': grant['project_id'],
            'authority_epoch': grant['authority_epoch'], 'generation': grant['generation'],
            'captured_at': receipt['finished_at'], 'expires_at': grant['expires_at'], 'freshness': freshness,
            'work': result['work'], 'documents': result['documents'], 'body': body}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact')
    parser.add_argument('--grant', required=True)
    parser.add_argument('--grant-sha256', required=True, help='Independently received from the custody approver')
    parser.add_argument('--custodian', required=True)
    parser.add_argument('--session-file', help='Optional individual source session to check freshness')
    parser.add_argument('--ca-file')
    parser.add_argument('--read', help='One file listed in index.json, or index.json itself')
    args = parser.parse_args(argv)
    try:
        grant = read_grant(args.grant, args.grant_sha256, args.custodian)
        query = None
        if args.session_file:
            credentials = export.session_file(args.session_file)
            export.require(credentials['origin'] == grant['origin'] and credentials['principal_id'] == grant['principal_id'], 'replica-session-binding')
            query = export.HTTPSQueries(credentials, ca_file=args.ca_file)
        print(json.dumps(inspect(args.artifact, grant, query=query, read=args.read), sort_keys=True))
        return 0
    except (OSError, TypeError, ValueError, KeyError, OverflowError):
        print('Replica verification or read denied.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

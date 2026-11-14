#!/usr/bin/env python3
"""Restore the Git pack currently accepted by Home into a private directory."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import git_pack_store as store
from portable_recovery import (MAX_RESPONSE, TOKEN, UUID, HTTPSQueries, Reads, decoded, identity,
                               match, number, require, session_file, shape)


def observe(connection, principal, project):
    _, who = Reads(connection).one('identity')
    identity(who, principal)
    report = decoded(connection.pack_view(project))
    fields = {'protocol', 'status', 'snapshot', 'authority_epoch', 'object_count',
              'head', 'refs', 'request_id', 'accepted_at_ms'}
    if isinstance(report, dict):
        for field in ('generation', 'generation_limit'):
            if field in report:
                fields.add(field)
                number(report[field], positive=field == 'generation_limit')
    shape(report, fields)
    require(report['protocol'] == 'stead.code/1' and report['status'] == 'external'
            and match(TOKEN, report['snapshot']) and match(UUID, report['request_id']), 'accepted-pack-required')
    number(report['authority_epoch'])
    number(report['object_count'])
    number(report['accepted_at_ms'])
    require(int(report['object_count']) <= store.MAX_OBJECTS, 'object-count-bound')
    require(isinstance(report['refs'], str) and len(report['refs']) <= MAX_RESPONSE, 'ref-inventory')
    refs = decoded(report['refs'].encode('ascii'))
    store.validate_refs(refs, report['head'])
    scope = {'home': who['home'], 'project_id': project, 'repository_id': project,
             'authority_epoch': report['authority_epoch']}
    store.validate_scope(scope)
    return scope, report, refs


def restore(connection, principal, project, storage, destination, git):
    require(match(UUID, project), 'project-scope')
    observed = observe(connection, principal, project)
    scope, report, refs = observed

    def authorize(manifest):
        require(manifest['head'] == report['head'] and manifest['refs'] == refs
                and manifest['object_count'] == int(report['object_count']), 'home-pack-differs')
        require(observe(connection, principal, project) == observed, 'home-acceptance-changed')

    restored = store.restore(storage, report['snapshot'], scope, destination, git, authorize=authorize)
    return {'protocol': 'stead.git-pack-readback/1', 'status': 'restored', 'scope': scope,
            'snapshot': report['snapshot'], 'request_id': report['request_id'], 'object_count': restored['object_count']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('store', type=Path, help='Operator-owned private pack store')
    parser.add_argument('destination', type=Path, help='New repository path in an operator-owned private directory')
    parser.add_argument('--project', required=True)
    parser.add_argument('--session-file', required=True)
    parser.add_argument('--ca-file')
    parser.add_argument('--git', default='git')
    args = parser.parse_args(argv)
    try:
        git = shutil.which(args.git)
        require(git, 'stock-git-required')
        git = str(Path(git).resolve(strict=True))
        credentials = session_file(args.session_file)
        connection = HTTPSQueries(credentials, ca_file=args.ca_file)
        result = restore(connection, credentials['principal_id'], args.project, args.store, args.destination, git)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print('Accepted pack restoration failed.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

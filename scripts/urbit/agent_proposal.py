"""Read a delegated Work brief and submit an exact, already pushed Git change.

Brief/2 checks the execution contract immediately before submission. The current
Code submit protocol has no execution pin: a concurrent goal edit after this
read is not atomically rejected by the native authority. This preflight is not
the final publication fence reserved for the successor Run protocol.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

from portable_code import ref_name
from portable_recovery import (
    HTTPSQueries, OID, Reads, RecoveryError, TOKEN, UUID, decoded, encoded, identity,
    match, number, private_file, require, session_file, shape, text,
)


BRIEF = {'protocol', 'project_id', 'work_id', 'delegation_id', 'worker_ship',
         'target_ref', 'expires_at_ms', 'work_revision', 'title', 'description', 'work_url'}
BRIEF2 = BRIEF - {'work_revision'} | {'execution_contract_revision', 'execution_contract_digest'}
DELEGATION = {'delegation_id', 'worker_ship', 'ref', 'expires_at_ms', 'status', 'proposals', 'can_revoke'}
REVISION = re.compile(r'(?:[1-9]|[1-5][0-9]|6[0-4])')


def context(brief, credentials, read, code):
    require(isinstance(brief, dict) and brief.get('protocol') in ('stead.agent-brief/1', 'stead.agent-brief/2'), 'agent-brief')
    contract = brief['protocol'] == 'stead.agent-brief/2'
    shape(brief, BRIEF2 if contract else BRIEF)
    project, work, grant = (brief[name] for name in ('project_id', 'work_id', 'delegation_id'))
    require(all(match(UUID, key) for key in (project, work, grant)), 'agent-brief')
    require(brief['work_url'] == credentials['origin'] + f'/stead/#work/{project}/{work}', 'agent-brief-origin')
    target = text(brief['target_ref'], 128)
    ref_name(target.encode('utf-8').hex(), branch=True)
    if contract:
        number(brief['execution_contract_revision'])
        require(match(TOKEN, brief['execution_contract_digest']), 'agent-contract-digest')
    else:
        number(brief['work_revision'])
    number(brief['expires_at_ms'])
    _, member = read.one('identity')
    identity(member, credentials['principal_id'])
    require(member['identity_ship'] == brief['worker_ship'], 'agent-identity-mismatch')

    listing = code(project, 'work-delegations', work_id=work)
    shape(listing, {'protocol', 'status', 'work_id', 'rows'})
    require(listing['protocol'] == 'stead.code/1' and listing['status'] == 'work-delegations'
            and listing['work_id'] == work and isinstance(listing['rows'], str), 'agent-delegation-evidence')
    rows = decoded(listing['rows'].encode('utf-8'))
    require(isinstance(rows, dict) and len(rows) <= 32 and grant in rows, 'agent-delegation-unavailable')
    saved = rows[grant]
    shape(saved, DELEGATION)
    require(saved['status'] == 'active' and saved['delegation_id'] == grant
            and saved['worker_ship'] == member['identity_ship'] and saved['ref'] == target
            and saved['expires_at_ms'] == brief['expires_at_ms'], 'agent-delegation-unavailable')
    _, ticket = read.one('work', project, resource=work)
    require(ticket.get('resource_id') == work and ticket.get('kind') == 'work', 'agent-work-unavailable')
    if contract:
        require(ticket.get('execution_contract_protocol') == 'stead.work-contract/1'
                and ticket.get('execution_contract_revision') == brief['execution_contract_revision']
                and ticket.get('execution_contract_digest') == brief['execution_contract_digest'],
                'agent-work-contract-changed')
    else:
        require(ticket.get('resource_revision') == brief['work_revision'], 'agent-work-revision-changed')
    return brief | {'title': text(ticket.get('title'), 800), 'description': text(ticket.get('description'), 8192)}


def propose(brief, credentials, read, code, *, revision, base, head):
    require(match(REVISION, revision) and all(match(OID, value) for value in (base, head)) and base != head, 'agent-exact-revision')
    approved = context(brief, credentials, read, code)
    project, grant = approved['project_id'], approved['delegation_id']
    selection = {'proposal_id': grant, 'revision': revision}
    request = selection | {'work_id': approved['work_id'], 'ref': approved['target_ref'],
                           'base_oid': base, 'head_oid': head, 'delegation_id': grant}
    receipt = code(project, 'submit', **request)
    shape(receipt, {'protocol', 'status'})
    require(receipt['protocol'] == 'stead.code/1' and receipt['status'] in ('accepted', 'replayed'), 'agent-proposal-unconfirmed')
    proposal = code(project, 'proposal', **selection)
    require(proposal.get('protocol') == 'stead.code/1' and proposal.get('status') == 'proposal'
            and proposal.get('author') == credentials['principal_id']
            and all(proposal.get(name) == value for name, value in request.items() if name != 'delegation_id'),
            'agent-proposal-readback')
    return {'protocol': 'stead.agent-proposal/1', 'status': 'submitted-for-review',
            'project_id': project, **request}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief', type=Path, required=True, help='Private JSON copied from the Work item')
    parser.add_argument('--session-file', type=Path, required=True, help='The agent’s own approved Home session')
    parser.add_argument('--ca', type=Path)
    parser.add_argument('--base')
    parser.add_argument('--head')
    parser.add_argument('--revision', default='1')
    args = parser.parse_args(argv)
    if (args.base is None) != (args.head is None):
        parser.error('--base and --head are provided together')
    try:
        brief = decoded(private_file(args.brief, 16384), 16384)
        credentials = session_file(args.session_file)
        https = HTTPSQueries(credentials, ca_file=args.ca)
        read = Reads(https)

        def code(project, action, **fields):
            payload = {'protocol': 'stead.code/1', 'project_id': project, 'action': action, **fields}
            return decoded(https._post('/stead/api/code', payload))

        result = (context(brief, credentials, read, code) if args.base is None else
                  propose(brief, credentials, read, code, revision=args.revision, base=args.base, head=args.head))
        print(encoded(result).decode().strip())
    except (ValueError, OSError, TypeError, KeyError) as failure:
        code = str(failure) if isinstance(failure, RecoveryError) else 'agent-handoff-failed'
        parser.exit(1, f'Stead could not confirm the agent handoff ({code}).\n')


if __name__ == '__main__':
    main()

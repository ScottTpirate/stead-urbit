"""Finite public-SDK conformance cases; no simulated business state."""
import hashlib
import json


def uid(number):
    return '019939ba-4000-7000-8000-' + f'{number:012x}'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def run(sdk, owner, check, now):
    sequence = 40000

    def request(mode, value):
        nonlocal sequence
        sequence += 1
        return {'protocol': 'stead.' + mode + '/3', **value, 'request_id': uid(sequence)}

    def query(kind, project='', **fields):
        return request('query', {'kind': kind, 'project_id': project, 'container_id': '',
            'resource_id': '', 'cursor': '', 'search': '', **fields})

    def command(operation, resource, revision, payload, project=uid(1)):
        return request('command', {'operation': operation, 'resource_id': resource,
            'project_id': project, 'expected_revision': str(revision), 'authority_epoch': '1', 'payload': payload})

    def update(action, handle=None, **fields):
        handle = handle or {}
        return request('updates', {'action': action, 'watch_id': handle.get('watch_id', ''),
            'cursor': handle.get('cursor', '') if action != 'cancel' else '',
            'kind': '', 'project_id': '', 'container_id': '', 'resource_id': '', 'search': '', **fields})

    def accepted(value, result, actor='~bus'):
        digest = hashlib.sha256(b'stead.command/3\0' + canonical(value).encode()).hexdigest()
        principal, binding = (102, 202) if actor == '~bus' else (104, 204)
        check('accepted:' + value['operation'] + ':' + value['request_id'],
            result.get('protocol') == 'stead.receipt/3' and result.get('status') == 'accepted' and result.get('request_id') == value['request_id']
            and result.get('identity_ship') == actor and result.get('authentication') == 'native-sender/1'
            and result.get('canonical_sha256') == digest and result.get('project_id') == value['project_id']
            and result.get('resource_id') == value['resource_id'] and result.get('operation') == value['operation']
            and result.get('authority_epoch') == value['authority_epoch']
            and result.get('resource_revision') == str(int(value['expected_revision']) + 1)
            and result.get('principal_id') == uid(principal) and result.get('binding_id') == uid(binding)
            and result.get('binding_revision') == '1' and result.get('authentication_strength') == 'native-sender'
            and result.get('session_audit_id') == '' and result.get('runtime') == 'isolated-fake')

    caps = query('capabilities')
    result = sdk('query', caps)
    check('public-capabilities-from-current-native-member', result.get('protocol') == 'stead.query-result/3'
        and result.get('request_id') == caps['request_id'] and result.get('status') == 'read'
        and result.get('kind') == 'capabilities' and len(result.get('rows', {})) == 1)
    project_payload = {'organization_id': uid(5), 'owning_team_id': uid(6),
        'title': 'Independent SDK', 'project_key': 'SDK', 'preset': 'general'}
    create = command('project.create', uid(1), 0, project_payload)
    for mode, seed in (('command', create), ('query', query('projects')), ('updates', update('open', kind='projects'))):
        for version in ('1', '2', '999'):
            bad = request(mode, seed | {'protocol': 'stead.' + mode + '/' + version})
            result = sdk(mode, bad)
            expected = {'protocol': 'stead.result/3', 'status': 'rejected', 'error': 'unsupported_version',
                'request_id': bad['request_id'], 'canonical_sha256': hashlib.sha256(
                    ('stead.' + mode + '/3\0' + canonical(bad)).encode()).hexdigest()}
            check(mode + '-unsupported-version-' + version + '-correlated', result == expected)
    check('rejected-version-created-no-project', sdk('query', query('projects')).get('rows') == {})
    result = sdk('command', create)
    accepted(create, result)
    check('actual-public-caller-principal', result.get('principal_id') == uid(102))
    check('same-command-recovers-exact-receipt', sdk('command', create) == result)
    altered = {**create, 'payload': create['payload'] | {'title': 'Must not overwrite'}}
    check('request-id-reuse-with-changed-bytes-rejected', sdk('command', altered).get('error') == 'request_id_reuse')
    work_payload = {'title': 'Public SDK Work', 'description': 'Synthetic package-only client',
                    'type': 'task', 'status': 'todo', 'priority': 'medium'}
    work = command('work.create', uid(10), 0, work_payload)
    accepted(work, sdk('command', work))
    read = sdk('query', query('work', uid(1)))
    check('allowed-work-authoritative-readback', read.get('status') == 'read' and len(read.get('rows', {})) == 1
          and next(iter(read['rows'].values())).get('title') == work_payload['title'])
    changed = command('work.update', uid(10), 1, work_payload | {'title': 'Public SDK Work updated'})
    accepted(changed, sdk('command', changed))
    before_negatives = sdk('query', query('work', uid(1)))['rows']
    row = next(iter(before_negatives.values()))
    check('accepted-update-has-exact-id-revision-and-payload', row['resource_id'] == uid(10) and row['resource_revision'] == '2'
          and all(row[key] == value for key, value in changed['payload'].items()))
    stale = command('work.update', uid(10), 1, work_payload | {'title': 'Stale overwrite'})
    check('public-stale-save-revision-conflict', sdk('command', stale).get('error') == 'revision_conflict')
    # SDK rejection and Home rejection are separate observations. The malformed
    # and oversized carriers never become committed business outcomes.
    for label, raw in (('malformed-json', '{'), ('oversized-input', 'x' * 65537)):
        result = sdk('command', raw)
        check('public-client-' + label + '-fails-closed', result == {
            'protocol': 'stead.sdk-error/1', 'status': 'failed', 'error': 'request_unconfirmed'})
    malformed = command('work.create', uid(11), 0, work_payload) | {'unknown': 'field'}
    check('well-formed-invalid-envelope-fails-closed', sdk('command', malformed) == {
        'protocol': 'stead.sdk-error/1', 'status': 'failed', 'error': 'request_unconfirmed'})
    rows = sdk('query', query('work', uid(1))).get('rows', {})
    check('negative-inputs-and-conflict-preserve-exact-work-rows', rows == before_negatives)
    denied = sdk('query', query('project', uid(9)))
    check('unknown-scope-content-free', denied.get('error') == 'denied_or_not_found' and not denied.get('rows'))

    # An actual independent owner creates and explicitly grants a second scope.
    owned = command('project.create', uid(2), 0, project_payload | {'project_key': 'SDKOWNER'}, uid(2))
    accepted(owned, owner('command', owned), '~zod')
    check('existing-ungranted-scope-denied', sdk('query', query('project', uid(2))).get('error') == 'denied_or_not_found')
    grant = command('policy.grant', uid(2), 1, {'grant_id': uid(22), 'principal_id': uid(102),
        'role': 'contributor', 'expires_at_ms': str(now + 3600000)}, uid(2))
    accepted(grant, owner('command', grant), '~zod')
    handle = sdk('updates', update('open', kind='work', project_id=uid(2)))
    check('public-watch-open', handle.get('status') == 'watching' and len(handle.get('watch_id', '')) == 64
          and len(handle.get('cursor', '')) == 64 and handle.get('rows') == {})
    snapshot = sdk('query', query('work', uid(2)))
    check('watch-before-snapshot-matches-generation', snapshot.get('status') == 'read'
          and snapshot.get('generation') == handle.get('generation') and snapshot.get('rows') == {})
    queued = command('work.create', uid(12), 0, work_payload, uid(2))
    accepted(queued, owner('command', queued), '~zod')
    observed = sdk('updates', update('poll', handle))
    check('public-watch-delivers-authorized-invalidation', observed.get('status') == 'updated'
          and observed.get('rows', {}).get('0', {}).get('sequence') == '1'
          and observed.get('generation') != handle.get('generation'))
    check('watch-cursor-not-a-query-cursor', sdk('query', query('work', uid(2), cursor=observed['cursor'])).get('error') == 'stale_cursor')
    resumed = sdk('updates', update('resume', cursor=observed['cursor'], kind='work', project_id=uid(2)))
    check('public-resume-replaces-handle', resumed.get('status') == 'resumed'
          and resumed.get('watch_id') != observed.get('watch_id'))
    late = sdk('updates', update('poll', observed))
    check('reordered-old-handle-cannot-dequeue-current-watch', late.get('status') == 'refresh_required' and late.get('rows') == {})
    current = sdk('updates', update('poll', resumed))
    check('public-new-handle-still-live', current.get('status') == 'updated')
    replay = sdk('updates', update('poll', resumed))
    check('public-replayed-cursor-requires-refresh', replay.get('status') == 'refresh_required' and replay.get('rows') == {})
    check('public-watch-cancellation-idempotent', sdk('updates', update('cancel', current)).get('status') == 'cancelled'
          and sdk('updates', update('cancel', current)).get('status') == 'cancelled')
    revoked = sdk('updates', update('open', kind='work', project_id=uid(2)))
    queued = command('work.update', uid(12), 1, work_payload | {'title': 'Queued before revocation'}, uid(2))
    accepted(queued, owner('command', queued), '~zod')
    revoke = command('policy.revoke', uid(2), 2, {'grant_id': uid(22)}, uid(2))
    accepted(revoke, owner('command', revoke), '~zod')
    final = sdk('updates', update('poll', revoked))
    check('revoked-public-subscriber-discards-queued-data', final.get('status') == 'refresh_required'
          and final.get('rows') == {} and final.get('cursor') == '' and final.get('generation') == '')
    check('revoked-member-query-denied', sdk('query', query('work', uid(2))).get('error') == 'denied_or_not_found')
    before_denied = owner('query', query('work', uid(2)))['rows']
    row = next(iter(before_denied.values()))
    check('owner-readback-before-denied-mutation', len(before_denied) == 1 and row['resource_id'] == uid(12)
          and row['resource_revision'] == '2' and all(row[key] == value for key, value in queued['payload'].items()))
    blocked = command('work.create', uid(13), 0, work_payload, uid(2))
    check('revoked-member-mutation-denied', sdk('command', blocked).get('error') == 'denied_or_not_found')
    final = owner('query', query('work', uid(2)))
    check('denied-mutation-preserves-exact-authority-rows', final.get('rows') == before_denied)

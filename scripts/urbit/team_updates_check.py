"""Real configured Gall update controls; no mocked transport or business state."""
from __future__ import annotations


def run(call, check, query, mutation, uid, now):
    sequence = 8000
    project = uid(2)

    def updates(action, *, watch='', cursor='', kind='', scope=''):
        nonlocal sequence
        sequence += 1
        return {'protocol': 'stead.updates/3', 'request_id': uid(sequence),
                'action': action, 'watch_id': watch, 'cursor': cursor, 'kind': kind,
                'project_id': scope, 'container_id': '', 'resource_id': '', 'search': ''}

    def opened(ship='nec', kind='work'):
        result = call(ship, 'updates', updates('open', kind=kind, scope=project))
        check('updates-open-' + ship + '-' + kind, result.get('status') == 'watching'
              and len(result.get('watch_id', '')) == 64 and len(result.get('cursor', '')) == 64
              and result.get('rows') == {})
        return result

    def poll(handle, ship='nec', **replace):
        return call(ship, 'updates', updates('poll', watch=handle['watch_id'],
                                           cursor=handle['cursor']) | replace)

    def cancel(handle, ship='nec'):
        return call(ship, 'updates', updates('cancel', watch=handle['watch_id']))

    def accepted(operation, resource, revision, payload):
        command = mutation(operation, resource, revision, payload, project=project)
        result = call('bus', 'command', command)
        check('updates-fixture-' + operation, result.get('status') == 'accepted')
        return command

    accepted('project.create', project, 0, {'organization_id': uid(5), 'owning_team_id': uid(6),
             'title': 'Update controls', 'project_key': 'UPDATES', 'preset': 'general'})
    accepted('policy.grant', project, 1, {'grant_id': uid(22), 'principal_id': uid(103),
             'role': 'contributor', 'expires_at_ms': str(now + 3600000)})
    work = opened()
    snapshot = call('nec', 'query', query('work', project=project))
    check('updates-open-precedes-fresh-empty-snapshot', snapshot.get('status') == 'read'
          and snapshot.get('rows') == {} and snapshot.get('generation') == work['generation'])
    first = poll(work)
    check('updates-empty-poll-rotates-cursor-without-generation-change', first.get('status') == 'updated'
          and first.get('rows') == {} and first.get('generation') == work['generation']
          and first.get('cursor') != work['cursor'])
    payload = {'title': 'Queued native work', 'description': 'Public synthetic update',
               'type': 'task', 'status': 'todo', 'priority': 'none'}
    command = accepted('work.create', uid(11), 0, payload)
    observed = poll(first)
    check('updates-accepted-command-invalidates-authorized-scope', observed.get('status') == 'updated'
          and list(observed.get('rows', {})) == ['0']
          and set(observed['rows']['0']) == {'sequence', 'generation'}
          and observed['rows']['0']['sequence'] == '1'
          and observed['generation'] == observed['rows']['0']['generation']
          and observed['generation'] != first['generation'])
    call('bus', 'command', command)
    unchanged = poll(observed)
    check('updates-duplicate-command-no-new-invalidation', unchanged.get('status') == 'updated'
          and unchanged.get('rows') == {} and unchanged.get('generation') == observed['generation'])
    foreign = poll(unchanged, 'bus')
    check('updates-foreign-actor-no-dequeue', foreign.get('status') == 'refresh_required'
          and foreign.get('rows') == {})
    check('updates-foreign-cancel-content-free', cancel(unchanged, 'bus').get('status') == 'cancelled')
    owned = poll(unchanged)
    check('updates-foreign-requests-preserve-owner-watch', owned.get('status') == 'updated')
    paged = call('nec', 'query', query('work', project=project, cursor=owned['cursor']))
    check('updates-cursor-cannot-be-used-for-query', paged.get('error') == 'stale_cursor')
    accepted('work.update', uid(11), 1, payload | {'title': 'Second native version'})
    resumed = call('nec', 'updates', updates('resume', cursor=owned['cursor'], kind='work', scope=project))
    check('updates-resume-replaces-watch', resumed.get('status') == 'resumed'
          and resumed.get('watch_id') != owned['watch_id'])
    delayed = poll(owned)
    check('updates-delayed-old-handle-cannot-consume-resumed-watch', delayed.get('status') == 'refresh_required')
    suffix = poll(resumed)
    check('updates-resume-delivers-unread-suffix', suffix.get('status') == 'updated'
          and suffix.get('rows', {}).get('0', {}).get('sequence') == '2')
    replayed = poll(resumed)
    check('updates-replayed-cursor-requires-refresh', replayed.get('status') == 'refresh_required'
          and replayed.get('rows') == {})
    check('updates-cancel-after-replay-idempotent', cancel(suffix).get('status') == 'cancelled'
          and cancel(suffix).get('status') == 'cancelled')

    # A private container is visible to its owner only; no counter, body or
    # invalidation can escape through the other member's broad projections.
    watches = {kind: opened(kind=kind) for kind in ('work', 'search', 'activity', 'relations')}
    full = call('nec', 'updates', updates('open', kind='inbox', scope=project))
    check('updates-four-watch-cap-at-native-boundary', full.get('error') == 'capacity_exceeded')
    accepted('container.create', uid(40), 0, {'title': 'PRIVATE-UPDATE-CANARY', 'visibility': 'private'})
    for kind, handle in watches.items():
        row = poll(handle)
        check('updates-private-container-invisible-' + kind, row.get('status') == 'updated'
              and row.get('rows') == {} and row.get('generation') == handle['generation'])
        watches[kind] = row
    # Queue visible work, then revoke before dequeue. Neither queued content nor
    # even its generation is returned to the now-ungranted principal.
    accepted('work.update', uid(11), 2, payload | {'title': 'Queued before revocation'})
    accepted('policy.revoke', project, 2, {'grant_id': uid(22)})
    for kind, handle in watches.items():
        row = poll(handle)
        check('updates-revocation-discards-queued-' + kind, row.get('status') == 'refresh_required'
              and row.get('rows') == {} and row.get('generation') == '' and row.get('cursor') == '')
    denied = call('nec', 'updates', updates('open', kind='work', scope=project))
    check('updates-revoked-scope-open-denied', denied.get('error') == 'denied_or_not_found')
    accepted('policy.grant', project, 3, {'grant_id': uid(23), 'principal_id': uid(103),
             'role': 'contributor', 'expires_at_ms': str(now + 3600000)})
    old = poll(watches['work'])
    check('updates-regrant-cannot-revive-old-handle', old.get('status') == 'refresh_required')
    # Keep one current watch for the caller's real cold-restart control.
    before_restart = opened()
    return updates('poll', watch=before_restart['watch_id'], cursor=before_restart['cursor'])

"""Real configured Gall update controls; no mocked transport or business state."""
from __future__ import annotations


def run(call, check, query, mutation, uid, now):
    sequence = 8000
    project = uid(2)

    def updates(action, *, watch='', cursor='', kind='', scope='', container=''):
        nonlocal sequence
        sequence += 1
        return {'protocol': 'stead.updates/3', 'request_id': uid(sequence),
                'action': action, 'watch_id': watch, 'cursor': cursor, 'kind': kind,
                'project_id': scope, 'container_id': container, 'resource_id': '', 'search': ''}

    def opened(ship='nec', kind='work', container=''):
        result = call(ship, 'updates', updates('open', kind=kind, scope=project, container=container))
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

    def deleted_invalidation(handle, label):
        row = poll(handle)
        check('updates-delete-invalidates-' + label, row.get('status') == 'updated'
              and len(row.get('rows', {})) == 1
              and row.get('generation') != handle['generation']
              and all(set(item) == {'sequence', 'generation'} for item in row['rows'].values()))
        return row

    # Deletion is an accepted change, not loss of the project's read grant.
    # A subscribed member must refresh away the tombstone and dangling links.
    accepted('work.create', uid(12), 0, payload | {'title': 'Work to delete'})
    deleting_work = opened()
    before_delete = deleting_work
    accepted('work.delete', uid(12), 1, {})
    deleting_work = deleted_invalidation(deleting_work, 'work')
    remaining = call('nec', 'query', query('work', project=project))
    check('updates-deleted-work-absent-with-survivor', remaining.get('status') == 'read'
          and [row.get('resource_id') for row in remaining.get('rows', {}).values()] == [uid(11)])
    replay = poll(before_delete)
    check('updates-delete-cursor-replay-requires-refresh', replay.get('status') == 'refresh_required'
          and replay.get('rows') == {} and replay.get('generation') == '' and replay.get('cursor') == '')
    check('updates-delete-watch-still-cancellable', cancel(deleting_work).get('status') == 'cancelled')

    accepted('container.create', uid(41), 0, {'title': 'Deletion controls', 'visibility': 'shared'})
    for document in (51, 52):
        markdown = f'---\nid: {uid(document)}\ntype: page\nstate: published\n---\nSynthetic deletion control\n'
        accepted('document.save', uid(document), 0, {'container_id': uid(41), 'markdown': markdown})
    def link(resource, source_kind, source, target):
        accepted('relation.create', uid(resource), 0, {'type': 'related_to',
            'source_project_id': project, 'source_kind': source_kind,
            'source_container_id': uid(41) if source_kind == 'document' else '', 'source_id': uid(source),
            'target_project_id': project, 'target_kind': 'document',
            'target_container_id': uid(41), 'target_id': uid(target)})
    link(61, 'work', 11, 51)
    link(62, 'document', 51, 52)
    relation_watch = opened(kind='relations')
    accepted('relation.delete', uid(61), 1, {})
    relation_watch = deleted_invalidation(relation_watch, 'relation')
    remaining = call('nec', 'query', query('relations', project=project))
    check('updates-deleted-relation-absent-with-survivor', remaining.get('status') == 'read'
          and [row.get('resource_id') for row in remaining.get('rows', {}).values()] == [uid(62)])
    document_watch = opened(kind='documents', container=uid(41))
    documents = call('nec', 'query', query('documents', project=project, container=uid(41)))
    source = next(row for row in documents['rows'].values() if row['resource_id'] == uid(51))
    accepted('document.delete', uid(51), 1, {'container_id': uid(41), 'expected_head': source['container_head']})
    document_watch = deleted_invalidation(document_watch, 'document')
    relation_watch = deleted_invalidation(relation_watch, 'document-relations')
    remaining = call('nec', 'query', query('documents', project=project, container=uid(41)))
    check('updates-deleted-document-absent-with-survivor', remaining.get('status') == 'read'
          and [row.get('resource_id') for row in remaining.get('rows', {}).values()] == [uid(52)])
    remaining_links = call('nec', 'query', query('relations', project=project))
    check('updates-deleted-document-hides-dangling-link', remaining_links.get('status') == 'read'
          and remaining_links.get('rows') == {})
    for handle in (document_watch, relation_watch):
        check('updates-delete-cancelled', cancel(handle).get('status') == 'cancelled')

    # A private container is visible to its owner only; no counter, body or
    # invalidation can escape through the other member's broad projections.
    watches = {kind: opened(kind=kind) for kind in ('work', 'search', 'activity', 'relations')}
    full = call('nec', 'updates', updates('open', kind='inbox', scope=project))
    check('updates-four-watch-cap-at-native-boundary', full.get('error') == 'capacity_exceeded')
    accepted('container.create', uid(40), 0, {'title': 'PRIVATE-UPDATE-CANARY', 'visibility': 'private'})
    markdown = f'---\nid: {uid(53)}\ntype: page\nstate: draft\n---\nPRIVATE-DELETE-CANARY\n'
    accepted('document.save', uid(53), 0, {'container_id': uid(40), 'markdown': markdown})
    private = call('bus', 'query', query('document', project=project, container=uid(40), resource=uid(53)))
    source = next(iter(private['rows'].values()))
    accepted('document.delete', uid(53), 1, {'container_id': uid(40), 'expected_head': source['container_head']})
    for kind, handle in watches.items():
        row = poll(handle)
        check('updates-private-create-and-delete-invisible-' + kind, row.get('status') == 'updated'
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

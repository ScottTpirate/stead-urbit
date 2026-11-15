"""Reserved real native-human-doc/1 journey, invoked by a trusted supervisor.

This module never starts a runtime, relaxes its guard, writes a pier, or reports
qualification. Run it on a freshly configured/admitted disposable no-Code Home
before any Code scenario. `legacy` is the existing actual Gall call adapter;
`product` records product_conn's raw framed observations; `ready` performs a
fresh actual owner bootstrap after bounded migration/restore; `restart` owns the
stop/reap/suspended-save comparison/reload/bootstrap procedure; `fingerprints`
executes the exact current release, review and lifecycle Dojo helpers, returning
release_authority, review_authority, release_vase and lifecycle_vase.
All callbacks are mandatory. Host mocks of this scenario are not native proof.
"""
from __future__ import annotations

import hashlib
import json
import re

from product_conn import canonical, digest, owner_route, result_route


def activation_input(dojo):
    output = dojo('zod', '+stead-product-predecessor').strip()
    if len(output) > 16384 or not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', output):
        raise ValueError('Actual predecessor generator did not return bounded bytes')
    atom = int(output.replace('.', ''), 16)
    raw = atom.to_bytes((atom.bit_length() + 7) // 8, 'little')
    value = json.loads(raw)
    if (not isinstance(value, dict)
            or set(value) != {'protocol', 'profile', 'expected_config_revision', 'predecessor_sha256'}
            or not all(isinstance(v, str) for v in value.values())
            or value['protocol'] != 'stead.product-activate/1'
            or value['profile'] != 'native-human-doc/1'
            or not re.fullmatch(r'[1-9][0-9]{0,19}', value['expected_config_revision'])
            or int(value['expected_config_revision']) >= 2**64
            or not re.fullmatch(r'[0-9a-f]{64}', value['predecessor_sha256'])
            or raw != canonical(value)):
        raise ValueError('Actual predecessor activation input differs')
    return value


def read_matches(value, request, epoch='1'):
    """Strict successful envelope correlation before a row becomes evidence."""
    if not isinstance(value, dict) or not isinstance(request, dict):
        return False
    protocol = request.get('protocol')
    if protocol == 'stead.doc-change-query/1':
        result_protocol = 'stead.doc-change-query-result/1'
        scope = ('request_id', 'kind', 'project_id', 'work_id', 'change_id',
                 'result_revision', 'result_digest', 'side')
    elif protocol in ('stead.query/3', 'stead.query/4'):
        result_protocol = protocol.replace('stead.query/', 'stead.query-result/')
        scope = ('request_id', 'kind', 'project_id', 'container_id', 'resource_id')
    else:
        return False
    return (set(value) == {'protocol', 'status', 'authority_epoch', 'generation', 'cursor', 'rows', *scope}
            and value['protocol'] == result_protocol and value['status'] == 'read'
            and all(isinstance(request.get(k), str) and value[k] == request[k] for k in scope)
            and value['authority_epoch'] == epoch
            and isinstance(value['generation'], str) and re.fullmatch(r'[0-9a-f]{64}', value['generation']) is not None
            and isinstance(value['cursor'], str) and (value['cursor'] == '' or re.fullmatch(r'[0-9a-f]{64}', value['cursor']) is not None)
            and isinstance(value['rows'], dict) and len(value['rows']) <= 20
            and set(value['rows']) == {str(i) for i in range(len(value['rows']))})


def owner_matches(value, command):
    return (isinstance(value, dict) and set(value) == {'protocol', 'status', 'request_id',
            'canonical_sha256', 'operation', 'expected_revision', 'resulting_revision',
            'recorded_at_ms', 'error', 'capacity_class'}
            and value['protocol'] == 'stead.owner-receipt/1' and value['status'] == 'accepted'
            and value['error'] == '' and value['request_id'] == command['request_id']
            and value['operation'] == command['operation']
            and value['expected_revision'] == command['expected_revision']
            and value['resulting_revision'] == str(int(command['expected_revision']) + 1)
            and value['canonical_sha256'] == digest(command['protocol'], canonical(command))
            and value['capacity_class'] in ('ordinary', 'security')
            and isinstance(value['recorded_at_ms'], str)
            and re.fullmatch(r'[1-9][0-9]{0,19}', value['recorded_at_ms']) is not None
            and int(value['recorded_at_ms']) < 2**64)


def run(*, legacy, product, check, dojo, ready, restart, fingerprints, paused_predecessor, config, now, uid):
    if (config.get('home') != '~zod' or config.get('runtime') != 'isolated-fake'
            or config.get('custody') != 'local-disposable' or type(now) is not int or now <= 0
            or set(config.get('bindings', {})) != {'~bus', '~nec'}):
        raise ValueError('Fresh disposable two-member fixture required')
    alice, bob = (config['bindings']['~' + ship] for ship in ('bus', 'nec'))
    project, collection, document, work, outcome, change = map(uid, range(5000, 5006))
    sequence = 900000

    def request():
        nonlocal sequence
        sequence += 1
        return uid(sequence)

    def legacy_command(operation, resource, expected, payload):
        return {'protocol': 'stead.command/3', 'request_id': request(), 'project_id': project,
                'resource_id': resource, 'authority_epoch': '1', 'expected_revision': str(expected),
                'operation': operation, 'payload': payload}

    def query(kind, resource='', container='', protocol='stead.query/4'):
        return {'protocol': protocol, 'request_id': request(), 'project_id': project,
                'resource_id': resource, 'container_id': container, 'kind': kind, 'search': '', 'cursor': ''}

    def invoke(ship, mode, value, *, route=None):
        binding = config['bindings'].get('~' + ship, {'binding_id': uid(299), 'binding_revision': '1'})
        route = route or result_route(ship, binding['binding_id'], int(binding['binding_revision']), value)
        observed = product(ship, mode, value, route=route)
        if mode in ('query', 'doc-query') and observed.get('status') == 'read':
            check('product-read-exact-envelope-correlation', read_matches(observed, value))
        return observed

    def legacy_read(value):
        observed = legacy('bus', 'query', value)
        check('product-legacy-document-read-correlation', read_matches(observed, value))
        return observed

    def row(value):
        if (not isinstance(value, dict) or value.get('status') != 'read'
                or not isinstance(value.get('rows'), dict) or len(value['rows']) != 1):
            raise AssertionError('Expected one actual authorized row')
        return next(iter(value['rows'].values()))

    def accepted(name, value, command, protocol):
        check(name, value.get('status') == 'accepted' and value.get('error', '') == ''
              and value.get('protocol') == protocol and value.get('request_id') == command['request_id']
              and value.get('canonical_sha256') == digest(command['protocol'], canonical(command)))

    def owner(operation, expected, payload):
        command = {'protocol': 'stead.owner-command/1', 'request_id': request(), 'operation': operation,
                   'expected_revision': str(expected), 'payload': payload}
        check('product-owner-command-delivery', product('zod', 'owner-command', command, route='/') == {})
        observed = product('zod', 'owner-receipt', None, route=owner_route(command))
        check('product-owner-command-accepted', owner_matches(observed, command))
        return command, observed

    def work_command(operation, expected, payload):
        return {'protocol': 'stead.command/4', 'request_id': request(), 'project_id': project,
                'resource_id': work, 'authority_epoch': '1', 'operation': operation,
                'expected': expected, 'payload': payload}

    def doc_command(operation, expected, payload):
        return {'protocol': 'stead.doc-change/1', 'request_id': request(), 'project_id': project,
                'work_id': work, 'change_id': change, 'authority_epoch': '1',
                'expected_revision': str(expected), 'operation': operation, 'payload': payload}

    def action(operation, receipt):
        return doc_command(operation, int(receipt['resulting_revision']), {
            'result_revision': receipt['result_revision'], 'result_digest': receipt['result_digest'],
            'note': 'Checked this exact version.'})

    def fingerprint(name):
        observed = fingerprints()
        check(name + '-actual-fingerprint-helper-agreement',
              isinstance(observed, dict) and set(observed) == {
                  'release_authority', 'review_authority', 'release_vase', 'lifecycle_vase'}
              and all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for v in observed.values())
              and observed['release_authority'] == observed['review_authority']
              and observed['release_vase'] == observed['lifecycle_vase'])
        return observed

    create = legacy_command('project.create', project, 0, {
        'organization_id': config['organization_id'], 'owning_team_id': config['team_id'],
        'title': 'Product rehearsal', 'project_key': 'PRODUCT', 'preset': 'general'})
    check('product-predecessor-project', legacy('bus', 'command', create).get('status') == 'accepted')
    grant = legacy_command('policy.grant', project, 1, {
        'grant_id': uid(5010), 'principal_id': bob['principal_id'], 'role': 'contributor',
        'expires_at_ms': str(min(now + 3600000, int(bob['expires_at_ms'])))})
    check('product-predecessor-reviewer-grant', legacy('bus', 'command', grant).get('status') == 'accepted')
    box = legacy_command('container.create', collection, 0, {'title': 'Guide', 'visibility': 'shared'})
    check('product-predecessor-shared-collection', legacy('bus', 'command', box).get('status') == 'accepted')
    markdown = '---\nid: ' + document + '\ntype: page\nstate: published\n---\n# Guide λ\nOriginal exact text.\n'
    save = legacy_command('document.save', document, 0, {'container_id': collection, 'markdown': markdown})
    check('product-predecessor-document', legacy('bus', 'command', save).get('status') == 'accepted')
    fingerprint('product-predecessor-v3')
    activate = activation_input(dojo)
    denied = product('bus', 'activate', activate, route='/')
    check('product-activation-remote-owner-denied', denied.get('protocol') == 'stead.test-terminal/1'
          and denied.get('kind') == 'poke-fail')
    stale = product('zod', 'activate', activate | {'predecessor_sha256': '0' * 64}, route='/')
    check('product-activation-stale-prefix-denied', stale.get('protocol') == 'stead.test-terminal/1'
          and stale.get('kind') == 'poke-fail')
    check('product-activation-owner-delivery', product('zod', 'activate-paused', activate, route='/') == {})
    paused_predecessor(activate)  # Must prove ACTUAL idle saved10/predecessor before restart.
    ready()  # Bounded actual bootstrap, not a sleep or readiness boolean.
    fingerprint('product-converted-v10')
    for person in (alice, bob):
        owner('principal.declare', 1, {'principal_id': person['principal_id'], 'kind': 'person',
                                     'display_name': person['display_name'], 'active': 'yes'})
    roster = invoke('bus', 'query', query('principals'))
    check('product-current-typed-roster', roster.get('status') == 'read'
          and {r['principal_id'] for r in roster.get('rows', {}).values() if r.get('principal_kind') == 'person'}
          == {alice['principal_id'], bob['principal_id']})
    unauthorized_query = query('principals')
    outsider = invoke('bud', 'query', unauthorized_query)
    check('product-outsider-watch-denied', outsider.get('protocol') == 'stead.test-terminal/1'
          and outsider.get('kind') == 'watch-ack-fail')
    wrong_route = result_route('bus', bob['binding_id'], int(bob['binding_revision']), unauthorized_query)
    crossed = invoke('bus', 'query', unauthorized_query, route=wrong_route)
    check('product-native-watch-binding-cannot-be-spoofed', crossed.get('protocol') == 'stead.test-terminal/1'
          and crossed.get('kind') == 'watch-ack-fail')
    target = {'kind': 'document', 'project_id': project, 'collection_id': collection, 'document_id': document,
              'expected_revision': '1', 'base_markdown_sha256': hashlib.sha256(markdown.encode()).hexdigest()}
    properties = {'type': 'task', 'status': 'todo', 'priority': 'medium',
                  'owner_principal_id': alice['principal_id'], 'worker_principal_id': alice['principal_id'], 'blocked_reason': ''}
    contract = {'title': 'Revise the guide', 'description': 'Use the shared source.',
                'acceptance_criteria': 'Independently reviewed exact Markdown.', 'required_outcomes': {outcome: target}}
    create_work = work_command('work.create', {'work_revision': '0', 'execution_contract_revision': '0'}, properties | contract)
    accepted('product-work-created', invoke('bus', 'command', create_work), create_work, 'stead.receipt/4')
    current = row(invoke('bus', 'query', query('work', work)))
    check('product-created-work-visible-outside-legacy-index', current['title'] == contract['title']
          and current['execution_contract_revision'] == '1' and current['work_revision'] == '1')
    old_work = legacy_command('work.create', uid(5011), 0, {
        'title': 'Must not bypass', 'description': '', 'type': 'task', 'status': 'todo', 'priority': 'none'})
    check('product-legacy-work-write-denied', legacy('bus', 'command', old_work).get('status') == 'rejected')
    check('product-old-work-read-explicitly-unsupported', legacy('bus', 'query', query('work', protocol='stead.query/3')).get('status') != 'read')
    comment = work_command('work.comment', {'discussion_sequence': current['discussion_sequence']}, {'body': 'Please clarify the last step.'})
    accepted('product-comment-accepted', invoke('nec', 'command', comment), comment, 'stead.receipt/4')
    after_comment = row(invoke('bus', 'query', query('work', work)))
    check('product-comment-preserves-execution-pin', all(after_comment[k] == current[k] for k in (
        'work_revision', 'execution_contract_revision', 'execution_contract_digest')))
    draft = markdown + 'First proposal.\n'
    submission_payload = {'outcome_id': outcome, 'target': target, 'markdown': draft, 'summary': 'Revise the guide',
                          'execution_contract_revision': current['execution_contract_revision'],
                          'execution_contract_digest': current['execution_contract_digest'], 'run_id': '', 'attempt': '0'}
    submit = doc_command('change.submit', 0, submission_payload)
    submitted = invoke('bus', 'doc-command', submit)
    accepted('product-doc-submitted', submitted, submit, 'stead.doc-change-receipt/1')
    self_review = action('change.approve', submitted)
    check('product-independent-review-required', invoke('bus', 'doc-command', self_review).get('error') == 'self_review_denied')
    request_changes = action('change.request-changes', submitted)
    requested = invoke('nec', 'doc-command', request_changes)
    accepted('product-changes-requested', requested, request_changes, 'stead.doc-change-receipt/1')
    revised_markdown = draft + 'Clarified final step λ.  \n'
    revise = doc_command('change.submit', int(requested['resulting_revision']), submission_payload | {'markdown': revised_markdown})
    revised = invoke('bus', 'doc-command', revise)
    accepted('product-doc-revised', revised, revise, 'stead.doc-change-receipt/1')
    stale_approval = doc_command('change.approve', int(revised['resulting_revision']), self_review['payload'])
    check('product-old-output-review-denied', invoke('nec', 'doc-command', stale_approval).get('error') == 'result_conflict')
    approve = action('change.approve', revised)
    approved = invoke('nec', 'doc-command', approve)
    accepted('product-doc-approved', approved, approve, 'stead.doc-change-receipt/1')
    body_query = {'protocol': 'stead.doc-change-query/1', 'request_id': request(), 'kind': 'body',
                  'project_id': project, 'work_id': work, 'change_id': change,
                  'result_revision': approved['result_revision'], 'result_digest': approved['result_digest'],
                  'side': 'after', 'cursor': ''}
    proposed_body = row(invoke('nec', 'doc-query', body_query))
    check('product-exact-review-body', proposed_body.get('markdown') == revised_markdown)
    not_done = row(invoke('bus', 'query', query('completion', work)))
    check('product-approval-is-not-acceptance', not_done['ready'] == 'no')
    accept = action('change.accept', approved)
    committed = invoke('bus', 'doc-command', accept)
    accepted('product-doc-accepted', committed, accept, 'stead.doc-change-receipt/1')
    check('product-exact-accept-retry', invoke('bus', 'doc-command', accept) == committed)
    document_read = row(legacy_read(query('document', document, collection, 'stead.query/3')))
    check('product-canonical-markdown-exact', document_read['markdown'] == revised_markdown and document_read['resource_revision'] == '2')
    completion = row(invoke('bus', 'query', query('completion', work)))
    check('product-accepted-outcomes-ready', completion['ready'] == 'yes'
          and completion['execution_contract_digest'] == current['execution_contract_digest'])
    complete = work_command('work.complete', {'work_revision': current['work_revision'],
        'execution_contract_revision': current['execution_contract_revision']}, {'basis': 'accepted-outcomes', 'note': ''})
    completed = invoke('bus', 'command', complete)
    accepted('product-work-completed', completed, complete, 'stead.receipt/4')
    done = row(invoke('bus', 'query', query('work', work)))
    check('product-done-has-accepted-basis', done['status'] == 'done' and done['completion_basis'] == 'accepted-outcomes')
    before = fingerprint('product-complete-before-restart')
    restart()  # Must stop/reap, compare suspended vase, reload, and rebootstrap.
    after = fingerprint('product-complete-after-restart')
    check('product-restart-retains-all-authority-and-vase-bytes', before == after)
    check('product-restart-exact-accept-receipt', invoke('bus', 'doc-command', accept) == committed)
    check('product-restart-exact-completion-receipt', invoke('bus', 'command', complete) == completed)
    restored = row(legacy_read(query('document', document, collection, 'stead.query/3')))
    check('product-restart-exact-markdown', restored['markdown'] == revised_markdown)
    owner('principal.declare', 2, {'principal_id': bob['principal_id'], 'kind': 'person',
                                  'display_name': bob['display_name'], 'active': 'no'})
    revoked = invoke('nec', 'doc-command', approve)
    check('product-revocation-precedes-cached-approval', revoked.get('protocol') == 'stead.test-terminal/1'
          and revoked.get('kind') == 'watch-ack-fail')
    owner('home.configure', 1, {'configuration': canonical(config | {'expected_revision': '1', 'bindings': {
        **config['bindings'], '~nec': bob | {'binding_revision': '2', 'active': 'no'}}}).decode()})
    ready()
    owner_saved = fingerprint('product-owner-config-recorded')
    restart()
    check('product-owner-configuration-restores-in-same-timeline', owner_saved == fingerprint('product-owner-config-restored'))
    check('product-owner-config-preserves-content', row(invoke('bus', 'query', query('work', work)))['status'] == 'done')
    return {'profile': 'native-human-doc/1', 'scope': 'actual native Gall; HTTP/browser/agent-run not included',
            'project_id': project, 'work_id': work, 'change_id': change, 'document_id': document,
            'accepted_markdown_sha256': hashlib.sha256(revised_markdown.encode()).hexdigest(),
            'final_fingerprints': owner_saved}

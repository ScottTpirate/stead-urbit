"""Independent native-observer evidence checks and bounded control adapter.

No ships run on import. The caller owns guarded lifecycle and supplies call/pause.
Observer evidence proves signs delivered to Gall on-agent for the known mark and
route, not that a peer runtime received no other bytes. Runtime/mark-conversion
errors must be retained and cannot support a clean zero-delivery claim.
"""
from __future__ import annotations

import hashlib
import json
import re

UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
HEX = re.compile(r'[0-9a-f]{64}')
DECIMAL = re.compile(r'0|[1-9][0-9]*')
FAKES = {'zod', 'bus', 'nec', 'bud'}
PROBE_FIELDS = {'protocol', 'id', 'status', 'fault', 'route', 'watch_requested',
                'leave_requested', 'closed', 'ongoing_subscription', 'facts', 'kicks',
                'watch_acks', 'watch_nacks', 'poke_acks', 'poke_nacks', 'pokes_requested', 'events'}
EVENT_FIELDS = {'kind', 'source_ship', 'peer_agent', 'peer_agent_basis', 'wire', 'mark',
                'payload_bytes', 'payload_sha256', 'source_provenance_sha256',
                'observed_at_ms', 'after_terminal'}
RECEIPT_FIELDS = {'protocol', 'status', 'request_id', 'canonical_sha256', 'project_id',
                  'resource_id', 'resource_kind', 'container_id', 'resource_revision',
                  'authority_epoch', 'principal_id', 'binding_id', 'authentication',
                  'authentication_strength', 'accepted_at_ms', 'git_commit_oid'}


class ObservationError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ObservationError(reason)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate observation JSON key')
        result[key] = value
    return result


def number(value):
    require(isinstance(value, str) and bool(DECIMAL.fullmatch(value)), 'Noncanonical observation counter')
    require(int(value) <= 2**64 - 1, 'Observation counter overflow')
    return int(value)


def observation(record, *, probe_id=None, route=None):
    """Validate exact raw owner-query bytes plus their actual native call record."""
    require(isinstance(record, dict) and bool(record.get('native')), 'Native owner query evidence missing')
    raw = record.get('raw')
    require(isinstance(raw, str) and 0 < len(raw.encode()) <= 262144, 'Observation response bound')
    obj = json.loads(raw, object_pairs_hook=unique)
    require(obj == record.get('json') and isinstance(obj, dict), 'Observation raw/decoded disagreement')
    require(set(obj) == PROBE_FIELDS and obj['protocol'] == 'stead.observer/1', 'Observer envelope')
    require(bool(UUID.fullmatch(obj['id'])), 'Observer probe ID')
    require(probe_id is None or obj['id'] == probe_id, 'Wrong observer probe')
    require(route is None or obj['route'] == route, 'Wrong observed route')
    require(obj['status'] == 'observed' and obj['fault'] == '', 'Observer latched a failure')
    for field in ('watch_requested', 'leave_requested', 'closed', 'ongoing_subscription'):
        require(obj[field] in ('true', 'false'), 'Observer boolean encoding')
    require(isinstance(obj['events'], dict) and len(obj['events']) <= 256, 'Observer events bound')
    counters = {kind: 0 for kind in ('fact', 'kick', 'watch-ack', 'watch-nack', 'poke-ack', 'poke-nack')}
    ordered = sorted(obj['events'].items(), key=lambda pair: number(pair[0]))
    last_time = 0
    terminal_seen = False
    for serial, event in ordered:
        require(0 < number(serial) <= 256, 'Observer event serial')
        require(isinstance(event, dict) and set(event) == EVENT_FIELDS, 'Observer event envelope')
        kind = event['kind']
        require(kind in counters, 'Unsupported/invalid delivered event')
        counters[kind] += 1
        lane = 'poke' if kind.startswith('poke-') else 'watch'
        require(event['wire'] == f"/probe/{obj['id']}/{lane}", 'Native sign on wrong wire/lane')
        require(event['source_ship'] == '~zod' and event['peer_agent'] == 'stead-home', 'Wrong native peer')
        require(event['peer_agent_basis'] == 'fixed issued Gall wire; sign has no agent field', 'Unstated peer-agent inference')
        require(bool(HEX.fullmatch(event['source_provenance_sha256'])), 'Source provenance missing')
        when, size = number(event['observed_at_ms']), number(event['payload_bytes'])
        require(when >= last_time, 'Observer event time reversed')
        last_time = when
        require(event['after_terminal'] in ('true', 'false'), 'Terminal flag encoding')
        # closed/leaving are latched for a probe. A late ACK is legal, but it
        # cannot claim to precede an already observed kick or watch NACK.
        require(not terminal_seen or event['after_terminal'] == 'true', 'Terminal marker reversed')
        require(event['after_terminal'] != 'true' or terminal_seen or obj['leave_requested'] == 'true',
                'Terminal marker has no preceding close or local leave')
        terminal_seen = terminal_seen or event['after_terminal'] == 'true' or kind in ('kick', 'watch-nack')
        if kind == 'fact':
            require(event['mark'] == 'stead-result-2' and 0 < size <= 262144, 'Wrong fact mark/size')
            require(bool(HEX.fullmatch(event['payload_sha256'])), 'Fact digest missing')
            require(event['after_terminal'] == 'false', 'Private fact delivered after duct termination/leave')
        else:
            require(size == 0 and event['payload_sha256'] == '' and event['mark'] == '', 'Nonfact payload metadata')
    for kind, value in counters.items():
        field = {'fact': 'facts', 'kick': 'kicks'}.get(kind, kind.replace('-', '_') + 's')
        require(number(obj[field]) == value, 'Observer counter/event mismatch: ' + field)
    require(number(obj['pokes_requested']) <= 4, 'Observer poke bound')
    return obj, ordered


def verify_one_shot(trace, raw, *, ship=None, route=None):
    """One observed request duct and an independently active foreign sentinel.

    Trace shape: classification, request{ship,probe_id,route}, response (owner
    observation call result), sentinels[{ship,before,after}], runtime_errors[].
    The sentinel uses its own reserved result path. It must already be watching
    when the request is made. Equal counters alone are insufficient: exact event
    maps and native owner-query records are retained. Known-mark leak controls
    belong to the separately required native delivery suite.
    """
    require(isinstance(trace, dict) and trace.get('classification') == 'real-native-observer', 'Actual native observer trace missing')
    require(trace.get('runtime_errors') == [], 'Missing or nonempty runtime error evidence')
    logs = trace.get('runtime_log_evidence')
    require(isinstance(logs, list) and bool(logs), 'Actual runtime log delta references missing')
    for log in logs:
        require(isinstance(log, dict) and log.get('ship') in FAKES
                and isinstance(log.get('path'), str) and bool(log['path'])
                and isinstance(log.get('sha256'), str) and bool(HEX.fullmatch(log['sha256']))
                and type(log.get('start')) is int and type(log.get('end')) is int
                and 0 <= log['start'] <= log['end'], 'Malformed runtime log delta reference')
    require({log['ship'] for log in logs} == FAKES, 'All four runtime log deltas required')
    request = trace.get('request', {})
    require(isinstance(request, dict), 'Observed request must be an object')
    require(isinstance(request.get('ship'), str) and request['ship'] in FAKES, 'Observed requester missing')
    require(isinstance(request.get('probe_id'), str) and bool(UUID.fullmatch(request['probe_id'])),
            'Explicit observed probe identity required')
    require(isinstance(request.get('route'), str) and request['route'].startswith('/v2/')
            and len(request['route'].encode()) <= 1024, 'Explicit bounded observed route required')
    require(ship is None or request['ship'] == ship, 'Wrong observed requester')
    require(route is None or request.get('route') == route, 'Wrong request path correlation')
    obj, events = observation(trace.get('response'), probe_id=request.get('probe_id'), route=request.get('route'))
    require(obj['watch_requested'] == 'true' and obj['leave_requested'] == 'false', 'No completed watch observation')
    require((number(obj['facts']), number(obj['kicks']), number(obj['watch_acks']), number(obj['watch_nacks'])) == (1, 1, 1, 0), 'One fact/one kick/one watch ACK required')
    require(obj['closed'] == 'true' and obj['ongoing_subscription'] == 'false', 'Duct remains open')
    require(number(obj['pokes_requested']) == number(obj['poke_acks']) == number(obj['poke_nacks']) == 0,
            'Read-only observation contains poke activity')
    require(isinstance(raw, str), 'Expected exact response bytes missing')
    fact = next(event for _, event in events if event['kind'] == 'fact')
    require(fact['payload_sha256'] == hashlib.sha256(raw.encode()).hexdigest() and number(fact['payload_bytes']) == len(raw.encode()), 'Observed fact differs from business response')
    kinds = [event['kind'] for _, event in events]
    require(kinds.index('fact') < kinds.index('kick'), 'Fact after kick')
    sentinels = trace.get('sentinels')
    require(isinstance(sentinels, list) and bool(sentinels), 'No active foreign subscriber observation')
    identities = set()
    for sentinel in sentinels:
        require(isinstance(sentinel, dict), 'Sentinel must be an object')
        other = sentinel.get('ship')
        require(isinstance(other, str) and other in FAKES and other != request['ship'] and other not in identities, 'Foreign sentinel identity')
        identities.add(other)
        before, _ = observation(sentinel.get('before'))
        after, _ = observation(sentinel.get('after'), probe_id=before['id'], route=before['route'])
        require(isinstance(before['route'], str), 'Sentinel route must be text')
        parts = before['route'].split('/')
        reserved = (len(parts) == 8 and parts[:4] == ['', 'v2', 'result', '~' + other]
                    and all(bool(UUID.fullmatch(part)) for part in parts[4:7])
                    and bool(HEX.fullmatch(parts[7])))
        held = sentinel.get('held_control', {})
        require(isinstance(held, dict), 'Held sentinel control must be an object')
        held_read = (other == 'bud' and before['route'] == request['route']
                     and held.get('operation') == 'hold-outsider-read'
                     and held.get('ship') == 'bud' and held.get('route') == before['route']
                     and bool(held.get('native')))
        require(reserved or held_read, 'Sentinel must be its own reservation or owner-evidenced held outsider read')
        for state in (before, after):
            require(state['watch_requested'] == 'true' and state['ongoing_subscription'] == 'true'
                    and state['closed'] == 'false' and state['leave_requested'] == 'false',
                    'Sentinel is not continuously active in the recorded snapshots')
        require(number(before['watch_acks']) == 1 and number(before['watch_nacks']) == 0 and number(before['facts']) == 0, 'Sentinel baseline not acknowledged and empty')
        require(before['events'] == after['events'] and after['ongoing_subscription'] == 'true', 'Foreign duct received an event during the observed request')
    return {'status': 'passed', 'classification': 'real-native-observer',
            'scope': 'Known-mark on-agent delivery on one request duct; no foreign sentinel event',
            'event_count': len(events), 'foreign_sentinels': len(sentinels)}


class Observer:
    """Owner-local fixture controls. Never interprets a control ACK as acceptance."""
    def __init__(self, call, pause):
        self.call, self.pause = call, pause

    def control(self, ship, action, probe_id, *, route='', raw=''):
        require(ship in FAKES and bool(UUID.fullmatch(probe_id)), 'Synthetic observer identity')
        require(action in ('watch', 'poke', 'leave', 'leave-ended'), 'Observer control action')
        command = {'action': action, 'id': probe_id, 'target': '~zod', 'route': route, 'raw': raw}
        wire = json.dumps(command, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        return self.call(ship, 'observe', route='/', raw=wire)

    def read(self, ship, probe_id):
        result = self.call(ship, 'observer-read', route='/v1/observer/' + probe_id, raw=b'')
        observation(result, probe_id=probe_id)
        return result

    def wait_for(self, ship, probe_id, predicate, *, attempts=40):
        require(type(attempts) is int and 1 <= attempts <= 80, 'Bounded observer polling required')
        seen = []
        for index in range(attempts):
            result = self.read(ship, probe_id)
            seen.append(result)
            if predicate(result['json']):
                return {'final': result, 'observations': seen}
            if index + 1 < attempts:
                self.pause(0.2)
        raise ObservationError('Bounded observer wait expired; no successful business outcome inferred')


def transport_outcome(events, *, expected_request=None):
    """Host-only event permutation oracle; never native execution evidence."""
    facts, terminal, failed = [], False, False
    for event in events:
        kind = event.get('kind')
        if kind == 'fact':
            if terminal:
                failed = True
            facts.append(event.get('raw'))
        elif kind in ('nack', 'error', 'invalid-fact'):
            failed = True
        elif kind in ('kick', 'timeout', 'cancel'):
            terminal = True
        elif kind != 'ack':
            failed = True
    if failed or len(facts) > 1:
        return {'status': 'failed', 'saved': False}
    if not facts:
        return {'status': 'unavailable' if terminal else 'pending', 'saved': False}
    try:
        raw = facts[0]
        require(isinstance(raw, str) and 0 < len(raw.encode()) <= 262144, 'Fact bound')
        result = json.loads(raw, object_pairs_hook=unique)
        if result.get('protocol') == 'stead.receipt/2' and result.get('status') == 'accepted':
            require(set(result) == RECEIPT_FIELDS and all(isinstance(v, str) for v in result.values()), 'Incomplete receipt')
            for field in ('request_id', 'project_id', 'resource_id', 'principal_id', 'binding_id'):
                require(bool(UUID.fullmatch(result[field])), 'Invalid accepted identity')
            require(bool(HEX.fullmatch(result['canonical_sha256'])), 'Invalid accepted digest')
            for field in ('resource_revision', 'authority_epoch', 'accepted_at_ms'):
                number(result[field])
            correlation = {'request_id', 'canonical_sha256', 'project_id', 'resource_id', 'resource_kind', 'container_id'}
            require(isinstance(expected_request, dict) and set(expected_request) >= correlation
                    and all(result.get(k) == v for k, v in expected_request.items()), 'Missing/mismatched request correlation')
            require(result['resource_kind'] in ('project', 'work', 'document', 'policy'), 'Unknown accepted kind')
            require(result['container_id'] == '' if result['resource_kind'] != 'document' else bool(UUID.fullmatch(result['container_id'])), 'Accepted container scope')
            return {'status': 'accepted', 'saved': True}
        if result == {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'}:
            return {'status': 'rejected', 'saved': False}
    except (ValueError, TypeError, AttributeError):
        pass
    return {'status': 'failed', 'saved': False}

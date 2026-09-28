"""Closed public protocol/3 outcome validation for the finite native SDK trial."""
import hashlib
import json
import re

HEX = re.compile(r'[0-9a-f]{64}')
UINT = re.compile(r'(?:0|[1-9][0-9]{0,19})')
RECEIPT = set('protocol status request_id canonical_sha256 project_id resource_id resource_kind container_id resource_revision authority_epoch operation principal_id binding_id binding_revision identity_ship authentication authentication_strength session_audit_id runtime accepted_at_ms git_commit_oid'.split())
QUERY = set('protocol status request_id kind project_id container_id resource_id authority_epoch generation cursor rows'.split())
UPDATE = set('protocol status request_id watch_id cursor generation rows'.split())


def require(condition, message):
    if not condition:
        raise ValueError('Public result validation: ' + message)


def uint(value, positive=False):
    return isinstance(value, str) and UINT.fullmatch(value) is not None and int(value) < 2**64 and (not positive or int(value) > 0)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def validate(mode, request, value, actor='~bus'):
    require(isinstance(value, dict) and 0 < len(canonical(value).encode()) <= 262144, 'bounded object')
    if value.get('protocol') == 'stead.sdk-error/1':
        require(value == {'protocol': 'stead.sdk-error/1', 'status': 'failed', 'error': 'request_unconfirmed'}, 'unconfirmed SDK shape')
        return
    require(isinstance(request, dict), 'unparseable request cannot have a business outcome')
    if value.get('protocol') == 'stead.receipt/3':
        require(mode == 'command' and set(value) == RECEIPT and all(isinstance(v, str) for v in value.values()), 'receipt fields')
        expected = {key: request[key] for key in ('request_id', 'project_id', 'resource_id', 'operation', 'authority_epoch')}
        prefix = '019939ba-4000-7000-8000-'
        principal, binding = (102, 202) if actor == '~bus' else (104, 204)
        expected.update(status='accepted', canonical_sha256=hashlib.sha256(('stead.command/3\0' + canonical(request)).encode()).hexdigest(),
            resource_revision=str(int(request['expected_revision']) + 1), container_id='', git_commit_oid='',
            principal_id=prefix + f'{principal:012x}', binding_id=prefix + f'{binding:012x}', binding_revision='1',
            identity_ship=actor, authentication='native-sender/1', authentication_strength='native-sender',
            session_audit_id='', runtime='isolated-fake', resource_kind=request['operation'].split('.')[0])
        require(all(value[k] == v for k, v in expected.items()) and uint(value['accepted_at_ms'], True), 'correlated receipt')
        return
    if value.get('status') == 'rejected':
        require(all(isinstance(v, str) for v in value.values()) and re.fullmatch(r'[a-z_]{1,64}', value.get('error', '')), 'bounded rejection')
        if set(value) == {'protocol', 'status', 'error', 'request_id', 'canonical_sha256'}:
            require(value['protocol'] == 'stead.result/3' and value['request_id'] == request['request_id']
                and value['canonical_sha256'] == hashlib.sha256(('stead.' + mode + '/3\0' + canonical(request)).encode()).hexdigest(), 'correlated rejection')
        elif mode == 'query':
            require(set(value) == {'protocol', 'status', 'error'} and value['protocol'] == 'stead.result/3', 'query rejection')
        elif mode == 'updates':
            require(set(value) == {'protocol', 'status', 'error', 'request_id'} and value['protocol'] == 'stead.update-result/3'
                and value['request_id'] == request['request_id'], 'update rejection')
        else:
            raise ValueError('Uncorrelated command rejection')
        return
    if mode == 'query':
        require(set(value) == QUERY and value['protocol'] == 'stead.query-result/3' and value['status'] == 'read', 'query fields')
        require(all(isinstance(v, str) for k, v in value.items() if k != 'rows'), 'query strings')
        require(all(value[k] == request[k] for k in ('request_id', 'kind', 'project_id', 'container_id', 'resource_id')), 'query scope')
        require(uint(value['authority_epoch']) and HEX.fullmatch(value['generation']) and (value['cursor'] == '' or HEX.fullmatch(value['cursor'])), 'query revision/cursors')
        require(isinstance(value['rows'], dict) and len(value['rows']) <= 20, 'query rows')
        if request['kind'] == 'capabilities':
            require(len(value['rows']) == 1, 'exactly one capabilities row')
        for key, row in value['rows'].items():
            require(isinstance(key, str) and len(key) <= 1024 and isinstance(row, dict)
                and all(isinstance(k, str) and isinstance(v, str) for k, v in row.items()), 'row string fields')
            if request['kind'] == 'capabilities':
                require(set(row) == set('protocol profile commands queries updates authentication max_request_bytes max_response_bytes page_size runtime'.split()), 'capabilities row fields')
                require(row == {'protocol': 'stead.capabilities/3', 'profile': 'configured-team',
                    'commands': 'stead.command/3', 'queries': 'stead.query/3', 'updates': 'stead.updates/3',
                    'authentication': 'native-sender/1', 'max_request_bytes': '65536', 'max_response_bytes': '262144',
                    'page_size': '20', 'runtime': 'isolated-fake'}, 'public capability values')
            elif request['kind'] == 'work':
                require(set(row) == set('kind resource_id container_id resource_revision title description type status priority snippet'.split())
                    and row['kind'] == 'work' and row['container_id'] == '' and uint(row['resource_revision'], True), 'Work row fields')
            elif request['kind'] in ('projects', 'project'):
                fields = set('kind resource_id resource_revision project_id title project_key preset authority_epoch role'.split())
                if row.get('role') == 'maintainer':
                    fields.add('policy_revision')
                require(set(row) == fields and row['kind'] == 'project' and row['resource_id'] == row['project_id']
                    and uint(row['resource_revision'], True) and uint(row['authority_epoch'], True), 'project row fields')
        return
    require(mode == 'updates' and set(value) == UPDATE and value['protocol'] == 'stead.update-result/3'
        and value['request_id'] == request['request_id'] and all(isinstance(v, str) for k, v in value.items() if k != 'rows'), 'update fields')
    expected = {'open': 'watching', 'poll': 'updated', 'resume': 'resumed', 'cancel': 'cancelled'}[request['action']]
    require(value['status'] in (expected, 'refresh_required'), 'update action')
    require(isinstance(value['rows'], dict) and len(value['rows']) <= 16, 'update rows')
    if value['status'] in ('cancelled', 'refresh_required'):
        require(value['cursor'] == value['generation'] == '' and value['rows'] == {}, 'content-free terminal update')
        require(value['watch_id'] == request['watch_id'], 'terminal watch correlation')
        return
    require(HEX.fullmatch(value['watch_id']) and HEX.fullmatch(value['cursor']) and HEX.fullmatch(value['generation']), 'opaque update bindings')
    if request['action'] == 'poll':
        require(value['watch_id'] == request['watch_id'] and value['cursor'] != request['cursor'], 'poll watch and rotated cursor')
    else:
        require(value['rows'] == {}, 'open/resume has no payload')
    require(set(value['rows']) == {str(n) for n in range(len(value['rows']))}, 'consecutive row keys')
    previous = None
    for index in range(len(value['rows'])):
        row = value['rows'][str(index)]
        require(isinstance(row, dict) and set(row) == {'sequence', 'generation'} and uint(row['sequence'], True)
            and isinstance(row['generation'], str) and HEX.fullmatch(row['generation']), 'content-free invalidation')
        require(previous is None or int(row['sequence']) == previous + 1, 'contiguous update sequence')
        previous = int(row['sequence'])
    if value['rows']:
        require(value['rows'][str(len(value['rows']) - 1)]['generation'] == value['generation'], 'final generation')

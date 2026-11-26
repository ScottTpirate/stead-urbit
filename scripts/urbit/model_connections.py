"""Reserved pure model-connection boundary; no HTTP, secrets, tools or authority.

The supervisor must admit current native effect authority and journal a request
before doing I/O. Nothing in this module grants that authority. Connection and
provider bytes are never interpreted as executable code or a tool invocation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
import re
from urllib.parse import urlsplit, urlunsplit

UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
SHA = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')
SPEC_FIELDS = {'protocol', 'connection_id', 'revision', 'display_name', 'adapter',
               'endpoint', 'model', 'authentication', 'capabilities', 'limits'}
LIMITS = {'input_bytes': 65536, 'output_bytes': 131072, 'turns': 16,
          'tool_calls': 32, 'request_timeout_ms': 60000, 'duration_ms': 600000,
          'input_tokens': 131072, 'output_tokens': 32768, 'total_tokens': 262144,
          'cost_units': 1000000000, 'billable_micro_usd': 100000000}
SCOPE_FIELDS = {'home', 'project_id', 'run_id', 'attempt', 'effect_sequence',
                'run_contract_sha256', 'context_digest', 'definition_id',
                'definition_revision', 'runtime_id', 'runtime_revision',
                'runtime_policy_digest', 'connection_digest'}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def text(value, maximum, *, nonempty=False, label=False):
    require(type(value) is str and '\0' not in value, 'invalid_text')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError as error:
        raise ValueError('invalid_text') from error
    require(int(nonempty) <= size <= maximum, 'text_bound')
    if label:
        require(not any(ord(char) < 32 or ord(char) == 127 for char in value), 'invalid_label')
    return value


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'closed_fields')
    return value


def uint(value, maximum=2**64 - 1, *, positive=False):
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', value) is not None,
            'decimal_string_required')
    number = int(value)
    require(int(positive) <= number <= maximum, 'integer_bound')
    return number


def uuid(value):
    require(type(value) is str and UUID.fullmatch(value) is not None, 'uuid_required')
    return value


def digest(value):
    require(type(value) is str and SHA.fullmatch(value) is not None, 'digest_required')
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def domain_hash(domain, raw):
    return hashlib.sha256(domain.encode('ascii') + b'\0' + raw).hexdigest()


def decode(raw, maximum):
    require(type(raw) is bytes and 0 < len(raw) <= maximum, 'json_byte_bound')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate_key')
            value[key] = item
        return value
    def constant(_):
        raise ValueError('invalid_number')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=constant)
        def bounded(item, depth=0):
            require(depth <= 8, 'json_depth_bound')
            if type(item) is dict:
                require(len(item) <= 128, 'json_member_bound')
                for key, child in item.items():
                    text(key, 128)
                    bounded(child, depth + 1)
            elif type(item) is list:
                require(len(item) <= 128, 'json_array_bound')
                for child in item:
                    bounded(child, depth + 1)
            elif type(item) is str:
                text(item, maximum)
            else:
                require(item is None or type(item) in (int, bool), 'invalid_number')
                if type(item) is int:
                    require(abs(item) <= 2**53 - 1, 'unsafe_integer')
        bounded(value)
        return value
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('invalid_json') from error


def endpoint(value):
    closed(value, {'url', 'placement', 'egress_policy_digest'})
    url = text(value['url'], 2048, nonempty=True, label=True)
    placement = value['placement']
    require(placement in ('remote-api', 'local-isolated'), 'unsupported_placement')
    digest(value['egress_policy_digest'])
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError as error:
        raise ValueError('invalid_endpoint') from error
    require(host and '@' not in parts.netloc and not parts.username and not parts.password and not parts.query
            and not parts.fragment and '%' not in url and '\\' not in url, 'invalid_endpoint')
    require(re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*chat/completions', parts.path) is not None,
            'unsupported_endpoint_path')
    require(port is None or 1 <= port <= 65535, 'invalid_endpoint_port')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if placement == 'remote-api':
        require(parts.scheme == 'https', 'remote_tls_required')
        require(address.is_global if address else re.fullmatch(
            r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', host) is not None,
            'remote_host_required')
    else:
        require(parts.scheme in ('http', 'https') and host in ('127.0.0.1', '::1')
                and port is not None, 'isolated_loopback_endpoint_required')
    authority = ('[' + host + ']') if ':' in host else host
    if port is not None and not (placement == 'remote-api' and parts.scheme == 'https' and port == 443):
        authority += ':' + str(port)
    # DNS resolution, TLS, redirects, actual egress and worker-host placement are
    # supervisor admission duties. A syntactic URL check is not an egress grant.
    return {**value, 'url': urlunsplit((parts.scheme, authority, parts.path, '', ''))}


@dataclass(frozen=True)
class ConnectionSpec:
    raw: bytes
    sha256: str

    def value(self):
        return json.loads(self.raw)


def connection(raw):
    value = closed(decode(raw, 8192), SPEC_FIELDS)
    require(value['protocol'] in ('stead.model-connection/1', 'stead.model-connection/2')
            and value['adapter'] in ('openai.chat-completions/1', 'llamacpp.chat-completions/1'),
            'unsupported_connection')
    uuid(value['connection_id']); uint(value['revision'], positive=True)
    text(value['display_name'], 200, nonempty=True, label=True)
    text(value['model'], 200, nonempty=True, label=True)
    target = endpoint(value['endpoint'])
    if value['adapter'] == 'llamacpp.chat-completions/1':
        require(target['placement'] == 'local-isolated', 'llamacpp_isolated_placement_required')
    auth = value['authentication']
    require(type(auth) is dict, 'invalid_authentication')
    if auth.get('kind') == 'none':
        closed(auth, {'kind'})
        require(target['placement'] == 'local-isolated', 'remote_secret_reference_required')
    else:
        closed(auth, {'kind', 'reference_id', 'revision'})
        require(auth['kind'] == 'bearer-reference', 'unsupported_authentication')
        uuid(auth['reference_id']); uint(auth['revision'], positive=True)
    cap_fields = {'instruction_role', 'function_tools', 'token_limit_field', 'strict_tools', 'parallel_tool_calls', 'store'}
    if value['protocol'] == 'stead.model-connection/2':
        cap_fields.add('required_tool_choice')
    caps = closed(value['capabilities'], cap_fields)
    required_choice = caps.get('required_tool_choice', 'unsupported')
    require(required_choice in ('unsupported', 'single-function/1')
            and (required_choice == 'unsupported' or caps['function_tools'] == 'json-schema-strings/1'),
            'unsupported_required_tool_choice')
    require(caps['instruction_role'] in ('system', 'developer')
            and caps['function_tools'] in ('disabled', 'json-schema-strings/1')
            and caps['token_limit_field'] in ('max_tokens', 'max_completion_tokens')
            and all(caps[key] in ('supported', 'unsupported') for key in ('strict_tools', 'parallel_tool_calls', 'store')),
            'unsupported_capabilities')
    limits = closed(value['limits'], LIMITS)
    parsed = {name: uint(limits[name], maximum, positive=name != 'billable_micro_usd')
              for name, maximum in LIMITS.items()}
    require(parsed['request_timeout_ms'] <= parsed['duration_ms']
            and parsed['input_tokens'] + parsed['output_tokens'] <= parsed['total_tokens'], 'inconsistent_limits')
    require(target['placement'] == 'local-isolated' or parsed['billable_micro_usd'] > 0,
            'remote_spend_ceiling_required')
    normalized = canonical({**value, 'endpoint': target})
    return ConnectionSpec(normalized, domain_hash(value['protocol'], normalized))


def effect_id(scope):
    """Proposed supervisor UUIDv7 derivation, not a new native UUID contract.

    Same project/run/attempt/sequence keeps its ID even if request bytes change;
    the native exact-intent conflict then remains able to detect that change.
    """
    closed(scope, SCOPE_FIELDS)
    text(scope['home'], 128, nonempty=True, label=True)
    for key in ('project_id', 'run_id', 'definition_id', 'runtime_id'):
        uuid(scope[key])
    uint(scope['attempt'], 3, positive=True); uint(scope['effect_sequence'], 32, positive=True)
    for key in ('definition_revision', 'runtime_revision'):
        uint(scope[key], positive=True)
    for key in ('run_contract_sha256', 'context_digest', 'runtime_policy_digest', 'connection_digest'):
        digest(scope[key])
    key = {name: scope[name] for name in ('home', 'project_id', 'run_id', 'attempt', 'effect_sequence')}
    suffix = bytearray.fromhex(domain_hash('stead.supervisor-effect-id/1', canonical(key)))[:16]
    suffix[:6] = bytes.fromhex(scope['run_id'].replace('-', ''))[:6]
    suffix[6] = (suffix[6] & 15) | 112
    suffix[8] = (suffix[8] & 63) | 128
    raw = suffix.hex()
    return '-'.join((raw[:8], raw[8:12], raw[12:16], raw[16:20], raw[20:]))


def tools(value):
    require(type(value) is list and len(value) <= 16, 'tool_registry_bound')
    names, identities, result = set(), set(), []
    for tool in value:
        closed(tool, {'tool_id', 'revision', 'name', 'description', 'arguments'})
        identity = uuid(tool['tool_id']); uint(tool['revision'], positive=True)
        require(type(tool['name']) is str and NAME.fullmatch(tool['name']) and tool['name'] not in names
                and identity not in identities, 'duplicate_or_invalid_tool')
        names.add(tool['name']); identities.add(identity)
        text(tool['description'], 1024, label=True)
        args = tool['arguments']
        require(type(args) is dict and len(args) <= 16, 'tool_argument_bound')
        for name, bound in args.items():
            require(type(name) is str and NAME.fullmatch(name), 'tool_argument_name')
            uint(bound, 8192, positive=True)
        result.append(tool)
    require(len(canonical(result)) <= 32768, 'tool_registry_byte_bound')
    # Argument-map insertion order is not a versioned distinction. Canonicalize
    # it before deriving the provider schema's ordered required-name array.
    return json.loads(canonical(result))


@dataclass(frozen=True)
class RequestDraft:
    body: bytes
    effect_id: str
    request_digest: str
    connection_digest: str
    scope_digest: str
    scope: bytes
    tool_registry: bytes
    turn: str
    # Not a credential, HTTP operation, native receipt or execution permit.


def prepare_chat(spec, scope, turn, instructions, messages, registry, *, prior_digest=None, required_tool=None):
    require(type(spec) is ConnectionSpec and connection(spec.raw) == spec, 'connection_pin_changed')
    value = spec.value(); identifier = effect_id(scope)
    require(scope['connection_digest'] == spec.sha256, 'connection_scope_changed')
    uint(turn, int(value['limits']['turns']), positive=True)
    text(instructions, 8192, nonempty=True)
    require(type(messages) is list and 1 <= len(messages) <= 32, 'message_bound')
    wire_messages = [{'role': value['capabilities']['instruction_role'], 'content': instructions}]
    # This first seam is one text conversation turn. Tool-result continuations
    # require a reviewed durable tool journal; accepting arbitrary caller-supplied
    # assistant/tool IDs here would invent provenance, so they stay unsupported.
    for message in messages:
        closed(message, {'role', 'content'})
        require(message['role'] == 'user', 'unsupported_message_role')
        text(message['content'], int(value['limits']['input_bytes']), nonempty=True)
        wire_messages.append(dict(message))
    approved = tools(registry)
    caps = value['capabilities']
    require(not approved or caps['function_tools'] == 'json-schema-strings/1', 'tools_unsupported')
    body = {'model': value['model'], 'messages': wire_messages, 'stream': False, 'n': 1,
            caps['token_limit_field']: int(value['limits']['output_tokens'])}
    if caps['store'] == 'supported':
        body['store'] = False
    offered = approved
    if required_tool is not None:
        require(caps.get('required_tool_choice') == 'single-function/1', 'required_tool_unsupported')
        offered = [tool for tool in approved if tool['name'] == required_tool]
        require(len(offered) == 1, 'required_tool_not_in_registry')
    if offered:
        body['tools'] = [{'type': 'function', 'function': {
            'name': tool['name'], 'description': tool['description'],
            'parameters': {'type': 'object', 'properties': {name: {'type': 'string', 'maxLength': int(bound)}
                for name, bound in tool['arguments'].items()}, 'required': list(tool['arguments']), 'additionalProperties': False},
            **({'strict': True} if caps['strict_tools'] == 'supported' else {})}} for tool in offered]
        body['tool_choice'] = 'required' if required_tool is not None else 'auto'
        if caps['parallel_tool_calls'] == 'supported':
            body['parallel_tool_calls'] = False
    raw = canonical(body)
    require(len(raw) <= int(value['limits']['input_bytes']), 'request_byte_bound')
    request_digest = domain_hash('stead.provider-request/1', canonical({
        'connection_digest': spec.sha256, 'scope': scope, 'turn': turn, 'body_sha256': hashlib.sha256(raw).hexdigest(),
        'tool_registry_sha256': domain_hash('stead.tool-registry/1', canonical(approved))}))
    if prior_digest is not None:
        require(digest(prior_digest) == request_digest, 'existing_effect_conflict')
    return RequestDraft(raw, identifier, request_digest, spec.sha256,
                        domain_hash('stead.provider-scope/1', canonical(scope)), canonical(scope), canonical(approved), turn)


def required_tool_name(body):
    if body.get('tool_choice') != 'required':
        return None
    offered = body.get('tools')
    require(type(offered) is list and len(offered) == 1 and type(offered[0]) is dict
            and type(offered[0].get('function')) is dict, 'invalid_required_tool_choice')
    name = offered[0]['function'].get('name')
    require(type(name) is str and NAME.fullmatch(name), 'invalid_required_tool_choice')
    return name


def validate_request(spec, request):
    """Check retained bytes, not authority; dispatch still needs native admission."""
    require(type(request) is RequestDraft, 'invalid_request_draft')
    scope = closed(decode(request.scope, 8192), SCOPE_FIELDS)
    body = decode(request.body, 65536)
    require(type(body) is dict and type(body.get('messages')) is list and len(body['messages']) >= 2,
            'invalid_request_draft')
    first = closed(body['messages'][0], {'role', 'content'})
    registry = decode(request.tool_registry, 32768)
    rebuilt = prepare_chat(spec, scope, request.turn, first['content'], body['messages'][1:], registry,
                           required_tool=required_tool_name(body))
    require(request == rebuilt, 'request_bytes_changed')
    return request


def reply_value(config, raw):
    """Explicit local compatibility profile; metadata cannot grant authority.

    Keep the original response bytes for its digest. Only known timing fields
    and absent/empty non-thinking metadata are removed before the unchanged
    common proposal decoder. No unknown extension or content is discarded.
    """
    maximum = int(config['limits']['output_bytes'])
    if config['adapter'] == 'openai.chat-completions/1':
        return decode(raw, maximum)
    require(config['adapter'] == 'llamacpp.chat-completions/1', 'unsupported_connection')
    require(type(raw) is bytes and 0 < len(raw) <= maximum, 'json_byte_bound')
    from decimal import Decimal, InvalidOperation

    def unique(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, 'duplicate_key')
            result[key] = item
        return result

    def constant(_):
        raise ValueError('invalid_number')

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                           parse_float=Decimal, parse_constant=constant)
        require(type(value) is dict, 'unsupported_response')
        if 'timings' in value:
            timing = value.pop('timings')
            integers = {'cache_n', 'prompt_n', 'predicted_n'}
            metrics = {'prompt_ms', 'prompt_per_token_ms', 'prompt_per_second',
                       'predicted_ms', 'predicted_per_token_ms', 'predicted_per_second'}
            require(type(timing) is dict and set(timing) == integers | metrics,
                    'unsupported_llamacpp_timings')
            for key in integers:
                require(type(timing[key]) is int and 0 <= timing[key] <= 262144,
                        'invalid_llamacpp_timing_count')
            for key in metrics:
                number = timing[key]
                require(type(number) in (int, Decimal) and 0 <= number <= 10**12,
                        'invalid_llamacpp_timing_metric')
        choices = value.get('choices')
        # Structural choice/message validation still belongs to the common
        # decoder. Handle only this one explicitly declared local extension.
        if type(choices) is list:
            require(len(choices) <= 128, 'json_array_bound')
            for choice in choices:
                if type(choice) is dict and type(choice.get('message')) is dict:
                    message = choice['message']
                    if 'reasoning_content' in message:
                        require(message['reasoning_content'] is None
                                or message['reasoning_content'] == '',
                                'llamacpp_non_thinking_profile_required')
                        del message['reasoning_content']
        # Decimal anywhere other than the exact timing metrics above fails;
        # then the existing bounded JSON shape/type/depth rules apply fully.
        return decode(canonical(value), maximum)
    except (UnicodeError, RecursionError, json.JSONDecodeError, TypeError, InvalidOperation) as error:
        raise ValueError('invalid_llamacpp_json') from error


def normalize_reply(spec, request, raw):
    """Return bounded untrusted proposals; never invoke, accept or retry them."""
    require(type(spec) is ConnectionSpec and connection(spec.raw) == spec
            and type(request) is RequestDraft and request.connection_digest == spec.sha256, 'response_pin_changed')
    validate_request(spec, request)
    config = spec.value()
    value = reply_value(config, raw)
    require(type(value) is dict and not set(value) - {'id', 'object', 'created', 'model', 'choices', 'usage',
            'system_fingerprint', 'service_tier'} and {'id', 'object', 'created', 'model', 'choices', 'usage'} <= set(value),
            'unsupported_response')
    text(value['id'], 200, nonempty=True, label=True)
    require(value['object'] == 'chat.completion' and value['model'] == config['model'], 'response_model_changed')
    require(type(value['created']) is int and 0 <= value['created'] <= 2**53 - 1, 'invalid_created')
    require(type(value['choices']) is list and len(value['choices']) == 1, 'single_choice_required')
    choice = value['choices'][0]
    require(type(choice) is dict and {'index', 'message', 'finish_reason'} <= set(choice)
            and not set(choice) - {'index', 'message', 'finish_reason', 'logprobs'}
            and type(choice['index']) is int and choice['index'] == 0, 'invalid_choice')
    message = choice['message']
    require(type(message) is dict and {'role', 'content'} <= set(message)
            and not set(message) - {'role', 'content', 'refusal', 'tool_calls', 'annotations'}
            and message['role'] == 'assistant' and message.get('annotations', []) == [], 'unsupported_message')
    content = message['content']
    require(content is None or type(content) is str, 'unsupported_content')
    if content is not None:
        text(content, int(config['limits']['output_bytes']))
    refusal = message.get('refusal')
    require(refusal is None or type(refusal) is str, 'invalid_refusal')
    if refusal is not None:
        text(refusal, 8192)
    usage = value['usage']
    require(type(usage) is dict and {'prompt_tokens', 'completion_tokens', 'total_tokens'} <= set(usage)
            and not set(usage) - {'prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_tokens_details',
                                 'completion_tokens_details'}, 'invalid_usage')
    counts = {}
    for source, limit in [('prompt_tokens', 'input_tokens'), ('completion_tokens', 'output_tokens'), ('total_tokens', 'total_tokens')]:
        require(type(usage[source]) is int and 0 <= usage[source] <= int(config['limits'][limit]), 'usage_bound')
        counts[source] = usage[source]
    require(counts['prompt_tokens'] + counts['completion_tokens'] == counts['total_tokens'], 'usage_total_changed')
    finish = choice['finish_reason']
    require(finish in ('stop', 'tool_calls', 'length', 'content_filter'), 'unsupported_finish')
    calls = message.get('tool_calls', [])
    require(type(calls) is list and len(calls) <= int(config['limits']['tool_calls']), 'tool_call_bound')
    require((finish == 'tool_calls') == bool(calls), 'inconsistent_tool_finish')
    registry = {tool['name']: tool for tool in tools(decode(request.tool_registry, 32768))}
    proposals, ids = [], set()
    for call in calls:
        closed(call, {'id', 'type', 'function'})
        text(call['id'], 200, nonempty=True, label=True)
        require(call['id'] not in ids and call['type'] == 'function', 'duplicate_or_unknown_tool_call')
        ids.add(call['id']); function = closed(call['function'], {'name', 'arguments'})
        require(type(function['name']) is str and function['name'] in registry, 'tool_not_in_registry')
        tool = registry[function['name']]
        arguments = closed(decode(text(function['arguments'], 8192).encode(), 8192), tool['arguments'])
        for name, bound in tool['arguments'].items():
            text(arguments[name], int(bound))
        proposals.append({'provider_call_id': call['id'], 'tool_id': tool['tool_id'], 'revision': tool['revision'],
                          'name': tool['name'], 'arguments': arguments})
    state = 'refused' if refusal else {'stop': 'text-proposal', 'tool_calls': 'tool-proposals',
                                      'length': 'incomplete', 'content_filter': 'blocked'}[finish]
    if state in ('refused', 'incomplete', 'blocked'):
        proposals = []
    else:
        required = required_tool_name(decode(request.body, 65536))
        if required is not None:
            require(len(proposals) == 1 and proposals[0]['name'] == required, 'required_tool_reply_mismatch')
    return {'state': state, 'text': content or '', 'tool_proposals': proposals,
            'observed_usage': counts, 'provider_response_id': value['id'],
            'response_sha256': hashlib.sha256(raw).hexdigest(), 'request_digest': request.request_digest,
            'authority': 'untrusted-proposal'}

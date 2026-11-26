"""Host-only model connection boundaries; no actual I/O/model/credentials."""
import copy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('model_connections_candidate', ROOT / 'scripts/urbit/model_connections.py')
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def uid(number):
    return '019939ba-4000-7000-8000-' + format(number, '012x')


def configuration():
    return {'protocol': 'stead.model-connection/1', 'connection_id': uid(1), 'revision': '1',
            'display_name': 'Approved inference connection', 'adapter': 'openai.chat-completions/1',
            'endpoint': {'url': 'https://api.example.test/v1/chat/completions', 'placement': 'remote-api',
                         'egress_policy_digest': 'a' * 64}, 'model': 'explicitly-configured-model-version',
            'authentication': {'kind': 'bearer-reference', 'reference_id': uid(2), 'revision': '3'},
            'capabilities': {'instruction_role': 'developer', 'function_tools': 'json-schema-strings/1',
                             'token_limit_field': 'max_completion_tokens', 'strict_tools': 'supported',
                             'parallel_tool_calls': 'supported', 'store': 'supported'},
            'limits': {'input_bytes': '65536', 'output_bytes': '65536', 'turns': '8', 'tool_calls': '8',
                       'request_timeout_ms': '10000', 'duration_ms': '120000', 'input_tokens': '4096',
                       'output_tokens': '1024', 'total_tokens': '8192', 'cost_units': '10000',
                       'billable_micro_usd': '100000'}}


def context(spec):
    return {'home': '~bus', 'project_id': uid(3), 'run_id': uid(4), 'attempt': '1', 'effect_sequence': '1',
            'run_contract_sha256': 'b' * 64, 'context_digest': 'c' * 64, 'definition_id': uid(5),
            'definition_revision': '2', 'runtime_id': uid(6), 'runtime_revision': '3',
            'runtime_policy_digest': 'd' * 64, 'connection_digest': spec.sha256}


def registry():
    return [{'tool_id': uid(7), 'revision': '2', 'name': 'read_declared_doc',
             'description': 'Request a current authorized read of an already-declared target.',
             'arguments': {'outcome_id': '36'}}]


def prepared(config=None, toolset=None):
    spec = M.connection(M.canonical(config or configuration()))
    request = M.prepare_chat(spec, context(spec), '1', 'Return an untrusted proposal only.',
                             [{'role': 'user', 'content': 'Clarify the pinned guide. λ'}],
                             registry() if toolset is None else toolset)
    return spec, request


def response():
    return {'id': 'chatcmpl-example', 'object': 'chat.completion', 'created': 1794770000,
            'model': 'explicitly-configured-model-version', 'choices': [{'index': 0,
             'message': {'role': 'assistant', 'content': 'Proposed text λ', 'refusal': None},
             'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 40, 'completion_tokens': 10, 'total_tokens': 50}}


class ConnectionBoundaryTests(unittest.TestCase):
    def test_canonical_connection_and_secret_reference_remain_separate_from_identity(self):
        value = configuration(); raw = json.dumps(value, indent=2).encode()
        spec = M.connection(raw)
        self.assertEqual(M.connection(spec.raw), spec)
        value['model'] = 'changed-after-load'
        self.assertEqual(spec.value()['model'], 'explicitly-configured-model-version')
        self.assertNotIn('principal_id', spec.value())
        self.assertEqual(spec.value()['authentication'], {'kind': 'bearer-reference', 'reference_id': uid(2), 'revision': '3'})

    def test_closed_fields_duplicate_keys_numbers_unicode_and_unbounded_json_fail(self):
        valid = configuration()
        invalid = [M.canonical({**valid, 'api_key': 'forbidden-value-field'}),
                   M.canonical(valid).replace(b'"revision":"1"', b'"revision":"1","revision":"2"', 1),
                   M.canonical({**valid, 'revision': True}), M.canonical({**valid, 'revision': 1.0}),
                   b'{"x":9007199254740992}', b'{"x":NaN}', b'{"x":"\\ud800"}', b'x' * 8193]
        for raw in invalid:
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                M.connection(raw)

    def test_endpoint_tls_credentials_paths_and_local_placement_are_explicit(self):
        for url in ['http://api.example.test/v1/chat/completions', 'https://user:key@api.example.test/v1/chat/completions',
                    'https://@api.example.test/v1/chat/completions',
                    'https://api.example.test/v1/chat/completions?key=x', 'https://127.0.0.1/v1/chat/completions',
                    'https://api.example.test/v1/../chat/completions', 'https://api.example.test/v1/%63hat/completions']:
            value = configuration(); value['endpoint']['url'] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                M.connection(M.canonical(value))
        value = configuration(); value['endpoint'].update(placement='local-isolated', url='http://127.0.0.1:11434/v1/chat/completions')
        value['authentication'] = {'kind': 'none'}; value['limits']['billable_micro_usd'] = '0'
        self.assertEqual(M.connection(M.canonical(value)).value()['endpoint']['placement'], 'local-isolated')
        value['endpoint']['url'] = 'https://127.0.0.1:443/v1/chat/completions'
        local = M.connection(M.canonical(value)); self.assertEqual(M.connection(local.raw), local)
        value['limits']['cost_units'] = '0'
        with self.assertRaises(ValueError): M.connection(M.canonical(value))

    def test_version_model_capability_and_egress_changes_change_exact_digest(self):
        value = configuration(); spec = M.connection(M.canonical(value))
        for field, changed in [('revision', '2'), ('model', 'another-explicit-version')]:
            self.assertNotEqual(M.connection(M.canonical({**value, field: changed})).sha256, spec.sha256)
        other = copy.deepcopy(value); other['endpoint']['egress_policy_digest'] = 'e' * 64
        changed = M.connection(M.canonical(other))
        with self.assertRaisesRegex(ValueError, 'connection_scope_changed'):
            M.prepare_chat(changed, context(spec), '1', 'Instructions', [{'role': 'user', 'content': 'Goal'}], [])

    def test_bounded_limits_reject_bool_zero_inconsistent_or_unsupported_configuration(self):
        for key, value in [('input_bytes', True), ('turns', '0'), ('tool_calls', '33'), ('input_tokens', '999999')]:
            raw = configuration(); raw['limits'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): M.connection(M.canonical(raw))
        raw = configuration(); raw['limits']['request_timeout_ms'] = '60000'; raw['limits']['duration_ms'] = '1000'
        with self.assertRaises(ValueError): M.connection(M.canonical(raw))
        raw = configuration(); raw['adapter'] = 'another-provider/1'
        with self.assertRaises(ValueError): M.connection(M.canonical(raw))

    def test_prepared_http_body_is_explicit_nonstreaming_and_contains_no_secret(self):
        spec, request = prepared(); body = json.loads(request.body)
        self.assertEqual(body['model'], spec.value()['model']); self.assertFalse(body['stream'])
        self.assertEqual(body['n'], 1); self.assertEqual(body['max_completion_tokens'], 1024)
        self.assertFalse(body['parallel_tool_calls']); self.assertFalse(body['store'])
        self.assertEqual(body['messages'][0]['role'], 'developer'); self.assertNotIn('authentication', body)
        self.assertNotIn('reference_id', request.body.decode()); self.assertNotIn('Authorization', request.body.decode())
        config = configuration(); config['capabilities']['function_tools'] = 'disabled'
        with self.assertRaisesRegex(ValueError, 'tools_unsupported'): prepared(config)
        self.assertNotIn('tools', json.loads(prepared(config, [])[1].body))
        tools = registry(); tools[0]['arguments'] = {'second': '12', 'first': '12'}
        reordered = copy.deepcopy(tools); reordered[0]['arguments'] = {'first': '12', 'second': '12'}
        self.assertEqual(prepared(toolset=tools)[1], prepared(toolset=reordered)[1])

    def test_effect_uuid_is_stable_for_sequence_and_changed_bytes_conflict(self):
        spec, first = prepared(); scope = context(spec)
        self.assertRegex(first.effect_id, M.UUID)
        changed = M.prepare_chat(spec, scope, '1', 'Return an untrusted proposal only.',
                                 [{'role': 'user', 'content': 'A different goal'}], registry())
        self.assertEqual(changed.effect_id, first.effect_id); self.assertNotEqual(changed.request_digest, first.request_digest)
        with self.assertRaisesRegex(ValueError, 'existing_effect_conflict'):
            M.prepare_chat(spec, scope, '1', 'Changed instructions', [{'role': 'user', 'content': 'Goal'}], [], prior_digest=first.request_digest)
        self.assertNotEqual(M.effect_id({**scope, 'attempt': '2'}), first.effect_id)
        self.assertNotEqual(M.effect_id({**scope, 'effect_sequence': '2'}), first.effect_id)
        self.assertEqual(M.validate_request(spec, first), first)
        altered_body = json.loads(first.body); altered_body['model'] = 'substituted-model'
        for altered in [replace(first, body=M.canonical(altered_body)), replace(first, effect_id=uid(20)),
                        replace(first, request_digest='e' * 64), replace(first, scope_digest='e' * 64)]:
            with self.subTest(altered=altered.request_digest), self.assertRaises(ValueError):
                M.validate_request(spec, altered)

    def test_provider_cannot_supply_instruction_or_tool_history_and_input_stays_bounded(self):
        spec, _ = prepared()
        for role in ['system', 'developer', 'assistant', 'tool']:
            with self.subTest(role=role), self.assertRaises(ValueError):
                M.prepare_chat(spec, context(spec), '1', 'Pinned instructions', [{'role': role, 'content': 'Escalate'}], [])
        with self.assertRaises(ValueError): M.prepare_chat(spec, context(spec), '9', 'Pinned instructions', [{'role': 'user', 'content': 'Goal'}], [])
        with self.assertRaises(ValueError): M.prepare_chat(spec, context(spec), '1', 'Pinned instructions', [{'role': 'user', 'content': 'λ' * 65536}], [])

    def test_model_response_is_only_a_bounded_proposal_not_completion(self):
        spec, request = prepared(); value = M.normalize_reply(spec, request, M.canonical(response()))
        self.assertEqual(value['state'], 'text-proposal'); self.assertEqual(value['authority'], 'untrusted-proposal')
        self.assertEqual(value['text'], 'Proposed text λ'); self.assertEqual(value['tool_proposals'], [])
        self.assertNotIn('accepted', value); self.assertNotIn('done', value)
        changed = response(); changed['model'] = 'silently-substituted-model'
        with self.assertRaisesRegex(ValueError, 'response_model_changed'): M.normalize_reply(spec, request, M.canonical(changed))

    def test_unknown_duplicate_or_overbound_tool_arguments_never_become_effects(self):
        spec, request = prepared(); value = response(); value['choices'][0].update(finish_reason='tool_calls')
        message = value['choices'][0]['message']; message['content'] = None
        call = {'id': 'call-1', 'type': 'function', 'function': {'name': 'read_declared_doc', 'arguments': json.dumps({'outcome_id': uid(10)})}}
        message['tool_calls'] = [call]
        proposal = M.normalize_reply(spec, request, M.canonical(value))['tool_proposals'][0]
        self.assertEqual(proposal['tool_id'], uid(7)); self.assertEqual(proposal['arguments'], {'outcome_id': uid(10)})
        for arguments in ['{"outcome_id":"a","outcome_id":"b"}', '{"outcome_id":"' + 'x' * 37 + '"}', '{"outcome_id":"x","admin":"yes"}']:
            wrong = copy.deepcopy(value); wrong['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = arguments
            with self.subTest(arguments=arguments), self.assertRaises(ValueError): M.normalize_reply(spec, request, M.canonical(wrong))
        wrong = copy.deepcopy(value); wrong['choices'][0]['message']['tool_calls'][0]['function']['name'] = 'grant_admin'
        with self.assertRaisesRegex(ValueError, 'tool_not_in_registry'): M.normalize_reply(spec, request, M.canonical(wrong))
        message['tool_calls'].append(copy.deepcopy(call))
        with self.assertRaises(ValueError): M.normalize_reply(spec, request, M.canonical(value))

    def test_refusal_truncation_filter_and_bad_usage_cannot_report_success(self):
        spec, request = prepared()
        for finish, state in [('length', 'incomplete'), ('content_filter', 'blocked')]:
            value = response(); value['choices'][0]['finish_reason'] = finish
            self.assertEqual(M.normalize_reply(spec, request, M.canonical(value))['state'], state)
        value = response(); value['choices'][0]['message']['refusal'] = 'Cannot provide that output.'
        self.assertEqual(M.normalize_reply(spec, request, M.canonical(value))['state'], 'refused')
        for count in [True, 1.5, 999999, -1]:
            value = response(); value['usage']['completion_tokens'] = count
            with self.subTest(count=count), self.assertRaises(ValueError): M.normalize_reply(spec, request, M.canonical(value))

    def test_wrong_connection_multiple_choices_unknown_fields_and_raw_html_remain_untrusted(self):
        spec, request = prepared(); value = response(); value['choices'].append(copy.deepcopy(value['choices'][0]))
        with self.assertRaises(ValueError): M.normalize_reply(spec, request, M.canonical(value))
        changed = configuration(); changed['revision'] = '2'
        with self.assertRaisesRegex(ValueError, 'response_pin_changed'):
            M.normalize_reply(M.connection(M.canonical(changed)), request, M.canonical(response()))
        value = response(); value['authority'] = 'maintainer'
        with self.assertRaises(ValueError): M.normalize_reply(spec, request, M.canonical(value))
        value = response(); value['choices'][0]['message']['content'] = '<script>fake_accept()</script>'
        result = M.normalize_reply(spec, request, M.canonical(value))
        self.assertEqual(result['text'], value['choices'][0]['message']['content'])
        self.assertEqual(result['authority'], 'untrusted-proposal')


if __name__ == '__main__':
    unittest.main()

"""Authored local-adapter shape cases; no model, server or transport execution."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('connection_fixtures', Path(__file__).with_name('test_model_connections.py'))
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)
M = F.M


def local():
    value = F.configuration()
    value['adapter'] = 'llamacpp.chat-completions/1'
    value['endpoint'].update(url='http://127.0.0.1:8080/v1/chat/completions', placement='local-isolated')
    value['authentication'] = {'kind': 'none'}
    value['limits']['billable_micro_usd'] = '0'
    value['capabilities'].update(instruction_role='system', token_limit_field='max_tokens',
                                 strict_tools='unsupported', parallel_tool_calls='unsupported', store='unsupported')
    return value


def response():
    value = F.response()
    # Authored documented server shape; this is not a captured model response.
    value['timings'] = {'cache_n': 0, 'prompt_n': 40, 'predicted_n': 10,
                        'prompt_ms': 30.958, 'prompt_per_token_ms': 0.77395,
                        'prompt_per_second': 1292.073,
                        'predicted_ms': 661.064, 'predicted_per_token_ms': 66.1064,
                        'predicted_per_second': 15.127}
    value['choices'][0]['message']['reasoning_content'] = ''
    value['usage']['prompt_tokens_details'] = {'cached_tokens': 0}
    return value


class LlamaCppConnectionTests(unittest.TestCase):
    def test_profile_is_explicit_versioned_local_and_native_cost_remains_positive(self):
        config = local()
        spec, request = F.prepared(config)
        old = copy.deepcopy(config); old['adapter'] = 'openai.chat-completions/1'
        self.assertNotEqual(spec.sha256, M.connection(M.canonical(old)).sha256)
        self.assertEqual(request.connection_digest, spec.sha256)
        for changes in ({'adapter': 'llamacpp.chat-completions/2'},
                        {'adapter': 'anything-automatic'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                M.connection(M.canonical(config | changes))
        remote = F.configuration(); remote['adapter'] = config['adapter']
        with self.assertRaisesRegex(ValueError, 'llamacpp_isolated_placement_required'):
            M.connection(M.canonical(remote))
        config['limits']['cost_units'] = '0'
        with self.assertRaises(ValueError):
            M.connection(M.canonical(config))

    def test_documented_fractional_timings_keep_raw_hash_and_untrusted_usage(self):
        spec, request = F.prepared(local())
        raw = M.canonical(response())
        result = M.normalize_reply(spec, request, raw)
        self.assertEqual(result['response_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['text'], 'Proposed text λ')
        self.assertEqual(result['observed_usage'], {'prompt_tokens': 40, 'completion_tokens': 10, 'total_tokens': 50})
        self.assertEqual(result['authority'], 'untrusted-proposal')
        self.assertEqual(result['state'], 'text-proposal')
        self.assertNotIn('timings', result)
        generic, generic_request = F.prepared()
        with self.assertRaises(ValueError):
            M.normalize_reply(generic, generic_request, raw)

    def test_tools_remain_known_bounded_proposals_with_exact_original_response(self):
        spec, request = F.prepared(local())
        value = response(); choice = value['choices'][0]
        choice['finish_reason'] = 'tool_calls'
        choice['message'].update(content=None, tool_calls=[{
            'id': 'local-call-1', 'type': 'function', 'function': {
                'name': 'read_declared_doc', 'arguments': M.canonical({'outcome_id': F.uid(9)}).decode()}}])
        raw = M.canonical(value); result = M.normalize_reply(spec, request, raw)
        self.assertEqual(result['state'], 'tool-proposals')
        self.assertEqual(result['tool_proposals'][0]['tool_id'], F.uid(7))
        self.assertEqual(result['tool_proposals'][0]['arguments'], {'outcome_id': F.uid(9)})
        self.assertEqual(result['response_sha256'], hashlib.sha256(raw).hexdigest())
        for name in ['shell', 'read_any_url']:
            choice['message']['tool_calls'][0]['function']['name'] = name
            with self.assertRaisesRegex(ValueError, 'tool_not_in_registry'):
                M.normalize_reply(spec, request, M.canonical(value))

    def test_only_exact_bounded_timing_fields_can_contain_fractional_numbers(self):
        spec, request = F.prepared(local())
        bad = []
        for key, item in [('cache_n', True), ('prompt_n', 1.5), ('predicted_n', 262145),
                          ('prompt_ms', -0.1), ('predicted_ms', True),
                          ('predicted_per_second', 10**12 + 1), ('prompt_per_second', '1.0')]:
            value = response(); value['timings'][key] = item; bad.append(value)
        value = response(); value['timings']['unknown'] = 1; bad.append(value)
        value = response(); del value['timings']['cache_n']; bad.append(value)
        value = response(); value['timings'] = None; bad.append(value)
        value = response(); value['created'] = 1.25; bad.append(value)
        value = response(); value['usage']['prompt_tokens'] = 40.5; bad.append(value)
        value = response(); value['provider_extension'] = {'secret': 'not-authority'}; bad.append(value)
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                M.normalize_reply(spec, request, M.canonical(value))

    def test_non_thinking_extension_never_discards_unexpected_reasoning_or_content(self):
        spec, request = F.prepared(local())
        for item in ('hidden explanation', False, 0, [], {}):
            value = response(); value['choices'][0]['message']['reasoning_content'] = item
            with self.subTest(item=item), self.assertRaises(ValueError):
                M.normalize_reply(spec, request, M.canonical(value))
        for item in (None, ''):
            value = response(); value['choices'][0]['message'].update(reasoning_content=item, content='<b>data λ</b>')
            self.assertEqual(M.normalize_reply(spec, request, M.canonical(value))['text'], '<b>data λ</b>')
        value = response(); del value['timings']; del value['choices'][0]['message']['reasoning_content']
        self.assertEqual(M.normalize_reply(spec, request, M.canonical(value))['state'], 'text-proposal')

    def test_original_closed_byte_duplicate_model_and_incomplete_guards_still_apply(self):
        spec, request = F.prepared(local()); raw = M.canonical(response())
        invalid = [b'{"id":"duplicate",' + raw[1:],
                   raw.replace(b'30.958', b'NaN'), raw.replace(b'30.958', b'Infinity'),
                   raw.replace(b'30.958', b'1e999999'), b'[' * 2000 + b']' * 2000,
                   b'\xff', raw + b' ' * int(local()['limits']['output_bytes'])]
        for data in invalid:
            with self.subTest(data=data[:30]), self.assertRaises(ValueError):
                M.normalize_reply(spec, request, data)
        value = response(); value['model'] = 'another-model'
        with self.assertRaisesRegex(ValueError, 'response_model_changed'):
            M.normalize_reply(spec, request, M.canonical(value))
        for finish, state in [('length', 'incomplete'), ('content_filter', 'blocked')]:
            value = response(); value['choices'][0]['finish_reason'] = finish
            result = M.normalize_reply(spec, request, M.canonical(value))
            self.assertEqual(result['state'], state)
            self.assertEqual(result['tool_proposals'], [])


if __name__ == '__main__':
    unittest.main()

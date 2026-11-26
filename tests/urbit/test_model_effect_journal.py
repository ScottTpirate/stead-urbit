"""Authored private filesystem cases; no native effect, model call or transport."""
from contextlib import contextmanager
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parents[2] / 'scripts/urbit'


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load('model_connections')
J = load('model_effect_journal')


def uid(n):
    return '019939ba-4000-7000-8000-' + format(n, '012x')


def inputs(sequence='1', body='Revise this synthetic guide. λ', run=4):
    config = {'protocol': 'stead.model-connection/1', 'connection_id': uid(1), 'revision': '1',
        'display_name': 'Private test connection', 'adapter': 'openai.chat-completions/1',
        'endpoint': {'url': 'http://127.0.0.1:8080/v1/chat/completions', 'placement': 'local-isolated',
                     'egress_policy_digest': 'a' * 64}, 'model': 'synthetic-model',
        'authentication': {'kind': 'none'},
        'capabilities': {'instruction_role': 'system', 'function_tools': 'disabled',
            'token_limit_field': 'max_tokens', 'strict_tools': 'unsupported',
            'parallel_tool_calls': 'unsupported', 'store': 'unsupported'},
        'limits': {'input_bytes': '65536', 'output_bytes': '65536', 'turns': '8', 'tool_calls': '8',
            'request_timeout_ms': '10000', 'duration_ms': '120000', 'input_tokens': '4096',
            'output_tokens': '1024', 'total_tokens': '8192', 'cost_units': '10000', 'billable_micro_usd': '0'}}
    spec = M.connection(M.canonical(config))
    scope = {'home': '~bus', 'project_id': uid(3), 'run_id': uid(run), 'attempt': '1',
        'effect_sequence': sequence, 'run_contract_sha256': 'b' * 64, 'context_digest': 'c' * 64,
        'definition_id': uid(5), 'definition_revision': '2', 'runtime_id': uid(6),
        'runtime_revision': '3', 'runtime_policy_digest': 'd' * 64, 'connection_digest': spec.sha256}
    request = M.prepare_chat(spec, scope, '1', 'Return an untrusted text proposal.',
                             [{'role': 'user', 'content': body}], [])
    return spec, request


def intent(spec, request):
    charge = {'tool_calls': '0', 'network_calls': '1', 'token_units': '5120',
              'cost_units': '1', 'input_bytes': str(len(request.body)), 'output_bytes': '65536'}
    return M.canonical({'effect_id': request.effect_id, 'kind': 'provider-call',
        'provider_id': spec.value()['connection_id'], 'request_digest': request.request_digest,
        'result': '', 'charge': M.canonical(charge).decode()})


def response(content='Revised synthetic guide. λ', finish='stop', refusal=None):
    return M.canonical({'id': 'synthetic-call', 'object': 'chat.completion', 'created': 1,
        'model': 'synthetic-model', 'choices': [{'index': 0, 'finish_reason': finish,
        'message': {'role': 'assistant', 'content': content, 'refusal': refusal}}],
        'usage': {'prompt_tokens': 12, 'completion_tokens': 10, 'total_tokens': 22}})


@contextmanager
def directory():
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        root.chmod(0o700)
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            yield root, fd
        finally:
            os.close(fd)


@contextmanager
def opened(fd, spec, request):
    journal = J.EffectJournal(fd, spec, request)
    try:
        yield journal
    finally:
        journal.close()


class ModelEffectJournalTests(unittest.TestCase):
    def test_exact_prepare_reopen_and_conflicting_request_never_overwrite(self):
        spec, request = inputs()
        with directory() as (root, fd):
            with opened(fd, spec, request) as journal:
                self.assertEqual(journal.observe()['state'], 'prepared')
                self.assertFalse(journal.observe()['may_dispatch'])
            path = root / request.effect_id / 'request.json'
            before = path.read_bytes()
            with opened(fd, spec, request) as journal:
                self.assertEqual(journal.observe()['request_digest'], request.request_digest)
            changed_spec, changed = inputs(body='Changed task intent')
            self.assertEqual(changed.effect_id, request.effect_id)
            with self.assertRaises(ValueError): J.EffectJournal(fd, changed_spec, changed)
            self.assertEqual(path.read_bytes(), before)

    def test_started_is_new_only_once_and_reopened_state_has_no_dispatch(self):
        spec, request = inputs(); raw = intent(spec, request)
        with directory() as (root, fd):
            with opened(fd, spec, request) as journal:
                self.assertTrue(journal.record_started(raw, 'e' * 64))
                self.assertFalse(journal.record_started(raw, 'e' * 64))
                before = (root / request.effect_id / 'started.json').read_bytes()
                with self.assertRaises(ValueError): journal.record_started(raw, 'f' * 64)
            with opened(fd, spec, request) as journal:
                self.assertEqual(journal.observe()['state'], 'unknown')
                self.assertFalse(journal.record_started(raw, 'e' * 64))
                self.assertFalse(journal.observe()['may_dispatch'])
            self.assertEqual((root / request.effect_id / 'started.json').read_bytes(), before)

    def test_response_receipt_binds_original_bytes_without_embedding_long_proposal(self):
        spec, request = inputs(); raw = response('λ' * 18000)
        with directory() as (root, fd):
            with opened(fd, spec, request) as journal:
                journal.record_started(intent(spec, request), 'e' * 64)
                result = journal.retain_response(raw)
                self.assertEqual(result['state'], 'completed')
                self.assertFalse(result['native_settled'])
                self.assertEqual(result['response_sha256'], J.sha(raw))
                self.assertEqual(journal.retain_response(raw), result)
                with self.assertRaises(ValueError): journal.retain_response(response('different'))
            target = root / request.effect_id
            self.assertEqual((target / 'response.bin').read_bytes(), raw)
            receipt = (target / 'result.json').read_bytes()
            self.assertLessEqual(len(receipt), J.RECORD_MAX)
            self.assertNotIn(('λ' * 100).encode(), receipt)
            self.assertEqual(json.loads(receipt)['proposal_digest'], M.domain_hash(
                'stead.model-journal-proposal/1', M.canonical(M.normalize_reply(spec, request, raw))))
            with opened(fd, spec, request) as journal: self.assertEqual(journal.observe(), result)

    def test_response_only_recovery_never_silently_completes_publication(self):
        spec, request = inputs(); raw = response(); publish = J.publish
        with directory() as (root, fd):
            with opened(fd, spec, request) as journal:
                journal.record_started(intent(spec, request), 'e' * 64)
                def interrupted(target, name, body, maximum):
                    if name == 'result.json': raise OSError('authored boundary interruption')
                    return publish(target, name, body, maximum)
                with patch.object(J, 'publish', interrupted), self.assertRaises(OSError): journal.retain_response(raw)
                self.assertEqual(journal.observe()['state'], 'response-retained')
            with opened(fd, spec, request) as journal:
                self.assertEqual(journal.retain_response(raw)['state'], 'response-retained')
                self.assertFalse((root / request.effect_id / 'result.json').exists())

    def test_refusal_length_and_malformed_model_output_never_become_authority(self):
        spec, request = inputs()
        cases = [(response(refusal='No'), 'refused', 'completed'),
                 (response(finish='length'), 'incomplete', 'completed'),
                 (b'{"malformed":true}', 'unknown', 'unknown')]
        for raw, observation, state in cases:
            with self.subTest(observation=observation), directory() as (_, fd), opened(fd, spec, request) as journal:
                journal.record_started(intent(spec, request), 'e' * 64)
                observed = journal.retain_response(raw)
                self.assertEqual((observed['state'], observed['provider_observation']), (state, observation))
                self.assertFalse(observed['may_dispatch']); self.assertFalse(observed['native_settled'])

    def test_unknown_terminal_preserves_uncertainty_and_cannot_take_late_response(self):
        spec, request = inputs()
        with directory() as (root, fd), opened(fd, spec, request) as journal:
            journal.record_started(intent(spec, request), 'e' * 64)
            observed = journal.record_unknown('timeout')
            before = (root / request.effect_id / 'result.json').read_bytes()
            self.assertEqual(observed['state'], 'unknown')
            with self.assertRaises(ValueError): journal.retain_response(response())
            with self.assertRaises(ValueError): journal.record_unknown('canceled')
            self.assertEqual((root / request.effect_id / 'result.json').read_bytes(), before)

    def test_every_native_intent_identity_and_full_charge_is_exactly_bound(self):
        spec, request = inputs(); value = json.loads(intent(spec, request))
        with directory() as (_, fd), opened(fd, spec, request) as journal:
            for field, bad in [('effect_id', uid(99)), ('provider_id', uid(98)), ('request_digest', '0' * 64),
                               ('result', 'unexpected'), ('kind', 'doc-proposal')]:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    journal.record_started(M.canonical(value | {field: bad}), 'e' * 64)
            for field, bad in [('network_calls', '0'), ('token_units', '0'), ('cost_units', '0'),
                               ('input_bytes', True), ('output_bytes', '18446744073709551616')]:
                charge = json.loads(value['charge']) | {field: bad}
                with self.subTest(field=field), self.assertRaises(ValueError):
                    journal.record_started(M.canonical(value | {'charge': M.canonical(charge).decode()}), 'e' * 64)
            raw = intent(spec, request)
            journal.record_started(raw, 'e' * 64)
            charge = json.loads(value['charge']); charge['cost_units'] = '2'
            with self.assertRaises(ValueError):
                journal.record_started(M.canonical(value | {'charge': M.canonical(charge).decode()}), 'e' * 64)
            self.assertEqual(json.loads(J.read(journal.fd, 'started.json', J.RECORD_MAX))['native_intent'], raw.decode())

    def test_write_link_unlink_and_each_fsync_fault_keep_no_retry_permission(self):
        spec, request = inputs(); raw = intent(spec, request)
        cases = [('write', None), ('link', None), ('unlink', None), ('fsync', 1), ('fsync', 2), ('fsync', 3)]
        for operation, nth in cases:
            with self.subTest(operation=operation, nth=nth), directory() as (root, fd):
                with opened(fd, spec, request) as journal:
                    original = getattr(J.os, operation); count = 0
                    def fail(*args, **kwargs):
                        nonlocal count
                        count += 1
                        if nth is None or count == nth: raise OSError('authored publication failure')
                        return original(*args, **kwargs)
                    with patch.object(J.os, operation, fail), self.assertRaises(OSError): journal.record_started(raw, 'e' * 64)
                if operation == 'fsync' and nth == 3:
                    with opened(fd, spec, request) as journal:
                        self.assertEqual(journal.observe()['state'], 'unknown')
                        self.assertFalse(journal.record_started(raw, 'e' * 64))
                else:
                    with self.assertRaises((ValueError, OSError)): J.EffectJournal(fd, spec, request)
                self.assertEqual((root / request.effect_id / 'request.json').read_bytes(), J.prepared_record(spec, request))

    def test_wrong_modes_symlinks_hardlinks_and_extra_names_are_refused(self):
        spec, request = inputs()
        for kind in ('root-mode', 'file-mode', 'symlink', 'hardlink', 'extra', 'extra-root'):
            with self.subTest(kind=kind), directory() as (root, fd):
                with opened(fd, spec, request): pass
                target = root / request.effect_id / 'request.json'
                if kind == 'root-mode': root.chmod(0o750)
                elif kind == 'file-mode': target.chmod(0o644)
                elif kind == 'symlink':
                    original = target.with_name('private-original'); target.rename(original); target.symlink_to(original.name)
                elif kind == 'hardlink': os.link(target, root / request.effect_id / 'extra-link')
                elif kind == 'extra': target.with_name('unexpected').write_bytes(b'unknown')
                else: (root / 'unknown').write_bytes(b'unknown')
                with self.assertRaises((ValueError, OSError)): J.EffectJournal(fd, spec, request)

    def test_cross_run_capacity_and_replaced_directory_are_fail_closed(self):
        spec, request = inputs()
        with directory() as (root, fd), opened(fd, spec, request) as journal:
            other_spec, other = inputs(sequence='2', run=88)
            with self.assertRaises(ValueError): J.EffectJournal(fd, other_spec, other)
            # A held directory FD cannot conceal a replaced public entry.
            target = root / request.effect_id; target.rename(root / uid(99)); target.mkdir(mode=0o700)
            with self.assertRaises(ValueError): journal.observe()
        with directory() as (root, fd):
            for n in range(33): (root / uid(100 + n)).mkdir(mode=0o700)
            with self.assertRaises(ValueError): J.EffectJournal(fd, spec, request)

    def test_oversize_duplicate_json_and_tampered_receipt_remain_rejected(self):
        spec, request = inputs()
        with directory() as (root, fd), opened(fd, spec, request) as journal:
            journal.record_started(intent(spec, request), 'e' * 64)
            with self.assertRaises(ValueError): journal.retain_response(b'x' * 65537)
            self.assertEqual(journal.observe()['state'], 'unknown')
            journal.retain_response(response())
            target = root / request.effect_id / 'result.json'; raw = target.read_bytes()
            for corrupted in (raw.replace(b'"completed"', b'"changed"') + b' ',
                              b'{"protocol":"duplicate",' + raw[1:],
                              raw.replace(request.request_digest.encode(), b'f' * 64)):
                target.write_bytes(corrupted)
                with self.assertRaises(ValueError): journal.observe()
            target.write_bytes(raw); self.assertEqual(journal.observe()['state'], 'completed')

    def test_invalid_preparation_does_not_leak_fd_or_touch_the_attempt(self):
        spec, request = inputs()
        with directory() as (root, fd):
            with patch.object(J.os, 'dup', wraps=os.dup) as duplicate:
                with self.assertRaises(ValueError): J.EffectJournal(fd, spec, replace(request, body=b'{}'))
                duplicate.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])
            with patch.object(J.os, 'geteuid', return_value=0), self.assertRaises(ValueError):
                J.EffectJournal(fd, spec, request)


if __name__ == '__main__':
    unittest.main()

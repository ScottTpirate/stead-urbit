"""Inert document revision checks; real tiny files, no model or network call.

Only UID/source ownership observations are synthetic in client/worker orchestration.
The request adapter, normalizer, Markdown assessment and saved artifact bytes are real.
"""
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'scripts/urbit/model_connections.py'
CLIENT = ROOT / 'scripts/ci/model_proof/client.py'
WORKER = ROOT / 'scripts/ci/model_proof/worker.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


C = load('doc_revision_client', CLIENT)
M = load('doc_revision_adapter', MODEL)
W = load('doc_revision_worker', WORKER)


def reply(markdown):
    return C.canonical({'id': 'synthetic-reply', 'object': 'chat.completion', 'created': 1,
        'model': C.MODEL, 'choices': [{'index': 0, 'finish_reason': 'tool_calls',
            'message': {'role': 'assistant', 'content': None, 'tool_calls': [{
                'id': 'synthetic-tool', 'type': 'function', 'function': {
                    'name': 'propose_doc_update', 'arguments': json.dumps({'markdown': markdown})}}]}}],
        'usage': {'prompt_tokens': 120, 'completion_tokens': 110, 'total_tokens': 230}})


def expected():
    return C.SOURCE_MARKDOWN.replace('Monday', 'Wednesday')


def stat_uid(path, uid):
    values = list(os.stat(path))
    values[4] = uid
    return os.stat_result(values)


class ModelDocRevisionTests(unittest.TestCase):
    def invoke(self, root, raw=None, error=None):
        output = root / 'client'
        original_lstat = Path.lstat
        def info(path, *args, **kwargs):
            if path == MODEL:
                return stat_uid(path, 65534)
            if path == output:
                return stat_uid(path, 1000)
            return original_lstat(path, *args, **kwargs)
        # Namespace/UID ownership belongs to the actual runtime owner. These
        # inert tests explicitly replace it while using actual bounded files.
        with ExitStack() as stack:
            stack.enter_context(patch.object(C, 'SOURCE', MODEL))
            stack.enter_context(patch.object(C, 'OUTPUT', output))
            stack.enter_context(patch.object(C.os, 'getuid', return_value=1000))
            stack.enter_context(patch.object(C.os, 'geteuid', return_value=1000))
            stack.enter_context(patch.object(C.sys, 'argv', ['client.py']))
            stack.enter_context(patch.object(Path, 'lstat', info))
            post = stack.enter_context(patch.object(C, 'post_once', return_value=raw, side_effect=error))
            status = C.main()
            post.assert_called_once()
        return status, {p.name: p.read_bytes() for p in output.iterdir()}

    def test_request_contains_original_task_without_completed_edit(self):
        spec, scope = C.connection_and_scope(M)
        request = C.prepare_revision(M, spec, scope)
        body = json.loads(request.body)
        self.assertEqual(spec.value()['limits']['turns'], '1')
        self.assertEqual(spec.value()['limits']['billable_micro_usd'], '0')
        self.assertEqual(C.revision_context()['repositories'], [])
        content = body['messages'][-1]['content']
        self.assertIn(C.TASK, content)
        self.assertIn(json.dumps(C.SOURCE_MARKDOWN)[1:-1], content)
        self.assertNotIn('Wednesday', content)
        self.assertNotIn('Wednesday', body['messages'][0]['content'])
        self.assertEqual(body['max_tokens'], 256)
        self.assertEqual(body['tools'][0]['function']['parameters']['properties']['markdown']['type'], 'string')
        self.assertEqual(M.validate_request(spec, request), request)

    def test_identity_untouched_material_and_semantic_change_are_required(self):
        self.assertTrue(C.accepted_revision(C.assess_revision(expected())))
        variants = [C.SOURCE_MARKDOWN, expected().replace(C.DOCUMENT_ID, C.uid(99)),
            expected().replace('state: published', 'state: draft'),
            expected().replace('10:00', '11:00'), expected().replace('Room Cedar', 'Room Elm'),
            expected().replace('document owner', 'team'), expected().rstrip('\n'),
            '```markdown\n' + expected() + '```\n', expected().replace('Wednesday', 'Tuesday')]
        for value in variants:
            with self.subTest(value=value):
                self.assertFalse(C.accepted_revision(C.assess_revision(value)))
        self.assertFalse(C.accepted_revision(C.assess_revision(None)))

    def test_actual_client_retains_exact_original_response_and_argument(self):
        raw = reply(expected())
        with tempfile.TemporaryDirectory() as directory:
            status, files = self.invoke(Path(directory), raw)
        self.assertEqual(status, 0)
        self.assertEqual(set(files), {'request.json', 'response.bin', 'proposal.json', 'report.json'})
        self.assertEqual(files['response.bin'], raw)
        proposal = json.loads(files['proposal.json'])
        self.assertEqual(proposal['tool_proposals'][0]['arguments'], {'markdown': expected()})
        self.assertEqual(proposal['response_sha256'], hashlib.sha256(raw).hexdigest())
        report = json.loads(files['report.json'])
        self.assertTrue(report['semantic_edit_proposed'])
        self.assertEqual(report['revision_checks'], C.assess_revision(expected()))
        for key in ('tool_executed', 'document_mutated', 'native_authority_supplied', 'qualifies_g3'):
            self.assertIs(report[key], False)

    def test_wrong_model_edit_is_retained_as_failure_without_repair(self):
        wrong = expected().rstrip('\n')
        raw = reply(wrong)
        with tempfile.TemporaryDirectory() as directory:
            status, files = self.invoke(Path(directory), raw)
        self.assertEqual(status, 1)
        self.assertEqual(files['response.bin'], raw)
        self.assertEqual(json.loads(files['proposal.json'])['tool_proposals'][0]['arguments']['markdown'], wrong)
        report = json.loads(files['report.json'])
        self.assertEqual((report['attempted_requests'], report['completed_responses']), (1, 1))
        self.assertFalse(report['semantic_edit_proposed'])
        self.assertFalse(report['revision_checks']['final_newline_preserved'])

    def test_uncertain_request_never_retries_or_manufactures_a_response(self):
        with tempfile.TemporaryDirectory() as directory:
            status, files = self.invoke(Path(directory), error=TimeoutError())
        self.assertEqual(status, 1)
        self.assertEqual(set(files), {'request.json', 'report.json'})
        report = json.loads(files['report.json'])
        self.assertEqual((report['attempted_requests'], report['completed_responses']), (1, 0))
        self.assertEqual(report['error_class'], 'TimeoutError')

    def test_worker_recomputes_verdict_from_retained_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status, files = self.invoke(root, reply(expected()))
            self.assertEqual(status, 0)
            original_lstat = Path.lstat
            def info(path, *args, **kwargs):
                return stat_uid(path, 1000) if path == root / 'client' else original_lstat(path, *args, **kwargs)
            # Privileged immutable-file metadata is covered by the existing
            # owner profile; here only those observations are doubled.
            with patch.object(W, 'OUTPUT', root), patch.object(W, 'INPUT', CLIENT.parent), \
                    patch.object(Path, 'lstat', info), \
                    patch.object(W, 'ordinary', side_effect=lambda path, **kw: path.read_bytes()):
                pins, digest = W.result_files()
                self.assertEqual(digest, C.sha(files['report.json']))
                self.assertEqual(set(pins), set(files))
                proposal = json.loads(files['proposal.json'])
                proposal['tool_proposals'][0]['arguments']['markdown'] = C.SOURCE_MARKDOWN
                altered = C.canonical(proposal)
                (root / 'client/proposal.json').write_bytes(altered)
                report = json.loads(files['report.json'])
                report['artifacts']['proposal.json'] = {'bytes': len(altered), 'sha256': C.sha(altered)}
                (root / 'client/report.json').write_bytes(C.canonical(report))
                with self.assertRaises(ValueError):
                    W.result_files()


if __name__ == '__main__':
    unittest.main()

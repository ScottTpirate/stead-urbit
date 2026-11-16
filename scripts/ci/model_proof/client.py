"""One synthetic local-model request, inside the separately admitted CI worker.

This is a compatibility proof, not a native Run worker. It has no native receipt,
credentials, tool executor or authority. Its only network destination is fixed
loopback in the worker's private network namespace. The outer owner must prove
that namespace and own the server, resource limits and cleanup.
"""
from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time

SOURCE = Path('/input/model_connections.py')
SOURCE_SHA = '6f65a2d6c0dcb666c6ed621f914dc8392b01637d488f4a1c4d33fb043cdb5400'
OUTPUT = Path('/output/client')
PORT = 8088
MODEL = 'qwen3-0.6b-stead-compat1'
MAX_RESPONSE = 32768
SOURCE_UID = 65534  # Root outside the one-UID worker user namespace is unmapped.
EXPECTED_MARKDOWN = '# Team guide\n\nReview changes before accepting.\n'


def require(ok):
    if not ok:
        raise ValueError('Model compatibility proof refused')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def publish(name, raw, maximum):
    require(name in ('request.json', 'response.bin', 'proposal.json', 'report.json')
            and type(raw) is bytes and 0 < len(raw) <= maximum)
    fd = os.open(OUTPUT / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'sha256': sha(raw), 'bytes': len(raw)}


def timeout(_signum, _frame):
    raise TimeoutError('Model request deadline')


def post_once(body):
    """No retries, redirects, proxy, DNS hostname or dynamic destination."""
    require(type(body) is bytes and 0 < len(body) <= 8192)
    http.client._MAXLINE = 8192
    http.client._MAXHEADERS = 32
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=60)
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        connection.request('POST', '/v1/chat/completions', body=body,
                           headers={'Content-Type': 'application/json',
                                    'Accept': 'application/json',
                                    'Connection': 'close', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        require(response.status == 200)
        headers = response.getheaders()
        selected = {}
        for name, value in headers:
            name = name.lower()
            if name in ('content-length', 'transfer-encoding', 'content-type', 'content-encoding'):
                require(name not in selected)
                selected[name] = value.lower().strip()
        require(selected.get('content-type') in ('application/json', 'application/json; charset=utf-8')
                and selected.get('content-encoding', 'identity') == 'identity')
        require(not ('content-length' in selected and 'transfer-encoding' in selected))
        require(selected.get('transfer-encoding', 'chunked') == 'chunked')
        expected = None
        if 'content-length' in selected:
            raw_length = selected['content-length']
            require(raw_length.isascii() and raw_length.isdecimal() and len(raw_length) <= 6)
            expected = int(raw_length)
            require(0 < expected <= MAX_RESPONSE)
        raw = response.read(MAX_RESPONSE + 1)
        require(0 < len(raw) <= MAX_RESPONSE and (expected is None or len(raw) == expected))
        return raw
    finally:
        connection.close()
        signal.setitimer(signal.ITIMER_REAL, 0)


def uid(number):
    return '00000000-0000-7000-8000-' + str(number).zfill(12)


def main():
    require(os.getuid() == os.geteuid() == 1000 and len(sys.argv) == 1)
    info = SOURCE.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == SOURCE_UID and info.st_nlink == 1
            and not info.st_mode & 0o022 and info.st_size == 22885)
    require(sha(SOURCE.read_bytes()) == SOURCE_SHA)
    # The admitted owner binds an empty private output directory. Never reuse a
    # prior proof, infer native authority or manufacture a native-start receipt.
    OUTPUT.mkdir(mode=0o700)
    info = OUTPUT.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
            and stat.S_IMODE(info.st_mode) == 0o700)
    module_spec = importlib.util.spec_from_file_location('model_connections', SOURCE)
    model = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = model
    module_spec.loader.exec_module(model)
    started = time.monotonic()
    report = {'protocol': 'stead.synthetic-model-compatibility-proof/1', 'status': 'fail',
              'classification': 'actual-local-inference-with-synthetic-public-document',
              'model_adapter_sha256': SOURCE_SHA, 'model': MODEL, 'attempted_requests': 0,
              'completed_responses': 0, 'native_authority_supplied': False,
              'tool_executed': False, 'document_mutated': False, 'qualifies_g3': False,
              'artifacts': {}, 'error_class': 'none'}
    try:
        value = {'protocol': 'stead.model-connection/1', 'connection_id': uid(1),
                 'revision': '1', 'display_name': 'Isolated Qwen compatibility proof',
                 'adapter': 'llamacpp.chat-completions/1', 'model': MODEL,
                 'endpoint': {'url': 'http://127.0.0.1:8088/v1/chat/completions',
                     'placement': 'local-isolated',
                     'egress_policy_digest': sha(b'stead.synthetic-model-proof.loopback-only/1')},
                 'authentication': {'kind': 'none'},
                 'capabilities': {'instruction_role': 'system',
                     'function_tools': 'json-schema-strings/1', 'token_limit_field': 'max_tokens',
                     'strict_tools': 'unsupported', 'parallel_tool_calls': 'supported',
                     'store': 'unsupported'},
                 'limits': {'input_bytes': '8192', 'output_bytes': str(MAX_RESPONSE),
                     'turns': '1', 'tool_calls': '1', 'request_timeout_ms': '60000',
                     'duration_ms': '180000', 'input_tokens': '1536', 'output_tokens': '256',
                     'total_tokens': '1792', 'cost_units': '1', 'billable_micro_usd': '0'}}
        spec = model.connection(canonical(value))
        scope = {'home': '~zod', 'project_id': uid(2), 'run_id': uid(3), 'attempt': '1',
                 'effect_sequence': '1', 'definition_id': uid(4), 'definition_revision': '1',
                 'runtime_id': uid(5), 'runtime_revision': '1', 'connection_digest': spec.sha256,
                 'run_contract_sha256': sha(b'synthetic-contract'),
                 'context_digest': sha(b'# Team guide\n'),
                 'runtime_policy_digest': sha(b'synthetic-compatibility-no-authority')}
        registry = [{'tool_id': uid(6), 'revision': '1', 'name': 'propose_doc_update',
                     'description': 'Return a proposed Markdown document for human review. Does not save it.',
                     'arguments': {'markdown': '1024'}}]
        instructions = ('You propose document edits for a reviewer. Use the supplied '
                        'propose_doc_update function exactly once with the complete Markdown. '
                        'Do not claim that any document was saved or accepted.')
        messages = [{'role': 'user', 'content': 'Update the public test document. Call propose_doc_update '
                     'exactly once. Its markdown argument must equal the decoded JSON string below, '
                     'including its final newline. Preserve every character; do not trim whitespace. '
                     'JSON string: ' + json.dumps(EXPECTED_MARKDOWN, ensure_ascii=False)}]
        request = model.prepare_chat(spec, scope, '1', instructions, messages, registry)
        report['connection_digest'] = spec.sha256
        report['request_digest'] = request.request_digest
        report['artifacts']['request.json'] = publish('request.json', request.body, 8192)
        # The parent grants one synthetic inference, not a native effect. An
        # exception after this point stays uncertain and never causes a retry.
        report['attempted_requests'] = 1
        raw = post_once(request.body)
        report['completed_responses'] = 1
        report['artifacts']['response.bin'] = publish('response.bin', raw, MAX_RESPONSE)
        proposal = model.normalize_reply(spec, request, raw)
        report['artifacts']['proposal.json'] = publish('proposal.json', canonical(proposal), 65536)
        report['proposal_state'] = proposal['state']
        report['observed_usage'] = proposal['observed_usage']
        calls = proposal['tool_proposals']
        report['exact_document_proposed'] = (proposal['state'] == 'tool-proposals' and len(calls) == 1
            and calls[0]['name'] == 'propose_doc_update' and calls[0]['tool_id'] == uid(6)
            and calls[0]['revision'] == '1' and calls[0]['arguments'] == {'markdown': EXPECTED_MARKDOWN})
        require(report['exact_document_proposed'])
        report['status'] = 'pass'
    except BaseException as error:
        kind = type(error).__name__
        allowed = {'ValueError', 'TypeError', 'TimeoutError', 'OSError', 'ConnectionRefusedError',
                   'ConnectionResetError', 'BrokenPipeError', 'RemoteDisconnected', 'IncompleteRead',
                   'BadStatusLine', 'LineTooLong', 'HTTPException', 'PermissionError', 'FileExistsError'}
        report['error_class'] = kind if kind in allowed else 'unrecognized'
    finally:
        report['elapsed_ms'] = int((time.monotonic() - started) * 1000)
        publish('report.json', canonical(report), 16384)
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

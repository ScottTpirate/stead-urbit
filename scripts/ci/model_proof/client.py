"""One semantic Doc revision, inside the separately admitted local-model worker.

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

INPUT = Path('/input')
SOURCE_SHA = '6f65a2d6c0dcb666c6ed621f914dc8392b01637d488f4a1c4d33fb043cdb5400'
OUTPUT = Path('/output/client')
PORT = 8088
MODEL = 'qwen2.5-1.5b-stead-compat2'
MAX_RESPONSE = 32768
SUPPORT = {'model_connections.py': {'bytes': 22885, 'sha256': '6f65a2d6c0dcb666c6ed621f914dc8392b01637d488f4a1c4d33fb043cdb5400'}, 'model_doc_replacement.py': {'bytes': 4202, 'sha256': '4786f6782a7c76ebd11dcfc73259597215dd5dad8318d088fdb7f7263b85f619'}}
SOURCE_UID = 65534  # Root outside the one-UID worker user namespace is unmapped.
DOCUMENT_ID = '00000000-0000-7000-8000-000000000008'
HEADER = '---\nid: ' + DOCUMENT_ID + '\ntype: page\nstate: published\n---\n'
BEFORE_REVIEW = HEADER + '\n# Review schedule\n\n## Weekly review\n'
REVIEW_LINE = 'The review is on Monday at 10:00 in Room Cedar.\n'
AFTER_REVIEW = '\n## Contact\nAsk the document owner if you cannot attend.\n'
SOURCE_MARKDOWN = BEFORE_REVIEW + REVIEW_LINE + AFTER_REVIEW
TASK = ('Move the weekly review two weekdays later. Keep its time and room. '
        'Change only the weekday in the review sentence. Preserve the complete '
        'Stead header, document ID and every other character, including the final newline.')


def revision_context():
    """An existing synthetic Doc, with explicit scope and no repository context."""
    return {'project_id': uid(2), 'collection_id': uid(7), 'document_id': DOCUMENT_ID,
            'expected_revision': '1', 'base_markdown_sha256': sha(SOURCE_MARKDOWN.encode()),
            'markdown': SOURCE_MARKDOWN, 'task': TASK, 'repositories': []}


def target():
    context = revision_context()
    return {'kind': 'document', **{field: context[field] for field in
        ('project_id', 'collection_id', 'document_id', 'expected_revision', 'base_markdown_sha256')}}


def prepare_revision(model, replacement, spec, scope):
    context = revision_context()
    scope = dict(scope, context_digest=sha(canonical(context)))
    tool = replacement.replacement_tool(target(), '1024')
    instructions = ('Propose one edit for review by calling propose_doc_replacement exactly once. '
                    'Use old_text for the original weekday and new_text for the new weekday. '
                    'Only the reviewer can accept the edit.')
    messages = [{'role': 'user', 'content': 'Read the original document and follow its editing task. '
                 + canonical(context).decode()}]
    return model.prepare_chat(spec, scope, '1', instructions, messages, [tool])


def load_support(directory):
    modules = {}
    for filename, expected in SUPPORT.items():
        path = directory / filename
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid == SOURCE_UID and info.st_nlink == 1
                and not info.st_mode & 0o022 and info.st_size == expected['bytes'])
        raw = path.read_bytes()
        require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'])
        name = path.stem
        module_spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[name] = module
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        modules[name] = module
    return modules['model_connections'], modules['model_doc_replacement']


def assess_revision(markdown):
    """Compare original output bytes; never trim, normalize, append or repair them."""
    is_text = type(markdown) is str
    raw = markdown.encode('utf-8') if is_text else b''
    # The expected weekday is verifier-only. It is never included in the request.
    expected_line = REVIEW_LINE.replace('Monday', 'Wednesday')
    return {'document_id': DOCUMENT_ID, 'base_markdown_sha256': sha(SOURCE_MARKDOWN.encode()),
            'output_markdown_sha256': sha(raw), 'output_markdown_bytes': len(raw),
            'canonical_header_preserved': is_text and markdown.startswith(HEADER),
            'untouched_material_preserved': is_text and markdown.startswith(BEFORE_REVIEW)
                and markdown.endswith(AFTER_REVIEW),
            'requested_semantic_edit': is_text and markdown == BEFORE_REVIEW + expected_line + AFTER_REVIEW,
            'changed_from_original': is_text and markdown != SOURCE_MARKDOWN,
            'final_newline_preserved': is_text and markdown.endswith('\n')}


def accepted_revision(checks):
    return all(checks[key] is True for key in ('canonical_header_preserved',
        'untouched_material_preserved', 'requested_semantic_edit',
        'changed_from_original', 'final_newline_preserved'))


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


def connection_and_scope(model):
    value = {'protocol': 'stead.model-connection/1', 'connection_id': uid(1),
             'revision': '2', 'display_name': 'Isolated Qwen Doc replacement',
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
             'context_digest': sha(canonical(revision_context())),
             'runtime_policy_digest': sha(b'synthetic-compatibility-no-authority')}
    return spec, scope


def main():
    require(os.getuid() == os.geteuid() == 1000 and len(sys.argv) == 1)
    model, replacement = load_support(INPUT)
    # The admitted owner binds an empty private output directory. Never reuse a
    # prior proof, infer native authority or manufacture a native-start receipt.
    OUTPUT.mkdir(mode=0o700)
    info = OUTPUT.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
            and stat.S_IMODE(info.st_mode) == 0o700)
    started = time.monotonic()
    report = {'protocol': 'stead.synthetic-model-doc-replacement/1', 'status': 'fail',
              'classification': 'actual-local-inference-with-synthetic-public-document',
              'model_adapter_sha256': SOURCE_SHA, 'model': MODEL, 'attempted_requests': 0,
              'completed_responses': 0, 'native_authority_supplied': False,
              'external_tool_executed': False, 'document_mutated': False, 'qualifies_g3': False,
              'artifacts': {}, 'error_class': 'none'}
    try:
        spec, scope = connection_and_scope(model)
        request = prepare_revision(model, replacement, spec, scope)
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
        proposed = replacement.materialize(spec, request, proposal, target(), SOURCE_MARKDOWN, '1024')
        report['review_document'] = proposed
        report['revision_checks'] = assess_revision(proposed['markdown'])
        report['semantic_edit_proposed'] = accepted_revision(report['revision_checks'])
        require(report['semantic_edit_proposed'])
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

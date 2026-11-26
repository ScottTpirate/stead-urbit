"""Prepare a single Doc replacement for review from an untrusted model proposal."""
import hashlib

import model_connections as model

TOOL_ID = '019cb890-1fce-77ba-9120-539758b72f89'
TOOL_NAME = 'propose_doc_replacement'
MAX_FRAGMENT = 2048
MAX_MARKDOWN = 32768
TARGET_FIELDS = {'kind', 'project_id', 'collection_id', 'document_id', 'expected_revision', 'base_markdown_sha256'}


def replacement_tool(target, max_output_bytes):
    """Register only for one currently authorized existing Doc and one output budget."""
    model.closed(target, TARGET_FIELDS)
    model.require(target['kind'] == 'document', 'existing_doc_required')
    for field in ('project_id', 'collection_id', 'document_id'):
        model.uuid(target[field])
    model.uint(target['expected_revision'], positive=True)
    model.digest(target['base_markdown_sha256'])
    model.uint(max_output_bytes, MAX_MARKDOWN, positive=True)
    pin = model.domain_hash('stead.doc-replacement-target/1', model.canonical({
        'target': target, 'max_output_bytes': max_output_bytes}))
    return {'name': TOOL_NAME, 'tool_id': TOOL_ID, 'revision': '1',
            'description': 'Propose one literal text replacement in the selected Doc body for review. '
                           'old_text must occur exactly once. Keep all other text. Doc pin ' + pin,
            'arguments': {'old_text': str(MAX_FRAGMENT), 'new_text': str(MAX_FRAGMENT)}}


def materialize(spec, request, proposal, target, base_markdown, max_output_bytes):
    """Return full proposed Markdown for a pinned target, without submitting or saving it."""
    model.validate_request(spec, request)
    tool = replacement_tool(target, max_output_bytes)
    registry = model.decode(request.tool_registry, 32768)
    scope = model.decode(request.scope, 8192)
    model.require(scope['project_id'] == target['project_id'] and tool in registry,
                  'doc_target_or_budget_changed')
    model.require(type(proposal) is dict and proposal.get('request_digest') == request.request_digest
                  and proposal.get('authority') == 'untrusted-proposal'
                  and proposal.get('state') == 'tool-proposals', 'doc_reply_not_actionable')
    calls = proposal.get('tool_proposals')
    model.require(type(calls) is list and len(calls) == 1, 'one_doc_replacement_required')
    call = model.closed(calls[0], {'provider_call_id', 'tool_id', 'revision', 'name', 'arguments'})
    model.require(all(call[field] == tool[field] for field in ('tool_id', 'revision', 'name')),
                  'incorrect_doc_tool')
    args = model.closed(call['arguments'], tool['arguments'])
    old = model.text(args['old_text'], MAX_FRAGMENT, nonempty=True)
    new = model.text(args['new_text'], MAX_FRAGMENT)
    model.require(old != new and '\r' not in old and '\r' not in new, 'invalid_doc_replacement')
    model.text(base_markdown, MAX_MARKDOWN, nonempty=True)
    model.require('\r' not in base_markdown and hashlib.sha256(base_markdown.encode()).hexdigest() == target['base_markdown_sha256'],
                  'doc_base_changed')
    header = f"---\nid: {target['document_id']}\ntype: page\nstate: published\n---\n"
    model.require(base_markdown.startswith(header), 'invalid_doc_header')
    body = base_markdown[len(header):]
    first = body.find(old)
    # Advancing by one detects overlapping occurrences as well (e.g. "aa" in "aaa").
    model.require(first >= 0 and body.find(old, first + 1) < 0, 'doc_match_missing_or_ambiguous')
    revised = header + body[:first] + new + body[first + len(old):]
    trailing_lfs = len(base_markdown) - len(base_markdown.rstrip('\n'))
    model.require(len(revised) - len(revised.rstrip('\n')) == trailing_lfs, 'doc_final_newline_changed')
    model.require(len(revised.encode()) <= int(max_output_bytes), 'doc_output_byte_bound')
    return {'target': dict(target), 'markdown': revised}


def recover(journal, result_sha256, target, base_markdown, max_output_bytes):
    """Recover and materialize the proposal bound to the retained terminal journal receipt."""
    proposal = journal.read_proposal(result_sha256)
    return materialize(journal.spec, journal.request, proposal, target, base_markdown, max_output_bytes)

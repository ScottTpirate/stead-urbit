"""Independent v2 execution/assertion layer; original v1 executor is preserved.

This module owns no ship, lifecycle, Git process, authentication or native state.
The caller supplies callbacks and must identify whether they are real or mocked.

call(ship, mode, route='/', raw=b'') -> {'raw': str|None, 'json': dict|None,
                                       'native': evidence}
snapshot() -> native owner snapshot, either flat counts or {'counts': {...}};
              requires state_jam_sha256/state_sha256, journal/receipts/object counts.
restart() -> lifecycle evidence. export(ship, project, container, snapshot=None)
returns raw object/file hex, snapshot_commit_oid and actual fsck argv/returncode.
object_matrix(case, captures) -> {'variants': [{'name': str, 'response': call-result}]}.
trusted_now_ms() -> current native trusted time; wait_until(deadline_ms) -> evidence
including now_ms and elapsed_seconds. Neither callback may fabricate/modify time.

Missing callbacks/assertion evidence produce incomplete results, never green skips.
No native execution happens on import. The codec/delivery/migration suites remain
separately owned; this module does not claim their qualification.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
import re
import time

import delivery_cases


HEX64 = re.compile(r'[0-9a-f]{64}')
OID = re.compile(r'[0-9a-f]{40}')
UINT = re.compile(r'0|[1-9][0-9]*')
FILE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.md')
DENIAL = {'protocol': 'stead.result/2', 'status': 'rejected', 'error': 'denied_or_not_found'}
BINDINGS = {'zod': '019939ba-4000-7000-8000-000000000201',
            'bus': '019939ba-4000-7000-8000-000000000202',
            'nec': '019939ba-4000-7000-8000-000000000203',
            'bud': '019939ba-4000-7000-8000-000000000204'}
COUNT_ALIASES = {'journal': 'journal_events', 'works': 'work_items'}


def revision_key(cmd):
    operation, project, resource = cmd['operation'], cmd['project_id'], cmd['resource_id']
    if operation.startswith('policy.'):
        return 'policy/' + project
    if operation == 'project.create':
        return 'project/' + project
    if operation == 'document.save':
        return f"document/{project}/{cmd['payload']['container_id']}/{resource}"
    return f'work/{project}/{resource}'


def canonical(command):
    """Serialize already validated recipe commands using the frozen JSON profile.

    This is not a second schema validator. The import-independent stdlib settings
    are tested against the six frozen byte vectors because /code has no repo root.
    """
    return json.dumps(command, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def command_digest(raw):
    return hashlib.sha256(b'stead.command/2\0' + raw).hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate response key')
        out[key] = value
    return out


def uint(value):
    if type(value) is int and 0 <= value <= 2**64 - 1:
        return value
    if isinstance(value, str) and UINT.fullmatch(value):
        result = int(value)
        if result <= 2**64 - 1:
            return result
    raise ValueError('Expected nonnegative integer or canonical decimal string')


class CaseFailure(Exception):
    pass


class Runner:
    def __init__(self, corpus, call, snapshot, restart=None, export=None, object_matrix=None,
                 *, trusted_now_ms=None, wait_until=None, classification='adapter-driven-unqualified',
                 include_second_project=False, include_scoped_privacy=False, encode=canonical,
                 review_evidence=None, delivery_evidence=None, defer_phase1_reviews=False):
        self.corpus = copy.deepcopy(corpus)
        self.commands = copy.deepcopy(corpus['commands'])
        self.call, self.snapshot = call, snapshot
        self.restart, self.export, self.object_matrix = restart, export, object_matrix
        self.trusted_now_ms, self.wait_until, self.encode = trusted_now_ms, wait_until, encode
        self.include_second_project = include_second_project
        self.include_scoped_privacy = include_scoped_privacy
        self.review_evidence = review_evidence or {}
        self.delivery_evidence = delivery_evidence
        self.defer_phase1_reviews = defer_phase1_reviews
        self.delivery_occurrences = Counter()
        self.captures, self.heads, self.views = {}, {}, {}
        self.short_expiry = None
        self.current = None
        self.report = {'status': 'incomplete', 'classification': classification,
                       'test_owner': '/root/qa_review', 'cases': [],
                       'scope': ['ordered_cases', 'real_expiry_continuation', 'source_review_continuation'],
                       'not_qualified_here': ['native codec corpus', 'delivery-order suite',
                                              'trusted-context controls', 'migration suite',
                                              'synthetic object-collision fixtures', 'full confidentiality'],
                       'checks': [], 'calls': [], 'snapshots': []}

    def check(self, name, condition, detail=None):
        item = {'case': self.current['name'], 'name': name, 'status': 'passed' if condition else 'failed'}
        if detail is not None:
            item['detail'] = detail
        self.current['checks'].append(item)
        self.report['checks'].append(item)
        if not condition:
            raise CaseFailure(name)

    def skip(self, name, reason):
        item = {'case': self.current['name'], 'name': name, 'status': 'skipped', 'reason': reason}
        self.current['checks'].append(item)
        self.report['checks'].append(item)

    def snap(self):
        result = copy.deepcopy(self.snapshot())
        if not isinstance(result, dict):
            raise ValueError('Snapshot adapter must return a JSON object')
        state_hash = result.get('state_sha256', result.get('state_jam_sha256'))
        self.check('snapshot-business-hash-present', isinstance(state_hash, str) and bool(HEX64.fullmatch(state_hash)))
        source = result.get('counts', result)
        counts = {}
        for name in ('journal', 'receipts', 'objects', 'object_bytes', 'projects', 'works', 'documents', 'grants'):
            value = source.get(name, source.get(COUNT_ALIASES.get(name, name)))
            if value is not None:
                counts[name] = uint(value)
        self.check('snapshot-required-counts-present', all(k in counts for k in ('journal', 'receipts', 'objects', 'object_bytes')))
        result['_hash'], result['_counts'] = state_hash, counts
        self.report['snapshots'].append(result)
        return result

    def unchanged(self, before, after):
        self.check('no-business-change', before['_hash'] == after['_hash'] and before['_counts'] == after['_counts'])

    def invoke(self, ship, mode, route='/', raw=b''):
        result = copy.deepcopy(self.call(ship, mode, route=route, raw=raw))
        self.report['calls'].append({'case': self.current['name'], 'ship': ship, 'mode': mode,
                                     'route': route, 'request_sha256': hashlib.sha256(raw).hexdigest(),
                                     'response': result})
        self.check('native-result-present', isinstance(result, dict) and isinstance(result.get('raw'), str)
                   and isinstance(result.get('json'), dict), 'ACK, NACK or missing result alone is not a business outcome')
        self.check('response-byte-bound', 0 < len(result['raw'].encode('utf-8')) <= 262144)
        decoded = json.loads(result['raw'], object_pairs_hook=unique)
        self.check('raw-json-equals-adapter-json', decoded == result['json'])
        self.check('native-evidence-present', 'native' in result and result['native'] is not None)
        if mode == 'read':
            self.delivery(result, ship=ship, route=route)
        return result

    def denial(self, result, expected):
        error = expected.get('error', 'denied_or_not_found')
        if error == 'denied_or_not_found':
            self.check('exact-opaque-denial', result['json'] == DENIAL)
        else:
            self.check('exact-authorized-error', result['json'] == {'protocol': 'stead.result/2',
                        'status': 'rejected', 'error': error})

    def review(self, identifier, historical_name):
        """Preserve a missing historical assertion until typed evidence exists.

        qualification_gate independently validates source/artifact bindings.
        This layer accepts only its verified item output, never reviewer prose
        or a blanket boolean. Source and N/A remain distinct check statuses.
        """
        evidence = self.review_evidence.get(identifier)
        if not isinstance(evidence, dict) or evidence.get('verified_by') != 'stead.qualification-gate/2':
            self.skip(historical_name, 'Required typed current evidence missing: ' + identifier)
            return
        kind = evidence.get('kind')
        status = {'source_review': 'reviewed', 'not_applicable': 'not_applicable', 'native': 'passed'}.get(kind)
        self.check('typed-review-evidence:' + identifier,
                   status is not None and evidence.get('status') == status
                   and bool(evidence.get('artifact')) and bool(evidence.get('bindings')))
        item = {'case': self.current['name'], 'name': historical_name, 'status': status,
                'evidence_id': identifier, 'kind': kind,
                'scope': evidence.get('scope'), 'historical_status': 'skipped'}
        self.current['checks'].append(item)
        self.report['checks'].append(item)

    def delivery(self, result, *, ship=None, route=None):
        native = result.get('native')
        evidence = native.get('delivery') if isinstance(native, dict) else None
        if evidence is None and self.delivery_evidence is not None:
            evidence = self.delivery_evidence(self.current['name'], ship, route, copy.deepcopy(result))
        if evidence is None:
            self.skip('one-shot-request-duct-only', 'Required actual native fact/kick/foreign-sentinel evidence missing')
            return
        proof = delivery_cases.verify_one_shot(evidence, result['raw'], ship=ship, route=route)
        self.current.setdefault('delivery_observations', []).append(copy.deepcopy(evidence))
        self.check('one-shot-request-duct-only', proof['status'] == 'passed', proof)

    def read_expected(self, result, path, expected):
        if expected.get('result') == 'rejected':
            self.denial(result, expected)
            return
        if expected.get('result') == 'accepted':
            old = self.captures[expected['receipt_equal_to']]['response']
            self.check('recovered-original-public-receipt', result['raw'] == old['raw'] and result['json'] == old['json'])
            return
        obj = result['json']
        parts = path.strip('/').split('/')
        self.check('read-envelope', set(obj) == {'protocol', 'status', 'project_id', 'resource_id', 'resource_revision', 'payload'}
                   and obj['protocol'] == 'stead.result/2' and obj['status'] == 'read')
        self.check('read-target', obj['project_id'] == parts[2] and obj['resource_id'] == (parts[4] if parts[1] == 'document' else parts[3] if len(parts) > 3 else parts[2]))
        if parts[1] == 'document':
            self.check('read-container-scope', obj['payload'].get('container_id') == parts[3])
        if 'resource_revision' in expected:
            self.check('read-revision', obj['resource_revision'] == expected['resource_revision'])
        if 'payload_equal_to' in expected:
            ref = expected['payload_equal_to'].removesuffix('.payload')
            self.check('read-exact-payload', obj['payload'] == self.commands[ref]['payload'])
        if 'markdown_equal_to' in expected:
            ref = expected['markdown_equal_to'].removesuffix('.payload.markdown')
            self.check('read-exact-markdown', obj['payload'].get('markdown') == self.commands[ref]['payload']['markdown'])
        if 'response_equal_to' in expected:
            old = self.captures[expected['response_equal_to']]['responses'][0]
            self.check('no-observable-private-activity-delta', result['raw'] == old['raw'] and result['json'] == old['json'])

    def receipt(self, result, cmd, expected, ship):
        if 'receipt_equal_to' in expected:
            old = self.captures[expected['receipt_equal_to']]['response']
            self.check('original-receipt-bytes-and-fields', result['raw'] == old['raw'] and result['json'] == old['json'])
            return
        obj = result['json']
        fields = {'protocol': 'stead.receipt/2', 'status': 'accepted', 'request_id': cmd['request_id'],
                  'canonical_sha256': command_digest(self.encode(cmd)), 'project_id': cmd['project_id'],
                  'resource_id': cmd['resource_id'], 'principal_id': self.corpus['principals'][ship],
                  'binding_id': BINDINGS[ship], 'authentication': 'fake-native/1',
                  'authentication_strength': 'synthetic-native-sender',
                  'resource_revision': expected['resource_revision'], 'authority_epoch': expected['authority_epoch'],
                  'resource_kind': ('policy' if cmd['operation'].startswith('policy.') else cmd['operation'].split('.')[0]),
                  'container_id': cmd['payload']['container_id'] if cmd['operation'] == 'document.save' else ''}
        self.check('accepted-receipt-fields', all(obj.get(k) == v for k, v in fields.items()))
        self.check('accepted-receipt-closed-envelope', set(obj) == set(fields) | {'accepted_at_ms', 'git_commit_oid'})
        self.check('accepted-time-is-decimal', isinstance(obj['accepted_at_ms'], str) and bool(UINT.fullmatch(obj['accepted_at_ms'])))
        git = obj['git_commit_oid']
        self.check('receipt-git-oid', bool(OID.fullmatch(git)) if cmd['operation'] == 'document.save' else git == '')
        self.check('canonical-receipt-bytes', result['raw'].encode() == canonical(obj))
        if cmd['operation'] == 'policy.grant':
            self.check('grant-future-at-acceptance', uint(cmd['payload']['expires_at_ms']) > uint(obj['accepted_at_ms']))

    def atomic(self, before, after, cmd, result, expected):
        self.check('accepted-state-changed', before['_hash'] != after['_hash'])
        delta = {k: after['_counts'][k] - value for k, value in before['_counts'].items()}
        self.check('one-journal-and-receipt', delta['journal'] == 1 and delta['receipts'] == 1)
        if 'now_ms' in before and 'now_ms' in after:
            self.check('acceptance-time-within-authority-observations',
                       uint(before['now_ms']) <= uint(result['json']['accepted_at_ms']) <= uint(after['now_ms']))
        else:
            self.skip('acceptance-time-authority-window', 'Snapshot has no trusted native time observations')
        op = cmd['operation']
        for count, operation in (('projects', 'project.create'), ('works', 'work.create'), ('grants', 'policy.grant')):
            if count in delta:
                amount = int(op == operation or (count == 'grants' and op == 'project.create'))
                self.check(count + '-count-delta', delta[count] == amount)
        if 'documents' in delta:
            self.check('document-count-delta', delta['documents'] == int(op == 'document.save' and cmd['expected_revision'] == '0'))
        if op != 'document.save':
            self.check('nongit-mutation-preserves-object-store', delta['objects'] == 0 and delta['object_bytes'] == 0)
        elif 'git_object_count_delta' in expected:
            self.check('document-object-admission-count', delta['objects'] == expected['git_object_count_delta'] and delta['object_bytes'] > 0)
        record = after.get('last_journal_record')
        if record is None:
            self.skip('journal-content-and-chain', 'Snapshot lacks exact last_journal_record bytes')
        else:
            parsed = json.loads(record, object_pairs_hook=unique)
            self.check('canonical-journal-record', canonical(parsed).decode() == record)
            digest = hashlib.sha256(b'stead.journal/1\0' + record.encode()).hexdigest()
            self.check('private-owner-journal-hash', digest == after['last_journal_digest'])
            wanted = {'protocol': 'stead.journal/1', 'sequence': expected['journal_sequence'],
                      'previous_digest': self.heads.get(cmd['project_id'], '0' * 64),
                      'canonical_command': self.encode(cmd).decode(), 'old_revision': cmd['expected_revision'],
                      'new_revision': expected['resource_revision'], 'principal_id': result['json']['principal_id'],
                      'binding_id': result['json']['binding_id'], 'policy_revision': expected['decision_policy_revision'],
                      'authority_epoch': cmd['authority_epoch'], 'accepted_at_ms': result['json']['accepted_at_ms'],
                      'git_commit_oid': result['json']['git_commit_oid'], 'authentication': 'fake-native/1',
                      'authentication_strength': 'synthetic-native-sender'}
            self.check('journal-exact-context-and-project-chain', parsed == wanted)
        self.heads[cmd['project_id']] = after.get('last_journal_digest')
        if 'revisions' not in before or 'revisions' not in after:
            self.skip('all-unrelated-resource-revisions-unchanged', 'Snapshot lacks full revision map; explicit cross-resource cases still execute')
        else:
            target = revision_key(cmd)
            self.check('accepted-target-native-revision', after['revisions'].get(target) == expected['resource_revision'])
            for key, old in before['revisions'].items():
                if key != target and not (op == 'project.create' and key == 'policy/' + cmd['project_id']):
                    self.check('unrelated-revision:' + key, after['revisions'].get(key) == old)

    def materialized(self, evidence, refs, expected_head=None, expected_parent=None, parent_known=False):
        self.check('export-object-evidence', isinstance(evidence, dict) and isinstance(evidence.get('objects'), dict) and bool(evidence['objects']))
        head = evidence['snapshot_commit_oid']
        self.check('export-head-format', isinstance(head, str) and bool(OID.fullmatch(head)))
        if expected_head is not None:
            self.check('export-head-equals-receipt', head == expected_head)
        bodies = {}
        for oid, obj in evidence['objects'].items():
            raw = bytes.fromhex(obj['hex'])
            self.check('object-length:' + oid, len(raw) == uint(obj['byte_length']))
            self.check('object-sha1:' + oid, obj['kind'] in ('blob', 'tree', 'commit') and
                       hashlib.sha1(f"{obj['kind']} {len(raw)}\0".encode() + raw).hexdigest() == oid)
            bodies[oid] = raw
        self.check('head-is-materialized-commit', head in bodies and evidence['objects'][head]['kind'] == 'commit')
        headers = bodies[head].split(b'\n\n', 1)[0].decode('ascii').splitlines()
        parents = [line[7:] for line in headers if line.startswith('parent ')]
        if parent_known:
            self.check('native-container-commit-parent', parents == ([] if expected_parent is None else [expected_parent]))
        self.check('single-parent-native-subset', len(parents) <= 1)
        trees = [line[5:] for line in headers if line.startswith('tree ')]
        self.check('one-materialized-tree', len(trees) == 1 and trees[0] in bodies and evidence['objects'][trees[0]]['kind'] == 'tree')
        remaining, tree_files, names = bodies[trees[0]], {}, []
        while remaining:
            entry, remaining = remaining.split(b'\0', 1)
            mode, name = entry.split(b' ', 1)
            self.check('flat-regular-git-tree-entry', mode == b'100644' and bool(FILE.fullmatch(name.decode('ascii'))) and len(remaining) >= 20)
            oid, remaining = remaining[:20].hex(), remaining[20:]
            self.check('tree-entry-is-materialized-blob', oid in bodies and evidence['objects'][oid]['kind'] == 'blob')
            names.append(name)
            tree_files[name.decode()] = {'oid': oid, 'hex': bodies[oid].hex()}
        self.check('git-tree-byte-order-and-unique-names', names == sorted(names) and len(names) == len(set(names)))
        self.check('stock-git-files-match-native-tree', evidence['files'] == tree_files)
        pending, reachable = [(head, 'commit')], set()
        while pending:
            oid, kind = pending.pop()
            self.check('reachable-object-kind:' + oid, oid in bodies and evidence['objects'][oid]['kind'] == kind)
            if oid in reachable:
                continue
            reachable.add(oid)
            body = bodies[oid]
            if kind == 'commit':
                lines = body.split(b'\n\n', 1)[0].decode('ascii').splitlines()
                tree = [line[5:] for line in lines if line.startswith('tree ')]
                parent = [line[7:] for line in lines if line.startswith('parent ')]
                self.check('reachable-commit-shape:' + oid, len(tree) == 1 and len(parent) <= 1)
                pending.extend((value, 'commit') for value in parent)
                pending.extend((value, 'tree') for value in tree)
            elif kind == 'tree':
                ordered = []
                while body:
                    header, body = body.split(b'\0', 1)
                    mode, name = header.split(b' ', 1)
                    self.check('reachable-tree-entry:' + oid, mode == b'100644' and bool(FILE.fullmatch(name.decode('ascii'))) and len(body) >= 20)
                    ordered.append(name)
                    pending.append((body[:20].hex(), 'blob'))
                    body = body[20:]
                self.check('reachable-tree-order:' + oid, ordered == sorted(ordered) and len(ordered) == len(set(ordered)))
        self.check('no-unreachable-or-other-container-export-objects', set(bodies) == reachable)
        if refs is not None:
            wanted = {self.commands[ref]['resource_id'] + '.md': self.commands[ref]['payload']['markdown'].encode().hex() for ref in refs}
            self.check('exact-authorized-markdown-file-set', {name: value['hex'] for name, value in tree_files.items()} == wanted)
        fsck = evidence.get('fsck', {})
        argv = fsck.get('argv', [])
        self.check('actual-stock-git-fsck-full-strict', bool(argv) and argv[0].split('/')[-1] == 'git'
                   and argv[-3:] == ['fsck', '--full', '--strict'] and fsck.get('returncode') == 0)
        self.check('all-export-responses-bounded', 0 < uint(evidence['max_response_bytes']) <= 262144)
        self.check('export-native-evidence-present', bool(evidence.get('native')))

    def after_save(self, cmd, expected, result):
        if self.export is None:
            self.skip('native-git-content-and-parent', 'Export adapter unavailable')
            return None
        evidence = self.export(self.current['action']['sender'], cmd['project_id'], cmd['payload']['container_id'])
        parent = None
        if 'container_commit_parent_from' in expected:
            parent = self.captures[expected['container_commit_parent_from']]['response']['json']['git_commit_oid']
        self.materialized(evidence, expected.get('reachable_file_refs'), result['json']['git_commit_oid'], parent,
                          'container_commit_parent' in expected or 'container_commit_parent_from' in expected)
        commit = bytes.fromhex(evidence['objects'][evidence['snapshot_commit_oid']]['hex'])
        headers, message = commit.split(b'\n\n', 1)
        identity = f"Stead Fixture <{result['json']['principal_id']}@stead.invalid> {uint(result['json']['accepted_at_ms']) // 1000} +0000"
        self.check('git-author-and-committer-match-native-principal',
                   f'author {identity}'.encode() in headers.splitlines()
                   and f'committer {identity}'.encode() in headers.splitlines())
        self.check('git-message-matches-accepted-document',
                   message == f"Save {cmd['resource_id']} revision {expected['resource_revision']}\n".encode())
        return evidence

    def execute(self, case):
        action, expected = case['action'], case['expected']
        before = self.snap()
        kind = action['kind']
        saved = {}
        if kind == 'mutation':
            cmd = copy.deepcopy(self.commands[action['command_ref']])
            if action.get('late_bind'):
                now = uint(self.trusted_now_ms())
                self.short_expiry = now + 120000
                self.check('short-grant-within-fixture-binding', self.short_expiry <= 4102444800000)
                cmd['payload']['expires_at_ms'] = str(self.short_expiry)
                self.commands[action['command_ref']] = copy.deepcopy(cmd)
            raw = self.encode(cmd)
            route = f"/v2/result/~{action['sender']}/{BINDINGS[action['sender']]}/{cmd['project_id']}/{cmd['request_id']}/{command_digest(raw)}"
            result = self.invoke(action['sender'], 'command', route, raw)
            saved = {'response': result, 'command': cmd}
            if expected['result'] == 'rejected':
                self.denial(result, expected)
            else:
                self.receipt(result, cmd, expected, action['sender'])
                if 'receipt_equal_to' not in expected:
                    after = self.snap()
                    self.atomic(before, after, cmd, result, expected)
                    if action.get('late_bind'):
                        self.check('short-grant-acceptance-window', self.short_expiry - uint(result['json']['accepted_at_ms']) >= 60000)
                    if case['name'] == 'accept-work-before-expiry':
                        self.check('work-accepted-before-real-expiry', self.short_expiry is not None and uint(result['json']['accepted_at_ms']) < self.short_expiry)
                    if cmd['operation'] == 'document.save':
                        saved['export'] = self.after_save(cmd, expected, result)
                        self.unchanged(after, self.snap())
                    self.views[revision_key(cmd)] = {
                        'command': cmd, 'response': result, 'sender': action['sender']}
                    self.captures[case['name']] = saved
                    return
        elif kind in ('read', 'read_pair'):
            paths = [action['path']] if kind == 'read' else action['paths']
            results = []
            for path in paths:
                response = self.invoke(action['sender'], 'read', path)
                self.read_expected(response, path, expected if kind == 'read' else expected['each'])
                results.append(response)
            if kind == 'read_pair':
                self.check('known-unknown-response-byte-equality', len(results) == 2 and results[0]['raw'] == results[1]['raw'])
            saved = {'responses': results}
        elif kind == 'read_matrix':
            for ship in action['senders']:
                for path in action['paths']:
                    result = self.invoke(ship, 'read', path)
                    if ship == 'bud':
                        self.denial(result, {'error': 'denied_or_not_found'})
                        continue
                    self.read_expected(result, path, {})
                    payload = result['json']['payload']
                    if '/project/' in path:
                        wanted = dict(self.commands['project_create']['payload'])
                        revision = '1'
                    else:
                        wanted = self.commands['work_a_update_2']['payload']
                        revision = '3'
                    self.check('exact-public-projection-no-private-metadata', payload == wanted and result['json']['resource_revision'] == revision)
            self.review('scoped-private-metadata', 'projection-timing-and-all-metadata-nondisclosure')
        elif kind in ('export', 'export_snapshot'):
            if self.export is None:
                self.skip('git-export-exact-objects', 'Export adapter unavailable')
            else:
                snapshot = None
                if kind == 'export':
                    _, _, _, project, container = action['manifest_path'].split('/')
                else:
                    source = self.captures[action['snapshot_from']]
                    project, container = source['command']['project_id'], source['command']['payload']['container_id']
                    snapshot = source['response']['json']['git_commit_oid']
                evidence = self.export(action['sender'], project, container, snapshot=snapshot)
                refs = expected.get('accepted_file_refs')
                self.materialized(evidence, refs, snapshot)
                if 'equal_to' in expected:
                    previous = self.captures[expected['equal_to']]['export']
                    self.check('export-exact-bytes-after-restart', all(evidence[k] == previous[k] for k in ('snapshot_commit_oid', 'objects', 'files')))
                saved['export'] = evidence
        elif kind == 'object_read_matrix':
            if self.object_matrix is None:
                self.skip('object-read-matrix', 'Object matrix adapter unavailable')
            else:
                evidence = self.object_matrix(case, copy.deepcopy(self.captures))
                variants = evidence['variants']
                self.check('all-object-variants-returned', [v['name'] for v in variants] == action['variants'])
                objects = self.captures[action['base_manifest_from']]['export']['objects']
                for index, variant in enumerate(variants):
                    result = variant['response']
                    self.check('matrix-raw-json-consistent', json.loads(result['raw'], object_pairs_hook=unique) == result['json'])
                    self.check('matrix-response-bound', 0 < len(result['raw'].encode()) <= 262144)
                    if index:
                        self.denial(result, expected['all_other_variants'])
                    else:
                        payload = result['json'].get('payload', {})
                        obj = objects.get(payload.get('oid'))
                        self.check('authorized-object-exact-native-bytes', result['json'].get('status') == 'read' and obj is not None
                                   and payload.get('hex') == obj['hex'] and payload.get('kind') == obj['kind']
                                   and uint(payload['byte_length']) == uint(obj['byte_length']))
                    self.delivery(result)
                saved['matrix'] = evidence
        elif kind == 'warm_home_restart':
            if self.restart is None:
                self.skip('saved-state-round-trip', 'Restart callback unavailable; no restart was executed')
            else:
                evidence = self.restart()
                saved['restart'] = evidence
                self.check('restart-adapter-evidence-present', evidence is not None)
                if isinstance(evidence, dict) and all(k in evidence for k in ('old_pid', 'old_exit', 'replacement_pid')):
                    self.check('graceful-stop-and-distinct-replacement', evidence['old_exit'] == 0
                               and uint(evidence['old_pid']) > 0 and uint(evidence['replacement_pid']) > 0
                               and evidence['old_pid'] != evidence['replacement_pid'])
                else:
                    self.skip('graceful-stop-and-distinct-replacement', 'Lifecycle adapter lacks old/replacement PID and exit evidence')
                # Fresh authenticated reads prove the retained business revisions;
                # these expected values came from the corpus, not the response.
                project = self.corpus['fixture_ids']['project']
                project_view = self.invoke('bus', 'read', f'/v2/project/{project}')
                self.read_expected(project_view, f'/v2/project/{project}', {'resource_revision': expected['project_content_revision']})
                self.check('restored-private-policy-revision', self.snap()['revisions'].get('policy/' + project) == expected['policy_revision'])
                self.check('no-public-policy-counter', 'policy_revision' not in project_view['json']['payload'])
                for scope, field in (('work', 'work_revisions'), ('document', 'document_revisions')):
                    for resource, revision in expected[field].items():
                        previous = self.views[f'{scope}/{project}/{resource}']
                        route = f'/v2/{scope}/{project}/{resource}'
                        response = self.invoke(previous['sender'], 'read', route)
                        self.read_expected(response, route, {'resource_revision': revision})
                        if scope == 'work':
                            self.check('restored-work-content:' + resource, response['json']['payload'] == previous['command']['payload'])
                        else:
                            self.check('restored-document-content:' + resource,
                                       response['json']['payload'].get('markdown') == previous['command']['payload']['markdown']
                                       and response['json']['payload'].get('git_commit_oid') == previous['response']['json']['git_commit_oid'])
                self.review('no-effect-subsystem', 'no-external-effects-replayed')
        elif kind == 'wait_until':
            self.check('recorded-expiry-exists', self.short_expiry is not None)
            evidence = self.wait_until(self.short_expiry)
            self.check('real-authority-expiry-observed', isinstance(evidence, dict) and uint(evidence['now_ms']) >= self.short_expiry
                       and type(evidence.get('elapsed_seconds')) in (int, float) and evidence['elapsed_seconds'] >= 0)
            self.check('fresh-trusted-expiry-observation', uint(self.trusted_now_ms()) >= self.short_expiry)
            saved['expiry_observation'] = evidence
        else:
            self.skip('case-action', 'Unsupported action kind: ' + kind)
        after = self.snap()
        self.unchanged(before, after)
        self.captures[case['name']] = saved

    def run(self):
        started = time.monotonic()
        lanes = [('ordered_cases', self.corpus['ordered_cases'], None)]
        expiry_ready = self.trusted_now_ms is not None and self.wait_until is not None
        reason = None if expiry_ready else 'Real trusted-time/wait adapters missing; mutation continuation is not started'
        for name in ('real_expiry_continuation', 'source_review_continuation'):
            if name in self.corpus:
                lanes.append((name, self.corpus[name]['cases'], reason))
        if self.include_second_project and 'separate_project_journal_lane' in self.corpus:
            self.report['scope'].append('separate_project_journal_lane')
            lanes.append(('separate_project_journal_lane', self.corpus['separate_project_journal_lane']['cases'], reason))
        if self.include_scoped_privacy and 'scoped_privacy_lane' in self.corpus:
            self.report['scope'].append('scoped_privacy_lane')
            privacy_reason = reason or (None if self.include_second_project else 'Second-project prerequisite was not selected')
            lanes.append(('scoped_privacy_lane', self.corpus['scoped_privacy_lane']['cases'], privacy_reason))
        aborted = None
        for lane, cases, skip_reason in lanes:
            for case in cases:
                self.current = {'name': case['name'], 'lane': lane, 'action': copy.deepcopy(case['action']),
                                'status': 'not_run', 'checks': []}
                self.report['cases'].append(self.current)
                if aborted or skip_reason:
                    self.current['reason'] = aborted or skip_reason
                    continue
                try:
                    self.execute(case)
                    if case.get('review_assertion'):
                        self.review('receipt-lookup-order', 'source-ordering-property')
                    statuses = {c['status'] for c in self.current['checks']}
                    self.current['status'] = 'incomplete' if 'skipped' in statuses else 'passed'
                    if not self.current['checks']:
                        raise ValueError('Zero-assertion case cannot pass')
                except Exception as exc:
                    self.current['status'] = 'failed'
                    self.current['error'] = f'{type(exc).__name__}: {exc}'
                    aborted = 'Prior case failed; dependent native state is not assumed: ' + case['name']
        counts = dict(Counter(c['status'] for c in self.report['cases']))
        self.report['case_counts'] = counts
        self.report['check_counts'] = dict(Counter(c['status'] for c in self.report['checks']))
        self.report['status'] = ('failed' if counts.get('failed') else 'incomplete'
                                 if not counts or counts.get('not_run') or counts.get('incomplete') else 'passed')
        self.report['functional_status'] = self.report['status']
        if self.report['status'] != 'passed':
            self.report['status'] = 'failed'
            self.report['failure_reason'] = 'Missing, skipped, unrun or failed required current-scope evidence'
            if self.defer_phase1_reviews:
                from qualification_gate import DEFERRED
                expected = {(case, name, 'Required typed current evidence missing: ' + identifier)
                            for identifier, (case, name) in DEFERRED.items()}
                skipped = [r for r in self.report['checks'] if r['status'] != 'passed']
                if (counts == {'passed': 145, 'incomplete': 3} and len(skipped) == 3
                        and all(r['status'] == 'skipped' for r in skipped)
                        and {(r.get('case'), r.get('name'), r.get('reason')) for r in skipped} == expected):
                    self.report['status'] = 'incomplete'
                    self.report['failure_reason'] = 'Executed native cases await three exact independent typed dispositions'
        self.report['elapsed_seconds'] = round(time.monotonic() - started, 6)
        self.report['captures'] = self.captures
        return self.report


def run(corpus, call, snapshot, restart=None, export=None, object_matrix=None, **options):
    return Runner(corpus, call, snapshot, restart, export, object_matrix, **options).run()

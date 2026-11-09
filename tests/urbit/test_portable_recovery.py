"""Synthetic HTTPS API responses and actual offline archive/filesystem checks.

No native runtime, authenticated live home, network, or restore is exercised.
The fixture independently supplies v3 rows; it does not implement authority.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('portable_recovery', ROOT / 'scripts/urbit/portable_recovery.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


def uid(n):
    return f'019939ba-4000-7000-8000-{n:012x}'


PROJECT, PRINCIPAL, BOX, DOC = map(uid, (1, 2, 3, 4))
ORIGIN = 'https://stead.example'
SECRET = 'd' * 64
CSRF = 'e' * 64
HEAD = '1' * 40


class Source:
    def __init__(self, count=1, mutate=None):
        self.calls, self.mutate, self.count = [], mutate, count
        self.who = {'principal_id': PRINCIPAL, 'identity_ship': '~bus', 'binding_id': uid(8),
            'binding_revision': '2', 'session_audit_id': 'a' * 64, 'display_name': 'Synthetic member',
            'organization_id': uid(9), 'team_id': uid(10), 'home': '~zod', 'can_create': 'no'}
        self.project = {'kind': 'project', 'resource_id': PROJECT, 'project_id': PROJECT, 'title': 'Portable fixture',
            'project_key': 'PORT', 'preset': 'general', 'authority_epoch': '7', 'resource_revision': '1', 'role': 'reader'}
        self.box = {'kind': 'container', 'resource_id': BOX, 'container_id': BOX, 'resource_revision': '1',
            'title': 'Pages', 'visibility': 'shared', 'container_head': HEAD}
        self.document = {'kind': 'document', 'resource_id': DOC, 'container_id': BOX, 'resource_revision': '2',
            'container_head': HEAD, 'title': 'Exact λ page', 'snippet': 'Exact λ page', 'visibility': 'shared',
            'markdown': f'---\nid: {DOC}\ntype: page\nstate: published\n---\n# Exact λ page\n\nTrailing spaces  \n\n'}
        self.work = [{'kind': 'work', 'resource_id': uid(100 + i), 'container_id': '', 'resource_revision': '3',
            'title': f'Item {i}', 'description': 'λ' * 250 + f'\nComplete description {i}\n',
            'type': 'task', 'status': 'in_progress', 'priority': 'medium', 'snippet': 'λ' * 160} for i in range(count)]
        self.relation = {'kind': 'relation', 'resource_id': uid(2000), 'container_id': '', 'resource_revision': '1',
            'title': 'Page documents item', 'type': 'documents', 'source_project_id': PROJECT,
            'source_kind': 'document', 'source_container_id': BOX, 'source_id': DOC,
            'target_project_id': PROJECT, 'target_kind': 'work', 'target_container_id': '', 'target_id': uid(100)}

    def __call__(self, query):
        self.calls.append(copy.deepcopy(query))
        assert set(query) == {'protocol', 'request_id', 'kind', 'project_id', 'container_id', 'resource_id', 'search', 'cursor'}
        assert query['protocol'] == 'stead.query/3'
        assert query['search'] == ''
        kind = query['kind']
        assert query['project_id'] == ('' if kind == 'identity' else PROJECT)
        next_cursor = ''
        generation = {'identity': '0', 'work': '2', 'document': '3', 'documents': '3', 'project': '4'}.get(kind, '1') * 64
        if kind == 'identity':
            rows = [self.who]
        elif kind == 'containers':
            rows = [self.box]
        elif kind == 'project':
            rows = [self.project]
        elif kind == 'work' and query['resource_id']:
            rows = [next(row for row in self.work if row['resource_id'] == query['resource_id'])]
        elif kind == 'work':
            offset = 20 if query['cursor'] else 0
            rows = [{**row, 'description': row['snippet']} for row in self.work[offset:offset + 20]]
            next_cursor = 'f' * 64 if offset + 20 < len(self.work) else ''
        elif kind == 'documents':
            assert query['container_id'] == BOX
            rows = [{k: v for k, v in self.document.items() if k != 'markdown'}]
        elif kind == 'document':
            assert (query['container_id'], query['resource_id']) == (BOX, DOC)
            rows = [self.document]
        elif kind == 'relations':
            rows = [self.relation] if self.work else []
        else:
            raise AssertionError('Unexpected query')
        value = {'protocol': 'stead.query-result/3', 'status': 'read', 'request_id': query['request_id'], 'kind': kind,
            'project_id': query['project_id'], 'container_id': query['container_id'], 'resource_id': query['resource_id'],
            'authority_epoch': '0' if kind == 'identity' else '7', 'generation': generation, 'cursor': next_cursor,
            'rows': {str(i): copy.deepcopy(row) for i, row in enumerate(rows)}}
        if self.mutate:
            self.mutate(query, value, self.calls)
        return json.dumps(value, ensure_ascii=False).encode()


class PortableRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-portable-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bundle = self.base / 'portable.zip'

    def capture(self, source=None):
        return P.capture(source or Source(), PROJECT, PRINCIPAL, ORIGIN)

    def publish(self, source=None):
        data, receipt = self.capture(source)
        result = P.write_bundle(data, receipt, self.bundle)
        return data, receipt, result

    def rewrite(self, transform):
        with zipfile.ZipFile(self.bundle) as z:
            files = {entry.filename: z.read(entry) for entry in z.infolist()}
        transform(files)
        with zipfile.ZipFile(self.bundle, 'w') as z:
            for name, raw in files.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                z.writestr(info, raw)

    def test_full_work_exact_markdown_and_offline_roundtrip(self):
        source = Source(21)
        data, receipt, result = self.publish(source)
        self.assertEqual(result['work'], 21)
        self.assertEqual(data['work'][0]['description'], source.work[0]['description'])
        self.assertGreater(len(data['work'][0]['description']), 160)
        self.assertEqual(receipt['source'], 'synthetic-test-only')
        self.assertEqual(receipt['authority_epoch'], '7')
        self.assertEqual(receipt['generation'], '1' * 64)
        files, checked = P.verify(self.bundle)
        name = f'docs/{BOX}/{DOC}.md'
        self.assertEqual(files[name], source.document['markdown'].encode())
        record = json.loads(files['records.json'])['documents'][0]
        raw = files[name]
        self.assertEqual(record['blob_oid'], hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest())
        self.assertEqual(checked['authentication'], 'not-independently-verifiable-offline')
        self.assertEqual(self.bundle.stat().st_mode & 0o777, 0o600)
        destination = self.base / 'recovered'
        self.assertEqual(P.extract(self.bundle, destination)['status'], 'files-extracted')
        self.assertEqual((destination / name).read_bytes(), raw)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(path.stat().st_mode & 0o077 == 0 for path in destination.rglob('*')))
        self.assertEqual(json.loads((destination / 'index.json').read_bytes())['documents'][0]['file'], name)
        self.assertNotIn('session_audit_id', receipt['identity'])
        self.assertNotIn('cursor', json.dumps(receipt))
        self.assertNotIn(SECRET.encode(), self.bundle.read_bytes())
        self.assertNotIn(CSRF.encode(), self.bundle.read_bytes())
        self.assertEqual(P.verify(self.bundle, expected_sha256=result['sha256'])[1], checked)
        with self.assertRaises(P.RecoveryError):
            P.verify(self.bundle, expected_sha256='0' * 64)

    def test_queries_never_leave_requested_project_or_call_mutations(self):
        source = Source()
        self.capture(source)
        self.assertEqual({call['project_id'] for call in source.calls}, {'', PROJECT})
        self.assertEqual({call['kind'] for call in source.calls}, {'identity', 'containers', 'project', 'work', 'documents', 'document', 'relations'})
        self.assertEqual([call['kind'] for call in source.calls[:3]], ['identity', 'containers', 'project'])
        self.assertEqual([call['kind'] for call in source.calls[-3:]], ['project', 'containers', 'identity'])

    def test_denied_and_uncorrelated_responses_fail_before_publication(self):
        for key, value in [('status', 'rejected'), ('protocol', 'stead.result/2'), ('request_id', uid(999)),
                           ('project_id', uid(999)), ('kind', 'receipt')]:
            with self.subTest(key=key):
                def mutate(query, result, calls):
                    if query['kind'] == 'work':
                        result[key] = value
                with self.assertRaises(P.RecoveryError):
                    self.publish(Source(mutate=mutate))
                self.assertFalse(self.bundle.exists())

    def test_generation_epoch_identity_or_head_changes_fail(self):
        for mode in ('generation', 'epoch', 'principal', 'head', 'revision'):
            with self.subTest(mode=mode):
                def mutate(query, value, calls):
                    if mode == 'generation' and query['kind'] == 'containers' and len(calls) > 3:
                        value['generation'] = '9' * 64
                    if mode == 'epoch' and query['kind'] == 'work' and query['resource_id']:
                        value['authority_epoch'] = '8'
                    if mode == 'principal' and query['kind'] == 'identity' and len(calls) > 1:
                        value['rows']['0']['principal_id'] = uid(999)
                    if mode == 'head' and query['kind'] == 'document':
                        value['rows']['0']['container_head'] = '8' * 40
                    if mode == 'revision' and query['kind'] == 'work' and query['resource_id']:
                        value['rows']['0']['resource_revision'] = '4'
                with self.assertRaises(P.RecoveryError):
                    self.publish(Source(mutate=mutate))
                self.assertFalse(self.bundle.exists())

    def test_foreign_scope_document_and_missing_relation_endpoint_fail(self):
        for mode in ('box', 'document-id', 'relation-project', 'relation-endpoint'):
            def mutate(query, value, calls):
                if query['kind'] == 'document' and mode == 'box':
                    value['rows']['0']['container_id'] = uid(999)
                if query['kind'] == 'document' and mode == 'document-id':
                    value['rows']['0']['markdown'] = value['rows']['0']['markdown'].replace(DOC, uid(999))
                if query['kind'] == 'relations' and mode == 'relation-project':
                    value['rows']['0']['target_project_id'] = uid(999)
                if query['kind'] == 'relations' and mode == 'relation-endpoint':
                    value['rows']['0']['target_id'] = uid(999)
            with self.subTest(mode=mode), self.assertRaises(P.RecoveryError):
                self.publish(Source(mutate=mutate))
            self.assertFalse(self.bundle.exists())

    def test_duplicate_resource_and_reused_pagination_fail(self):
        for mode in ('duplicate', 'cursor', 'changed'):
            def mutate(query, value, calls):
                if query['kind'] == 'work' and not query['resource_id'] and query['cursor']:
                    if mode == 'duplicate':
                        value['rows']['0']['resource_id'] = uid(100)
                    elif mode == 'cursor':
                        value['rows'] = {str(i): value['rows']['0'] for i in range(20)}
                        value['cursor'] = 'f' * 64
                    else:
                        value['generation'] = 'a' * 64
            with self.subTest(mode=mode), self.assertRaises(P.RecoveryError):
                self.capture(Source(21, mutate))

    def test_resource_byte_and_read_bounds(self):
        source = Source()
        source.work[0]['description'] = 'x' * 8193
        with self.assertRaises(P.RecoveryError):
            self.capture(source)
        with patch.object(P, 'MAX_READS', 3), self.assertRaises(P.RecoveryError):
            self.capture()
        with patch.object(P, 'MAX_CAPTURE', 100), self.assertRaises(P.RecoveryError):
            self.capture()
        with self.assertRaises(P.RecoveryError):
            P.capture(lambda _: b'x' * (P.MAX_RESPONSE + 1), PROJECT, PRINCIPAL, ORIGIN)

    def test_json_duplicates_nan_and_surrogates_are_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[[[[', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(P.RecoveryError):
                P.decoded(raw)
        with self.assertRaises(P.RecoveryError):
            P.text('\ud800')

    def test_session_file_private_regular_no_links_and_exact_fields(self):
        path = self.base / 'session.json'
        credentials = {'origin': ORIGIN, 'principal_id': PRINCIPAL, 'session': SECRET, 'csrf': CSRF}
        path.write_text(json.dumps(credentials)); path.chmod(0o600)
        self.assertEqual(P.session_file(path), credentials)
        path.chmod(0o644)
        with self.assertRaises(P.RecoveryError):
            P.session_file(path)
        path.chmod(0o600)
        symlink = self.base / 'symlink'
        symlink.symlink_to(path)
        with self.assertRaises(P.RecoveryError):
            P.session_file(symlink)
        hardlink = self.base / 'hardlink'
        os.link(path, hardlink)
        with self.assertRaises(P.RecoveryError):
            P.session_file(path)
        hardlink.unlink()
        path.write_text(json.dumps({**credentials, 'owner_code': 'not-allowed'}))
        with self.assertRaises(P.RecoveryError):
            P.session_file(path)

    def test_plain_http_userinfo_paths_and_redirect_origins_rejected(self):
        for value in ('http://stead.example', 'https://user:pass@stead.example', 'https://stead.example/',
                      'https://stead.example?x=1', 'https://stead.example:0', 'https://-bad.example', 'https://stead..example'):
            with self.subTest(value=value), self.assertRaises(P.RecoveryError):
                P.origin(value)

    def test_no_overwrite_of_archive_or_extract_destination(self):
        data, receipt, _ = self.publish()
        before = self.bundle.read_bytes()
        with self.assertRaises(P.RecoveryError):
            P.write_bundle(data, receipt, self.bundle)
        self.assertEqual(self.bundle.read_bytes(), before)
        out = self.base / 'existing'; out.mkdir()
        (out / 'keep').write_text('retained')
        with self.assertRaises(FileExistsError):
            P.extract(self.bundle, out)
        self.assertEqual((out / 'keep').read_text(), 'retained')

    def test_tampered_body_and_forged_derived_index_rejected(self):
        self.publish()
        self.rewrite(lambda files: files.__setitem__(f'docs/{BOX}/{DOC}.md', b'changed'))
        with self.assertRaises(P.RecoveryError):
            P.verify(self.bundle)
        self.bundle.unlink(); self.publish()
        def forge(files):
            files['index.json'] = b'{}'
            manifest = json.loads(files['manifest.json'])
            manifest['files']['index.json'] = {'bytes': 2, 'sha256': hashlib.sha256(b'{}').hexdigest()}
            files['manifest.json'] = json.dumps(manifest).encode()
        self.rewrite(forge)
        with self.assertRaises(P.RecoveryError):
            P.verify(self.bundle)

    def test_archive_traversal_symlinks_compression_and_duplicate_names_rejected(self):
        for mode in ('traversal', 'symlink', 'compression', 'duplicate'):
            with zipfile.ZipFile(self.bundle, 'w') as z:
                info = zipfile.ZipInfo('../escape' if mode == 'traversal' else 'records.json')
                info.create_system = 3
                info.external_attr = ((stat.S_IFLNK if mode == 'symlink' else stat.S_IFREG) | 0o600) << 16
                info.compress_type = zipfile.ZIP_DEFLATED if mode == 'compression' else zipfile.ZIP_STORED
                z.writestr(info, b'{}')
                if mode == 'duplicate':
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', UserWarning)
                        z.writestr(info, b'{}')
            with self.subTest(mode=mode), self.assertRaises(P.RecoveryError):
                P.verify(self.bundle)
            self.assertFalse((self.base / 'escape').exists())

    def test_cli_failure_never_echoes_sensitive_response(self):
        with patch.object(P, 'session_file', side_effect=P.RecoveryError(SECRET)), patch('sys.stderr', new_callable=io.StringIO) as err:
            result = P.main(['capture', '--session-file', str(self.base / 'missing'), '--project', PROJECT, '--output', str(self.bundle)])
        self.assertEqual(result, 1)
        self.assertNotIn(SECRET, err.getvalue())
        self.assertFalse(self.bundle.exists())

    def test_cli_offline_verify_and_extract(self):
        _, _, receipt = self.publish()
        for args, status in ((['verify', str(self.bundle), '--sha256', receipt['sha256']], 'integrity-verified'),
                             (['extract', str(self.bundle), '--output', str(self.base / 'cli-output')], 'files-extracted')):
            with patch('sys.stdout', new_callable=io.StringIO) as out:
                self.assertEqual(P.main(args), 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result['status'], status)
            self.assertEqual(result['source'], 'synthetic-test-only')
            self.assertEqual(result['authentication'], 'not-independently-verifiable-offline')

    def test_extract_rename_replacement_preserves_unrelated_data(self):
        self.publish()
        real_open = os.open
        for inject_failure in (True, False):
            output = self.base / f'extract-{inject_failure}'
            moved = self.base / f'moved-{inject_failure}'
            def adversarial_open(path, flags, *args, **kwargs):
                if path == 'capture.json':
                    output.rename(moved)
                    output.mkdir()
                    (output / 'unrelated-sentinel').write_text('preserve this')
                    if inject_failure:
                        raise OSError('synthetic write failure after rename')
                return real_open(path, flags, *args, **kwargs)
            with self.subTest(inject_failure=inject_failure), patch.object(P.os, 'open', adversarial_open):
                with self.assertRaises((OSError, P.RecoveryError)):
                    P.extract(self.bundle, output)
            self.assertEqual((output / 'unrelated-sentinel').read_text(), 'preserve this')
            self.assertEqual([p.name for p in output.iterdir()], ['unrelated-sentinel'])
            self.assertTrue((moved / 'README.txt').exists())
            if not inject_failure:
                self.assertTrue((moved / 'records.json').exists())

    def test_nested_extract_directory_replacement_cannot_claim_success(self):
        self.publish()
        real_open = os.open
        for kind in ('work', 'container'):
            output = self.base / f'nested-{kind}'
            name = f'{uid(100)}.md' if kind == 'work' else f'{DOC}.md'
            nested = output / 'work' if kind == 'work' else output / 'docs' / BOX
            moved = self.base / f'moved-nested-{kind}'
            def adversarial_open(path, flags, *args, **kwargs):
                if path == name:
                    nested.rename(moved)
                    nested.mkdir()
                    (nested / 'unrelated-sentinel').write_text('retain nested data')
                return real_open(path, flags, *args, **kwargs)
            with self.subTest(kind=kind), patch.object(P.os, 'open', adversarial_open):
                with self.assertRaises(P.RecoveryError):
                    P.extract(self.bundle, output)
            self.assertEqual((nested / 'unrelated-sentinel').read_text(), 'retain nested data')
            self.assertEqual([p.name for p in nested.iterdir()], ['unrelated-sentinel'])
            self.assertTrue((moved / name).exists())


class HTTPBoundary(unittest.TestCase):
    def run_query(self, *, status=200, content_type='application/json', encoding='identity', body=b'{}'):
        requests, response_reads = [], []
        class Response:
            def __init__(self):
                self.status, self.remaining = status, body
            def getheader(self, key, default):
                return {'Content-Type': content_type, 'Content-Encoding': encoding}.get(key, default)
            def read1(self, size):
                response_reads.append(size)
                part, self.remaining = self.remaining[:size], self.remaining[size:]
                return part
        class Connection:
            sock = None
            def __init__(self, *args, **kwargs):
                requests.append(('connect', args, kwargs))
            def request(self, *args, **kwargs):
                requests.append(('request', args, kwargs))
            def getresponse(self):
                return Response()
            def close(self):
                requests.append(('closed',))
        credentials = {'origin': ORIGIN, 'principal_id': PRINCIPAL, 'session': SECRET, 'csrf': CSRF}
        self.requests, self.response_reads = requests, response_reads
        with patch.object(P.http.client, 'HTTPSConnection', Connection):
            query = P.HTTPSQueries(credentials)
            self.assertTrue(query.context.check_hostname)
            self.assertEqual(query.context.verify_mode, P.ssl.CERT_REQUIRED)
            return query({'protocol': 'stead.query/3'})

    def test_tls_required_exact_path_and_only_member_credentials(self):
        self.assertEqual(self.run_query(), b'{}')
        _, args, kwargs = self.requests[1]
        self.assertEqual(args, ('POST', '/stead/api/query'))
        self.assertEqual(kwargs['headers']['Cookie'], '__Host-stead-session=' + SECRET)
        self.assertEqual(kwargs['headers']['X-Stead-CSRF'], CSRF)
        self.assertEqual(kwargs['headers']['Origin'], ORIGIN)
        self.assertEqual(self.requests[-1], ('closed',))

    def test_redirect_and_wrong_type_stop_without_reading_body(self):
        for options in ({'status': 302}, {'status': 401}, {'content_type': 'text/html'}, {'encoding': 'gzip'}):
            with self.subTest(options=options), self.assertRaises(P.RecoveryError):
                self.run_query(**options)
            self.assertEqual(self.response_reads, [])
            self.assertEqual(len([r for r in self.requests if r[0] == 'request']), 1)

    def test_oversized_response_aborts_at_bound(self):
        with self.assertRaises(P.RecoveryError):
            self.run_query(body=b'x' * (P.MAX_RESPONSE + 1))
        self.assertEqual(sum(self.response_reads), P.MAX_RESPONSE + 1)


if __name__ == '__main__':
    unittest.main()

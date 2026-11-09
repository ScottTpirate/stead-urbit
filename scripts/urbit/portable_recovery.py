"""Bounded member-authorized current-record export; never a home-state restore.

Only capture performs network I/O, through the existing configured-team query
API. Offline hashes establish integrity, not a signature from the authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import stat
import sys
import time
from urllib.parse import urlsplit
import zipfile

UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
TOKEN = re.compile(r'[0-9a-f]{64}')
OID = re.compile(r'[0-9a-f]{40}')
NUMBER = re.compile(r'0|[1-9][0-9]{0,19}')
MAX_RESPONSE = 262144
MAX_CAPTURE = 32 * 1024 * 1024
MAX_ARTIFACT = 64 * 1024 * 1024
MAX_READS = 1400
DEADLINE = 300
SOURCES = {'https-member-query', 'synthetic-test-only'}
LOSSES = {
    'protocol': 'stead.portable-losses/1',
    'coverage': 'Current records readable by this principal in one project.',
    'omitted': [
        'Unreadable records, deleted records and previous revisions.',
        'Git commit/tree objects, complete history, Code repositories and attachments.',
        'Accepted journal, command receipts, activity, inbox and historical attribution.',
        'Grants, authentication credentials, sessions, identity keys and restore authority.',
    ],
    'git': 'Container heads are observed metadata. Blob OIDs are computed from exact Markdown; no commit linkage is proved.',
    'recovery': 'Offline files only. This is not a pier backup or an executable authority restore.',
    'authenticity': 'Client read observations and hashes are not an independently signed home attestation.',
}
README = b'''Stead portable current-record export\n\nRead index.json and records.json; pages are in docs/ and Work descriptions in work/.\nMarkdown bytes are preserved. Work Markdown and index.json are derived views.\nRead losses.json before treating this as a backup: history, inaccessible data,\ncredentials and authority state are absent. No restore or import is performed.\n\nVerify with: python3 scripts/urbit/portable_recovery.py verify ARTIFACT\nExtract with: python3 scripts/urbit/portable_recovery.py extract ARTIFACT --output NEW_DIRECTORY\nVerification proves internal integrity, not provenance, current permission or\na signature from the home. Retain a separately trusted artifact SHA-256 if needed.\nThis archive contains readable project data; protect every retained copy.\n'''


class RecoveryError(ValueError):
    """Fixed, nonsecret diagnostic code; never includes a response or credential."""


def require(condition, code):
    if not condition:
        raise RecoveryError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise RecoveryError('invalid-json') from None


def decoded(raw, bound=MAX_RESPONSE):
    require(isinstance(raw, bytes) and 0 < len(raw) <= bound, 'json-bound')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate-json-key')
            result[key] = value
        return result
    def invalid(_):
        raise RecoveryError('invalid-json')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError):
        raise RecoveryError('invalid-json') from None


def shape(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'record-shape')


def text(value, maximum=32768):
    require(isinstance(value, str), 'text-type')
    try:
        require(len(value.encode('utf-8')) <= maximum and '\0' not in value, 'text-bound')
    except UnicodeError:
        raise RecoveryError('invalid-text') from None
    return value


def match(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def number(value, positive=True):
    require(match(NUMBER, value) and int(value) <= 2**64 - 1 and (not positive or int(value) > 0), 'invalid-number')


def origin(value):
    require(isinstance(value, str) and len(value) <= 256, 'invalid-origin')
    require(re.fullmatch(r'https://[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?(?::[1-9][0-9]{0,4})?', value) is not None, 'invalid-origin')
    try:
        parts = urlsplit(value)
        require(parts.port is None or 1 <= parts.port <= 65535, 'invalid-origin')
        require(all(1 <= len(label) <= 63 and not label.startswith('-') and not label.endswith('-') for label in parts.hostname.split('.')), 'invalid-origin')
    except ValueError:
        raise RecoveryError('invalid-origin') from None
    return parts


def private_file(path, bound):
    """Open once, without following a leaf symlink; check the opened inode."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and info.st_nlink == 1 and info.st_mode & 0o077 == 0, 'private-file-required')
            require(info.st_size <= bound, 'file-bound')
            raw = stream.read(bound + 1)
            require(len(raw) <= bound, 'file-bound')
            return raw
    except OSError:
        raise RecoveryError('private-file-unavailable') from None


def session_file(path):
    value = decoded(private_file(path, 2048), 2048)
    shape(value, {'origin', 'principal_id', 'session', 'csrf'})
    origin(value['origin'])
    require(match(UUID, value['principal_id']) and match(TOKEN, value['session']) and match(TOKEN, value['csrf']), 'invalid-session-file')
    return value


def new_id():
    data = bytearray(secrets.token_bytes(16))
    data[:6] = int(time.time() * 1000).to_bytes(6, 'big')
    data[6] = (data[6] & 15) | 112
    data[8] = (data[8] & 63) | 128
    value = data.hex()
    return f'{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}'


class HTTPSQueries:
    """Exactly one HTTPS origin/route. No redirects, proxies or TLS bypass."""
    def __init__(self, credentials, *, ca_file=None):
        self.credentials = credentials
        self.parts = origin(credentials['origin'])
        self.context = ssl.create_default_context(cafile=ca_file)
        self.deadline = time.monotonic() + DEADLINE

    def __call__(self, query):
        return self._post('/stead/api/query', query)

    def _connection(self, timeout):
        return http.client.HTTPSConnection(self.parts.hostname, self.parts.port,
            context=self.context, timeout=timeout)

    def _post(self, route, body):
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'capture-deadline')
        connection = self._connection(min(15, remaining))
        try:
            connection.request('POST', route, body=encoded(body), headers={
                'Origin': self.credentials['origin'], 'Content-Type': 'application/json',
                'Cookie': '__Host-stead-session=' + self.credentials['session'],
                'X-Stead-CSRF': self.credentials['csrf'], 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Cache-Control': 'no-store',
            })
            response = connection.getresponse()
            require(response.status == 200, 'https-read-rejected')
            require(response.getheader('Content-Type', '').split(';')[0] == 'application/json'
                    and response.getheader('Content-Encoding', 'identity') == 'identity', 'https-response-type')
            result = bytearray()
            while True:
                remaining = self.deadline - time.monotonic()
                require(remaining > 0, 'capture-deadline')
                if connection.sock:
                    connection.sock.settimeout(min(15, remaining))
                chunk = response.read1(min(65536, MAX_RESPONSE + 1 - len(result)))
                require(time.monotonic() < self.deadline, 'capture-deadline')
                if not chunk:
                    break
                result.extend(chunk)
                require(len(result) <= MAX_RESPONSE, 'response-bound')
            return bytes(result)
        except (OSError, http.client.HTTPException):
            raise RecoveryError('https-query-failed') from None
        finally:
            connection.close()


class Reads:
    def __init__(self, query):
        self.query, self.receipts, self.total = query, [], 0
        self.deadline = time.monotonic() + DEADLINE

    def read(self, kind, project='', container='', resource='', cursor=''):
        require(len(self.receipts) < MAX_READS and time.monotonic() < self.deadline, 'capture-bound')
        request = {'protocol': 'stead.query/3', 'request_id': new_id(), 'kind': kind,
                   'project_id': project, 'container_id': container, 'resource_id': resource, 'search': '', 'cursor': cursor}
        raw = self.query(request)
        require(time.monotonic() < self.deadline, 'capture-deadline')
        value = decoded(raw)
        self.total += len(raw)
        require(self.total <= MAX_CAPTURE, 'capture-byte-bound')
        shape(value, {'protocol', 'status', 'request_id', 'kind', 'project_id', 'container_id', 'resource_id', 'authority_epoch', 'generation', 'cursor', 'rows'})
        require(value['protocol'] == 'stead.query-result/3' and value['status'] == 'read', 'read-rejected')
        require(all(value[key] == request[key] for key in ('request_id', 'kind', 'project_id', 'container_id', 'resource_id')), 'read-correlation')
        number(value['authority_epoch'], positive=bool(project))
        require(match(TOKEN, value['generation']) and (value['cursor'] == '' or match(TOKEN, value['cursor'])), 'read-token')
        rows = value['rows']
        require(isinstance(rows, dict) and len(rows) <= 20 and set(rows) == {str(i) for i in range(len(rows))}, 'read-rows')
        for row in rows.values():
            require(isinstance(row, dict) and len(row) <= 32, 'read-row')
            for key, item in row.items():
                text(key, 64)
                text(item)
        self.receipts.append({
            'request_id': request['request_id'], 'kind': kind, 'project_id': project,
            'container_id': container, 'resource_id': resource, 'authority_epoch': value['authority_epoch'],
            'generation': value['generation'], 'response_sha256': sha(raw), 'rows_sha256': sha(encoded(rows)),
            'row_count': len(rows), 'continued': value['cursor'] != '',
        })
        return value, [rows[str(i)] for i in range(len(rows))]

    def walk(self, kind, project, container='', bound=128):
        rows, seen, cursor, baseline = [], set(), '', None
        while True:
            value, page = self.read(kind, project, container, cursor=cursor)
            stamp = (value['authority_epoch'], value['generation'])
            require(baseline is None or stamp == baseline, 'changed-query-generation')
            baseline = stamp
            rows.extend(page)
            require(len(rows) <= bound, 'row-bound')
            cursor = value['cursor']
            if not cursor:
                return baseline, rows
            require(len(page) == 20 and cursor not in seen, 'invalid-pagination')
            seen.add(cursor)

    def one(self, kind, project='', container='', resource=''):
        value, rows = self.read(kind, project, container, resource)
        require(len(rows) == 1 and value['cursor'] == '', 'single-row-required')
        return (value['authority_epoch'], value['generation']), rows[0]


def rows_by_id(rows, bound):
    require(isinstance(rows, list) and len(rows) <= bound, 'row-bound')
    result = {}
    for row in rows:
        require(isinstance(row, dict) and match(UUID, row.get('resource_id')) and row['resource_id'] not in result, 'duplicate-or-invalid-resource')
        result[row['resource_id']] = row
    return result


def identity(row, principal):
    shape(row, {'principal_id', 'identity_ship', 'binding_id', 'binding_revision', 'session_audit_id', 'display_name', 'organization_id', 'team_id', 'home', 'can_create'})
    require(row['principal_id'] == principal and all(match(UUID, row[k]) for k in ('principal_id', 'binding_id', 'organization_id', 'team_id')), 'identity-mismatch')
    require(all(re.fullmatch(r'~[a-z-]{3,63}', row[k]) for k in ('identity_ship', 'home')) and match(TOKEN, row['session_audit_id']), 'identity-shape')
    number(row['binding_revision'])
    text(row['display_name'], 800)
    require(row['can_create'] in {'yes', 'no'}, 'identity-shape')


def validate_data(data):
    shape(data, {'project', 'work', 'containers', 'documents', 'relations'})
    project = data['project']
    require(isinstance(project, dict), 'project-shape')
    fields = {'kind', 'resource_id', 'project_id', 'title', 'project_key', 'preset', 'authority_epoch', 'resource_revision', 'role'}
    shape(project, fields | ({'policy_revision'} if project.get('role') == 'maintainer' else set()))
    require(project['kind'] == 'project' and match(UUID, project['project_id']) and project['project_id'] == project['resource_id']
            and project['preset'] == 'general' and project['role'] in {'maintainer', 'contributor', 'reader'}, 'project-shape')
    number(project['authority_epoch']); number(project['resource_revision'])
    if 'policy_revision' in project:
        number(project['policy_revision'])
    text(project['title'], 800)
    require(re.fullmatch(r'[A-Z][A-Z0-9]{1,9}', project['project_key']) is not None, 'project-key')
    works = rows_by_id(data['work'], 128)
    containers = rows_by_id(data['containers'], 32)
    relations = rows_by_id(data['relations'], 256)
    for row in works.values():
        shape(row, {'kind', 'resource_id', 'container_id', 'resource_revision', 'title', 'description', 'type', 'status', 'priority', 'snippet'})
        require(row['kind'] == 'work' and row['container_id'] == '', 'work-scope')
        number(row['resource_revision']); text(row['title'], 800); text(row['description'], 8192); text(row['snippet'], 640)
        require(row['type'] in {'deliverable', 'task', 'problem'} and row['status'] in {'backlog', 'todo', 'in_progress', 'blocked', 'done', 'canceled'}
                and row['priority'] in {'none', 'low', 'medium', 'high', 'urgent'}, 'work-fields')
    for key, row in containers.items():
        shape(row, {'kind', 'resource_id', 'container_id', 'resource_revision', 'title', 'visibility', 'container_head'})
        require(row['kind'] == 'container' and row['container_id'] == key and row['resource_revision'] == '1'
                and row['visibility'] in {'private', 'shared'} and (row['container_head'] == '' or match(OID, row['container_head'])), 'container-fields')
        text(row['title'], 800)
    require(isinstance(data['documents'], list) and len(data['documents']) <= 1024, 'document-bound')
    documents, counts = {}, {}
    for row in data['documents']:
        shape(row, {'kind', 'resource_id', 'container_id', 'resource_revision', 'container_head', 'title', 'snippet', 'visibility', 'markdown'})
        key = (row['container_id'], row['resource_id'])
        require(row['container_id'] in containers and match(UUID, row['resource_id']) and key not in documents, 'document-scope')
        box = containers[row['container_id']]
        require(row['kind'] == 'document' and row['visibility'] == box['visibility'] and row['container_head'] == box['container_head'] and match(OID, row['container_head']), 'document-head')
        number(row['resource_revision']); text(row['title'], 320); text(row['snippet'], 640); text(row['markdown'])
        state = 'draft' if row['visibility'] == 'private' else 'published'
        require(row['markdown'].startswith(f"---\nid: {row['resource_id']}\ntype: page\nstate: {state}\n---\n") and '\r' not in row['markdown'], 'document-frontmatter')
        documents[key] = row
        counts[key[0]] = counts.get(key[0], 0) + 1
        require(counts[key[0]] <= 32, 'document-bound')
    for row in relations.values():
        shape(row, {'kind', 'resource_id', 'container_id', 'resource_revision', 'title', 'type', 'source_project_id', 'source_kind', 'source_container_id', 'source_id', 'target_project_id', 'target_kind', 'target_container_id', 'target_id'})
        require(row['kind'] == 'relation' and row['container_id'] == '' and row['type'] in {'related_to', 'blocks', 'documents'}, 'relation-fields')
        number(row['resource_revision']); text(row['title'], 2048)
        for end in ('source', 'target'):
            require(row[end + '_project_id'] == project['project_id'], 'relation-project')
            kind, box, resource = (row[end + '_' + field] for field in ('kind', 'container_id', 'id'))
            require((kind == 'work' and box == '' and resource in works) or (kind == 'document' and (box, resource) in documents), 'relation-endpoint')
        if row['type'] == 'blocks':
            require(row['source_kind'] == row['target_kind'] == 'work', 'relation-type')
        if row['type'] == 'documents':
            require(row['source_kind'] == 'document' and row['target_kind'] == 'work', 'relation-type')


def capture(query, project, principal, home_origin, *, source='synthetic-test-only'):
    require(match(UUID, project) and match(UUID, principal) and source in SOURCES, 'capture-scope')
    origin(home_origin)
    started = datetime.now(timezone.utc).isoformat()
    reads = Reads(query)
    first_identity_stamp, who = reads.one('identity')
    identity(who, principal)
    baseline, boxes = reads.walk('containers', project, bound=32)
    box_map = rows_by_id(boxes, 32)
    project_stamp, project_row = reads.one('project', project)
    require(project_row.get('project_id') == project and project_row.get('authority_epoch') == baseline[0] == project_stamp[0], 'project-scope')
    work_stamp, listed_work = reads.walk('work', project)
    work_map = rows_by_id(listed_work, 128)
    work, documents = [], []
    for key, listing in sorted(work_map.items()):
        stamp, row = reads.one('work', project, resource=key)
        require(stamp == work_stamp and stamp[0] == baseline[0] and all(row.get(k) == v for k, v in listing.items() if k != 'description'), 'changed-work')
        work.append(row)
    for box in sorted(box_map):
        stamp, listed = reads.walk('documents', project, box, bound=32)
        for key, listing in sorted(rows_by_id(listed, 32).items()):
            detail_stamp, row = reads.one('document', project, box, key)
            require(detail_stamp == stamp and stamp[0] == baseline[0] and all(row.get(k) == v for k, v in listing.items()), 'changed-document')
            documents.append(row)
    relation_stamp, relations = reads.walk('relations', project, bound=256)
    require(relation_stamp == baseline, 'changed-project-generation')
    final_project_stamp, final_project = reads.one('project', project)
    final_stamp, final_boxes = reads.walk('containers', project, bound=32)
    final_identity_stamp, final_identity = reads.one('identity')
    require((final_stamp, rows_by_id(final_boxes, 32)) == (baseline, box_map)
            and (final_project_stamp, final_project) == (project_stamp, project_row)
            and (final_identity_stamp, final_identity) == (first_identity_stamp, who), 'capture-changed')
    data = {'project': project_row, 'work': work, 'containers': boxes, 'documents': documents, 'relations': relations}
    validate_data(data)
    observed_identity = {key: value for key, value in who.items() if key not in {'session_audit_id', 'can_create'}}
    receipt = {'protocol': 'stead.portable-capture/1', 'source': source, 'origin': home_origin,
               'project_id': project, 'authority_epoch': baseline[0], 'generation': baseline[1],
               'identity': observed_identity, 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
               'reads': reads.receipts, 'authenticity': 'Client observation only; no independent home signature.'}
    return data, receipt


def validate_receipt(receipt, project):
    shape(receipt, {'protocol', 'source', 'origin', 'project_id', 'authority_epoch', 'generation', 'identity', 'started_at', 'finished_at', 'reads', 'authenticity'})
    require(receipt['protocol'] == 'stead.portable-capture/1' and receipt['source'] in SOURCES and receipt['project_id'] == project['project_id']
            and receipt['authority_epoch'] == project['authority_epoch'] and match(TOKEN, receipt['generation'])
            and receipt['authenticity'] == 'Client observation only; no independent home signature.', 'capture-receipt')
    origin(receipt['origin'])
    shape(receipt['identity'], {'principal_id', 'identity_ship', 'binding_id', 'binding_revision', 'display_name', 'organization_id', 'team_id', 'home'})
    who = dict(receipt['identity'])
    who.update(session_audit_id='0' * 64, can_create='no')
    identity(who, who.get('principal_id'))
    for key in ('started_at', 'finished_at'):
        require(isinstance(receipt[key], str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T[0-9:.]+\+00:00', receipt[key]), 'capture-time')
    require(isinstance(receipt['reads'], list) and 7 <= len(receipt['reads']) <= MAX_READS, 'capture-read-bound')
    seen = set()
    for read in receipt['reads']:
        shape(read, {'request_id', 'kind', 'project_id', 'container_id', 'resource_id', 'authority_epoch', 'generation', 'response_sha256', 'rows_sha256', 'row_count', 'continued'})
        require(match(UUID, read['request_id']) and read['request_id'] not in seen and read['kind'] in {'identity', 'project', 'work', 'containers', 'documents', 'document', 'relations'}, 'capture-read')
        seen.add(read['request_id'])
        require(read['project_id'] == ('' if read['kind'] == 'identity' else project['project_id'])
                and all(read[k] == '' or match(UUID, read[k]) for k in ('container_id', 'resource_id'))
                and read['authority_epoch'] == ('0' if read['kind'] == 'identity' else project['authority_epoch']), 'capture-read-scope')
        require(all(match(TOKEN, read[k]) for k in ('generation', 'response_sha256', 'rows_sha256'))
                and type(read['row_count']) is int and 0 <= read['row_count'] <= 20 and type(read['continued']) is bool, 'capture-read-fields')


def package_files(data, receipt):
    validate_data(data)
    validate_receipt(receipt, data['project'])
    files = {'README.txt': README, 'losses.json': encoded(LOSSES), 'capture.json': encoded(receipt)}
    records = {**data, 'documents': []}
    index = {'protocol': 'stead.portable-index/1', 'project_id': data['project']['project_id'], 'work': [], 'documents': []}
    for row in data['work']:
        name = f"work/{row['resource_id']}.md"
        files[name] = (f"# {row['title']}\n\nType: {row['type']}\nStatus: {row['status']}\nPriority: {row['priority']}\n\n" + row['description']).encode('utf-8')
        index['work'].append({'id': row['resource_id'], 'title': row['title'], 'file': name})
    for row in data['documents']:
        name = f"docs/{row['container_id']}/{row['resource_id']}.md"
        raw = row['markdown'].encode('utf-8')
        files[name] = raw
        entry = {key: value for key, value in row.items() if key != 'markdown'}
        entry.update(markdown_file=name, markdown_sha256=sha(raw), blob_oid=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())
        records['documents'].append(entry)
        index['documents'].append({'id': row['resource_id'], 'container_id': row['container_id'], 'title': row['title'], 'file': name})
    files['records.json'] = encoded(records)
    files['index.json'] = encoded(index)
    require(len(files) <= 1200 and sum(map(len, files.values())) <= MAX_ARTIFACT - 1024 * 1024, 'artifact-bound')
    return files


def write_bundle(data, receipt, destination):
    files = package_files(data, receipt)
    manifest = {'protocol': 'stead.portable-artifact/1', 'files': {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in files.items()}}
    files['manifest.json'] = encoded(manifest)
    destination = Path(destination)
    require(not destination.exists() and not destination.is_symlink(), 'destination-exists')
    parent = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = '.stead-portable-' + secrets.token_hex(16)
    fd = None
    try:
        fd = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'w+b') as stream:
            fd = None
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
                for name, raw in sorted(files.items()):
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o600) << 16
                    archive.writestr(info, raw)
            stream.flush(); os.fsync(stream.fileno())
            opened = os.fstat(stream.fileno())
            require(opened.st_size <= MAX_ARTIFACT, 'artifact-bound')
            stream.seek(0)
            digest = sha(stream.read(MAX_ARTIFACT + 1))
            require(same_entry(parent, temporary, opened), 'temporary-binding-changed')
            # Exclusive, descriptor-relative publication; hash the held file,
            # never a pathname another process may replace after publication.
            os.link(temporary, destination.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            require(same_entry(parent, destination.name, opened), 'output-binding-changed')
            require(same_path(destination.parent, os.fstat(parent)), 'parent-binding-changed')
    finally:
        if fd is not None:
            os.close(fd)
        # Do not follow a renamed/replaced temporary entry for cleanup.
        if 'opened' in locals() and same_entry(parent, temporary, opened):
            os.unlink(temporary, dir_fd=parent)
        os.close(parent)
    return {'status': 'captured', 'source': receipt['source'], 'work': len(data['work']), 'documents': len(data['documents']), 'sha256': digest}


def same_entry(parent, name, opened):
    try:
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        return (current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino)
    except OSError:
        return False


def same_path(path, opened):
    try:
        current = os.stat(path, follow_symlinks=False)
        return (current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino)
    except OSError:
        return False


def verify(path, *, expected_sha256=None):
    require(expected_sha256 is None or match(TOKEN, expected_sha256), 'invalid-expected-digest')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_ARTIFACT, 'artifact-bound')
            raw = stream.read(MAX_ARTIFACT + 1)
        require(len(raw) <= MAX_ARTIFACT, 'artifact-bound')
        require(expected_sha256 is None or sha(raw) == expected_sha256, 'artifact-digest')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            require(1 <= len(entries) <= 1201 and len({entry.filename for entry in entries}) == len(entries), 'archive-inventory')
            require(sum(entry.file_size for entry in entries) <= MAX_ARTIFACT, 'artifact-bound')
            files = {}
            for entry in entries:
                require(entry.compress_type == zipfile.ZIP_STORED and not entry.flag_bits & 1
                        and stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFREG and not entry.extra
                        and re.fullmatch(r'(?:[a-z]+\.json|README\.txt|work/[0-9a-f-]{36}\.md|docs/[0-9a-f-]{36}/[0-9a-f-]{36}\.md)', entry.filename), 'archive-entry')
                files[entry.filename] = archive.read(entry)
    except (OSError, zipfile.BadZipFile, RuntimeError):
        raise RecoveryError('artifact-unreadable') from None
    require('manifest.json' in files, 'manifest-missing')
    manifest = decoded(files.pop('manifest.json'), 1024 * 1024)
    shape(manifest, {'protocol', 'files'})
    require(manifest['protocol'] == 'stead.portable-artifact/1' and isinstance(manifest['files'], dict) and set(manifest['files']) == set(files), 'manifest-inventory')
    for name, body in files.items():
        shape(manifest['files'][name], {'bytes', 'sha256'})
        require(type(manifest['files'][name]['bytes']) is int and manifest['files'][name]['bytes'] == len(body)
                and manifest['files'][name]['sha256'] == sha(body), 'file-digest')
    require({'records.json', 'capture.json', 'index.json', 'losses.json', 'README.txt'} <= set(files), 'records-missing')
    records = decoded(files['records.json'], MAX_CAPTURE)
    receipt = decoded(files['capture.json'], 2 * 1024 * 1024)
    require(isinstance(records, dict) and isinstance(records.get('documents'), list) and len(records['documents']) <= 1024, 'document-bound')
    documents = []
    for entry in records['documents']:
        require(isinstance(entry, dict) and {'markdown_file', 'markdown_sha256', 'blob_oid'} <= set(entry), 'document-file')
        name = entry['markdown_file']
        require(isinstance(name, str) and name in files and match(TOKEN, entry['markdown_sha256']) and sha(files[name]) == entry['markdown_sha256'], 'document-file')
        row = {key: value for key, value in entry.items() if key not in {'markdown_file', 'markdown_sha256', 'blob_oid'}}
        try:
            row['markdown'] = files[name].decode('utf-8')
        except UnicodeError:
            raise RecoveryError('document-encoding') from None
        documents.append(row)
    data = {**records, 'documents': documents}
    expected = package_files(data, receipt)
    require(expected == files, 'derived-file-mismatch')
    return files, {'status': 'integrity-verified', 'authentication': 'not-independently-verifiable-offline',
                   'source': receipt['source'], 'work': len(data['work']), 'documents': len(documents), 'sha256': sha(raw)}


def extract(path, destination, *, expected_sha256=None):
    files, result = verify(path, expected_sha256=expected_sha256)
    destination = Path(destination)
    # This creates only a new private data directory, never a pier or authority.
    parent = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    directories = {}
    try:
        os.mkdir(destination.name, mode=0o700, dir_fd=parent)
        root = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        directories[()] = root
        opened = os.fstat(root)
        for name, raw in sorted(files.items()):
            parts, key = name.split('/'), ()
            for part in parts[:-1]:
                child = (*key, part)
                if child not in directories:
                    os.mkdir(part, mode=0o700, dir_fd=directories[key])
                    directories[child] = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directories[key])
                key = child
            with os.fdopen(os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directories[key]), 'wb') as stream:
                stream.write(raw)
        for key, directory in directories.items():
            if key:
                require(same_entry(directories[key[:-1]], key[-1], os.fstat(directory)), 'output-binding-changed')
        require(same_entry(parent, destination.name, opened) and same_path(destination.parent, os.fstat(parent)), 'output-binding-changed')
    finally:
        # On failure preserve the private partial output. Recursive pathname
        # cleanup could delete unrelated data after a concurrent rename.
        for directory in directories.values():
            os.close(directory)
        os.close(parent)
    return {**result, 'status': 'files-extracted'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    cap = sub.add_parser('capture', help='Read one project through an existing individual HTTPS session')
    cap.add_argument('--session-file', required=True)
    cap.add_argument('--project', required=True)
    cap.add_argument('--output', required=True)
    cap.add_argument('--ca-file', help='Trusted CA file; TLS hostname and certificate verification remain required')
    check = sub.add_parser('verify', help='Check offline integrity, not authority or authentication')
    check.add_argument('artifact')
    check.add_argument('--sha256', help='Previously retained trusted artifact digest')
    unpack = sub.add_parser('extract', help='Recover readable files into a new private directory')
    unpack.add_argument('artifact'); unpack.add_argument('--output', required=True)
    unpack.add_argument('--sha256', help='Previously retained trusted artifact digest')
    args = parser.parse_args(argv)
    try:
        if args.action == 'capture':
            output = Path(args.output)
            require(not output.exists() and not output.is_symlink() and output.parent.is_dir(), 'destination-unavailable')
            credentials = session_file(args.session_file)
            data, receipt = capture(HTTPSQueries(credentials, ca_file=args.ca_file), args.project,
                credentials['principal_id'], credentials['origin'], source='https-member-query')
            result = write_bundle(data, receipt, args.output)
        elif args.action == 'verify':
            _, result = verify(args.artifact, expected_sha256=args.sha256)
        else:
            result = extract(args.artifact, args.output, expected_sha256=args.sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (RecoveryError, OSError, ValueError, TypeError, KeyError, OverflowError):
        # Never serialize raw API exceptions, response text, paths or secrets.
        print('Portable export failed; no successful capture or restore is claimed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

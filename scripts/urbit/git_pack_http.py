"""Read-only Smart HTTP adapter for Home-approved, immutable Git packs."""
import base64
import binascii
import http.client
import re
import ssl
import subprocess
from threading import BoundedSemaphore
import time

import git_pack_store as store
from git_pack_upload import MAX_REQUEST, authorized_response
from portable_recovery import (TOKEN, UUID, RecoveryError, decoded, encoded, match,
                               number, origin, require, shape, sha)


MAX_DECISION = 160 * 1024
FETCH_TYPE = 'application/x-git-upload-pack-request'
PATH = re.compile(r'/stead/git/([0-9a-z-]{36})\.git/(info/refs|git-upload-pack)')
READ_PROTOCOL = 'stead.code-pack-read/1'
FIELDS = {'protocol', 'home', 'project_id', 'repository_id', 'authority_epoch',
          'snapshot', 'head', 'refs', 'pack_sha256', 'pack_bytes', 'object_count',
          'object_bytes', 'object_ids_sha256', 'principal_id', 'binding_id',
          'binding_revision', 'identity_ship'}


class Denied(RecoveryError):
    pass


def basic(value):
    if not isinstance(value, str) or len(value) != 102 or not value.isascii() or not value.startswith('Basic '):
        raise Denied('git-credential-required')
    value = value[6:]
    try:
        raw = base64.b64decode(value, validate=True)
        token = raw[6:].decode('ascii')
    except (UnicodeError, binascii.Error):
        raise Denied('git-credential-required') from None
    if not raw.startswith(b'stead:') or base64.b64encode(raw).decode('ascii') != value or not match(TOKEN, token):
        raise Denied('git-credential-required')
    return 'Basic ' + value


def decision(raw, project):
    row = decoded(raw, MAX_DECISION)
    shape(row, FIELDS)
    require(row['protocol'] == READ_PROTOCOL and row['project_id'] == project
            and row['repository_id'] == project, 'home-decision-scope')
    require(all(match(UUID, row[key]) for key in ('principal_id', 'binding_id'))
            and match(store.SHIP, row['identity_ship']) and row['identity_ship'] != row['home'],
            'home-decision-actor')
    for key in ('binding_revision', 'pack_bytes', 'object_count', 'object_bytes'):
        number(row[key])
    for key in ('snapshot', 'pack_sha256', 'object_ids_sha256'):
        require(match(TOKEN, row[key]), 'home-decision-digest')
    require(32 <= int(row['pack_bytes']) <= store.MAX_PACK
            and int(row['object_count']) <= store.MAX_OBJECTS
            and int(row['object_bytes']) <= store.MAX_OBJECT_BYTES, 'home-decision-bound')
    require(isinstance(row['refs'], str) and row['refs'].isascii(), 'home-decision-refs')
    refs = decoded(row['refs'].encode('ascii'), MAX_DECISION)
    store.validate_refs(refs, row['head'])
    scope = {key: row[key] for key in ('home', 'project_id', 'repository_id', 'authority_epoch')}
    store.validate_scope(scope)
    manifest = {'format': store.FORMAT, 'object_format': 'sha1', 'scope': scope,
                'head': row['head'], 'refs': refs, 'pack_sha256': row['pack_sha256'],
                'object_ids_sha256': row['object_ids_sha256'],
                **{key: int(row[key]) for key in ('pack_bytes', 'object_count', 'object_bytes')}}
    require(sha(encoded(manifest)) == row['snapshot'], 'home-decision-manifest')
    return scope, row, refs


class HomeDecision:
    """One fixed HTTPS origin with a fresh authoritative decision per call."""

    def __init__(self, home_origin, *, ca_file=None):
        self.home = origin(home_origin)
        self.context = ssl.create_default_context(cafile=ca_file)

    def __call__(self, authorization, project):
        authorization = basic(authorization)
        require(match(UUID, project), 'project-scope')
        deadline = time.monotonic() + 5
        connection = http.client.HTTPSConnection(self.home.hostname, self.home.port, context=self.context, timeout=5)
        try:
            connection.request('GET', f'/stead/git/{project}.git/stead-snapshot', headers={
                'Authorization': authorization, 'Accept': 'application/json',
                'Host': self.home.netloc, 'Accept-Encoding': 'identity', 'Connection': 'close',
                'Cache-Control': 'no-store',
            })
            with connection.getresponse() as result:
                if result.status == 401:
                    raise Denied('git-credential-denied')
                require(result.status == 200 and result.getheader('Content-Type', '').split(';')[0] == 'application/json'
                        and result.getheader('Content-Encoding', 'identity') == 'identity', 'home-decision-unavailable')
                length = result.getheader('Content-Length', '')
                if length:
                    require(re.fullmatch(r'[1-9][0-9]{0,5}', length) and int(length) <= MAX_DECISION,
                            'home-decision-bound')
                raw = bytearray()
                while True:
                    remaining = deadline - time.monotonic()
                    require(remaining > 0, 'home-decision-timeout')
                    if connection.sock:
                        connection.sock.settimeout(remaining)
                    chunk = result.read1(min(65_536, MAX_DECISION + 1 - len(raw)))
                    require(time.monotonic() < deadline, 'home-decision-timeout')
                    if not chunk:
                        break
                    raw.extend(chunk)
                    require(len(raw) <= MAX_DECISION, 'home-decision-bound')
                require(not length or len(raw) == int(length), 'home-decision-bound')
                return decision(bytes(raw), project)
        except (OSError, http.client.HTTPException):
            raise RecoveryError('home-decision-unavailable') from None
        finally:
            connection.close()


class ReadApplication:
    """WSGI adapter; mount behind an HTTPS ingress with request and time limits.

    Ingress must reject duplicate headers and ambiguous request framing, preserve
    the configured host, enforce worker and write deadlines, and route only
    canonical HTTPS requests here. Do not route browser requests or serve the
    pack store as static files. The Home must be a trusted controlled origin.
    """

    def __init__(self, git_origin, decide, storage, binary, *, jobs=1):
        configured = origin(git_origin)
        self.authorities = {configured.netloc}
        if configured.port in (None, 443):
            self.authorities.update((configured.hostname, f'{configured.hostname}:443'))
        self.decide = decide
        self.storage = storage
        self.binary = binary
        require(type(jobs) is int and 1 <= jobs <= 4, 'upload-pack-concurrency')
        self.slots = BoundedSemaphore(jobs)

    def __call__(self, environ, start_response):
        def refused(status):
            headers = [('Cache-Control', 'no-store'), ('Content-Length', '0')]
            if status == '401 Unauthorized':
                headers.append(('WWW-Authenticate', 'Basic realm="Stead Git"'))
            start_response(status, headers)
            return ()

        if (environ.get('wsgi.url_scheme') != 'https' or environ.get('HTTP_HOST') not in self.authorities
                or any(environ.get(key) for key in ('HTTP_COOKIE', 'HTTP_X_STEAD_CSRF', 'HTTP_TRANSFER_ENCODING',
                                                   'HTTP_CONTENT_ENCODING', 'HTTP_ORIGIN', 'SCRIPT_NAME'))):
            return refused('400 Bad Request')
        path = PATH.fullmatch(environ.get('PATH_INFO', ''))
        if path is None or not match(UUID, path[1]):
            return refused('404 Not Found')
        operation = 'advertise' if path[2] == 'info/refs' else 'fetch'
        method, query = (environ.get(key, '') for key in ('REQUEST_METHOD', 'QUERY_STRING'))
        length = environ.get('CONTENT_LENGTH', '')
        if operation == 'advertise':
            if method != 'GET' or query != 'service=git-upload-pack' or length not in ('', '0'):
                return refused('400 Bad Request')
        elif (method != 'POST' or query or environ.get('CONTENT_TYPE') != FETCH_TYPE
              or not re.fullmatch(r'[1-9][0-9]{0,4}', length) or int(length) > MAX_REQUEST):
            return refused('400 Bad Request')
        try:
            authorization = basic(environ.get('HTTP_AUTHORIZATION'))
        except Denied:
            return refused('401 Unauthorized')
        return self._body(environ, start_response, refused, authorization, path[1], operation, length)

    def _body(self, environ, start_response, refused, authorization, project, operation, length):
        # This iterator owns the slot and private spool across delivery. WSGI
        # servers must close it on a client disconnect.
        def authorize():
            return self.decide(authorization, project)

        if not self.slots.acquire(blocking=False):
            yield from refused('503 Service Unavailable')
            return
        try:
            body = b'' if operation == 'advertise' else environ['wsgi.input'].read(int(length))
            if operation == 'fetch' and len(body) != int(length):
                yield from refused('400 Bad Request')
                return
            worker = authorized_response(authorize, project, self.storage, self.binary, operation, body)
            try:
                mime, count, spool = worker.__enter__()
            except Denied:
                yield from refused('401 Unauthorized')
                return
            except (RecoveryError, OSError, subprocess.SubprocessError):
                yield from refused('503 Service Unavailable')
                return
            try:
                start_response('200 OK', [('Content-Type', mime), ('Content-Length', str(count)),
                                          ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')])
                while block := spool.read(65_536):
                    yield block
            finally:
                worker.__exit__(None, None, None)
        finally:
            self.slots.release()

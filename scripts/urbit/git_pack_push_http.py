"""Opt-in private Smart HTTP receive endpoint for an authenticated Home."""
import base64
import re
import subprocess
from threading import BoundedSemaphore
import time

from git_pack_http import Denied, MAX_DECISION, basic, decision
from git_pack_receive import MAX_WIRE
from git_pack_receive_adapter import CAPABILITIES, MAX_SECONDS, Rejected, packet, receive_push, within
from portable_code import ref_name
from portable_recovery import UUID, RecoveryError, decoded, encoded, match, origin, require


PATH = re.compile(r'/stead/git/([0-9a-z-]{36})\.git/(info/refs|git-receive-pack)')
LENGTH = re.compile(r'[1-9][0-9]{0,6}')
MIME = 'application/x-git-receive-pack-'
SERVICE = packet(b'# service=git-receive-pack\n') + b'0000'
ORDERED_CAPABILITIES = b'report-status atomic ofs-delta object-format=sha1'
assert frozenset(ORDERED_CAPABILITIES.split()) == CAPABILITIES


def advertisement(raw, project):
    """Build readable pkt-lines from the selected exact writable snapshot."""
    parsed = decoded(raw, MAX_DECISION)
    require(encoded(parsed)[:-1] == raw, 'push-advertisement-canonical')
    _, _, refs = decision(raw, project)
    listed = sorted((ref_name(name), oid.encode('ascii')) for name, oid in refs.items())
    require(all(oid != b'0' * 40 for _, oid in listed), 'push-advertisement-oid')
    suffix = b'\0' + ORDERED_CAPABILITIES
    lines = []
    for name, oid in listed:
        # Stock receive-pack lists updateable names, with no synthetic HEAD.
        # Annotated tags retain their tag object identity.
        lines.append(packet(oid + b' ' + name + suffix + b'\n'))
        suffix = b''
    return SERVICE + b''.join(lines) + b'0000'


class WriteApplication:
    """Mount only behind a private HTTPS ingress configured for this profile.

    The advertisement callback receives canonical Git Basic auth and a project
    UUID, plus a monotone deadline keyword. It must authorize current write
    access at the selected Home and
    return the canonical decision for that exact accepted repository. The
    separate PushHome must authenticate the same individual at every step.
    Ingress must reject duplicate headers, preserve the exact unescaped target,
    enforce authenticated HTTPS and streaming deadlines, and supply one
    Content-Length framed body. This module opens no listener.
    """

    def __init__(self, git_origin, advertise, home, worker, spool_root, *, jobs=1, clock=None, push_context=None):
        configured = origin(git_origin)
        self.authorities = {configured.netloc}
        if configured.port in (None, 443):
            self.authorities.update((configured.hostname, f'{configured.hostname}:443'))
        require(type(jobs) is int and 1 <= jobs <= 4, 'receive-pack-concurrency')
        self.slots = BoundedSemaphore(jobs)
        self.advertise = advertise
        self.home = home
        self.worker = worker
        self.spool_root = spool_root
        self.clock = clock
        self.push_context = push_context

    @classmethod
    def private_relay(cls, git_origin, relay, signed_worker, spool_root, *, jobs=1):
        def context():
            push = relay.push(signed_worker)
            return push, push

        return cls(git_origin, relay.advertise, None, None, spool_root, jobs=jobs,
                   clock=relay.clock, push_context=context)

    def __call__(self, environ, start_response):
        def refused(status):
            headers = [('Cache-Control', 'no-store'), ('Content-Length', '0')]
            if status == '401 Unauthorized':
                headers.append(('WWW-Authenticate', 'Basic realm="Stead Git"'))
            start_response(status, headers)
            return ()

        if (environ.get('wsgi.url_scheme') != 'https' or environ.get('HTTP_HOST') not in self.authorities
                or environ.get('SCRIPT_NAME', '') != ''
                or any(key in environ for key in ('HTTP_COOKIE', 'HTTP_X_STEAD_CSRF', 'HTTP_TRANSFER_ENCODING',
                                                  'HTTP_CONTENT_ENCODING', 'HTTP_ORIGIN'))):
            return refused('400 Bad Request')
        path = PATH.fullmatch(environ.get('PATH_INFO', ''))
        if path is None or not match(UUID, path[1]):
            return refused('404 Not Found')
        discovery = path[2] == 'info/refs'
        method, query, length, content_type = (
            environ.get(key, '') for key in ('REQUEST_METHOD', 'QUERY_STRING', 'CONTENT_LENGTH', 'CONTENT_TYPE'))
        if discovery:
            if method != 'GET' or query != 'service=git-receive-pack' or length not in ('', '0') or content_type:
                return refused('400 Bad Request')
        elif (method != 'POST' or query or content_type != MIME + 'request'
              or not match(LENGTH, length)
              or int(length) > MAX_WIRE or 'wsgi.input' not in environ):
            return refused('400 Bad Request')
        try:
            authorization = basic(environ.get('HTTP_AUTHORIZATION'))
        except Denied:
            return refused('401 Unauthorized')
        if not self.slots.acquire(blocking=False):
            return refused('503 Service Unavailable')
        try:
            deadline = time.monotonic() + MAX_SECONDS
            if discovery:
                raw = self.advertise(authorization, path[1], deadline=deadline)
                within(deadline)
                response = advertisement(raw, path[1])
            else:
                bearer = base64.b64decode(authorization[6:])[6:].decode('ascii')
                home, worker = (self.home, self.worker) if self.push_context is None else self.push_context()
                response = receive_push(home, worker, self.spool_root, path[1], bearer,
                                        environ['wsgi.input'], int(length), deadline=deadline, clock=self.clock)
            within(deadline)
        except Denied:
            return refused('401 Unauthorized')
        except Rejected:
            return refused('403 Forbidden')
        except (RecoveryError, OSError, subprocess.SubprocessError):
            return refused('503 Service Unavailable')
        finally:
            self.slots.release()

        subtype = 'advertisement' if discovery else 'result'
        start_response('200 OK', [('Content-Type', MIME + subtype), ('Content-Length', str(len(response))),
                                  ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')])
        return (response,)

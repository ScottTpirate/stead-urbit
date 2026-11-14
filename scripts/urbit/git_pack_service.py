"""Mount one private project behind an operator-owned HTTPS ingress.

Fetches use the supplied fresh Home read decision and a relay-owned accepted
snapshot copy. Pushes use the pinned Home relay and the verifier's private
Unix socket. Publish each accepted snapshot to the read store by its digest;
the strict storage ownership checks require separate read and write stores.

Ingress must supply authenticated HTTPS metadata, reject duplicate or
ambiguous framing, preserve the exact target, bind the body to Content-Length,
enforce upload and response timeouts, and close disconnected WSGI iterators.
This mount only serves the four Smart HTTP operations for the configured
project. It opens no listener and provides no fallback or forwarding route.
"""
from __future__ import annotations

import os
from pathlib import Path
import re

from git_pack_http import FETCH_TYPE, ReadApplication
from git_pack_push_http import MIME, WriteApplication
from git_pack_receive import MAX_WIRE
from git_pack_relay import Relay
from git_pack_upload import MAX_REQUEST
import git_pack_worker_socket as worker
from portable_recovery import UUID, match, require


LENGTH = re.compile(r'[1-9][0-9]{0,6}')
FORBIDDEN = ('HTTP_COOKIE', 'HTTP_COOKIE2', 'HTTP_X_STEAD_CSRF', 'HTTP_ORIGIN', 'HTTP_TRANSFER_ENCODING',
             'HTTP_CONTENT_ENCODING', 'HTTP_X_STEAD_RELAY')


def private_mount(git_origin, project, decide, read_storage, git, relay, spool_root, worker_socket,
                  worker_uid, relay_uid, *, fetch_limit=MAX_REQUEST, push_limit=MAX_WIRE,
                  read_jobs=1, write_jobs=1):
    """Build a WSGI application with fixed project, dependencies and limits."""
    require(match(UUID, project) and callable(decide) and isinstance(relay, Relay), 'pack-service-config')
    require(type(fetch_limit) is int and 0 < fetch_limit <= MAX_REQUEST
            and type(push_limit) is int and 0 < push_limit <= MAX_WIRE, 'pack-service-limit')
    worker.identities(relay_uid, worker_uid)
    read_storage, git, spool_root, worker_socket = map(Path, (read_storage, git, spool_root, worker_socket))
    require(all(path.is_absolute() for path in (read_storage, git, spool_root, worker_socket))
            and read_storage != spool_root and 0 < len(os.fsencode(worker_socket)) <= 107,
            'pack-service-path')

    def signed_worker(admitted, path, deadline):
        return worker.request(worker_socket, worker_uid, relay_uid, admitted, path, deadline, clock=relay.clock)

    read = ReadApplication(git_origin, decide, read_storage, git, jobs=read_jobs)
    write = WriteApplication.private_relay(git_origin, relay, signed_worker, spool_root, jobs=write_jobs)
    base = f'/stead/git/{project}.git'
    discovery = base + '/info/refs'
    fetch = base + '/git-upload-pack'
    push = base + '/git-receive-pack'
    services = {'service=git-upload-pack': read, 'service=git-receive-pack': write}
    uploads = {fetch: (read, FETCH_TYPE, fetch_limit), push: (write, MIME + 'request', push_limit)}

    def application(environ, start_response):
        def refuse(status):
            start_response(status, [('Cache-Control', 'no-store'), ('Content-Length', '0')])
            return ()

        path = environ.get('PATH_INFO', '')
        if path not in (discovery, fetch, push):
            return refuse('404 Not Found')
        method = environ.get('REQUEST_METHOD')
        query = environ.get('QUERY_STRING', '')
        length = environ.get('CONTENT_LENGTH', '')
        mime = environ.get('CONTENT_TYPE', '')
        if (environ.get('SCRIPT_NAME', '') != '' or any(name in environ for name in FORBIDDEN)
                or environ.get('wsgi.url_scheme') != 'https' or environ.get('HTTP_HOST') not in read.authorities):
            return refuse('400 Bad Request')
        if path == discovery:
            if method != 'GET' or query not in services or length not in ('', '0') or mime:
                return refuse('400 Bad Request')
            selected = services[query]
        else:
            selected, expected_mime, limit = uploads[path]
            if (method != 'POST' or query != '' or mime != expected_mime or not match(LENGTH, length)
                    or int(length) > limit or not callable(getattr(environ.get('wsgi.input'), 'read', None))):
                return refuse('400 Bad Request')
        target = path + ('?' + query if query else '')
        if any(name in environ and environ[name] != target for name in ('RAW_URI', 'REQUEST_URI')):
            return refuse('400 Bad Request')
        return selected(environ, start_response)

    return application

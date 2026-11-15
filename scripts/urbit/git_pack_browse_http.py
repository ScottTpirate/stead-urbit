"""Serve bounded repository reads for one fixed project using Home browser sessions."""
import re
from threading import BoundedSemaphore
import time

import git_pack_browse
import git_pack_changes
from git_pack_http import Denied
from portable_recovery import RecoveryError, TOKEN, decoded, encoded, match


PATH = '/stead/api/code/browse'
SESSION_COOKIE = '__Host-stead-session'
LENGTH = re.compile(r'[1-9][0-9]{0,3}')
COOKIE = re.compile(r'[\x20-\x7e]{1,4096}')
DENIALS = {'session_required': '401 Unauthorized', 'invalid_csrf': '403 Forbidden',
           'denied_or_not_found': '404 Not Found', 'stale_selection': '409 Conflict'}
STALE = {'accepted-pack-required', 'home-acceptance-changed', 'changes-revision-changed'}
NOT_FOUND = {'browse-ref', 'browse-path-unavailable', 'changes-path-unavailable', 'changes-proposal-unavailable'}


def session_from(cookies):
    if not match(COOKIE, cookies) or ',' in cookies:
        return None
    values = [value for item in cookies.split(';') for name, _, value in [item.strip().partition('=')]
              if name.strip() == SESSION_COOKIE]
    return values[0] if len(values) == 1 and match(TOKEN, values[0]) else None


def reply(start_response, status, value):
    body = encoded(value)
    start_response(status, [('Content-Type', 'application/json'), ('Content-Length', str(len(body))),
                            ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
                            ('Cross-Origin-Resource-Policy', 'same-origin')])
    return [body]


def mount(relay, project, read_store, reader):
    capacity = BoundedSemaphore(1)

    def application(environ, start_response):
        changes = environ.get('PATH_INFO') == git_pack_changes.PATH
        handler = git_pack_changes if changes else git_pack_browse
        prefix = 'changes' if changes else 'browse'
        def error(status, reason):
            return reply(start_response, status, {'error': reason})

        if (environ.get('PATH_INFO') not in (PATH, git_pack_changes.PATH) or environ.get('QUERY_STRING')
                or environ.get('REQUEST_METHOD') != 'POST' or environ.get('CONTENT_TYPE') != 'application/json'
                or environ.get('HTTP_HOST') != relay.origin.netloc
                or any(environ.get(key) for key in ('HTTP_AUTHORIZATION', 'HTTP_X_STEAD_RELAY',
                                                    'HTTP_TRANSFER_ENCODING', 'HTTP_CONTENT_ENCODING'))):
            return error('400 Bad Request', 'invalid_request')
        if environ.get('HTTP_ORIGIN') != relay.origin.geturl():
            return error('403 Forbidden', 'invalid_csrf')
        csrf = environ.get('HTTP_X_STEAD_CSRF', '')
        if not match(TOKEN, csrf):
            return error('403 Forbidden', 'invalid_csrf')
        session = session_from(environ.get('HTTP_COOKIE', ''))
        if session is None:
            return error('401 Unauthorized', 'session_required')
        length = environ.get('CONTENT_LENGTH', '')
        if not match(LENGTH, length) or int(length) > handler.MAX_REQUEST:
            return error('400 Bad Request', 'invalid_request')
        if not capacity.acquire(blocking=False):
            return error('503 Service Unavailable', prefix + '_busy')
        try:
            try:
                raw = environ['wsgi.input'].read(int(length))
                if len(raw) != int(length):
                    return error('400 Bad Request', 'invalid_request')
                request = decoded(raw, handler.MAX_REQUEST)
                handler.request_path(request)
            except (OSError, ValueError):
                return error('400 Bad Request', 'invalid_request')
            if request['project_id'] != project:
                return error('404 Not Found', 'denied_or_not_found')

            deadline = time.monotonic() + 12

            def authorize():
                pack = relay.browser_pack_view(project, session, csrf, deadline)
                if not changes:
                    return pack
                proposal = relay.browser_external_proposal(project, request['proposal_id'], session, csrf, deadline)
                return pack, proposal

            try:
                read = git_pack_changes.changes if changes else git_pack_browse.browse
                value = read(authorize, relay.home_ship, request, read_store, reader, deadline=deadline)
            except Denied as exc:
                reason = str(exc)
                return error(DENIALS.get(reason, '404 Not Found'), reason if reason in DENIALS else 'denied_or_not_found')
            except RecoveryError as exc:
                if str(exc) in STALE:
                    return error('409 Conflict', 'stale_selection')
                if str(exc) in NOT_FOUND:
                    return error('404 Not Found', 'denied_or_not_found')
                if str(exc) == 'changes-metadata-bound':
                    return error('422 Unprocessable Content', 'changes_too_large')
                return error('503 Service Unavailable', prefix + '_unavailable')
            except OSError:
                return error('503 Service Unavailable', prefix + '_unavailable')
            return reply(start_response, '200 OK', value)
        finally:
            capacity.release()

    return application

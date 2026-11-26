#!/usr/bin/env python3
"""Render a reviewed TLS edge profile for one Stead Home and Git project."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import ipaddress
import json
from pathlib import Path
import re
import sys

from git_pack_browse import MAX_REQUEST as MAX_BROWSE
from git_pack_browse_http import PATH as BROWSE_PATH
from git_pack_changes import PATH as CHANGES_PATH
from git_pack_http import FETCH_TYPE
from git_pack_push_http import MIME
from git_pack_receive import MAX_WIRE
from git_pack_upload import MAX_REQUEST
from portable_recovery import UUID, match, require


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_release import frontend  # noqa: E402

HOME_POSTS = tuple('/stead/' + route for route in (
    'auth/start', 'auth/status', 'auth/consume', 'auth/logout', 'auth/resume',
    'api/capabilities', 'api/command', 'api/query', 'api/updates', 'api/code',
))
LABEL = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?')
FILE = re.compile(r'/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*')


@dataclass(frozen=True)
class Profile:
    hostname: str
    public_port: int
    listen_ipv4: str
    home_port: int
    git_socket: Path
    project: str
    certificate: Path
    key: Path
    home_ca: Path
    origin_port: int | None = None


def exact_profile(profile):
    host = profile.hostname
    labels = host.split('.')
    require(0 < len(host) <= 253 and len(labels) >= 2 and all(match(LABEL, name) for name in labels)
            and not labels[-1].isdigit(), 'edge-hostname')
    address = ipaddress.IPv4Address(profile.listen_ipv4)
    require(not address.is_multicast and not address.is_unspecified, 'edge-listen-address')
    ports = (profile.public_port, profile.home_port)
    require(len(set(ports)) == 2 and type(ports[0]) is int and (ports[0] == 443 or 1024 <= ports[0] <= 65_535)
            and type(ports[1]) is int and 1024 <= ports[1] <= 65_535, 'edge-port')
    if profile.origin_port is not None:
        require(address.is_loopback and type(profile.origin_port) is int
                and (profile.origin_port == 443 or 1024 <= profile.origin_port <= 65_535), 'edge-private-origin-port')
    require(match(UUID, profile.project), 'edge-project')
    for item in (profile.certificate, profile.key, profile.home_ca, profile.git_socket):
        require(match(FILE, str(item)) and all(part not in ('.', '..') for part in item.parts[1:]), 'edge-file-path')
    require(len({profile.certificate, profile.key, profile.home_ca}) == 3, 'edge-distinct-tls-files')
    require(len(str(profile.git_socket)) <= 107 and profile.git_socket not in (profile.certificate, profile.key, profile.home_ca),
            'edge-git-socket')


def asset_routes(desk):
    _, raw = frontend(lambda name: (desk / name).read_bytes())
    return tuple(sorted(row['route'] for row in json.loads(raw)['routes'] if row['route'].startswith('/stead/')))


def route(method, target, authority, mime, body):
    # Exact raw URI, original request-line target form, TLS SNI and Host are
    # checked independently; case-insensitive literal map keys would be wrong.
    prefix = re.escape('|'.join((method, target, authority, mime)) + '|')
    return f'"~^{prefix}{body}\\|0$"'


def positive_length(maximum):
    # Match canonical positive wire lengths before any upstream is selected.
    # nginx's named-location jump can bypass a location-only body-size check.
    digits = str(maximum)
    shorter = f'[1-9][0-9]{{0,{len(digits) - 2}}}'
    terms = [shorter, digits]
    for index, digit in enumerate(digits):
        minimum = 1 if index == 0 else 0
        if int(digit) > minimum:
            remaining = len(digits) - index - 1
            tail = f'[0-9]{{{remaining}}}' if remaining else ''
            terms.append(digits[:index] + f'[{minimum}-{int(digit) - 1}]' + tail)
    return '(?:' + '|'.join(terms) + ')'


def git_metadata_guard():
    # nginx combines repeated generic headers with a comma. Reject ambiguous
    # Authorization before handing its value to the WSGI adapter's Basic parser.
    return [
        '        if ($stead_git_authorization = 0) { return 400; }',
        '        if ($stead_git_foreign) { return 400; }',
    ]


def target_location(name, *, address, authority, maximum, timeout, tls_name=None, tls_ca=None, headers=(), git=False):
    lines = [f'    location @{name} {{', *(git_metadata_guard() if git else []), f'        client_max_body_size {maximum};',
             '        proxy_http_version 1.1;', '        proxy_pass_request_headers off;',
             '        proxy_request_buffering on;', '        proxy_buffering off;', '        proxy_next_upstream off;',
             '        proxy_redirect off;', '        proxy_connect_timeout 5s;', '        proxy_send_timeout 15s;',
             f'        proxy_read_timeout {timeout}s;', '        proxy_set_header Connection close;',
             f'        proxy_set_header Host "{authority}";',
             '        proxy_set_header Content-Length $content_length;', '        proxy_set_header Content-Type $http_content_type;',
             '        proxy_set_header Transfer-Encoding "";']
    if tls_name:
        lines.extend(['        proxy_ssl_server_name on;', f'        proxy_ssl_name {tls_name};', '        proxy_ssl_verify on;',
                      '        proxy_ssl_verify_depth 3;', f'        proxy_ssl_trusted_certificate {tls_ca};',
                      '        proxy_ssl_protocols TLSv1.2 TLSv1.3;'])
    lines.extend(f'        proxy_set_header {key} {value};' for key, value in headers)
    return '\n'.join([*lines, f'        proxy_pass {address};', '    }'])


def render(profile: Profile, desk: Path) -> str:
    """Render an http-context include. It performs no setup or listener changes."""
    exact_profile(profile)
    host = profile.hostname
    origin_port = profile.public_port if profile.origin_port is None else profile.origin_port
    host_header = f'{host}:{origin_port}' if origin_port != 443 else host
    authority = host_header + '|' + host
    base = f'/stead/git/{profile.project}.git'
    get = '(?:0)?'
    bare_home = re.escape('|' + authority + '||') + get + r'\|0$'
    entries = [(route('GET', path, authority, '', get), '421') for path in asset_routes(desk)]
    entries += [(route('POST', path, authority, 'application/json', positive_length(65_536)), '421') for path in HOME_POSTS]
    entries += [(route('GET', base + '/info/refs?service=git-' + name + '-pack', authority, '', get), '422')
                for name in ('upload', 'receive')]
    entries += [(route('POST', base + '/git-upload-pack', authority, FETCH_TYPE, positive_length(MAX_REQUEST)), '423'),
                (route('POST', base + '/git-receive-pack', authority, MIME + 'request', positive_length(MAX_WIRE)), '424'),
                (route('POST', BROWSE_PATH, authority, 'application/json', positive_length(MAX_BROWSE)), '425'),
                (route('POST', CHANGES_PATH, authority, 'application/json', positive_length(MAX_BROWSE)), '425')]
    rows = '\n'.join(f'    {test} {value};' for test, value in entries)
    common = [('Authorization', '$http_authorization'), ('Git-Protocol', '$http_git_protocol'),
              ('X-Forwarded-Proto', 'https'), ('X-Stead-Edge-Target', '$request_uri')]
    browser_headers = (('Cookie', '$http_cookie'), ('X-Stead-CSRF', '$http_x_stead_csrf'), ('Origin', '$http_origin'))
    home = target_location('stead_browser', address=f'https://127.0.0.1:{profile.home_port}', authority=host_header,
                           maximum=65_536, timeout=30, tls_name=host, tls_ca=profile.home_ca, headers=browser_headers)
    browse = target_location('stead_browse', address=f'http://unix:{profile.git_socket}:', authority=host_header,
                             maximum=MAX_BROWSE, timeout=14, headers=(*browser_headers, *common[2:]))
    git = '\n'.join(target_location(name, address=f'http://unix:{profile.git_socket}:', authority=host_header,
                                    maximum=maximum, timeout=65, headers=common, git=True)
                    for name, maximum in (('stead_discover', '1'), ('stead_fetch', MAX_REQUEST), ('stead_push', MAX_WIRE)))
    return f'''# Generated by git_pack_edge.py for explicit activation in nginx's http context.
# Public TLS terminates here. Browser requests use separately verified native TLS.
map $request $stead_exact_request_line {{
    default 0;
    "~^(GET|POST) /[!-~]+ HTTP/1[.]1$" 1;
}}
map "$http_transfer_encoding|$http_content_encoding|$http_expect|$http_upgrade|$http_te|$http_trailer" $stead_http_encoding {{
    default 1;
    "|||||" 0;
}}
map "$request|$http_host|$ssl_server_name|$http_content_type|$content_length|$stead_http_encoding" $stead_bare_home {{
    default 0;
    "~^(?:GET|HEAD) / HTTP/1[.]1{bare_home}" 1;
}}
map "$request_method|$request_uri|$http_host|$ssl_server_name|$http_content_type|$content_length|$stead_http_encoding" $stead_edge_route {{
    default 404;
{rows}
}}
map $http_authorization $stead_git_authorization {{
    default 0;
    "" 1;
    # A username in the URL can make stock Git probe with an empty password.
    # Pass just that shape through to the relay's ordinary 401 challenge.
    "~^Basic c3RlYWQ6$" 1;
    "~^Basic [A-Za-z0-9+/]{{94}}==$" 1;
}}
map "$http_cookie|$http_cookie2|$http_x_stead_csrf|$http_origin" $stead_git_foreign {{
    default 1;
    "|||" 0;
}}
server {{
    listen {profile.listen_ipv4}:{profile.public_port} ssl default_server;
    server_name {host};
    ssl_certificate {profile.certificate};
    ssl_certificate_key {profile.key};
    ssl_protocols TLSv1.2 TLSv1.3;
    access_log off;
    error_log /dev/null;
    server_tokens off;
    client_header_timeout 5s;
    client_body_timeout 15s;
    send_timeout 15s;
    keepalive_timeout 0;
    client_header_buffer_size 1k;
    large_client_header_buffers 2 8k;
    client_max_body_size {MAX_WIRE};
    error_page 421 = @stead_browser;
    error_page 422 = @stead_discover;
    error_page 423 = @stead_fetch;
    error_page 424 = @stead_push;
    error_page 425 = @stead_browse;
    location / {{
        absolute_redirect off;
        if ($stead_bare_home) {{ return 302 /stead/; }}
        if ($stead_exact_request_line = 0) {{ return 400; }}
        if ($stead_http_encoding) {{ return 400; }}
        if ($stead_edge_route = 421) {{ return 421; }}
        if ($stead_edge_route = 422) {{ return 422; }}
        if ($stead_edge_route = 423) {{ return 423; }}
        if ($stead_edge_route = 424) {{ return 424; }}
        if ($stead_edge_route = 425) {{ return 425; }}
        return 404;
    }}
{home}
{browse}
{git}
}}
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('hostname', 'listen-ipv4', 'project'):
        parser.add_argument('--' + name, required=True)
    for name in ('public-port', 'home-port'):
        parser.add_argument('--' + name, required=True, type=int)
    parser.add_argument('--origin-port', type=int, help='Retain the canonical HTTPS port behind a private tunnel')
    for name in ('certificate', 'key', 'home-ca', 'git-socket', 'desk'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = vars(parser.parse_args(argv))
    desk = args.pop('desk')
    try:
        print(render(Profile(**args), desk), end='')
    except (OSError, UnicodeError, ValueError):
        parser.exit(1, 'The selected Stead edge profile or verified desk is invalid.\n')


if __name__ == '__main__':
    main()

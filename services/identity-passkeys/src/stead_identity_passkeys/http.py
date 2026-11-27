"""A same-origin JSON API served behind the planet's existing TLS proxy."""
import argparse
import fcntl
import json
import os
import sqlite3
import stat
import struct
from pathlib import Path

from waitress import serve

from .bridge import LocalIdentity, Rejected, Unavailable
from .verifier import Verifier


PREFIX = "/stead-identity/passkeys/"
LIMIT = 65536
ROUTES = {"register/begin", "register/finish", "authenticate/begin", "authenticate/finish", "list", "revoke"}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("duplicate field")
        result[key] = value
    return result


def application(service):
    def handle(env, start_response):
        try:
            route = env.get("PATH_INFO", "").removeprefix(PREFIX)
            if env.get("PATH_INFO") != PREFIX + route or route not in ROUTES:
                status, value = "404 Not Found", {"error": "not_found"}
            elif (env.get("REQUEST_METHOD") != "POST" or env.get("HTTP_HOST") != service.origin[8:]
                  or env.get("HTTP_ORIGIN") != service.origin or env.get("QUERY_STRING")
                  or env.get("CONTENT_TYPE") != "application/json"
                  or env.get("HTTP_SEC_FETCH_SITE", "same-origin") != "same-origin"):
                status, value = "403 Forbidden", {"error": "invalid_request"}
            else:
                length = int(env.get("CONTENT_LENGTH") or 0)
                if not 0 < length <= LIMIT:
                    raise Rejected("invalid content length")
                payload = env["wsgi.input"].read(length)
                if len(payload) != length:
                    raise Rejected("short request")
                body = json.loads(payload.decode("utf-8"), object_pairs_hook=unique)
                value = service.dispatch(route, body)
                status = "200 OK"
        except (ValueError, KeyError, IndexError, TypeError, OverflowError, RecursionError,
                AssertionError, struct.error):
            # FIDO parsers consume untrusted CBOR, JSON and binary data. Keep
            # protocol details and credential identifiers out of error reports.
            status, value = "400 Bad Request", {"error": "request_declined"}
        except (Unavailable, sqlite3.Error):
            status, value = "503 Service Unavailable", {"error": "identity_unavailable"}
        data = json.dumps(value, separators=(",", ":")).encode()
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(data))),
                                ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                                ("X-Content-Type-Options", "nosniff"), ("Cross-Origin-Resource-Policy", "same-origin"),
                                ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")])
        return [data]
    return handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Exact canonical HTTPS Identity origin")
    parser.add_argument("--planet", required=True)
    parser.add_argument("--eyre-tls-port", required=True, type=int)
    parser.add_argument("--eyre-ca", type=Path, help="Private CA bundle if Eyre uses private TLS")
    parser.add_argument("--secret-file", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8791, help="Local reverse proxy upstream port")
    args = parser.parse_args()
    if not all(0 < p <= 65535 for p in (args.port, args.eyre_tls_port)):
        parser.error("ports must be in range")
    os.umask(0o077)
    mode = args.secret_file.stat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        parser.error("bridge secret file must be private (0400 or 0600)")
    if args.database.parent.stat().st_mode & 0o077:
        parser.error("database requires its own private directory (0700)")
    bridge = LocalIdentity(args.origin, args.eyre_tls_port, args.secret_file.read_text().strip(), args.eyre_ca)
    with open(str(args.database) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verifier = Verifier(args.database, args.planet, args.origin, bridge)
        serve(application(verifier), host="127.0.0.1", port=args.port, threads=4,
              connection_limit=32, channel_timeout=15, cleanup_interval=5, max_request_body_size=LIMIT,
              max_request_header_size=8192, clear_untrusted_proxy_headers=True, expose_tracebacks=False)


if __name__ == "__main__":
    main()

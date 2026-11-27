"""Point-to-point TLS to the Identity agent. Never send a browser cookie."""
import http.client
import json
import re
import socket
import ssl
from urllib.parse import urlsplit


class Rejected(ValueError):
    """An invalid, stale or unauthorized request."""


class Unavailable(RuntimeError):
    """Transport or service unavailable."""


TOKEN = re.compile(r"[0-9a-f]{64}")
SHIP = re.compile(r"~[a-z-]{3,80}")
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def origin_host(origin, *, relying_party=True):
    if not isinstance(origin, str) or len(origin) > 256:
        raise ValueError("invalid HTTPS origin")
    url = urlsplit(origin)
    host = url.hostname or ""
    labels = host.split(".")
    if (not all(DNS_LABEL.fullmatch(s) for s in labels) or url.scheme != "https"
            or (relying_party and (len(labels) < 2 or labels[-1].isdigit()))):
        raise ValueError("invalid Identity hostname")
    port = url.port
    canonical = "https://" + host + (f":{port}" if port and port != 443 else "")
    if origin != canonical:
        raise ValueError("origin must be canonical and exact")
    return host


class LocalIdentity:
    def __init__(self, origin, port, secret, ca_file=None):
        self.origin = origin
        self.host = origin_host(origin)
        if not TOKEN.fullmatch(secret):
            raise ValueError("invalid bridge secret")
        self.secret = secret
        self.port = port
        self.tls = ssl.create_default_context(cafile=ca_file)

    def __call__(self, action, challenge_id, ticket=""):
        payload = json.dumps({
            "protocol": "stead.passkey-bridge/1", "secret": self.secret,
            "action": action, "challenge_id": challenge_id, "ticket": ticket,
        }).encode()
        # The host header and TLS SNI refer to the Identity origin. Network
        # traffic goes only to the operator-configured local Eyre TLS port.
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=4) as sock:
                with self.tls.wrap_socket(sock, server_hostname=self.host) as secured:
                    conn = http.client.HTTPConnection(self.host, timeout=4)
                    conn.sock = secured
                    try:
                        conn.request("POST", "/stead-identity/api/verifier", body=payload,
                                     headers={"Host": self.origin[8:], "Origin": self.origin,
                                              "Content-Type": "application/json"})
                        reply = conn.getresponse()
                        if 400 <= reply.status < 500:
                            raise Rejected("Identity declined the request")
                        body = reply.read(4097)
                        if (reply.status != 200 or len(body) > 4096
                                or reply.getheader("Content-Type", "").split(";")[0] != "application/json"):
                            raise Unavailable("Identity unavailable")
                        result = json.loads(body)
                    finally:
                        conn.close()
        except (OSError, http.client.HTTPException, json.JSONDecodeError, UnicodeError) as error:
            raise Unavailable("Identity unavailable") from error
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise Rejected("Identity declined the request")
        return result

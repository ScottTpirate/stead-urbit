"""WebAuthn ceremonies for one planet and one exact Identity origin."""
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from fido2.server import Fido2Server
from fido2.utils import websafe_encode
from fido2.webauthn import (AttestedCredentialData, AuthenticationResponse,
                            PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity,
                            RegistrationResponse, ResidentKeyRequirement, UserVerificationRequirement)

from .bridge import Rejected, SHIP, TOKEN, Unavailable, origin_host


def fields(body, required, optional=()):
    if not isinstance(body, dict) or not set(required) <= body.keys() <= set(required) | set(optional):
        raise Rejected("invalid fields")


def token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise Rejected("invalid token")
    return value


class Verifier:
    MAX_KEYS = 16
    MAX_PENDING = 64
    TTL = 120

    def __init__(self, path, planet, origin, bridge, clock=time.time):
        if not SHIP.fullmatch(planet):
            raise ValueError("invalid planet")
        self.path, self.planet, self.origin, self.bridge, self.clock = path, planet, origin, bridge, clock
        rp = PublicKeyCredentialRpEntity(id=origin_host(origin), name="Stead Identity")
        self.fido = Fido2Server(rp, verify_origin=lambda claimed: claimed == self.origin)
        self.fido.timeout = self.TTL * 1000
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS identity(singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                       "planet TEXT NOT NULL, origin TEXT NOT NULL, handle BLOB NOT NULL)")
            db.execute("INSERT OR IGNORE INTO identity VALUES (1,?,?,?)", (planet, origin, secrets.token_bytes(32)))
            binding = db.execute("SELECT planet,origin,handle FROM identity WHERE singleton=1").fetchone()
            if binding[:2] != (planet, origin):
                raise ValueError("credential database belongs to a different Identity")
            self.user = PublicKeyCredentialUserEntity(id=binding[2], name=planet, display_name=planet)
            db.execute("CREATE TABLE IF NOT EXISTS credential(id TEXT PRIMARY KEY, data BLOB NOT NULL, "
                       "counter INTEGER NOT NULL, backup_eligible INTEGER NOT NULL, label TEXT NOT NULL, created TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS ceremony(id TEXT PRIMARY KEY, kind TEXT NOT NULL, "
                       "state TEXT NOT NULL, context TEXT NOT NULL, expires INTEGER NOT NULL)")
            # Single instance per Identity. A restart retires outstanding operations.
            db.execute("DELETE FROM ceremony")

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, isolation_level=None, timeout=6)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        finally:
            db.close()

    def owner(self, body, action):
        result = self.bridge("owner", action, token(body["ticket"]))
        if result.get("planet") != self.planet or result.get("status") != "ok":
            raise Rejected("owner authorization required")

    def native(self, action, challenge):
        result = self.bridge(action, challenge)
        if (result.get("planet") != self.planet or result.get("status") != "ok"
                or result.get("challenge_id") != challenge or not isinstance(result.get("home"), str)
                or not SHIP.fullmatch(result["home"])):
            raise Rejected("native request unavailable")
        if origin_host(result.get("origin"), relying_party=False) == self.fido.rp.id:
            raise Rejected("Home and Identity must have separate hostnames")
        context = {key: result[key] for key in ("home", "origin", "challenge_id")}
        if action == "approve":
            context["return_proof"] = token(result.get("return_proof"))
        return context

    def dispatch(self, route, body):
        if route == "list":
            fields(body, ["ticket"])
            self.owner(body, "list")
            with self.transaction() as db:
                rows = db.execute("SELECT id,label,created FROM credential ORDER BY created,id")
                return {"status": "ok", "credentials": [dict(zip(("id", "label", "created_at"), row)) for row in rows]}
        if route == "revoke":
            fields(body, ["ticket", "id"])
            if not isinstance(body["id"], str) or not 1 <= len(body["id"]) <= 1400:
                raise Rejected("invalid credential")
            self.owner(body, "revoke")
            with self.transaction() as db:
                db.execute("DELETE FROM credential WHERE id=?", (body["id"],))
            return {"status": "ok"}
        if route in ("register/begin", "authenticate/begin"):
            return self.begin(route.split("/")[0], body)
        if route in ("register/finish", "authenticate/finish"):
            return self.finish(route.split("/")[0], body)
        raise Rejected("unknown operation")

    def begin(self, kind, body):
        if kind == "register":
            fields(body, ["ticket"], ["label"])
            label = body.get("label", "Passkey")
            if not isinstance(label, str) or not 1 <= len(label.strip()) <= 64 or not label.isprintable():
                raise Rejected("invalid label")
            self.owner(body, "register")
            context = {"label": label.strip()}
        else:
            fields(body, ["challenge_id"])
            context = self.native("context", token(body["challenge_id"]))
        now = int(self.clock())
        with self.transaction() as db:
            db.execute("DELETE FROM ceremony WHERE expires<=?", (now,))
            if db.execute("SELECT count(*) FROM ceremony").fetchone()[0] >= self.MAX_PENDING:
                raise Unavailable("ceremonies busy")
            keys = [AttestedCredentialData(row[0]) for row in db.execute("SELECT data FROM credential")]
            if kind == "register":
                if len(keys) >= self.MAX_KEYS:
                    raise Rejected("credential limit reached")
                options, state = self.fido.register_begin(
                    self.user, keys, resident_key_requirement=ResidentKeyRequirement.PREFERRED,
                    user_verification=UserVerificationRequirement.REQUIRED)
            else:
                if not keys:
                    raise Rejected("no passkey")
                options, state = self.fido.authenticate_begin(keys, user_verification=UserVerificationRequirement.REQUIRED)
            ceremony = secrets.token_hex(32)
            db.execute("INSERT INTO ceremony VALUES (?,?,?,?,?)",
                       (ceremony, kind, json.dumps(state), json.dumps(context), now + self.TTL))
        return {"status": "ok", "ceremony": ceremony, **dict(options), **(context if kind == "authenticate" else {})}

    def finish(self, kind, body):
        fields(body, ["ceremony", "credential"])
        ceremony = token(body["ceremony"])
        with self.transaction() as db:
            row = db.execute("SELECT state,context FROM ceremony WHERE id=? AND kind=? AND expires>?",
                             (ceremony, kind, int(self.clock()))).fetchone()
            if row is None:
                raise Rejected("ceremony unavailable")
            db.execute("DELETE FROM ceremony WHERE id=?", (ceremony,))
        state, context = map(json.loads, row)
        raw = body["credential"]
        if not isinstance(raw, dict) or raw.get("type") != "public-key" or raw.get("id") != raw.get("rawId"):
            raise Rejected("invalid credential")
        with self.transaction() as db:
            if kind == "register":
                response = RegistrationResponse.from_dict(raw)
                self.top_level(response.response.client_data)
                auth = self.fido.register_complete(state, response)
                key = auth.credential_data
                if (key is None or not 1 <= len(key.credential_id) <= 1023
                        or key.credential_id != response.raw_id
                        or key.public_key.get(3) not in {alg.alg for alg in self.fido.allowed_algorithms}
                        or db.execute("SELECT count(*) FROM credential").fetchone()[0] >= self.MAX_KEYS):
                    raise Rejected("invalid credential")
                if auth.is_backed_up() and not auth.is_backup_eligible():
                    raise Rejected("invalid backup flags")
                created = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="seconds")
                try:
                    db.execute("INSERT INTO credential VALUES (?,?,?,?,?,?)",
                               (websafe_encode(key.credential_id), bytes(key), auth.counter, auth.is_backup_eligible(),
                                context["label"], created))
                except sqlite3.IntegrityError as error:
                    raise Rejected("credential already registered") from error
                return {"status": "ok"}
            response = AuthenticationResponse.from_dict(raw)
            self.top_level(response.response.client_data)
            if response.response.user_handle not in (None, self.user.id):
                raise Rejected("wrong planet")
            found = db.execute("SELECT data,counter,backup_eligible FROM credential WHERE id=?", (response.id,)).fetchone()
            if found is None:
                raise Rejected("credential unavailable")
            self.fido.authenticate_complete(state, [AttestedCredentialData(found[0])], response)
            auth = response.response.authenticator_data
            if (auth.credential_data is not None or auth.is_backup_eligible() != bool(found[2])
                    or (auth.is_backed_up() and not auth.is_backup_eligible())):
                raise Rejected("credential state invalid")
            # Synced copies can have independent counters. A device-bound
            # credential that advertises a counter must continue increasing it.
            if not auth.is_backup_eligible() and (auth.counter or found[1]) and auth.counter <= found[1]:
                raise Rejected("credential state invalid")
            if self.native("context", context["challenge_id"]) != context:
                raise Rejected("native request changed")
            # Serialize delivery with credential removal. The ship retires the
            # pending request and rechecks consent before sending its Gall poke.
            approved = self.native("approve", context["challenge_id"])
            if any(approved[key] != value for key, value in context.items()):
                raise Rejected("native approval mismatch")
            db.execute("UPDATE credential SET counter=? WHERE id=?", (max(found[1], auth.counter), response.id))
            return {"status": "ok", **approved}

    @staticmethod
    def top_level(client):
        if client.cross_origin is not False or "topOrigin" in json.loads(client):
            raise Rejected("top-level Identity page required")

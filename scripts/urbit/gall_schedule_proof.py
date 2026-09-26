"""Fail-closed validation of a supplied bounded Gall schedule report.

This module never runs Hoon or verifies that supplied data was executed. The
guarded caller must separately retain native commands, positive/negative native
results, logs, toolchain identity and exact source bindings. Authored unit-test
records can pass these structural checks; they are not native evidence.

The bounded jam/cue implementation follows the pinned hoon.hoon ++jam/++cue and
++mat/++rub specification (Urbit 5a187fed, lines1989-2060, MIT, copyright Urbit).
It is used only to inspect retained test nouns, never as an application decoder.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import delivery_cases as D

MODULE = Path(__file__).resolve()
ROOT = MODULE.parent.parent.parent
SPECS = Path('/specs') if MODULE.parent == Path('/code') else ROOT / 'specs/urbit'
HEX = re.compile(r"[0-9a-f]+")
HASH = re.compile(r"[0-9a-f]{64}")
DECIMAL = re.compile(r"0|[1-9][0-9]*")
MAX_REPORT = 131072
MAX_JAM = 16384
MAX_NODES = 4096
MAX_DEPTH = 96
MAX_EXPANDED = 16384
# Native-only measurement cap justified by the retained Gall05 size diagnostic.
# These bytes are omitted, never accepted by the bounded jam decoder below.
MAX_OPAQUE_JAM = 2097152
PROTOCOL = "stead.native-scheduled-gall/2"
POKE_PROTOCOL = "stead.gall-poke-projection/1"
POKE_MEASUREMENT_SCOPE = "native hash-and-size only; omitted bytes not reconstructed"
POKE_MARKER = "stead-opaque-vase-type"
POKE_MEASUREMENTS = ("original_moves", "original_poke", "omitted_type")
POKE_FIELDS = frozenset({"old_poke_moves", "fresh_poke_moves"})
REQUIREMENT = "delivery-late-old-leave"
NOUN_FIELDS = frozenset("""
old_duct new_duct old_watch_moves old_watch_gifts captured_leave_moves
captured_leave delivered_leave delivered_leave_output
old_result_gifts fresh_watch_moves fresh_watch_gifts
fresh_result_gifts old_incoming_active old_incoming_retired incoming_before
incoming_after live_watch_moves live_leave_moves live_delivery_output
""".split())
JSON_FIELDS = frozenset("""
old_pending_active old_pending_retired pending_before pending_after
observer_before observer_after old_observer_retired old_observer_after
observer_completed old_observer_completed final_pending receipt
business_committed business_after_leave business_completed business_final
live_pending_before live_pending_after live_observer
""".split())
TEXT_FIELDS = frozenset("""
protocol classification status requirement clock transport late_old_leave
current_live_leave_control expected_fresh_pending same_path old_nonce new_nonce
receipt_sha256
""".split())
ASSERTIONS = (
    "bounded-native-schedule-scope",
    "canonical-jam-record-integrity",
    "bounded-tagged-poke-projections-with-explicit-opaque-measurements",
    "captured-emitted-old-leave-delivered-unchanged",
    "distinct-old-and-fresh-nonce-ducts",
    "old-home-duct-retired-before-fresh-watch",
    "fresh-pending-and-incoming-duct-unchanged",
    "fresh-and-retired-observers-unchanged",
    "business-history-unchanged-after-old-leave",
    "fresh-exact-correlated-fact-and-kick",
    "retired-old-observer-no-private-fact",
    "exact-retry-preserves-business-history",
    "current-live-leave-removes-reservation",
    REQUIREMENT,
)


class ScheduleProofError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise ScheduleProofError(message)


def _decimal(value, maximum=2**64 - 1):
    _require(isinstance(value, str) and len(value) <= 20
             and DECIMAL.fullmatch(value), "Noncanonical bounded decimal")
    result = int(value)
    _require(result <= maximum, "Decimal exceeds bound")
    return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def canonical(command):
    """Serialize the bounded selected corpus command; no schema/auth inference."""
    _require(isinstance(command, dict) and set(command) == {
        'protocol', 'request_id', 'project_id', 'resource_id', 'expected_revision',
        'authority_epoch', 'operation', 'payload'}, 'Selected command envelope')
    _require(command['protocol'] == 'stead.command/2' and command['operation'] == 'work.create'
             and isinstance(command['payload'], dict) and set(command['payload']) == {
                 'title', 'description', 'type', 'status', 'priority'}, 'Selected work command payload')
    _require(all(isinstance(value, str) for key, value in command.items() if key != 'payload')
             and all(isinstance(value, str) for value in command['payload'].values()),
             'Selected command values must be strings')
    result = json.dumps(command, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    _require(0 < len(result) <= 65536, 'Selected command byte bound')
    return result


def command_digest(command):
    return hashlib.sha256(b'stead.command/2\0' + canonical(command)).hexdigest()


def _json(raw):
    _require(isinstance(raw, str) and 0 < len(raw.encode()) <= MAX_REPORT,
             "JSON byte bound")
    # Bound nesting before invoking the platform JSON decoder.
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            _require(depth <= 12, "JSON nesting bound")
        elif char in "]}":
            depth -= 1
            _require(depth >= 0, "Unbalanced JSON")
    try:
        value = json.loads(raw, object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               ScheduleProofError("Non-JSON constant")))
    except (TypeError, json.JSONDecodeError, RecursionError) as error:
        raise ScheduleProofError("Invalid JSON") from error
    _require(isinstance(value, dict), "Expected JSON object")
    return value


def _mat(value):
    if value == 0:
        return 1, 1
    bits = value.bit_length()
    width = bits.bit_length()
    return 2 * width + bits, ((1 << width)
           | ((bits & ((1 << (width - 1)) - 1)) << (width + 1))
           | (value << (2 * width)))


def _jam(noun):
    """Canonical encoder, also usable by explicitly authored host fixtures."""
    interned = {}
    identities = {}
    sizes = {}
    next_id = 0

    def identify(value, depth=0):
        nonlocal next_id
        _require(depth <= MAX_DEPTH, "Noun depth bound")
        if type(value) is int:
            _require(0 <= value and value.bit_length() <= MAX_JAM * 8,
                     "Noun atom bound")
            key, size = ("atom", value), 1
        else:
            _require(type(value) is tuple and len(value) == 2, "Invalid noun cell")
            if id(value) in identities:
                return identities[id(value)]
            left, right = identify(value[0], depth + 1), identify(value[1], depth + 1)
            key, size = ("cell", left, right), 1 + sizes[left] + sizes[right]
        _require(size <= MAX_EXPANDED, "Expanded noun bound")
        if key not in interned:
            next_id += 1
            _require(next_id <= MAX_NODES, "Noun node bound")
            interned[key] = next_id
            sizes[next_id] = size
        identifier = interned[key]
        if type(value) is tuple:
            identities[id(value)] = identifier
        return identifier

    identify(noun)
    positions = {}

    def pack(value, offset):
        identifier = interned[("atom", value)] if type(value) is int else identities[id(value)]
        previous = positions.get(identifier)
        if previous is not None and not (type(value) is int
                and value.bit_length() <= previous.bit_length()):
            length, bits = _mat(previous)
            return length + 2, 3 | (bits << 2)
        if previous is None:
            positions[identifier] = offset
        if type(value) is int:
            length, bits = _mat(value)
            return length + 1, bits << 1
        left_length, left = pack(value[0], offset + 2)
        right_length, right = pack(value[1], offset + 2 + left_length)
        length = 2 + left_length + right_length
        _require(length <= MAX_JAM * 8, "Encoded noun bound")
        return length, 1 | (left << 2) | (right << (2 + left_length))

    length, value = pack(noun, 0)
    _require(length <= MAX_JAM * 8, "Encoded noun bound")
    return value.to_bytes((length + 7) // 8, "little")


def _cue(raw):
    _require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_JAM and raw[-1] != 0,
             "Noncanonical jam atom")
    bits = int.from_bytes(raw, "little")
    limit = bits.bit_length()
    positions = {}
    steps = 0

    def read(offset, count):
        _require(0 <= count <= MAX_JAM * 8 and offset + count <= limit,
                 "Truncated or oversized jam field")
        return (bits >> offset) & ((1 << count) - 1)

    def rub(offset):
        width = 0
        while read(offset + width, 1) == 0:
            width += 1
            _require(width <= 18, "Jam length prefix bound")
        if width == 0:
            return 1, 0
        length = (1 << (width - 1)) + read(offset + width + 1, width - 1)
        return 2 * width + length, read(offset + 2 * width, length)

    def unpack(offset, depth=0):
        nonlocal steps
        steps += 1
        _require(steps <= MAX_NODES and depth <= MAX_DEPTH, "Jam traversal bound")
        if read(offset, 1) == 0:
            size, atom = rub(offset + 1)
            result = size + 1, atom, 1
            positions[offset] = result[1:]
            return result
        if read(offset + 1, 1) == 1:
            size, pointer = rub(offset + 2)
            _require(pointer < offset and pointer in positions, "Invalid jam backreference")
            return size + 2, *positions[pointer]
        left_size, left, left_count = unpack(offset + 2, depth + 1)
        right_size, right, right_count = unpack(offset + 2 + left_size, depth + 1)
        count = 1 + left_count + right_count
        _require(count <= MAX_EXPANDED, "Expanded jam noun bound")
        value = (left, right)
        positions[offset] = value, count
        return 2 + left_size + right_size, value, count

    used, noun, _ = unpack(0)
    _require(used == limit and _jam(noun) == raw, "Noncanonical or trailing jam encoding")
    return noun


def _record(raw):
    record = _json(raw)
    _require(set(record) == {"jam_hex", "jam_sha256", "jam_bytes", "noun"},
             "Jam record fields")
    encoded = record["jam_hex"]
    _require(isinstance(encoded, str) and 0 < len(encoded) <= 2 * MAX_JAM
             and len(encoded) % 2 == 0 and HEX.fullmatch(encoded), "Canonical jam hex required")
    binary = bytes.fromhex(encoded)
    _require(_decimal(record["jam_bytes"], MAX_JAM) == len(binary), "Jam byte count mismatch")
    _require(isinstance(record["jam_sha256"], str) and HASH.fullmatch(record["jam_sha256"])
             and hashlib.sha256(binary).hexdigest() == record["jam_sha256"], "Jam digest mismatch")
    _require(isinstance(record["noun"], str) and 0 < len(record["noun"].encode()) <= MAX_REPORT,
             "Missing bounded diagnostic noun text")
    # Diagnostic pretty text is retained but never trusted as parsed noun data.
    return _cue(binary)


def _atom(text):
    return int.from_bytes(text.encode(), "little")


def _cord(noun):
    _require(type(noun) is int and noun >= 0 and noun.bit_length() <= MAX_REPORT * 8,
             "Expected bounded cord atom")
    try:
        return noun.to_bytes((noun.bit_length() + 7) // 8, "little").decode("utf-8")
    except UnicodeDecodeError as error:
        raise ScheduleProofError("Invalid UTF-8 cord") from error


def _parts(noun, count):
    result = []
    for _ in range(count - 1):
        _require(type(noun) is tuple and len(noun) == 2, "Missing noun tuple field")
        result.append(noun[0])
        noun = noun[1]
    return result + [noun]


def _list(noun, maximum=64):
    result = []
    while noun != 0:
        _require(type(noun) is tuple and len(noun) == 2 and len(result) < maximum,
                 "Malformed or oversized noun list")
        result.append(noun[0])
        noun = noun[1]
    return result


def _path(noun):
    parts = [_cord(part) for part in _list(noun, 16)]
    _require(all(0 < len(part.encode()) <= 128 for part in parts), "Path segment bound")
    return "/" + "/".join(parts)


def _pass(noun, action):
    parent, tag, wire, vane, task, sack, agent, verb, argument = _parts(noun, 9)
    _require([tag, vane, task, agent, verb] == list(map(_atom,
             ["pass", "g", "deal", "stead-home", action])), "Unexpected emitted Gall deal")
    sender, target, provenance = _parts(sack, 3)
    # Pinned hoon.hoon ++po suffix table: ~zod=0 and ~bus=182.
    _require(sender == 182 and target == 0 and _path(provenance) == "/gall/stead-observer",
             "Wrong native deal sender/target/provenance")
    _require([_path(path) for path in _list(parent, 2)] == ["/init"], "Wrong parent duct")
    return (wire, parent), argument


def _one_pass(noun, action):
    moves = _list(noun, 4)
    _require(len(moves) == 2, "Control must emit exactly one deal and one ACK")
    emitted = []
    acks = []
    for move in moves:
        _, kind = _parts(move, 2)
        tag, _ = _parts(kind, 2)
        (emitted if tag == _atom("pass") else acks).append(move)
    _require(len(emitted) == len(acks) == 1, "Missing emitted deal/control ACK")
    _gift(acks[0], "poke-ack", expected_duct=None)
    _require([_path(path) for path in _list(_parts(acks[0], 5)[0], 2)] == ["/schedule/control"],
             "Owner control ACK on wrong duct")
    _pass(emitted[0], action)
    return emitted[0]


def _gift(noun, kind, expected_duct):
    duct, give, unto, tag, body = _parts(noun, 5)
    _require([give, unto, tag] == list(map(_atom, ["give", "unto", kind])), "Unexpected Gall gift")
    _require(expected_duct is None or duct == expected_duct, "Gift delivered on wrong duct")
    if kind != "fact":
        _require(body == 0, "NACK or nonempty terminal gift")
        return None
    mark, vase = _parts(body, 2)
    _require(mark == _atom("stead-result-2"), "Wrong delivered fact mark")
    _, value = _parts(vase, 2)
    return _cord(value)


def _watch_gifts(noun, duct):
    moves = _list(noun, 2)
    _require(len(moves) == 1, "Watch must have exactly one native ACK")
    _gift(moves[0], "watch-ack", duct)


def _result_gifts(noun, watch_duct, poke_duct, receipt):
    moves = _list(noun, 4)
    _require(len(moves) == 3, "Exactly one fact, kick and poke ACK required")
    seen = set()
    for move in moves:
        tag = _cord(_parts(move, 5)[3])
        _require(tag in {"poke-ack", "fact", "kick"} and tag not in seen, "Duplicate or wrong gift")
        seen.add(tag)
        value = _gift(move, tag, poke_duct if tag == "poke-ack" else watch_duct)
        _require(tag != "fact" or value == receipt, "Fact bytes differ from exact receipt")


def _poke_projection(raw):
    """Inspect the projection; omitted original bytes cannot be reconstructed."""
    projection = _json(raw)
    measurement_keys = {stem + suffix for stem in POKE_MEASUREMENTS
                        for suffix in ("_jam_sha256", "_jam_bytes")}
    _require(set(projection) == measurement_keys | {
        "protocol", "representation", "measurement_scope", "projected_moves"}
        and all(isinstance(value, str) for value in projection.values()),
        "Poke projection fields")
    _require(projection["protocol"] == POKE_PROTOCOL
             and projection["representation"] == "poke-vase-type-omitted"
             and projection["measurement_scope"] == POKE_MEASUREMENT_SCOPE,
             "Poke projection scope")
    for stem in POKE_MEASUREMENTS:
        _require(HASH.fullmatch(projection[stem + "_jam_sha256"])
                 and 0 < _decimal(projection[stem + "_jam_bytes"], MAX_OPAQUE_JAM),
                 "Missing or unbounded native-only opaque measurement")
    noun = _record(projection["projected_moves"])
    emitted = _one_pass(noun, "poke")
    _, cage = _pass(emitted, "poke")
    _, vase = _parts(cage, 2)
    marker, _ = _parts(vase, 2)
    tag, digest, size = _parts(marker, 3)
    _require(tag == _atom(POKE_MARKER)
             and _cord(digest) == projection["omitted_type_jam_sha256"]
             and type(size) is int and size == _decimal(projection["omitted_type_jam_bytes"], MAX_OPAQUE_JAM),
             "Poke projection omitted-type marker mismatch")
    return noun, {key: projection[key] for key in sorted(measurement_keys)}


def _duct(noun, nonce, probe, lane="watch"):
    paths = _list(noun, 2)
    _require(len(paths) == 2 and _path(paths[1]) == "/init", "Bad complete duct")
    wire = [_cord(part) for part in _list(paths[0], 12)]
    expected_tail = [nonce, "probe", probe, lane] if lane == "watch" else ["probe", probe, lane]
    _require(wire[:2] == ["use", "stead-observer"] and len(wire[2]) <= 128
             and wire[3:6] == ["out", "~zod", "stead-home"]
             and wire[6:] == expected_tail, "Duct nonce/probe/wire mismatch")
    return wire[2]


def _incoming(noun, duct, route):
    node, left, right = _parts(noun, 3)
    key, value = _parts(node, 2)
    sender, path = _parts(value, 2)
    _require(left == right == 0 and key == duct and sender == 182 and _path(path) == route,
             "Wrong live incoming Gall duct/map")


def _pending(value, route, expected):
    _require(set(value) == {"protocol", "now_ms", "total", "by_ship", "entries"}
             and value["protocol"] == "stead.fixture-pending/1", "Pending envelope")
    _decimal(value["now_ms"])
    _require(_decimal(value["total"], 64) == expected, "Wrong actual pending count")
    _require(value["by_ship"] == {ship: str(expected if ship == "bus" else 0)
                                  for ship in ("zod", "bus", "nec", "bud")}, "Pending per-sender count")
    if expected == 0:
        _require(value["entries"] == {}, "Retired pending entry remains")
        return
    _require(isinstance(value["entries"], dict) and set(value["entries"]) == {route}, "Pending path mismatch")
    row = value["entries"][route]
    _require(isinstance(row, dict) and set(row) == {"sender", "expires_at_ms", "incoming_ducts"}
             and row["sender"] == "~bus" and row["incoming_ducts"] == "1", "Pending recipient mismatch")
    _require(_decimal(row["expires_at_ms"]) > _decimal(value["now_ms"]), "Pending watch already expired")


def _observer(raw, value, route, *, facts, kicks, pokes, ongoing, leaving):
    # The shim supplies provenance of the *input shape*, not execution evidence.
    D.observation({"raw": raw, "json": value,
                   "native": {"scope": "supplied schedule payload; execution unverified"}}, route=route)
    expected = {"facts": str(facts), "kicks": str(kicks), "watch_acks": "1",
                "watch_nacks": "0", "poke_acks": str(pokes), "poke_nacks": "0",
                "pokes_requested": str(pokes), "ongoing_subscription": str(ongoing).lower(),
                "leave_requested": str(leaving).lower(), "closed": str(kicks == 1).lower(),
                "watch_requested": "true"}
    _require(all(value[key] == wanted for key, wanted in expected.items()), "Observer outcome mismatch")


def _validate(payload):
    """Validate supplied output or raise ValueError; this never proves execution."""
    _require(isinstance(payload, dict) and set(payload) == NOUN_FIELDS | POKE_FIELDS | JSON_FIELDS | TEXT_FIELDS,
             "Missing or unexpected schedule report field")
    _require(all(isinstance(value, str) for value in payload.values()), "Native report values must be strings")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    _require(len(encoded) <= MAX_REPORT, "Schedule report exceeds bound")
    expected = {"protocol": PROTOCOL, "classification": "native-scheduled-gall",
                "requirement": REQUIREMENT, "status": "passed", "late_old_leave": "passed",
                "current_live_leave_control": "passed", "expected_fresh_pending": "1",
                "clock": "2026-09-25T00:00:00Z; fixed test clock",
                "transport": "mock direct Gall dispatch; no Ames or UDP"}
    _require(all(payload[key] == value for key, value in expected.items()), "Wrong schedule scope/control")
    nouns = {key: _record(payload[key]) for key in NOUN_FIELDS}
    opaque_measurements = {}
    for key in sorted(POKE_FIELDS):
        nouns[key], opaque_measurements[key] = _poke_projection(payload[key])
    _require(all(opaque_measurements["old_poke_moves"][key] == opaque_measurements["fresh_poke_moves"][key]
                 for key in ("omitted_type_jam_sha256", "omitted_type_jam_bytes")),
             "Old/fresh native-only omitted-type measurements differ")
    data = {key: _json(payload[key]) for key in JSON_FIELDS}
    corpus = json.loads((SPECS / "fixtures/native-cases-v2.json").read_bytes())
    command = corpus["commands"]["work_a_create"]
    command_raw = canonical(command).decode()
    digest = command_digest(command)
    binding = "019939ba-4000-7000-8000-000000000202"
    route = f"/v2/result/~bus/{binding}/{command['project_id']}/{command['request_id']}/{digest}"
    _require(payload["same_path"] == route, "Wrong exact correlated result path")
    old, fresh = data["old_observer_retired"], data["observer_before"]
    live = data["live_observer"]
    _require(len({old.get("id"), fresh.get("id"), live.get("id")}) == 3, "Probe IDs must differ")
    old_nonce, new_nonce = payload["old_nonce"], payload["new_nonce"]
    _require(0 < _decimal(old_nonce) < _decimal(new_nonce), "Fresh nonce must differ and advance")
    old_duct, new_duct = nouns["old_duct"], nouns["new_duct"]
    _require(old_duct != new_duct, "Old/fresh ducts identical")
    run_nonce = _duct(old_duct, old_nonce, old["id"])
    _require(_duct(new_duct, new_nonce, fresh["id"]) == run_nonce, "Unexpected agent rebuild")
    old_watch = _one_pass(nouns["old_watch_moves"], "watch")
    fresh_watch = _one_pass(nouns["fresh_watch_moves"], "watch")
    for move, duct in ((old_watch, old_duct), (fresh_watch, new_duct)):
        actual_duct, watched = _pass(move, "watch")
        _require(actual_duct == duct and _path(watched) == route, "Watch task/duct mismatch")
    captured = _one_pass(nouns["captured_leave_moves"], "leave")
    _require(captured == nouns["captured_leave"] == nouns["delivered_leave"]
             and payload["captured_leave"] == payload["delivered_leave"], "Captured/delivered leave changed")
    leave_duct, leave_arg = _pass(captured, "leave")
    _require(leave_duct == old_duct and leave_arg == 0 and nouns["delivered_leave_output"] == 0,
             "Old leave input/output differs")
    _watch_gifts(nouns["old_watch_gifts"], old_duct)
    _watch_gifts(nouns["fresh_watch_gifts"], new_duct)
    for field in ("old_pending_active", "pending_before", "pending_after", "live_pending_before"):
        _pending(data[field], route, 1)
    for field in ("old_pending_retired", "final_pending", "live_pending_after"):
        _pending(data[field], route, 0)
    _incoming(nouns["old_incoming_active"], old_duct, route)
    _require(nouns["old_incoming_retired"] == 0, "Old home duct not retired")
    _incoming(nouns["incoming_before"], new_duct, route)
    _require(payload["incoming_before"] == payload["incoming_after"], "Fresh incoming duct changed")
    for before, after in (("pending_before", "pending_after"),
                          ("observer_before", "observer_after"),
                          ("old_observer_retired", "old_observer_after"),
                          ("old_observer_retired", "old_observer_completed")):
        _require(payload[before] == payload[after], "Old leave changed pending/observer: " + after)
    _observer(payload["observer_before"], fresh, route, facts=0, kicks=0, pokes=0, ongoing=True, leaving=False)
    _observer(payload["old_observer_retired"], old, route, facts=0, kicks=0, pokes=1, ongoing=False, leaving=True)
    _observer(payload["observer_completed"], data["observer_completed"], route,
              facts=1, kicks=1, pokes=1, ongoing=False, leaving=False)
    _require(data["observer_completed"]["id"] == fresh["id"], "Fresh completion changed probe")
    _require(all(data["observer_completed"]["events"].get(serial) == event
                 for serial, event in fresh["events"].items()), "Fresh completion rewrote prior observation")
    _observer(payload["live_observer"], live, route, facts=0, kicks=0, pokes=0, ongoing=False, leaving=True)
    receipt = data["receipt"]
    _require(set(receipt) == D.RECEIPT_FIELDS and receipt["protocol"] == "stead.receipt/2"
             and receipt["status"] == "accepted", "Accepted receipt envelope")
    for field, value in {"request_id": command["request_id"], "canonical_sha256": digest,
            "project_id": command["project_id"], "resource_id": command["resource_id"],
            "resource_kind": "work", "resource_revision": "1", "authority_epoch": "1",
            "binding_id": binding, "principal_id": "019939ba-4000-7000-8000-000000000102",
            "container_id": "", "git_commit_oid": "", "authentication": "fake-native/1",
            "authentication_strength": "synthetic-native-sender"}.items():
        _require(receipt[field] == value, "Receipt correlation mismatch: " + field)
    _decimal(receipt["accepted_at_ms"])
    receipt_hash = hashlib.sha256(payload["receipt"].encode()).hexdigest()
    _require(payload["receipt_sha256"] == receipt_hash, "Receipt digest mismatch")
    facts = [event for event in data["observer_completed"]["events"].values() if event["kind"] == "fact"]
    _require(len(facts) == 1 and facts[0]["payload_sha256"] == receipt_hash
             and _decimal(facts[0]["payload_bytes"]) == len(payload["receipt"].encode()), "Observed fact bytes uncorrelated")
    for label, probe, duct in (("old", old["id"], old_duct), ("fresh", fresh["id"], new_duct)):
        poke = _one_pass(nouns[label + "_poke_moves"], "poke")
        poke_duct, cage = _pass(poke, "poke")
        _require(_duct(poke_duct, "", probe, "poke") == run_nonce, "Poke provenance changed")
        mark, vase = _parts(cage, 2)
        _require(mark == _atom("stead-command-2") and _cord(_parts(vase, 2)[1]) == command_raw,
                 "Poke is not the exact frozen work command")
        _result_gifts(nouns[label + "_result_gifts"], duct, poke_duct, payload["receipt"])
    history = data["business_committed"]
    history_fields = set("""protocol now_ms state_jam_sha256 projects work_items documents grants
        objects object_bytes journal_events receipts last_journal_record last_journal_digest
        journal_sha256 receipts_sha256 objects_sha256 bindings_sha256 containers_sha256
        reachable_sha256 ordinary_count revisions security_counts""".split())
    _require(set(history) == history_fields and history.get("protocol") == "stead.fixture-snapshot/1"
             and all(history.get(key) == value for key, value in
                     {"projects": "1", "work_items": "1", "journal_events": "3", "receipts": "3",
                      "documents": "0", "grants": "2", "objects": "0", "object_bytes": "0",
                      "ordinary_count": "3"}.items()),
             "Committed business fixture mismatch")
    _require(history["now_ms"] == receipt["accepted_at_ms"], "Fixed-clock receipt/history mismatch")
    _require(history["revisions"] == {"project/" + command["project_id"]: "1",
             "policy/" + command["project_id"]: "2",
             "work/" + command["project_id"] + "/" + command["resource_id"]: "1"}
             and history["security_counts"] == {command["project_id"]: "0"}, "Business revision mismatch")
    for key in ("state_jam_sha256", "last_journal_digest", "journal_sha256", "receipts_sha256",
                "objects_sha256", "bindings_sha256", "containers_sha256", "reachable_sha256"):
        _require(isinstance(history.get(key), str) and HASH.fullmatch(history[key]), "Missing business digest")
    journal = _json(history["last_journal_record"])
    journal_expected = {"protocol": "stead.journal/1", "sequence": "3", "canonical_command": command_raw,
                        "principal_id": receipt["principal_id"], "binding_id": binding,
                        "authentication": receipt["authentication"],
                        "authentication_strength": receipt["authentication_strength"],
                        "accepted_at_ms": receipt["accepted_at_ms"], "policy_revision": "2",
                        "authority_epoch": "1", "old_revision": "0", "new_revision": "1",
                        "git_commit_oid": ""}
    _require(set(journal) == set(journal_expected) | {"previous_digest"}
             and all(journal[key] == value for key, value in journal_expected.items())
             and isinstance(journal["previous_digest"], str) and HASH.fullmatch(journal["previous_digest"]),
             "Last business journal does not correlate to exact command")
    _require(hashlib.sha256(b"stead.journal/1\0" + history["last_journal_record"].encode()).hexdigest()
             == history["last_journal_digest"], "Business journal digest mismatch")
    for key in ("business_after_leave", "business_completed", "business_final"):
        _require(payload[key] == payload["business_committed"], "Business history changed: " + key)
    live_watch = _one_pass(nouns["live_watch_moves"], "watch")
    live_leave = _one_pass(nouns["live_leave_moves"], "leave")
    live_duct, live_path = _pass(live_watch, "watch")
    live_leave_duct, live_arg = _pass(live_leave, "leave")
    _require(live_duct == live_leave_duct and live_arg == 0 and _path(live_path) == route
             and live_duct not in (old_duct, new_duct), "Live-leave positive control input mismatch")
    live_wire = _list(_list(live_duct, 2)[0], 12)
    live_nonce = _cord(live_wire[6]) if len(live_wire) > 6 else ""
    _require(_decimal(live_nonce) > _decimal(new_nonce)
             and _duct(live_duct, live_nonce, live["id"]) == run_nonce,
             "Live-leave control nonce/probe mismatch")
    _require(nouns["live_delivery_output"] == 0, "Live-leave control emitted unexpected gifts")
    assertions = [{"name": name, "status": "passed"} for name in ASSERTIONS]
    _require(assertions and len({row["name"] for row in assertions}) == len(assertions)
             and all(row["name"] for row in assertions), "Empty or duplicate assertion inventory")
    return {"protocol": "stead.native-schedule-payload-validation/2", "status": "passed",
            "classification": "host-validation-of-supplied-native-schedule",
            "requirement": REQUIREMENT, "native_execution_verified": False,
            "report_sha256": hashlib.sha256(encoded).hexdigest(),
            "jam_record_count": len(nouns), "projected_jam_record_count": len(POKE_FIELDS),
            "opaque_measurements": {"scope": POKE_MEASUREMENT_SCOPE,
                "independently_reconstructed": False, "records": opaque_measurements},
            "assertions": assertions}


def validate(payload):
    """Validate supplied output or raise ValueError; this never proves execution."""
    try:
        return _validate(payload)
    except (KeyError, IndexError, TypeError, OverflowError, RecursionError) as error:
        raise ScheduleProofError("Malformed or out-of-bounds schedule payload") from error

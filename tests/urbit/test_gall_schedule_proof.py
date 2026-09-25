"""Authored native-shaped reports exercise host validation ONLY, never Gall.

No fixture in this module is native evidence. The positive specimen deliberately
uses invented bytes and state digests to make the validator's boundary explicit.
Actual execution and source identity must be established by the guarded runner.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/urbit"))
import gall_schedule_proof as G


def j(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def a(text):
    return int.from_bytes(text.encode(), "little")


def tup(*values):
    result = values[-1]
    for value in reversed(values[:-1]):
        result = value, result
    return result


def lst(values):
    return tup(*values, 0) if values else 0


def path(text):
    return lst([a(part) for part in text.lstrip("/").split("/")])


def record(noun):
    raw = G._jam(noun)
    return j({"jam_hex": raw.hex(), "jam_sha256": hashlib.sha256(raw).hexdigest(),
              "jam_bytes": str(len(raw)), "noun": "AUTHORED HOST FIXTURE; not native output"})


def gift(duct, kind, body=0):
    return tup(duct, a("give"), a("unto"), a(kind), body)


def specimen():
    """A complete invented report to test rejection controls, not execution."""
    command = json.loads((ROOT / "specs/urbit/fixtures/native-cases-v2.json").read_bytes())["commands"]["work_a_create"]
    command_raw = G.canonical(command).decode()
    digest = G.command_digest(command)
    binding = "019939ba-4000-7000-8000-000000000202"
    project, resource = command["project_id"], command["resource_id"]
    route = f"/v2/result/~bus/{binding}/{project}/{command['request_id']}/{digest}"
    ids = {name: f"019939ba-4000-7000-8000-00000000900{number}"
           for number, name in enumerate(("old", "fresh", "live"), 1)}
    init = lst([path("/init")])
    control_duct = lst([path("/schedule/control")])

    def wire(probe, nonce=None, lane="watch"):
        return path("/use/stead-observer/0w1.test/out/~zod/stead-home/"
                    + (str(nonce) + "/" if nonce else "") + f"probe/{probe}/{lane}")

    ducts = {name: tup(wire(ids[name], number), init)
             for number, name in enumerate(("old", "fresh", "live"), 1)}

    def move(name, verb):
        number = {"old": 1, "fresh": 2, "live": 3}[name]
        lane = "poke" if verb == "poke" else "watch"
        arg = 0 if verb == "leave" else path(route) if verb == "watch" else tup(
            a("stead-command-2"), tup(a("AUTHORED_TYPE_ONLY"), a(command_raw)))
        return tup(init, a("pass"), wire(ids[name], None if verb == "poke" else number, lane),
                   a("g"), a("deal"), tup(182, 0, path("/gall/stead-observer")),
                   a("stead-home"), a(verb), arg)

    def control(name, verb):
        return lst([gift(control_duct, "poke-ack"), move(name, verb)])

    receipt = {"protocol": "stead.receipt/2", "status": "accepted", "request_id": command["request_id"],
               "canonical_sha256": digest, "project_id": project, "resource_id": resource,
               "resource_kind": "work", "container_id": "", "resource_revision": "1", "authority_epoch": "1",
               "principal_id": "019939ba-4000-7000-8000-000000000102", "binding_id": binding,
               "authentication": "fake-native/1", "authentication_strength": "synthetic-native-sender",
               "accepted_at_ms": "1790294400000", "git_commit_oid": ""}
    receipt_raw = j(receipt)
    receipt_digest = hashlib.sha256(receipt_raw.encode()).hexdigest()

    def result_gifts(name):
        return lst([gift(tup(wire(ids[name], lane="poke"), init), "poke-ack"),
                    gift(ducts[name], "fact", tup(a("stead-result-2"), (a("AUTHORED_TYPE_ONLY"), a(receipt_raw)))),
                    gift(ducts[name], "kick")])

    def pending(count):
        return {"protocol": "stead.fixture-pending/1", "now_ms": receipt["accepted_at_ms"], "total": str(count),
                "by_ship": {ship: str(count if ship == "bus" else 0) for ship in ("zod", "bus", "nec", "bud")},
                "entries": {route: {"sender": "~bus", "expires_at_ms": "1790294460000", "incoming_ducts": "1"}} if count else {}}

    def event(kind, probe, serial, terminal=False):
        fact = kind == "fact"
        return {"kind": kind, "source_ship": "~zod", "peer_agent": "stead-home",
                "peer_agent_basis": "fixed issued Gall wire; sign has no agent field",
                "wire": f"/probe/{probe}/{'poke' if kind == 'poke-ack' else 'watch'}",
                "mark": "stead-result-2" if fact else "", "payload_bytes": str(len(receipt_raw.encode())) if fact else "0",
                "payload_sha256": receipt_digest if fact else "", "source_provenance_sha256": "c" * 64,
                "observed_at_ms": receipt["accepted_at_ms"], "after_terminal": str(terminal).lower()}

    def observer(name, completed=False):
        leaving = name != "fresh"
        kinds = ["watch-ack"] + (["poke-ack"] if name == "old" or completed else []) + (["fact", "kick"] if completed else [])
        serial = {"old": 1, "fresh": 3, "live": 7}[name]
        return {"protocol": "stead.observer/1", "id": ids[name], "status": "observed", "fault": "", "route": route,
                "watch_requested": "true", "leave_requested": str(leaving).lower(), "closed": str(completed).lower(),
                "ongoing_subscription": str(name == "fresh" and not completed).lower(),
                "facts": str(int(completed)), "kicks": str(int(completed)), "watch_acks": "1", "watch_nacks": "0",
                "poke_acks": str(int(name == "old" or completed)), "poke_nacks": "0",
                "pokes_requested": str(int(name == "old" or completed)),
                "events": {str(serial + index): event(kind, ids[name], serial + index, name == "old" and index > 0)
                           for index, kind in enumerate(kinds)}}

    journal = {"protocol": "stead.journal/1", "sequence": "3", "previous_digest": "0" * 64,
               "canonical_command": command_raw, "principal_id": receipt["principal_id"], "binding_id": binding,
               "authentication": receipt["authentication"], "authentication_strength": receipt["authentication_strength"],
               "accepted_at_ms": receipt["accepted_at_ms"], "policy_revision": "2", "authority_epoch": "1",
               "old_revision": "0", "new_revision": "1", "git_commit_oid": ""}
    history = {"protocol": "stead.fixture-snapshot/1", "now_ms": receipt["accepted_at_ms"],
               "projects": "1", "work_items": "1", "documents": "0", "grants": "2", "objects": "0", "object_bytes": "0",
               "journal_events": "3", "receipts": "3", "ordinary_count": "3", "last_journal_record": j(journal),
               "last_journal_digest": hashlib.sha256(b"stead.journal/1\0" + j(journal).encode()).hexdigest(),
               "revisions": {"project/" + project: "1", "policy/" + project: "2", "work/" + project + "/" + resource: "1"},
               "security_counts": {project: "0"}}
    history.update({name: "d" * 64 for name in ("state_jam_sha256", "journal_sha256", "receipts_sha256",
                                               "objects_sha256", "bindings_sha256", "containers_sha256", "reachable_sha256")})
    incoming = lambda name: tup(tup(ducts[name], tup(182, path(route))), 0, 0)
    nouns = {"old_duct": ducts["old"], "new_duct": ducts["fresh"],
             "captured_leave": move("old", "leave"), "delivered_leave": move("old", "leave"),
             "captured_leave_moves": control("old", "leave"), "delivered_leave_output": 0,
             "old_incoming_active": incoming("old"), "old_incoming_retired": 0,
             "incoming_before": incoming("fresh"), "incoming_after": incoming("fresh"),
             "live_watch_moves": control("live", "watch"), "live_leave_moves": control("live", "leave"),
             "live_delivery_output": 0}
    for name in ("old", "fresh"):
        nouns[name + "_watch_moves"] = control(name, "watch")
        nouns[name + "_watch_gifts"] = lst([gift(ducts[name], "watch-ack")])
        nouns[name + "_poke_moves"] = control(name, "poke")
        nouns[name + "_result_gifts"] = result_gifts(name)
    data = {name: pending(1) for name in ("old_pending_active", "pending_before", "pending_after", "live_pending_before")}
    data.update({name: pending(0) for name in ("old_pending_retired", "final_pending", "live_pending_after")})
    data.update({name: observer("old") for name in ("old_observer_retired", "old_observer_after", "old_observer_completed")})
    data.update({name: observer("fresh") for name in ("observer_before", "observer_after")})
    data.update({"observer_completed": observer("fresh", True), "live_observer": observer("live"), "receipt": receipt})
    data.update({name: history for name in ("business_committed", "business_after_leave", "business_completed", "business_final")})
    payload = {"protocol": G.PROTOCOL, "classification": "native-scheduled-gall", "requirement": G.REQUIREMENT,
               "status": "passed", "clock": "2026-09-25T00:00:00Z; fixed test clock",
               "transport": "mock direct Gall dispatch; no Ames or UDP", "late_old_leave": "passed",
               "current_live_leave_control": "passed", "expected_fresh_pending": "1", "same_path": route,
               "old_nonce": "1", "new_nonce": "2", "receipt_sha256": receipt_digest}
    payload.update({name: record(value) for name, value in nouns.items()})
    payload.update({name: j(value) for name, value in data.items()})
    return payload


class GallScheduleProofTests(unittest.TestCase):
    def reject(self, change):
        value = specimen()
        change(value)
        with self.assertRaises(ValueError):
            G.validate(value)

    def test_authored_specimen_checks_shape_without_claiming_execution(self):
        result = G.validate(specimen())
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["native_execution_verified"])
        self.assertEqual(result["classification"], "host-validation-of-supplied-native-schedule")
        names = [row["name"] for row in result["assertions"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn(G.REQUIREMENT, names)
        self.assertGreaterEqual(len(names), 10)
        self.assertTrue(all(row["status"] == "passed" for row in result["assertions"]))

    def test_known_small_jam_vectors_and_bounded_backreferences(self):
        for noun, encoded in ((0, "02"), (1, "0c"), (2, "48"), ((0, 0), "29")):
            with self.subTest(noun=noun):
                self.assertEqual(G._jam(noun).hex(), encoded)
                self.assertEqual(G._cue(bytes.fromhex(encoded)), noun)
        repeated = tup(1 << 200, 1 << 200)
        self.assertEqual(G._cue(G._jam(repeated)), repeated)
        for raw in (b"", b"\0", b"\xff", b"\x02\0", b"\x02\x01", b"x" * (G.MAX_JAM + 1)):
            with self.subTest(raw=raw[:5]), self.assertRaises(ValueError):
                G._cue(raw)

    def test_every_required_record_is_required(self):
        for field in G.NOUN_FIELDS | G.JSON_FIELDS | G.TEXT_FIELDS:
            with self.subTest(field=field):
                self.reject(lambda value, field=field: value.pop(field))

    def test_missing_wrong_and_noncanonical_jam_integrity_fails(self):
        for field, replacement in (("jam_sha256", "0" * 64), ("jam_sha256", "missing"),
                                   ("jam_bytes", "01"), ("jam_bytes", "99999"), ("jam_hex", "0A"),
                                   ("jam_hex", "a"), ("jam_hex", "0200"), ("noun", "")):
            def change(value, field=field, replacement=replacement):
                obj = json.loads(value["captured_leave"])
                obj[field] = replacement
                value["captured_leave"] = j(obj)
            with self.subTest(field=field, replacement=replacement):
                self.reject(change)
        def missing_hash(value):
            obj = json.loads(value["captured_leave"])
            obj.pop("jam_sha256")
            value["captured_leave"] = j(obj)
        self.reject(missing_hash)

    def test_edited_captured_task_with_recomputed_hash_still_fails(self):
        self.reject(lambda value: value.update(delivered_leave=record(0)))
        self.reject(lambda value: value.update(captured_leave=value["delivered_leave_output"],
                                               delivered_leave=value["delivered_leave_output"]))
        def all_changed(value):
            captured = G._record(value["captured_leave"])
            fields = G._parts(captured, 9)
            fields[7] = a("watch")
            changed = tup(*fields)
            value["captured_leave"] = value["delivered_leave"] = record(changed)
            moves = G._list(G._record(value["captured_leave_moves"]))
            moves[1] = changed
            value["captured_leave_moves"] = record(lst(moves))
        self.reject(all_changed)

    def test_edited_duct_same_nonce_and_noncanonical_nonce_fail(self):
        self.reject(lambda value: value.update(old_duct=value["new_duct"]))
        self.reject(lambda value: value.update(new_nonce=value["old_nonce"]))
        self.reject(lambda value: value.update(new_nonce="02"))
        self.reject(lambda value: value.update(new_duct=record(lst([path("/invented"), path("/init")]))))

    def test_pending_incoming_history_or_observer_change_fails(self):
        for field in ("pending_after", "business_after_leave", "business_completed", "business_final",
                      "observer_after", "old_observer_after", "old_observer_completed"):
            def change(value, field=field):
                obj = json.loads(value[field])
                obj["unexpected_change"] = "changed"
                value[field] = j(obj)
            with self.subTest(field=field):
                self.reject(change)
        self.reject(lambda value: value.update(incoming_after=value["old_incoming_active"]))

    def test_no_retirement_or_wrong_fresh_pending_fails(self):
        self.reject(lambda value: value.update(old_incoming_retired=value["old_incoming_active"]))
        self.reject(lambda value: value.update(old_pending_retired=value["old_pending_active"]))
        self.reject(lambda value: value.update(expected_fresh_pending="2"))
        self.reject(lambda value: value.update(pending_before=value["old_pending_retired"],
                                               pending_after=value["old_pending_retired"]))

    def test_missing_live_leave_or_failed_control_fails(self):
        self.reject(lambda value: value.update(current_live_leave_control="failed"))
        self.reject(lambda value: value.update(live_pending_after=value["live_pending_before"]))
        self.reject(lambda value: value.update(live_leave_moves=value["captured_leave_moves"]))
        self.reject(lambda value: value.update(live_delivery_output=value["old_watch_gifts"]))

    def test_scope_cannot_be_promoted_to_other_native_requirement(self):
        for field, value in (("classification", "real-native-fake-ships"), ("requirement", "other-requirement"),
                             ("protocol", "stead.native-scheduled-gall/2"), ("status", "planned"),
                             ("transport", "Ames UDP"), ("late_old_leave", "failed")):
            with self.subTest(field=field):
                self.reject(lambda report, field=field, value=value: report.update({field: value}))

    def test_wrong_receipt_fact_and_missing_event_fail(self):
        self.reject(lambda value: value.update(receipt_sha256="0" * 64))
        def wrong_fact(value):
            obj = json.loads(value["observer_completed"])
            next(event for event in obj["events"].values() if event["kind"] == "fact")["payload_sha256"] = "0" * 64
            value["observer_completed"] = j(obj)
        self.reject(wrong_fact)
        def no_event(value):
            obj = json.loads(value["observer_completed"])
            obj["events"] = {}
            value["observer_completed"] = j(obj)
        self.reject(no_event)
        def changed_watch_ack(value):
            obj = json.loads(value["observer_completed"])
            next(event for event in obj["events"].values() if event["kind"] == "watch-ack")["source_provenance_sha256"] = "e" * 64
            value["observer_completed"] = j(obj)
        self.reject(changed_watch_ack)

    def test_duplicate_json_key_deep_input_and_malformed_types_fail(self):
        self.reject(lambda value: value.update(pending_before='{"total":"1","total":"0"}'))
        self.reject(lambda value: value.update(pending_before='{"x":' * 14 + "0" + "}" * 14))
        self.reject(lambda value: value.update(old_duct=record(0)))
        self.reject(lambda value: value.update(observer_before="null"))
        self.reject(lambda value: value.update(unknown="extra"))
        for invalid in (None, [], {}, {"status": True}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                G.validate(invalid)

    def test_empty_or_duplicate_assertion_inventory_cannot_pass(self):
        for invalid in ((), ("same", "same"), ("",)):
            with self.subTest(invalid=invalid), mock.patch.object(G, "ASSERTIONS", invalid), self.assertRaises(ValueError):
                G.validate(specimen())


if __name__ == "__main__":
    unittest.main(verbosity=2)

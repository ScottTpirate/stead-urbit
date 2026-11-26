"""Inert capture control and full byte-custody regressions; no native execution."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'scripts/ci/home_asset_rehearsal/evidence.py'
SPEC = importlib.util.spec_from_file_location('saved8_encoding_evidence', PATH)
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)


class Saved8EncodingTests(unittest.TestCase):
    def test_fixed_control_refuses_before_saved_state_or_chunk_requests(self):
        for response in ('0x0', '0x7361.7665.6438.6865.79', 'compiler refused', '', 'x' * 65):
            calls = []
            def dojo(source):
                calls.append(source)
                return {E.SUSPENDED: '%.n', E.DESK: '%release-test', E.ENCODING_CONTROL: response}[source]
            with self.subTest(response=response), self.assertRaises(ValueError):
                E.collect(dojo, 'seed8')
            self.assertEqual(calls, [E.SUSPENDED, E.DESK, E.ENCODING_CONTROL])
        error = TimeoutError('inert owned request')
        calls = []
        def interrupted(source):
            calls.append(source)
            if source == E.ENCODING_CONTROL:
                raise error
            return {E.SUSPENDED: '%.n', E.DESK: '%release-test'}[source]
        with self.assertRaises(TimeoutError) as raised:
            E.collect(interrupted, 'seed8')
        self.assertIs(raised.exception, error)
        self.assertEqual(calls, [E.SUSPENDED, E.DESK, E.ENCODING_CONTROL])
        self.assertEqual(E.ENCODING_CONTROL, "+home-ui-capture [262.144 'stead.saved8-hex-control/1']")
        # This one fixed control is outside the unchanged ordinary offset range.
        with self.assertRaises(ValueError):
            E.command(262144, '')

    def test_control_then_multichunk_bytes_and_final_fingerprint_remain_required(self):
        # Real canonical JSON/hex/hash checking around an explicitly inert byte vector.
        raw = bytes(range(256)) * 65 + b'\x01'
        fingerprint = 'a' * 64
        capture_pin = E.sha(b'stead.saved8-capture/1\0' + raw.hex().encode())
        calls = []
        def dojo(source):
            calls.append(source)
            if source == E.SUSPENDED: return '%.n'
            if source == E.DESK: return '%release-test'
            if source == E.ENCODING_CONTROL: return '0x73.6176.6564.3868.6578'
            if source == E.FINGERPRINT: return '0x' + fingerprint
            for offset in (0, E.CHUNK):
                previous = '' if offset == 0 else capture_pin
                if source == E.command(offset, previous):
                    part = raw[offset:offset + E.CHUNK]
                    row = dict.fromkeys(E.PINS, 'b' * 64)
                    row.update(protocol='stead.saved8-capture/1', offset=str(offset),
                        length=str(len(part)), total_bytes=str(len(raw)), data_hex=part.hex(),
                        capture_pin=capture_pin, vase_fingerprint=fingerprint)
                    return hex(int.from_bytes(E.canonical(row), 'little'))
            raise AssertionError('unexpected native request')
        value = E.collect(dojo, 'seed8')
        self.assertEqual(value['data'], raw)
        self.assertEqual(value['artifact_sha256'], E.sha(raw))
        self.assertEqual(value['capture_pin'], capture_pin)
        self.assertEqual(calls, [E.SUSPENDED, E.DESK, E.ENCODING_CONTROL, E.FINGERPRINT,
            E.command(0, ''), E.command(E.CHUNK, capture_pin), E.SUSPENDED, E.DESK, E.FINGERPRINT])
        original = dojo
        count = 0
        def changed_fingerprint(source):
            nonlocal count
            if source == E.FINGERPRINT:
                count += 1
                if count == 2: return '0x' + 'c' * 64
            return original(source)
        with self.assertRaises(ValueError):
            E.collect(changed_fingerprint, 'seed8')

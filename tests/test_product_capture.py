"""Authored capture boundary data only. No runtime or old-vase observation."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('product_capture_fixture', ROOT / 'scripts/urbit/product_capture.py')
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)
FP = 'a' * 64


def printed(raw):
    digits = format(int.from_bytes(raw, 'little'), 'x')
    groups = []
    while digits:
        groups.append(digits[-4:])
        digits = digits[:-4]
    groups.reverse()
    return '0x' + '.\n  '.join('.'.join(groups[i:i + 16]) for i in range(0, len(groups), 16))


def row(raw, offset=0, target='product'):
    selected = raw[offset:offset + capture.CHUNK]
    return {'protocol': 'stead.v10-capture/1', 'target': target,
            'offset': str(offset), 'length': str(len(selected)), 'total_bytes': str(len(raw)),
            'capture_pin': capture.domain('stead.v10-capture/1', raw.hex().encode()),
            'native_vase_fingerprint': FP, 'type_pin': 'b' * 64, 'payload_pin': 'c' * 64,
            'data_hex': selected.hex()}


class AuthoredSource:
    def __init__(self, raw, target='product'):
        self.raw, self.target, self.calls, self.index = raw, target, [], 0

    def dojo(self, ship, source):
        if ship != 'zod':
            raise AssertionError('Wrong authored ship')
        self.calls.append(source)
        if source == '.^(? %gu /=stead-home=/$)':
            return '%.n'
        offset = self.index * capture.CHUNK
        self.index += 1
        pin = '' if offset == 0 else row(self.raw)['capture_pin']
        if source != capture.source(self.target, offset, pin):
            raise AssertionError('Wrong exact capture command')
        return printed(capture.canonical(row(self.raw, offset, self.target)))

    def collect(self):
        return capture.collect(self.dojo, lambda: FP, self.target, FP)


class ProductCaptureTests(unittest.TestCase):
    def test_authored_two_chunks_preserve_zero_bytes_and_exact_scope(self):
        raw = b'prefix' + b'\0' * (capture.CHUNK - 6) + b'\0\0tail'
        source = AuthoredSource(raw)
        retained = source.collect()
        self.assertEqual(source.index, 2)
        self.assertEqual(capture.validate_record(retained), raw)
        self.assertIn('16.384', source.calls[2])
        self.assertEqual(retained['native_vase_fingerprint'], FP)
        self.assertEqual(retained['type_pin'], 'b' * 64)

    def test_duplicate_extra_noncanonical_or_nonstring_fields_refused(self):
        value = row(b'fixture')
        malformed = [json.dumps(value).encode(), capture.canonical(value | {'extra': ''}),
                     capture.canonical(value | {'offset': 0}),
                     capture.canonical(value)[:-1] + b',"offset":"0"}']
        for raw in malformed:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                capture.chunk(printed(raw), 'product', 0, '', FP)

    def test_target_time_free_source_and_pin_shapes_are_closed(self):
        for target, offset, pin in [('global', 0, ''), ('product', True, ''),
                                     ('product', 1, ''), ('product', 0, 'a' * 64),
                                     ('product', capture.CHUNK, "'; bad")]:
            with self.subTest(target=target, offset=offset), self.assertRaises(ValueError):
                capture.source(target, offset, pin)
        for change in ({'target': 'predecessor'}, {'capture_pin': 'x' * 64},
                       {'native_vase_fingerprint': 'd' * 64}, {'type_pin': ''}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                capture.chunk(printed(capture.canonical(row(b'fixture') | change)), 'product', 0, '', FP)

    def test_offsets_lengths_truncated_zero_bytes_and_size_cap_refused(self):
        value = row(b'zero\0tail')
        for change in ({'offset': '1'}, {'length': '7'}, {'total_bytes': '262145'},
                       {'data_hex': value['data_hex'][2:]}, {'length': '01'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                capture.chunk(printed(capture.canonical(value | change)), 'product', 0, '', FP)

    def test_changed_snapshot_on_second_chunk_is_not_collected(self):
        source = AuthoredSource(b'x' * (capture.CHUNK + 1))
        original = source.dojo
        def dojo(ship, command):
            result = original(ship, command)
            if source.index == 2:
                changed = row(source.raw, capture.CHUNK) | {'payload_pin': 'd' * 64}
                return printed(capture.canonical(changed))
            return result
        with self.assertRaises(ValueError):
            capture.collect(dojo, lambda: FP, 'product', FP)

    def test_final_idle_and_independent_fingerprint_are_mandatory(self):
        source = AuthoredSource(b'fixture')
        with self.assertRaises(ValueError):
            capture.collect(source.dojo, lambda: 'f' * 64, 'product', FP)
        source = AuthoredSource(b'fixture')
        original = source.dojo
        def resumed(ship, command):
            if command == '.^(? %gu /=stead-home=/$)' and source.index:
                return '%.y'
            return original(ship, command)
        with self.assertRaises(ValueError):
            capture.collect(resumed, lambda: FP, 'product', FP)

    def test_retained_artifact_bytes_and_numeric_types_are_exact(self):
        value = AuthoredSource(b'fixture').collect()
        for change in ({'artifact_bytes': 7.0}, {'artifact_bytes': True},
                       {'data_hex': 'aa' * 7}, {'artifact_sha256': 'f' * 64},
                       {'capture_pin': 'e' * 64}, {'extra': ''}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                capture.validate_record(value | change)

    def test_maximum_capture_is_sixteen_chunks_and_never_expands_cap(self):
        source = AuthoredSource(b'x' * capture.MAX_BYTES)
        self.assertEqual(capture.validate_record(source.collect()), source.raw)
        self.assertEqual(source.index, 16)
        source = AuthoredSource(b'x' * (capture.MAX_BYTES + 1))
        with self.assertRaises(ValueError):
            source.collect()

    def test_exports_require_exact_candidate_generator_and_two_targets(self):
        rows = {target: AuthoredSource(b'fixture', target).collect() for target in ('predecessor', 'product')}
        pin = {'bytes': 1, 'sha256': 'f' * 64}
        inputs = {'candidate_commit': capture.OLD_CANDIDATE, 'controller_commit': 'd' * 40,
                  'composed_files': {capture.GENERATOR: pin},
                  'controller_files': {capture.GENERATOR: pin, 'specs/urbit/toolchain.lock.json': pin}}
        files = capture.exports(rows, inputs, 'e' * 32, 'a' * 64)
        self.assertEqual(set(files), {'v10-old-predecessor.jam', 'v10-old-predecessor.json',
                                     'v10-old-product.jam', 'v10-old-product.json'})
        self.assertEqual(files['v10-old-product.jam'], b'fixture')
        descriptor = json.loads(files['v10-old-product.json'])
        self.assertFalse(descriptor['qualifies_phase'])
        self.assertEqual(descriptor['capture_stage'], 'actual-cold-suspended-product')
        for bad_rows, bad_inputs in [({'product': rows['product']}, inputs),
                (rows | {'extra': rows['product']}, inputs),
                (rows, inputs | {'candidate_commit': '0' * 40}),
                (rows, inputs | {'composed_files': {capture.GENERATOR: pin | {'bytes': 2}}}),
                (rows, inputs | {'controller_commit': 'unknown'}),
                (rows, inputs | {'controller_files': inputs['controller_files'] | {
                    'specs/urbit/toolchain.lock.json': pin | {'bytes': True}}})]:
            with self.subTest(), self.assertRaises(ValueError):
                capture.exports(bad_rows, bad_inputs, 'e' * 32, 'a' * 64)


if __name__ == '__main__':
    unittest.main()

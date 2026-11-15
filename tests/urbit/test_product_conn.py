"""Host admission tests only; native calls are deliberately not executed."""
from pathlib import Path
import hashlib
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import product_conn
import product_home_check


ID = '019939ba-4000-7000-8000-000000000001'
BINDING = '019939ba-4000-7000-8000-000000000202'
VALUE = {'protocol': 'stead.query/4', 'request_id': ID, 'title': 'λ\n'}
ACTIVATION = {'protocol': 'stead.product-activate/1', 'profile': 'native-human-doc/1',
              'expected_config_revision': '1', 'predecessor_sha256': 'a' * 64}


def dojo_atom(raw):
    return hex(int.from_bytes(raw, 'little'))


class ProductConnTests(unittest.TestCase):
    def test_result_route_binds_exact_protocol_unicode_bytes_and_identity(self):
        raw = product_conn.canonical(VALUE)
        expected = hashlib.sha256(b'stead.query/4\0' + raw).hexdigest()
        route = product_conn.result_route('bus', BINDING, 1, VALUE)
        self.assertEqual(route, f'/product/result/~bus/{BINDING}/1/{ID}/{expected}')
        self.assertNotEqual(route, product_conn.result_route('nec', BINDING, 1, VALUE))
        self.assertNotEqual(route, product_conn.result_route('bus', BINDING, 2, VALUE))

    def test_owner_receipt_is_a_distinct_exact_request_path(self):
        value = {'protocol': 'stead.owner-command/1', 'request_id': ID}
        expected = hashlib.sha256(b'stead.owner-command/1\0' + product_conn.canonical(value)).hexdigest()
        self.assertEqual(product_conn.owner_route(value), f'/product-owner-receipt/{ID}/{expected}')
        with self.assertRaises(ValueError):
            product_conn.owner_route(VALUE)

    def test_closed_product_driver_keeps_opaque_actual_exchange_evidence(self):
        sentinel = {'raw_frame_evidence': 'not a native verdict'}
        route = product_conn.result_route('bus', BINDING, 1, VALUE)
        with patch.object(product_conn.core_conn, 'exchange', return_value=sentinel) as exchange:
            observed = product_conn.run('vere', '/fake/.urb/conn.sock', 'query', route, product_conn.canonical(VALUE))
        self.assertIs(observed, sentinel)
        self.assertIn('%stead-product-check %noun', exchange.call_args.args[2])
        self.assertIn('~zod %stead-home %query', exchange.call_args.args[2])
        self.assertEqual(exchange.call_args.kwargs, {'timeout': 75})

    def test_unknown_modes_real_targets_and_overlong_requests_never_exchange(self):
        with patch.object(product_conn.core_conn, 'exchange') as exchange:
            for kwargs in ({'mode': 'configure'}, {'mode': 'query', 'target': 'sampel-palnet'},
                           {'mode': 'activate', 'raw': b'x' * 65537},
                           {'mode': 'activate', 'raw': b'{}\0'}, {'mode': 'activate', 'timeout': 76}):
                with self.subTest(kwargs={k: len(v) if isinstance(v, bytes) else v for k, v in kwargs.items()}):
                    with self.assertRaises(ValueError):
                        product_conn.run('vere', '/fake/socket', **kwargs)
            exchange.assert_not_called()

    def test_result_route_rejects_scope_suffix_and_noncanonical_revision(self):
        route = product_conn.result_route('bus', BINDING, 1, VALUE)
        bad = [route + '/', route + '/extra', route.replace('/1/', '/01/'),
               route.replace('/1/', '/18446744073709551616/'), route.replace('/product/', '/v3/'),
               route.replace('~bus', '~sampel-palnet'), route[:-1] + 'g', '/']
        with patch.object(product_conn.core_conn, 'exchange') as exchange:
            for selected in bad:
                with self.subTest(route=selected), self.assertRaises(ValueError):
                    product_conn.run('vere', '/fake/socket', 'query', selected)
            exchange.assert_not_called()

    def test_owner_pokes_and_receipt_watch_have_closed_distinct_carriers(self):
        receipt = product_conn.owner_route({'protocol': 'stead.owner-command/1', 'request_id': ID})
        with patch.object(product_conn.core_conn, 'exchange') as exchange:
            product_conn.run('vere', '/fake/socket', 'owner-receipt', receipt)
            self.assertIn('%owner-receipt', exchange.call_args.args[2])
            for mode, route, raw in [('activate', receipt, b'{}'), ('owner-command', receipt, b'{}'),
                                     ('owner-receipt', receipt, b'{}'), ('owner-receipt', '/', b'')]:
                with self.subTest(mode=mode, route=route), self.assertRaises(ValueError):
                    product_conn.run('vere', '/fake/socket', mode, route, raw)
            self.assertEqual(exchange.call_count, 1)

    def test_predecessor_input_requires_exact_canonical_native_generator_bytes(self):
        calls = []
        def dojo(ship, source):
            calls.append((ship, source))
            return dojo_atom(product_conn.canonical(ACTIVATION))
        self.assertEqual(product_home_check.activation_input(dojo), ACTIVATION)
        self.assertEqual(calls, [('zod', '+stead-product-predecessor')])

    def test_predecessor_input_rejects_wrong_profile_fields_and_noncanonical_bytes(self):
        variants = [product_conn.canonical(ACTIVATION | {'profile': 'live'}),
                    product_conn.canonical(ACTIVATION | {'actor': 'owner'}),
                    product_conn.canonical(ACTIVATION | {'expected_config_revision': '01'}),
                    product_conn.canonical(ACTIVATION | {'expected_config_revision': 1}),
                    product_conn.canonical(ACTIVATION | {'expected_config_revision': str(2**64)}),
                    product_conn.canonical(ACTIVATION | {'predecessor_sha256': '0' * 63}),
                    json.dumps(ACTIVATION).encode(), b'[]']
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                product_home_check.activation_input(lambda *_: dojo_atom(raw))
        for raw in ('', '0xgg', '0x' + 'a' * 16384, 'terminal failure'):
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                product_home_check.activation_input(lambda *_: raw)

    def test_read_evidence_rejects_wrong_protocol_request_scope_and_pins(self):
        request = {'protocol': 'stead.doc-change-query/1', 'request_id': ID, 'kind': 'body',
                   'project_id': ID, 'work_id': ID, 'change_id': ID, 'result_revision': '2',
                   'result_digest': 'a' * 64, 'side': 'after', 'cursor': ''}
        response = {**request, 'protocol': 'stead.doc-change-query-result/1', 'status': 'read',
                    'authority_epoch': '1', 'generation': 'b' * 64, 'rows': {'0': {'markdown': 'exact'}}}
        self.assertTrue(product_home_check.read_matches(response, request))
        for field in ('protocol', 'request_id', 'kind', 'project_id', 'work_id', 'change_id',
                      'result_revision', 'result_digest', 'side', 'authority_epoch', 'generation'):
            with self.subTest(field=field):
                self.assertFalse(product_home_check.read_matches(response | {field: 'wrong'}, request))
        self.assertFalse(product_home_check.read_matches(response | {'actor': 'fabricated'}, request))
        self.assertFalse(product_home_check.read_matches(response | {'rows': {'1': {}}}, request))
        request = {'protocol': 'stead.query/4', 'request_id': ID, 'kind': 'work', 'project_id': ID,
                   'container_id': '', 'resource_id': ID, 'search': '', 'cursor': ''}
        response = {k: request[k] for k in ('request_id', 'kind', 'project_id', 'container_id', 'resource_id', 'cursor')}
        response.update(protocol='stead.query-result/4', status='read', authority_epoch='1',
                        generation='b' * 64, rows={'0': {}})
        self.assertTrue(product_home_check.read_matches(response, request))
        self.assertFalse(product_home_check.read_matches(response | {'resource_id': ''}, request))

    def test_owner_receipt_evidence_requires_exact_protocol_operation_and_cas(self):
        command = {'protocol': 'stead.owner-command/1', 'request_id': ID, 'operation': 'principal.declare',
                   'expected_revision': '1', 'payload': {}}
        receipt = {'protocol': 'stead.owner-receipt/1', 'status': 'accepted', 'request_id': ID,
                   'canonical_sha256': product_conn.digest(command['protocol'], product_conn.canonical(command)),
                   'operation': command['operation'], 'expected_revision': '1', 'resulting_revision': '2',
                   'recorded_at_ms': '1000', 'error': '', 'capacity_class': 'ordinary'}
        self.assertTrue(product_home_check.owner_matches(receipt, command))
        for field in ('protocol', 'operation', 'expected_revision', 'resulting_revision', 'error', 'canonical_sha256'):
            with self.subTest(field=field):
                self.assertFalse(product_home_check.owner_matches(receipt | {field: 'wrong'}, command))
        self.assertFalse(product_home_check.owner_matches(receipt | {'recorded_at_ms': str(2**64)}, command))


if __name__ == '__main__':
    unittest.main()

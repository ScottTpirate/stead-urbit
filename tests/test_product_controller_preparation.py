"""Host shape checks only. No Hoon/native runtime or child is executed."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PREPARED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import team_check  # Real host helper imports, before private overlay resolution.
import review_prepare


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, PREPARED / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


conn = load('product_conn', 'scripts/urbit/product_conn.py')
load('product_home_check', 'scripts/urbit/product_home_check.py')
controller = load('prepared_product_controller', 'scripts/urbit/product_controller.py')


class PreparedControllerTests(unittest.TestCase):
    def setUp(self):
        self.activate = {'protocol': 'stead.product-activate/1', 'profile': 'native-human-doc/1',
            'expected_config_revision': '1', 'predecessor_sha256': 'a' * 64}
        self.expected = self.activate | {'protocol': 'stead.product-checkpoint/1', 'target': 'predecessor'}

    def atom(self, value, *, raw=None):
        raw = conn.canonical(value) if raw is None else raw
        return hex(int.from_bytes(raw, 'little'))

    def test_exact_actual_predecessor_shape(self):
        self.assertEqual(controller.checkpoint_value(self.atom(self.expected), self.activate), self.expected)

    def test_completed_product_is_never_partial_evidence(self):
        with self.assertRaises(ValueError):
            controller.checkpoint_value(self.atom(self.expected | {'target': 'product'}), self.activate)

    def test_changed_prefix_or_configuration_is_rejected(self):
        for mutation in ({'predecessor_sha256': 'b' * 64}, {'expected_config_revision': '2'}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                controller.checkpoint_value(self.atom(self.expected | mutation), self.activate)

    def test_noncanonical_extra_or_wrong_profile_is_rejected(self):
        variants = [self.atom(self.expected, raw=conn.canonical(self.expected) + b' '),
                    self.atom(self.expected | {'available': 'yes'}),
                    self.atom(self.expected | {'profile': 'live-synthetic'})]
        for value in variants:
            with self.subTest(value=value[:40]), self.assertRaises(ValueError):
                controller.checkpoint_value(value, self.activate)

    def test_bounded_atomic_output_required(self):
        for value in ('%.y', '0xnothex', '0x' + 'a' * 16384):
            with self.subTest(value=value[:40]), self.assertRaises(ValueError):
                controller.checkpoint_value(value, self.activate)

    def test_paused_carrier_uses_only_fixed_controller_thread(self):
        with patch.object(conn.core_conn, 'exchange', return_value={'native': 'mock'}) as exchange:
            self.assertEqual(conn.run('vere', '/socket', 'activate-paused', '/', b'{}'), {'native': 'mock'})
            args, kwargs = exchange.call_args
            self.assertIn('%stead-product-checkpoint', args[2])
            self.assertIn('[~zod %stead-home %activate-paused ~', args[2])
            self.assertEqual(kwargs, {'timeout': 75})

    def test_paused_carrier_rejects_target_route_and_deadline_expansion(self):
        with patch.object(conn.core_conn, 'exchange') as exchange:
            for kwargs in ({'target': 'bus'}, {'route': '/unrelated'}, {'timeout': 76}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    conn.run('vere', '/socket', 'activate-paused', raw=b'{}', **kwargs)
            exchange.assert_not_called()

    def test_normal_activation_keeps_original_carrier(self):
        with patch.object(conn.core_conn, 'exchange', return_value={}) as exchange:
            conn.run('vere', '/socket', 'activate', '/', b'{}')
            self.assertIn('%stead-product-check ', exchange.call_args.args[2])
            self.assertNotIn('%stead-product-checkpoint', exchange.call_args.args[2])


if __name__ == '__main__':
    unittest.main()

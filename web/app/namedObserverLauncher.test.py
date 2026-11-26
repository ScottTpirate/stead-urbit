"""Inert TLS-preflight cases: no socket, subprocess, browser or identity call."""
import base64
import hashlib
from pathlib import Path
import unittest
from unittest import mock
import named_observer as launcher


class NamedPreflightTests(unittest.TestCase):
    def test_ca_hostname_and_exact_key_pin_are_required_before_admission(self):
        der = b'synthetic public key'
        expected = base64.b64encode(hashlib.sha256(der).digest()).decode()
        context = mock.MagicMock()
        context.wrap_socket.return_value.__enter__.return_value.getpeercert.return_value = b'synthetic certificate'
        with mock.patch.object(launcher.ssl, 'create_default_context', return_value=context) as ca, \
             mock.patch.object(launcher.socket, 'create_connection') as connect, \
             mock.patch.object(launcher.subprocess, 'check_output', side_effect=[b'public key', der]) as decode:
            launcher.verify_forward('https://home.example.invalid', 14043, expected, Path('/synthetic/ca.pem'))
            ca.assert_called_once_with(cafile='/synthetic/ca.pem')
            connect.assert_called_once_with(('127.0.0.1', 14043), timeout=5)
            self.assertEqual(context.wrap_socket.call_args.kwargs, {'server_hostname': 'home.example.invalid'})
            self.assertEqual(decode.call_count, 2)
        with mock.patch.object(launcher.ssl, 'create_default_context', return_value=context), \
             mock.patch.object(launcher.socket, 'create_connection'), \
             mock.patch.object(launcher.subprocess, 'check_output', side_effect=[b'public key', b'wrong public key']):
            with self.assertRaisesRegex(ValueError, 'public key changed'):
                launcher.verify_forward('https://home.example.invalid', 14043, expected, Path('/synthetic/ca.pem'))

    def test_weakened_origin_or_forward_never_opens_a_connection(self):
        for origin, port in [('http://home.example.invalid', 14043),
                ('https://user:password@home.example.invalid', 14043),
                ('https://home.example.invalid/another-app', 14043),
                ('https://home.example.invalid', True), ('https://home.example.invalid', 0)]:
            with self.subTest(origin=origin, port=port), \
                 mock.patch.object(launcher.socket, 'create_connection') as connect:
                with self.assertRaises(ValueError):
                    launcher.verify_forward(origin, port, 'A' * 43 + '=', Path('/synthetic/ca.pem'))
                connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()

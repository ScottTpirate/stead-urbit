import fcntl
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import pilot_start


class PilotStart(unittest.TestCase):
    def test_startup_injection_uses_role_and_seals_original_bytes(self):
        jam = b'native jam stand-in'
        frame = b'\0' + len(jam).to_bytes(4, 'little') + jam
        for role in ('home', 'identity'):
            with self.subTest(role=role), patch.object(pilot_start.core_conn, 'evaluate', return_value=(frame, b'')) as evaluate:
                descriptor = pilot_start.suspension_ovum(Path('/opt/vere'), role)
                try:
                    evaluate.assert_called_once_with(Path('/opt/vere'), '-jn', f'[[%g %stead-startup ~] [%idle %stead-{role}]]'.encode())
                    self.assertEqual(os.read(descriptor, len(jam) + 1), jam)
                    self.assertTrue(fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) & fcntl.F_SEAL_WRITE)
                    with self.assertRaises(PermissionError):
                        os.pwrite(descriptor, b'a', 0)
                finally:
                    os.close(descriptor)

    def test_incomplete_frame_and_invalid_listener_fail_before_launch(self):
        with patch.object(pilot_start.core_conn, 'evaluate', return_value=(b'\0\x03\0\0\0ab', b'')):
            with self.assertRaisesRegex(ValueError, 'Incomplete startup suspension frame'):
                pilot_start.suspension_ovum('/opt/vere', 'home')
        for ports in ((0, 8080, 8443), (31337, 443, 8443), (31337, 8443, 8443)):
            with self.subTest(ports=ports), self.assertRaises(ValueError):
                pilot_start.arguments('/opt/vere', '/var/lib/ship', 3, *ports)

    def test_launch_only_resumes_the_existing_pier_with_loopback_http(self):
        self.assertEqual(pilot_start.arguments('/opt/vere', '/var/lib/ship', 3, 31337, 8080, 8443),
                         ['/opt/vere', '--no-dock', '--no-tty', '--http-ip', '127.0.0.1', '--ames-port', '31337',
                          '--http-port', '8080', '--https-port', '8443', '-I', '/proc/self/fd/3', '/var/lib/ship'])


if __name__ == '__main__':
    unittest.main()

import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from git_pack_oracle import PackError, unpack


def entry(kind, data, base=b'', declared=None):
    size = len(data) if declared is None else declared
    header = bytearray([(kind << 4) | (size & 15)])
    size >>= 4
    while size:
        header[-1] |= 128
        header.append(size & 127)
        size >>= 7
    return bytes(header) + base + zlib.compress(data)


def pack(*entries):
    body = b'PACK' + struct.pack('>II', 2, len(entries)) + b''.join(entries)
    return body + hashlib.sha1(body).digest()


def oid(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


class GitPackTests(unittest.TestCase):
    def test_stock_git_packs_expand_to_original_objects(self):
        git = shutil.which('git')
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_ALLOW_PROTOCOL': ''}
        with tempfile.TemporaryDirectory() as path:
            def command(*args, data=None):
                return subprocess.run([git, '-C', path, *args], input=data, capture_output=True,
                                      check=True, timeout=15, env=env).stdout

            command('init', '--bare', '--template=', '--object-format=sha1')
            base = b''.join(f'An unchanged value for line {n:05d}\n'.encode() for n in range(1024))
            inputs = [base[:18000] + str(n).encode() + base[18001:] for n in range(6)]
            expected = {}
            for body in inputs:
                value = command('hash-object', '-w', '--stdin', data=body).decode().strip()
                self.assertEqual(value, oid(body))
                expected[value] = ('blob', body)
            object_list = ('\n'.join(expected) + '\n').encode()
            for options in ((), ('--delta-base-offset',)):
                wire = command('pack-objects', '--stdout', '--threads=1', '--window=10', '--depth=10',
                               *options, data=object_list)
                self.assertEqual(unpack(wire), expected)
                trailer = wire[-20:].hex()
                command('index-pack', '--strict', '--stdin', data=wire)
                details = command('verify-pack', '-v', f'objects/pack/pack-{trailer}.idx')
                self.assertTrue(any(len(line.split()) == 7 and line[:40].decode() in expected
                                    for line in details.splitlines() if len(line) >= 40), details)

    def test_forward_reference_delta_is_resolved(self):
        base = b'abcd'
        target = b'abcd!'
        patch = b'\x04\x05\x90\x04\x01!'
        data = pack(entry(7, patch, bytes.fromhex(oid(base))), entry(3, base))
        self.assertEqual(unpack(data), {oid(base): ('blob', base), oid(target): ('blob', target)})

    def test_checksum_valid_malformed_entries_are_rejected(self):
        base = b'abcd'
        reference = bytes.fromhex(oid(base))
        cases = [
            (pack(entry(3, b'x' * 4096, declared=1)), 'inflated size exceeds'),
            (pack(entry(3, b'x', declared=2)), 'inflated size differs'),
            (pack(entry(6, b'', b'\x01')), 'offset'),
            (pack(entry(7, b'\x04\x04\x90\x04', reference)), 'unresolved'),
            (pack(entry(3, base), entry(7, b'\x04\x04\x90\x05', reference)), 'delta copy'),
            (pack(entry(3, base), entry(7, b'\x04\x00\x00', reference)), 'invalid delta literal'),
        ]
        for data, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(PackError, reason):
                unpack(data)
        data = bytearray(pack(entry(3, base)))
        data[-1] ^= 1
        with self.assertRaisesRegex(PackError, 'checksum'):
            unpack(data)


if __name__ == '__main__':
    unittest.main()

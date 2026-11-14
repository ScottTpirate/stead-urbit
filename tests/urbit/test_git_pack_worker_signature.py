"""Independent OpenSSL verification of exact worker proof signatures."""
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import git_pack_worker_signature as worker


PROOF = b'{"proof":"exact bytes"}\n'


@unittest.skipUnless(Path('/usr/bin/openssl').is_file(), 'Unprivileged stock OpenSSL is required')
class WorkerSignatureTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.key = self.generate('worker')

    def openssl(self, *args):
        return subprocess.run(['/usr/bin/openssl', *args], cwd=self.root, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              env={'LC_ALL': 'C', 'OPENSSL_CONF': '/dev/null'}, timeout=5)

    def generate(self, name, algorithm='ED25519'):
        key = self.root / f'{name}.pem'
        result = self.openssl('genpkey', '-algorithm', algorithm, '-out', key.name)
        self.assertEqual(result.returncode, 0)
        key.chmod(0o600)
        result = self.openssl('pkey', '-in', key.name, '-pubout', '-out', f'{name}.pub')
        self.assertEqual(result.returncode, 0)
        return key

    def verifies(self, signature, key_name, proof=PROOF, generation=1):
        binary = b'stead.git-pack-worker-attestation/1\x00' + str(generation).encode() + b'\x00'
        binary += sha256(proof).hexdigest().encode('ascii')
        (self.root / 'message').write_bytes(binary)
        (self.root / 'signature').write_bytes(bytes.fromhex(signature))
        return self.openssl('pkeyutl', '-verify', '-pubin', '-rawin', '-inkey', f'{key_name}.pub',
                            '-sigfile', 'signature', '-in', 'message').returncode == 0

    def test_independent_verification_binds_exact_proof_and_generation(self):
        signature = worker.sign(PROOF, 1, self.key)
        self.assertRegex(signature, r'^[0-9a-f]{128}$')
        self.assertEqual(signature, worker.sign(PROOF, 1, self.key))
        self.assertTrue(self.verifies(signature, 'worker'))
        self.assertFalse(self.verifies(signature, 'worker', proof=PROOF.rstrip()))
        self.assertFalse(self.verifies(signature, 'worker', generation=2))
        changed = ('a' if signature[0] != 'a' else 'b') + signature[1:]
        self.assertFalse(self.verifies(changed, 'worker'))

    def test_rotated_key_and_maximum_generation(self):
        rotated = self.generate('rotated')
        old = worker.sign(PROOF, 1, self.key)
        new = worker.sign(PROOF, 2**64 - 1, rotated)
        self.assertTrue(self.verifies(new, 'rotated', generation=2**64 - 1))
        self.assertFalse(self.verifies(new, 'worker', generation=2**64 - 1))
        self.assertFalse(self.verifies(old, 'rotated'))

    def test_bounds_and_exact_owned_private_key_profile(self):
        for generation in (False, 0, -1, 2**64, '1'):
            with self.subTest(generation=generation), self.assertRaisesRegex(ValueError, 'signing-generation'):
                worker.sign(PROOF, generation, self.key)
        for proof in (b'', b' ' * 65_537, bytearray(PROOF)):
            with self.subTest(proof_size=len(proof)), self.assertRaisesRegex(ValueError, 'signing-proof-bound'):
                worker.sign(proof, 1, self.key)
        self.assertTrue(self.verifies(worker.sign(b'a' * 65_536, 1, self.key), 'worker', proof=b'a' * 65_536))
        self.key.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'private-key'):
            worker.sign(PROOF, 1, self.key)
        self.key.chmod(0o600)
        link = self.root / 'link.pem'
        link.symlink_to(self.key)
        with self.assertRaisesRegex(ValueError, 'signing-unavailable'):
            worker.sign(PROOF, 1, link)
        link.unlink()
        os.link(self.key, link)
        with self.assertRaisesRegex(ValueError, 'private-key'):
            worker.sign(PROOF, 1, self.key)

    def test_other_key_type_and_private_path_replacement_are_refused(self):
        other = self.generate('other', algorithm='ED448')
        with self.assertRaisesRegex(ValueError, 'signing-key-type'):
            worker.sign(PROOF, 1, other)
        sign_held = worker.sign_held
        replacement = self.generate('replacement')

        def swapped(fd, data):
            result = sign_held(fd, data)
            replacement.replace(self.key)
            return result

        with patch.object(worker, 'sign_held', side_effect=swapped), self.assertRaisesRegex(ValueError, 'key-changed'):
            worker.sign(PROOF, 1, self.key)


if __name__ == '__main__':
    unittest.main()

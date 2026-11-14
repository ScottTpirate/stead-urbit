"""Tiny exact-tree and installed GnuPG controls; no native runtime or live data."""
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import checkpoint_archive as checkpoint


class CheckpointArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-checkpoint-archive-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pier = self.root / 'source'
        for name in ('.urb', 'base', 'retained-alias'):
            directory = self.pier / name
            directory.mkdir(mode=0o700, parents=True)
            (directory / 'state').write_bytes(name.encode() + b'\x00\r\n')
        self.archive = self.root / 'checkpoint.tar'
        self.expected = checkpoint.archive_tree(self.pier, self.archive)
        self.binary = shutil.which('gpg')
        self.pin = hashlib.sha256(Path(self.binary).read_bytes()).hexdigest() if self.binary else None
        self.key = self.root / 'synthetic.key'
        self.key.write_bytes(os.urandom(32).hex().encode() + b'\n')
        self.key.chmod(0o600)

    def test_exact_archive_restores_every_retained_mount_and_refuses_overwrite(self):
        restored = self.root / 'restored'
        self.assertEqual(checkpoint.extract_tree(self.archive, restored, self.expected), self.expected)
        self.assertEqual(checkpoint.fingerprint(restored), checkpoint.fingerprint(self.pier))
        self.assertEqual((restored / 'retained-alias/state').read_bytes(), b'retained-alias\x00\r\n')
        with self.assertRaises(OSError):
            checkpoint.extract_tree(self.archive, restored, self.expected)
        self.assertEqual(checkpoint.fingerprint(restored), self.expected)

    def test_wrong_expected_tree_and_nonzero_trailing_bytes_never_publish(self):
        output = self.root / 'restored'
        with self.assertRaisesRegex(ValueError, 'tree-differs'):
            checkpoint.extract_tree(self.archive, output, self.expected | {'sha256': '0' * 64})
        self.assertFalse(output.exists())
        with self.archive.open('ab') as file:
            file.write(b'hidden second payload')
        with self.assertRaisesRegex(ValueError, 'trailing-data'):
            checkpoint.extract_tree(self.archive, output, self.expected)
        self.assertFalse(output.exists())

    def test_hostile_archive_paths_links_duplicates_and_special_files_are_rejected(self):
        for kind in ('parent', 'absolute', 'symlink', 'hardlink', 'device', 'duplicate', 'large'):
            with self.subTest(kind=kind):
                source = self.root / (kind + '.tar')
                with tarfile.open(source, 'w', format=tarfile.USTAR_FORMAT) as archive:
                    member = tarfile.TarInfo('../escaped' if kind == 'parent' else '/escaped' if kind == 'absolute' else 'entry')
                    member.size = 0
                    if kind == 'symlink':
                        member.type, member.linkname = tarfile.SYMTYPE, '/tmp'
                    elif kind == 'hardlink':
                        member.type, member.linkname = tarfile.LNKTYPE, 'other'
                    elif kind == 'device':
                        member.type = tarfile.CHRTYPE
                    elif kind == 'large':
                        member.size = checkpoint.MAX_FILE + 1
                    if kind == 'large':
                        archive.fileobj.write(member.tobuf(format=tarfile.USTAR_FORMAT))
                    else:
                        archive.addfile(member)
                    if kind == 'duplicate':
                        archive.addfile(member)
                source.chmod(0o600)
                target = self.root / ('restored-' + kind)
                with self.assertRaises((ValueError, tarfile.TarError)):
                    checkpoint.extract_tree(source, target, self.expected)
                self.assertFalse(target.exists())
        self.assertFalse((self.root / 'escaped').exists())

    def test_checkpoint_source_links_or_runtime_lock_are_rejected(self):
        (self.pier / '.vere.lock').write_bytes(b'owned')
        with self.assertRaisesRegex(ValueError, 'source-running'):
            checkpoint.archive_tree(self.pier, self.root / 'bad.tar')
        (self.pier / '.vere.lock').unlink()
        (self.pier / 'redirect').symlink_to('/tmp')
        with self.assertRaises(ValueError):
            checkpoint.archive_tree(self.pier, self.root / 'bad.tar')
        self.assertFalse((self.root / 'bad.tar').exists())

    @unittest.skipUnless(shutil.which('gpg'), 'Installed GnuPG required for actual AEAD execution')
    def test_installed_pinned_gpg_aead_roundtrip_then_exact_tree_restore(self):
        cipher, plain = self.root / 'checkpoint.gpg', self.root / 'decrypted.tar'
        result = checkpoint.crypt_file(self.archive, cipher, self.key, self.binary, self.pin)
        self.assertEqual(result['algorithm'], 'GnuPG-AES256-OCB')
        checkpoint.crypt_file(cipher, plain, self.key, self.binary, self.pin, decrypt=True)
        self.assertEqual(plain.read_bytes(), self.archive.read_bytes())
        self.assertEqual(checkpoint.extract_tree(plain, self.root / 'restored', self.expected), self.expected)

    @unittest.skipUnless(shutil.which('gpg'), 'Installed GnuPG required for actual AEAD execution')
    def test_corrupt_ciphertext_wrong_key_and_wrong_binary_pin_never_publish(self):
        cipher = self.root / 'checkpoint.gpg'
        checkpoint.crypt_file(self.archive, cipher, self.key, self.binary, self.pin)
        destination = self.root / 'refused.tar'
        with self.assertRaisesRegex(ValueError, 'gpg-pin'):
            checkpoint.crypt_file(cipher, destination, self.key, self.binary, '0' * 64, decrypt=True)
        raw = cipher.read_bytes()
        cipher.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'authentication'):
            checkpoint.crypt_file(cipher, destination, self.key, self.binary, self.pin, decrypt=True)
        self.assertFalse(destination.exists())
        cipher.write_bytes(raw)
        self.key.write_bytes(os.urandom(32).hex().encode() + b'\n')
        with self.assertRaisesRegex(ValueError, 'authentication'):
            checkpoint.crypt_file(cipher, destination, self.key, self.binary, self.pin, decrypt=True)
        self.assertFalse(destination.exists())

    @unittest.skipUnless(shutil.which('gpg'), 'Installed GnuPG required for actual AEAD execution')
    def test_legacy_mdc_ciphertext_is_rejected_by_explicit_aead_profile(self):
        home = self.root / 'gnupg'
        home.mkdir(mode=0o700)
        cipher = self.root / 'legacy.gpg'
        with self.key.open('rb') as key:
            command = [self.binary, '--no-options', '--homedir', str(home), '--batch', '--no-tty', '--no-autostart',
                       '--pinentry-mode', 'loopback', '--passphrase-fd', str(key.fileno()), '--no-symkey-cache',
                       '--no-random-seed-file', '--rfc4880', '--cipher-algo', 'AES256', '--s2k-count', '65536',
                       '--output', str(cipher), '--symmetric', str(self.archive)]
            done = subprocess.run(command, pass_fds=(key.fileno(),), capture_output=True, timeout=10)
        self.assertEqual(done.returncode, 0)
        cipher.chmod(0o600)
        destination = self.root / 'refused.tar'
        with self.assertRaisesRegex(ValueError, 'authentication'):
            checkpoint.crypt_file(cipher, destination, self.key, self.binary, self.pin, decrypt=True)
        self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()

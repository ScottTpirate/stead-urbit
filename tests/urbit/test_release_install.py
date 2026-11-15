"""Host-only install-controller checks. Native Dojo responses are mocked."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import release_install as install


class ReleaseInstallTests(unittest.TestCase):
    def test_fingerprint_keeps_whole_product_target_and_rejects_native_failure(self):
        # Mocked Dojo verifies controller construction/output handling only.
        # The configured native lane must execute both target variants.
        native = SimpleNamespace(dojo=Mock(return_value='0x1'))
        self.assertEqual(install.saved_home_fingerprint(native, authoritative=True), f'{1:064x}')
        source = native.dojo.call_args.args[0]
        self.assertIn('(shax (jam -.+>.q.saved))', source)
        self.assertIn("?>  =('native-human-doc/1' profile.stored)", source)
        self.assertIn('(shax (jam [profile.stored target.stored code.stored mode.stored retired.stored packs.stored external.stored reviews.stored]))', source)
        for authoritative in (False, True):
            for reply in ('native assertion failed', '0x' + 'f' * 65):
                with self.subTest(authoritative=authoritative, reply=reply), self.assertRaises(ValueError):
                    install.saved_home_fingerprint(SimpleNamespace(dojo=Mock(return_value=reply)), authoritative=authoritative)

    def test_no_preserved_piers_or_writable_input_alias_in_namespace(self):
        state = Path('/tmp/owned-release-proof')
        command = install.sandbox_command(state, Path('/tmp/guard'), 'a' * 32,
                                          {'kernel': {'directory': 'pinned-kernel'}}, Path('/tmp/toolchain'))
        writes = [(command[index + 1], command[index + 2]) for index, token in enumerate(command) if token == '--bind']
        self.assertEqual(writes, [(str(state / 'work'), '/state')])
        reads = [(command[index + 1], command[index + 2]) for index, token in enumerate(command) if token == '--ro-bind']
        for name in ('package', 'controller', 'support', 'helpers'):
            self.assertIn((str(state / name), '/' + name), reads)
        self.assertFalse(any('.piers' in token for token in command))
        self.assertIn('--unshare-all', command)
        self.assertIn('--die-with-parent', command)
        self.assertIn('--clearenv', command)

    def test_typed_kelvin_and_bill_have_distinct_readback_from_raw_files(self):
        native = SimpleNamespace(dojo=Mock(return_value='%.y'), check=Mock())
        install.clay_readback(native, {'sys.kelvin': '0' * 64, 'desk.bill': '1' * 64,
                                     'app/stead-home.hoon': '2' * 64}, 'stead-home')
        sources = [call.args[0] for call in native.dojo.call_args_list]
        self.assertTrue(any('[%zuse 408]' in source for source in sources))
        self.assertTrue(any('~[%stead-home]' in source for source in sources))
        self.assertEqual(sum('sha-256l:sha' in source for source in sources), 1)

    def test_failed_clay_readback_is_not_reported_as_installed(self):
        native = SimpleNamespace(dojo=Mock(side_effect=['%.y', '%.n']), check=Mock())
        with patch.object(install.time, 'monotonic', side_effect=[0, 0, 0, 61]), patch.object(install.time, 'sleep'):
            with self.assertRaisesRegex(TimeoutError, 'content differs'):
                install.clay_readback(native, {'app/stead-home.hoon': '0' * 64}, 'stead-home')

    def test_clay_readback_waits_for_exact_bytes_after_old_file_exists(self):
        native = SimpleNamespace(dojo=Mock(side_effect=['%.y', '%.n', '%.y', '%.y']), check=Mock())
        with patch.object(install.time, 'sleep'):
            install.clay_readback(native, {'app/stead-home.hoon': '0' * 64}, 'stead-home')
        self.assertEqual(native.dojo.call_args_list[1].args, native.dojo.call_args_list[3].args)
        native.check.assert_called_once()

    def test_new_desk_waits_for_hoon_mark_before_staging_typed_asset(self):
        with tempfile.TemporaryDirectory(prefix='stead-release-controller-') as temporary:
            root = Path(temporary)
            package = root / 'package'
            package.mkdir()
            (package / 'sys.kelvin').write_text('[%zuse 408]\n')
            (package / 'mar').mkdir()
            (package / 'mar/stead-asset.hoon').write_text('mark')
            (package / 'asset.stead-asset').write_text('content')
            mount = root / 'pier' / install.DESK
            mount.mkdir(parents=True)
            (mount / 'sys.kelvin').write_text('[%zuse 408]\n')

            def readback(_native, files, _agent):
                if 'mar/stead-asset.hoon' in files:
                    self.assertEqual(set(files), {'mar/stead-asset.hoon'})
                    self.assertFalse((mount / 'asset.stead-asset').exists())
                else:
                    self.assertTrue((mount / 'asset.stead-asset').is_file())

            native = SimpleNamespace(pier=mount.parent, dojo=Mock(), check=Mock())
            with patch.object(install, 'clay_readback', side_effect=readback) as read:
                self.assertEqual(install.install_desk(native, 'stead-home', package), install.inventory(package))
            self.assertEqual(read.call_count, 2)
            self.assertEqual([call.args[0] for call in native.dojo.call_args_list if call.args[0].startswith('|commit')],
                             ['|commit %release-test', '|commit %release-test'])

    def test_foreign_files_in_new_desk_are_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix='stead-release-controller-') as temporary:
            root = Path(temporary)
            package = root / 'package'
            package.mkdir()
            (package / 'sys.kelvin').write_text('[%zuse 408]\n')
            pier = root / 'pier'
            mount = pier / install.DESK
            mount.mkdir(parents=True)
            sentinel = mount / 'unexpected'
            sentinel.write_text('keep this evidence')
            native = SimpleNamespace(pier=pier, dojo=Mock(), check=Mock())
            with self.assertRaisesRegex(ValueError, 'undeclared files'):
                install.install_desk(native, 'stead-home', package)
            self.assertEqual(sentinel.read_text(), 'keep this evidence')
            self.assertFalse(any(call.args[0].startswith('|commit') for call in native.dojo.call_args_list))

    def test_agent_lifecycle_waits_for_observed_transition(self):
        native = SimpleNamespace(dojo=Mock(side_effect=['%.n', '%.n', '%.y']), check=Mock())
        with patch.object(install.time, 'sleep'):
            install.wait_agent(native, 'stead-home', True)
        self.assertEqual(native.dojo.call_count, 3)
        self.assertEqual(native.check.call_count, 2)

    def test_malformed_agent_status_and_unapproved_role_fail(self):
        native = SimpleNamespace(dojo=Mock(return_value='compiler error'), check=Mock())
        with self.assertRaisesRegex(ValueError, 'not a boolean'):
            install.wait_agent(native, 'stead-home', True)
        with self.assertRaisesRegex(ValueError, 'verified Stead role'):
            install.install_desk(native, 'foreign-agent')


if __name__ == '__main__':
    unittest.main()

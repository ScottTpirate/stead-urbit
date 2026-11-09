"""Host-only recovery controls using disposable file fixtures."""
import hashlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import release_recovery as recovery


class ReleaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-release-recovery-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / 'source'
        self.source.mkdir(mode=0o700)
        for name in ('.urb', recovery.install.DESK):
            (self.source / name).mkdir(mode=0o700)
        self.journal = self.source / '.urb/synthetic-journal'
        self.journal.write_bytes(b'recorded synthetic state')
        self.destination = self.directory / 'copies'
        self.destination.mkdir(mode=0o700)

    def test_offline_backup_and_restore_copy_exact_bytes_without_changing_source(self):
        before = recovery.install.checkpoint_tree(self.source, installed=True)
        with patch.object(recovery.install, 'retired_checkpoint_scope') as retired:
            self.assertEqual(recovery.copy_round_trip(self.source, self.destination, 'a' * 32), before)
        self.assertEqual(retired.call_count, 2)
        for copied in ('backup', 'restored'):
            self.assertEqual(recovery.install.checkpoint_tree(self.destination / copied, installed=True), before)
        self.assertEqual(recovery.install.checkpoint_tree(self.source, installed=True), before)

    def test_detects_corruption_in_restored_copy(self):
        tree = recovery.install.checkpoint_tree

        def corrupt_after_copy(source, copy_to=None, **kwargs):
            result = tree(source, copy_to, **kwargs)
            if copy_to is not None and copy_to.name == 'restored':
                (copy_to / '.urb/synthetic-journal').write_bytes(b'altered')
            return result

        with patch.object(recovery.install, 'retired_checkpoint_scope'), patch.object(
                recovery.install, 'checkpoint_tree', side_effect=corrupt_after_copy):
            with self.assertRaisesRegex(ValueError, 'fingerprint differs'):
                recovery.copy_round_trip(self.source, self.destination, 'a' * 32)
        self.assertEqual(self.journal.read_bytes(), b'recorded synthetic state')

    def test_detects_original_change_during_restore(self):
        tree = recovery.install.checkpoint_tree

        def change_original_after_copy(source, copy_to=None, **kwargs):
            result = tree(source, copy_to, **kwargs)
            if copy_to is not None and copy_to.name == 'restored':
                self.journal.write_bytes(b'altered')
            return result

        with patch.object(recovery.install, 'retired_checkpoint_scope'), patch.object(
                recovery.install, 'checkpoint_tree', side_effect=change_original_after_copy):
            with self.assertRaisesRegex(ValueError, 'Original pier changed'):
                recovery.copy_round_trip(self.source, self.destination, 'a' * 32)

    def test_stopped_proof_rejects_a_runtime_lock_and_unretired_scope(self):
        (self.source / '.vere.lock').symlink_to('absent')
        with patch.object(recovery.install, 'retired_checkpoint_scope'):
            with self.assertRaisesRegex(ValueError, 'runtime ownership lock'):
                recovery.assert_stopped(self.source, 'a' * 32)
        with patch.object(recovery.install, 'retired_checkpoint_scope', side_effect=ValueError('Active scope')):
            with self.assertRaisesRegex(ValueError, 'Active scope'):
                recovery.assert_stopped(self.source, 'a' * 32)

    def test_installed_layout_is_not_admitted_for_preinstall_retry(self):
        with self.assertRaisesRegex(ValueError, 'uninstalled synthetic pier'):
            recovery.install.checkpoint_tree(self.source)

    def test_receipt_requires_exact_pinned_bytes_and_unique_keys(self):
        path = self.directory / 'report.json'
        original = b'{"status":"pass"}'
        with patch.object(recovery, 'read', return_value=original):
            self.assertEqual(recovery.pinned_json(path, hashlib.sha256(original).hexdigest(), 1024), {'status': 'pass'})
            with self.assertRaisesRegex(ValueError, 'Trusted receipt SHA-256 differs'):
                recovery.pinned_json(path, '0' * 64, 1024)
        duplicate = b'{"status":"pass","status":"fail"}'
        with patch.object(recovery, 'read', return_value=duplicate):
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
                recovery.pinned_json(path, hashlib.sha256(duplicate).hexdigest(), 1024)

    def test_retained_copy_fingerprint_mismatch_stops_before_boot(self):
        with patch.object(recovery.install, 'retired_checkpoint_scope'):
            before = recovery.copy_round_trip(self.source, self.destination, 'a' * 32)
            (self.destination / 'backup/.urb/synthetic-journal').write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'fingerprint differs: backup'):
                recovery.retained_trees(self.source, self.destination, before, 'a' * 32)

    def test_native_saved_vase_checks_configured_schema_and_exact_hash_width(self):
        native = SimpleNamespace(dojo=Mock(return_value='0x1.0000\n'))
        self.assertEqual(recovery.install.saved_home_fingerprint(native), f'{65536:064x}')
        self.assertIn('[%stead-home %3 *]', native.dojo.call_args.args[0])
        self.assertEqual(recovery.install.saved_home_fingerprint(native, authoritative=True), f'{65536:064x}')
        self.assertIn('[%stead-home %3 [* *]]', native.dojo.call_args.args[0])
        self.assertIn('(jam -.+>.q.saved)', native.dojo.call_args.args[0])
        native.dojo.return_value = 'dojo: evaluation failed'
        with self.assertRaisesRegex(ValueError, 'configured schema 3'):
            recovery.install.saved_home_fingerprint(native)

    def test_same_schema_asset_plan_rejects_native_or_compatibility_changes(self):
        inventory = 'desk/web/stead/inventory.hoon'
        asset = 'desk/web/stead/asset-' + 'a' * 64 + '.stead-asset'
        agent = 'desk/app/stead-home.hoon'
        pins = {'agents': ['stead-home'], 'role': 'home', 'compatibility': {'kernel_kelvin': 408},
                'saved_state_version': 3, 'toolchain_sha256': '1' * 64, 'contract_sha256': '2' * 64}
        before = dict(pins, source_commit='old', frontend_sha256='old', files={inventory: {'sha256': 'old'},
                      asset: {'sha256': 'old'}, agent: {'sha256': 'same'}})
        after = dict(pins, source_commit='new', frontend_sha256='new', files={inventory: {'sha256': 'new'},
                     asset.replace('a' * 64, 'b' * 64): {'sha256': 'new'}, agent: {'sha256': 'same'}})
        plan = recovery.asset_upgrade_plan(before, after, 'a' * 64, 'b' * 64, 'c' * 64)
        self.assertEqual(plan['source_desk'], recovery.desk_inventory(before))
        with self.assertRaisesRegex(ValueError, 'compatible Home packages'):
            recovery.asset_upgrade_plan(before, dict(after, saved_state_version=4), 'a' * 64, 'b' * 64, 'c' * 64)
        after['files'][agent] = {'sha256': 'changed'}
        with self.assertRaisesRegex(ValueError, 'only generated inventory'):
            recovery.asset_upgrade_plan(before, after, 'a' * 64, 'b' * 64, 'c' * 64)

    def test_replace_verified_asset_delta_rejects_dirty_desk_before_commit(self):
        mount = self.source / recovery.install.DESK
        package = self.directory / 'package'
        asset = 'asset-' + 'a' * 64 + '.stead-asset'
        replacement = 'asset-' + 'b' * 64 + '.stead-asset'
        for root, asset_name, contents in ((mount, asset, 'old'), (package, replacement, 'new')):
            desk = root / 'web/stead'
            desk.mkdir(parents=True)
            (desk / asset_name).write_text(contents)
            (desk / 'inventory.hoon').write_text(contents)
        previous, target = recovery.install.inventory(mount), recovery.install.inventory(package)
        native = SimpleNamespace(pier=self.source, dojo=Mock(return_value='%.y'), check=Mock())
        (mount / 'unexpected.txt').write_text('keep this evidence')
        with self.assertRaisesRegex(ValueError, 'both verified desk inventories'):
            recovery.install.replace_clay_assets(native, previous, target, package)
        native.dojo.assert_not_called()
        (mount / 'unexpected.txt').unlink()
        native.dojo.side_effect = ['%.y', '>=', '%.n', '>=', '%.y', '%.y', '%.y', '%.y', '%.n']
        delta = recovery.install.replace_clay_assets(native, previous, target, package)
        self.assertEqual(delta['removed'], ['web/stead/' + asset])
        self.assertEqual(recovery.install.inventory(mount), target)
        self.assertEqual(recovery.install.inventory(package), target)
        route = f'/=release-test=/web/stead/{asset.removesuffix(".stead-asset")}/stead-asset'
        self.assertEqual(native.dojo.call_args_list[1].args[0], '|rm ' + route)
        self.assertEqual(native.dojo.call_args_list[3].args[0], '|commit %release-test')
        self.assertEqual(native.dojo.call_args.args[0], f'.^(? %cu {route})')


if __name__ == '__main__':
    unittest.main()

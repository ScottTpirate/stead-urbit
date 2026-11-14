"""Check exact Home admission-to-stock-worker proof binding."""
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from dogfood_rehearsal import Git
import git_pack_proof as proof
import git_pack_push as push
import git_pack_receive as receive
import git_pack_store as store
from portable_recovery import decoded, encoded, sha


MAIN = b'refs/heads/main'
TAG = b'refs/tags/exact-\xff'
PROJECT = '019939ba-4000-7000-8000-000000000001'
ACTOR = {'identity_ship': '~bus', 'principal_id': '019939ba-4000-7000-8000-000000000002',
         'binding_id': '019939ba-4000-7000-8000-000000000003', 'binding_revision': '3'}
SCOPE = {'home': '~zod', 'authority_epoch': '1', 'project_id': PROJECT, 'repository_id': PROJECT}


def packet(body):
    return f'{4 + len(body):04x}'.encode() + body


class GitPackProofTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = self.root / 'store'
        self.storage.mkdir(mode=0o700)
        pinned = Path(__file__).resolve().parents[2] / '.runtime/tooling/git-2.55.0/bin/git'
        self.git = str(pinned) if pinned.is_file() else shutil.which('git')
        self.source = Git(self.git, self.root / 'source.git')
        self.source.init_bare(MAIN)
        tree = self.source.run('mktree', data=b'').stdout.strip()
        self.base = self.source.run('commit-tree', tree, '-m', 'Base').stdout.strip()
        self.tip = self.source.run('commit-tree', tree, '-p', self.base, '-m', 'Advance').stdout.strip()
        initial = self.private('base.pack', self.pack(self.base))
        base, _ = store.stage(self.storage, initial, sha(initial.read_bytes()), SCOPE,
                              {MAIN.hex(): self.base.decode()}, MAIN.hex(), self.git)
        wire = packet(b' '.join((push.ZERO_OID.encode(), self.base, TAG)) + b'\0 report-status')
        wire += packet(b' '.join((self.base, self.tip, MAIN))) + b'0000' + self.pack(self.tip)
        self.wire = self.private('upload.wire', wire)
        changes, _ = receive.parse(wire)
        self.claim = {
            'protocol': proof.ADMISSION, 'scope': SCOPE, 'actor': ACTOR, 'base_snapshot': base,
            'generation': '0', 'attempt': '1', 'incarnation': 'b' * 64, 'update_count': '2',
            'changes': {f'{index:02d}': change for index, change in enumerate(changes)},
            'request_id': '019939ba-4000-7000-8000-000000000004', 'wire_sha256': sha(wire),
            'admitted_at_ms': '1000', 'expires_at_ms': '6000',
        }

    def private(self, name, contents):
        file = self.root / name
        file.write_bytes(contents)
        file.chmod(0o600)
        return file

    def pack(self, root):
        return self.source.run('pack-objects', '--stdout', '--revs', '--threads=1', data=root + b'\n').stdout

    def export(self, claim, now_ms=lambda: 2000):
        raw = encoded(claim)
        return proof.prepare(raw, sha(raw), self.storage, self.wire, self.git, now_ms=now_ms)

    def test_verified_full_pack_binds_home_claim_and_preserves_order(self):
        raw = self.export(self.claim)
        result = decoded(raw)
        self.assertEqual(raw, encoded(result))
        self.assertEqual(result['protocol'], proof.PROTOCOL)
        self.assertEqual(result['admission_sha256'], sha(encoded(self.claim)))
        for key in proof.CLAIM - {'changes'}:
            self.assertEqual(result[key], self.claim[key])
        self.assertEqual(result['updates'], {
            '00': {'ref': TAG.hex(), 'prior': push.ZERO_OID, 'target': self.base.decode(),
                   'kind': 'commit', 'lineage': 'none'},
            '01': {'ref': MAIN.hex(), 'prior': self.base.decode(), 'target': self.tip.decode(),
                   'kind': 'commit', 'lineage': 'fast-forward'},
        })
        manifest = store.restore(self.storage, result['candidate_snapshot'], SCOPE,
                                 self.root / 'restored.git', self.git)
        self.assertEqual(result['pack'], {key: str(manifest[key]) for key in proof.PACK})
        self.assertEqual(manifest['refs'], {MAIN.hex(): self.tip.decode(), TAG.hex(): self.base.decode()})

    def test_pinned_bytes_and_wire_command_order_gate_staging(self):
        modified = self.claim | {'actor': ACTOR | {'binding_revision': '4'}}
        with patch.object(receive, 'prepare', side_effect=AssertionError('staging started')):
            with self.assertRaisesRegex(ValueError, 'proof-admission-digest'):
                proof.prepare(encoded(modified), sha(encoded(self.claim)), self.storage, self.wire,
                              self.git, now_ms=lambda: 2000)
            with self.assertRaisesRegex(ValueError, 'proof-change-substitution'):
                self.export(self.claim | {'changes': {'00': self.claim['changes']['01'],
                                                      '01': self.claim['changes']['00']}})
            with self.assertRaisesRegex(ValueError, 'proof-change-bound'):
                self.export(self.claim | {'update_count': '1'})
            with self.assertRaisesRegex(ValueError, 'receive-wire-digest'):
                self.export(self.claim | {'wire_sha256': 'a' * 64})
            with self.assertRaisesRegex(ValueError, 'proof-lease'):
                self.export(self.claim, now_ms=lambda: 6000)

    def test_worker_result_cannot_substitute_identity_of_snapshot_or_input(self):
        result = receive.prepare(self.storage, SCOPE, self.claim['base_snapshot'], self.wire,
                                 self.claim['wire_sha256'], self.git)
        invalid_candidate = deepcopy(result)
        invalid_candidate['manifest']['pack_bytes'] += 1
        with patch.object(receive, 'prepare', return_value=invalid_candidate):
            with self.assertRaisesRegex(ValueError, 'proof-snapshot-digest'):
                self.export(self.claim)
        invalid_candidate = result | {'upload_sha256': 'a' * 64}
        with patch.object(receive, 'prepare', return_value=invalid_candidate):
            with self.assertRaisesRegex(ValueError, 'proof-candidate-substitution'):
                self.export(self.claim)
        invalid_candidate = deepcopy(result)
        invalid_candidate['changes'][1]['target_kind'] = 'tag'
        with patch.object(receive, 'prepare', return_value=invalid_candidate):
            with self.assertRaisesRegex(ValueError, 'proof-object-facts'):
                self.export(self.claim)
        for change in ('head', 'refs'):
            invalid_candidate = deepcopy(result)
            manifest = invalid_candidate['manifest']
            extra = b'refs/heads/unproposed'.hex()
            manifest['refs'][extra] = next(iter(manifest['refs'].values()))
            if change == 'head':
                manifest['head'] = extra
            invalid_candidate['candidate_snapshot'] = sha(encoded(manifest))
            with patch.object(receive, 'prepare', return_value=invalid_candidate):
                with self.assertRaisesRegex(ValueError, 'proof-candidate-refs'):
                    self.export(self.claim)
        with patch.object(receive, 'prepare', return_value=result):
            ticks = iter((2000, 2001, 6000))
            with self.assertRaisesRegex(ValueError, 'proof-lease'):
                self.export(self.claim, now_ms=lambda: next(ticks))

    def test_v1_decoded_and_serialized_sizes_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'proof-admission-bound'):
            proof.admission(b'x' * 65_537, 'a' * 64, 2000)
        claim = deepcopy(self.claim)
        changes = []
        refs = {}
        facts = []
        prior = 'a' * 40
        for i in range(30):
            name = f'refs/heads/ref-{i:02d}/'.encode() + b'a' * (1005 if i else 700)
            ref = name.hex()
            change = {'ref': ref, 'prior': prior if i == 0 else push.ZERO_OID, 'target': 'b' * 40}
            changes.append(change)
            refs[ref] = 'b' * 40
            facts.append(change | {'action': 'fast-forward' if i == 0 else 'create', 'target_kind': 'commit'})
        claim['changes'] = {f'{index:02d}': change for index, change in enumerate(changes)}
        claim['update_count'] = str(len(changes))
        ref, *_ = refs
        manifest = {'format': store.FORMAT, 'object_format': 'sha1', 'scope': SCOPE, 'head': ref, 'refs': refs,
                    'pack_sha256': 'a' * 64, 'pack_bytes': 200, 'object_count': 3, 'object_bytes': 1000,
                    'object_ids_sha256': 'c' * 64}
        candidate = {'protocol': push.PROTOCOL, 'status': 'candidate-staged', 'scope': SCOPE,
                     'base_snapshot': claim['base_snapshot'], 'upload_sha256': claim['wire_sha256'],
                     'candidate_snapshot': sha(encoded(manifest)), 'manifest': manifest, 'changes': facts}
        raw = encoded(claim)
        self.assertLessEqual(len(raw), proof.MAX_MESSAGE)
        claim = proof.admission(raw, sha(raw), 2000)
        with self.assertRaisesRegex(ValueError, 'proof-output-bound'):
            proof._export(claim, sha(raw), candidate, head=ref, refs=refs)
        existing = set(self.storage.rglob('snapshot.json'))
        with patch.object(receive, 'parse', return_value=(changes, b'')), \
                patch.object(store, 'read_manifest', return_value=manifest | {'refs': {ref: prior}}), \
                patch.object(receive, 'prepare', side_effect=AssertionError('oversized proof staged')):
            with self.assertRaisesRegex(ValueError, 'proof-output-bound'):
                self.export(claim)
        self.assertEqual(existing, set(self.storage.rglob('snapshot.json')))


if __name__ == '__main__':
    unittest.main()

"""Stock Git review preparation preserves the exact accepted pack objects."""
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from dogfood_rehearsal import Git
import git_pack_review as review
import git_pack_store as store
from portable_recovery import encoded, sha
from test_git_pack_push import PackPushTests, MAIN, SCOPE, TAG, TOPIC


PROPOSAL = '019939ba-4000-7000-8000-000000000002'
WORK = '019939ba-4000-7000-8000-000000000003'


class PackReviewTests(PackPushTests):
    def setUp(self):
        super().setUp()
        self.review_refs = self.base_refs | {TOPIC: self.second}
        pack, digest = self.pack('live-base', self.review_refs.values())
        self.current, self.manifest = store.stage(self.storage, pack, digest, SCOPE, self.review_refs,
                                                  MAIN, self.binary)

    def reviewed(self, **changes):
        values = {'storage': self.storage, 'scope': SCOPE, 'base_snapshot': self.current,
                  'source_ref': bytes.fromhex(TOPIC), 'target_ref': bytes.fromhex(MAIN), 'base_oid': self.first,
                  'head_oid': self.second, 'git': self.binary, 'proposal_id': PROPOSAL,
                  'proposal_revision': 5, 'work_id': WORK, 'generation': 2}
        return review.prepare(**(values | changes))

    def test_candidate_advances_one_ref_and_retains_all_pack_bytes(self):
        result = self.reviewed()
        candidate = result['candidate_snapshot']
        self.assertEqual(self.reviewed(), result)
        self.assertNotEqual(candidate, self.current)
        self.assertEqual(result['status'], 'candidate-staged')
        self.assertEqual(result['intent_sha256'], sha(encoded(result['intent'])))
        self.assertEqual(result['intent']['source'], TOPIC)
        self.assertEqual(result['intent']['generation'], '2')
        self.assertEqual(result['changes'], [{'ref': MAIN, 'prior': self.first, 'target': self.second,
                                              'action': 'fast-forward', 'target_kind': 'commit'}])
        self.assertEqual(result['manifest'], self.manifest | {'refs': self.review_refs | {MAIN: self.second}})
        scope = '.'.join(SCOPE[key] for key in ('home', 'project_id', 'repository_id'))
        self.assertEqual((self.storage / scope / candidate / store.PACK_NAME).read_bytes(),
                         (self.storage / scope / self.current / store.PACK_NAME).read_bytes())
        restored = self.root / 'reviewed.git'
        store.restore(self.storage, candidate, SCOPE, restored, self.binary)
        Git(self.binary, restored).run('fsck', '--full', '--strict')
        self.assertEqual(store.restore(self.storage, self.current, SCOPE, self.root / 'base.git', self.binary),
                         self.manifest)

    def test_stale_or_mismatched_source_target_and_proposal_refuse_before_staging(self):
        count = self.snapshots()
        for params, reason in [({'head_oid': self.other}, 'review-source-changed'),
                               ({'base_oid': self.other}, 'review-target-changed'),
                               ({'source_ref': bytes.fromhex(MAIN)}, 'review-source-is-target'),
                               ({'source_ref': bytes.fromhex(TAG)}, 'ref-name'),
                               ({'target_ref': b'refs/heads/not-default'}, 'review-target-changed'),
                               ({'proposal_revision': 0}, 'review-proposal'),
                               ({'generation': True}, 'review-proposal'),
                               ({'deadline': time.monotonic() - 1}, 'git-timeout')]:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                self.reviewed(**params)
        self.assertEqual(self.snapshots(), count)

    def test_exact_source_without_ancestry_does_not_stage_candidate(self):
        refs = self.base_refs | {TOPIC: self.other}
        pack, digest = self.pack('diverged', refs.values())
        base, _ = store.stage(self.storage, pack, digest, SCOPE, refs, MAIN, self.binary)
        count = self.snapshots()
        with self.assertRaisesRegex(ValueError, 'non-fast-forward'):
            self.reviewed(base_snapshot=base, head_oid=self.other)
        self.assertEqual(self.snapshots(), count)

    def test_replaced_temporary_pack_cannot_stage_even_with_same_bytes(self):
        count = self.snapshots()
        preflight = review.push.prepare

        def swap(storage, scope, base, pack, packed_digest, updates, binary, **options):
            replacement = pack.with_suffix('.swap')
            replacement.write_bytes(pack.read_bytes())
            replacement.chmod(0o600)
            replacement.replace(pack)
            return preflight(storage, scope, base, pack, packed_digest, updates, binary, **options)

        with patch.object(review.push, 'prepare', side_effect=swap), \
                self.assertRaisesRegex(ValueError, 'review-workspace-binding'):
            self.reviewed()
        self.assertEqual(self.snapshots(), count)


def load_tests(loader, _standard, _pattern):
    return loader.suiteClass(PackReviewTests(name) for name in loader.getTestCaseNames(PackReviewTests)
                             if name in PackReviewTests.__dict__)

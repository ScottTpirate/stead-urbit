"""Offline release evidence and key rotation using real synthetic Ed25519 keys."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_release_package

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release as package
import release_readiness as readiness


def openssl(*args):
    return subprocess.run(['/usr/bin/openssl', *map(str, args)], check=True, capture_output=True, timeout=5,
                          env={'LC_ALL': 'C', 'OPENSSL_CONF': '/dev/null'}).stdout


class SyntheticReview:
    def __init__(self, directory, archives):
        self.directory = directory
        self.bundle = directory / 'bundle'
        self.bundle.mkdir()
        self.keys = {}
        for role in sorted(readiness.KEY_ROLES | {'replacement'}):
            private = directory / (role + '.key')
            openssl('genpkey', '-algorithm', 'ED25519', '-out', private)
            public = openssl('pkey', '-in', private, '-pubout', '-outform', 'DER')
            assert public[:12] == readiness.ED25519_SPKI and len(public) == 44
            self.keys[role] = public[12:].hex()
        self.trust = {'protocol': readiness.TRUST, 'profile': 'synthetic', 'generation': 1,
                      'keys': {role: self.keys[role] for role in readiness.KEY_ROLES}, 'retired_publishers': []}
        self.candidate = {'protocol': readiness.CANDIDATE, 'profile': 'synthetic', 'release': 'v1.0.0',
                          'source_commit': archives['home'][1]['source_commit'], 'archives': {}}
        for role, (raw, manifest) in archives.items():
            (self.bundle / (role + '.tar')).write_bytes(raw)
            self.candidate['archives'][role] = {'sha256': package.digest(raw), 'target': package.target_profile(manifest)}

    def sign(self, role, statement, signer=None):
        statement_path = self.directory / 'statement'
        statement_path.write_bytes(readiness.signing_bytes(role, statement))
        return openssl('pkeyutl', '-sign', '-rawin', '-inkey', self.directory / ((signer or role) + '.key'),
                       '-in', statement_path).hex()

    def signed(self, role, statement, signer=None):
        return package.encoded({'statement': statement, 'signature': self.sign(role, statement, signer)})

    def reviewer(self, role, candidate_digest, *, observation=None, signer=None):
        raw = observation or ('Synthetic observation for ' + role).encode()
        (self.bundle / (role + '.evidence')).write_bytes(raw)
        signed = self.signed(role, {'protocol': readiness.RECEIPT, 'candidate_sha256': candidate_digest,
                                   'checks': sorted(readiness.REVIEW_CHECKS[role]),
                                   'observation_sha256': package.digest(raw)}, signer)
        (self.bundle / (role + '.json')).write_bytes(signed)
        return package.digest(signed)

    def create(self, policy=None, publisher='publisher'):
        trust_raw = package.encoded(self.trust if policy is None else policy)
        self.candidate['trust_sha256'] = package.digest(trust_raw)
        candidate = self.signed('publisher', self.candidate, publisher)
        candidate_digest = package.digest(package.encoded(self.candidate))
        (self.bundle / 'candidate.json').write_bytes(candidate)
        reviews = {role: self.reviewer(role, candidate_digest) for role in readiness.REVIEW_CHECKS}
        observation = b'Synthetic owner review'
        (self.bundle / 'owner.evidence').write_bytes(observation)
        owner = {'protocol': readiness.APPROVAL, 'candidate_sha256': candidate_digest, 'reviews': reviews,
                 'checks': sorted(readiness.OWNER_CHECKS), 'observation_sha256': package.digest(observation)}
        (self.bundle / 'owner.json').write_bytes(self.signed('owner', owner))
        (self.directory / 'trust.json').write_bytes(trust_raw)
        return trust_raw

    def rotation(self, *, signer='replacement'):
        prior_digest = package.digest(package.encoded(self.trust))
        statement = {'protocol': readiness.ROTATION, 'prior_trust_sha256': prior_digest,
                     'next_generation': 2, 'next_publisher': self.keys['replacement'],
                     'retired_publisher': self.keys['publisher']}
        signatures = {role: self.sign(role, statement) for role in ('owner', 'recovery')}
        signatures['next-publisher'] = self.sign('next-publisher', statement, signer)
        return package.encoded({'statement': statement, 'signatures': signatures})


class ReleaseReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = test_release_package.ReleasePackageTests
        fixture.setUpClass()
        cls.addClassCleanup(fixture.tearDownClass)
        cls.archives = {role: (getattr(fixture, role), getattr(fixture, role + '_manifest'))
                        for role in ('home', 'identity')}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stead-release-readiness-')
        self.addCleanup(self.temp.cleanup)
        self.fixture = SyntheticReview(Path(self.temp.name), self.archives)

    def verify(self, raw, expected=None):
        return readiness.verify_bundle(self.fixture.bundle, raw, expected or package.digest(raw))

    def test_complete_evidence_is_bound_to_exact_archives_and_synthetic_scope(self):
        raw = self.fixture.create()
        result = self.verify(raw)
        self.assertEqual(result['source_commit'], self.archives['home'][1]['source_commit'])
        self.assertEqual(result['reviews'], sorted(readiness.REVIEW_CHECKS))
        self.assertEqual(result['owner_approval'], 'synthetic')
        self.assertEqual(result['profile'], 'synthetic')
        with self.assertRaisesRegex(ValueError, 'pinned trust'):
            self.verify(raw, 'a' * 64)
        with (self.fixture.bundle / 'identity.tar').open('ab') as archive:
            archive.write(b'!')
        with self.assertRaisesRegex(ValueError, 'Archive digest'):
            self.verify(raw)

    def test_independent_role_keys_and_distinct_observations(self):
        raw = self.fixture.create()
        candidate = package.digest(package.encoded(self.fixture.candidate))
        self.fixture.reviewer('team-b', candidate, signer='team-a')
        with self.assertRaisesRegex(ValueError, 'signature rejected for team-b'):
            self.verify(raw)
        shared = (self.fixture.bundle / 'team-a.evidence').read_bytes()
        self.fixture.reviewer('team-b', candidate, observation=shared)
        with self.assertRaisesRegex(ValueError, 'observations must be distinct'):
            self.verify(raw)

    def test_new_signed_team_review_requires_new_owner_approval(self):
        raw = self.fixture.create()
        candidate = package.digest(package.encoded(self.fixture.candidate))
        self.fixture.reviewer('team-b', candidate, observation=b'Second synthetic team B review')
        with self.assertRaisesRegex(ValueError, 'Owner review differs'):
            self.verify(raw)
        self.fixture.reviewer('team-b', 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'different candidate'):
            self.verify(raw)

    def test_scope_cannot_be_relabelled_by_publisher(self):
        self.fixture.candidate['profile'] = 'independent'
        raw = self.fixture.create()
        with self.assertRaisesRegex(ValueError, 'trust policy differs'):
            self.verify(raw)

    def test_key_loss_recovery_accepts_replacement_and_rejects_replay(self):
        prior = package.encoded(self.fixture.trust)
        prior_digest = package.digest(prior)
        rotation = self.fixture.rotation()
        (self.fixture.directory / 'publisher.key').unlink()
        report = readiness.verify_recovery(prior, prior_digest, rotation)
        self.assertEqual(report['status'], 'rotation-verified')
        self.assertEqual(report['next_trust']['retired_publishers'], [self.fixture.keys['publisher']])
        self.assertEqual(report['next_trust']['generation'], 2)
        new_raw = self.fixture.create(policy=report['next_trust'], publisher='replacement')
        self.assertEqual(self.verify(new_raw)['trust_sha256'], report['next_trust_sha256'])
        with self.assertRaisesRegex(ValueError, 'prior policy or generation differs'):
            readiness.verify_recovery(new_raw, report['next_trust_sha256'], rotation)

    def test_recovery_refuses_wrong_replacement_proof_and_signature_reuse(self):
        prior = package.encoded(self.fixture.trust)
        prior_digest = package.digest(prior)
        with self.assertRaisesRegex(ValueError, 'signature rejected for next-publisher'):
            readiness.verify_recovery(prior, prior_digest, self.fixture.rotation(signer='team-b'))
        changed = json.loads(self.fixture.rotation())
        changed['signatures']['recovery'] = changed['signatures']['owner']
        with self.assertRaisesRegex(ValueError, 'signature rejected for recovery'):
            readiness.verify_recovery(prior, prior_digest, package.encoded(changed))

    def test_retired_key_cannot_sign_new_candidate_under_recovered_trust(self):
        prior = package.encoded(self.fixture.trust)
        report = readiness.verify_recovery(prior, package.digest(prior), self.fixture.rotation())
        raw = self.fixture.create(policy=report['next_trust'], publisher='publisher')
        with self.assertRaisesRegex(ValueError, 'signature rejected for publisher'):
            self.verify(raw)

        return_to_old_key = {'protocol': readiness.ROTATION, 'prior_trust_sha256': package.digest(raw),
                             'next_generation': 3, 'next_publisher': self.fixture.keys['publisher'],
                             'retired_publisher': self.fixture.keys['replacement']}
        signatures = {role: self.fixture.sign(role, return_to_old_key) for role in ('owner', 'recovery')}
        signatures['next-publisher'] = self.fixture.sign('next-publisher', return_to_old_key, 'publisher')
        with self.assertRaisesRegex(ValueError, 'trust keys must be distinct'):
            readiness.verify_recovery(raw, package.digest(raw), package.encoded({
                'statement': return_to_old_key, 'signatures': signatures}))


if __name__ == '__main__':
    unittest.main()

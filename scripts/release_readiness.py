#!/usr/bin/env python3
"""Verify exact release evidence and recovery-key rotation offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

from package_release import MAX_ARCHIVE, digest, encoded, read_bounded, require, unique, verify_bytes


TRUST = 'stead.release-trust/1'
CANDIDATE = 'stead.release-candidate/1'
RECEIPT = 'stead.release-review/1'
APPROVAL = 'stead.release-owner-approval/1'
ROTATION = 'stead.release-key-recovery/1'
PROFILES = {'synthetic', 'independent'}
SHA256 = re.compile(r'[0-9a-f]{64}')
COMMIT = re.compile(r'[0-9a-f]{40}')
SIGNATURE = re.compile(r'[0-9a-f]{128}')
ED25519_SPKI = bytes.fromhex('302a300506032b6570032100')
KEY_ROLES = {'publisher', 'recovery', 'owner', 'backup-maintainer', 'team-a', 'team-b', 'app-integrator'}
TEAM_CHECKS = {'install', 'upgrade', 'restore', 'export', 'supported-profile'}
REVIEW_CHECKS = {
    'backup-maintainer': {'reproduce-release', 'private-reporting-drill', 'key-recovery-drill'},
    'team-a': TEAM_CHECKS,
    'team-b': TEAM_CHECKS,
    'app-integrator': {'separate-app', 'published-sdk', 'supported-profile'},
}
OWNER_CHECKS = {'history-license-secret-review', 'release-blocking-defects-reviewed', 'support-matrix-reviewed',
                'independent-reviewers-confirmed', 'public-release-approved'}
MAX_RECORD = 16 * 1024
MAX_OBSERVATION = 4 * 1024 * 1024
MAX_RETIRED_KEYS = 64


def matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def exact(value, fields, message):
    require(isinstance(value, dict) and set(value) == fields, message)


def decode(raw):
    value = json.loads(raw, object_pairs_hook=unique)
    require(encoded(value) == raw, 'Expected canonical release JSON')
    return value


def trust_policy(raw, expected):
    require(matches(SHA256, expected) and digest(raw) == expected, 'Independently pinned trust digest differs')
    policy = decode(raw)
    exact(policy, {'protocol', 'profile', 'generation', 'keys', 'retired_publishers'}, 'Release trust fields differ')
    require(policy['protocol'] == TRUST and policy['profile'] in PROFILES, 'Release trust profile differs')
    keys, retired = policy['keys'], policy['retired_publishers']
    exact(keys, KEY_ROLES, 'Release reviewer key roles differ')
    require(isinstance(retired, list) and len(retired) <= MAX_RETIRED_KEYS, 'Retired publisher key limit')
    require(type(policy['generation']) is int and policy['generation'] == len(retired) + 1, 'Release trust generation differs')
    public_keys = [*keys.values(), *retired]
    require(all(matches(SHA256, key) for key in public_keys) and len(set(public_keys)) == len(public_keys),
            'Release trust keys must be distinct Ed25519 public keys')
    return policy


def signing_bytes(role, statement):
    return statement['protocol'].encode('ascii') + b'\0' + role.encode('ascii') + b'\0' + encoded(statement)


def verify_signature(role, statement, signature, public_key):
    require(matches(SIGNATURE, signature) and matches(SHA256, public_key), 'Release signature/key shape differs')
    with tempfile.TemporaryDirectory(prefix='stead-release-signature-') as folder:
        directory = Path(folder)
        (directory / 'public.der').write_bytes(ED25519_SPKI + bytes.fromhex(public_key))
        (directory / 'signature').write_bytes(bytes.fromhex(signature))
        (directory / 'statement').write_bytes(signing_bytes(role, statement))
        result = subprocess.run(['/usr/bin/openssl', 'pkeyutl', '-verify', '-pubin', '-keyform', 'DER', '-rawin',
                                 '-inkey', 'public.der', '-sigfile', 'signature', '-in', 'statement'],
                                cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env={'LC_ALL': 'C', 'OPENSSL_CONF': '/dev/null'},
                                check=False, timeout=5)
    require(result.returncode == 0, 'Release signature rejected for ' + role)


def signed_record(raw, protocol, role, key, fields):
    record = decode(raw)
    exact(record, {'statement', 'signature'}, 'Signed release record fields differ')
    statement = record['statement']
    exact(statement, fields | {'protocol'}, 'Release statement fields differ')
    require(statement['protocol'] == protocol, 'Release statement protocol differs')
    verify_signature(role, statement, record['signature'], key)
    return statement


def verify_packages(bundle, candidate):
    require(matches(COMMIT, candidate['source_commit']), 'Release source identity differs')
    require(matches(re.compile(r'v[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}'), candidate['release']), 'Release version differs')
    archives = candidate['archives']
    exact(archives, {'home', 'identity'}, 'Both release roles are required')
    manifests = {}
    for role, archive in archives.items():
        exact(archive, {'sha256', 'target'}, 'Release archive pin fields differ')
        raw = read_bounded(bundle, role + '.tar', MAX_ARCHIVE)
        manifest = verify_bytes(raw, expected_sha256=archive['sha256'], target=archive['target'])
        require(manifest['role'] == role and manifest['source_commit'] == candidate['source_commit'],
                'Release archive source/role differs')
        manifests[role] = manifest
    require(all(manifests['home'][field] == manifests['identity'][field] for field in
                ('contract_sha256', 'toolchain_sha256', 'packager_sha256', 'shared_packager_sha256', 'frontend_sha256')),
            'Release role archive provenance differs')


def verify_review(bundle, trust, role, candidate_digest):
    raw = read_bounded(bundle, role + '.json', MAX_RECORD)
    receipt = signed_record(raw, RECEIPT, role, trust['keys'][role], {'candidate_sha256', 'observation_sha256', 'checks'})
    require(receipt['candidate_sha256'] == candidate_digest, 'Review belongs to a different candidate')
    require(receipt['checks'] == sorted(REVIEW_CHECKS[role]), 'Release review checks differ for ' + role)
    observation = read_bounded(bundle, role + '.evidence', MAX_OBSERVATION)
    require(observation and digest(observation) == receipt['observation_sha256'], 'Release review evidence differs for ' + role)
    return digest(raw), receipt['observation_sha256']


def verify_bundle(bundle, trust_raw, trust_digest):
    trust = trust_policy(trust_raw, trust_digest)
    candidate = signed_record(read_bounded(bundle, 'candidate.json', MAX_RECORD), CANDIDATE, 'publisher',
                              trust['keys']['publisher'], {'profile', 'release', 'source_commit', 'archives', 'trust_sha256'})
    require(candidate['trust_sha256'] == trust_digest and candidate['profile'] == trust['profile'],
            'Candidate trust policy differs')
    verify_packages(bundle, candidate)
    candidate_digest = digest(encoded(candidate))
    reviews, evidence = {}, set()
    for role in REVIEW_CHECKS:
        receipt_digest, observation_digest = verify_review(bundle, trust, role, candidate_digest)
        require(observation_digest not in evidence, 'Reviewer observations must be distinct')
        reviews[role] = receipt_digest
        evidence.add(observation_digest)
    owner = signed_record(read_bounded(bundle, 'owner.json', MAX_RECORD), APPROVAL, 'owner', trust['keys']['owner'],
                          {'candidate_sha256', 'reviews', 'checks', 'observation_sha256'})
    require(owner['candidate_sha256'] == candidate_digest and owner['reviews'] == reviews
            and owner['checks'] == sorted(OWNER_CHECKS), 'Owner review differs from the verified candidate and reviews')
    observation = read_bounded(bundle, 'owner.evidence', MAX_OBSERVATION)
    require(observation and digest(observation) == owner['observation_sha256']
            and owner['observation_sha256'] not in evidence, 'Owner review evidence differs')
    return {'protocol': 'stead.release-readiness-report/1', 'status': 'signed-evidence-verified',
            'profile': trust['profile'], 'release': candidate['release'], 'source_commit': candidate['source_commit'],
            'candidate_sha256': candidate_digest, 'trust_sha256': trust_digest, 'reviews': sorted(reviews),
            'owner_approval': 'synthetic' if trust['profile'] == 'synthetic' else 'attested'}


def verify_recovery(trust_raw, trust_digest, recovery_raw):
    trust = trust_policy(trust_raw, trust_digest)
    recovery = decode(recovery_raw)
    exact(recovery, {'statement', 'signatures'}, 'Release recovery record fields differ')
    statement, signatures = recovery['statement'], recovery['signatures']
    exact(statement, {'protocol', 'prior_trust_sha256', 'retired_publisher', 'next_publisher', 'next_generation'},
          'Release recovery statement fields differ')
    exact(signatures, {'owner', 'recovery', 'next-publisher'}, 'Release recovery signatures differ')
    require(statement['protocol'] == ROTATION and statement['prior_trust_sha256'] == trust_digest
            and statement['retired_publisher'] == trust['keys']['publisher']
            and type(statement['next_generation']) is int and statement['next_generation'] == trust['generation'] + 1,
            'Release recovery prior policy or generation differs')
    next_policy = trust | {'generation': statement['next_generation'],
                           'keys': trust['keys'] | {'publisher': statement['next_publisher']},
                           'retired_publishers': [*trust['retired_publishers'], trust['keys']['publisher']]}
    next_raw = encoded(next_policy)
    next_digest = digest(next_raw)
    trust_policy(next_raw, next_digest)
    for role in ('owner', 'recovery'):
        verify_signature(role, statement, signatures[role], trust['keys'][role])
    verify_signature('next-publisher', statement, signatures['next-publisher'], statement['next_publisher'])
    return {'protocol': 'stead.release-key-recovery-report/1', 'status': 'rotation-verified',
            'prior_trust_sha256': trust_digest, 'next_trust_sha256': next_digest, 'next_trust': next_policy}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trust', type=Path, required=True)
    parser.add_argument('--trust-sha256', required=True)
    subcommands = parser.add_subparsers(dest='action', required=True)
    subcommands.add_parser('verify').add_argument('bundle', type=Path)
    subcommands.add_parser('verify-recovery').add_argument('recovery', type=Path)
    args = parser.parse_args()
    try:
        trust_raw = read_bounded(args.trust.parent, args.trust.name, MAX_RECORD)
        if args.action == 'verify':
            result = verify_bundle(args.bundle, trust_raw, args.trust_sha256)
        else:
            recovery = read_bounded(args.recovery.parent, args.recovery.name, MAX_RECORD)
            result = verify_recovery(trust_raw, args.trust_sha256, recovery)
        print(json.dumps(result, sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, RecursionError, tarfile.TarError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Release evidence refused: {error}\n')


if __name__ == '__main__':
    main()

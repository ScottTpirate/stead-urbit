"""First cross-ship handoff fixtures with actual Ed25519 signing and verification."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
try:
    import project_migration as migration
finally:
    sys.path.pop(0)


def uid(number):
    return f'019939ba-4000-7000-8000-{number:012x}'


def command(operation, request, resource, payload):
    return {'protocol': migration.COMMAND, 'request_id': uid(request), 'project_id': uid(1),
            'resource_id': uid(resource), 'operation': operation, 'expected_revision': '0',
            'authority_epoch': '1', 'payload': payload}


def event(sequence, previous, command_value, **identity_overrides):
    identity = {'identity_ship': '~nec', 'principal_id': uid(5), 'binding_id': uid(6),
                'binding_revision': '1', 'binding_expires_at_ms': '2000000000000'}
    identity.update(identity_overrides)
    auth = {'home': '~zod', 'organization_id': uid(3), 'team_id': uid(4), 'authentication': 'native-sender/1',
            'authentication_strength': 'native-sender', 'session_audit_id': '', 'runtime': 'isolated-fake',
            'credential_expires_at_ms': identity['binding_expires_at_ms'],
            'identity': migration.canonical(identity).decode()}
    raw_command = migration.canonical(command_value)
    revision = command_value['expected_revision']
    next_revision = str(int(revision) + 1)
    receipt = {'protocol': 'stead.receipt/3', 'status': 'accepted',
               'canonical_sha256': migration.domain_hash(migration.COMMAND, raw_command),
               'resource_kind': command_value['operation'].split('.')[0], 'container_id': '',
               'resource_revision': next_revision, 'accepted_at_ms': str(1_900_000_000_000 + sequence), 'git_commit_oid': ''}
    receipt.update({key: command_value[key] for key in ('request_id', 'project_id', 'resource_id', 'authority_epoch', 'operation')})
    receipt.update({key: identity[key] for key in ('identity_ship', 'principal_id', 'binding_id', 'binding_revision')})
    receipt.update({key: auth[key] for key in ('authentication', 'authentication_strength', 'session_audit_id', 'runtime')})
    return {'protocol': migration.JOURNAL, 'sequence': str(sequence), 'previous_digest': previous,
            'canonical_command': raw_command.decode(), 'old_revision': revision, 'new_revision': next_revision,
            'receipt': migration.canonical(receipt).decode(), 'authentication_context': migration.canonical(auth).decode(),
            'grant_target': ''}


class ProjectMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        private = tempfile.TemporaryDirectory(prefix='stead-handoff-keys-')
        cls.addClassCleanup(private.cleanup)
        cls.keys = {}
        for role in ('source', 'destination'):
            key = Path(private.name) / (role + '.pem')
            cls.openssl('genpkey', '-algorithm', 'ED25519', '-out', str(key))
            public = cls.openssl('pkey', '-in', str(key), '-pubout', '-outform', 'DER')
            assert public.startswith(migration.ED25519_SPKI) and len(public) == 44
            cls.keys[role] = (key, public[-32:].hex())

    @staticmethod
    def openssl(*args):
        return subprocess.run(['/usr/bin/openssl', *args], env={'LC_ALL': 'C', 'OPENSSL_CONF': '/dev/null'},
                              check=True, capture_output=True, timeout=5).stdout

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-handoff-test-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.paths = {name: self.base / name for name in ('directory', 'trust', 'signed', 'journal', 'snapshot',
                      'source_fence', 'source_observation', 'destination_readback', 'destination_observation')}
        self.current = {'protocol': migration.DIRECTORY, 'project_id': uid(1), 'custody_id': uid(2),
                        'home': '~zod', 'origin': 'https://source.example', 'authority_epoch': '1'}
        current_digest = self.write('directory', self.current)
        self.pins = {'protocol': 'stead.project-handoff-trust/1', 'current_directory_sha256': current_digest,
                     'source_ed25519': self.keys['source'][1], 'destination_ed25519': self.keys['destination'][1],
                     'destination_home': '~bus', 'destination_origin': 'https://target.example'}
        self.write('trust', self.pins)
        created = command('project.create', 7, 1, {'organization_id': uid(3), 'owning_team_id': uid(4),
                          'title': 'Migration fixture', 'project_key': 'FIX', 'preset': 'general'})
        work = command('work.create', 8, 9, {'title': 'Keep authorship', 'description': 'Ñ with LF\n',
                       'type': 'task', 'status': 'backlog', 'priority': 'medium'})
        first = event(1, '0' * 64, created)
        self.rows = [first, event(2, migration.domain_hash(migration.JOURNAL, migration.canonical(first)), work)]
        self.transfer = {'protocol': migration.HANDOFF, 'migration_id': uid(10), 'project_id': uid(1),
                         'custody_id': uid(2), 'prior_directory_sha256': current_digest, 'destination_home': '~bus',
                         'destination_origin': 'https://target.example', 'destination_epoch': '2',
                         'snapshot_sha256': self.write('snapshot', b'opaque\x00snapshot bytes')}
        self.stage_journal()
        self.sign()

    def write(self, name, value):
        raw = value if isinstance(value, bytes) else migration.canonical(value)
        path = self.paths[name]
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o600), 'wb') as stream:
            stream.write(raw)
        return migration.sha(raw)

    def stage_journal(self):
        rows = [migration.canonical(row) for row in self.rows]
        self.transfer['journal_sha256'] = self.write('journal', b'\n'.join(rows) + b'\n')
        self.transfer['journal_count'] = str(len(rows))
        self.transfer['journal_head'] = migration.domain_hash(migration.JOURNAL, rows[-1])
        for role in ('source', 'destination'):
            self.stage_evidence(role)

    def stage_evidence(self, role, *, source_status=None, **overrides):
        source = role == 'source'
        observation = ('fixture observation for ' + role).encode()
        if source:
            observation = {'protocol': 'stead.project-retirement-status/1', 'home': '~zod', 'authority_epoch': '1',
                           'writer_state': 'retired', 'retired_at_ms': '1900000000100'}
            observation.update({key: self.transfer[key] for key in (
                'project_id', 'migration_id', 'journal_head', 'destination_home')})
            observation.update(source_status or {})
        observation_sha = self.write(role + '_observation', observation)
        proof = {'protocol': 'stead.project-source-fence/1' if source else 'stead.project-destination-readback/1',
                 'home': '~zod' if source else '~bus', 'authority_epoch': '1' if source else '2',
                 'writer_state': 'retired' if source else 'write-disabled', 'observation_sha256': observation_sha}
        proof.update({key: self.transfer[key] for key in ('migration_id', 'project_id', 'journal_head', 'snapshot_sha256')})
        proof.update(overrides)
        name = 'source_fence' if source else 'destination_readback'
        self.transfer[name + '_sha256'] = self.write(name, proof)

    def sign(self, *, wrong_role=False):
        envelope = {'transfer': self.transfer}
        for role in ('source', 'destination'):
            raw = b'stead.project-handoff/1\0' + role.encode() + b'\0' + migration.canonical(self.transfer)
            message = self.base / 'message'
            message.write_bytes(raw)
            key = self.keys['source' if wrong_role else role][0]
            envelope[role + '_signature'] = self.openssl('pkeyutl', '-sign', '-rawin', '-inkey', str(key),
                                                          '-in', str(message)).hex()
        self.write('signed', envelope)

    def test_verifies_candidate_without_changing_inputs(self):
        before = {name: path.read_bytes() for name, path in self.paths.items()}
        result = migration.verify(**self.paths)
        self.assertEqual(result['status'], 'verified-candidate')
        self.assertIs(result['authority_changed'], False)
        self.assertEqual(result['candidate_directory'], {'protocol': 'stead.project-directory-candidate/1',
                         'project_id': uid(1), 'custody_id': uid(2), 'home': '~bus',
                         'origin': 'https://target.example', 'authority_epoch': '2'})
        self.assertEqual(before, {name: path.read_bytes() for name, path in self.paths.items()})

    def test_wrong_signature_role_and_stale_epoch_fail(self):
        self.sign(wrong_role=True)
        with self.assertRaisesRegex(ValueError, 'handoff-signature-invalid'):
            migration.verify(**self.paths)
        self.transfer['destination_epoch'] = '3'
        self.sign()
        with self.assertRaisesRegex(ValueError, 'handoff-destination-mismatch'):
            migration.verify(**self.paths)
        self.write('directory', self.current | {'authority_epoch': '2'})
        with self.assertRaisesRegex(ValueError, 'current-directory-pin-mismatch'):
            migration.verify(**self.paths)

    def test_signed_broken_history_or_unfenced_writer_fails(self):
        self.rows[1]['previous_digest'] = 'c' * 64
        self.stage_journal()
        self.sign()
        with self.assertRaisesRegex(ValueError, 'journal-link-mismatch'):
            migration.verify(**self.paths)
        self.rows[1]['previous_digest'] = migration.domain_hash(migration.JOURNAL, migration.canonical(self.rows[0]))
        self.stage_journal()
        self.stage_evidence('source', writer_state='active')
        self.sign()
        with self.assertRaisesRegex(ValueError, 'evidence-scope-mismatch'):
            migration.verify(**self.paths)

    def test_changed_observation_and_snapshot_fail(self):
        self.write('snapshot', b'changed snapshot')
        with self.assertRaisesRegex(ValueError, 'evidence-digest-mismatch'):
            migration.verify(**self.paths)
        self.write('snapshot', b'opaque\x00snapshot bytes')
        self.write('destination_observation', b'changed observation')
        with self.assertRaisesRegex(ValueError, 'evidence-digest-mismatch'):
            migration.verify(**self.paths)

    def test_signed_status_must_match_native_source_fence(self):
        for override in ({'writer_state': 'active'}, {'destination_home': '~bud'},
                         {'retired_at_ms': '1900000000000'}, {'journal_head': 'f' * 64}):
            with self.subTest(override=override):
                self.stage_evidence('source', source_status=override)
                self.sign()
                with self.assertRaisesRegex(ValueError, 'native-source-status-mismatch'):
                    migration.verify(**self.paths)

    def test_signed_binding_history_preserves_ownership_and_revisions(self):
        create, work = (migration.decoded(row['canonical_command'].encode()) for row in self.rows)
        for first_actor, second_actor, error in (
                ({}, {'principal_id': uid(11)}, 'journal-binding-owner-changed'),
                ({}, {'identity_ship': '~bud'}, 'journal-binding-revision-conflict'),
                ({'binding_revision': '2'}, {}, 'journal-binding-revision-conflict'),
                ({}, {'identity_ship': '~bud', 'binding_id': uid(12), 'binding_revision': '2'}, None)):
            with self.subTest(first_actor=first_actor, second_actor=second_actor):
                first = event(1, '0' * 64, create, **first_actor)
                previous = migration.domain_hash(migration.JOURNAL, migration.canonical(first))
                self.rows = [first, event(2, previous, work, **second_actor)]
                self.stage_journal()
                self.sign()
                if error is None:
                    self.assertEqual(migration.verify(**self.paths)['status'], 'verified-candidate')
                else:
                    with self.assertRaisesRegex(ValueError, error):
                        migration.verify(**self.paths)

    def test_signed_payload_respects_native_parser_bounds(self):
        work = migration.decoded(self.rows[1]['canonical_command'].encode())
        for payload in ({f'key-{index}': 'value' for index in range(17)}, {'description': 'bad\0value'}):
            with self.subTest(payload=payload):
                self.rows[1] = event(2, self.rows[1]['previous_digest'], work | {'payload': payload})
                self.stage_journal()
                self.sign()
                with self.assertRaisesRegex(ValueError, 'journal-command-shape'):
                    migration.verify(**self.paths)

    def test_signed_creator_renewal_preserves_original_unrevoked_grant(self):
        original = self.rows[:]
        renewal = command('policy.renew-creator-grant', 13, 1, {'grant_id': uid(7)}) | {'expected_revision': '1'}
        binding = {'binding_revision': '2', 'binding_expires_at_ms': '2100000000000'}
        revoke = command('policy.revoke', 14, 1, {'grant_id': uid(7)}) | {'expected_revision': '1'}
        for change, actor, revoked, error in (
                ({}, {}, False, None),
                ({'payload': {'grant_id': uid(8)}}, {}, False, 'journal-creator-grant-renewal'),
                ({}, {'binding_id': uid(12)}, False, 'journal-creator-grant-renewal'),
                ({}, {'binding_expires_at_ms': '2000000000000'}, False, 'journal-creator-grant-renewal'),
                ({'expected_revision': '2'}, {}, False, 'journal-policy-revision'),
                ({'expected_revision': '2'}, {}, True, 'journal-creator-grant-renewal')):
            with self.subTest(change=change, actor=actor, revoked=revoked):
                self.rows = original[:]
                if revoked:
                    previous = migration.domain_hash(migration.JOURNAL, migration.canonical(self.rows[-1]))
                    self.rows.append(event(3, previous, revoke))
                previous = migration.domain_hash(migration.JOURNAL, migration.canonical(self.rows[-1]))
                self.rows.append(event(len(self.rows) + 1, previous, renewal | change, **(binding | actor)))
                self.stage_journal()
                self.sign()
                if error is None:
                    self.assertEqual(migration.verify(**self.paths)['status'], 'verified-candidate')
                else:
                    with self.assertRaisesRegex(ValueError, error):
                        migration.verify(**self.paths)

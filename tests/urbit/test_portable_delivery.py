import base64
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import portable_delivery as audit
from portable_recovery import RecoveryError, encoded, sha


def ident(suffix):
    return f'019939ba-4000-7000-8000-{suffix:012d}'


PROJECT = ident(1)
HEAD = 'a' * 40
REF = b'refs/heads/audit-\xff'.hex()
ARTIFACT = b'\0exact bytes\xff'
KEY = {'proposal_id': ident(4), 'revision': '1'}


def fixture():
    proof = {'source': 'a' * 64, 'recipe': 'b' * 64, 'output_sha256': sha(ARTIFACT), 'outcome': 'passed'}
    rows = [
        {'kind': 'ref', 'ref_hex': REF, 'oid': HEAD},
        {'kind': 'protection', 'ref_hex': REF},
        {'kind': 'proposal', **KEY, 'author': ident(5), 'work_id': ident(2), 'ref_hex': REF,
         'base_oid': audit.ZERO, 'head_oid': HEAD, 'delegation_id': ident(8)},
        {'kind': 'approval', **KEY, 'reviewer': ident(6)},
        {'kind': 'ref_receipt', 'request_id': ident(7), 'repository_revision': '1', 'actor': ident(6),
         'digest': 'c' * 64, 'changes': '1', 'proposal_id': KEY['proposal_id'], 'proposal_revision': '1'},
        {'kind': 'ref_change', 'request_id': ident(7), 'index': '0', 'ref_hex': REF,
         'prior_oid': audit.ZERO, 'target_oid': HEAD},
        {'kind': 'build', **KEY, **proof, 'job_id': ident(10), 'requester': ident(6), 'stage': 'finished',
         'assigned_worker': ident(9), 'lease_worker': ident(9), 'attempt': '1', 'lease_expires_ms': '900',
         'artifact_base64': base64.b64encode(ARTIFACT).decode('ascii')},
        {'kind': 'release', **KEY, **proof, 'release_id': ident(11), 'job_id': ident(10), 'actor': ident(12)},
        {'kind': 'delegation', 'delegation_id': ident(8), 'stage': 'revoked', 'work_id': ident(2),
         'ref_hex': REF, 'sponsor': ident(6), 'worker': ident(5), 'expires_at_ms': '800'},
    ]
    header = {'protocol': audit.PROTOCOL, 'home': '~zod', 'project_id': PROJECT, 'repository_id': PROJECT,
              'epoch': '1', 'repository_revision': '1', 'records': str(len(rows))}
    return {'format': audit.FORMAT, 'snapshot': audit.snapshot(header, rows),
            'header': header, 'records': rows, 'losses': audit.LOSSES}


def page(value, offset):
    return {
        'protocol': 'stead.code/1', 'status': 'delivery-export',
        'snapshot': value['snapshot'], 'total': value['header']['records'],
        'next_offset': str(offset + 4) if offset + 4 < len(value['records']) else '',
        'header': encoded(value['header']).decode().rstrip('\n'),
        'records': b''.join(encoded(row) for row in value['records'][offset:offset + 4]).decode(),
    }


class DeliveryAuditTests(unittest.TestCase):
    def test_pagination_binds_all_rows_and_expected_scope(self):
        value = fixture()
        seen = []
        def fetch(body):
            self.assertEqual(body['project_id'], PROJECT)
            self.assertEqual(body['snapshot'], value['snapshot'] if seen else '')
            seen.append(int(body['offset']))
            return encoded(page(value, seen[-1]))
        self.assertEqual(audit.collect(fetch, PROJECT, '~zod', '1'), value)
        self.assertEqual(seen, [0, 4, 8])

    def test_snapshot_change_never_yields_partial_artifact(self):
        value = fixture()
        def fetch(body):
            offset = int(body['offset'])
            result = page(value, offset)
            if offset:
                result['snapshot'] = 'd' * 64
            return encoded(result)
        with self.assertRaisesRegex(RecoveryError, 'audit-changed'):
            audit.collect(fetch, PROJECT, '~zod', '1')

    def test_page_rejects_wrong_home_scope(self):
        with self.assertRaisesRegex(RecoveryError, 'audit-page-scope'):
            audit.collect(lambda _: encoded(page(fixture(), 0)), PROJECT, '~bus', '1')

    def test_canonical_lines_and_handoff_are_checked(self):
        response = page(fixture(), 0)
        response['records'] = ' ' + response['records']
        with self.assertRaisesRegex(RecoveryError, 'audit-canonical-row'):
            audit.collect(lambda _: encoded(response), PROJECT, '~zod', '1')
        response = page(fixture(), 0)
        response['next_offset'] = '0'
        with self.assertRaisesRegex(RecoveryError, 'audit-page-cursor'):
            audit.collect(lambda _: encoded(response), PROJECT, '~zod', '1')

    def test_snapshot_alone_cannot_rebind_artifact_or_merge(self):
        for index, key, substitute, code in (
            (6, 'artifact_base64', 'YQ==', 'artifact-evidence'),
            (5, 'target_oid', 'b' * 40, 'merge-link'),
            (7, 'actor', ident(9), 'release-link'),
        ):
            with self.subTest(code=code):
                bad = deepcopy(fixture())
                bad['records'][index][key] = substitute
                bad['snapshot'] = audit.snapshot(bad['header'], bad['records'])
                with self.assertRaisesRegex(RecoveryError, code):
                    audit.validate(bad)

    def test_ref_history_cannot_omit_a_change(self):
        bad = fixture()
        bad['records'].pop(5)
        bad['header']['records'] = str(len(bad['records']))
        bad['snapshot'] = audit.snapshot(bad['header'], bad['records'])
        with self.assertRaisesRegex(RecoveryError, 'receipt-ref-cas'):
            audit.validate(bad)

    def test_exact_export_preserves_non_utf8_ref_and_binary_artifact(self):
        value = audit.validate(fixture())
        self.assertEqual(bytes.fromhex(value['records'][0]['ref_hex']), b'refs/heads/audit-\xff')
        self.assertEqual(base64.b64decode(value['records'][6]['artifact_base64']), ARTIFACT)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'delivery.json'
            digest = audit.write_archive(destination, value)
            self.assertEqual(audit.read(destination, digest), value)
            with self.assertRaisesRegex(RecoveryError, 'audit-file-digest'):
                audit.read(destination, '0' * 64)

    def test_empty_home_is_a_single_complete_page(self):
        value = fixture()
        value['records'] = []
        value['header'].update(records='0', repository_revision='0')
        value['snapshot'] = audit.snapshot(value['header'], value['records'])
        self.assertEqual(audit.collect(lambda _: encoded(page(value, 0)), PROJECT, '~zod', '1'), value)

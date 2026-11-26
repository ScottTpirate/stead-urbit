"""Import planner, durable checkpoint and independent simulated member API."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from test_portable_recovery import BOX, DOC, ORIGIN, PRINCIPAL, PROJECT, Source, uid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
import portable_import as importer
import portable_recovery as portable

HOME = 'https://home.localhost:8443'
MEMBER = Source().who | {'can_create': 'yes'}


class Target:
    def __init__(self, progress):
        self.credentials = {'origin': HOME}
        self.current = copy.deepcopy(MEMBER)
        self.read = portable.Reads(self)
        self.events, self.calls = [], []
        self.progress = progress
        self.loss = False
        self.alter = None
        self.policy = '1'
        self.artifacts = {}

    def member(self):
        return copy.deepcopy(self.current)

    def send(self, command):
        checkpoint = json.loads(self.progress.read_bytes())
        assert checkpoint['phase'] == 'awaiting-receipt'
        assert checkpoint['pending']['request_id'] == command['request_id']
        self.calls.append(copy.deepcopy(command))
        key = command['request_id']
        if key not in self.artifacts:
            self.events.append(copy.deepcopy(command))
            body = json.dumps(command, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            digest = hashlib.sha256(b'stead.command/3\0' + body).hexdigest()
            kind = command['operation'].split('.')[0]
            row = {'protocol': 'stead.receipt/3', 'status': 'accepted', 'canonical_sha256': digest,
                   **{name: command[name] for name in ('request_id', 'project_id', 'resource_id', 'operation', 'authority_epoch')},
                   'resource_revision': str(int(command['expected_revision']) + 1), 'resource_kind': kind, 'runtime': 'isolated-fake',
                   'container_id': command['resource_id'] if kind == 'container' else command['payload'].get('container_id', ''),
                   'authentication': 'native-approved-browser/1', 'authentication_strength': 'native-approved-browser',
                   'accepted_at_ms': '1800000000000', 'git_commit_oid': 'b' * 40 if kind == 'document' else '',
                   **{name: self.current[name] for name in ('identity_ship', 'principal_id', 'binding_id', 'binding_revision', 'session_audit_id')}}
            self.artifacts[key] = row
        if self.loss:
            self.loss = False
            raise portable.RecoveryError('synthetic-lost-response')
        row = copy.deepcopy(self.artifacts[key])
        return self.alter(row) if self.alter else row

    def __call__(self, query):
        kind = query['kind']
        project = query['project_id']
        resource = query['resource_id']
        container = query['container_id']
        rows = []
        if kind == 'identity':
            rows.append(self.member())
        else:
            comments = {}
            for event in self.events:
                if event['operation'] == 'work.comment' and event['project_id'] == project:
                    receipt = self.artifacts[event['request_id']]
                    comments.setdefault(event['resource_id'], []).append({
                        'comment_revision': receipt['resource_revision'], 'body': event['payload']['body'],
                        **{name: receipt[name] for name in ('identity_ship', 'principal_id', 'accepted_at_ms')}})
            if kind == 'comments':
                rows = comments.get(resource, [])
            for command in self.events:
                if command['project_id'] != project:
                    continue
                item = command['resource_id']
                operation = command['operation']
                payload = copy.deepcopy(command['payload'])
                row = {'resource_id': item, 'resource_revision': '1'}
                if kind == 'project' and operation == 'project.create':
                    payload.pop('organization_id')
                    payload.pop('owning_team_id')
                    rows.append(row | payload | {'kind': 'project', 'project_id': item, 'role': 'maintainer',
                                                'policy_revision': self.policy, 'authority_epoch': '1'})
                if kind == 'work' and operation == 'work.create' and resource in ('', item):
                    if item in comments:
                        row['resource_revision'] = comments[item][-1]['comment_revision']
                        if resource:
                            row['comment_count'] = str(len(comments[item]))
                    rows.append(row | payload | {'kind': 'work', 'container_id': '', 'snippet': payload['description'][:30]})
                if kind == 'containers' and operation == 'container.create':
                    rows.append(row | payload | {'kind': 'container', 'container_id': item, 'container_head': 'b' * 40})
                if kind in ('documents', 'document') and operation == 'document.save' and payload['container_id'] == container and resource in ('', item):
                    markdown = payload.pop('markdown')
                    row |= payload | {'kind': 'document', 'container_head': 'b' * 40, 'title': 'Page', 'snippet': 'Page', 'visibility': 'shared'}
                    if kind == 'document':
                        row['markdown'] = markdown
                    rows.append(row)
                if kind == 'relations' and operation == 'relation.create':
                    rows.append(row | payload | {'kind': 'relation', 'container_id': '', 'title': 'Related'})
        return portable.encoded({'protocol': 'stead.query-result/3', 'status': 'read',
                **{key: query[key] for key in ('request_id', 'kind', 'project_id', 'container_id', 'resource_id')},
                'authority_epoch': '1' if project else '0', 'generation': 'a' * 64, 'cursor': '',
                'rows': {str(index): row for index, row in enumerate(rows)}})


class PortableImport(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='stead-portable-import-test-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.archive = self.directory / 'source.zip'
        data, receipt = portable.capture(Source(), PROJECT, PRINCIPAL, ORIGIN)
        artifact = portable.write_bundle(data, receipt, self.archive)
        self.files, _ = portable.verify(self.archive, expected_sha256=artifact['sha256'])
        self.plan, self.commands = importer.plan_commands(self.files, artifact['sha256'], HOME,
            importer.target_member(MEMBER), uid(800), 'Imported λ', 'IMPORTED')
        self.plan_file = self.directory / 'plan.json'
        self.digest = importer.published_plan(self.plan, self.plan_file)
        self.target = Target(self.directory / 'progress.json')

    def apply(self, limit=16):
        with importer.Progress(self.directory) as progress:
            return importer.apply_import(self.target, self.plan, self.digest, self.commands, progress, limit)

    def readback(self):
        with importer.Progress(self.directory) as progress:
            return importer.verify_import(self.target, self.plan, self.digest, self.commands, progress)

    def test_verified_plan_remaps_scopes_and_only_page_frontmatter_id(self):
        self.assertEqual(importer.load_plan(self.archive, self.plan_file, self.digest), (self.plan, self.commands))
        self.assertEqual(self.plan_file.stat().st_mode & 0o777, 0o600)
        self.assertEqual([row['operation'] for row in self.commands],
                         ['project.create', 'work.create', 'container.create', 'document.save', 'relation.create'])
        project, work, box, doc, link = self.commands
        self.assertNotEqual(project['project_id'], PROJECT)
        self.assertNotEqual(box['resource_id'], BOX)
        self.assertEqual(doc['payload']['container_id'], box['resource_id'])
        self.assertEqual(doc['payload']['markdown'], Source().document['markdown'].replace(DOC, doc['resource_id'], 1))
        self.assertEqual(link['payload']['source_id'], doc['resource_id'])
        self.assertEqual(link['payload']['target_id'], work['resource_id'])
        self.assertEqual(link['payload']['source_project_id'], project['project_id'])
        with self.assertRaises(FileExistsError):
            importer.published_plan(self.plan, self.plan_file)
        with self.assertRaises(portable.RecoveryError):
            importer.load_plan(self.archive, self.plan_file, '0' * 64)

    def test_source_assignment_is_reported_as_a_destination_import_loss(self):
        data = portable.decoded(self.files['records.json'], portable.MAX_CAPTURE)
        data['work'][0]['assignee_principal_id'] = uid(801)
        files = dict(self.files, **{'records.json': portable.encoded(data)})
        plan, commands = importer.plan_commands(files, self.plan['artifact_sha256'], HOME,
            importer.target_member(MEMBER), uid(800), 'Imported λ', 'IMPORTED')
        self.assertEqual(commands, self.commands)
        self.assertTrue(any('Work assignments' in change for change in plan['losses']['import_changes']))

    def discussion_archive(self):
        source = Source()
        work = source.work[0]
        work['resource_revision'] = '8'
        source.comments[work['resource_id']] = [
            {'comment_revision': revision, 'body': body, 'principal_id': uid(801), 'identity_ship': '~nec',
             'accepted_at_ms': '1000'}
            for revision, body in [('3', 'First λ.  \n'), ('5', 'x' * 2048), ('8', 'Second comment')]]
        data, receipt = portable.capture(source, PROJECT, PRINCIPAL, ORIGIN)
        self.archive = self.directory / 'discussion.zip'
        artifact = portable.write_bundle(data, receipt, self.archive)
        files, _ = portable.verify(self.archive, expected_sha256=artifact['sha256'])
        return files, artifact['sha256']

    def test_import_discussion_keeps_attribution_and_replays_a_lost_receipt(self):
        files, archive_digest = self.discussion_archive()
        self.plan, self.commands = importer.plan_commands(files, archive_digest, HOME,
            importer.target_member(MEMBER), uid(800), 'Imported λ', 'IMPORTED')
        plan_file = self.directory / 'discussion-plan.json'
        self.digest = importer.published_plan(self.plan, plan_file)
        self.assertEqual(importer.load_plan(self.archive, plan_file, self.digest), (self.plan, self.commands))
        self.assertEqual(self.plan['losses']['archive_only_comments'], [{'work_id': uid(100), 'comment_revision': '5',
                                                                       'reason': 'attributed_body_exceeds_2048_bytes'}])
        notes = [step for step in self.plan['steps'] if step['operation'] == 'work.comment']
        self.assertEqual([note['source_scope'] for note in notes], [[uid(100), '3'], [uid(100), '8']])
        self.assertEqual(notes[0]['source_author']['principal_id'], uid(801))
        first, second = self.commands[2:4]
        self.assertEqual((first['expected_revision'], second['expected_revision']), ('1', '2'))
        self.assertEqual(first['payload'], {'body': 'Imported comment from ~nec at 1970-01-01T00:00:01.000Z\n\nFirst λ.  \n'})
        self.assertEqual(self.apply(2)['accepted'], 2)
        self.target.loss = True
        self.assertEqual(self.apply()['phase'], 'awaiting-receipt')
        self.assertEqual(self.apply()['phase'], 'complete')
        self.assertEqual(self.target.calls[2], self.target.calls[3])
        self.assertEqual(self.readback()['work'], 1)
        self.assertEqual(len(self.target.events), len(self.commands))
        self.target.events[3]['payload']['body'] += ' changed'
        with self.assertRaisesRegex(portable.RecoveryError, 'discussion-mismatch'):
            self.readback()

    def test_original_discussion_free_plan_still_resumes_exactly(self):
        files, digest = self.discussion_archive()
        plan, commands = importer.plan_commands(files, digest, HOME, importer.target_member(MEMBER),
                                                uid(800), 'Imported λ', 'IMPORTED', importer.LEGACY_FORMAT)
        self.assertEqual(commands, self.commands)
        self.assertTrue(any('Work discussions' in change for change in plan['losses']['import_changes']))
        path = self.directory / 'legacy-plan.json'
        self.assertEqual(importer.load_plan(self.archive, path, importer.published_plan(plan, path)), (plan, commands))

    def test_exact_digest_alone_does_not_authorize_an_altered_plan(self):
        edited = copy.deepcopy(self.plan)
        edited['steps'][1]['resource_id'] = uid(801)
        raw = portable.encoded(edited)
        self.plan_file.write_bytes(raw)
        with self.assertRaisesRegex(portable.RecoveryError, 'plan-reconstruction'):
            importer.load_plan(self.archive, self.plan_file, portable.sha(raw))
        self.assertEqual(self.target.calls, [])

    def test_invalid_source_command_content_is_rejected_during_planning(self):
        source = Source()
        source.work[0]['description'] = 'invalid\rtext'
        data, receipt = portable.capture(source, PROJECT, PRINCIPAL, ORIGIN)
        archive = self.directory / 'invalid.zip'
        artifact = portable.write_bundle(data, receipt, archive)
        files, _ = portable.verify(archive, expected_sha256=artifact['sha256'])
        with self.assertRaisesRegex(portable.RecoveryError, 'work-description'):
            importer.plan_commands(files, artifact['sha256'], HOME, importer.target_member(MEMBER), uid(801),
                                   'Import', 'IMPORT')
        self.assertEqual(self.target.calls, [])

    def test_resume_same_exact_command_across_sessions_after_lost_receipt(self):
        self.target.loss = True
        first = self.apply()
        self.assertEqual((first['phase'], first['accepted'], first['last_attempt']), ('awaiting-receipt', 0, 'unconfirmed'))
        old = self.target.calls[0]
        self.target.current['session_audit_id'] = '9' * 64
        second = self.apply(1)
        self.assertEqual(self.target.calls, [old, old])
        self.assertEqual(len(self.target.events), 1)
        self.assertEqual((second['phase'], second['accepted']), ('ready', 1))
        final = self.apply()
        self.assertEqual((final['phase'], final['accepted']), ('complete', 5))
        self.assertEqual(self.apply()['accepted'], 5)
        self.assertEqual(len(self.target.events), 5)
        self.assertEqual(len(self.target.calls), 6)
        self.assertNotIn('9' * 64, self.target.progress.read_text())
        self.assertNotIn(MEMBER['session_audit_id'], self.target.progress.read_text())
        self.assertEqual(self.readback()['documents'], 1)

    def test_bad_receipt_stops_and_keeps_pending_state(self):
        self.target.alter = lambda receipt: receipt | {'binding_revision': '999'}
        result = self.apply()
        self.assertEqual((result['phase'], result['accepted']), ('awaiting-receipt', 0))
        self.assertEqual(len(self.target.calls), 1)
        with self.assertRaisesRegex(portable.RecoveryError, 'not-complete'):
            self.readback()

    def test_correlated_rejection_keeps_prior_uncertainty_and_never_advances(self):
        self.target.loss = True
        self.assertEqual(self.apply()['last_attempt'], 'unconfirmed')
        self.target.alter = lambda receipt: {key: receipt[key] for key in ('request_id', 'canonical_sha256')} | {
            'protocol': 'stead.result/3', 'status': 'rejected', 'error': 'denied_or_not_found'}
        result = self.apply()
        self.assertEqual((result['phase'], result['accepted'], result['last_attempt']), ('awaiting-receipt', 0, 'rejected'))
        self.assertEqual(self.target.calls[0], self.target.calls[1])
        self.assertEqual(len(self.target.events), 1)

    def test_authority_changes_stop_before_new_command(self):
        self.assertEqual(self.apply(1)['accepted'], 1)
        self.target.policy = '2'
        with self.assertRaisesRegex(portable.RecoveryError, 'target-changed'):
            self.apply()
        self.target.current['binding_revision'] = '3'
        with self.assertRaisesRegex(portable.RecoveryError, 'target-member'):
            self.apply()
        self.assertEqual(len(self.target.calls), 1)

    def test_readback_detects_actual_body_difference(self):
        self.assertEqual(self.apply()['accepted'], 5)
        self.target.events[1]['payload']['description'] = 'different'
        with self.assertRaisesRegex(portable.RecoveryError, 'readback-mismatch'):
            self.readback()

    def test_owned_progress_does_not_follow_symlinks_or_share_lock(self):
        with importer.Progress(self.directory):
            with self.assertRaises(BlockingIOError):
                with importer.Progress(self.directory):
                    pass
        self.target.progress.symlink_to(self.plan_file)
        with self.assertRaises(OSError):
            self.apply()
        self.assertEqual(self.target.calls, [])

    def test_only_numeric_loopback_socket_is_used_and_tls_hostname_preserved(self):
        raw = Mock()
        tls = Mock()
        connection = importer.LoopbackHTTPS('home.localhost', 8443, tls, 5)
        with patch.object(importer.socket, 'create_connection', return_value=raw) as socket:
            connection.connect()
            socket.assert_called_once_with(('127.0.0.1', 8443), 5)
            tls.wrap_socket.assert_called_once_with(raw, server_hostname='home.localhost')
        with self.assertRaisesRegex(portable.RecoveryError, 'disposable-home-required'):
            importer.LocalHome({'origin': ORIGIN})

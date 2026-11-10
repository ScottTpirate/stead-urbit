"""Local archive custody and freshness checks using synthetic query responses."""
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import unittest

from test_portable_recovery import BOX, DOC, ORIGIN, PRINCIPAL, PROJECT, ROOT, Source, uid

sys.path.insert(0, str(ROOT / 'scripts/urbit'))
try:
    import project_replica as replica
finally:
    sys.path.pop(0)


class ProjectReplica(unittest.TestCase):
    def prepare(self, source=None):
        directory = tempfile.TemporaryDirectory(prefix='stead-replica-test-')
        self.addCleanup(directory.cleanup)
        base = Path(directory.name)
        source = source or Source()
        artifact = base / 'shared.zip'
        grant_path = base / 'grant.json'
        data, capture = replica.export.capture(source, PROJECT, PRINCIPAL, ORIGIN)
        receipt = replica.export.write_bundle(data, capture, artifact)
        finished = datetime.fromisoformat(capture['finished_at'])
        expiry = finished + timedelta(hours=2)
        grant = {'protocol': 'stead.replica-grant/1', 'custodian': 'replica-one', 'scope': replica.SCOPE,
                 'home': '~zod', 'origin': ORIGIN, 'project_id': PROJECT, 'principal_id': PRINCIPAL,
                 'authority_epoch': '7', 'generation': capture['generation'], 'artifact_sha256': receipt['sha256'],
                 'expires_at': expiry.isoformat()}
        raw = replica.export.encoded(grant)
        grant_path.write_bytes(raw)
        grant_path.chmod(0o600)
        return source, artifact, grant_path, replica.export.sha(raw), grant, expiry

    def test_offline_and_online_freshness_and_expired_reads(self):
        source, artifact, path, digest, _, expiry = self.prepare()
        grant = replica.read_grant(path, digest, 'replica-one')
        name = f'docs/{BOX}/{DOC}.md'
        now = expiry - timedelta(minutes=20)
        offline = replica.inspect(artifact, grant, now=now, read=name)
        self.assertEqual(offline['freshness'], 'offline-unchecked')
        self.assertEqual(offline['body'], source.document['markdown'])
        self.assertEqual(replica.inspect(artifact, grant, now=now, query=source)['freshness'], 'observed-current')
        source.mutate = lambda _, result, __: result.update(generation='a' * 64)
        self.assertEqual(replica.inspect(artifact, grant, now=now, query=source)['freshness'], 'stale')
        self.assertEqual(replica.inspect(artifact, grant, now=expiry)['freshness'], 'expired')
        for current, query in ((now, source), (expiry, None)):
            with self.assertRaisesRegex(ValueError, 'replica-read-denied'):
                replica.inspect(artifact, grant, now=current, query=query, read=name)

    def test_scope_pins_and_private_content(self):
        source = Source()
        source.box['visibility'] = 'private'
        source.document['visibility'] = 'private'
        source.document['markdown'] = source.document['markdown'].replace('state: published', 'state: draft')
        _, artifact, path, digest, grant, expiry = self.prepare(source)
        for expected, custodian in (('a' * 64, 'replica-one'), (digest, 'replica-two')):
            with self.assertRaises(ValueError):
                replica.read_grant(path, expected, custodian)
        now = expiry - timedelta(minutes=20)
        with self.assertRaisesRegex(ValueError, 'replica-snapshot-binding'):
            replica.inspect(artifact, dict(grant, project_id=uid(99)), now=now)
        with self.assertRaisesRegex(ValueError, 'replica-private-content'):
            replica.inspect(artifact, grant, now=now)
        artifact.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private-file-required'):
            replica.inspect(artifact, grant, now=now)

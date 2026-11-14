"""Check real two-UID private pack projection in a disposable user namespace."""
from functools import partial
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import unittest

import test_git_pack_proof as fixtures
from git_pack_http import decision
import git_pack_projection as projection
import git_pack_projection_socket as transport
import git_pack_store as store
from git_pack_upload import authorized_response
from portable_recovery import RecoveryError, decoded, encoded, sha
from test_git_pack_push_http import selection


RELAY_UID, WORKER_UID, OUTSIDER_UID = 1, 2, 3
GROUP_GID = 1


def as_user(uid):
    os.setgroups([])
    os.setgid(GROUP_GID)
    os.setuid(uid)
    assert os.getresuid() == (uid, uid, uid)


def exercise(root, mode):
    raw = (root / 'decision').read_bytes()
    scope, row, refs = decision(raw, fixtures.PROJECT)
    snapshot = row['snapshot']
    worker_store, read_store = root / 'worker', root / 'relay'
    endpoint = root / 'run' / 'pack.sock'
    source = worker_store / '.'.join(scope[key] for key in ('home', 'project_id', 'repository_id')) / snapshot
    target = read_store / source.parent.name / snapshot
    deadline = time.monotonic() + 15

    readable, writable = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(readable)
        as_user(WORKER_UID)
        try:
            assert not os.access(read_store, os.R_OK | os.W_OK | os.X_OK)
            calls = []

            def is_selected(digest, until):
                assert time.monotonic() < until <= deadline
                calls.append(digest)
                return digest == snapshot and (mode != 'revoke' or len(calls) == 1)

            expected_peer = RELAY_UID if mode != 'wrong-server-peer' else OUTSIDER_UID
            with transport.ArtifactSocket(endpoint, worker_store, scope, is_selected, expected_peer, WORKER_UID,
                                          group_gid=GROUP_GID) as server:
                os.write(writable, b'1')
                assert server.serve_one(deadline) is (mode == 'ok')
            assert not endpoint.exists()
            expected_checks = 2 if mode in ('ok', 'revoke') else int(mode == 'unselected')
            assert len(calls) == expected_checks
            os._exit(0)
        except BaseException:
            import traceback
            traceback.print_exc()
            os._exit(1)

    os.close(writable)
    assert select.select([readable], [], [], 5)[0]
    assert os.read(readable, 1) == b'1'
    os.close(readable)
    try:
        as_user(RELAY_UID)
        assert not os.access(worker_store, os.R_OK | os.W_OK | os.X_OK)
        worker_uid = WORKER_UID if mode != 'wrong-client-peer' else OUTSIDER_UID
        open_pack = partial(transport.open_artifact, endpoint, worker_uid, RELAY_UID)
        if mode == 'ok':
            result = projection.project(lambda until: raw, fixtures.PROJECT, scope['home'], read_store,
                                        open_pack, Path('/usr/bin/git'), deadline=deadline)
            assert result == snapshot and target.stat().st_uid == RELAY_UID
            assert sha((target / store.PACK_NAME).read_bytes()) == row['pack_sha256']
            with authorized_response(lambda: (scope, row, refs), fixtures.PROJECT, read_store, '/usr/bin/git',
                                     'advertise') as (_, _, advertised):
                assert next(iter(refs.values())).encode() in advertised.read()
        else:
            try:
                if mode in ('wrong-scope', 'unselected'):
                    asked_scope = scope | {'authority_epoch': '2'} if mode == 'wrong-scope' else scope
                    asked_digest = '0' * 64 if mode == 'unselected' else snapshot
                    with open_pack(asked_digest, asked_scope, deadline) as stream:
                        stream.read(1)
                else:
                    projection.project(lambda until: raw, fixtures.PROJECT, scope['home'], read_store,
                                       open_pack, Path('/usr/bin/git'), deadline=deadline)
            except RecoveryError:
                pass
            else:
                raise AssertionError('identity, scope or completion gate permitted the request')
            assert not target.exists()
    finally:
        _, status = os.waitpid(child, 0)
        assert os.waitstatus_to_exitcode(status) == 0


@unittest.skipUnless(shutil.which('unshare'), 'Linux subordinate user namespaces are required')
class ArtifactSocketTests(unittest.TestCase):
    def setUp(self):
        self.namespace = ['unshare', '--map-root-user', '--map-auto']
        capability = subprocess.run((*self.namespace, sys.executable, '-B', '-c',
                                     'import os; os.setgroups([]); os.setgid(1); os.setuid(3)'),
                                    capture_output=True, timeout=2)
        if capability.returncode:
            self.skipTest('Kernel or host subordinate UID/GID mapping is unavailable')
        fixture = fixtures.GitPackProofTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.root.chmod(0o755)
        fixture.storage.rename(self.root / 'worker')
        for name, mode in (('relay', 0o700), ('run', 0o710)):
            path = self.root / name
            path.mkdir(mode=mode)
            path.chmod(mode)
        with store.repository_directory(self.root / 'worker', fixtures.SCOPE) as (repo, _), \
                store.open_snapshot(repo, fixture.claim['base_snapshot']) as held:
            manifest = store.read_manifest(held, fixture.claim['base_snapshot'], fixtures.SCOPE)
        template = decoded(selection())
        template.update(snapshot=fixture.claim['base_snapshot'], head=manifest['head'],
                        refs=encoded(manifest['refs'])[:-1].decode(),
                        **{key: str(manifest[key]) for key in projection.SIZES + projection.DIGESTS})
        (self.root / 'decision').write_bytes(encoded(template)[:-1])

    def run_mode(self, mode):
        result = subprocess.run((*self.namespace, sys.executable, '-B', __file__, str(self.root), mode),
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))

    def test_distinct_unprivileged_users_pass_exact_snapshot_to_stock_git(self):
        self.run_mode('ok')

    def test_peer_checks_scope_selection_and_revocation_fail_closed(self):
        for mode in ('wrong-client-peer', 'wrong-server-peer', 'wrong-scope', 'unselected', 'revoke'):
            with self.subTest(mode=mode):
                self.run_mode(mode)


if __name__ == '__main__':
    # Namespace root only prepares disposable ownership, then both children
    # irrevocably drop to different mapped UIDs. Restore ownership on cleanup.
    root, mode = Path(sys.argv[1]), sys.argv[2]
    for path, uid in ((root / 'worker', WORKER_UID), (root / 'relay', RELAY_UID), (root / 'run', WORKER_UID)):
        for entry in path.rglob('*'):
            os.chown(entry, uid, GROUP_GID)
        os.chown(path, uid, GROUP_GID)
    runner = os.fork()
    if runner == 0:
        exercise(root, mode)
        os._exit(0)
    _, outcome = os.waitpid(runner, 0)
    for name in ('worker', 'relay', 'run'):
        path = root / name
        for entry in path.rglob('*'):
            os.chown(entry, 0, 0)
        os.chown(path, 0, 0)
    sys.exit(os.waitstatus_to_exitcode(outcome))

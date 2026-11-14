"""Reconcile one accepted pack into the relay-owned read store.

Use a single foreground invocation from the operator's scheduler. It reads the
same nonsecret lease as the verifier and never takes a member credential. A
normal Git fetch still performs its own current Home authorization.
"""
from __future__ import annotations

import argparse
from functools import partial
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import git_pack_projection as projection
from git_pack_projection_lease import Mailbox
from git_pack_projection_socket import ArtifactSocket, open_artifact
from git_pack_worker_socket import identities
from portable_recovery import require


def reconcile(mailbox, read_store, source, git, *, deadline):
    deadline = projection._deadline(deadline)
    accepted = mailbox.current(deadline)

    def current():
        require(mailbox.current(deadline) == accepted, 'pack-projection-selection-changed')

    return projection.project_manifest(accepted.snapshot, accepted.manifest, current,
                                       read_store, source, git, deadline=deadline)


def serve(mailbox, socket_path, worker_store, relay_uid, worker_uid, socket_gid):
    class ExitRequested(Exception):
        pass

    def stop(*_):
        raise ExitRequested

    previous = signal.signal(signal.SIGTERM, stop)
    try:
        with ArtifactSocket(socket_path, worker_store, mailbox.scope, mailbox.is_selected,
                            relay_uid, worker_uid, group_gid=socket_gid) as service:
            while True:
                service.serve_one(time.monotonic() + projection.MAX_SECONDS)
    except (ExitRequested, KeyboardInterrupt):
        pass
    finally:
        signal.signal(signal.SIGTERM, previous)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mailbox', type=Path, required=True)
    parser.add_argument('--artifact-socket', type=Path, required=True)
    parser.add_argument('--controller-uid', type=int, required=True)
    parser.add_argument('--mailbox-gid', type=int, required=True)
    parser.add_argument('--worker-uid', type=int, required=True)
    parser.add_argument('--relay-uid', type=int, required=True)
    parser.add_argument('--home', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--authority-epoch', required=True)
    mode = parser.add_subparsers(dest='mode', required=True)
    one = mode.add_parser('once')
    one.add_argument('--read-store', type=Path, required=True)
    one.add_argument('--git', type=Path, required=True)
    one.add_argument('--seconds', type=int, default=projection.MAX_SECONDS)
    worker = mode.add_parser('serve')
    worker.add_argument('--worker-store', type=Path, required=True)
    worker.add_argument('--socket-gid', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        identities(args.relay_uid, args.worker_uid)
        expected_uid = args.relay_uid if args.mode == 'once' else args.worker_uid
        require(args.relay_uid > 0 and args.worker_uid > 0 and expected_uid == os.getuid() == os.geteuid()
                and args.controller_uid not in (args.relay_uid, args.worker_uid), 'pack-projection-service-uids')
        scope = {'home': args.home, 'project_id': args.project, 'repository_id': args.project,
                 'authority_epoch': args.authority_epoch}
        mailbox = Mailbox(args.mailbox, scope, args.controller_uid, args.mailbox_gid)
        if args.mode == 'serve':
            serve(mailbox, args.artifact_socket, args.worker_store, args.relay_uid, args.worker_uid, args.socket_gid)
            return 0
        require(0 < args.seconds <= projection.MAX_SECONDS, 'pack-projection-deadline')
        source = partial(open_artifact, args.artifact_socket, args.worker_uid, args.relay_uid)
        snapshot = reconcile(mailbox, args.read_store, source, args.git, deadline=time.monotonic() + args.seconds)
    except (OSError, ValueError, subprocess.SubprocessError):
        print('The private pack projection command failed.', file=sys.stderr)
        return 1
    print(snapshot)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

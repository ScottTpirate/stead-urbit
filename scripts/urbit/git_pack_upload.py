"""Generate one stock upload-pack response from a Home-accepted snapshot."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile

import git_pack_store as store
from execution_policy import directory_fd
from git_pack_readback import observe
from portable_code import private_directory, staged_repository
from portable_recovery import UUID, match, require, same_entry, same_path

MAX_REQUEST = 65_536
MAX_RESPONSE = 2 * store.MAX_PACK
MAX_ADVERTISEMENT = 256 * 1024
SERVICE = b'# service=git-upload-pack\n'
ADVERTISEMENT = f'{4 + len(SERVICE):04x}'.encode('ascii') + SERVICE + b'0000'


@contextmanager
def response(connection, principal, project, storage, binary, operation, request=b''):
    with authorized_response(lambda: observe(connection, principal, project), project,
                             storage, binary, operation, request) as result:
        yield result


@contextmanager
def authorized_response(authorize, project, storage, binary, operation, request=b''):
    """Yield a private spool only after a fresh Home read matches the initial decision.

    The caller must supply this Git client's individual authorization and must
    start disclosure as part of this operation. This worker does not listen on
    a socket, issue credentials, keep sessions, accept pushes, or serve files.
    """
    require(match(UUID, project), 'project-scope')
    require(isinstance(request, bytes) and
            ((operation == 'advertise' and not request) or
             (operation == 'fetch' and 0 < len(request) <= MAX_REQUEST)), 'upload-pack-request')
    observed = authorize()
    scope, report, refs = observed
    snapshot = report['snapshot']

    # The Git invocation sees only the complete object closure that Home
    # selected. A persistent repository or alternate object store is not used.
    with tempfile.TemporaryFile() as spool:
        with store.repository_directory(storage, scope) as (directory, check_store):
            with store.open_snapshot(directory, snapshot) as source:
                value = store.read_manifest(source, snapshot, scope)
                require(value['head'] == report['head'] and value['refs'] == refs
                        and value['object_count'] == int(report['object_count']), 'home-pack-differs')
                with tempfile.TemporaryDirectory(prefix='stead-git-upload-') as scratch:
                    with directory_fd(Path(scratch)) as parent:
                        opened_parent = private_directory(parent)
                        with staged_repository(parent, binary, command_prefix=store.GIT_LIMITS) as (name, opened, git):
                            _, inventory = store.verify_pack(git, source, store.PACK_NAME,
                                                             value['pack_sha256'], refs, value['head'])
                            require(all(type(value[key]) is type(actual) and value[key] == actual
                                        for key, actual in inventory.items()), 'snapshot-inventory')
                            args = ('-c', 'pack.threads=1', 'upload-pack', '--strict', '--stateless-rpc')
                            if operation == 'advertise':
                                spool.write(ADVERTISEMENT)
                                git.run_to(spool, *args, '--advertise-refs', git.path, limit=MAX_ADVERTISEMENT)
                            else:
                                git.run_to(spool, *args, git.path, data=request, limit=MAX_RESPONSE)
                            require(same_entry(parent, name, opened) and same_path(Path(scratch), opened_parent),
                                    'staging-binding')
                check_store()
                require(same_entry(directory, snapshot, os.fstat(source)), 'snapshot-binding')
        length = spool.tell()
        require(length > (len(ADVERTISEMENT) if operation == 'advertise' else 0), 'empty-upload-pack-response')
        spool.seek(0)
        require(authorize() == observed, 'home-acceptance-changed')
        subtype = 'advertisement' if operation == 'advertise' else 'result'
        yield f'application/x-git-upload-pack-{subtype}', length, spool

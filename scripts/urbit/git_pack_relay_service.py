"""Build the Git relay WSGI application for an edge-only Unix socket."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
import weakref

from execution_policy import directory_fd
import git_pack_browse_http as browser
from git_pack_relay import Relay
from git_pack_service import private_mount
from git_pack_store import SHIP
from git_pack_worker_service import exact_path, held_file, disjoint, MAX_GIT, sandbox_ready, wrapper
from portable_code import private_directory
from portable_recovery import TOKEN, UUID, decoded, match, require, same_entry, same_path, shape


PROFILE = 'stead.git-pack-relay-service/1'
FIELDS = {'protocol', 'project', 'home', 'origin', 'home_port', 'certificate_sha256', 'ca',
          'capability', 'relay_uid', 'worker_uid', 'worker_socket', 'spool', 'read_store',
          'git', 'git_sha256'}


def stable_git(binary, digest):
    # The relay cannot replace the reviewed engine between startup and exec.
    for path in binary.parents:
        with directory_fd(path) as fd:
            info = os.fstat(fd)
            require(info.st_uid == 0 and not info.st_mode & 0o022, 'pack-relay-service-git-parent')
    with held_file(binary, MAX_GIT) as stream:
        info = os.fstat(stream.fileno())
        require(info.st_uid == 0 and stat.S_ISREG(info.st_mode)
                and hashlib.file_digest(stream, 'sha256').hexdigest() == digest, 'pack-relay-service-git')


def load_ca(path):
    with directory_fd(path.parent) as parent:
        directory = os.fstat(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= 65536,
                    'pack-relay-service-ca')
            raw = source.read(65537)
            after = os.fstat(source.fileno())
            require(len(raw) == info.st_size and after.st_ctime_ns == info.st_ctime_ns
                    and same_entry(parent, path.name, after) and same_path(path.parent, directory),
                    'pack-relay-service-ca-changed')
    return raw.decode('ascii')


def create_application(profile):
    """Load reviewed private settings at process startup. No listener is opened."""
    path = exact_path(str(profile))
    with held_file(path, 8192, secret=True) as source:
        config = decoded(source.read(8193), 8192)
    shape(config, FIELDS)
    require(config['protocol'] == PROFILE and type(config['relay_uid']) is int
            and 0 < os.getuid() == os.geteuid() == config['relay_uid']
            and type(config['worker_uid']) is int and config['worker_uid'] > 0,
            'pack-relay-service-profile')
    require(match(UUID, config['project']) and match(SHIP, config['home']), 'pack-relay-service-scope')
    require(type(config['home_port']) is int and 0 < config['home_port'] <= 65_535
            and match(TOKEN, config['git_sha256']), 'pack-relay-service-pin')
    read_store, spool, git, ca, worker = (exact_path(config[key])
                                         for key in ('read_store', 'spool', 'git', 'ca', 'worker_socket'))
    disjoint((read_store, spool, git, ca, worker.parent, path))
    stable_git(git, config['git_sha256'])
    with directory_fd(read_store) as directory:
        private_directory(directory)
    with directory_fd(spool) as directory:
        private_directory(directory)
    relay = Relay(config['origin'], config['home'], config['capability'],
                  certificate_sha256=config['certificate_sha256'], ca_data=load_ca(ca), connect_port=config['home_port'])
    sandbox_ready()
    engine = tempfile.TemporaryDirectory(prefix='stead-relay-engine-', dir=spool)
    try:
        reader = install_isolated_reader(engine.name, git)
        mounted = private_mount(config['origin'], config['project'], relay.read_decision, read_store, reader,
                                relay, spool, worker, config['worker_uid'], config['relay_uid'])
        browse = browser.mount(relay, config['project'], read_store, reader)
    except BaseException:
        engine.cleanup()
        raise

    def application(environ, start_response):
        path = environ.get('PATH_INFO', '')
        query = environ.get('QUERY_STRING', '')
        target = path + ('?' + query if query else '')
        forwarded = {key for key in environ if key.startswith('HTTP_X_FORWARDED_')}
        if (environ.get('HTTP_X_STEAD_EDGE_TARGET') != target or environ.get('HTTP_FORWARDED')
                or forwarded != {'HTTP_X_FORWARDED_PROTO'} or environ['HTTP_X_FORWARDED_PROTO'] != 'https'):
            start_response('400 Bad Request', [('Cache-Control', 'no-store'), ('Content-Length', '0')])
            return ()
        if path == browser.PATH:
            return browse(environ, start_response)
        return mounted(environ, start_response)

    weakref.finalize(application, engine.cleanup)
    return application


def install_isolated_reader(directory, git):
    """Create a read-side executable under a separately owned private directory."""
    directory, git = Path(directory), Path(git)
    with directory_fd(directory) as parent:
        private_directory(parent)
        name = 'git-isolated'
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o500, dir_fd=parent)
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(wrapper(git))
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent)
    return directory / name

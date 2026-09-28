"""Bind every privileged helper to the exact still-live controller parent."""
from __future__ import annotations
import ctypes
from concurrent.futures import Future
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading


def nft_binary():
    # Fixed distribution paths inside the existing read-only /usr mount; never
    # search an inherited PATH for a capability-bearing packet controller.
    if not os.statvfs('/usr').f_flag & os.ST_RDONLY:
        raise ValueError('Namespace system tools must be read-only')
    for name in ('/usr/bin/nft', '/usr/sbin/nft'):
        path = Path(name)
        if path.is_file():
            info = path.stat()
            # Host UID0 is intentionally unmapped in this user namespace.
            if info.st_mode & 0o022 or not os.access(path, os.X_OK):
                raise ValueError('Namespace packet controller mode differs')
            return name
    raise ValueError('Namespace packet controller is unavailable')


def command(argv, *, privileged=False):
    if not argv:
        raise ValueError('Nonempty owned command required')
    return ['/usr/bin/python3', '-B', str(Path(__file__).resolve()), str(os.getpid()),
            'controller' if privileged else 'fixture', *map(str, argv)]


def fixture_command(argv):
    if os.environ.get('STEAD_CONFIGURED') != '1':
        return argv
    if os.getuid() != 0:
        raise ValueError('Configured evaluator must run inside the owned namespace')
    return command(argv)


class ChildLauncher:
    """PDEATHSIG belongs to the creating thread, so keep that thread alive."""
    def __init__(self):
        self.requests = queue.Queue()
        self.lock = threading.Lock()
        self.children = []
        self.closed = False
        self.thread = threading.Thread(target=self.work, daemon=True, name='owned-native-launcher')
        self.thread.start()

    def work(self):
        while True:
            request = self.requests.get()
            if request is None:
                return
            arguments, options, result = request
            try:
                child = subprocess.Popen(command(arguments), **options)
                self.children.append(child)
                result.set_result(child)
            except BaseException as error:
                result.set_exception(error)

    def spawn(self, arguments, **options):
        with self.lock:
            if self.closed or not self.thread.is_alive():
                raise RuntimeError('Owned native launcher is closed')
            result = Future()
            self.requests.put((arguments, options, result))
            return result.result()

    def close(self):
        with self.lock:
            if any(child.poll() is None for child in self.children):
                raise RuntimeError('Stop and reap native children before closing launcher')
            self.closed = True
            self.requests.put(None)
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError('Owned native launcher did not exit')


def main():
    parent = int(sys.argv[1])
    mode = sys.argv[2]
    arguments = sys.argv[3:]
    if parent <= 1 or mode not in ('controller', 'fixture') or not arguments:
        raise ValueError('Invalid owned child request')
    # This is a fresh single-threaded process, never a preexec_fn in a threaded
    # supervisor. The second parent check closes the spawn/death race.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Cannot bind owned child lifetime')
    if os.getppid() != parent:
        raise RuntimeError('Controller exited before child admission')
    if mode == 'controller':
        if arguments[0] != nft_binary():
            raise ValueError('Only the namespace packet controller retains capabilities')
    else:
        arguments = ['/usr/bin/setpriv', '--bounding-set=-all', '--inh-caps=-all',
                     '--ambient-caps=-all', '--no-new-privs', '--', *arguments]
    os.execv(arguments[0], arguments)


if __name__ == '__main__':
    main()

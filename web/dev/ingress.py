"""Fail-closed raw TLS ingress for the isolated fake-ship namespace.

No HTTP headers, TLS termination, owner authentication or caller-selected target.
The supervisor owns each child object and arms only after its native bootstrap ACK.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import selectors
import socket
import stat
import threading
import time

PUBLIC_TLS = {'zod': 18443, 'bus': 18444, 'nec': 18445, 'bud': 18446}
TOKEN = re.compile(r'[0-9a-f]{64}\Z')


class TLSIngress:
    MAX_CONNECTIONS = 32
    BUFFER = 65536
    IDLE_SECONDS = 60

    def __init__(self, directory, ship, guard, *, connect=socket.create_connection):
        if ship not in PUBLIC_TLS:
            raise ValueError('Unknown disposable ship')
        self.ship, self.guard, self.connect = ship, guard, connect
        self.directory = Path(directory)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise ValueError('Private existing ingress directory required')
        info = self.directory.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('Ingress directory must be owned and mode 0700')
        self.path = self.directory / (ship + '.tls.sock')
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.process = None
        self.pidfd = None
        self.nonce = None
        self.incarnation = None
        self.armed = False
        self.acknowledged = False
        self.connections = set()
        self.threads = set()
        self.server = socket.socket(socket.AF_UNIX)
        try:
            self.server.bind(str(self.path))
            os.chmod(self.path, 0o600)
            self.inode = self.path.stat().st_ino
            self.server.listen(self.MAX_CONNECTIONS)
            self.server.settimeout(.1)
        except BaseException:
            self.server.close()
            raise
        self.acceptor = threading.Thread(target=self._accept, daemon=True)
        self.monitor = threading.Thread(target=self._monitor, daemon=True)
        self.acceptor.start()
        self.monitor.start()

    def _disarm(self, *, retire=True):
        self.armed = False
        if retire:
            self.nonce = None
            self.acknowledged = True
        self.incarnation = None
        for stream in tuple(self.connections):
            try:
                stream.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            stream.close()
        self.connections.clear()

    def bind_child(self, process):
        with self.lock:
            if self.closed.is_set() or process.poll() is not None:
                raise ValueError('Live owned child required')
            if self.process is not None and self.process is not process and self.process.poll() is None:
                raise ValueError('Previous child must be stopped and reaped before replacement')
            self._disarm()
            if self.pidfd is not None:
                os.close(self.pidfd)
                self.pidfd = None
            self.pidfd = os.pidfd_open(process.pid)
            self.process = process  # Popen identity, never a reusable numeric PID.
            self.nonce = secrets.token_hex(32)
            self.acknowledged = False
            return self.nonce

    def _live(self):
        if self.process is None or self.pidfd is None or self.process.poll() is not None:
            return False
        with selectors.DefaultSelector() as poll:
            poll.register(self.pidfd, selectors.EVENT_READ)
            return not poll.select(0)

    def arm(self, process, nonce, acknowledgement):
        with self.lock:
            try:
                self.guard()
            except Exception:
                self._disarm()
                raise
            if process is not self.process or nonce != self.nonce:
                raise ValueError('Stale bootstrap completion')
            if (self.closed.is_set() or self.acknowledged
                    or not self._live() or set(acknowledgement) != {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                    or acknowledgement['protocol'] != 'stead.bootstrap/1'
                    or acknowledgement['status'] != 'ready'
                    or acknowledgement['home'] != '~' + self.ship
                    or acknowledgement['nonce'] != nonce
                    or not isinstance(acknowledgement['incarnation'], str)
                    or not TOKEN.fullmatch(acknowledgement['incarnation'])):
                self._disarm()
                raise ValueError('Bootstrap does not match this live child incarnation')
            self._disarm(retire=False)  # Existing streams cannot span a second bootstrap.
            self.incarnation = acknowledgement['incarnation']
            self.armed = True
            self.acknowledged = True

    def disarm(self, process=None):
        with self.lock:
            if process is None or process is self.process:
                self._disarm()

    def _monitor(self):
        while not self.closed.wait(.05):
            with self.lock:
                try:
                    self.guard()
                    if not self._live():
                        self._disarm()
                except Exception:
                    self._disarm()

    def _accept(self):
        while not self.closed.is_set():
            try:
                peer, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            backend = thread = None
            with self.lock:
                try:
                    self.guard()
                    if not self.armed or not self._live() or len(self.connections) // 2 >= self.MAX_CONNECTIONS:
                        raise ValueError('Ingress fenced')
                    process = self.process
                    incarnation = self.incarnation
                    # Only the enumerated public secure port; never Lens/Khan.
                    backend = self.connect(('127.0.0.1', PUBLIC_TLS[self.ship]), timeout=2)
                    if process is not self.process or not self.armed or not self._live():
                        backend.close()
                        raise ValueError('Child changed during connect')
                    self.connections.update((peer, backend))
                    thread = threading.Thread(target=self._relay, args=(peer, backend, process, incarnation), daemon=True)
                    self.threads.add(thread)
                    thread.start()
                except Exception:
                    if thread is not None and not thread.is_alive():
                        self.threads.discard(thread)
                    for stream in (peer, backend):
                        if stream is not None:
                            self.connections.discard(stream)
                            stream.close()

    def _relay(self, first, second, process, incarnation):
        streams = (first, second)
        buffers = {first: bytearray(), second: bytearray()}
        ended = set()
        shutdown = set()
        last = time.monotonic()
        try:
            for stream in streams:
                stream.setblocking(False)
            while not self.closed.is_set() and time.monotonic() - last < self.IDLE_SECONDS:
                with self.lock:
                    if not self.armed or self.process is not process or self.incarnation != incarnation or not self._live():
                        return
                for stream, other in ((first, second), (second, first)):
                    if other in ended and not buffers[stream] and stream not in shutdown:
                        stream.shutdown(socket.SHUT_WR)
                        shutdown.add(stream)
                if len(ended) == 2 and not any(buffers.values()):
                    return
                with selectors.DefaultSelector() as ready:
                    for stream, other in ((first, second), (second, first)):
                        mask = (selectors.EVENT_READ if stream not in ended and len(buffers[other]) <= self.BUFFER - 16384 else 0)
                        if buffers[stream]:
                            mask |= selectors.EVENT_WRITE
                        if mask:
                            ready.register(stream, mask, other)
                    for key, events in ready.select(.1):
                        stream, other = key.fileobj, key.data
                        if events & selectors.EVENT_READ:
                            data = stream.recv(16384)
                            if data:
                                buffers[other].extend(data)
                                last = time.monotonic()
                            else:
                                ended.add(stream)
                        if events & selectors.EVENT_WRITE:
                            sent = stream.send(buffers[stream])
                            del buffers[stream][:sent]
                            last = time.monotonic()
        except (OSError, ValueError):
            pass
        finally:
            with self.lock:
                for stream in streams:
                    self.connections.discard(stream)
                    stream.close()
                self.threads.discard(threading.current_thread())

    def close(self):
        self.closed.set()
        with self.lock:
            self._disarm()
            self.server.close()
            if self.pidfd is not None:
                os.close(self.pidfd)
                self.pidfd = None
            threads = tuple(self.threads)
        for thread in (*threads, self.acceptor, self.monitor):
            thread.join(timeout=2)
        if self.path.exists() and self.path.stat().st_ino == self.inode:
            self.path.unlink()

"""Bounded host-loopback byte relay to four fixed private TLS ingress sockets.

No HTTP parsing, forwarded headers, TLS termination, Lens, or caller-selected port.
"""
import os
from pathlib import Path
import selectors
import socket
import stat
import struct
import threading
import time

PORTS = {'zod': 8443, 'bus': 8444, 'nec': 8445, 'bud': 8446}


class LoopbackBridge:
    def __init__(self, directory, healthy):
        self.healthy = healthy
        self.closed = threading.Event()
        self.lock = threading.RLock()
        self.streams, self.workers = set(), set()
        self.servers, self.acceptors = [], []
        directory = Path(directory)
        if directory.is_symlink():
            raise ValueError('Redirected ingress directory')
        self.directory = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(self.directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            os.close(self.directory)
            raise ValueError('Ingress directory must be owned and private')
        self.monitor = None
        try:
            self.healthy()
            for ship, port in PORTS.items():
                self.socket_info(ship)
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.servers.append(server)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('127.0.0.1', port))
                server.listen(32)
                server.settimeout(.1)
                thread = threading.Thread(target=self.accept, args=(server, ship), daemon=True)
                self.acceptors.append(thread)
                thread.start()
            self.monitor = threading.Thread(target=self.watch, daemon=True)
            self.monitor.start()
        except BaseException:
            self.close()
            raise

    def socket_info(self, ship):
        info = os.stat(ship + '.tls.sock', dir_fd=self.directory, follow_symlinks=False)
        if not stat.S_ISSOCK(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
            raise ValueError('Unowned or redirected TLS ingress socket')
        return (info.st_dev, info.st_ino)

    def stop(self):
        self.closed.set()
        with self.lock:
            for stream in (*self.servers, *self.streams):
                try:
                    stream.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                stream.close()

    def watch(self):
        while not self.closed.wait(.25):
            try:
                self.healthy()
            except Exception:
                self.stop()

    def accept(self, server, ship):
        while not self.closed.is_set():
            try:
                frontend, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            backend = worker = None
            with self.lock:
                try:
                    if self.closed.is_set() or len(self.streams) >= 64:
                        raise ValueError('Bridge closed or full')
                    self.healthy()
                    expected = self.socket_info(ship)
                    backend = socket.socket(socket.AF_UNIX)
                    backend.settimeout(1)
                    backend.connect(f'/proc/self/fd/{self.directory}/{ship}.tls.sock')
                    _, uid, _ = struct.unpack('3i', backend.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != os.getuid() or self.socket_info(ship) != expected:
                        raise ValueError('TLS ingress identity changed')
                    self.streams.update((frontend, backend))
                    worker = threading.Thread(target=self.relay, args=(frontend, backend), daemon=True)
                    self.workers.add(worker)
                    worker.start()
                except Exception:
                    if worker is not None and not worker.is_alive():
                        self.workers.discard(worker)
                    for stream in (frontend, backend):
                        if stream is not None:
                            self.streams.discard(stream)
                            stream.close()

    def relay(self, first, second):
        streams = (first, second)
        buffers = {first: bytearray(), second: bytearray()}
        ended, shutdown = set(), set()
        last = time.monotonic()
        try:
            for stream in streams:
                stream.setblocking(False)
            while not self.closed.is_set() and time.monotonic() - last < 60:
                for stream, other in ((first, second), (second, first)):
                    if other in ended and not buffers[stream] and stream not in shutdown:
                        stream.shutdown(socket.SHUT_WR)
                        shutdown.add(stream)
                if len(ended) == 2 and not any(buffers.values()):
                    return
                with selectors.DefaultSelector() as ready:
                    for stream, other in ((first, second), (second, first)):
                        mask = selectors.EVENT_READ if stream not in ended and len(buffers[other]) <= 65536 - 16384 else 0
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
                    self.streams.discard(stream)
                    stream.close()
                self.workers.discard(threading.current_thread())

    def close(self):
        self.stop()
        with self.lock:
            threads = [*self.acceptors, *self.workers, *([self.monitor] if self.monitor else [])]
        for thread in threads:
            if thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=2)
        remaining = [thread.name for thread in threads if thread is not threading.current_thread() and thread.is_alive()]
        if self.directory is not None:
            os.close(self.directory)
            self.directory = None
        if remaining:
            raise RuntimeError('Loopback relay threads failed to stop: ' + ', '.join(remaining))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

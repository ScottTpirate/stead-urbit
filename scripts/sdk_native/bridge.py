"""A bounded fixed-peer UDP relay over an inherited private stream socket.

The stream is owned by the two trusted controllers, never a Vere child. There
is no address field, TCP forwarding, namespace entry or arbitrary RPC dispatch.
"""
import json
import queue
import socket
import struct
import threading
import time

MAX_MESSAGE = 1_000_000
MAX_DATAGRAM = 65507


def exact(channel, length, deadline=None):
    deadline = time.monotonic() + 2 if deadline is None else deadline
    data = bytearray()
    while len(data) < length:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('SDK bridge frame deadline')
        channel.settimeout(remaining)
        part = channel.recv(length - len(data))
        if not part:
            raise EOFError('SDK bridge closed')
        data.extend(part)
    return bytes(data)


class Bridge:
    def __init__(self, channel, alias_port, native_port):
        if (alias_port, native_port) not in ((31337, 31519), (31519, 31337)):
            raise ValueError('Fixed synthetic peer ports required')
        self.channel = channel
        self.channel.settimeout(2)
        self.native_port = native_port
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(('127.0.0.1', alias_port))  # No reuse: one exclusive alias.
        self.udp.settimeout(.2)
        self.messages = queue.Queue(maxsize=1)
        self.lock = threading.Lock()
        self.forward_lock = threading.Lock()
        self.opened = threading.Event()
        self.closed = threading.Event()
        self.error = None
        self.sent = self.received = self.dropped = 0
        self.threads = [threading.Thread(target=self.receive, daemon=True),
                        threading.Thread(target=self.relay, daemon=True)]
        for thread in self.threads:
            thread.start()

    def check(self):
        if self.error is not None:
            raise RuntimeError('SDK bridge failed') from self.error
        if self.closed.is_set():
            raise EOFError('SDK bridge is closed')

    def fail(self, error):
        self.error = error
        self.opened.clear()
        self.closed.set()

    def admit(self):
        self.check()
        with self.forward_lock:
            if self.opened.is_set():
                raise ValueError('SDK relay already admitted')
            # Bound and discard packets queued on the closed local alias.
            import select
            for _ in range(64):
                if not select.select([self.udp], [], [], 0)[0]:
                    self.opened.set()
                    return
                self.udp.recvmsg(MAX_DATAGRAM)
                self.dropped += 1
            raise ValueError('SDK pre-admission UDP queue bound')

    def disarm(self):
        self.opened.clear()
        # Once this returns, no already-started forwarding operation remains.
        with self.forward_lock:
            self.opened.clear()

    def send(self, kind, raw):
        maximum = MAX_DATAGRAM if kind == b'D' else MAX_MESSAGE if kind == b'J' else 0
        if not 0 < len(raw) <= maximum:
            raise ValueError('Bridge frame kind or length')
        self.check()
        with self.lock:
            self.channel.sendall(kind + struct.pack('!I', len(raw)) + raw)

    def message(self, value):
        self.send(b'J', json.dumps(value, sort_keys=True, separators=(',', ':')).encode())

    def receive(self):
        try:
            while not self.closed.is_set():
                # Idle is allowed; a started frame has the bounded socket wait.
                import select
                if not select.select([self.channel], [], [], .2)[0]:
                    continue
                admitted = self.opened.is_set()
                deadline = time.monotonic() + 2
                header = exact(self.channel, 5, deadline)
                kind, size = header[:1], struct.unpack('!I', header[1:])[0]
                limit = MAX_DATAGRAM if kind == b'D' else MAX_MESSAGE if kind == b'J' else 0
                if not 0 < size <= limit:
                    raise ValueError('Bridge frame kind or length')
                raw = exact(self.channel, size, deadline)
                if kind == b'D':
                    with self.forward_lock:
                        if admitted and self.opened.is_set():
                            if self.udp.sendto(raw, ('127.0.0.1', self.native_port)) != size:
                                raise ValueError('Incomplete forwarded datagram')
                            self.received += 1
                        else:
                            self.dropped += 1
                else:
                    self.messages.put_nowait(json.loads(raw))
        except BaseException as error:
            if not self.closed.is_set():
                self.fail(error)

    def relay(self):
        try:
            while not self.closed.is_set():
                import select
                if not select.select([self.udp], [], [], .2)[0]:
                    continue
                with self.forward_lock:
                    try:
                        raw, _, flags, address = self.udp.recvmsg(MAX_DATAGRAM)
                    except TimeoutError:
                        continue
                    if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
                        raise ValueError('Truncated SDK datagram')
                    if not raw or address != ('127.0.0.1', self.native_port):
                        raise ValueError('Unexpected SDK datagram source')
                    if self.opened.is_set():
                        self.send(b'D', raw)
                        self.sent += 1
                    else:
                        self.dropped += 1
        except BaseException as error:
            if not self.closed.is_set():
                self.fail(error)

    def get(self, timeout, check=lambda: None):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.check()
            check()
            try:
                return self.messages.get(timeout=.2)
            except queue.Empty:
                pass
        raise TimeoutError('SDK controller response deadline')

    def close(self):
        self.disarm()
        self.closed.set()
        try:
            self.channel.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.channel.close()
        self.udp.close()
        for thread in self.threads:
            thread.join(timeout=3)
            if thread.is_alive():
                raise RuntimeError('SDK relay did not stop')
        while not self.messages.empty():
            self.messages.get_nowait()

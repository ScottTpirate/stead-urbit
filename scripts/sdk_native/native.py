"""Fixed fresh fake-ship operations shared by the two trusted SDK controllers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import core_conn
import owned_child


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(directory):
    root = Path(directory)
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError('SDK input redirect or special file')
        if path.is_file():
            if len(result) >= 256 or path.stat().st_size > 524288:
                raise ValueError('SDK input inventory bound')
            result[path.relative_to(root).as_posix()] = sha(path)
    if not result:
        raise ValueError('Empty SDK input inventory')
    return result


class Native:
    def __init__(self, ship, port, guard):
        if (ship, port) not in (('zod', 31337), ('bus', 31519)):
            raise ValueError('Fixed fresh synthetic identity required')
        self.ship, self.port, self.guard = ship, port, guard
        self.pier = Path('/state') / ship
        if self.pier.exists() or self.pier.is_symlink():
            raise ValueError('SDK qualification requires a new empty pier')
        self.lock = json.loads(Path('/toolchain.json').read_text())
        self.binary = '/runtime/' + self.lock['runtime']['binary']
        self.logpath = Path('/state') / (ship + '.log')
        self.log = self.logpath.open('xb')
        self.launcher = owned_child.ChildLauncher()
        self.process = None
        self.commands = []
        self.started = time.monotonic()
        self.cleanup = None

    def start(self):
        self.guard()
        argv = [self.binary, '-t', '-L', '--no-dock', '--loom', '31',
                '-b', '127.0.0.1', '-p', str(self.port), '--http-port', '18080' if self.ship == 'zod' else '18081',
                '-F', self.ship, '-B', '/runtime/downloads/' + self.lock['boot_artifact']['archive'],
                '-A', '/kernel/pkg/arvo', '-c', str(self.pier)]
        self.process = self.launcher.spawn(argv, stdin=subprocess.DEVNULL,
            stdout=self.log, stderr=self.log, close_fds=True)
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            self.check()
            try:
                if self.dojo('zuse', timeout=15).strip() != '%408':
                    raise ValueError('Pinned kernel Kelvin differs')
                break
            except (OSError, StopIteration, ValueError):
                time.sleep(.5)
        else:
            raise TimeoutError('Fresh SDK fake boot deadline')
        if self.dojo('our').strip() != '~' + self.ship:
            raise ValueError('Native identity differs')
        self.dojo('|mount %base')
        deadline = time.monotonic() + 30
        while not (self.pier / 'base').is_dir():
            self.check()
            if time.monotonic() > deadline:
                raise TimeoutError('Native base mount deadline')
            time.sleep(.1)
        return {'identity': '~' + self.ship, 'boot_seconds': round(time.monotonic() - self.started, 3),
                'pid': self.process.pid, 'proof': self.proof()}

    def check(self):
        self.guard()
        if self.process is not None and self.process.poll() is not None:
            raise RuntimeError('SDK native child exited unexpectedly')
        if self.logpath.stat().st_size > 16 * 1024 * 1024:
            raise ValueError('SDK native log bound')

    def dojo(self, source, timeout=180):
        self.check()
        port = next(int(line.split()[0]) for line in (self.pier / '.http.ports').read_text().splitlines() if 'loopback' in line)
        expression = '+hood/' + source[1:] if source.startswith('|') else source
        body = json.dumps({'source': {'dojo': expression}, 'sink': {'app': 'hood'} if source.startswith('|') else {'stdout': None}}).encode()
        with urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}', data=body,
                headers={'Content-Type': 'application/json'}), timeout=timeout) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError('Native Lens response bound')
        value = json.loads(raw)
        if not isinstance(value, str):
            raise ValueError('Native Lens result shape')
        self.commands.append({'source': source, 'output': value})
        return value

    def install(self, sources):
        expected = inventory(sources)
        for group in (True, False):
            selected = [name for name in expected if name.endswith('.hoon') == group]
            if not selected:
                continue
            for name in selected:
                target = self.pier / 'base' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(Path(sources) / name, target)
                if sha(target) != expected[name]:
                    raise ValueError('Installed SDK bytes differ')
            self.dojo('|commit %base')
            for name in selected:
                path = Path(name)
                route = '/' + '/'.join([*path.with_suffix('').parts, path.suffix[1:]])
                deadline = time.monotonic() + 60
                while self.dojo(f'=/  arc=arch  .^(arch %cy /=base={route})  ?=(^ -.arc)').strip() != '%.y':
                    if time.monotonic() > deadline:
                        raise TimeoutError('Clay import deadline: ' + name)
                    time.sleep(.1)
                digest = core_conn.atom(bytes.fromhex(expected[name])[::-1])
                observed = self.dojo(f'=/  raw=@t  .^(@t %cx /=base={route})  =({digest} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))').strip()
                if observed != '%.y':
                    raise ValueError('Clay SDK source readback differs: ' + name)
        if inventory(sources) != expected:
            raise ValueError('SDK source changed during install')
        return expected

    def exchange(self, thread, noun, timeout=90):
        if thread not in ('stead-sdk-qualify', 'stead-sdk-invoke'):
            raise ValueError('Fixed SDK thread required')
        self.check()
        result = core_conn.exchange(self.binary, self.pier / '.urb/conn.sock',
            f'[32 %fyrd [%base %{thread} %noun [%noun {noun}]]]', timeout=timeout)
        self.commands.append({'thread': thread, 'result': result})
        if result['outcome'] is None:
            raise ValueError('SDK thread did not return a result')
        return result['outcome']['json']

    def readback(self, expected, case=''):
        if case and (not case.startswith('~') or any(c not in '~.0123456789abcdef' for c in case)):
            raise ValueError('Absolute Clay case grammar')
        for name, digest in expected.items():
            path = Path(name)
            route = '/' + '/'.join([*path.with_suffix('').parts, path.suffix[1:]])
            literal = core_conn.atom(bytes.fromhex(digest)[::-1])
            observed = self.dojo(f'=/  raw=@t  .^(@t %cx /=base/{case}{route})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))') if case else self.dojo(
                f'=/  raw=@t  .^(@t %cx /=base={route})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))')
            if observed.strip() != '%.y':
                raise ValueError('Installed/invoked Clay bytes changed: ' + name)
        return True

    def proof(self):
        self.check()
        pid = self.process.pid
        status = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
        caps = {name: status[name].strip() for name in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd', 'NoNewPrivs')}
        if caps['NoNewPrivs'] != '1' or any(v != '0000000000000000' for k, v in caps.items() if k != 'NoNewPrivs'):
            raise ValueError('SDK Vere child retains privileges')
        inodes = {os.readlink(p)[8:-1] for p in Path(f'/proc/{pid}/fd').iterdir() if os.readlink(p).startswith('socket:[')}
        endpoint = '0100007F:' + f'{self.port:04X}'
        matches = [line.split() for line in Path('/proc/net/udp').read_text().splitlines()[1:] if line.split()[1] == endpoint]
        if len(matches) != 1 or matches[0][9] not in inodes:
            raise ValueError('Exclusive owned fake Ames socket absent')
        return {'capabilities': caps, 'udp': endpoint,
                'namespaces': {name: os.readlink(f'/proc/{pid}/ns/{name}') for name in ('net', 'pid', 'mnt', 'user')},
                'lens_ports': [int(line.split()[0]) for line in (self.pier / '.http.ports').read_text().splitlines() if 'loopback' in line]}

    def stop(self):
        if self.cleanup is not None:
            return self.cleanup
        if self.process is None:
            try:
                self.launcher.close()
            finally:
                self.log.close()
            self.cleanup = {'started': False, 'reaped': True, 'clean': True}
            return self.cleanup
        premature = self.process.poll() is not None
        forced = False
        try:
            if not premature:
                self.process.terminate()
                try:
                    self.process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    forced = True
                    self.process.kill()
                    self.process.wait(timeout=5)
        finally:
            primary = sys.exc_info()[1]
            errors = []
            for close in (self.log.close, self.launcher.close):
                try:
                    close()
                except BaseException as error:
                    errors.append(type(error).__name__ + ': ' + str(error))
            if errors:
                if primary is not None:
                    primary.add_note('SDK cleanup: ' + '; '.join(errors))
                else:
                    raise RuntimeError('SDK cleanup: ' + '; '.join(errors))
        code = self.process.returncode
        self.cleanup = {'exit_code': code, 'reaped': code is not None,
                        'clean': code == 0 and not premature and not forced, 'premature': premature, 'forced': forced}
        return self.cleanup

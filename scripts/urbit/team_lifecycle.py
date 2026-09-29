"""Owned configured-fixture startup. No production identities or host firewall."""
from __future__ import annotations
import fcntl
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import core_conn
from conn import framed_length
import native_peer_fence
import native_tls
import owned_child
from digests import tree_sha

INGRESS_CODE = Path('/web-dev') if Path(__file__).parent == Path('/code') else Path(__file__).resolve().parents[2] / 'web/dev'
sys.path.insert(0, str(INGRESS_CODE))
from ingress import TLSIngress, PUBLIC_TLS
LOADED_INGRESS_DIGEST = tree_sha(INGRESS_CODE)

APPS = {'zod': 'stead-home', 'bus': 'stead-identity', 'nec': 'stead-identity', 'bud': 'stead-identity'}


class TeamLifecycle:
    def __init__(self, directory, host_namespace, binary, guard, failed, record):
        self.binary, self.guard, self.failed, self.record = binary, guard, failed, record
        self.directory = Path(directory)
        if self.directory.parent.is_symlink():
            raise ValueError('Redirected ingress parent')
        self.directory.parent.mkdir(mode=0o700, exist_ok=True)
        parent = self.directory.parent.stat()
        if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise ValueError('Ingress parent must be owned and private')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.certificates = native_tls.create(self.directory / 'certificates')
        self.children = {}
        self.boots = {}
        self.restart_expected = {}
        self.launcher = owned_child.ChildLauncher()
        self.peers = native_peer_fence.NativePeerFence(host_namespace, guard, failed)
        self.ingress = {ship: TLSIngress(self.directory, ship, guard) for ship in APPS}

    def injection(self, ship):
        # One immutable actual jammed Arvo ovum, delivered through Vere -I.
        source = f'[[%g %stead-startup ~] [%idle %{APPS[ship]}]]'
        frame, diagnostics = core_conn.evaluate(self.binary, '-jn', source.encode())
        if len(frame) != 5 + framed_length(frame[:5]):
            raise ValueError('Startup idle injection is not one complete native frame')
        raw = frame[5:]
        descriptor = os.memfd_create('stead-startup-idle', os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
        try:
            os.write(descriptor, raw)
            os.lseek(descriptor, 0, os.SEEK_SET)
            seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
            fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
            if fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != seals or os.read(descriptor, len(raw) + 1) != raw:
                raise ValueError('Startup injection immutable-byte verification failed')
            os.lseek(descriptor, 0, os.SEEK_SET)
            return descriptor, {'source': source, 'jam_sha256': hashlib.sha256(raw).hexdigest(),
                                'bytes': len(raw), 'seals': seals, 'encoder_stderr': diagnostics.decode()}
        except BaseException:
            os.close(descriptor)
            raise

    def launch(self, ship, arguments, *, lifetime_fd, log, register, fresh=False):
        self.guard()
        previous = self.children.get(ship)
        if previous is not None and previous.poll() is None:
            raise ValueError('Stop and reap the previous owned ship before restart')
        if not fresh and ship not in self.restart_expected:
            raise ValueError('A captured saved-state expectation is required for restart')
        descriptor, proof = self.injection(ship)
        try:
            arguments = [*arguments[:-1], '-p', str(native_peer_fence.PORTS[ship]),
                         '--https-port', str(PUBLIC_TLS[ship]), '-I', f'/proc/self/fd/{descriptor}', arguments[-1]]
            # Serialize the final verified block with spawn. Shutdown has a
            # separate best-effort block; a closed controller never admits Popen.
            with self.peers.lock:
                self.guard()
                self.peers.block(ship)
                self.ingress[ship].disarm()
                self.guard()
                process = self.launcher.spawn(arguments, stdin=subprocess.DEVNULL, stdout=log,
                                              stderr=log, close_fds=True, pass_fds=(lifetime_fd, descriptor))
                register(process)  # Publish ownership before any fallible setup.
                self.children[ship] = process
                self.guard()  # A concurrent stop cannot strand the new child.
                nonce = self.ingress[ship].bind_child(process)
                self.boots[ship] = {'process': process, 'nonce': nonce, 'suspended': False,
                                    'present': False, 'fresh': fresh, 'acknowledged': False, 'injection': proof}
                self.record('configured launch ' + ship, {'pid': process.pid, 'argv': arguments, 'injection': proof})
        finally:
            os.close(descriptor)
        return process

    def exists_on_base(self, ship, dojo):
        app = APPS[ship]
        source = f'(lien ~(tap in .^((set [@tas ?]) %ge /=base=/$)) |=([name=@tas live=?] =(name %{app})))'
        value = dojo(ship, source).strip()
        if value not in ('%.y', '%.n'):
            raise ValueError('Native app inventory did not return a boolean')
        return value == '%.y'

    def suspension_checkpoint(self, ship, dojo):
        entry = self.boots[ship]
        if entry['process'] is not self.children[ship] or entry['process'].poll() is not None:
            raise ValueError('Startup checkpoint no longer belongs to this child')
        if dojo(ship, f'.^(? %gu /={APPS[ship]}=/$)').strip() != '%.n':
            raise ValueError('Startup injection did not suspend the saved application')
        present = self.exists_on_base(ship, dojo)
        if entry['fresh']:
            if present:
                raise ValueError('Fresh verified seed unexpectedly contains the configured app')
        else:
            if not present or self.saved_fingerprint(ship, dojo) != self.restart_expected[ship]:
                raise ValueError('Suspended application differs from the expected saved state')
        entry.update(suspended=True, present=present)
        self.record('configured suspension ' + ship, {'pid': entry['process'].pid, 'present_on_base': present})

    def saved_fingerprint(self, ship, dojo):
        if dojo(ship, f'.^(desk %gd /={APPS[ship]}=/$)').strip() != '%base':
            raise ValueError('Configured application is not on the verified desk')
        pattern = '[%stead-home %3 *]' if ship == 'zod' else '[%stead-identity %1 *]'
        source = (f'=/  egg=egg-any:gall  .^(egg-any:gall %gv /={APPS[ship]}=/$)  '
                  f'?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  '
                  f'?>  ?=({pattern} q.saved)  ^-  @ux  (shax (jam saved))')
        result = dojo(ship, source).strip()
        if not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', result):
            raise ValueError('Native saved-vase fingerprint is not a hash')
        value = int(result.replace('.', ''), 16)
        if value >= 2 ** 256:
            raise ValueError('Native saved-vase fingerprint exceeds SHA-256')
        return f'{value:064x}'

    def prepare_restart(self, ship, dojo):
        entry = self.boots[ship]
        if not entry['acknowledged'] or entry['process'].poll() is not None:
            raise ValueError('A current admitted child is required to capture restart state')
        self.block(ship)
        digest = self.saved_fingerprint(ship, dojo)
        self.restart_expected[ship] = digest
        self.record('configured restart expectation ' + ship, {'saved_vase_sha256': digest})
        return digest

    def reinstall(self, ship, dojo):
        entry = self.boots[ship]
        if not entry['suspended'] or not entry['present'] or entry['acknowledged']:
            raise ValueError('A previously installed suspended app is required for reload')
        if dojo(ship, f'.^(desk %gd /={APPS[ship]}=/$)').strip() != '%base':
            raise ValueError('Saved app is not on the verified base desk')
        # The earlier suspension checkpoint is mandatory. These commands cannot
        # repair absent/failed startup injection after admitting old authority.
        dojo(ship, f'|rein %base [%.n %{APPS[ship]}]')
        dojo(ship, f'|rein %base [%.y %{APPS[ship]}]')
        deadline = time.monotonic() + 60
        while dojo(ship, f'.^(? %gu /={APPS[ship]}=/$)').strip() != '%.y':
            self.guard()
            if time.monotonic() > deadline:
                raise TimeoutError('Configured app failed supported reload')
            time.sleep(.1)

    def admit(self, ship, acknowledgement, dojo):
        entry = self.boots[ship]
        process = entry['process']
        location = {'ship': ship, 'mode': 'initial' if entry.get('fresh') else 'restart',
                    'step': 'startup-checkpoint', 'rollback_errors': []}
        try:
            if not entry['suspended'] or entry['acknowledged'] or process is not self.children[ship]:
                raise ValueError('Missing fresh owned startup checkpoint')
            location['step'] = 'app-inventory'
            if not self.exists_on_base(ship, dojo):
                raise ValueError('Missing configured application on verified desk')
            location['step'] = 'tls-verify'
            tls = native_tls.verify(process, self.certificates, ship, self.guard)
            # arm validates the exact one-use nonce, native ACK and live pidfd.
            location['step'] = 'ingress-arm'
            self.ingress[ship].arm(process, entry['nonce'], acknowledgement)
            location['step'] = 'peer-release'
            proof = self.peers.release(ship, process)
            entry['acknowledged'] = True
            location['step'] = 'record'
            self.record('configured admission ' + ship, {'pid': process.pid,
                        'incarnation': acknowledgement['incarnation'], 'peer_proof': proof, 'tls': tls})
        except BaseException as error:
            location['error'] = type(error).__name__ + ': ' + str(error)[:2000]
            try:
                location['ingress_retirement'] = self.ingress[ship].retirement()
            except BaseException:
                location['ingress_retirement'] = {}
            # Preserve the initiating error and attempt both fail-closed actions
            # even if one rollback operation fails. Public projection is closed.
            for rollback in (lambda: self.ingress[ship].disarm(process), lambda: self.peers.block(ship)):
                try:
                    rollback()
                except BaseException as cleanup_error:
                    location['rollback_errors'].append(type(cleanup_error).__name__ + ': ' + str(cleanup_error)[:2000])
            error.admission_failure = location
            raise

    def block(self, ship):
        self.ingress[ship].disarm()
        with self.peers.lock:
            if not self.peers.closed.is_set():
                self.peers.block(ship)
            elif self.peers.kernel_state != 'verified-empty':
                raise ValueError('Closed native peer barrier lacks verified empty policy')

    def disarm_browser(self):
        # Safe in a failure callback: no native mutex or packet-controller call.
        for ingress in self.ingress.values():
            ingress.disarm()

    def close(self):
        self.disarm_browser()
        errors = []
        for ingress in self.ingress.values():
            try:
                ingress.close()
            except Exception as error:
                errors.append(str(error))
        try:
            self.peers.close()
        except Exception as error:
            errors.append(str(error))
        try:
            self.launcher.close()
        except Exception as error:
            errors.append(str(error))
        if errors:
            raise RuntimeError('; '.join(errors))

"""Short-lived local test CA and actual pinned Eyre certificate installation.

No OS trust changes, public CA, proxy TLS termination, or persisted browser token.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import secrets
import socket
import ssl
import stat
import subprocess
import time
import core_conn
import owned_child

HOSTS = {'zod': 'home.localhost', 'bus': 'bus.localhost', 'nec': 'nec.localhost', 'bud': 'bud.localhost'}
PORTS = {'zod': 18443, 'bus': 18444, 'nec': 18445, 'bud': 18446}


def openssl(*arguments):
    command = owned_child.fixture_command(['/usr/bin/openssl', *map(str, arguments)])
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    if result.returncode != 0:
        # Never attach process arguments or diagnostics to retained test reports.
        raise RuntimeError('Disposable certificate generation failed')


def create(directory):
    directory = Path(directory)
    directory.mkdir(mode=0o700, exist_ok=False)
    ca = directory / 'ca.cnf'
    ca.write_text('[req]\nprompt=no\ndistinguished_name=dn\nx509_extensions=ca\n'
                  '[dn]\nCN=Stead disposable local test CA\n[ca]\n'
                  'basicConstraints=critical,CA:true,pathlen:0\n'
                  'keyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n')
    openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
            '-nodes', '-days', '2', '-config', ca, '-keyout', directory / 'ca-key.pem', '-out', directory / 'ca.pem')
    for ship, host in HOSTS.items():
        config = directory / (ship + '.cnf')
        config.write_text('[req]\nprompt=no\ndistinguished_name=dn\n'
                          f'[dn]\nCN={host}\n[server]\n'
                          'basicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature\n'
                          'extendedKeyUsage=serverAuth\n' + f'subjectAltName=DNS:{host}\n')
        openssl('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
                '-config', config, '-keyout', directory / (ship + '-key.pem'), '-out', directory / (ship + '.csr'))
        openssl('x509', '-req', '-in', directory / (ship + '.csr'), '-CA', directory / 'ca.pem',
                '-CAkey', directory / 'ca-key.pem', '-set_serial', '0x' + secrets.token_hex(16), '-days', '2',
                '-extfile', config, '-extensions', 'server', '-out', directory / (ship + '.pem'))
    for path in directory.iterdir():
        path.chmod(0o600)
    return directory


def pem(path, *, private):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as source:
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or (private and stat.S_IMODE(info.st_mode) != 0o600) or info.st_size > 8192):
            raise ValueError('Invalid disposable certificate input')
        raw = source.read(8193)
    lines = raw.splitlines()
    if not lines or len(lines) > (64 if private else 128) or any(len(line) > 256 for line in lines):
        raise ValueError('Certificate line bounds')
    return '[' + ' '.join(core_conn.atom(line) for line in lines) + ' ~]'


def install(binary, channel, directory, ship):
    if ship not in HOSTS:
        raise ValueError('Unknown disposable TLS identity')
    directory = Path(directory)
    key = pem(directory / (ship + '-key.pem'), private=True)
    cert = pem(directory / (ship + '.pem'), private=False)
    noun = f'[32 %fyrd [%base %stead-local-tls %noun [%noun [{key} {cert}]]]]'
    try:
        result = core_conn.exchange(binary, channel, noun)
        if (result.get('outcome') or {}).get('json') != {'requested': 'yes'}:
            raise RuntimeError('Missing native certificate setup response')
    except Exception:
        # exchange traces include the private setup noun. Never propagate them.
        raise RuntimeError('Native disposable certificate setup failed') from None


def owned_listener(process, ship):
    sockets = set()
    for descriptor in Path(f'/proc/{process.pid}/fd').iterdir():
        try:
            target = descriptor.readlink().as_posix()
        except FileNotFoundError:
            continue
        found = re.fullmatch(r'socket:\[(\d+)\]', target)
        if found:
            sockets.add(found[1])
    port = f'{PORTS[ship]:04X}'
    listeners = []
    for table in ('tcp', 'tcp6'):
        for line in Path('/proc/net/' + table).read_text().splitlines()[1:]:
            fields = line.split()
            if fields[3] == '0A' and fields[1].split(':')[1] == port:
                listeners.append((fields[1], fields[9]))
    if not listeners or len(listeners) > 2 or any(inode not in sockets for _, inode in listeners) or process.poll() is not None:
        raise ValueError('TLS listener is not exclusively owned by the current native child')
    return [{'endpoint': endpoint, 'inode': inode} for endpoint, inode in listeners]


def verify(process, directory, ship, guard):
    directory = Path(directory)
    expected = hashlib.sha256(ssl.PEM_cert_to_DER_cert((directory / (ship + '.pem')).read_text())).hexdigest()
    context = ssl.create_default_context(cafile=str(directory / 'ca.pem'))
    deadline = time.monotonic() + 30
    while True:
        guard()
        if process.poll() is not None:
            raise ValueError('Native TLS child exited')
        try:
            listeners = owned_listener(process, ship)
            with socket.create_connection(('127.0.0.1', PORTS[ship]), timeout=2) as raw:
                with context.wrap_socket(raw, server_hostname=HOSTS[ship]) as secure:
                    fingerprint = hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
                    if fingerprint != expected or process.poll() is not None:
                        raise ValueError('Native TLS certificate or child mismatch')
                    return {'hostname': HOSTS[ship], 'certificate_sha256': fingerprint,
                            'protocol': secure.version(), 'owned_listeners': listeners}
        except (OSError, ValueError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(.1)

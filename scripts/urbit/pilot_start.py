#!/usr/bin/env python3
"""Start one existing pilot pier with Stead suspended behind the host network fence."""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import subprocess

import core_conn
from conn import framed_length
from digests import sha
from pilot_owner import approved_runtime, private_pier, require


def suspension_ovum(binary, role):
    require(role in ('home', 'identity'), 'Use the installed pilot role')
    expression = f'[[%g %stead-startup ~] [%idle %stead-{role}]]'
    frame, _ = core_conn.evaluate(binary, '-jn', expression.encode())
    require(len(frame) == 5 + framed_length(frame[:5]), 'Incomplete startup suspension frame')
    raw = frame[5:]
    descriptor = os.memfd_create('stead-pilot-idle', os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
    try:
        require(os.write(descriptor, raw) == len(raw), 'Incomplete startup suspension write')
        os.lseek(descriptor, 0, os.SEEK_SET)
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
        require(fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) == seals
                and os.pread(descriptor, len(raw) + 1, 0) == raw, 'Startup suspension bytes could not be sealed')
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def arguments(binary, pier, descriptor, ames_port, http_port, https_port):
    ports = (ames_port, http_port, https_port)
    require(len(set(ports)) == len(ports) and all(1024 <= port <= 65535 for port in ports),
            'Use three distinct unprivileged listener ports')
    return [str(binary), '--no-dock', '--no-tty', '--http-ip', '127.0.0.1', '--ames-port', str(ames_port),
            '--http-port', str(http_port), '--https-port', str(https_port),
            '-I', f'/proc/self/fd/{descriptor}', str(pier)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--pier', type=Path, required=True)
    parser.add_argument('--role', choices=('home', 'identity'), required=True)
    parser.add_argument('--approved-runtime-sha256', required=True)
    for name in ('ames', 'http', 'https'):
        parser.add_argument(f'--{name}-port', type=int, required=True)
    args = parser.parse_args()
    try:
        pier = private_pier(args.pier)
        binary = args.binary.absolute()
        require(sha(binary) == approved_runtime(args.approved_runtime_sha256), 'Vere executable differs from the approved pin')
        descriptor = suspension_ovum(binary, args.role)
        try:
            argv = arguments(binary, pier, descriptor, args.ames_port, args.http_port, args.https_port)
            os.set_inheritable(descriptor, True)
            os.execv(binary, argv)
        finally:
            os.close(descriptor)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Pilot launch failed before Vere startup: {error}\n')
    except subprocess.SubprocessError:
        parser.exit(1, 'Pilot launch failed before Vere startup: native suspension encoding failed\n')


if __name__ == '__main__':
    main()

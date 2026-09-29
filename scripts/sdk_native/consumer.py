"""Fixed public-package-only controller inside the consumer's private namespace."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

import core_conn
from bridge import Bridge
from native import Native, inventory


def verify_private_import(rejected, trace):
    # This pinned Clay diagnostic was observed alongside the specific generator
    # build failure. A generic failure or a different missing import cannot pass.
    if (rejected.splitlines() != ['/gen/stead-sdk-private/hoon', '%generator-build-fail']
            or len(trace) > 262144
            or b'clay: no files match /lib/stead-core/hoon' not in trace.splitlines()):
        raise ValueError('Private import did not fail for its unavailable dependency')


def invoke_sample(clay_case, value):
    if (set(value) != {'mode', 'raw', 'binding'} or value['mode'] not in ('command', 'query', 'updates')
            or not isinstance(value['raw'], str) or len(value['raw'].encode()) > 65537
            or not re.fullmatch(r'[0-9a-f-]{36}', value['binding'])):
        raise ValueError('SDK call input grammar')
    # The pinned Khan %fyrd path lifts this sample into the unit expected by
    # invoke.hoon. Supplying a unit marker here would wrap the sample twice.
    return (f"[{clay_case} ~zod {core_conn.atom(value['binding'].encode())} "
            f"1 %{value['mode']} {core_conn.atom(value['raw'].encode())}]")


def isolation(ports, abstract):
    absent = ('/native', '/code', '/helpers', '/controller', '/seed', '/home-state',
              '/state/zod', '/state/nec', '/home/skilgore', '/root/.gitconfig', '/run/docker.sock', '/var/run/docker.sock')
    if any(Path(name).exists() for name in absent):
        raise ValueError('Private authority or host path entered the consumer')
    addresses = json.loads(subprocess.check_output(['/usr/bin/ip', '-j', 'address']))
    if {row['ifname'] for row in addresses} != {'lo'}:
        raise ValueError('Consumer has a non-loopback interface')
    tested = []
    for host, port in [('1.1.1.1', 443), *[('127.0.0.1', p) for p in ports]]:
        with socket.socket() as connection:
            connection.settimeout(.2)
            if connection.connect_ex((host, port)) == 0:
                raise ValueError('Consumer reached a forbidden TCP endpoint')
            tested.append([host, port])
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(.2)
        if connection.connect_ex('\0' + abstract) == 0:
            raise ValueError('Consumer reached the Home abstract control socket')
    return {'absent_paths': list(absent), 'tcp_denied': tested, 'abstract_denied': True,
            'namespaces': {name: os.readlink('/proc/self/ns/' + name) for name in ('net', 'pid', 'mnt', 'user')}}


def run():
    os.umask(0o077)
    channel = socket.socket(fileno=0)
    os.close(1)  # No diagnostic/output alias can leak into the stream.
    bridge = Bridge(channel, 31337, 31519)
    native = None
    stopped = False
    compiled = None
    cleaning = threading.Event()
    watchdog_stop = threading.Event()
    inputs = inventory('/public')
    context = json.loads(Path('/consumer-context.json').read_text())
    if inputs != context['public'] or inventory('/runner') != context['runner']:
        raise ValueError('Consumer public/runner source admission differs')
    installed = {}
    primary_error = None
    def watch():
        while not watchdog_stop.wait(.25):
            try:
                bridge.check()
                if not cleaning.is_set() and native is not None and native.process is not None and native.process.poll() is not None:
                    raise RuntimeError('Consumer native child exited unexpectedly')
            except BaseException as error:
                bridge.fail(error)
                try:
                    if native is not None and native.process is not None and native.process.poll() is None:
                        native.process.terminate()
                except OSError:
                    pass
                try:
                    bridge.channel.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                return
    watchdog = threading.Thread(target=watch, daemon=True)
    watchdog.start()
    try:
        while True:
            request = bridge.get(1800)
            if not isinstance(request, dict) or set(request) != {'id', 'operation', 'value'}:
                raise ValueError('SDK controller request shape')
            ident, operation, value = request['id'], request['operation'], request['value']
            if not isinstance(ident, int) or ident < 1:
                raise ValueError('SDK controller correlation')
            result = None
            if operation == 'compile' and native is None and value == {}:
                native = Native('bus', 31519, bridge.check)
                boot = native.start()
                staging = Path('/state/install')
                shutil.copytree('/public/desk-dev', staging)
                for source, target in (('qualify.hoon', 'ted/stead-sdk-qualify.hoon'),
                                       ('invoke.hoon', 'ted/stead-sdk-invoke.hoon'),
                                       ('private-import.hoon', 'gen/stead-sdk-private.hoon'),
                                       ('public-import.hoon', 'gen/stead-sdk-public.hoon')):
                    destination = staging / target
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile('/runner/' + source, destination)
                installed = native.install(staging)
                # Both filesystem and Clay absence alongside the actual failed
                # compilation are required; a generic timeout cannot pass.
                if native.dojo('=/  arc=arch  .^(arch %cy /=base=/lib/stead-core/hoon)  ?=(^ -.arc)').strip() != '%.n':
                    raise ValueError('Private library unexpectedly available')
                if native.dojo('+stead-sdk-public ~').strip() != '%sdk-import-control-compiled':
                    raise ValueError('Public import control did not compile')
                offset = native.logpath.stat().st_size
                rejected = native.dojo('+stead-sdk-private ~')
                with native.logpath.open('rb') as log:
                    log.seek(offset)
                    trace = log.read(262145)
                verify_private_import(rejected, trace)
                start = time.monotonic()
                compiled = native.exchange('stead-sdk-qualify', '~', timeout=180)
                if (compiled.get('protocol') != 'stead.sdk-compile/1' or compiled.get('status') != 'compiled'
                        or compiled.get('consumer') != '~bus' or compiled.get('desk') != 'base'
                        or not re.fullmatch(r'~[0-9.]+[a-z0-9.~]*', compiled.get('clay_case', ''))
                        or compiled.get('marks') != 'stead-command-3,stead-query-3,stead-result-3,stead-updates-3'):
                    raise ValueError('Native SDK compile receipt differs')
                result = {'boot': boot, 'compiled': compiled, 'compile_seconds': round(time.monotonic() - start, 3),
                          'installed': installed, 'private_import': {'output': rejected, 'log_hex': trace.hex()}}
            elif operation == 'isolation' and native is not None and not stopped:
                if (set(value) != {'ports', 'abstract'} or not 1 <= len(value['ports']) <= 8
                        or any(type(p) is not int or not 1024 <= p <= 65535 for p in value['ports'])
                        or not re.fullmatch(r'stead-sdk-[0-9a-f]{32}', value['abstract'])):
                    raise ValueError('Isolation probe destinations differ')
                result = isolation(value['ports'], value['abstract'])
                result['native'] = native.proof()
            elif operation == 'open' and compiled and value == {} and not bridge.opened.is_set():
                native.check()
                bridge.admit()
                result = {'admitted': True, 'proof': native.proof()}
            elif operation == 'call' and compiled and not stopped:
                noun = invoke_sample(compiled['clay_case'], value)
                if not bridge.opened.is_set():
                    raise ValueError('SDK consumer transport is not admitted')
                native.readback({'ted/stead-sdk-invoke.hoon': installed['ted/stead-sdk-invoke.hoon']})
                result = native.exchange('stead-sdk-invoke', noun)
            elif operation == 'stop' and native is not None and not stopped and value == {}:
                bridge.disarm()
                current_verified = native.readback(installed)
                snapshot_verified = native.readback(installed, compiled['clay_case'])
                cleaning.set()
                cleanup = native.stop()
                if not cleanup['clean']:
                    raise RuntimeError('Consumer native cleanup was not clean')
                transcript = Path('/state/transcript.json')
                transcript.write_text(json.dumps(native.commands))
                from native import sha
                result = {'cleanup': cleanup, 'inputs_unchanged': inputs == inventory('/public') and inventory('/runner') == context['runner'],
                          'installed_unchanged': installed == inventory('/state/install') and current_verified and snapshot_verified,
                          'transcript_sha256': sha(transcript), 'command_count': len(native.commands),
                          'datagrams': {'sent': bridge.sent, 'received': bridge.received}}
                stopped = True
            elif operation == 'finish' and stopped and value == {}:
                return 0
            else:
                raise ValueError('Unsupported SDK controller state/operation')
            bridge.message({'id': ident, 'result': result})
    except BaseException as error:
        primary_error = error
        Path('/state/failure.json').write_text(json.dumps({'error': type(error).__name__ + ': ' + str(error),
            'commands': native.commands if native else [], 'native_failure': getattr(error, 'native_failure', None)}))
        try:
            bridge.message({'error': type(error).__name__ + ': ' + str(error)})
        except Exception:
            pass
        raise
    finally:
        cleaning.set()
        bridge.opened.clear()
        cleanup_errors = []
        if native is not None and not stopped:
            try:
                native.stop()
            except BaseException as error:
                cleanup_errors.append(type(error).__name__ + ': ' + str(error))
                Path('/state/cleanup-error.txt').write_text(type(error).__name__ + ': ' + str(error))
        watchdog_stop.set()
        try:
            bridge.close()
        except BaseException as error:
            cleanup_errors.append(type(error).__name__ + ': ' + str(error))
            Path('/state/bridge-cleanup-error.txt').write_text(type(error).__name__ + ': ' + str(error))
        watchdog.join(timeout=2)
        if watchdog.is_alive():
            cleanup_errors.append('Consumer watchdog did not stop')
        if cleanup_errors:
            if primary_error is not None:
                primary_error.add_note('SDK cleanup: ' + '; '.join(cleanup_errors))
            else:
                raise RuntimeError('SDK cleanup: ' + '; '.join(cleanup_errors))


if __name__ == '__main__':
    raise SystemExit(run())

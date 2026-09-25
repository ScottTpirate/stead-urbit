"""Private namespace evaluator. Invoked only by the guarded outer runner."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
import sys

sys.path.insert(0, str(Path(__file__).parent))
import bootstrap

ROOT = Path('/work')
INPUT = Path('/input')
CONTROL = Path('/control')
EVIDENCE = Path('/output')
PIN = json.loads((INPUT / 'candidate.lock.json').read_text())
TOOLCHAIN = json.loads((INPUT / 'toolchain.lock.json').read_text())
TOKEN = secrets.token_urlsafe(32)
AUTH = base64.b64encode(('vector:' + TOKEN).encode()).decode()
REDACTIONS = (TOKEN, AUTH)
EVENTS = (EVIDENCE / 'commands.jsonl').open('w', buffering=1)
CHECKS = []
PORT = None
RUNTIME = None
FINISHING = threading.Event()
URL = 'http://127.0.0.1:8080/git/audit'


def clean(value):
    text = value if isinstance(value, str) else json.dumps(value)
    for secret in REDACTIONS:
        text = text.replace(secret, '<generated-synthetic-credential>')
    return text


def event(kind, **values):
    EVENTS.write(clean({'kind': kind, **values}) + '\n')


def phase(name):
    target = EVIDENCE / 'status.json'
    temporary = EVIDENCE / 'status.next'
    temporary.write_text(json.dumps({'phase': name}) + '\n')
    temporary.replace(target)
    print(name, flush=True)


def cancelled():
    if (CONTROL / 'STOP').exists():
        raise InterruptedError('evaluation stop requested')


def interrupt_control(_signum, _frame):
    if not FINISHING.is_set():
        raise InterruptedError('evaluation stop requested')


def watch_stop():
    while not FINISHING.wait(0.5):
        if (CONTROL / 'STOP').exists():
            os.kill(os.getpid(), signal.SIGUSR1)
            return


def check(name, passed, **details):
    row = {'name': name, 'passed': bool(passed), **details}
    CHECKS.append(row)
    event('check', **row)
    if not passed:
        raise AssertionError(name)


def log_runtime(stream):
    secrets_bytes = tuple(value.encode() for value in REDACTIONS)
    hold = max(map(len, secrets_bytes))
    pending = b''
    with (EVIDENCE / 'native.log').open('wb', buffering=0) as out:
        while data := stream.read(65536):
            pending += data
            for secret in secrets_bytes:
                pending = pending.replace(secret, b'<generated-synthetic-credential>')
            if len(pending) > hold:
                out.write(pending[:-hold])
                pending = pending[-hold:]
        for secret in secrets_bytes:
            pending = pending.replace(secret, b'<generated-synthetic-credential>')
        out.write(pending)


def lens(payload, label, timeout=None, stopping=False):
    if not stopping:
        cancelled()
    timeout = timeout or PIN['limits']['command_timeout_seconds']
    req = urllib.request.Request('http://127.0.0.1:' + str(PORT),
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status, raw = response.status, response.read(1024 * 1024).decode()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read(1024 * 1024).decode()
    event('lens', label=label, payload=payload, http_status=status, output=raw,
          elapsed_seconds=round(time.monotonic() - started, 3))
    if status != 200:
        raise RuntimeError(f'Lens request failed: {label}; HTTP {status}')
    return json.loads(raw)


def expression(value):
    return lens({'source': {'dojo': value}, 'sink': {'stdout': None}}, value)


def hood(command, stopping=False):
    result = lens({'source': {'dojo': '+hood/' + command}, 'sink': {'app': 'hood'}},
                  '+hood/' + command, timeout=10 if stopping else None, stopping=stopping)
    if not isinstance(result, str) or result.strip() not in ('', '>='):
        raise RuntimeError('Native hood command failed: ' + clean(result))


def action(noun, label):
    result = lens({'source': {'as': {'mark': 'git-action', 'next': {'dojo': noun}}},
                   'sink': {'app': 'urgit'}}, label)
    if result != '>=':
        raise RuntimeError('Native app action failed: ' + clean(result))


def git(*argv, cwd=ROOT, auth=False, input=None, expect=0):
    cancelled()
    env = {'PATH': '/usr/bin', 'HOME': '/home/audit', 'LANG': 'C.UTF-8',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_AUTHOR_DATE': '2026-09-12T00:00:00Z',
           'GIT_COMMITTER_DATE': '2026-09-12T00:00:00Z'}
    if auth:
        env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='http.extraHeader',
                   GIT_CONFIG_VALUE_0='Authorization: Basic ' + AUTH)
    args = ['/usr/bin/git', '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null', *argv]
    result = subprocess.run(args, cwd=cwd, env=env, input=input, capture_output=True, timeout=120)
    stdout = ('PACK sha256=' + hashlib.sha256(result.stdout).hexdigest()
              if result.stdout.startswith(b'PACK') else result.stdout.decode(errors='replace'))
    event('stock-git', argv=args, cwd=str(cwd), authenticated=auth,
          input_sha256=hashlib.sha256(input).hexdigest() if input else None,
          exit_code=result.returncode, stdout=stdout, stderr=result.stderr.decode(errors='replace'))
    if expect is not None and result.returncode != expect:
        raise RuntimeError('Unexpected Git exit: ' + repr(argv) + ': ' + str(result.returncode))
    return result


def ref():
    return git('ls-remote', URL, 'refs/heads/main').stdout.decode().split()[0]


def vectors():
    phase('native vectors and independent stock-Git object/pack validation')
    replies = {}
    for name in ('git-codec-vector', 'git-pack-vector', 'git-stock-pack-vector',
                 'git-delta-pack-vector', 'git-ofs-delta-pack-vector'):
        replies[name] = expression('+urgit!' + name)
    codec_oid = git('hash-object', '--stdin', input=b'hello world\n').stdout.decode().strip()
    check('native-codec-matches-stock-Git', codec_oid in replies['git-codec-vector'], oid=codec_oid)
    match = re.fullmatch(r'\[(\d+) ([\d.]+)\]\s*', replies['git-pack-vector'])
    if not match:
        raise AssertionError('native pack vector shape')
    pack = int(match[2].replace('.', '')).to_bytes(int(match[1]), 'little')
    bare = ROOT / 'native-pack-git'
    git('init', '--bare', '--initial-branch=main', str(bare))
    git('index-pack', '--strict', '--stdin', input=pack, cwd=bare)
    recovered = git('cat-file', 'blob', codec_oid, cwd=bare).stdout
    git('fsck', '--full', '--strict', cwd=bare)
    check('native-pack-accepted-by-stock-Git', recovered == b'hello world\n',
          pack_bytes=len(pack), pack_sha256=hashlib.sha256(pack).hexdigest(),
          expected_fsck_notice='single unreferenced blob; no default references')
    for name in ('git-stock-pack-vector', 'git-delta-pack-vector', 'git-ofs-delta-pack-vector'):
        reply = replies[name]
        check(name, 'decoded=%.y' in reply and '%.n' not in reply
              and (name == 'git-stock-pack-vector' or 'object-count=6' in reply), output=reply)
    (EVIDENCE / 'native-vectors.json').write_text(json.dumps(replies, indent=2) + '\n')


def smart_http():
    phase('stock-Git Smart HTTP corpus')
    action("[%create 'audit' %.y]", 'create synthetic public repository')
    action("[%set-write-token 'audit' '" + TOKEN + "']", 'set generated synthetic repository credential')
    client, clone = ROOT / 'client', ROOT / 'clone'
    git('init', '--initial-branch=main', str(client))
    git('config', 'user.name', 'Synthetic Vector', cwd=client)
    git('config', 'user.email', 'synthetic@example.invalid', cwd=client)
    (client / 'README.md').write_text('Synthetic Urgit ordinary-Git interoperability vector.\n')
    git('add', 'README.md', cwd=client)
    git('commit', '-m', 'synthetic first revision', cwd=client)
    first = git('rev-parse', 'HEAD', cwd=client).stdout.decode().strip()
    denied = git('push', URL, 'HEAD:refs/heads/main', cwd=client, expect=None)
    check('unauthenticated-push-denied', denied.returncode == 128
          and b'terminal prompts disabled' in denied.stderr and b'not found' not in denied.stderr)
    git('push', URL, 'HEAD:refs/heads/main', cwd=client, auth=True)
    check('push-preserves-original-oid', ref() == first, oid=first)
    git('clone', URL, str(clone))
    git('fsck', '--full', '--strict', cwd=clone)
    check('clone-fsck-roundtrip', git('rev-parse', 'HEAD', cwd=clone).stdout.decode().strip() == first
          and (clone / 'README.md').read_bytes() == (client / 'README.md').read_bytes())
    git('tag', '-a', 'v0-synthetic', '-m', 'synthetic annotated tag', cwd=client)
    tag = git('rev-parse', 'v0-synthetic', cwd=client).stdout.decode().strip()
    git('push', URL, 'refs/tags/v0-synthetic', cwd=client, auth=True)
    git('fetch', '--tags', 'origin', cwd=clone)
    check('annotated-tag-oid-preserved', git('rev-parse', 'v0-synthetic', cwd=clone).stdout.decode().strip() == tag, oid=tag)
    (client / 'README.md').write_text('Synthetic Urgit ordinary-Git interoperability vector.\nAccepted second revision.\n')
    git('commit', '-am', 'synthetic second revision', cwd=client)
    second = git('rev-parse', 'HEAD', cwd=client).stdout.decode().strip()
    git('push', URL, 'HEAD:refs/heads/main', cwd=client, auth=True)
    git('fetch', 'origin', cwd=clone)
    git('fsck', '--full', '--strict', cwd=clone)
    check('incremental-fetch-oid-preserved', git('rev-parse', 'origin/main', cwd=clone).stdout.decode().strip() == second, oid=second)
    (client / 'README.md').write_text('Synthetic candidate third revision remains unaccepted.\n')
    git('commit', '-am', 'synthetic unaccepted third revision', cwd=client)
    third = git('rev-parse', 'HEAD', cwd=client).stdout.decode().strip()
    stale = git('push', '--force-with-lease=refs/heads/main:' + first, URL,
                'HEAD:refs/heads/main', cwd=client, auth=True, expect=None)
    check('stale-client-lease-denied', stale.returncode == 1 and b'stale info' in stale.stderr and ref() == second,
          limitation='client lease check, not concurrent server CAS')
    pack = git('pack-objects', '--stdout', '--all', cwd=client).stdout
    command = (second + ' ' + third + ' refs/heads/main\0 report-status\n').encode()
    body = f'{len(command) + 4:04x}'.encode() + command + b'0000' + pack[:-1] + bytes([pack[-1] ^ 1])
    req = urllib.request.Request(URL + '/git-receive-pack', data=body,
                                 headers={'Content-Type': 'application/x-git-receive-pack-request',
                                          'Authorization': 'Basic ' + AUTH})
    with urllib.request.urlopen(req, timeout=120) as response:
        malformed = response.read(65536).decode()
    event('corrupted-pack', request_sha256=hashlib.sha256(body).hexdigest(), response=malformed)
    check('corrupt-pack-no-ref-change', 'unpack invalid or unsupported pack' in malformed
          and 'ng refs/heads/main unpack failed' in malformed and ref() == second)
    action("[%clear-write-token 'audit']", 'revoke synthetic repository credential')
    revoked = git('push', URL, 'HEAD:refs/heads/main', cwd=client, auth=True, expect=None)
    check('revoked-before-request-push-denied', revoked.returncode == 128
          and b'terminal prompts disabled' in revoked.stderr and ref() == second,
          limitation='revoked before request; no staged-revocation result')


def main():
    global PORT, RUNTIME
    marker = json.loads((INPUT / '.stead-disposable.json').read_text())
    if marker != {'format': 1, 'purpose': 'URB-025 isolated candidate evaluation', 'fake_identity': 'zod'}:
        raise ValueError('Missing exact disposable audit marker')
    if (ROOT / 'zod').exists() or Path('/home/skilgore').exists() or len(os.sched_getaffinity(0)) != 1:
        raise ValueError('Evaluator requires fresh pier and isolated one-CPU environment')
    routes = Path('/proc/net/route').read_text().splitlines()[1:]
    if any(line.split()[1] == '00000000' for line in routes):
        raise ValueError('Network namespace has a default route')
    baseline = json.loads((INPUT / 'bootstrap.json').read_text())
    args = bootstrap.argv(baseline['mode'], PIN['limits']['loom_exponent'])
    if baseline['mode'] == 'verified-stopped-fake-seed':
        shutil.copytree(INPUT / 'seed-zod', ROOT / 'zod')
        bootstrap.verify_work(ROOT / 'zod', baseline)
    report = {'status': 'failed', 'scope': PIN['profile'], 'checks': CHECKS,
              'excluded_claims': PIN['excluded_claims'], 'runtime_argv': args,
              'bootstrap': baseline}
    reader = None
    signal.signal(signal.SIGUSR1, interrupt_control)
    threading.Thread(target=watch_stop, daemon=True).start()
    try:
        phase('booting one pinned fake ship on one CPU')
        RUNTIME = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        reader = threading.Thread(target=log_runtime, args=(RUNTIME.stdout,), daemon=True)
        reader.start()
        deadline = time.monotonic() + PIN['limits']['boot_timeout_seconds']
        while time.monotonic() < deadline:
            cancelled()
            if RUNTIME.poll() is not None:
                raise RuntimeError('Native runtime exited before readiness')
            ports = ROOT / 'zod/.http.ports'
            if ports.exists():
                for line in ports.read_text().splitlines():
                    if 'loopback' in line:
                        PORT = int(line.split()[0])
                if PORT:
                    try:
                        ready = lens({'source': {'dojo': 'zuse'}, 'sink': {'stdout': None}}, 'kernel readiness', timeout=3)
                        if ready.strip() == '%' + str(TOOLCHAIN['kernel']['kelvin']):
                            break
                    except (RuntimeError, OSError):
                        pass
            time.sleep(1)
        else:
            raise TimeoutError('Pinned fake ship boot deadline')
        check('pinned-native-kernel-ready', ready.strip() == '%' + str(TOOLCHAIN['kernel']['kelvin']), result=ready.strip())
        identity = expression('our')
        # Clay's empty-desk %d lists all local desks; Gall %f lists non-nuked
        # agent incarnations, including suspended ones. These read native state.
        clean = expression('=/  desks=(set @tas)  .^((set @tas) %cd /(scot %p our)//(scot %da now))  =/  apps=(map @tas @)  .^((map @tas @) %gf /(scot %p our)//(scot %da now)/$)  ?&(!((~(has in desks) %urgit)) !((~(has by apps) %urgit)))')
        bootstrap.validate(identity, ready, clean)
        report['native_baseline'] = {'identity': identity, 'kelvin': ready, 'clean_urgit_state': clean}
        phase('compiling pinned native candidate desk')
        hood('new-desk %urgit')
        hood('mount %urgit')
        mount = ROOT / 'zod/urgit'
        if not mount.is_dir() or mount.is_symlink():
            raise RuntimeError('Native desk mount absent')
        shutil.copytree(INPUT / 'candidate/desk', mount, dirs_exist_ok=True)
        shutil.copyfile(INPUT / 'skeleton.hoon', mount / 'lib/skeleton.hoon')
        hood('commit %urgit')
        hood('install our %urgit')
        vectors()
        smart_http()
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = clean(repr(error))
        event('failure', error=repr(error))
    finally:
        FINISHING.set()
        phase('stopping the disposable fake ship')
        if RUNTIME is not None and RUNTIME.poll() is None:
            if PORT:
                try:
                    lens({'source': {'cancel': None}, 'sink': {'stdout': None}}, 'cancel pending control request', timeout=3, stopping=True)
                    hood('exit', stopping=True)
                except Exception as error:
                    event('shutdown-request-failure', error=repr(error))
            else:
                # A thermal stop during boot has no native control endpoint.
                # Do not keep that busy boot running for a grace period in
                # which no exit request could have been sent.
                report['status'] = 'failed'
                report['shutdown_fallback'] = 'SIGTERM: native control endpoint unavailable'
                try:
                    os.killpg(RUNTIME.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                RUNTIME.wait(timeout=30)
            except subprocess.TimeoutExpired:
                report['status'] = 'failed'
                report['shutdown_fallback'] = 'SIGTERM after native exit deadline'
                os.killpg(RUNTIME.pid, signal.SIGTERM)
                try:
                    RUNTIME.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(RUNTIME.pid, signal.SIGKILL)
                    RUNTIME.wait(timeout=10)
                    report['shutdown_fallback'] = 'SIGKILL after termination deadline'
        if reader is not None:
            reader.join(timeout=5)
            if reader.is_alive():
                report['status'] = 'failed'
                report['error'] = 'runtime output did not close after shutdown'
        report['runtime_exit_code'] = RUNTIME.returncode if RUNTIME is not None else None
        if report['runtime_exit_code'] != 0:
            report['status'] = 'failed'
        EVENTS.flush()
        logs_clean = all(not any(value.encode() in p.read_bytes() for value in REDACTIONS)
                         for p in EVIDENCE.iterdir() if p.is_file())
        report['generated_credential_absent_from_evidence'] = logs_clean
        if not logs_clean:
            # Never publish an accidental credential in evidence, even though
            # the namespace and pier are disposable and inaccessible externally.
            for path in EVIDENCE.iterdir():
                if path.is_file():
                    raw = path.read_bytes()
                    for value in REDACTIONS:
                        raw = raw.replace(value.encode(), b'<generated-synthetic-credential>')
                    path.write_bytes(raw)
            report['status'] = 'failed'
            report['error'] = 'credential redaction invariant failed; evidence scrubbed'
        (EVIDENCE / 'report.json').write_text(clean(report) + '\n')
        phase(report['status'])
        print(clean({'status': report['status'], 'checks': len(CHECKS), 'runtime_exit_code': report['runtime_exit_code']}), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

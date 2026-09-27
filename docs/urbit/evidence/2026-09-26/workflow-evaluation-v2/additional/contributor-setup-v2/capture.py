"""Record clean pinned setup/doctor on existing Linux prerequisites; no ships."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/skilgore/stead-urbit')
OUT = ROOT / '.runtime/phase01-20260926/contributor-clean-setup-v2'
HEAD = '55475f0565ceb38db9eb5bc057962967398aa5da'
ORIGIN = 'https://github.com/ScottTpirate/stead-urbit.git'
UPSTREAM = 'https://github.com/ScottTpirate/stead.git'

def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()

def remotes(cwd=ROOT):
    assert git('remote', 'get-url', 'origin', cwd=cwd) == ORIGIN
    assert git('remote', 'get-url', '--push', 'origin', cwd=cwd) == ORIGIN
    assert git('remote', 'get-url', 'upstream', cwd=cwd) == UPSTREAM
    assert git('remote', 'get-url', '--push', 'upstream', cwd=cwd) == 'DISABLED_UPSTREAM_PUSH'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

remotes()
assert git('rev-parse', 'HEAD') == HEAD
assert os.sched_getaffinity(0) == {19}
cg = Path('/proc/self/cgroup').read_text().strip().split('::')[1]
cpu = (Path('/sys/fs/cgroup') / cg.lstrip('/') / 'cpu.max').read_text().strip()
assert cpu == '5000 10000'
assert not OUT.exists()
OUT.mkdir(mode=0o700)
CLONE = OUT / 'checkout'
record = {'protocol': 'stead.clean-contributor-setup/1', 'source_commit': HEAD,
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'classification': 'real pinned network downloads and local namespace setup; no Hoon execution',
    'scope': {'cpu_max': cpu, 'affinity': [19], 'control_group': cg},
    'steps': [], 'status': 'running', 'native_ships_started': False,
    'limits': ['Uses existing Linux host prerequisites; not a fresh OS installation.',
        'No source edits, native boot, participant trial, user study or Phase 1 acceptance.',
        'Source clone is local; GitHub clone authentication is not exercised.']}

def save():
    remotes()
    (OUT / 'result.json').write_text(json.dumps(record, indent=2) + '\n')

def step(name, command, cwd):
    remotes()
    start = time.monotonic()
    with (OUT / (name + '.stdout.log')).open('xb') as out, (OUT / (name + '.stderr.log')).open('xb') as err:
        done = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, timeout=900)
    row = {'name': name, 'command': command, 'cwd': str(cwd.relative_to(ROOT)) or '.',
        'exit_code': done.returncode, 'elapsed_seconds': time.monotonic() - start}
    for stream in ('stdout', 'stderr'):
        p = OUT / f'{name}.{stream}.log'
        row[stream] = {'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
    record['steps'].append(row)
    save()
    print(json.dumps(row), flush=True)
    if done.returncode:
        raise RuntimeError(f'{name} failed with exit {done.returncode}')

save()
try:
    step('clone', ['git', 'clone', '--no-local', '--no-hardlinks', '--no-checkout',
         '--single-branch', '--branch', 'increment/phase01-closeout-20260925', str(ROOT), str(CLONE)], ROOT)
    remotes()
    subprocess.run(['git', 'remote', 'set-url', 'origin', ORIGIN], cwd=CLONE, check=True)
    remotes()
    subprocess.run(['git', 'remote', 'add', 'upstream', UPSTREAM], cwd=CLONE, check=True)
    remotes()
    subprocess.run(['git', 'remote', 'set-url', '--push', 'upstream', 'DISABLED_UPSTREAM_PUSH'], cwd=CLONE, check=True)
    remotes(CLONE)
    step('checkout', ['git', 'checkout', '--detach', HEAD], CLONE)
    assert git('rev-parse', 'HEAD', cwd=CLONE) == HEAD
    assert git('status', '--porcelain', cwd=CLONE) == ''
    assert not (CLONE / '.runtime').exists() and not (CLONE / '.piers').exists()
    record['initial'] = {'tracked_clean': True, 'runtime_absent': True, 'piers_absent': True,
        'tree': git('rev-parse', 'HEAD^{tree}', cwd=CLONE),
        'remotes': git('remote', '-v', cwd=CLONE).splitlines()}
    save()
    for name, command in [('help', ['make']), ('setup', ['make', 'setup']),
                         ('doctor', ['make', 'doctor']), ('status', ['make', 'status'])]:
        remotes(CLONE)
        step(name, command, CLONE)
    assert git('status', '--porcelain', cwd=CLONE) == ''
    data = json.loads((CLONE / 'specs/urbit/toolchain.lock.json').read_text())
    record['downloads'] = []
    for key in ('runtime', 'kernel', 'boot_artifact', 'frontend'):
        item = data[key]
        p = CLONE / '.runtime/downloads' / item['archive']
        assert sha(p) == item['sha256']
        record['downloads'].append({'key': key, 'url': item['url'], 'file': item['archive'],
                                   'bytes': p.stat().st_size, 'sha256': sha(p)})
    record['final'] = {'tracked_clean': True, 'live_piers_exist': (CLONE / '.piers/fakes/live').exists(),
        'control_socket_exists': (CLONE / '.piers/fakes/control.sock').exists(),
        'namespace_negative_result': (OUT / 'doctor.stdout.log').read_text().splitlines()[1]}
    assert not record['final']['live_piers_exist'] and not record['final']['control_socket_exists']
    record['status'] = 'passed'
except BaseException as error:
    record['status'] = 'failed'
    record['error'] = type(error).__name__ + ': ' + str(error)
    raise
finally:
    record['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()

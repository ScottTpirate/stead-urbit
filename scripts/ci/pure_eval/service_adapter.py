"""Private fixed pure evaluator adapter; caller must authenticate immutable hosted source first."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import select
import signal
import stat
import subprocess
import sys
import time
import types
PREFIX='scripts/ci/pure_eval/'
DATA_PREFIX=PREFIX+'data/'
MODEL_DATA_PREFIX=PREFIX+'model_data/'
DEBUG_DATA_PREFIX=PREFIX+'debug_data/'
DEBUG_COMPOSITION='adecaa18bc47cf8dd60bb10198eadba0abd4554f852dc0c30dbb020e6b5082a8'
REPOSITORY_COMPOSITION='1c1f04d82fcfc4eac6f5edf5d00b39f29bbbeb541687fb5df5a431726810a280'
MODEL_COMPOSITION='c23002a6a5d1423167a0ef2caa9c35bc86b5ccc64ba3fff640dc73edfd9dfaa6'
MODEL_SOURCE_PATHS={'native/core/desk/lib/stead-actor.hoon': 'native/core/desk/lib/stead-actor.hoon', 'native/core/desk/lib/stead-codec-v1.hoon': 'native/core/desk/lib/stead-codec-v1.hoon', 'native/core/desk/lib/stead-codec.hoon': 'native/core/desk/lib/stead-codec.hoon', 'native/core/desk/lib/stead-core-v1.hoon': 'native/core/desk/lib/stead-core-v1.hoon', 'native/core/desk/lib/stead-core.hoon': 'native/core/desk/lib/stead-core.hoon', 'native/core/desk/lib/stead-git.hoon': 'native/core/desk/lib/stead-git.hoon', 'native/core/desk/lib/stead-model-codec.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/lib/stead-model-codec.hoon', 'native/core/desk/lib/stead-model-material.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/lib/stead-model-material.hoon', 'native/core/desk/lib/stead-model-reply.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/lib/stead-model-reply.hoon', 'native/core/desk/lib/stead-model-turn-codec.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/lib/stead-model-turn-codec.hoon', 'native/core/desk/lib/stead-principals.hoon': 'native/core/desk/lib/stead-principals.hoon', 'native/core/desk/lib/stead-run-codec.hoon': 'native/core/desk/lib/stead-run-codec.hoon', 'native/core/desk/lib/stead-run-state.hoon': 'native/core/desk/lib/stead-run-state.hoon', 'native/core/desk/lib/stead-session.hoon': 'native/core/desk/lib/stead-session.hoon', 'native/core/desk/lib/stead-team-codec.hoon': 'native/core/desk/lib/stead-team-codec.hoon', 'native/core/desk/lib/stead-team-config.hoon': 'native/core/desk/lib/stead-team-config.hoon', 'native/core/desk/lib/stead-team.hoon': 'native/core/desk/lib/stead-team.hoon', 'native/core/desk/tests/stead-model-codec.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/tests/stead-model-codec.hoon', 'native/core/desk/tests/stead-model-reply.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/tests/stead-model-reply.hoon', 'native/core/desk/tests/stead-model-turn-codec.hoon': 'scripts/ci/pure_eval/model_data/native/core/desk/tests/stead-model-turn-codec.hoon', 'pkg/base-dev/lib/test.hoon': 'scripts/ci/pure_eval/data/pkg/base-dev/lib/test.hoon'}
# Exact logical-source to immutable captured-controller path map; no fallback.
FIXED_SOURCE_PATHS = {'native/core/desk/lib/stead-actor.hoon': 'native/core/desk/lib/stead-actor.hoon', 'native/core/desk/lib/stead-code-ancestry.hoon': 'native/core/desk/lib/stead-code-ancestry.hoon', 'native/core/desk/lib/stead-code-build-home.hoon': 'native/core/desk/lib/stead-code-build-home.hoon', 'native/core/desk/lib/stead-code-credentials.hoon': 'native/core/desk/lib/stead-code-credentials.hoon', 'native/core/desk/lib/stead-code-delivery-export.hoon': 'native/core/desk/lib/stead-code-delivery-export.hoon', 'native/core/desk/lib/stead-code-delivery.hoon': 'native/core/desk/lib/stead-code-delivery.hoon', 'native/core/desk/lib/stead-code-fetch-wire.hoon': 'native/core/desk/lib/stead-code-fetch-wire.hoon', 'native/core/desk/lib/stead-code-fetch.hoon': 'native/core/desk/lib/stead-code-fetch.hoon', 'native/core/desk/lib/stead-code-git-delta.hoon': 'native/core/desk/lib/stead-code-git-delta.hoon', 'native/core/desk/lib/stead-code-git-emit.hoon': 'native/core/desk/lib/stead-code-git-emit.hoon', 'native/core/desk/lib/stead-code-git-entry.hoon': 'native/core/desk/lib/stead-code-git-entry.hoon', 'native/core/desk/lib/stead-code-git-graph.hoon': 'native/core/desk/lib/stead-code-git-graph.hoon', 'native/core/desk/lib/stead-code-git-inflate.hoon': 'native/core/desk/lib/stead-code-git-inflate.hoon', 'native/core/desk/lib/stead-code-git-objects.hoon': 'native/core/desk/lib/stead-code-git-objects.hoon', 'native/core/desk/lib/stead-code-git-pack.hoon': 'native/core/desk/lib/stead-code-git-pack.hoon', 'native/core/desk/lib/stead-code-git-pkt.hoon': 'native/core/desk/lib/stead-code-git-pkt.hoon', 'native/core/desk/lib/stead-code-git-resolve.hoon': 'native/core/desk/lib/stead-code-git-resolve.hoon', 'native/core/desk/lib/stead-code-git-response.hoon': 'native/core/desk/lib/stead-code-git-response.hoon', 'native/core/desk/lib/stead-code-home.hoon': 'native/core/desk/lib/stead-code-home.hoon', 'native/core/desk/lib/stead-code-http.hoon': 'native/core/desk/lib/stead-code-http.hoon', 'native/core/desk/lib/stead-code-pack-anchor.hoon': 'native/core/desk/lib/stead-code-pack-anchor.hoon', 'native/core/desk/lib/stead-code-pack-ledger.hoon': 'native/core/desk/lib/stead-code-pack-ledger.hoon', 'native/core/desk/lib/stead-code-pack-promotion.hoon': 'native/core/desk/lib/stead-code-pack-promotion.hoon', 'native/core/desk/lib/stead-code-pack-push.hoon': 'native/core/desk/lib/stead-code-pack-push.hoon', 'native/core/desk/lib/stead-code-pack-review-board.hoon': 'native/core/desk/lib/stead-code-pack-review-board.hoon', 'native/core/desk/lib/stead-code-pack-review.hoon': 'native/core/desk/lib/stead-code-pack-review.hoon', 'native/core/desk/lib/stead-code-receive-wire.hoon': 'native/core/desk/lib/stead-code-receive-wire.hoon', 'native/core/desk/lib/stead-code-receive.hoon': 'native/core/desk/lib/stead-code-receive.hoon', 'native/core/desk/lib/stead-code-review-api.hoon': 'native/core/desk/lib/stead-code-review-api.hoon', 'native/core/desk/lib/stead-code-review-home.hoon': 'native/core/desk/lib/stead-code-review-home.hoon', 'native/core/desk/lib/stead-code-review.hoon': 'native/core/desk/lib/stead-code-review.hoon', 'native/core/desk/lib/stead-code-service.hoon': 'native/core/desk/lib/stead-code-service.hoon', 'native/core/desk/lib/stead-code-store.hoon': 'native/core/desk/lib/stead-code-store.hoon', 'native/core/desk/lib/stead-code-upload.hoon': 'native/core/desk/lib/stead-code-upload.hoon', 'native/core/desk/lib/stead-codec-v1.hoon': 'native/core/desk/lib/stead-codec-v1.hoon', 'native/core/desk/lib/stead-codec.hoon': 'native/core/desk/lib/stead-codec.hoon', 'native/core/desk/lib/stead-core-v1.hoon': 'native/core/desk/lib/stead-core-v1.hoon', 'native/core/desk/lib/stead-core.hoon': 'native/core/desk/lib/stead-core.hoon', 'native/core/desk/lib/stead-git.hoon': 'native/core/desk/lib/stead-git.hoon', 'native/core/desk/lib/stead-http.hoon': 'native/core/desk/lib/stead-http.hoon', 'native/core/desk/lib/stead-principals.hoon': 'native/core/desk/lib/stead-principals.hoon', 'native/core/desk/lib/stead-project-retirement.hoon': 'native/core/desk/lib/stead-project-retirement.hoon', 'native/core/desk/lib/stead-repository-authority.hoon': 'scripts/ci/pure_eval/data/native/core/desk/lib/stead-repository-authority.hoon', 'native/core/desk/lib/stead-repository-catalog.hoon': 'scripts/ci/pure_eval/data/native/core/desk/lib/stead-repository-catalog.hoon', 'native/core/desk/lib/stead-repository-import.hoon': 'scripts/ci/pure_eval/data/native/core/desk/lib/stead-repository-import.hoon', 'native/core/desk/lib/stead-repository-store.hoon': 'scripts/ci/pure_eval/data/native/core/desk/lib/stead-repository-store.hoon', 'native/core/desk/lib/stead-session.hoon': 'native/core/desk/lib/stead-session.hoon', 'native/core/desk/lib/stead-team-codec.hoon': 'native/core/desk/lib/stead-team-codec.hoon', 'native/core/desk/lib/stead-team-config.hoon': 'native/core/desk/lib/stead-team-config.hoon', 'native/core/desk/lib/stead-team.hoon': 'native/core/desk/lib/stead-team.hoon', 'native/core/desk/tests/stead-repository-authority.hoon': 'scripts/ci/pure_eval/data/native/core/desk/tests/stead-repository-authority.hoon', 'native/core/desk/tests/stead-repository-catalog.hoon': 'scripts/ci/pure_eval/data/native/core/desk/tests/stead-repository-catalog.hoon', 'native/core/desk/tests/stead-repository-import.hoon': 'scripts/ci/pure_eval/data/native/core/desk/tests/stead-repository-import.hoon', 'native/core/desk/tests/stead-repository-store.hoon': 'scripts/ci/pure_eval/data/native/core/desk/tests/stead-repository-store.hoon', 'pkg/base-dev/lib/test.hoon': 'scripts/ci/pure_eval/data/pkg/base-dev/lib/test.hoon'}
SOURCE_PATHS={'worker.py':PREFIX+'worker.py','codec.py':PREFIX+'codec.py',
 'interface.json':PREFIX+'interface.json','composition.json':DATA_PREFIX+'composition.json',
 'owned_child.py':'scripts/urbit/owned_child.py'}
MODULE_PATHS={'owner_boundary':PREFIX+'owner_boundary.py','owner_collection':PREFIX+'owner_collection.py',
 'pure_intake':PREFIX+'intake.py','codec':PREFIX+'codec.py'}
SETUP_SECONDS=720
UNIT_WAIT_SECONDS=630
REPORT_LIMIT=4194304
METADATA_RESERVE=131072

def require(ok):
    if not ok:
        raise ValueError('Fixed hosted pure evaluator adapter refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return {'bytes': len(raw), 'sha256': sha(raw)}


def load(hosted):
    """Only captured immutable controller bytes; no filesystem import search."""
    require(os.getuid() == 0 and sys.flags.isolated and sys.dont_write_bytecode)
    result = {}
    for name, path in MODULE_PATHS.items():
        require(name not in sys.modules)
        raw = hosted.CONTROLLER_FILES[path]
        require(type(raw) is bytes and 0 < len(raw) <= 262144)
        module = types.ModuleType(name)
        module.__file__ = str(hosted.CAPTURED / path)
        sys.modules[name] = module
        exec(compile(raw, module.__file__, 'exec'), module.__dict__)
        result[name] = module
    return result


def write_new(path, raw, *, mode=0o600, gid=0):
    require(type(raw) is bytes and len(raw) <= 4 * 1024**2)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        os.fchown(fd, 0, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def read_json(boundary, path, maximum):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    raw = boundary.read_file(path, maximum)
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    require(canonical(value) == raw)
    return value


def source_map(hosted):
    return {path: pin(raw) for path, raw in hosted.CONTROLLER_FILES.items()}


def setup_failure_positions(hosted, intake, error, phase):
    """Closed positions from captured intake code; never exception text or locals."""
    require(phase in ('admission', 'apparmor', 'bwrap', 'intake', 'input',
                      'launch', 'execution', 'result'))
    path = MODULE_PATHS['pure_intake']
    raw = hosted.CONTROLLER_FILES[path]
    filename = str(hosted.CAPTURED / path)
    require(type(raw) is bytes and 0 < len(raw) <= 262144
            and intake.__file__ == filename)
    root = compile(raw, filename, 'exec')  # Inspect code only; no execution.
    admitted, pending = [], [root]
    while pending:
        code = pending.pop()
        require(len(admitted) < 256)
        admitted.append(code)
        pending.extend(value for value in code.co_consts if type(value) is types.CodeType)
    line_count = len(raw.splitlines())
    locations, seen, inspected, truncated = [], set(), 0, False
    trace = error.__traceback__
    while trace is not None and inspected < 64:
        inspected += 1
        code, line = trace.tb_frame.f_code, trace.tb_lineno
        if (code.co_filename == filename and code in admitted
                and type(line) is int and 1 <= line <= line_count
                and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', code.co_name)):
            key = (code.co_name, line)
            if key not in seen:
                seen.add(key)
                if len(locations) < 16:
                    locations.append({'function': key[0], 'line': key[1]})
                else:
                    truncated = True
        trace = trace.tb_next
    return {'protocol': 'stead.fixed-pure-eval-setup-failure/1', 'phase': phase,
            'source_sha256': sha(raw), 'locations': locations,
            'frames_inspected': inspected, 'truncated': truncated or trace is not None}


def job_context(hosted, boundary, job):
    require(re.fullmatch('/var/lib/stead-pure-eval-proof-[a-z0-9]{8}', str(job)) is not None)
    hosted.regular_root(job)
    value = read_json(boundary, job / 'guardian.json', 2 * 1024**2)
    require(type(value) is dict and set(value) == {'protocol', 'boundary', 'owner', 'identity',
        'workflow_binding', 'controller_files', 'outer_pid', 'outer_start', 'created_monotonic_ns'})
    require(value['protocol'] == 'stead.fixed-pure-eval-guardian-input/1'
            and canonical(value['controller_files']) == canonical(source_map(hosted)))
    binding = value['workflow_binding']
    commit = hosted.local.git('rev-parse', 'HEAD').decode().strip()
    require(canonical(binding) == canonical(hosted.workflow_binding(binding['workflow_commit'], commit)))
    require(value['identity']['workflow_sha'] == binding['workflow_commit']
            and value['identity']['repository'] == hosted.hosted_identity.REPOSITORY
            and value['identity']['runner_environment'] == 'github-hosted')
    boundary.context(value['boundary'])
    selected_sources, _, _ = selected_paths(value['boundary']['sources']['composition.json']['sha256'])
    require(value['boundary']['sources'] == {name: pin(hosted.CONTROLLER_FILES[path])
        for name, path in selected_sources.items()})
    require(canonical(value['owner']) == boundary.read_file(job / 'input/owner.json', 262144))
    require(type(value['outer_pid']) is int and value['outer_pid'] > 1
            and type(value['outer_start']) is int and value['outer_start'] > 0
            and type(value['created_monotonic_ns']) is int)
    return value


def lease_bytes(path, expected_uid, expected_gid, expected_mode):
    """Read one immutable published inode, including an atomically unlinked old one."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        def admitted(info):
            return (stat.S_ISREG(info.st_mode) and info.st_uid == expected_uid
                    and info.st_gid == expected_gid and stat.S_IMODE(info.st_mode) == expected_mode
                    and info.st_nlink in (0, 1) and 0 < info.st_size <= 1024)
        def stable(info):
            return (info.st_dev, info.st_ino, info.st_uid, info.st_gid,
                    info.st_mode, info.st_size, info.st_mtime_ns)
        require(admitted(before))
        raw = os.read(fd, 1025)
        after = os.fstat(fd)
        require(admitted(after) and stable(before) == stable(after) and len(raw) == before.st_size)
        return raw
    finally:
        os.close(fd)


def lease_read(boundary, path, owner_sha256, last):
    raw = lease_bytes(path, 0, 0, 0o600)
    row = json.loads(raw)
    require(canonical(row) == raw)
    require(type(row) is dict and set(row) == {'protocol', 'owner_sha256', 'generation', 'issued_ns', 'expires_ns'}
            and row['protocol'] == 'stead.fixed-pure-eval-lease/1' and row['owner_sha256'] == owner_sha256
            and all(type(row[k]) is int for k in ('generation', 'issued_ns', 'expires_ns'))
            and 0 < row['generation'] <= 10000000
            and row['expires_ns'] - row['issued_ns'] == 5000000000
            and 0 < row['issued_ns'] <= time.monotonic_ns() < row['expires_ns'])
    current = (row['generation'], row['issued_ns'])
    require(current == last or (current[0] > last[0] and current[1] > last[1]))
    return current


def lease_publish(job, label, owner_sha256, generation, gid):
    require(label in ('caller', 'guardian') and type(generation) is int and 0 < generation <= 10000000)
    now = time.monotonic_ns()
    raw = canonical({'protocol': 'stead.fixed-pure-eval-lease/1', 'owner_sha256': owner_sha256,
        'generation': generation, 'issued_ns': now, 'expires_ns': now + 5000000000})
    require(len(raw) <= 1024)
    # The temporary is outside the /lease bind, so its inventory stays closed.
    temporary = job / ('.lease-' + label + '-' + secrets.token_hex(8))
    destination = job / 'caller-lease.json' if label == 'caller' else job / 'lease/guardian.json'
    try:
        write_new(temporary, raw, mode=0o600 if label == 'caller' else 0o440,
                  gid=0 if label == 'caller' else gid)
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def heartbeat_factory(hosted, boundary, value, job):
    """Root-owned source record plus actual parent pidfd/EOF and finite service."""
    require(stat.S_ISFIFO(os.fstat(0).st_mode))
    os.set_blocking(0, False)
    parent = value['outer_pid']
    fd = os.pidfd_open(parent, 0)
    expected = (parent, value['outer_start'])
    try:
        require(boundary.proc_identity(parent) == expected)
    except BaseException:
        os.close(fd)
        raise
    previous = time.monotonic_ns()
    last, generation = (0, 0), 0
    owner_sha256 = sha(canonical(value['owner']))
    def guard():
        nonlocal previous, last, generation
        now = time.monotonic_ns()
        require(previous <= now and 0 <= now - value['created_monotonic_ns'] < 600 * 10**9)
        previous = now
        require(not select.select([fd], [], [], 0)[0]
                and boundary.proc_identity(parent) == expected)
        if select.select([0], [], [], 0)[0]:
            # No bytes are permitted on the lifetime pipe; either bytes or EOF
            # ends admission. It is never the worker's separate go channel.
            os.read(0, 1)
            raise ValueError('Fixed model caller ended')
        hosted.hosted_apparmor.require_label()
        boundary.group(value['boundary'])
        last = lease_read(boundary, job / 'caller-lease.json', owner_sha256, last)
        generation += 1
        lease_publish(job, 'guardian', owner_sha256, generation, value['boundary']['host_gid'])
    return guard, fd


def closed_error(error):
    name = type(error).__name__
    return name if name in {'ValueError', 'TypeError', 'OSError', 'TimeoutError', 'PermissionError',
        'FileNotFoundError', 'ProcessLookupError', 'BrokenPipeError', 'CalledProcessError',
        'TimeoutExpired', 'JSONDecodeError', 'UnicodeDecodeError'} else 'unrecognized'


def child(hosted, job, parent):
    modules = load(hosted)
    boundary = modules['owner_boundary']
    value = job_context(hosted, boundary, job)
    boundary.group(value['boundary'])
    boundary.launch_child(job, value['boundary'], parent)
    raise AssertionError('Fixed child exec returned')


def service_command(hosted, collection, job, context):
    require(re.fullmatch('stead-pure-eval-[a-f0-9]{32}\\.service', context['unit']) is not None)
    command = ['/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--service-type=exec',
               '--unit=' + context['unit']]
    command.extend('--property=' + key + '=' + value
                   for key, value in collection.service_properties(context['cpu']).items())
    return command + ['/usr/bin/python3', '-I', '-B', str(Path(hosted.__file__)), '_pure_guardian', str(job)]


def fixed_data(hosted, codec, composition_sha256=REPOSITORY_COMPOSITION):
    selected = codec.profile(composition_sha256)
    source_paths, fixed_paths, data_prefix = selected_paths(composition_sha256)
    composition_raw = hosted.CONTROLLER_FILES[source_paths['composition.json']]
    require(sha(composition_raw) == selected['composition_sha256'])
    composition = json.loads(composition_raw)
    paths = set(composition['sources']) | {composition['composition']['test_helper']['path']}
    require(len(paths) == selected['source_files'] and set(fixed_paths) == paths)
    expected_data = {path for path in fixed_paths.values() if path.startswith(data_prefix)}
    expected_data.add(data_prefix + 'composition.json')
    require({path for path in hosted.CONTROLLER_FILES if path.startswith(data_prefix)} == expected_data)
    files = {}
    for name, path in fixed_paths.items():
        raw = hosted.CONTROLLER_FILES[path]
        expected = composition['sources'][name] if name in composition['sources'] else composition['composition']['test_helper']
        require(type(raw) is bytes and pin(raw) == {'bytes': expected['bytes'], 'sha256': expected['sha256']})
        files[name] = raw
    jobs = codec.jobs(files, composition_raw)
    require(codec.job_profile(jobs) == selected)
    return files, jobs, {name: sha(raw) for name, raw in files.items()}


def selected_paths(composition_sha256=REPOSITORY_COMPOSITION):
    """Only three source-owned maps; no caller path, prefix, source or suite list."""
    require(type(composition_sha256) is str)
    if composition_sha256 == REPOSITORY_COMPOSITION:
        return dict(SOURCE_PATHS), dict(FIXED_SOURCE_PATHS), DATA_PREFIX
    if composition_sha256 == DEBUG_COMPOSITION:
        sources = dict(SOURCE_PATHS)
        sources['interface.json'] = PREFIX + 'debug-interface.json'
        sources['composition.json'] = DEBUG_DATA_PREFIX + 'composition.json'
        return sources, dict(FIXED_SOURCE_PATHS), DEBUG_DATA_PREFIX
    require(composition_sha256 == MODEL_COMPOSITION)
    sources = dict(SOURCE_PATHS)
    sources['interface.json'] = PREFIX + 'model-interface.json'
    sources['composition.json'] = MODEL_DATA_PREFIX + 'composition.json'
    return sources, dict(MODEL_SOURCE_PATHS), MODEL_DATA_PREFIX


def complete_guard(guard, allow_failure=False):
    require(type(guard) is dict and guard['protocol'] == 'stead.fixed-pure-eval-guard/1'
            and guard['status'] in (('pass','fail') if allow_failure else ('pass',))
            and guard['error_class'] == guard['cleanup_error_class'] == 'none'
            and guard['parent_admitted'] is True and guard['owned_children_empty'] is True
            and guard['child_streams_eof'] is True and guard['adapter_owned_cleanup'] is True
            and guard['qualifies_phase'] is False and type(guard['worker_result']) is dict
            and guard['worker_result']['status'] == guard['status']
            and guard['worker_result']['report'] == guard['report_pin'])
    row=guard['report_pin']
    require(type(row) is dict and set(row)=={'bytes','sha256'} and type(row['bytes']) is int
            and 0 < row['bytes'] <= REPORT_LIMIT and type(row['sha256']) is str
            and re.fullmatch('[a-f0-9]{64}',row['sha256']))


def guardian(hosted, job):
    modules=load(hosted)
    boundary,collection,codec=(modules[n] for n in ('owner_boundary','owner_collection','codec'))
    value=job_context(hosted,boundary,job);context=value['boundary']
    _,jobs,hashes=fixed_data(hosted,codec,context['sources']['composition.json']['sha256'])
    heartbeat,parentfd=heartbeat_factory(hosted,boundary,value,job)
    process=None;result=None;artifact=None;closed=False
    try:
        heartbeat();collection.service_current(context)
        require(set((boundary.group(context)/'cgroup.procs').read_text().splitlines())=={str(os.getpid())})
        command=['/usr/bin/python3','-I','-B',str(Path(hosted.__file__)),'_pure_child',str(job),str(os.getpid())]
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            close_fds=True,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        diagnostic_sources = {name: {'raw': hosted.CONTROLLER_FILES[MODULE_PATHS[name]],
            'filename': str(hosted.CAPTURED / MODULE_PATHS[name])}
            for name in ('owner_collection','owner_boundary')}
        diagnostic_sources['service_adapter'] = {
            'raw': hosted.CONTROLLER_FILES[PREFIX + 'service_adapter.py'],
            'filename': __file__}
        result,artifact=collection.run(process,job,context,value['owner'],heartbeat,codec,jobs,hashes,
                                      diagnostic_sources=diagnostic_sources)
    except BaseException as error:
        result={'protocol':'stead.fixed-pure-eval-adapter-failure/1','status':'fail',
                'error_class':closed_error(error),'qualifies_phase':False}
    finally:
        if process is not None:
            try:
                if process.stdin is not None and not process.stdin.closed:process.stdin.close()
            except BaseException:pass
            try:closed=collection.cleanup(process,context)
            except BaseException:closed=False
            for stream in (process.stdout,process.stderr):
                try:
                    if stream is not None:stream.close()
                except BaseException:closed=False
        else:
            closed=set((boundary.group(context)/'cgroup.procs').read_text().splitlines())=={str(os.getpid())}
        os.close(parentfd)
        require(result is not None);result['adapter_owned_cleanup']=closed
        if not closed:result['status']='fail';artifact=None
        if artifact is not None:
            complete_guard(result,allow_failure=True)
            require(pin(artifact)==result['report_pin'])
            retained=job/'retained';retained.mkdir(mode=0o700);os.chmod(retained,0o700)
            write_new(retained/'report.json',artifact)
        require(len(canonical(result)) <= 32768)
        write_new(job/'pure-guard.json',canonical(result))
    return 0 if result['status']=='pass' else 1


def checked_report(hosted,boundary,collection,codec,job,guard):
    complete_guard(guard,allow_failure=True)
    require(type(guard['worker_exit_code']) is int
            and guard['worker_exit_code']==(0 if guard['status']=='pass' else 1))
    directory=job/'retained';boundary.directory(directory,0o700)
    require({p.name for p in directory.iterdir()}=={'report.json'})
    raw=boundary.read_file(directory/'report.json',REPORT_LIMIT,guard['report_pin'])
    context=job_context(hosted,boundary,job)
    _,jobs,hashes=fixed_data(hosted,codec,context['boundary']['sources']['composition.json']['sha256'])
    report=collection.validate_report(raw,codec,jobs,hashes)
    require(report['status']==guard['status'])
    return raw


def outer(hosted,args,identity,binding):
    """Existing repository profile remains the default and existing hosted entry."""
    return _outer(hosted,args,identity,binding,REPOSITORY_COMPOSITION)


def outer_model_simple(hosted,args,identity,binding):
    """Fixed model-codec entry; no model inference."""
    return _outer(hosted,args,identity,binding,MODEL_COMPOSITION)


def outer_repository_debug(hosted,args,identity,binding):
    """Only the fixed catalog diagnostic with its unchanged original controls."""
    return _outer(hosted,args,identity,binding,DEBUG_COMPOSITION)

def _outer(hosted,args,identity,binding,composition_sha256):
    modules=load(hosted)
    boundary,collection,intake,codec=(modules[n] for n in ('owner_boundary','owner_collection','pure_intake','codec'))
    selected=codec.profile(composition_sha256)
    expected_mode={REPOSITORY_COMPOSITION:'pure', MODEL_COMPOSITION:'pure-model-simple',
                   DEBUG_COMPOSITION:'pure-repository-debug'}[composition_sha256]
    require(args.mode==expected_mode and args.control is None and args.candidate==args.controller
            and binding['controller_commit']==args.controller and identity['workflow_sha']==args.workflow)
    files,jobs,hashes=fixed_data(hosted,codec,composition_sha256)
    selected_sources,_,_=selected_paths(composition_sha256)
    started=time.monotonic();outer_pid=os.getpid();outer_identity=boundary.proc_identity(outer_pid)
    def setup_guard():
        require(os.geteuid()==0 and boundary.proc_identity(outer_pid)==outer_identity
                and 0<=time.monotonic()-started<SETUP_SECONDS)
        hosted.regular_root(hosted.ROOT)
    run_id=secrets.token_hex(16);job=Path('/var/lib/stead-pure-eval-proof-'+secrets.token_hex(4))
    account=pwd.getpwnam('runner')
    require(0<account.pw_uid<65534 and 0<account.pw_gid<65534 and not job.exists())
    context={'protocol':'stead.fixed-pure-eval-owner-context/1','run_id':run_id,
             'unit':'stead-pure-eval-'+run_id+'.service','cpu':min(os.sched_getaffinity(0)),
             'host_uid':account.pw_uid,'host_gid':account.pw_gid,
             'sources':{name:pin(hosted.CONTROLLER_FILES[path]) for name,path in selected_sources.items()},
             'bwrap_sha256':sha(boundary.read_file(Path('/usr/bin/bwrap'),4*1024**2))}
    boundary.context(context)
    result={'protocol':'stead.fixed-pure-eval-hosted-result/1','status':'fail',
            'classification':'isolated-fixed-ivory-composition-diagnostic','qualifies_phase':False,
            'native_application_executed':False,'identity':identity,'workflow_binding':binding,
            'controller_commit':args.controller,'run_id':run_id,'source_pins':source_map(hosted),
            'context':context,'error_class':'none','cleanup_error_class':'none',
            'cleanup':{'verified':False},'report_export':'absent'}
    # Source-bound static metadata plus the closed32KiB guardian envelope must
    # fit the report's fixed128KiB reserve before any executable is launched.
    require(len(canonical(result))+32768+16384 <= METADATA_RESERVE)
    process=None;service_started=False;setup_phase='admission'
    try:
        setup_guard();setup_phase='apparmor'
        result['apparmor_setup']=hosted.hosted_apparmor.prepare(hosted.regular_root)
        setup_phase='bwrap'
        result['bwrap_version']=subprocess.run(['/usr/bin/bwrap','--version'],check=True,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5,
            env={'PATH':'/usr/bin:/bin','LANG':'C'}).stdout.decode('ascii').strip()
        require(result['bwrap_version']=='bubblewrap 0.9.0')
        def setup_timeout(_signum,_frame):raise TimeoutError('Fixed pure setup deadline')
        old_alarm=signal.signal(signal.SIGALRM,setup_timeout)
        signal.setitimer(signal.ITIMER_REAL,max(0.001,SETUP_SECONDS-(time.monotonic()-started)))
        try:
            setup_phase='intake';result['intake']=intake.prepare(job,setup_guard)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_alarm)
        setup_phase='input'
        sources=job/'sources';sources.mkdir(mode=0o755);os.chmod(sources,0o755)
        for name,raw in files.items():
            require(re.fullmatch(r'[A-Za-z0-9_.\-/]+',name) and all(p not in ('','.','..') for p in name.split('/')))
            target=sources/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            for parent in target.parents:
                if parent==sources:break
                os.chmod(parent,0o755)
            write_new(target,raw,mode=0o444)
        for label in ('lease','input'):
            (job/label).mkdir(mode=0o550);os.chown(job/label,0,account.pw_gid);os.chmod(job/label,0o550)
        owner={'protocol':'stead.fixed-pure-eval-worker-input/1','host_uid':account.pw_uid,'host_gid':account.pw_gid,
               'outer_namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in boundary.NAMESPACES},
               'sources':context['sources'],'runtime':result['intake']['runtime']}
        for name,path in selected_sources.items():write_new(job/'input'/name,hosted.CONTROLLER_FILES[path],mode=0o440,gid=account.pw_gid)
        write_new(job/'input/owner.json',canonical(owner),mode=0o440,gid=account.pw_gid)
        os.chown(job,0,account.pw_gid);os.chmod(job,0o750);setup_guard()
        guardian_input={'protocol':'stead.fixed-pure-eval-guardian-input/1','boundary':context,
            'owner':owner,'identity':identity,'workflow_binding':binding,'controller_files':source_map(hosted),
            'outer_pid':outer_pid,'outer_start':outer_identity[1],'created_monotonic_ns':time.monotonic_ns()}
        write_new(job/'guardian.json',canonical(guardian_input))
        owner_sha=sha(canonical(owner));generation=1
        lease_publish(job,'caller',owner_sha,generation,account.pw_gid)
        lease_publish(job,'guardian',owner_sha,1,account.pw_gid)
        require(len(canonical(result))+32768 <= METADATA_RESERVE)
        setup_phase='launch';service_started=True
        process=hosted.spawn_owned(service_command(hosted,collection,job,context))
        setup_phase='execution';end=time.monotonic()+UNIT_WAIT_SECONDS
        while process.poll() is None:
            require(time.monotonic()<end);generation+=1
            lease_publish(job,'caller',owner_sha,generation,account.pw_gid);time.sleep(0.2)
        result['service_exit_code']=process.returncode
        setup_phase='result'
        result['guard']=read_json(boundary,job/'pure-guard.json',32768)
        complete_guard(result['guard'],allow_failure=True)
        require(process.returncode==(0 if result['guard']['status']=='pass' else 1))
        result['status']=result['guard']['status']
    except BaseException as error:
        result['error_class']=closed_error(error)
        try:result['setup_failure']=setup_failure_positions(hosted,intake,error,setup_phase)
        except BaseException:result['setup_failure']=None
    finally:
        if process is not None:
            try:process.stdin.close()
            except BaseException:result['cleanup_error_class']='caller-pipe-close'
        try:
            state=hosted.readback(context['unit'])
            if state.get('ActiveState') not in ('inactive','failed'):
                subprocess.run(['/usr/bin/systemctl','stop',context['unit']],check=True,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
                state=hosted.readback(context['unit'])
            cg=Path('/sys/fs/cgroup/system.slice')/context['unit']
            require(state.get('ActiveState') in ('inactive','failed') and
                    (not cg.exists() or 'populated 0' in (cg/'cgroup.events').read_text().splitlines()))
            result['cleanup']={'verified':True,'empty':True,'unit':context['unit'],
                               'active_state':state['ActiveState'],'service_started':service_started}
        except BaseException:result['cleanup_error_class']='service-cleanup'
        if process is not None:
            try:process.wait(timeout=5)
            except BaseException:
                result['cleanup_error_class']='caller-reap'
                try:process.kill();process.wait(timeout=5)
                except BaseException:pass
        if result['error_class']!='none' or result['cleanup_error_class']!='none' or not result['cleanup']['verified']:
            result['status']='fail'
        public=hosted.ROOT/'pure-evidence';public.mkdir(mode=0o755);os.chmod(public,0o755);hosted.regular_root(public)
        if job.is_dir() and (job/'pure-guard.json').is_file():
            result['guard']=read_json(boundary,job/'pure-guard.json',32768)
        artifact=None
        if (result['error_class']=='none' and result['cleanup_error_class']=='none'
                and result['cleanup'].get('verified') is True and result['cleanup'].get('empty') is True):
            try:
                artifact=checked_report(hosted,boundary,collection,codec,job,result['guard'])
                result['report_export']='collected';result['report_pin']=pin(artifact)
                require(len(canonical(result))<=METADATA_RESERVE
                        and len(canonical(result))+len(artifact)<=REPORT_LIMIT)
            except BaseException:
                artifact=None;result['status']='fail';result['report_export']='refused'
                result['report_error_class']='custody-schema-or-budget'
        if artifact is not None:write_new(public/'report.json',artifact,mode=0o644)
        require(len(canonical(result))<=METADATA_RESERVE)
        write_new(public/'owner-report.json',canonical(result),mode=0o644)
    return 0 if result['status']=='pass' else 1


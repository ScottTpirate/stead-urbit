"""Root-owned fixed saved8 adapter for the existing hosted native guardian.

No local entry, caller archive, live pier, supplied noun or candidate override.
The workflow must separately run the unchanged six resource failure controls.
The existing guardian runs its mandatory Doc isolation proof before this child.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import tarfile
import tempfile
import time

from . import evidence as E
from . import result as R

PROFILE = 'home-assets-saved8/1'
PREFIX = 'scripts/ci/home_asset_rehearsal/'
DATA = {
    'previous.tar': (1392640, R.PREVIOUS), 'target.tar': (1617920, R.NEXT),
    'seed-home.hoon': (607, 'd6d15bc9514001a2edcdcb67384881826215e7fd40c08465edc74962d8b70fdd'),
    'seed-lib.hoon': (15981, '4021487a4d7878461e02951a8e00ccd28b1b9eb2346ec3a09f596ca93bc131e4'),
    'a0-stead-codec.hoon': (9532, '56e3d574381bbf8cdf29ca192c70eff256009f89d782e3ffe859b19c1321cbd7'),
    'a0-stead-delivery.hoon': (556, '178cac634471554dae9928f8c38248751329314391061976a436a22a7075548d'),
    'a0-stead-team-client.hoon': (3355, '1c7d4abd0323c1020d99b7bd8109969cdc15423c3cd8b9fdc5a28bd9b074066d'),
    'a0-stead-local-tls.hoon': (586, '2e32b120e8d838eba65b67974abc1fe182fe8ce543ffc36715ce1f48a563511d'),
}
SEED = {'app/stead-home.hoon': 'seed-home.hoon', 'lib/stead-home-ui-seed.hoon': 'seed-lib.hoon'}
DRIVERS = {'lib/stead-codec.hoon': 'a0-stead-codec.hoon', 'lib/stead-delivery.hoon': 'a0-stead-delivery.hoon',
    'ted/stead-team-client.hoon': 'a0-stead-team-client.hoon', 'ted/stead-local-tls.hoon': 'a0-stead-local-tls.hoon'}
FROZEN = {
    PREFIX + '__init__.py': '012fb68d9afed4520e136077b0cc8124df015eb584ab421cf051d0d7c210bec4',
    PREFIX + 'worker.py': 'c357616483ea6fbbd041e0e2aa3ca0193c15de3b19d7c060068b566dc8321a95',
    PREFIX + 'runner.py': '49c299e1118a37707e4b509328875279d73d79745c5394b73df87e636d419e2e',
    PREFIX + 'evidence.py': '1515c00f1c8b6acde61e5e0f647a83f9e5cd78b11d157f46ec13db545c284175',
    PREFIX + 'capture.hoon': 'e6bad02fbecf2f73a7f3608eda8a0dad938dfe72af8d4909321c824148d277bc',
    'scripts/release_install.py': '30b2a651c3e7d124e7e5ef319f5581299d29427322e605f1ffca91e9015f5e80',
    'scripts/sdk_native/native.py': '3c12a59eafe9b165550d0bf469b359aaf3b3127ecf43f357cf561ce358ccde1c',
    'scripts/urbit/execution_policy.py': '8d52b799a3a7bff73f38e029b57fe0cfafd156b7c61184173860c21600ce41c0',
    'scripts/urbit/core_conn.py': '3a3fdbff9b01180f57e42ee4de56c9984a922bbc28a26a3361d12a50cf442494',
    'scripts/urbit/conn.py': 'd590a41033bbea62bad6f5dc63c16fdb16c61c906c773c8f3c9c316b69dd3454',
    'scripts/urbit/owned_child.py': 'a01fc92a0b5f000f5ddee505d475127681ac47ea9a7aa4d8b450594cd50ec229',
    'scripts/urbit/native_tls.py': '0c76e4fcbe37fceee823a5ba1bf3080a2523149996c8471a1afed0341b45ebc5',
    'scripts/urbit/team_conn.py': '1e77fc23760256c76402370f8ab0346c12d0f8d1bd44beb46cfdf1385ee7b858',
    'scripts/urbit/digests.py': '909b7c3a1d5672f73b449c00790e44eb8dd2906a8cabf9700c2d49ea9c47ae11',
    'scripts/ci/hosted_lease.py': 'a0da1a8138c0c9eb62a75c5b3032b00e7d2a8eb6a027e5c8c02ddb8daf6495f9',
    'scripts/ci/hosted_apparmor.py': '7f45ee3111d3739b9517a2f4c56813f1a11a36586ae29787e6cc741e9f7895bf',
    'specs/urbit/toolchain.lock.json': 'ae185adaec12b5aa0b2d48e2198ae65583902512ffd9d148706810c4819c650c',
}


def require(ok):
    if not ok:
        raise ValueError('Fixed saved8 hosted adapter refused')


def write_files(root, files):
    root.mkdir(mode=0o700)
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)


def archive(raw, name):
    require(name in ('previous', 'target') and (len(raw), E.sha(raw)) == DATA[name + '.tar'])
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as source:
        members = source.getmembers()
        require(len(members) == (124 if name == 'previous' else 126))
        for member in members:
            require(member.isfile() and member.name.startswith('stead-release/') and 0 < member.size <= 524288
                    and re.fullmatch(r'[A-Za-z0-9_./-]+', member.name)
                    and all(p not in ('', '.', '..') for p in member.name.split('/')))
            relative = member.name[len('stead-release/'):]
            require(relative not in result)
            result[relative] = source.extractfile(member).read()
            require(len(result[relative]) == member.size)
    manifest = json.loads(result['manifest.json'], object_pairs_hook=E.unique)
    require(manifest['source_commit'] == (R.BASE if name == 'previous' else R.TARGET)
            and manifest['role'] == 'home' and manifest['agents'] == ['stead-home']
            and type(manifest['saved_state_version']) is int and manifest['saved_state_version'] == 9)
    require(manifest['compatibility']['kernel_commit'] == R.KERNEL
            and manifest['compatibility']['runtime_binary_sha256'] == R.RUNTIME)
    R.exact(manifest['files'], {path: {'bytes': len(data), 'sha256': E.sha(data)}
        for path, data in result.items() if path != 'manifest.json'})
    desk = {path[5:]: E.sha(data) for path, data in result.items() if path.startswith('desk/')}
    require(len(desk) == (116 if name == 'previous' else 118))
    frontend = json.loads(result['source/frontend.json'], object_pairs_hook=E.unique)
    routes = [{'route': row['route'], 'sha256': row['sha256'], 'bytes': row['bytes']}
              for row in frontend['routes'] if row['route'].startswith('/stead/')]
    require(0 < len(routes) <= 32 and any(row['route'] == '/stead/' for row in routes))
    return result, manifest, desk, routes


def intake(hosted, job, args, account, binding, run_id, pins):
    """Only captured controller blobs and the two fixed public archives enter."""
    controller = hosted.CONTROLLER_FILES
    require(type(controller) is dict and len(controller) <= 512)
    for path, digest in FROZEN.items():
        require(type(controller.get(path)) is bytes and E.sha(controller[path]) == digest)
    data = {}
    for name, expected in DATA.items():
        raw = controller[PREFIX + 'data/' + name]
        require(type(raw) is bytes and (len(raw), E.sha(raw)) == expected)
        data[name] = raw
    old_files, old_manifest, old, old_routes = archive(data['previous.tar'], 'previous')
    new_files, new_manifest, new, new_routes = archive(data['target.tar'], 'target')
    for field in ('agents', 'role', 'compatibility', 'saved_state_version', 'toolchain_sha256',
                  'contract_sha256', 'packager_sha256', 'shared_packager_sha256', 'qualification'):
        R.exact(old_manifest[field], new_manifest[field])
    changed = {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}
    inventory = 'web/stead/inventory.hoon'
    require(inventory in changed and inventory in old.keys() & new.keys() and changed - {inventory}
            and all(re.fullmatch(r'web/stead/asset-[0-9a-f]{64}\.stead-asset', name) for name in changed - {inventory}))
    delta = {'removed': sorted(changed - new.keys()), 'updated': sorted(changed & new.keys())}
    sources = {'ci': {'home_asset_rehearsal/' + name: controller[PREFIX + name]
                for name in ('runner.py', 'evidence.py', 'capture.hoon')},
        'code': {'release_install.py': controller['scripts/release_install.py']},
        'helpers': {name + '.py': controller['scripts/urbit/' + name + '.py']
            for name in ('execution_policy', 'core_conn', 'conn', 'owned_child', 'native_tls', 'team_conn')},
        'support': {'native.py': controller['scripts/sdk_native/native.py']}}
    guardian = {name: controller['scripts/ci/' + name] for name in ('hosted.py', 'hosted_lease.py', 'hosted_apparmor.py')}
    guardian.update({name: controller[PREFIX + name] for name in ('worker.py', 'result.py')})
    guardian['digests.py'] = controller['scripts/urbit/digests.py']
    require(guardian['hosted.py'] == Path(hosted.__file__).read_bytes())
    views = job / 'views'; views.mkdir(mode=0o700)
    for name, files in sources.items():
        write_files(views / name, files)
    write_files(views / 'guardian', guardian)
    package = job / 'rehearsal'; package.mkdir(mode=0o700)
    write_files(package / 'previous', old_files); write_files(package / 'target', new_files)
    seed = {path: data[name] for path, name in SEED.items()}
    drivers = {path: data[name] for path, name in DRIVERS.items()}
    drivers['gen/home-ui-capture.hoon'] = controller[PREFIX + 'capture.hoon']
    write_files(package / 'seed', seed); write_files(package / 'drivers', drivers)
    for name in ('previous.tar', 'target.tar'):
        with (package / name).open('xb') as stream:
            stream.write(data[name])
    require(pins['runtime']['binary_sha256'] == R.RUNTIME and pins['kernel']['commit'] == R.KERNEL)
    hashes = lambda files: {name: E.sha(raw) for name, raw in files.items()}
    seed_desk = old | hashes(seed)
    inputs = {'protocol': 'stead.saved8-hosted-inputs/1', 'profile': PROFILE, 'run_id': run_id,
        'controller_commit': args.controller, 'candidate_commit': R.BASE, 'backend_commit': R.BASE,
        'target_commit': R.TARGET, 'workflow_binding': binding, 'controller_files': hosted.local.hashes(controller),
        'host_namespaces': {name: os.readlink('/proc/self/ns/' + name) for name in ('net', 'pid', 'mnt', 'user')},
        'owner_uid': account.pw_uid, 'owner_gid': account.pw_gid,
        'source_files': {'/' + name: hashes(files) for name, files in sources.items()}, 'guardian_files': hashes(guardian),
        'driver_files': hashes(drivers), 'seed_files': hashes(seed), 'runtime_sha256': R.RUNTIME,
        'pill_sha256': pins['boot_artifact']['sha256'], 'kernel_commit': R.KERNEL,
        'kernel_tree_sha256': pins['kernel']['source_tree_sha256'],
        'toolchain_sha256': FROZEN['specs/urbit/toolchain.lock.json'],
        'archives': {name: {'bytes': len(data[name + '.tar']), 'sha256': E.sha(data[name + '.tar'])} for name in ('previous', 'target')},
        'assets': {'previous': old_routes, 'target': new_routes, 'delta': delta},
        'desk_hashes': {stage: E.sha(E.canonical(seed_desk if stage == 'seed8' else new if stage == 'assets-loaded' else old)) for stage in E.STAGES}}
    require(len(E.canonical(inputs)) < 1048576)
    context = {'protocol': 'stead.saved8-rehearsal-context/1',
        **{k: inputs[k] for k in ('run_id', 'controller_commit', 'host_namespaces', 'driver_files', 'source_files',
                                'runtime_sha256', 'pill_sha256', 'kernel_commit')},
        'inputs_sha256': E.sha(E.canonical(inputs))}
    return inputs, context


def command(hosted, job, context):
    """Only this owner-created tag selects this exact mount and child command."""
    require(context.get('fixed_profile') == PROFILE and not context.get('control_case'))
    pins, views = context['pins'], job / 'views'
    argv = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--uid', '0', '--gid', '0',
        '--cap-add', 'CAP_NET_ADMIN', '--cap-add', 'CAP_SETPCAP', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        argv += ['--symlink', os.readlink(path), str(path)] if path.is_symlink() else ['--ro-bind', str(path), str(path)]
    argv += ['--proc', '/proc', '--dev', '/dev', '--dir', '/etc', '--size', str(hosted.local.TEMP_BYTES),
        '--tmpfs', '/tmp', '--size', str(hosted.local.STATE_BYTES), '--tmpfs', '/state']
    mounts = [(views / name, '/' + name) for name in ('ci', 'code', 'helpers', 'support', 'guardian')]
    mounts += [(job / 'rehearsal', '/rehearsal'), (job / 'inputs.json', '/inputs.json'),
        (job / 'control', '/execution'), (job / 'doc-proof.json', '/doc-proof.json'),
        (job / 'controller/specs/urbit/toolchain.lock.json', '/toolchain.json'),
        (hosted.ROOT / '.runtime' / pins['runtime']['binary'], '/runtime/' + pins['runtime']['binary']),
        (hosted.ROOT / '.runtime/downloads' / pins['boot_artifact']['archive'], '/runtime/downloads/' + pins['boot_artifact']['archive']),
        (hosted.ROOT / '.runtime' / pins['kernel']['directory'], '/kernel')]
    for source, target in mounts:
        argv += ['--ro-bind', str(source), target]
    return [*argv, '--chdir', '/state', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
        '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'TERM', 'dumb',
        '--setenv', 'STEAD_EXECUTION_ID', context['run_id'], '--setenv', 'STEAD_RELEASE_INSTALL_CHILD', '1',
        '--', '/usr/bin/python3', '-I', '-B', '/guardian/worker.py']


def exclusive(path, raw, created):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    created.append(path)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), 0o644); os.fsync(stream.fileno())


def sync_directory(root):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(root, owner, inputs, artifacts):
    """Receipt last; a failed later write removes only this attempt's files.

    All originals are validated before publication. A process/power loss before
    the receipt can leave unqualified files, never a successful receipt. No
    existing file is overwritten, even when attempting a failure receipt.
    """
    created = []
    try:
        files = {}
        if owner['status'] == 'pass':
            require(not owner['errors'] and owner['cleanup']['verified'] is True)
            require(type(artifacts) is dict and set(artifacts) == set(R.NAMES))
            require(all(type(raw) is bytes and 0 < len(raw) <=
                (E.MAX_CAPTURE if name.endswith('.jam') else R.MAX_DESCRIPTOR)
                for name, raw in artifacts.items()))
            require(sum(len(raw) for name, raw in artifacts.items() if name.endswith('.jam')) <= 5 * E.MAX_CAPTURE)
            files.update({name: artifacts[name] for name in R.NAMES})
            owner['artifacts'] = {name: {'bytes': len(raw), 'sha256': E.sha(raw)} for name, raw in files.items()}
        else:
            require(artifacts == {} and owner['artifacts'] == {})
        if inputs is not None:
            files['inputs.json'] = E.canonical(inputs) + b'\n'
            require(len(files['inputs.json']) <= 1048576)
        if owner.get('report') is not None:
            files['report.json'] = E.canonical(owner['report']) + b'\n'
            require(len(files['report.json']) <= R.MAX_FRAME)
        receipt = E.canonical(owner) + b'\n'
        require(len(receipt) <= R.MAX_FRAME)
        require(not any((root / name).exists() or (root / name).is_symlink()
                        for name in (*files, 'owner-report.json')))
        for name, raw in files.items():
            exclusive(root / name, raw, created)
        sync_directory(root)
        exclusive(root / 'owner-report.json', receipt, created)
        sync_directory(root)
    except BaseException as error:
        owner['status'], owner['artifacts'] = 'fail', {}
        owner['errors'].append({'phase': 'artifact-export', 'error_class': type(error).__name__})
        # The fixed public directory is root-owned. Never delete a pre-existing
        # file: only paths successfully opened O_EXCL by this invocation.
        for path in reversed(created):
            path.unlink()
        sync_directory(root)
        # Keep the original initiating failures. Avoid duplicating a large
        # provisional report in a failure receipt after an export error.
        failed = {key: value for key, value in owner.items() if key != 'report'}
        raw = E.canonical(failed) + b'\n'
        require(len(raw) <= R.MAX_FRAME)
        exclusive(root / 'owner-report.json', raw, [])
        sync_directory(root)
    return owner['status']


def collected(hosted, job, owner, inputs, rehearsal, run_id, controller):
    """No export before source-bound frame, EOF/reap and whole-unit cleanup."""
    require(job is not None and inputs is not None and rehearsal is not None and owner['cleanup']['verified'])
    guard = hosted.execution_policy.read_json(job / 'guard.json', maximum=1048576)
    owner['guard'] = guard
    hosted.require_collected_child(guard)
    require(guard['run_id'] == run_id and E.canonical(guard['policy']) == E.canonical(hosted.POLICY))
    from doc_worker_proof import verify_admission
    verify_admission(guard['doc_worker_admission'], inputs, run_id)
    with (job / 'console.private.log').open('rb') as stream:
        raw = stream.read(R.MAX_FRAME + 1)
    expected = {'run_id': run_id, 'controller_commit': controller, 'inputs_sha256': E.sha(E.canonical(inputs)),
        'worker_sha256': inputs['guardian_files']['worker.py'],
        'guardian_sources_sha256': E.sha(E.canonical(inputs['guardian_files']))}
    value, proposed = R.decode(raw, expected, context_sha=E.sha(E.canonical(rehearsal)),
        desk_hashes=inputs['desk_hashes'], assets=inputs['assets'])
    owner['worker'] = {k: value[k] for k in ('status', 'error_class', 'cleanup')}
    owner['worker_frame'] = {'bytes': len(raw), 'sha256': E.sha(raw)}
    owner['report'] = value['report']
    require(not owner['errors'] and guard['status'] == 'pass' and guard['exit_code'] == 0
        and value['status'] == 'pass' and value['cleanup'] is True)
    return proposed


def outer(hosted, args, identity, binding):
    require(os.geteuid() == 0 and args.mode == 'home-assets-saved8' and args.control is None
            and args.candidate == args.controller)
    run_id = os.urandom(16).hex()
    username, unit = 'steadci-' + run_id[:12], 'stead-hosted-' + run_id + '.service'
    owner = {'protocol': 'stead.saved8-hosted-owner/1', 'status': 'fail', 'profile': PROFILE,
        'classification': 'disposable-synthetic-saved8-only', 'qualifies_phase': False,
        'controller_commit': args.controller, 'backend_commit': R.BASE, 'target_commit': R.TARGET,
        'run_id': run_id, 'identity': identity, 'workflow_binding': binding, 'policy': hosted.POLICY,
        'errors': [], 'cleanup': {'verified': False}, 'worker': None, 'artifacts': {}}
    job = process = account = inputs = rehearsal = None
    phase = 'intake'
    try:
        import toolchain
        toolchain.CACHE = hosted.ROOT / '.runtime'
        pins = toolchain.verify()
        cpus = sorted(os.sched_getaffinity(0))[:2]
        require(len(cpus) == 2)
        owner['apparmor_setup'] = hosted.hosted_apparmor.prepare(hosted.regular_root)
        subprocess.run(['/usr/sbin/useradd', '--system', '--user-group', '--no-create-home', '--shell',
            '/usr/sbin/nologin', username], check=True, capture_output=True, timeout=10)
        account = pwd.getpwnam(username)
        owner['unrelated_profile_control'] = hosted.hosted_apparmor.unrelated(account)
        owner['unrelated_profile_observation'] = hosted.hosted_apparmor.verify_probe(
            owner['unrelated_profile_control'], account.pw_uid, account.pw_gid)
        job = Path(tempfile.mkdtemp(prefix='stead-hosted-', dir='/var/lib'))
        os.chown(job, 0, account.pw_gid); os.chmod(job, 0o750)
        hosted.local.materialize(hosted.CONTROLLER_FILES, job / 'controller')
        inputs, rehearsal = intake(hosted, job, args, account, binding, run_id, pins)
        # Worker admission pins compact canonical bytes, including the final LF.
        # Reuse the guardian's atomic canonical writer, not write_json's spaced form.
        hosted.write(job / 'inputs.json', inputs, shared=True, gid=account.pw_gid)
        (job / 'control').mkdir()
        context = {'run_id': run_id, 'unit': unit, 'uid': account.pw_uid, 'gid': account.pw_gid,
            'cpus': cpus, 'pins': pins, 'guard_sha256': E.sha(Path(hosted.__file__).read_bytes()),
            'control_case': None, 'fixed_profile': PROFILE}
        hosted.write(job / 'context.json', context)
        hosted.write(job / 'control/home-asset-rehearsal.json', rehearsal, shared=True, gid=account.pw_gid)
        hosted.share_tree(job, account.pw_gid)
        hosted.share_tree(hosted.ROOT / '.runtime', account.pw_gid)
        phase = 'owned-service'
        process = hosted.spawn_owned(hosted.service_command(job, context), diagnostics=job / 'caller-stderr.private.log')
        deadline = time.monotonic() + 7230
        while process.poll() is None:
            require(time.monotonic() < deadline)
            time.sleep(.5)
        require(process.returncode == 0)
    except BaseException as error:
        owner['errors'].append({'phase': phase, 'error_class': type(error).__name__})
    finally:
        # Each cleanup step runs even if the lifetime-pipe close raises EPIPE.
        if process is not None:
            try:
                process.stdin.close()
            except BaseException as error:
                owner['errors'].append({'phase': 'lifetime-close', 'error_class': type(error).__name__})
        try:
            state = hosted.readback(unit)
            if state.get('ActiveState') not in ('inactive', 'failed'):
                subprocess.run(['/usr/bin/systemctl', 'stop', unit], check=True, capture_output=True, timeout=20)
                state = hosted.readback(unit)
            group = Path('/sys/fs/cgroup/system.slice') / unit
            require(state.get('ActiveState') in ('inactive', 'failed')
                and (not group.exists() or 'populated 0' in (group / 'cgroup.events').read_text().splitlines()))
            owner['cleanup'] = {'verified': True, 'unit': unit, 'empty': True, 'active_state': state['ActiveState']}
        except BaseException as error:
            owner['errors'].append({'phase': 'unit-cleanup', 'error_class': type(error).__name__})
        if process is not None:
            try:
                process.wait(timeout=5)
                process.stead_diagnostic_thread.join(timeout=2)
                require(not process.stead_diagnostic_thread.is_alive()
                    and not process.stead_diagnostics['overflow'] and not process.stead_diagnostics['error'])
            except BaseException as error:
                owner['errors'].append({'phase': 'caller-reap', 'error_class': type(error).__name__})
                try:
                    if process.poll() is None:
                        process.kill(); process.wait(timeout=5)
                except BaseException as cleanup_error:
                    owner['errors'].append({'phase': 'caller-kill', 'error_class': type(cleanup_error).__name__})
        if account is not None:
            try:
                subprocess.run(['/usr/sbin/userdel', username], check=True, capture_output=True, timeout=10)
            except BaseException as error:
                owner['errors'].append({'phase': 'account-cleanup', 'error_class': type(error).__name__})
    artifacts = {}
    try:
        artifacts = collected(hosted, job, owner, inputs, rehearsal, run_id, args.controller)
        owner['status'] = 'pass'
    except BaseException as error:
        owner['errors'].append({'phase': 'final-evidence', 'error_class': type(error).__name__})
        owner['status'] = 'fail'
    public = hosted.ROOT / 'home-asset-evidence'
    public.mkdir(mode=0o700, exist_ok=True); hosted.regular_root(public)
    os.chmod(public, 0o755)
    publish(public, owner, inputs, artifacts)
    print(json.dumps({'status': owner['status'], 'evidence': 'home-asset-evidence/owner-report.json'}), flush=True)
    return 0 if owner['status'] == 'pass' else 1

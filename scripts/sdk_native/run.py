#!/usr/bin/env python3
"""Run the independently packaged native SDK in two disposable fake namespaces."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'scripts/urbit')]
import execution_policy
import prepare_sdk_consumer
import toolchain
from digests import sha, source_inventory, tree_sha

CONSUMER_RUNNER = ('bridge.py', 'native.py', 'consumer.py', 'qualify.hoon', 'invoke.hoon', 'private-import.hoon', 'public-import.hoon')
CONSUMER_HELPERS = ('core_conn.py', 'conn.py', 'owned_child.py')


def system_mounts():
    command = ['bwrap', '--unshare-all', '--new-session', '--die-with-parent', '--uid', '0', '--gid', '0',
               '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr']
    for name in ('bin', 'sbin', 'lib', 'lib64'):
        path = Path('/') / name
        if path.is_symlink():
            command += ['--symlink', os.readlink(path), str(path)]
        elif path.exists():
            command += ['--ro-bind', str(path), str(path)]
    return command + ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/etc']


def run(archive):
    if subprocess.check_output(['git', 'remote', 'get-url', '--push', 'origin'], cwd=ROOT, text=True).strip() != 'https://github.com/ScottTpirate/stead-urbit.git':
        raise ValueError('Derivative origin required')
    lock = toolchain.verify()
    stamp = time.strftime('%Y%m%d-%H%M%S', time.gmtime())
    prepared = '.runtime/sdk-builder-native-' + stamp
    receipt = prepare_sdk_consumer.prepare(ROOT, archive, prepared)
    state = ROOT / '.runtime' / ('sdk-consumer-' + stamp)
    state.mkdir(mode=0o700)
    (state / 'consumer').mkdir(mode=0o700)
    runner = state / 'runner'
    runner.mkdir(mode=0o700)
    for name in CONSUMER_RUNNER:
        shutil.copyfile(ROOT / 'scripts/sdk_native' / name, runner / name)
    for name in CONSUMER_HELPERS:
        shutil.copyfile(ROOT / 'scripts/urbit' / name, runner / name)
    expected_runner = {name: sha(ROOT / 'scripts/sdk_native' / name) for name in CONSUMER_RUNNER}
    expected_runner.update({name: sha(ROOT / 'scripts/urbit' / name) for name in CONSUMER_HELPERS})
    if source_inventory(runner) != expected_runner:
        raise ValueError('Copied consumer runner differs from the reviewed source')
    expected_public = {name.removeprefix('sdk/'): row['sha256'] for name, row in receipt['files'].items() if name.startswith('sdk/')}
    if source_inventory(ROOT / prepared / 'sdk') != expected_public:
        raise ValueError('Prepared public bytes differ from the verified package')
    before = {name: source_inventory(ROOT / name) for name in ('scripts/sdk_native', 'scripts/urbit', 'native/core/desk')}
    context = {'profile': 'independent-public-sdk-two-fresh-fakes',
               'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'dirty_paths': subprocess.check_output(['git', 'status', '--porcelain', '--', 'scripts/sdk_native', 'scripts/urbit', 'native/core/desk'], cwd=ROOT, text=True).splitlines(),
               'sources': before, 'toolchain_sha256': sha(toolchain.LOCK_PATH),
               'public_inputs': receipt, 'public': expected_public, 'runner': expected_runner,
               'host_namespaces': {name: os.readlink('/proc/self/ns/' + name) for name in ('net', 'pid', 'mnt', 'user')}}
    committed = {}
    listing = subprocess.check_output(['git', 'ls-tree', '-r', '-z', context['source_commit'], '--', *before], cwd=ROOT)
    for entry in listing.split(b'\0'):
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_path.decode()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('SDK qualification source is not a regular Git blob')
        raw = (ROOT / name).read_bytes()
        committed[name] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == oid
    actual_names = {prefix + '/' + name for prefix, files in before.items() for name in files}
    context['committed_bytes_verified'] = not context['dirty_paths'] and set(committed) == actual_names and all(committed.values())
    for name, digest in expected_runner.items():
        prefix = 'scripts/sdk_native' if name in CONSUMER_RUNNER else 'scripts/urbit'
        if before[prefix][name] != digest:
            raise ValueError('Runner changed before source capture')

    def command(control, run_id):
        execution_policy.write_json(control / 'sdk-context.json', context)
        command = system_mounts()
        for source, target in ((ROOT / 'scripts/sdk_native', '/controller'),
                               (ROOT / 'scripts/urbit', '/helpers'),
                               (ROOT / 'native/core/desk', '/native'),
                               (ROOT / prepared / 'sdk', '/public'),
                               (runner, '/runner'),
                               (toolchain.LOCK_PATH, '/toolchain.json'),
                               (ROOT / '.runtime/bin', '/runtime/bin'),
                               (ROOT / '.runtime/downloads', '/runtime/downloads'),
                               (ROOT / '.runtime' / lock['kernel']['directory'], '/kernel'),
                               (control, '/execution')):
            command += ['--ro-bind', str(source), target]
        command += ['--bind', str(state), '/state', '--chdir', '/state', '--clearenv',
                    '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'LANG', 'C.UTF-8',
                    '--setenv', 'STEAD_EXECUTION_ID', run_id, '--setenv', 'STEAD_CONFIGURED', '1',
                    '--', '/usr/bin/python3', '-B', '/controller/controller.py']
        return command

    guard = execution_policy.run_guarded(command, root=ROOT, label='sdk-consumer', timeout=3600)
    unchanged = (before == {name: source_inventory(ROOT / name) for name in before}
        and source_inventory(runner) == expected_runner and source_inventory(ROOT / prepared / 'sdk') == expected_public)
    result = {'classification': 'local-real-native-independent-sdk', 'guard': guard,
              'sources_unchanged': unchanged, 'evidence': str(state / 'report.json')}
    execution_policy.write_json(state / 'host-report.json', result)
    print(json.dumps({'guard_status': guard['status'], 'sources_unchanged': unchanged,
                      'evidence': str(state / 'report.json'), 'guard_report': guard['run_directory'] + '/report.json'}), flush=True)
    if guard['status'] != 'completed' or not unchanged:
        raise RuntimeError('Independent SDK qualification did not complete cleanly')
    report = execution_policy.read_json(state / 'report.json', 4 * 1024 * 1024)
    if report['status'] != 'pass':
        raise RuntimeError('Independent SDK native checks failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, help='Verified checkout-relative public SDK archive')
    run(parser.parse_args().archive)

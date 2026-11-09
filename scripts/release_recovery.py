#!/usr/bin/env python3
"""Verify a stopped synthetic Home copy and optionally boot a fresh clone offline."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

import package_release as release
import release_install as install

ROOT = release.ROOT
execution_policy = install.execution_policy
INSTALL_CLASS = 'local-native-clean-fake-desk-install'
COPY_CLASS = 'local-synthetic-stopped-pier-file-round-trip'
COPY_MARKER = {'format': 1, 'purpose': 'offline-synthetic-file-round-trip-never-boot'}
CHECKS = [
    *install.PREINSTALL_CHECKS,
    'base-has-no-stead-source',
    'selected-role-live-on-release-desk',
    'owner-local-role-configuration',
    'packaged-native-https-routes-and-assets',
    'explicit-stop-observed',
    'supported-reload-observed',
    'reload-blocks-http-until-owner-bootstrap',
    'reload-changes-owner-incarnation',
    'packaged-native-https-restored-after-bootstrap',
    'package-unchanged-after-load',
]


def read(path, limit):
    return release.read_bounded(ROOT, path.relative_to(ROOT), limit)


def pinned_json(path, expected, limit):
    raw = read(path, limit)
    if not re.fullmatch(r'[0-9a-f]{64}', expected) or release.digest(raw) != expected:
        raise ValueError('Trusted receipt SHA-256 differs: ' + path.name)
    return json.loads(raw, object_pairs_hook=release.unique)


def assert_stopped(pier, run_id):
    install.retired_checkpoint_scope(run_id)
    with execution_policy.directory_fd(pier) as descriptor:
        if '.vere.lock' in os.listdir(descriptor):
            raise ValueError('Synthetic pier still has a runtime ownership lock')


def desk_inventory(manifest):
    return {name.removeprefix('desk/'): pin['sha256'] for name, pin in manifest['files'].items()
            if name.startswith('desk/')}


def admitted_pier(prior_name, archive_sha, manifest, report_sha, guard_sha):
    if not re.fullmatch(r'\.runtime/release-install-[a-z0-9_]+', prior_name):
        raise ValueError('A fresh owned release-install run is required')
    prior = ROOT / prior_name
    with execution_policy.directory_fd(prior) as descriptor:
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Release run is not private and owned')
    marker = execution_policy.read_json(prior / '.stead-disposable.json')
    if marker != {'format': 1, 'purpose': 'fresh-offline-release-install-only'}:
        raise ValueError('Release run is not a disposable installation')

    report_path = prior / 'work/report.json'
    report = pinned_json(report_path, report_sha, 4 * 1024 * 1024)
    host = execution_policy.read_json(prior / 'host-report.json')
    if (host.get('evidence') != str(report_path) or host.get('source_unchanged') is not True
            or host.get('guard_status') != 'completed'
            or any(record.get('classification') != INSTALL_CLASS
                   or record.get('boot_mode') != 'fresh-fake'
                   or record.get('artifact_sha256') != archive_sha for record in (host, report))
            or report.get('source_commit') != manifest['source_commit']
            or report.get('status') != 'pass' or report.get('role') != 'home'
            or report.get('configured_home') is not True or report.get('boot', {}).get('identity') != '~zod'
            or report.get('checks') != [{'name': name, 'passed': True} for name in CHECKS]
            or report.get('cleanup') != install.CLEAN_STOP):
        raise ValueError('Release evidence does not describe a clean, configured fresh Home')

    guard_path = Path(host.get('guard_report', ''))
    if (guard_path.parent.parent != ROOT / '.runtime/execution-runs'
            or not re.fullmatch(r'release-install-[a-z0-9_]+', guard_path.parent.name)
            or guard_path.name != 'report.json'):
        raise ValueError('Release guard path binding differs')
    guard = pinned_json(guard_path, guard_sha, 8 * 1024 * 1024)
    run_id = guard.get('run_id', '')
    control = guard_path.parent / 'control'
    lease = execution_policy.read_json(control / 'lease.json')
    context = execution_policy.read_json(control / 'release-context.json', 1024 * 1024)
    if (not re.fullmatch(r'[0-9a-f]{32}', run_id) or guard.get('scope') != 'stead-native-' + run_id + '.scope'
            or guard.get('label') != 'release-install' or guard.get('run_directory') != str(guard_path.parent)
            or guard.get('launched') is not True or guard.get('status') != 'completed' or guard.get('exit_code') != 0
            or lease.get('state') != 'stopped' or lease.get('run_id') != run_id
            or lease.get('guard_sha256') != guard.get('guard_sha256')
            or context.get('artifact_sha256') != archive_sha
            or context.get('verifier_source_commit') != report.get('verifier_source_commit')):
        raise ValueError('Release guard, stopped lease or source binding differs')

    toolchain_path = ROOT / 'specs/urbit/toolchain.lock.json'
    lock_raw = read(toolchain_path, 64 * 1024)
    if release.digest(lock_raw) != manifest['toolchain_sha256']:
        raise ValueError('Synthetic pier toolchain differs from the verified package')
    argv = guard.get('argv', [])
    if 'bwrap' not in argv or argv[argv.index('bwrap'):] != install.sandbox_command(
            prior, control, run_id, json.loads(lock_raw), toolchain_path):
        raise ValueError('Release run did not use the isolated install workspace')

    pier = prior / 'work/zod'
    assert_stopped(pier, run_id)
    expected = desk_inventory(manifest)
    if report.get('installed_files') != expected or install.inventory(pier / install.DESK) != expected:
        raise ValueError('Stopped Home desk differs from the verified package')
    return pier, run_id, report


def copy_round_trip(source, destination, run_id):
    before = install.checkpoint_tree(source, installed=True)
    backup, restored = destination / 'backup', destination / 'restored'
    copied = install.checkpoint_tree(source, backup, installed=True)
    assert_stopped(source, run_id)
    if copied != before:
        raise ValueError('Backup differs from the original pier')
    restored_copy = install.checkpoint_tree(backup, restored, installed=True)
    if (restored_copy != before or install.checkpoint_tree(backup, installed=True) != before
            or install.checkpoint_tree(restored, installed=True) != before):
        raise ValueError('Backup or restored pier fingerprint differs')
    if install.checkpoint_tree(source, installed=True) != before:
        raise ValueError('Original pier changed during rehearsal')
    assert_stopped(source, run_id)
    return before


def rehearse(prior, archive, archive_sha, target_path, report_sha, guard_sha):
    if os.getuid() == 0:
        raise ValueError('A nonroot local caller is required')
    if release.git(ROOT, 'remote', 'get-url', '--push', 'origin').decode().strip() != 'https://github.com/ScottTpirate/stead-urbit.git':
        raise ValueError('Derivative origin required')
    raw = release.read_bounded(ROOT, archive, release.MAX_ARCHIVE)
    target = json.loads(release.read_bounded(ROOT, target_path, 8192), object_pairs_hook=release.unique)
    manifest = release.verify_bytes(raw, expected_sha256=archive_sha, target=target)
    if manifest['role'] != 'home':
        raise ValueError('This rehearsal is restricted to a verified Home package')
    with execution_policy.HeavyRunLock(ROOT / '.runtime/native-execution.lock'):
        pier, run_id, _ = admitted_pier(prior, archive_sha, manifest, report_sha, guard_sha)
        destination = Path(tempfile.mkdtemp(prefix='release-recovery-', dir=ROOT / '.runtime'))
        execution_policy.write_json(destination / '.stead-disposable.json', COPY_MARKER)
        result = {'status': 'failed', 'classification': COPY_CLASS,
                  'qualifies_phase': False, 'native_execution': False, 'application_restore_verified': False,
                  'artifact_sha256': archive_sha, 'install_report_sha256': report_sha,
                  'guard_report_sha256': guard_sha, 'source_commit': manifest['source_commit']}
        report_path = destination / 'report.json'
        execution_policy.write_json(report_path, result)
        result['checkpoint'] = copy_round_trip(pier, destination, run_id)
        result['status'] = 'pass'
        execution_policy.write_json(report_path, result)
        return report_path, result


def retained_trees(original, copies, checkpoint, run_id):
    assert_stopped(original, run_id)
    for path in (original, copies / 'backup', copies / 'restored'):
        if install.checkpoint_tree(path, installed=True) != checkpoint:
            raise ValueError('Retained recovery tree fingerprint differs: ' + path.name)
    assert_stopped(original, run_id)


def restore_checkpoint(state, manifest, original, copies, receipt_sha, archive_sha, report_sha, guard_sha):
    if not re.fullmatch(r'\.runtime/release-recovery-[a-z0-9_]+', copies):
        raise ValueError('An exact offline copy rehearsal directory is required')
    copies = ROOT / copies
    with execution_policy.directory_fd(copies) as descriptor:
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Copy rehearsal is not private and owned')
    if execution_policy.read_json(copies / '.stead-disposable.json') != COPY_MARKER:
        raise ValueError('Offline copy rehearsal marker differs')
    receipt = pinned_json(copies / 'report.json', receipt_sha, 8192)
    checkpoint = receipt.get('checkpoint')
    expected = {'status': 'pass', 'classification': COPY_CLASS, 'qualifies_phase': False,
                'native_execution': False, 'application_restore_verified': False,
                'artifact_sha256': archive_sha, 'install_report_sha256': report_sha,
                'guard_report_sha256': guard_sha, 'source_commit': manifest['source_commit'], 'checkpoint': checkpoint}
    if receipt != expected or not isinstance(checkpoint, dict):
        raise ValueError('Offline copy receipt does not bind the verified installation')

    pier, run_id, installed = admitted_pier(original, archive_sha, manifest, report_sha, guard_sha)
    incarnations = [installed.get('bootstrap_' + stage + '_reload', {}).get('incarnation', '')
                    for stage in ('before', 'after')]
    drivers = installed.get('test_driver_files')
    if (any(not re.fullmatch(r'[0-9a-f]{64}', value) for value in incarnations)
            or incarnations[0] == incarnations[1] or drivers != install.inventory(state / 'controller/drivers')):
        raise ValueError('Prior bootstrap or restored test driver binding differs')
    retained_trees(pier, copies, checkpoint, run_id)
    clone = state / 'work/zod'
    if (install.checkpoint_tree(copies / 'restored', clone, installed=True) != checkpoint
            or install.stopped_home_checkpoint(clone, installed['installed_files']) != checkpoint):
        raise ValueError('New boot clone differs from the verified restored copy')
    assert_stopped(pier, run_id)
    evidence = {'artifact_sha256': archive_sha, 'copy_report_sha256': receipt_sha,
                'install_report_sha256': report_sha, 'guard_report_sha256': guard_sha,
                'prior_incarnations': incarnations, 'test_drivers': drivers, 'pier': checkpoint}
    return evidence, (pier, copies, checkpoint, run_id)


def asset_upgrade_plan(source, target, source_sha, target_sha, saved_sha):
    pinned = ('agents', 'role', 'compatibility', 'saved_state_version', 'toolchain_sha256', 'contract_sha256')
    if (any(source[key] != target[key] for key in pinned) or source['role'] != 'home'
            or source['saved_state_version'] != 3 or source_sha == target_sha
            or source['source_commit'] == target['source_commit'] or source['frontend_sha256'] == target['frontend_sha256']
            or not re.fullmatch(r'[0-9a-f]{64}', saved_sha)):
        raise ValueError('Asset upgrade requires distinct compatible Home packages and reviewed v3 state')
    previous = desk_inventory(source)
    install.asset_delta(previous, desk_inventory(target))
    return {'source_artifact_sha256': source_sha, 'source_commit': source['source_commit'],
            'source_desk': previous, 'saved_home_sha256': saved_sha}


def boot_recovery(prior, archive, archive_sha, target, report_sha, guard_sha, copies, receipt_sha, *, upgrade=None):
    retained = None
    next_archive, next_sha, next_target = (archive, archive_sha, target) if upgrade is None else upgrade[:3]

    def prepare(state, manifest):
        nonlocal retained
        previous = manifest
        if upgrade is not None:
            raw = release.read_bounded(ROOT, archive, release.MAX_ARCHIVE)
            old_target = json.loads(release.read_bounded(ROOT, target, 8192), object_pairs_hook=release.unique)
            previous = release.verify_bytes(raw, expected_sha256=archive_sha, target=old_target)
            plan = asset_upgrade_plan(previous, manifest, archive_sha, next_sha, upgrade[3])
        evidence, retained = restore_checkpoint(state, previous, prior, copies, receipt_sha,
                                                archive_sha, report_sha, guard_sha)
        if upgrade is not None:
            evidence.update(artifact_sha256=next_sha, asset_upgrade=plan)
        return evidence

    report = install.run(next_archive, next_sha, next_target, prepare_restore=prepare, asset_upgrade=upgrade is not None)
    retained_trees(*retained)
    report.update(status='pass', retained_trees_unchanged=True)
    name = 'recovery-report.json' if upgrade is None else 'upgrade-report.json'
    path = Path(report['evidence']).parents[1] / name
    execution_policy.write_json(path, report)
    return path, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior', required=True, help='Exact .runtime/release-install-* run')
    parser.add_argument('--archive', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--install-report-sha256', required=True)
    parser.add_argument('--guard-report-sha256', required=True)
    parser.add_argument('--boot-copy', help='Exact .runtime/release-recovery-* run to clone and boot under the guard')
    parser.add_argument('--copy-report-sha256', help='Trusted report digest for --boot-copy')
    parser.add_argument('--upgrade-archive', help='Distinct verified target Home archive for an asset-only upgrade')
    parser.add_argument('--upgrade-sha256', help='Trusted target archive digest')
    parser.add_argument('--upgrade-target', help='Exact target archive compatibility record')
    parser.add_argument('--saved-home-sha256', help='Reviewed v3 Gall saved-vase fingerprint')
    args = parser.parse_args()
    if (args.boot_copy is None) != (args.copy_report_sha256 is None):
        parser.error('--boot-copy and --copy-report-sha256 must be supplied together')
    upgrade = (args.upgrade_archive, args.upgrade_sha256, args.upgrade_target, args.saved_home_sha256)
    if any(value is not None for value in upgrade) and (args.boot_copy is None or not all(upgrade)):
        parser.error('Asset upgrade needs --boot-copy and all four upgrade inputs')
    try:
        common = (args.prior, args.archive, args.sha256, args.target,
                  args.install_report_sha256, args.guard_report_sha256)
        if args.boot_copy is None:
            path, report = rehearse(*common)
        else:
            path, report = boot_recovery(*common, args.boot_copy, args.copy_report_sha256,
                                         upgrade=upgrade if args.upgrade_archive is not None else None)
        print(json.dumps({'report': str(path), **report}, sort_keys=True))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Recovery rehearsal failed: ' + str(error) + '\n')

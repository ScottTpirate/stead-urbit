#!/usr/bin/env python3
"""Rehearse selected GitHub Work drafts on one disposable local Stead Home."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import github_work_plan as github
import portable_import as importer
import portable_recovery as portable


FORMAT = 'stead.github-work-import-plan/1'
TARGET_KEYS = {'origin', 'target', 'seed', 'title', 'project_key', 'project_id'}


def reviewed_preview(source, preview, digest):
    portable.require(portable.match(portable.TOKEN, digest), 'github-preview-sha256')
    raw = portable.private_file(preview, 2 * github.MAX_INPUT)
    portable.require(portable.sha(raw) == digest, 'github-preview-sha256')
    preview_data = portable.decoded(raw, 2 * github.MAX_INPUT)
    portable.require(isinstance(preview_data, dict), 'github-preview-format')
    expected = github.plan(portable.private_file(source, github.MAX_INPUT),
                           preview_data.get('repository'), preview_data.get('protocol'))
    portable.require(raw == portable.encoded(expected), 'github-preview-reconstruction')
    return expected


def import_commands(preview, preview_digest, numbers, origin, target, seed, title, key):
    limit = min(github.PROJECT_WORK_LIMIT, importer.MAX_STEPS - 1)
    portable.require(isinstance(numbers, list) and 0 < len(numbers) <= limit
                     and all(type(number) is int and number > 0 for number in numbers)
                     and len(set(numbers)) == len(numbers), 'github-import-selection')
    drafts = {row['source']['number']: row for row in preview['drafts']}
    portable.require(all(number in drafts for number in numbers), 'github-import-incomplete-draft')
    destination = importer.import_target(origin, target, seed, title, key)
    project = destination['project_id']
    provenance = {'protocol': preview['protocol'], 'repository': preview['repository'],
                  'source_sha256': preview['source_sha256'], 'preview_sha256': preview_digest}
    scope = (preview['repository'], preview_digest)
    steps = []
    commands = []

    def add(operation, original, resource, payload):
        step, command = importer.import_step(destination, operation, original, resource, payload)
        steps.append(step)
        commands.append(command)

    add('project.create', scope, project, importer.project_payload(destination))
    for number in sorted(numbers):
        draft = drafts[number]
        resource = importer.child_id(seed, 'work', preview['repository'], number)
        add('work.create', (*scope, number), resource, draft['payload'])
    importer.check_command_ids(commands)
    plan = {'protocol': FORMAT, **destination, 'provenance': provenance,
            'selected_issues': [drafts[number]['source'] for number in sorted(numbers)], 'steps': steps}
    return plan, commands


def load_import(path, digest, preview, preview_digest):
    portable.require(portable.match(portable.TOKEN, digest), 'import-plan-digest')
    raw = portable.private_file(path, importer.MAX_PLAN)
    portable.require(portable.sha(raw) == digest, 'import-plan-digest')
    value = portable.decoded(raw, importer.MAX_PLAN)
    portable.shape(value, TARGET_KEYS | {'protocol', 'provenance', 'selected_issues', 'steps'})
    selected = value['selected_issues']
    portable.require(isinstance(selected, list) and len(selected) <= github.PROJECT_WORK_LIMIT
                     and all(isinstance(row, dict) and 'number' in row for row in selected), 'github-import-selection')
    expected, commands = import_commands(preview, preview_digest, [row['number'] for row in selected],
        value['origin'], value['target'], value['seed'], value['title'], value['project_key'])
    portable.require(raw == portable.encoded(expected), 'import-plan-reconstruction')
    return expected, commands


def make_plan(args, preview, home):
    target = importer.target_member(home.member())
    portable.require(target['home'] == args.target_home, 'import-target-home')
    plan, commands = import_commands(preview, args.preview_sha256, args.issue, home.credentials['origin'],
                                    target, portable.new_id(), args.title, args.project_key)
    check_project_key(home, plan)
    raw = portable.encoded(plan)
    portable.require(len(raw) <= importer.MAX_PLAN, 'import-plan-size')
    github.publish(raw, args.output)
    digest = portable.sha(raw)
    return {'phase': 'planned', 'project_id': plan['project_id'], 'plan_sha256': digest,
            'commands': len(commands)}


def check_project_key(home, plan):
    _, visible = home.read.walk('projects', '', bound=16)
    portable.require(not any(row.get('project_key') == plan['project_key']
                             and row.get('project_id') != plan['project_id'] for row in visible),
                     'import-target-key-in-use')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest='operation', required=True)
    prepare = operations.add_parser('plan', help='Plan selected issues in a new disposable project')
    apply = operations.add_parser('apply', help='Apply or resume one bounded batch to that project')
    verify = operations.add_parser('verify', help='Verify all selected drafts through native readback')
    for sub in (prepare, apply, verify):
        sub.add_argument('--source', required=True, type=Path, help='Original private GitHub JSON export')
        sub.add_argument('--preview', required=True, type=Path, help='Reviewed GitHub Work preview')
        sub.add_argument('--preview-sha256', required=True)
        sub.add_argument('--session-file', required=True)
        sub.add_argument('--ca-file')
        sub.add_argument('--target-home', required=True)
    prepare.add_argument('--project-key', required=True)
    prepare.add_argument('--title', required=True)
    prepare.add_argument('--issue', required=True, action='append', type=int, help='Complete draft issue number; repeat to select')
    prepare.add_argument('--output', required=True, type=Path)
    for sub in (apply, verify):
        sub.add_argument('--plan', required=True)
        sub.add_argument('--plan-sha256', required=True)
        sub.add_argument('--confirm-project', required=True)
        sub.add_argument('--progress', required=True, help='Dedicated existing directory with mode 0700')
    apply.add_argument('--limit', type=int, default=importer.MAX_BATCH)
    args = parser.parse_args(argv)
    try:
        preview = reviewed_preview(args.source, args.preview, args.preview_sha256)
        if args.operation != 'plan':
            plan, commands = load_import(args.plan, args.plan_sha256, preview, args.preview_sha256)
            portable.require(plan['project_id'] == args.confirm_project, 'import-project-confirmation')
            portable.require(plan['target']['home'] == args.target_home, 'import-target-home')
        home = importer.LocalHome(portable.session_file(args.session_file), ca_file=args.ca_file)
        if args.operation == 'plan':
            result = make_plan(args, preview, home)
        else:
            with importer.Progress(args.progress) as progress:
                if args.operation == 'apply':
                    importer.check_target(home, plan)
                    check_project_key(home, plan)
                    result = importer.apply_import(home, plan, args.plan_sha256, commands, progress, args.limit)
                else:
                    result = importer.verify_import(home, plan, args.plan_sha256, commands, progress)
        result['preview_sha256'] = args.preview_sha256
        sys.stdout.buffer.write(portable.encoded(result))
        return 2 if result['phase'] == 'awaiting-receipt' else 0
    except portable.RecoveryError as error:
        print(f'GitHub Work import stopped ({error}). Preserve the private plan and progress.', file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, ValueError, OverflowError):
        print('GitHub Work import stopped. Preserve the private plan and progress before retrying.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

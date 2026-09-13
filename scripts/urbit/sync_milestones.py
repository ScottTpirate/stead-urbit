#!/usr/bin/env python3
"""Print local milestone plan; --apply uses authenticated gh to create/assign it."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from check_ecosystem import check, load, REPOSITORY

PREFIX = 'repos/' + REPOSITORY

def gh(method: str, path: str, body: dict | None = None, paginate: bool = False):
    if not path.startswith(PREFIX + '/'):
        raise ValueError('Refusing a different repository')
    cmd = ['gh', 'api', '--hostname', 'github.com', '--method', method,
           '-H', 'Accept: application/vnd.github+json', path]
    if paginate:
        cmd += ['--paginate', '--slurp']
    if body is not None:
        cmd += ['--input', '-']
    result = subprocess.run(cmd, input=None if body is None else json.dumps(body),
                            text=True, capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError('GitHub CLI request failed; check authentication/permissions locally. No credentials logged.')
    return json.loads(result.stdout)

def synchronize(root: Path, api=gh) -> tuple[int, int]:
    check(root)
    meta, _ = load(root)
    pages = api('GET', PREFIX + '/milestones?state=all&per_page=100', paginate=True)
    existing = [m for page in pages for m in page]
    by_title = {}
    for m in existing:
        if m['title'] in by_title:
            raise ValueError('Ambiguous duplicate milestone titles')
        by_title[m['title']] = m
    wanted = {task: m for m in meta['milestones'] for task in m['tasks']}
    snapshots = {}
    # Validate every target before any mutation. Never silently reassign another plan's milestones.
    for task, number in meta['issue_map'].items():
        issue = api('GET', PREFIX + f'/issues/{number}')
        if 'pull_request' in issue or not issue['title'].startswith('[' + task + ']'):
            raise ValueError('Issue number/title mismatch')
        current = issue.get('milestone')
        if current and current['title'] != wanted[task]['title']:
            raise ValueError('Existing different milestone; human reconciliation required')
        snapshots[task] = issue
    created = assigned = 0
    for m in meta['milestones']:
        if m['title'] not in by_title:
            by_title[m['title']] = api('POST', PREFIX + '/milestones',
                                      {'title': m['title'], 'description': m['exit']})
            created += 1
    for task, number in meta['issue_map'].items():
        target = by_title[wanted[task]['title']]['number']
        if snapshots[task].get('milestone') is None:
            # Re-read to reduce races; run with a single coordinator (GitHub PATCH is not compare-and-swap).
            now = api('GET', PREFIX + f'/issues/{number}')
            current = now.get('milestone')
            if current is not None:
                if current['number'] != target:
                    raise ValueError('Concurrent milestone assignment; stop and reconcile')
                continue
            if not now['title'].startswith('[' + task + ']') or 'pull_request' in now:
                raise ValueError('Issue changed during synchronization')
            api('PATCH', PREFIX + f'/issues/{number}', {'milestone': target})
            assigned += 1
    return created, assigned

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true', help='Explicitly write to the fixed target repository')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        check(root)
        meta, _ = load(root)
        if not args.apply:
            print('DRY RUN: no network or changes. Target: ' + REPOSITORY)
            for m in meta['milestones']:
                numbers = [str(meta['issue_map'][t]) for t in m['tasks']]
                print(m['title'] + ' -> issues ' + ', '.join(numbers))
            print('Review, then run with --apply on an authenticated gh workstation. No dates, status, visibility or protection changes.')
            return 0
        made, assigned = synchronize(root)
        print(f'Created {made} milestones; assigned {assigned} issues. Existing milestones/statuses were preserved.')
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

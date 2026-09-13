#!/usr/bin/env python3
"""Check planning/skill structure only; never certify native implementation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

REPOSITORY = 'ScottTpirate/stead-urbit'
SKILLS = ('stead-hoon', 'stead-gall-security', 'stead-native-tests', 'stead-urbit-release')

def load(root: Path) -> tuple[dict, list[dict]]:
    meta = json.loads((root / 'specs/urbit/ecosystem.json').read_text())
    base = json.loads((root / 'specs/urbit/backlog.json').read_text())['issues']
    return meta, base + meta['tasks']

def check(root: Path) -> tuple[int, int, int]:
    meta, items = load(root)
    if meta['repository'] != REPOSITORY or meta['schema_version'] != 1:
        raise ValueError('Unexpected target repository or schema')
    ids = [x['id'] for x in items]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate task ID')
    if any(not re.fullmatch(r'URB-\d{3}', x) for x in ids):
        raise ValueError('Invalid task ID')
    by_id = {x['id']: x for x in items}
    edges = {}
    for x in items:
        if not x['title'] or not x['owner_role'] or not x['acceptance']:
            raise ValueError('Missing task title, owner or acceptance')
        if x['phase'] not in {str(i) for i in range(7)}:
            raise ValueError('Invalid phase')
        if not isinstance(x['depends_on'], list):
            raise ValueError('Dependencies must be a list')
        edges[x['id']] = list(x['depends_on'])
    edges['URB-130'] += meta['canary_admission']
    for deps in edges.values():
        if set(deps) - set(ids):
            raise ValueError('Unknown dependency')
    active, done = set(), set()
    def visit(node: str) -> None:
        if node in active:
            raise ValueError('Dependency cycle')
        if node in done:
            return
        active.add(node)
        for dep in edges[node]:
            visit(dep)
        active.remove(node)
        done.add(node)
    for node in ids:
        visit(node)
    mapping = meta['issue_map']
    if set(mapping) != set(ids):
        raise ValueError('Issue map does not cover tasks exactly')
    if any(type(n) is not int or n <= 1 for n in mapping.values()):
        raise ValueError('Invalid issue number')
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Duplicate issue number')
    phases, covered, mids, titles = set(), [], set(), set()
    for m in meta['milestones']:
        if m['phase'] in phases or m['id'] in mids or m['title'] in titles:
            raise ValueError('Duplicate milestone')
        if m['id'] != 'M' + m['phase'] or not m['exit']:
            raise ValueError('Invalid milestone')
        phases.add(m['phase']); mids.add(m['id']); titles.add(m['title'])
        for task in m['tasks']:
            if task not in by_id or by_id[task]['phase'] != m['phase']:
                raise ValueError('Milestone/task phase mismatch')
            covered.append(task)
    if phases != {str(i) for i in range(7)} or sorted(covered) != sorted(ids):
        raise ValueError('Milestones must cover each task once')
    for name in SKILLS:
        p = root / '.agents/skills' / name / 'SKILL.md'
        raw = p.read_bytes()
        if b'\r' in raw:
            raise ValueError('Skill uses non-LF source')
        parts = raw.decode().split('---\n', 2)
        if len(parts) != 3 or parts[0] != '':
            raise ValueError('Missing skill frontmatter')
        fields = {}
        for line in parts[1].strip().splitlines():
            key, sep, value = line.partition(':')
            if not sep or key in fields:
                raise ValueError('Invalid skill frontmatter')
            fields[key] = value.strip()
        if set(fields) != {'name', 'description'} or fields['name'] != name or not fields['description']:
            raise ValueError('Skill name/description invalid')
        if not parts[2].strip():
            raise ValueError('Empty skill body')
    for path in ('AGENTS.md','CONTRIBUTING.md','SECURITY.md','SUPPORT.md',
                 'docs/urbit/ECOSYSTEM_PLAN.md','docs/urbit/DEVELOPER_GUIDE.md','docs/urbit/STEAD_CARRYOVER.md'):
        if not (root / path).is_file():
            raise ValueError('Missing guidance: ' + path)
    return len(items), len(meta['milestones']), len(SKILLS)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        tasks, milestones, skills = check(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('FAIL (planning structure): ' + str(exc), file=sys.stderr)
        return 1
    print(f'PASS (planning only): {tasks} tasks, {milestones} milestones, {skills} skill files.')
    print('NOT VERIFIED: issue status, Hoon, skill effectiveness, live GitHub sync, security or release readiness.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

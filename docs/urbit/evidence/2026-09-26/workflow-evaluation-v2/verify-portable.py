"""Independent portable-byte/reference/inventory audit; no native or test run."""
from pathlib import Path, PurePosixPath
import datetime
import hashlib
import json
import os
import subprocess
import tarfile

BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent
OUT = BASE / 'portable-bundle'
MAX_FILE = 16 * 1024 * 1024
EXPECTED_INDEX = 'a92e0b35fdb4dcbf25348999a107a07514c0efaf0ffed88497134f6a5b9d01d0'
HEAD = '0d877cff4319de8d437f0da58d4518535f758c36'
ROLES = ('baseline', 'local_skill_assisted')


def check(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    check(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(), 'Nonregular/redirected input')
    check(path.stat().st_size <= MAX_FILE, 'File bound')
    data = path.read_bytes()
    check(len(data) <= MAX_FILE, 'Read bound')
    return data


def safe(name):
    value = PurePosixPath(name)
    check(not value.is_absolute() and value.as_posix() == name
          and all(part not in ('', '.', '..') for part in value.parts), 'Unsafe portable path')
    return value


def remotes():
    check(subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=REPO).decode().strip()
          == 'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong origin')
    check(subprocess.check_output(['git', 'remote', 'get-url', '--push', 'upstream'], cwd=REPO).decode().strip()
          == 'DISABLED_UPSTREAM_PUSH', 'Wrong upstream push boundary')


def main():
    remotes()
    check(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO).decode().strip() == HEAD, 'Changed HEAD')
    check(os.sched_getaffinity(0) == {19}, 'Wrong audit affinity')
    cgroup = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1]
    cpu = (Path('/sys/fs/cgroup') / cgroup.lstrip('/') / 'cpu.max').read_text().strip()
    check(cpu == '5000 10000', 'Wrong audit CPU quota')
    raw = read(OUT / 'index.json')
    check(digest(raw) == EXPECTED_INDEX, 'Index changed')
    index = json.loads(raw)
    output_paths = {'index.json'}
    for row in [index['archive'], index['members'], index['selection_plan'], *index['accessible_reports']]:
        safe(row['path'])
        check(row['path'] not in output_paths, 'Duplicate exposed output')
        value = read(OUT / row['path'])
        check(len(value) == row['bytes'] and digest(value) == row['sha256'], 'Portable output hash/length')
        output_paths.add(row['path'])
    actual_outputs = {p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file()}
    check(actual_outputs == output_paths, 'Unexpected/missing pre-review portable output')
    members = json.loads(read(OUT / index['members']['path']))
    plan = json.loads(read(OUT / index['selection_plan']['path']))
    declared = {row['path']: row for row in members}
    selected = {row['path']: row for row in plan['members']}
    check(len(declared) == len(selected) == len(members) == len(plan['members']) == 1258,
          'Duplicate/missing selected member')
    check(set(declared) == {'payload/' + name for name in selected}, 'Plan/member inventory differs')
    payload, total = {}, 0
    with tarfile.open(OUT / index['archive']['path'], 'r|gz') as archive:
        for member in archive:
            safe(member.name)
            check(member.name in declared and member.name not in payload and member.isfile()
                  and member.mode == 0o400 and member.uid == member.gid == member.mtime == 0
                  and member.uname == member.gname == '' and 0 <= member.size <= MAX_FILE,
                  'Archive entry identity/type/metadata differs')
            value = archive.extractfile(member).read(MAX_FILE + 1)
            check(len(value) == member.size == declared[member.name]['bytes']
                  and digest(value) == declared[member.name]['sha256'], 'Archive entry bytes differ')
            original = member.name.removeprefix('payload/')
            safe(original)
            row = selected[original]
            check(len(value) == row['bytes'] and digest(value) == row['sha256']
                  and read(REPO / original) == value, 'Selected original bytes differ')
            payload[member.name] = value
            total += len(value)
            check(total <= 128 * 1024 * 1024, 'Aggregate audit bound')
    check(set(payload) == set(declared) and total == index['counts']['uncompressed_bytes'] == 32451619,
          'Incomplete archive')
    for row in index['accessible_reports']:
        value = payload['payload/' + row['original_path']]
        check(row['compression'] is None and read(OUT / row['path']) == value
              and len(value) == row['original_bytes'] and digest(value) == row['original_sha256'],
              'Accessible report differs from original archive member')
    references = 0
    def check_refs(value):
        nonlocal references
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                name = value['path']
                if name.startswith('evidence.tar.gz#payload/'):
                    key = name.split('#', 1)[1]
                    check(key in payload, 'Missing archive-fragment reference')
                    data = payload[key]
                else:
                    safe(name)
                    check(name in output_paths, 'Unexposed/escaping portable result reference')
                    data = read(OUT / name)
                check(digest(data) == value['sha256'], 'Result/reference hash differs')
                references += 1
            for child in value.values():
                check_refs(child)
        elif isinstance(value, list):
            for child in value:
                check_refs(child)
    result = json.loads(read(OUT / 'reports/result.json'))
    audit = json.loads(read(OUT / 'reports/independent-audit.json'))
    check_refs(result)
    check_refs(audit)
    check(result['independent_review']['artifact'] == 'reports/independent-audit.json', 'Review link differs')
    audited_trees = []
    def inventory_tree(path):
        names = set()
        for parent, directories, files in os.walk(path, followlinks=False):
            directories[:] = [name for name in directories if name != '__pycache__']
            for name in directories + files:
                child = Path(parent) / name
                check(not child.is_symlink(), 'Inventory symlink')
                if child.is_dir() or name.endswith(('.lock', '.pyc')):
                    continue
                check(child.is_file(), 'Special inventory member')
                names.add(child.relative_to(REPO).as_posix())
        prefix = path.relative_to(REPO).as_posix() + '/'
        check(names == {name for name in selected if name.startswith(prefix)}, 'Omitted/extra lifecycle tree file')
        audited_trees.append({'path': prefix, 'files': len(names)})
    role_counts = {}
    for role in ROLES:
        for name in ('input', 'candidate', 'calls', 'timing', 'feedback-attempts'):
            inventory_tree(BASE / role / name)
        root = BASE / 'private-scores' / role
        inventory_tree(root)
        inventory_tree(REPO / '.runtime/workflow-evaluation-v2' / role)
        report = json.loads(read(root / 'native-inner.json'))
        subjects = report['tasks'][4]['t05_assessment']['subjects']
        check([row['outcome'] for row in subjects] == ['correct-pass','killed','survived','killed','killed'],
              'T05 outcome inventory differs from independently replayed report')
        check(report['tasks'][4]['expected_cases'] == report['tasks'][4]['observed_cases']
              and len(report['tasks'][4]['results']) == 5, 'Incomplete T05 task inventory')
        for relative, expected in report['generated_source_files_sha256'].items():
            key = 'payload/' + root.relative_to(REPO).as_posix() + '/native-inputs/' + relative
            check(key in payload and digest(payload[key]) == expected, 'Missing actual private generated source')
        receipts = sorted((BASE / role / 'feedback-attempts').glob('*/*/result.json'))
        published = 0
        for path in receipts:
            receipt = json.loads(read(path))
            owner = REPO / receipt['owned_run']['path']
            for name in ('report.json','events.jsonl','.stead-disposable.json','control/source-context.json'):
                check('payload/' + (owner / name).relative_to(REPO).as_posix() in payload,
                      'Missing actual reserved-attempt guard/source artifact')
            if receipt['status'] == 'published':
                published += 1
                report = json.loads(read(path.parent / 'internal.json'))
                original = REPO / report['evidence_file'] if 'evidence_file' in report else None
                check((path.parent / 'public.json').is_file(), 'Missing actual public feedback')
        role_counts[role] = {'reserved_public_attempts':len(receipts), 'published_public_attempts':published,
                            'private_subjects':len(subjects),
                            'wrapper_starts':len(list((BASE / role / 'calls').glob('*.start.json')))}
    for path in (REPO / '.runtime/workflow-evaluation-v2/feedback',
                 BASE / 'parent-deliveries', BASE / 'filtered-traces-safe', BASE / 'support-versions',
                 REPO / '.runtime/phase01-20260926/baseline-T06-1-infrastructure',
                 REPO / 'docs/urbit/evidence/2026-09-26/native-attempts/prequal12'):
        inventory_tree(path)
    check(role_counts == {'baseline':{'reserved_public_attempts':7,'published_public_attempts':6,
                                     'private_subjects':5,'wrapper_starts':49},
                          'local_skill_assisted':{'reserved_public_attempts':7,'published_public_attempts':7,
                                                  'private_subjects':5,'wrapper_starts':57}}, 'Actual lifecycle counts differ')
    check(read(OUT/'index.json') == raw, 'Index changed during final review')
    record = {'protocol':'stead.workflow-v2-portable-final-review/1', 'reviewer':'/root/independent_review',
              'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_commit':HEAD, 'index_sha256':EXPECTED_INDEX,
              'result_sha256':digest(read(OUT/'reports/result.json')),
              'artifact_semantic_review_sha256':digest(read(OUT/'reports/independent-audit.json')),
              'verifier_sha256':digest(read(Path(__file__).resolve())),
              'classification':'Separate read-only archive member, original-byte, reference and lifecycle-inventory audit',
              'status':'reviewed-complete-with-recorded-candidate-failures-and-provenance-limits',
              'checks':{'archive_members':len(payload),'uncompressed_bytes':total,'portable_outputs':len(output_paths),
                        'exposed_original_reports':len(index['accessible_reports']), 'resolved_result_references':references,
                        'all_original_bytes_unchanged':True,'all_members_rehashed':True,'all_exposed_report_bytes_match':True},
              'audited_lifecycle_trees':audited_trees,'actual_lifecycle_counts':role_counts,
              'resource_scope':{'affinity':[19],'cpu_max':cpu,'control_group':cgroup},
              'native_or_test_suites_executed':False,'hidden_reasoning_or_raw_rollouts_packaged':False,
              'qualifies_phase':False,
              'limits':['Original prepackaging pending-review labels are preserved; this is a later, separately attributed review.',
                        'Observed complete 5/6 tie is a completed local comparison, not a universal participant pass or efficacy claim.',
                        'All 15 encrypted deliveries match child descriptors; 12 earlier plaintexts remain unavailable and three are attributed integrator observations.',
                        'Complete context isolation or initial plaintext equality is not established; actual exposed-tool and path-typo limits remain explicit.',
                        'Full URB-170 closure also requires the separately mapped local-skill, upstream, editor, LF/frontmatter, sandbox and contributor-setup evidence.']}
    remotes()
    target = OUT / 'POSTPACKAGING_REVIEW.json'
    data = (json.dumps(record,indent=2,sort_keys=True)+'\n').encode()
    fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'review':str(target.relative_to(REPO)), 'sha256':digest(data), **record['checks']},indent=2))


if __name__ == '__main__':
    main()

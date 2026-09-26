"""Archive the completed synthetic paired trial; no native/test execution.

Run once from the repository root in a CPU50%/10ms, CPU19 user scope.
Inputs are explicit completed trial records, never raw Codex rollouts or piers.
Every retained original is byte-preserved and indexed under its original path.
"""
from __future__ import annotations
import collections
import datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile

REPO = Path.cwd()
OUT = Path(__file__).absolute().parent
BASE = REPO / '.runtime/workflow-participants'
WORKFLOW = REPO / '.runtime/workflow-evaluation'
ROLES = ('baseline', 'local_skill_assisted')
HEAD = '8334a75cad4c2b063147e7e3352cdf76da0d5893'
PACKAGE = 'd78697102021b4b4837efd2d560668310fad5ab69fcbf98c7592a9cd0fff3e00'
payload, descriptions, accessible = {}, {}, {}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode()


def read(path):
    path = Path(path).absolute()
    require(path.is_relative_to(REPO) and not any(p.is_symlink() for p in (path, *path.parents)), 'Redirected/nonrepository input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 16 * 1024 * 1024, 'Input file bound/type')
        data = source.read(16 * 1024 * 1024 + 1)
    require(len(data) <= 16 * 1024 * 1024, 'Input grew beyond bound')
    return data


def document(path):
    return json.loads(read(path))


def remotes():
    for extra in ([], ['--push']):
        require(subprocess.check_output(['git', 'remote', 'get-url', *extra, 'origin']).strip()
                == b'https://github.com/ScottTpirate/stead-urbit.git', 'Wrong derivative origin')
    require(subprocess.check_output(['git', 'remote', 'get-url', '--push', 'upstream']).strip()
            == b'DISABLED_UPSTREAM_PUSH', 'Upstream must stay read-only')


def save(path, raw):
    require(path.is_relative_to(OUT), 'Evidence output scope')
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Redirected output')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)


def add(path, classification):
    path = Path(path).absolute()
    name = path.relative_to(REPO).as_posix()
    require('.codex' not in path.parts and 'sessions' not in path.parts
            and '__pycache__' not in path.parts and not name.endswith(('.pyc', '.lock')), 'Excluded evidence path')
    raw = read(path)
    if name in payload:
        require(payload[name] == raw, 'Evidence changed during collection')
    else:
        payload[name] = raw
        require(len(payload) <= 4096 and sum(map(len, payload.values())) <= 128 * 1024 * 1024, 'Archive count/byte bound')
    descriptions.setdefault(name, set()).add(classification)
    return name


def tree(root, classification):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'Missing evidence directory')
    entries = 0
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name != '__pycache__')
        for name in dirs + sorted(names):
            entries += 1
            require(entries <= 8192, 'Evidence directory entry bound')
            path = Path(base) / name
            require(not path.is_symlink(), 'Redirected evidence entry')
            if path.is_dir():
                continue
            if name.endswith(('.pyc', '.lock')):
                continue
            add(path, classification)


def expose(origin, dest, classification, *, compressed=False):
    name = add(origin, classification)
    raw = payload[name]
    data = gzip.compress(raw, compresslevel=6, mtime=0) if compressed else raw
    target = OUT / dest
    save(target, data)
    ref = {'path': target.relative_to(REPO).as_posix(), 'sha256': sha(data), 'classification': classification,
           'original_path': name, 'bytes': len(data), 'decoded_sha256': sha(raw), 'decoded_bytes': len(raw)}
    accessible[name] = ref
    return ref


def archive_ref(path, classification):
    name = add(path, classification)
    return {'path': (OUT / 'evidence.tar.gz').relative_to(REPO).as_posix() + '#payload/' + name,
            'sha256': sha(payload[name]), 'classification': classification, 'hash_scope': 'exact uncompressed archive member'}


def filtered_trace_check(root):
    manifest = document(root / 'manifest.json')
    require(manifest['not_full_rollout'] is True, 'Trace must identify filtering')
    for role in ROLES:
        raw = read(root / (role + '.jsonl'))
        ref = manifest['roles'][role]['filtered_trace']
        require(sha(raw) == ref['sha256'] and len(raw) == ref['bytes'], 'Filtered trace hash mismatch')
        for line in raw.splitlines():
            row = json.loads(line)
            kind, data = row['type'], row['payload']
            if kind == 'response_item':
                require(data.get('type') in ('custom_tool_call', 'custom_tool_call_output', 'function_call',
                        'function_call_output', 'agent_message', 'message'), 'Excluded response payload')
                if data['type'] == 'message':
                    require(data.get('role') == 'assistant' and data.get('phase') in ('commentary', 'final_answer'),
                            'Hidden/nonvisible message cannot be exported')
            else:
                require(kind in ('session_meta', 'turn_context', 'inter_agent_communication_metadata', 'event_msg'), 'Excluded trace kind')
                if kind == 'event_msg':
                    require(data.get('type') in ('task_started', 'task_complete'), 'Excluded event body')
    tree(root, 'filtered-task-trace-not-full-rollout')
    return manifest


def preserve_run(owner, output_prefix):
    directory = REPO / owner['path']
    require(directory.parent == REPO / '.runtime/execution-runs' and directory.name.startswith('four-fakes-'), 'Wrong owned run path')
    for name in ('.stead-disposable.json', 'events.jsonl'):
        add(directory / name, 'actual-owned-guard-event-record')
    guard = expose(directory / 'report.json', output_prefix + '/guard.json', 'actual-outer-guard')
    context = expose(directory / 'control/source-context.json', output_prefix + '/source-context.json', 'actual-source-context')
    require(document(directory / 'report.json')['run_id'] == owner['run_id'], 'Owned guard identity mismatch')
    return guard, context


def check_shape(value, schema, root):
    if '$ref' in schema:
        selected = root
        for part in schema['$ref'].removeprefix('#/').split('/'):
            selected = selected[part]
        return check_shape(value, selected, root)
    kinds = schema.get('type')
    kinds = [kinds] if isinstance(kinds, str) else kinds
    types = {'object': dict, 'array': list, 'string': str, 'number': (int, float), 'null': type(None)}
    if kinds:
        require(any(isinstance(value, types[kind]) and not (kind == 'number' and isinstance(value, bool)) for kind in kinds), 'Result schema type')
    if 'const' in schema:
        require(value == schema['const'], 'Result schema const')
    if 'enum' in schema:
        require(value in schema['enum'], 'Result schema enum')
    if 'pattern' in schema and isinstance(value, str):
        require(re.fullmatch(schema['pattern'], value), 'Result schema pattern')
    if 'minimum' in schema and isinstance(value, (int, float)):
        require(value >= schema['minimum'], 'Result schema minimum')
    if isinstance(value, dict):
        require(set(schema.get('required', [])) <= set(value), 'Result schema required field')
        for key, child in schema.get('properties', {}).items():
            if key in value:
                check_shape(value[key], child, root)
    if isinstance(value, list) and 'items' in schema:
        for item in value:
            check_shape(item, schema['items'], root)


def main():
    remotes()
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == HEAD, 'Recorded source HEAD changed')
    cg = Path('/proc/self/cgroup').read_text().strip().removeprefix('0::')
    require(cg.startswith('/user.slice/') and '..' not in cg.split('/'), 'Owned packaging scope required')
    cpu_max = (Path('/sys/fs/cgroup' + cg) / 'cpu.max').read_text().strip()
    require(cpu_max == '5000 10000' and sorted(os.sched_getaffinity(0)) == [19], 'Packaging quota/affinity differs')
    final = document(BASE / 'final-submissions.json')
    launch = document(BASE / 'launch-admission.json')
    oracles = document(REPO / 'tests/urbit/skill_evaluation/reviewer/oracles.json')
    freeze = document(REPO / 'tests/urbit/skill_evaluation/freeze.json')
    require(freeze['package_sha256'] == PACKAGE, 'Frozen package differs')
    for path in sorted(BASE.iterdir()):
        if path.is_file() and not path.name.endswith('.lock'):
            add(path, 'parent-support-or-observation-record')
    tree(BASE / 'support-versions', 'preserved-superseded-support-source')
    traces = filtered_trace_check(BASE / 'filtered-traces')
    filtered_trace_check(BASE / 'filtered-traces-v1-missing-visible-messages')
    for role in ROLES:
        for area in ('input', 'candidate', 'calls', 'timing', 'feedback-attempts'):
            tree(BASE / role / area, 'participant-' + area)
        add(BASE / role / 'input-preparation.json', 'historical-prelaunch-preparation')
        tree(BASE / 'private-scores' / role, 'actual-private-score-lifecycle-and-inputs')
        tree(WORKFLOW / role, 'immutable-final-candidate-snapshot')
    tree(WORKFLOW / 'feedback', 'immutable-public-attempt-snapshot')
    for name in ('prequalification.json', 'prequalification-inner.json', 'prequalification-guard.json'):
        add(WORKFLOW / name, 'completed-reference-prequalification')
    one_binding = document(BASE / 'private-scores/baseline/score-result.json')['binding']
    for root, files in one_binding['inventories'].items():
        for name, expected in files.items():
            origin = REPO / root / name
            require(sha(read(origin)) == expected, 'Scored source differs: ' + str(origin))
            add(origin, 'exact-scored-source-input')
    for name in ('Makefile', 'LICENSE'):
        if (REPO / name).is_file():
            add(REPO / name, 'source-build-or-license')
    for name in ('LICENSE.txt', 'pkg/arvo/LICENSE.txt'):
        add(REPO / '.runtime/urbit-5a187fededc4582a34fcd6055c67bb63e0917b94' / name, 'pinned-upstream-license')
    prequal_refs = [expose(WORKFLOW / name, 'raw/prequalification/' + name, 'completed-reference-prequalification')
                    for name in ('prequalification.json', 'prequalification-inner.json', 'prequalification-guard.json')]
    original_prequal = REPO / 'docs/urbit/evidence/2026-09-26/native-attempts/prequal11/index.json'
    prequal_refs.append({'path': original_prequal.relative_to(REPO).as_posix(), 'sha256': sha(read(original_prequal)),
                         'classification': 'previous-portable-prequalification-index'})
    conditions, public_index, private_index = [], [], []
    for role in ROLES:
        root = BASE / 'private-scores' / role
        scored = document(root / 'score-result.json')
        inner = document(root / 'native-inner.json')
        require(scored['status'] == 'completed-with-candidate-failures' and scored['tasks_passed'] == 5
                and not scored['errors'] and scored['cleanup_completed'] is True, 'Private execution changed')
        require(inner['source_commit'] == HEAD and inner['package_sha256'] == PACKAGE
                and inner['candidate_files_sha256'] == inner['candidate_inputs_after'], 'Private source/input binding')
        for name, ref in scored['artifacts'].items():
            require(sha(read(root / name)) == ref['sha256'], 'Retained private artifact hash')
        raw_ref = expose(root / 'native-inner.json', 'raw/private/' + role + '/native-inner.json', 'actual-private-native-report')
        score_ref = expose(root / 'score-result.json', 'raw/private/' + role + '/score-result.json', 'parent-one-shot-score-admission')
        guard_ref, context_ref = preserve_run(scored['owned_run'], 'raw/private/' + role)
        require(guard_ref['decoded_sha256'] == scored['artifacts']['guard.json']['sha256'], 'Private guard copy differs')
        guard = document(root / 'guard.json')
        require(guard['status'] == 'completed' and guard['exit_code'] == 0 and not guard.get('cleanup')
                and guard.get('reason') is None, 'Private outer guard did not complete cleanly')
        private_index.append({'condition': role, 'report': raw_ref, 'score': score_ref, 'guard': guard_ref,
                              'source_context': context_ref, 'tasks_passed': 5, 'tasks_total': 6})
        attempts = {task['id']: [] for task in oracles['tasks']}
        for path in sorted((BASE / role / 'feedback-attempts').glob('*/*/result.json')):
            receipt = document(path)
            task, number = receipt['task'], receipt['attempt']
            prefix = 'raw/public/' + role + '/' + task + '/' + str(number)
            attempt_guard, attempt_context = preserve_run(receipt['owned_run'], prefix)
            result_ref = expose(path, prefix + '/result.json', 'actual-public-attempt-lifecycle')
            row = {'condition': role, 'task': task, 'number': number, 'candidate_files_sha256': receipt['files_sha256'],
                   'public_feedback_artifacts': [], 'observed_outcome': 'refused' if receipt.get('no_launch_refusal') else receipt.get('public_status'),
                   'lifecycle': result_ref, 'guard': attempt_guard, 'source_context': attempt_context,
                   'started_at': receipt['started_at'], 'finished_at': receipt['finished_at']}
            if receipt.get('status') == 'published':
                public_ref = expose(path.parent / 'public.json', prefix + '/public.json', 'actually-published-public-only-feedback')
                report_ref = expose(path.parent / 'internal.json', prefix + '/native-inner.json.gz', 'actual-public-native-report', compressed=True)
                controller = sorted(path.parent.glob('*-feedback.finish.json'))
                require(len(controller) == 1, 'Exact public controller result required')
                result = json.loads(bytes.fromhex(document(controller[0])['stdout_hex']))
                original = REPO / result['evidence_file']
                require(original.parent == REPO / '.piers/fakes/logs' and read(original) == read(path.parent / 'internal.json'), 'Public native report copy differs')
                add(original, 'original-public-native-report')
                tree(original.with_name(original.stem + '-inputs'), 'actual-public-generated-native-inputs')
                row['public_feedback_artifacts'] = [public_ref]
                row['native_report'] = report_ref
                row['native_execution'] = 'completed'
            else:
                require(receipt.get('no_launch_refusal') is True and receipt.get('native_execution') == 'not-launched', 'Unclassified public failure')
                row.update(native_execution='not-launched', native_report=None,
                           observation_limit='No candidate compile/runtime observation or public feedback file exists for this reservation.')
            attempts[task].append(row)
            public_index.append(row)
        trace = traces['roles'][role]
        contexts = trace['model_contexts']
        require({row['model'] for row in contexts} == {'gpt-6-astra'} and {row['effort'] for row in contexts} == {'max'}, 'Reported model/settings differ')
        initial = launch[role]['inventory']
        for name, expected in initial.items():
            require(sha(read(BASE / role / 'input' / name)) == expected, 'Initial participant input changed')
        final_clock = document(REPO / final['conditions'][role]['final_clock_record'])
        require(final_clock['state_after'] == 'closed' and final_clock['active_after_ns'] / 1e9
                == final['conditions'][role]['charged_active_seconds'], 'Final timing mismatch')
        tasks = []
        for row, task in zip(inner['tasks'], oracles['tasks'], strict=True):
            name = row['id']
            require(name == task['id'], 'Six-task order differs')
            task_assertions = [{'id': check['name'], 'status': 'passed' if check['passed'] else 'failed',
                                'actual': check['passed'], 'expected': True,
                                'artifact': {**raw_ref, 'pointer': '/checks/' + str(number)}}
                               for number, check in enumerate(inner['checks']) if check['name'].startswith((name + ':', name + '-'))]
            bindings = {'source_commit': HEAD, 'runtime_lock_sha256': inner['toolchain_sha256'],
                        'installed_clay_tree_sha256': None,
                        'installed_clay_scope': 'Only sequential installed-file projections and native readbacks were retained; no full Clay tree hash was measured.',
                        'installed_clay_projection_sha256': sha(json.dumps(inner['installed_clay_files'], sort_keys=True, separators=(',', ':')).encode()),
                        'loaded_closure_sha256': sha(json.dumps(inner['loaded_closure'], sort_keys=True, separators=(',', ':')).encode()),
                        'derived_hash_format': 'UTF-8 JSON, sorted keys, comma/colon separators, no trailing newline',
                        'oracle_sha256': freeze['files']['reviewer/oracles.json'],
                        'evaluator_sha256': inner['loaded_closure']['/code/skill_evaluation_support.py'],
                        'guard_report_sha256': guard_ref['decoded_sha256'],
                        'loaded_closure': inner['loaded_closure'],
                        'private_score_helper_sha256': scored['binding']['private_score_helper_sha256']}
            out = {'id': name, 'status': row['status'], 'attempts': attempts[name],
                   'candidate_files_sha256': inner['candidate_files_sha256'][name], 'bindings': bindings,
                   'classification': task['classification'], 'compile_outcome': 'passed',
                   'runtime_outcome': 'passed' if row['status'] == 'passed' else 'failed',
                   'expected_cases': row.get('expected_cases', []), 'observed_cases': row.get('observed_cases', []),
                   'assertions': task_assertions, 'artifacts': [raw_ref, guard_ref, context_ref, score_ref],
                   'private_scoring_invocations': 1, 'post_private_feedback_repairs': 0}
            if name == 'T05':
                tests = read(WORKFLOW / role / 'T05/tests/eval-coverage.hoon').decode()
                arms = re.findall(r'^\+\+ {2,}(test-[a-z0-9-]+)\b', tests, re.M)
                pure = [command for command in inner['commands'] if command.get('kind') == 'native-pure-evaluator' and command.get('label', '').startswith('T05-')]
                require([command['label'] for command in pure] == ['T05-correct', 'T05-claimed-author', 'T05-outsider-granted'], 'Actual partial mutation inventory differs')
                require('eval (run):' in pure[-1]['stderr'] and 'eval: bail: %exit' in pure[-1]['stderr']
                        and pure[-1]['stdout'] == '', 'Expected observed runtime failure differs')
                subjects = ['correct'] + [Path(path).stem for path in task['mutants']]
                out.update(status='invalid', observed_adapter_task_status=row['status'],
                           qualification_reason='Two required mutation subjects were not run; the frozen README invalidates missing-case tasks.',
                           expected_cases=['subject:' + label for label in subjects],
                           observed_cases=['subject:' + command['label'].removeprefix('T05-') for command in pure],
                           submitted_test_arms=arms, submitted_test_arm_count=len(arms),
                           correct_subject_arms_observed=len(arms),
                           mutation_subjects=[{'id': label, 'status': ('passed-correct-subject' if label == 'correct'
                                   else 'killed' if label == 'claimed-author' else 'not-killed-runtime-assertion-failed'
                                   if label == 'outsider-granted' else 'not_run')} for label in subjects],
                           missing_subjects=['everyone-granted', 'claim-must-match'],
                           compile_scope='Submitted tests compiled and executed against the correct subject and claimed-author mutant; outsider evaluator reached eval(run) then bailed. Later two mutation programs were not run.',
                           runtime_limit='The raw task row has no completed result/case arrays after the failed outsider-granted assertion. Partial command observations are retained here; no complete mutant inventory or successful outsider test tang is invented.',
                           error=row['error'])
            tasks.append(out)
        conditions.append({'condition': role, 'context_id': final['conditions'][role]['context_id'],
                           'model': 'gpt-6-astra', 'settings': {'reasoning_effort': 'max', 'fork_turns': 'none',
                           'immutable_backend_model_revision': None, 'exposed_tools': 'Full inherited catalog; permitted work operations restricted by instruction and file wrapper, with trace audit required.',
                           'active_budget_seconds': 1800, 'public_attempt_budget_per_task': 3},
                           'input_files_sha256': {name: value for name, value in initial.items() if not name.startswith('assisted/')},
                           'skill_files_sha256': {name: value for name, value in initial.items() if name.startswith('assisted/')},
                           'context_contamination': [],
                           'context_audit': 'Independent reviewer found no prohibited observed task/tool access; full inherited context and encrypted incoming plaintext equivalence are not proved.',
                           'active_seconds': final['conditions'][role]['charged_active_seconds'],
                           'infrastructure_seconds': final['conditions'][role]['infrastructure_paused_seconds'],
                           'timing_definition': final_clock['definition'],
                           'conservative_failed_delivery_charge_seconds': 23.683894211 if role == 'baseline' else 0,
                           'timing_artifact': archive_ref(REPO / final['conditions'][role]['final_clock_record'], 'actual-parent-clock-journal'),
                           'tasks': tasks, 'tasks_passed': 5, 'tasks_total': 6,
                           'first_work_order': ['T01', 'T02', 'T03', 'T04', 'T05', 'T06'],
                           'later_feedback_revisits': ['T01', 'T02'] if role == 'baseline' else [],
                           'filtered_trace': archive_ref(BASE / 'filtered-traces' / (role + '.jsonl'), 'filtered-task-and-tool-trace'),
                           'no_private_feedback_or_repairs': 'Parent final submission, immutable snapshots and one-shot scoring records retained and independently audited; no post-private participant work observed.'})
    result = {'protocol': 'stead.skill-evaluation-result/1', 'status': 'incomplete',
              'execution_status': 'both-one-shot-invocations-completed-T05-corpus-incomplete', 'package_sha256': PACKAGE, 'source_commit': HEAD,
              'prequalification_artifacts': prequal_refs, 'conditions': conditions,
              'independent_review': {'status': 'completed-with-blocking-T05-inventory-gap', 'reviewer': '/root/editor_tool_review',
                                     'scope': 'Task/tool traces, timing reconciliation and T05 semantics. Trace/timing checks cleared within stated limits; missing two mutation subjects invalidates T05 qualification.',
                                     'disposition': 'Keep URB-170 open; repair/version evaluator and run a new pair of fresh contexts. Never resume or privately rescore v1 candidates.',
                                     'record': {'path': (OUT / 'independent-review-disposition.json').relative_to(REPO).as_posix(),
                                                'sha256': sha(read(OUT / 'independent-review-disposition.json'))},
                                     'record_attribution': 'Actual reviewer messages received and recorded by /root/independent_review; reviewer did not author this artifact file.'},
              'comparison': {'baseline_passed': 5, 'local_skill_assisted_passed': 5, 'tasks_per_condition': 6,
                             'assisted_minus_baseline_passed': 0, 'invalid_tasks_per_condition': 1,
                             'interpretation': 'Five qualified task passes each and one invalid partial task each. Raw scorer reports5/6 each, but the six-task v1 corpus is incomplete. No efficacy or general model/skill effect claim.'},
              'qualification': 'No phase, deployment, production, live-network or browser acceptance follows from this trial.',
              'limits': ['One fresh context per condition, one private invocation each, same model alias/effort; immutable backend revision unknown.',
                         'Full inherited tools were exposed. Permitted file operations had wrapper controls; whole-model-tool isolation is not claimed.',
                         'Incoming agent-message bodies are encrypted in retained traces. Plaintext ledgers are actual integrator observations; delivery metadata/hashes are verifiable, not plaintext decryption or full context equivalence.',
                         'Corrected filtered traces retain visible task messages; the earlier export missing those messages remains preserved as v1. Neither export is the full raw rollout.',
                         'Baseline charged active time includes23.683894211seconds for a failed agent-capacity delivery which did not reach the participant. It is conservatively retained and both charged totals are below1800seconds.',
                         'First work progressed T01 through T06. Baseline later revisited T01/T02 for public feedback after earlier infrastructure/diagnostic delays; public feedback order is not the same as first-work order.',
                         'T05 failed in both conditions at outsider-granted. Claimed-author was killed; everyone-granted and claim-must-match were not run after that task failure. No missing subject is marked passed.',
                         'Native Hoon unit evaluation and pinned Gall with explicit synthetic routing/clock are not four-process identity, live Ames/UDP or production authorization evidence.',
                         'T03 compares complete vases natively, but transported type/tang evidence contains native size/hash measurements rather than reconstructed omitted bodies.',
                         'Installed Clay evidence is a measured file projection and typed metadata readbacks. A complete Clay tree digest was not observed and remains null.',
                         'The frozen protocol retains its original prepared-state text; execution is established by these later records, not by editing the frozen package.',
                         'Independent trace/timing review cleared within these limits; T05 qualification is invalid for missing mutation cases. URB-170 remains open pending a repaired version and fresh paired contexts.',
                         'No task/source changes, native runs or private repair attempts were made during this packaging.']}
    schema = document(REPO / 'tests/urbit/skill_evaluation/result.schema.json')
    check_shape(result, schema, schema)
    save(OUT / 'result.json', encoded(result))
    members = [{'archive_path': 'payload/' + name, 'original_path': name, 'bytes': len(raw), 'sha256': sha(raw),
                'classification': sorted(descriptions[name]), 'accessible_copy': accessible.get(name)}
               for name, raw in sorted(payload.items())]
    save(OUT / 'members.json', encoded({'protocol': 'stead.workflow-evidence-members/1', 'members': members,
                                      'file_count': len(members), 'uncompressed_bytes': sum(row['bytes'] for row in members)}))
    archive = OUT / 'evidence.tar.gz'
    with archive.open('xb') as output:
        with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0, compresslevel=6) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT) as tar:
                for row in members:
                    raw = payload[row['original_path']]
                    entry = tarfile.TarInfo(row['archive_path'])
                    entry.size, entry.mode, entry.mtime = len(raw), 0o400, 0
                    entry.uid = entry.gid = 0
                    entry.uname = entry.gname = ''
                    tar.addfile(entry, io.BytesIO(raw))
    require(all(read(REPO / name) == raw for name, raw in payload.items()), 'A selected original changed while packaging')
    with tarfile.open(archive, 'r:gz') as tar:
        actual = tar.getmembers()
        require([row.name for row in actual] == [row['archive_path'] for row in members], 'Archive member inventory differs')
        for member, row in zip(actual, members, strict=True):
            require(member.isfile() and member.size == row['bytes'] and sha(tar.extractfile(member).read()) == row['sha256'], 'Archive byte verification failed')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == HEAD, 'HEAD changed during packaging')
    output_files = []
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name != 'index.json':
            raw = read(path)
            output_files.append({'path': path.relative_to(REPO).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)})
    index = {'protocol': 'stead.workflow-evaluation-evidence/1', 'status': 'v1-incomplete-T05-invalid-two-missing-mutants',
             'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'prepared_by': '/root/independent_review',
             'source_commit': HEAD, 'package_sha256': PACKAGE, 'source_and_native_tests_executed_by_packager': False,
             'packaging_resources': {'cpu_max': cpu_max, 'affinity': [19], 'control_group': cg},
             'archive_format': 'gzip mtime0; sorted PAX tar regular files with uid/gid0, empty names, mode0400, mtime0; no links',
             'archive_members': len(members), 'archive_uncompressed_bytes': sum(row['bytes'] for row in members),
             'outputs': output_files, 'public_attempts': public_index, 'private_scores': private_index,
             'prequalification': prequal_refs, 'verification': {'archive_all_members_rehashed': True,
             'all_selected_originals_unchanged': True, 'result_schema_shape': True,
             'note': 'Artifact checks only; no Hoon, native, host-test or participant rerun.'},
             'omitted': ['Raw Codex rollout files, hidden reasoning, hidden system/developer content, unrelated sessions, tool caches, live/seed piers, empty lock files, unrelated isolation/probe workspaces.'],
             'path_rule': 'Output paths are repository-relative. Archive member names preserve original repository-relative paths under payload/. Extract only into a separate empty directory, never over a live workspace.'}
    save(OUT / 'index.json', encoded(index))
    print(json.dumps({'members': len(members), 'uncompressed_bytes': index['archive_uncompressed_bytes'],
                      'archive_bytes': archive.stat().st_size, 'index_sha256': sha(read(OUT / 'index.json')),
                      'result_sha256': sha(read(OUT / 'result.json'))}, indent=2))


if __name__ == '__main__':
    main()

"""URB-170 adapter; native prequalification is mandatory.

Call only inside the existing guarded supervisor. Mount the frozen package and
candidate inputs read-only. Candidate roots contain T01/... through T06/...;
T05 includes the immutable supplied library. prequalify=True instead selects
the frozen private references and mutations. No participant context is launched.

The host supplies the existing lifecycle/dojo/LOCK/LIVE/execution_check globals,
plus WORKFLOW_SOURCE_COMMIT (the actual commit, never a guessed SHA). Include
this module and its imported helpers in the supervisor's eager source closure.
The integrator must bind the final outer guard report to this inner checkpoint;
this module cannot declare that a still-running outer guard completed.
For candidate scoring, WORKFLOW_PREQUALIFICATION must supply inner and guard
artifacts as {path, sha256}, mounted read-only from the prior completed run.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

import core_conn
import execution_policy
import conn
from digests import sha, source_sha

PACKAGE_SHA = 'd78697102021b4b4837efd2d560668310fad5ab69fcbf98c7592a9cd0fff3e00'
TASKS = ('T01', 'T02', 'T03', 'T04', 'T05', 'T06')
MAX_FILE = 65536
MAX_TOTAL = 1024 * 1024
MAX_OUTPUT = 1_000_000
MAX_JAM = 262144
FAILURE_PREFIX = 65536
ANSI = re.compile(r'\x1b\[[0-9;]*m')
T06_PLATFORM_BASELINE = ('mar/noun.hoon', 'mar/hoon.hoon', 'mar/txt.hoon',
                         'mar/kelvin.hoon', 'sys.kelvin')
T06_PLATFORM_ADDITIONS = ('mar/bill.hoon',)
T06_METADATA_CHECKS = {
    'desk.bill': '=(~ .^((list dude:gall) %cx /=skill-eval=/desk/bill))',
    'sys.kelvin': '=([%zuse 408] .^(waft:clay %cx /=skill-eval=/sys/kelvin))',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def closure():
    return {str(Path(module.__file__).resolve()): sha(module.__file__)
            for module in (core_conn, conn, execution_policy)} | {str(Path(__file__).resolve()): sha(__file__)}


LOADED_CLOSURE = closure()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def json_bytes(raw):
    def invalid(value):
        raise ValueError('Non-JSON numeric constant: ' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def files(root, *, maximum=64):
    root = Path(root).absolute()
    if any(path.is_symlink() for path in (root, *root.parents)) or not root.is_dir():
        raise ValueError('Input must be a real unredirected directory')
    result, entries, total = {}, 0, 0

    def visit(directory, depth=0):
        nonlocal entries, total
        if depth > 16:
            raise ValueError('Workflow directory depth bound')
        with os.scandir(directory) as listing:
            for entry in listing:
                entries += 1
                if entries > maximum * 8:
                    raise ValueError('Workflow directory entry bound')
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode):
                    visit(Path(entry.path), depth + 1)
                    continue
                if not stat.S_ISREG(mode):
                    raise ValueError('Link or special file in workflow inputs')
                if len(result) >= maximum:
                    raise ValueError('Workflow file count bound')
                allowance = min(MAX_FILE, MAX_TOTAL - total)
                descriptor = os.open(entry.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(descriptor, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError('Changed workflow file type')
                    raw = stream.read(allowance + 1)
                if len(raw) > allowance:
                    raise ValueError('Workflow per-file or cumulative byte bound')
                if b'\0' in raw or b'\r' in raw:
                    raise ValueError('Workflow source must be NUL-free LF text')
                raw.decode('utf-8', errors='strict')
                total += len(raw)
                result[Path(entry.path).relative_to(root).as_posix()] = raw

    visit(root)
    if not result:
        raise ValueError('Empty workflow input inventory')
    return result


def declared_gate(source, task):
    """Check the requested public declaration; native compilation checks its body.

    Whitespace and full/inline Hoon comments may vary. Both tasks explicitly
    require these faces/molds; removing or widening the declaration is not a
    correct finite-case solution.
    """
    source = '\n'.join(line.split('::', 1)[0] for line in source.splitlines())
    arm, sample = {'T01': ('add-u8', r'left=@ud\s+right=@ud'),
                   'T02': ('maybe-count', r'enabled=\?\s+count=@ud')}[task]
    pattern = (r'\+\+\s+' + arm + r'\s+\|=\s+\[' + sample
               + r'\]\s+\^-\s+\(unit\s+@ud\)(?=\s)')
    return arm_names(source) == [arm] and re.match(pattern, arm_block(source, arm)) is not None


def result_jam(stdout):
    """Bound decimal conversion before allocation, without changing int limits.

    Pinned pretty output uses @ud decimal with optional thousands separators.
    Converting chunks of 1,000 digits avoids Python's global decimal-string
    limit; the total decimal length and resulting bytes remain bounded.
    """
    if len(stdout) > MAX_OUTPUT:
        raise ValueError('Native result text bound')
    match = re.fullmatch(r'\s*\[\s*%skill-result\s+([0-9.]+)\s*\]\s*', stdout)
    if match is None:
        raise ValueError('Missing exact native result frame')
    printed = match[1]
    if not re.fullmatch(r'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)', printed):
        raise ValueError('Malformed native decimal atom')
    digits = printed.replace('.', '')
    if len(digits) > MAX_JAM * 8 * 30103 // 100000 + 1:
        raise ValueError('Native result decimal byte bound')
    atom = 0
    for start in range(0, len(digits), 1000):
        part = digits[start:start + 1000]
        atom = atom * 10 ** len(part) + int(part)
    size = max(1, (atom.bit_length() + 7) // 8)
    if size > MAX_JAM or atom == 0:
        raise ValueError('Native result jam byte bound or empty jam')
    return atom.to_bytes(size, 'little')


def compiler_rejection(exit_code, stdout, stderr):
    """Pinned Vere may print its compiler diagnostic on either output stream.

    A generic eval bail, timeout/signal, or result frame is not the expected
    starter type error. Keep this identical at execution and receipt admission.
    """
    streams = (stdout, stderr)
    return (type(exit_code) is int and exit_code >= 0
            and all(isinstance(stream, str) and len(stream) <= MAX_OUTPUT for stream in streams)
            and not any('%skill-result' in stream for stream in streams)
            and any(re.search(r'\b(?:nest-fail|mull-[a-z-]+|mint-[a-z-]+)\b', stream) for stream in streams))


def evaluate_source(binary, source, record):
    """Retain bounded raw evidence even for timeout/limit/UTF-8 failures."""
    argv = [str(binary), 'eval', '--loom', '29']
    record.update(argv=argv, timeout_seconds=30)
    try:
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                result = subprocess.run(argv, input=source.encode(), stdout=out,
                                        stderr=err, timeout=30, check=False)
                record['exit_code'] = result.returncode
            finally:
                record['stdout_bytes'] = out.seek(0, os.SEEK_END)
                record['stderr_bytes'] = err.seek(0, os.SEEK_END)
                out.seek(0)
                err.seek(0)
                output, diagnostics = out.read(MAX_OUTPUT + 1), err.read(MAX_OUTPUT + 1)
                record.update(stdout_prefix_hex=output[:FAILURE_PREFIX].hex(),
                              stderr_prefix_hex=diagnostics[:FAILURE_PREFIX].hex(),
                              stdout_prefix_complete=len(output) <= FAILURE_PREFIX,
                              stderr_prefix_complete=len(diagnostics) <= FAILURE_PREFIX)
        if len(output) > MAX_OUTPUT or len(diagnostics) > MAX_OUTPUT:
            raise ValueError('Native evaluator output bound exceeded')
        stdout = ANSI.sub('', output.decode('utf-8', errors='strict')).strip()
        stderr = ANSI.sub('', diagnostics.decode('utf-8', errors='strict')).strip()
        record.update(status='completed', stdout=stdout, stderr=stderr)
        return result.returncode, stdout, stderr
    except BaseException as error:
        record.update(status='failed', error=type(error).__name__ + ': ' + str(error),
                      timed_out=isinstance(error, subprocess.TimeoutExpired))
        raise


def hashes(mapping):
    return {name: digest(raw) for name, raw in sorted(mapping.items())}


def verify_package(root):
    content = files(root)
    freeze = json_bytes(content.pop('freeze.json'))
    actual = hashes(content)
    identity = digest(json.dumps(actual, sort_keys=True, separators=(',', ':')).encode())
    if (identity != PACKAGE_SHA or freeze.get('package_sha256') != PACKAGE_SHA
            or freeze.get('files') != actual or freeze.get('file_count') != 39):
        raise ValueError('Frozen skill corpus mismatch')
    oracles = json_bytes(content['reviewer/oracles.json'])
    if tuple(task['id'] for task in oracles['tasks']) != TASKS:
        raise ValueError('Exactly the six frozen tasks are required')
    return content, oracles


def verified_artifact(reference):
    if not isinstance(reference, dict) or not re.fullmatch(r'[a-f0-9]{64}', reference.get('sha256', '')):
        raise ValueError('Exact prior evidence reference required')
    path = Path(reference['path']).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Prior evidence path is redirected/missing/oversized')
    raw = path.read_bytes()
    if digest(raw) != reference['sha256']:
        raise ValueError('Prior evidence bytes changed')
    return json_bytes(raw)


def require_prequalification(host, current_policy, content, oracles):
    proof = host.get('WORKFLOW_PREQUALIFICATION')
    if not isinstance(proof, dict) or set(proof) != {'inner', 'guard'}:
        raise ValueError('Completed independent reference prequalification required before candidate scoring')
    inner = verified_artifact(proof['inner'])
    guard = verified_artifact(proof['guard'])
    if (inner.get('protocol') != 'stead.skill-native-adapter/1' or inner.get('status') != 'pass'
            or inner.get('prequalification') is not True or inner.get('condition') != 'prequalification'
            or inner.get('package_sha256') != PACKAGE_SHA or inner.get('loaded_closure') != LOADED_CLOSURE
            or inner.get('loaded_supervisor_source_sha256') != host['LOADED_SOURCE_DIGEST']
            or inner.get('toolchain_sha256') != sha('/toolchain.json')
            or not re.fullmatch(r'[a-f0-9]{40}', inner.get('source_commit', ''))
            or inner.get('loaded_closure_after') != LOADED_CLOSURE
            or guard.get('status') != 'completed' or guard.get('exit_code') != 0
            or guard.get('policy') != current_policy
            or guard.get('guard_sha256') != sha(execution_policy.__file__)
            or not guard.get('run_id') or inner.get('execution_guard', {}).get('run_id') != guard['run_id']):
        raise ValueError('Prior prequalification is incomplete, stale or bound to the wrong guard')
    validate_prequalification_execution(inner, content, oracles)
    return proof


def arm_matches(source):
    matches = list(re.finditer(r'^\+\+ {2,}([a-z][a-z0-9-]*)\b', source, re.M))
    # Native Hoon also permits gap spellings with comments/newlines. This
    # bounded adapter does not parse those; reject them instead of silently
    # omitting a legal arm from the claimed complete native test inventory.
    if len(matches) != len(re.findall(r'^\+\+', source, re.M)):
        raise ValueError('Unsupported top-level Hoon arm spelling; inventory cannot omit arms')
    return matches


def arm_names(source):
    names = [match[1] for match in arm_matches(source)]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate top-level Hoon arms')
    return names


def arm_skeleton(source, editable):
    matches = arm_matches(source)
    end = source.rfind('\n--')
    if not matches or end < matches[-1].start():
        raise ValueError('Missing Hoon arm inventory/terminator')
    out = source[:matches[0].start()]
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else end
        out += ('++  ' + match[1] + '\n<editable>\n') if match[1] in editable else source[match.start():stop]
    return out + source[end:]


def arm_block(source, name):
    matches = arm_matches(source)
    for index, match in enumerate(matches):
        if match[1] == name:
            end = matches[index + 1].start() if index + 1 < len(matches) else source.rfind('\n--')
            return source[match.start():end].rstrip()
    raise ValueError('Expected original test arm missing')


def select_inputs(content, root, prequalify, feedback_task=None):
    if feedback_task is not None:
        if prequalify or feedback_task not in TASKS:
            raise ValueError('Public feedback requires one explicit candidate task')
        return {feedback_task: files(root, maximum=8)}
    if not prequalify:
        all_files = files(root, maximum=32)
        if {name.split('/')[0] for name in all_files} != set(TASKS):
            raise ValueError('Candidate needs exactly T01 through T06 directories')
        return {task: {name.split('/', 1)[1]: raw for name, raw in all_files.items()
                       if name.startswith(task + '/')} for task in TASKS}
    selected = {}
    for task in TASKS[:5]:
        prefix = 'reviewer/reference/' + task + '/'
        selected[task] = {name[len(prefix):]: raw for name, raw in content.items() if name.startswith(prefix)}
    selected['T05']['lib/eval-authorization.hoon'] = content['public/starters/T05/lib/eval-authorization.hoon']
    selected['T05']['coverage.json'] = json.dumps({
        'missing_behavior': 'sender and untrusted claim cases',
        'added_arms': arm_names(selected['T05']['tests/eval-coverage.hoon'].decode())[2:],
        'why_existing_tests_miss_it': 'existing writer/stale tests both use the writer identity'}).encode()
    selected['T06'] = {'desk/' + name: content['public/starters/T06/source/' + original]
                       for name, original in (('lib/eval-desk.hoon', 'eval-desk.hoon'),
                           ('gen/eval-desk-probe.hoon', 'eval-desk-probe.hoon'),
                           ('sys.kelvin', 'sys.kelvin'), ('desk.bill', 'desk.bill'))}
    selected['T06']['assembly.json'] = json.dumps({
        'protocol': 'stead.eval-assembly/1', 'kelvin': 408,
        'kernel_commit': '5a187fededc4582a34fcd6055c67bb63e0917b94', 'dependencies': [],
        'files': {name.removeprefix('desk/'): digest(raw) for name, raw in selected['T06'].items()}}).encode()
    return selected


def task_plan(oracles, feedback_task=None):
    """Public feedback never constructs held-out cases or mutation programs."""
    tasks = copy.deepcopy(oracles['tasks'])
    if feedback_task is None:
        return tasks
    if feedback_task not in TASKS:
        raise ValueError('Unknown public feedback task')
    task = next(task for task in tasks if task['id'] == feedback_task)
    if feedback_task in ('T01', 'T02', 'T03'):
        task['cases'] = [case for case in task['cases'] if case.get('public') is True]
        if len(task['cases']) != 2:
            raise ValueError('Exactly the two frozen public examples are required')
    elif feedback_task == 'T04':
        if len(task['public_scenario']) != 2:
            raise ValueError('Exactly the frozen public Gall scenario is required')
        task.pop('private_scenario')
    elif feedback_task == 'T05':
        task['mutants'] = []
        task['classification'] = 'native_tests_correct_subject_only'
    return [task]


def public_feedback_projection(report):
    """Participant-safe public observations; never return reference/oracle proof."""
    if report.get('public_feedback') is not True or report.get('feedback_task') not in TASKS:
        raise ValueError('Only a public feedback run can be disclosed as feedback')
    name = report['feedback_task']
    rows = report.get('tasks', [])
    if len(rows) != 1 or rows[0].get('id') != name:
        raise ValueError('Public feedback cannot disclose other tasks')
    start = report.get('public_command_start')
    commands = report['commands'][start:] if type(start) is int and 0 <= start <= len(report['commands']) else []
    infrastructure_failure = (bool(report.get('cleanup_error') or report.get('final_binding_error')
                                   or report.get('native_execution_interrupted'))
                              or (report.get('status') != 'pass' and rows[0].get('status') != 'failed'))
    return {'protocol': 'stead.skill-public-feedback/1', 'status': report['status'],
            'condition': report['condition'], 'task': name, 'attempt': report['feedback_attempt'],
            'source_commit': report['source_commit'], 'package_sha256': report['package_sha256'],
            'candidate_files_sha256': report['candidate_files_sha256'],
            'toolchain_sha256': report['toolchain_sha256'], 'outer_guard_status': 'pending',
            'qualifies_phase': False, 'private_scoring': False,
            'scope': 'Only the submitted task and frozen public examples; no private cases or mutation feedback.',
            'tasks': copy.deepcopy(rows), 'commands': copy.deepcopy(commands),
            'checks': [copy.deepcopy(row) for row in report['checks'] if row['name'].startswith((name + ':', name + '-'))],
            'infrastructure_error': ('Public feedback incomplete; integrator must inspect the private execution record.'
                                     if infrastructure_failure else None)}


def valid_observation(record, label):
    if not isinstance(record, dict) or record.get('label') != label:
        return False
    encoded = record.get('actual_jam_hex')
    if (not isinstance(encoded, str) or not 0 < len(encoded) <= MAX_JAM * 2
            or len(encoded) % 2 or not re.fullmatch(r'[0-9a-f]+', encoded)):
        return False
    raw = bytes.fromhex(encoded)
    return (any(raw) and record.get('actual_jam_sha256') == digest(raw)
            and isinstance(record.get('actual_noun'), str) and bool(record['actual_noun'].strip())
            and len(record['actual_noun']) <= MAX_OUTPUT
            and isinstance(record.get('decode_stderr'), str))


def initial_saved_noun(record):
    return re.fullmatch(r'\s*\[\s*1\s+0\s+0\s*\]\s*', record.get('actual_noun', '')) is not None


def prequalification_inventory(content, oracles):
    inventory = {}
    for task in oracles['tasks']:
        name = task['id']
        if name in ('T01', 'T02'):
            cases = [case['id'] for case in task['cases']]
            labels = [name + '-' + case for case in cases]
        elif name == 'T03':
            cases = [case['id'] for case in task['cases']]
            labels = ['T03-all-load-cases']
        elif name == 'T04':
            cases = ['public-' + str(i) for i in range(len(task['public_scenario']))]
            cases += [case['id'] for case in task['private_scenario']]
            labels = ['T04-public-Gall', 'T04-private-Gall']
        elif name == 'T05':
            source = content['reviewer/reference/T05/tests/eval-coverage.hoon'].decode()
            cases = [arm for arm in arm_names(source) if arm.startswith('test-')]
            labels = ['T05-correct'] + ['T05-' + Path(path).stem for path in task['mutants']]
        else:
            cases = ['assembly-bytes', 'repeat-empty-assembly', 'native-clean-generator']
            labels = ['T06-native-clean-generator']
        inventory[name] = {'cases': cases, 'labels': labels, 'classification': task['classification']}
    return inventory


def validate_prequalification_execution(inner, content, oracles):
    """Validate retained execution inventory, separately from source/guard binding.

    This admits a prior evaluator record; it is not an independent rerun or an
    authenticity proof for arbitrary user-authored JSON. It rejects truncated,
    empty and internally inconsistent records even when their files are hashed.
    """
    inventory = prequalification_inventory(content, oracles)
    rows = inner.get('tasks')
    checks = inner.get('checks')
    commands = inner.get('commands')
    if (not isinstance(rows, list) or [row.get('id') for row in rows if isinstance(row, dict)] != list(TASKS)
            or not isinstance(checks, list) or not checks
            or any(not isinstance(check, dict) or not isinstance(check.get('name'), str)
                   or check.get('passed') is not True for check in checks)
            or not isinstance(commands, list) or not commands
            or any(not isinstance(command, dict) or command.get('status') != 'completed'
                   or command.get('kind') not in ('native-dojo', 'native-pure-evaluator', 'native-observed-noun')
                   for command in commands)):
        raise ValueError('Missing or nonpassing prequalification execution inventory')
    references = {task: hashes(value) for task, value in select_inputs(content, None, True).items()}
    generated = inner.get('generated_source_files_sha256')
    if (inner.get('candidate_files_sha256') != references or inner.get('candidate_inputs_after') != references
            or not isinstance(generated, dict) or not generated
            or any(not re.fullmatch(r'[a-f0-9]{64}', value) for value in generated.values())
            or inner.get('generated_source_files_after') != generated):
        raise ValueError('Missing or changed prequalification source inputs')
    required = {'loaded-adapter-closure-current', 'loaded-supervisor-current', 'actual-evaluator-controls',
                'T02-starter-rejection:actual-compiler-rejection', 'candidate-inputs-unchanged',
                'loaded-adapter-closure-still-current', 'loaded-supervisor-still-current',
                'all-six-native-tasks-passed', 'T01:declared-public-interface', 'T02:declared-public-interface',
                'T05:immutable-subject', 'T05:exact-test-imports', 'T05:nonempty-complete-arm-inventory',
                'T05:coverage-report', 'T06:exact-supplied-bytes', 'T06:exact-assembly-manifest',
                'T06:repeat-empty-assembly', 'T06:pinned-platform-baseline',
                'T06:exact-native-mounted-desk', 'T06:native-clean-generator-result',
                'loaded-clay-metadata:skill-eval:desk.bill',
                'loaded-clay-metadata:skill-eval:sys.kelvin'}
    diagnostics = inner.get('prequalification_diagnostics')
    initial_label = 'T03-initial-save-probe'
    if (not isinstance(diagnostics, dict) or set(diagnostics) != {initial_label}
            or not valid_observation(diagnostics[initial_label], initial_label)
            or not initial_saved_noun(diagnostics[initial_label])):
        raise ValueError('Missing actual initial-save diagnostic')
    required.add(initial_label + ':initial-saved-noun')
    result_records = []
    for row in rows:
        name, wanted = row['id'], inventory[row['id']]
        results = row.get('results')
        if (row.get('status') != 'passed' or row.get('classification') != wanted['classification']
                or row.get('expected_cases') != wanted['cases'] or row.get('observed_cases') != wanted['cases']
                or not isinstance(results, list) or len(results) != len(wanted['labels'])):
            raise ValueError('Incomplete prequalification task cases: ' + name)
        required.update((name + ':exact-file-inventory', name + ':nonzero-native-results'))
        if name in ('T03', 'T04'):
            required.update((name + ':ten-Gall-arms', name + ':only-authorized-arms-edited'))
        if name == 'T03':
            result_records.append(diagnostics[initial_label])
        if name == 'T05':
            mutants = [Path(path).stem for path in oracles['tasks'][4]['mutants']]
            if row.get('mutants') != mutants or row.get('requires_independent_test_semantics_review') is not True:
                raise ValueError('Incomplete behavioral mutant inventory')
            required.update('T05:original-arm-retained:' + arm for arm in oracles['tasks'][4]['preserved_test_arms'])
        for result, label in zip(results, wanted['labels'], strict=True):
            if name == 'T06':
                if result != {'label': label, 'actual_noun': '42'}:
                    raise ValueError('Missing native clean-desk result')
            elif not valid_observation(result, label):
                raise ValueError('Missing or corrupt actual native noun: ' + label)
            else:
                result_records.append(result)
    control = inner.get('failure_control')
    control_label = 'deliberate-false-native-expectation'
    if (not valid_observation(control, control_label) or control['actual_jam_hex'] == '02'
            or control['actual_noun'].strip() in ('0', '~')):
        raise ValueError('Nonempty deliberate native assertion failure required')
    result_records.insert(0, control)
    observed = [command for command in commands if command['kind'] == 'native-observed-noun']
    if observed != [{'kind': 'native-observed-noun', 'status': 'completed', **record} for record in result_records]:
        raise ValueError('Native observation command/result inventory mismatch')
    pure_labels = [control_label] + inventory['T01']['labels'] + inventory['T02']['labels'] + inventory['T05']['labels']
    pure = [command for command in commands if command['kind'] == 'native-pure-evaluator']
    if [command.get('label') for command in pure] != [control_label, 'T02-starter-rejection', *pure_labels[1:]]:
        raise ValueError('Missing actual evaluator/starter command inventory')
    for command in pure:
        label = command['label']
        if (command.get('input_sha256') != generated.get(label + '.hoon')
                or type(command.get('exit_code')) is not int
                or not isinstance(command.get('stdout'), str) or not isinstance(command.get('stderr'), str)):
            raise ValueError('Missing evaluator command evidence')
        if label == 'T02-starter-rejection':
            if not compiler_rejection(command['exit_code'], command['stdout'], command['stderr']):
                raise ValueError('Starter needs actual type/compiler rejection')
        else:
            expected_jam = next(record['actual_jam_hex'] for record in result_records if record['label'] == label)
            if (command['exit_code'] != 0 or 'eval: bail:' in command['stderr']
                    or result_jam(command['stdout']).hex() != expected_jam):
                raise ValueError('Native evaluator command/result disagrees')
    all_labels = [record['label'] for record in result_records]
    if set(generated) != {label + '.hoon' for label in [*all_labels, 'T02-starter-rejection']}:
        raise ValueError('Generated native source inventory mismatch')
    required.update(label + ':native-evaluator-success' for label in pure_labels)
    required.update(label + ':exact-nonempty-result-frame' for label in all_labels)
    if not required.issubset({check['name'] for check in checks}):
        raise ValueError('Required actual prequalification checks missing')
    if not any(command.get('kind') == 'native-dojo' and command.get('source') == '+skill-eval!eval-desk-probe'
               and command.get('stdout', '').strip() == '42' for command in commands):
        raise ValueError('Missing clean-desk native command')
    for name, source in T06_METADATA_CHECKS.items():
        if not any(command.get('kind') == 'native-dojo' and command.get('source') == source
                   and command.get('stdout', '').strip() == '%.y' for command in commands):
            raise ValueError('Missing actual typed desk metadata readback: ' + name)
    generators = [command for command in commands if command.get('kind') == 'native-dojo'
                  and command.get('source') == '+skill-eval-check']
    expected_generators = [record for record in result_records if record['label'].startswith(('T03-', 'T04-'))]
    if (len(generators) != len(expected_generators)
            or any(result_jam(command.get('stdout', '').strip()).hex() != record['actual_jam_hex']
                   for command, record in zip(generators, expected_generators, strict=True))):
        raise ValueError('Native generator command/result disagrees')
    controls = inner.get('evaluator_controls', {})
    invalid = controls.get('invalid_input', {})
    if (controls.get('status') != 'passed' or controls.get('classification') != 'real-native-evaluator'
            or type(controls.get('large_frame_bytes')) is not int or not 65536 < controls['large_frame_bytes'] <= MAX_OUTPUT
            or type(invalid.get('exit')) is not int or invalid['exit'] != 0 or invalid.get('encoder_rejected') is not True
            or not isinstance(invalid.get('stderr'), str) or not invalid['stderr'].strip()
            or not re.fullmatch(r'(?:[a-f0-9]{2})*', invalid.get('stdout_hex', '!'))
            or any(not re.fullmatch(r'[a-f0-9]{64}', controls.get(key, ''))
                   for key in ('large_frame_sha256', 'result_sha256'))):
        raise ValueError('Missing or malformed actual evaluator controls')


# Gall initialization/loading follows pinned Urbit lib/test/ames-gall.hoon,
# commit 5a187fededc4582a34fcd6055c67bb63e0917b94 (MIT; notice retained in the
# frozen toolchain and native_gall_schedule/UPSTREAM_LICENSE.txt). Real Gall
# creates bowl.src from each synthetic dispatched sack. No app state is edited.
GALL_PRELUDE = '''/=  gall-raw  /sys/vane/gall
/=  candidate  /app/eval-access
=/  gall-bunt  (gall-raw ~zod)
=>
|%
++  make-gall
  |=  who=ship
  =/  pupa  (gall-raw who)
  =/  adult  (pupa now=~2026.9.25 eny=`@`0xdead.beef scry=*roof)
  =+  [moves next]=(call:adult duct=~[/init] dud=~ task=[%init ~])
  ?>  =(~ moves)
  next
--
=/  gall-adult  (make-gall ~zod)
=>
|%
+$  machine  _gall-adult
+$  motion  move:gall-bunt
++  call
  |=  [state=machine return=duct input=(hobo task:gall)]
  (call:(state ~2026.9.25 `@`0xdead.beef *roof) return ~ input)
++  load
  =/  state  (make-gall ~zod)
  =^  moves  state
    (call state ~[/load] [%load [[%eval-access [~zod %base da+~2026.9.25] candidate] ~]])
  =/  response=sign-arvo
    :+  %clay  %writ
    `[[%a da+~2026.9.25 %base] /app/eval-access/hoon vase+!>(!>(candidate))]
  =^  ready  state
    (take:(state ~2026.9.25 `@`0xdead.beef *roof) /sys/cor/eval-access/~zod/base/(scot %da ~2026.9.25) ~[/load] ~ response)
  state
++  saved
  |=  state=machine
  =/  current  (state ~2026.9.25 `@`0xdead.beef *roof)
  =/  yoke  (~(got by yokes.state.current) %eval-access)
  ?>  ?=(%live -.yoke)
  ?>  ?=(%& -.agent.yoke)
  =/  observed  on-save:p.agent.yoke
  q.observed
--
:-  %say
|=  *
:-  %noun
'''


def t03_initial_program():
    """Small prequalification diagnostic; no full vase/type serialization."""
    return '''/=  candidate  /app/eval-counter
:-  %say
|=  *
:-  %noun
~&  [%stead-skill-t03-initial %body-enter]
=/  context=bowl:gall  *bowl:gall
=.  our.context  ~zod
=.  src.context  ~zod
=.  now.context  ~2026.9.25
=/  original=agent:gall  ~(. candidate context)
~&  [%stead-skill-t03-initial %agent-ready]
=/  initial=vase  on-save:original
~&  [%stead-skill-t03-initial %save-returned]
?>  =([%1 0 0] q.initial)
^-  [@tas @ud]
[%skill-result (jam q.initial)]
'''


def t03_program(task):
    # One fixed-sample gate avoids accumulating twelve inferred agent subjects.
    # Pinned lull ++agent/++form defines the interface; hoon ++mute virtualizes
    # the same thunk as ++mule without reconstructing its full success type.
    # Rejection-only checks need its real %| result, never a returned agent.
    # Full-vase comparisons stay native. Their compiler types and rejection
    # tangs are transported as native jam lengths/SHA-256 digests: prequal10
    # reached every assertion but produced a 1,325,984-byte full evidence jam.
    code = ['/=  candidate  /app/eval-counter', ':-  %say', '|=  *', ':-  %noun',
            '~&  [%stead-skill-t03 %body-enter]',
            '=/  context=bowl:gall  *bowl:gall', '=.  our.context  ~zod',
            '=.  src.context  ~zod', '=.  now.context  ~2026.9.25',
            '=/  original=agent:gall  ~(. candidate context)',
            '~&  [%stead-skill-t03 %initial-agent-ready]', '=/  initial=vase  on-save:original',
            '~&  [%stead-skill-t03 %initial-save-returned]',
            '?>  =([%1 0 0] q.initial)',
            '=/  view-saved',
            '  |=  saved=vase',
            '  ^-  [value=* type-bytes=@ud type-sha256=@ux]',
            '  =/  encoded-type=@  (jam p.saved)',
            '  [q.saved (met 3 encoded-type) (shax encoded-type)]',
            '=/  run-case',
            '  |=  [label=@t incoming=vase expected=* must-reject=? repeat-load=?]',
            '  ^-  *',
            '  ~&  [%stead-skill-t03 %case-begin label]',
            '  =/  agent=agent:gall  ~(. candidate context)',
            '  ~&  [%stead-skill-t03 %case-agent-ready label]']
    if any(case.get('expect_native_rejection') for case in task['cases']):
        code += ['  ?:  must-reject',
                 '    ~&  [%stead-skill-t03 %reject-setup-begin label]',
                 '    =+  [cards loaded]=(on-load:agent !>([%1 5 2]))',
                 '    ~&  [%stead-skill-t03 %reject-setup-loaded label]',
                 '    ?>  =(~ cards)', '    =/  before=vase  on-save:loaded',
                 '    ~&  [%stead-skill-t03 %mute-begin label]',
                 '    =/  rejected  (mute:vi |.((on-load:loaded incoming)))',
                 '    ~&  [%stead-skill-t03 %mute-returned label]',
                 '    ?>  ?=(%| -.rejected)', '    =/  after=vase  on-save:loaded',
                 '    ?>  =(before after)', '    ~&  [%stead-skill-t03 %case-checked label]',
                 '    =/  encoded-tang=@  (jam p.rejected)',
                 '    [label (view-saved before) [-.rejected (met 3 encoded-tang) (shax encoded-tang)] (view-saved after)]']
    else:
        code += ['  ?>  =(%.n must-reject)']
    code += ['  ~&  [%stead-skill-t03 %load-begin label]',
             '  =+  [cards loaded]=(on-load:agent incoming)',
             '  ~&  [%stead-skill-t03 %load-returned label]', '  ?>  =(~ cards)',
             '  =/  observed=vase  on-save:loaded',
             '  ~&  [%stead-skill-t03 %save-returned label]', '  ?>  =(expected q.observed)',
             '  ?:  repeat-load',
             '    ~&  [%stead-skill-t03 %roundtrip-load-begin label]',
             '    =+  [later-cards reloaded]=(on-load:loaded observed)',
             '    ~&  [%stead-skill-t03 %roundtrip-load-returned label]', '    ?>  =(~ later-cards)',
             '    =/  again=vase  on-save:reloaded', '    ?>  =(observed again)',
             '    ~&  [%stead-skill-t03 %case-checked label]', '    [label cards (view-saved observed)]',
             '  ~&  [%stead-skill-t03 %case-checked label]', '  [label cards (view-saved observed)]',
             '=/  evidence=(list *)', '  :~']
    for case in task['cases']:
        code += [f"    (run-case '{case['id']}' !>({case['load_noun']}) {case.get('saved_noun', '~')} "
                 + ('%.y' if case.get('expect_native_rejection') else '%.n') + ' '
                 + ('%.y' if case.get('repeat_load_saved_output') else '%.n') + ')']
    return '\n'.join(code + ['  ==', '~&  [%stead-skill-t03 %all-cases-checked]',
        '~&  [%stead-skill-t03 %jam-begin]', '=/  encoded=@ud  (jam evidence)',
        '=/  encoded-bytes=@ud  (met 3 encoded)',
        '~&  [%stead-skill-t03 %result-jam-bytes encoded-bytes]',
        f"?.  (lte encoded-bytes {format(MAX_JAM, ',').replace(',', '.')})",
        '  ~|  [%stead-skill-t03-result-jam-oversize encoded-bytes]', '  !!',
        '^-  [@tas @ud]', '[%skill-result encoded]']) + '\n'


def t04_program(scenario):
    code = [GALL_PRELUDE, '=/  engine  load', '?>  =([%0 0] (saved engine))',
            '=/  evidence=(list *)  ~']
    for index, case in enumerate(scenario):
        action = (f"%poke %{case['mark']} !>({case['noun']})" if case['kind'] == 'poke'
                  else '%watch ' + case['path'])
        code += [f"=^  moves  engine  (call engine ~[/skill/step-{index}] [%deal [{case['sender']} ~zod /skill/fixture] %eval-access {action}])",
                 '?>  (lte (lent moves) 3)']
        tag = 'poke-ack' if case['kind'] == 'poke' else 'watch-ack'
        ack = '~' if case['outcome'] == 'ack' else '^'
        code += [f"=/  acks  (skim moves |=(item=motion ?=([* %give %unto %{tag} {ack}] item)))",
                 '?>  =(1 (lent acks))',
                 '=/  facts  (skim moves |=(item=motion ?=([* %give %unto %fact *] item)))',
                 '=/  kicks  (skim moves |=(item=motion ?=([* %give %unto %kick ~] item)))',
                 f"?>  =({len(case.get('facts', []))} (lent facts))",
                 f"?>  =({case.get('kicks', 0)} (lent kicks))",
                 f"?>  =({1 + len(case.get('facts', [])) + case.get('kicks', 0)} (lent moves))"]
        if case.get('hint'):
            code += [f"?>  ?=(^ (find (trip '{case['hint']}') (trip (crip <moves>))))"]
        if case.get('facts'):
            code += ['?>  ?=(^ facts)', '=/  fact  i.facts',
                     '?>  ?=([* %give %unto %fact *] fact)',
                     '=/  [return=duct a=@ b=@ c=@ result=cage]  fact',
                     '?>  =(%noun p.result)',
                     f"?>  =({case['facts'][0]['noun']} !<(@ud q.result))"]
        code += [f"?>  =({case['saved_noun']} (saved engine))",
                 f"=.  evidence  [[{index} (saved engine) moves] evidence]"]
    return '\n'.join(code + ['^-  [@tas @ud]', '[%skill-result (jam (flop evidence))]']) + '\n'


def run(host, package_root, candidate_root, condition, *, prequalify=False,
        feedback_task=None, feedback_attempt=None):
    """Execute actual native tasks; caller owns guard, mounts and outer receipt.

    Returns status fail/pass for adapter execution only. A pass is pending outer
    guard completion, equal-context metadata and independent review. T04 runs
    actual pinned Gall with synthetic sacks/clock, never four-process identity.
    """
    if condition not in ('baseline', 'local_skill_assisted', 'prequalification') or (prequalify != (condition == 'prequalification')):
        raise ValueError('Explicit condition/prequalification pairing required')
    public = feedback_task is not None
    if (public and (prequalify or feedback_task not in TASKS or type(feedback_attempt) is not int
                    or feedback_attempt not in (1, 2, 3))) or (not public and feedback_attempt is not None):
        raise ValueError('Public feedback requires a candidate condition, task and attempt 1 through 3')
    if not re.fullmatch(r'[a-f0-9]{40}', host.get('WORKFLOW_SOURCE_COMMIT', '')):
        raise ValueError('Actual workflow source commit required from integrator')
    content, oracles = verify_package(package_root)
    plan = task_plan(oracles, feedback_task)
    names = [task['id'] for task in plan]
    candidates = select_inputs(content, candidate_root, prequalify, feedback_task)
    original = {task: hashes(value) for task, value in candidates.items()}
    started = time.monotonic()
    token = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + condition
    if public:
        token += '-public-' + feedback_task + '-' + str(feedback_attempt)
    report_path = Path(host['STATE']) / 'logs' / ('skill-evaluation-' + token + '.json')
    work = Path(host['STATE']) / 'logs' / ('skill-evaluation-' + token + '-inputs')
    work.mkdir(exist_ok=False)
    report = {'protocol': 'stead.skill-native-adapter/1', 'status': 'fail',
              'classification': 'native-unit-and-pinned-gall-synthetic-routing',
              'condition': condition, 'prequalification': prequalify,
              'public_feedback': public, 'feedback_task': feedback_task, 'feedback_attempt': feedback_attempt,
              'qualifies_phase': False, 'outer_guard_status': 'pending',
              'source_commit': host['WORKFLOW_SOURCE_COMMIT'], 'package_sha256': PACKAGE_SHA,
              'candidate_files_sha256': original, 'loaded_closure': LOADED_CLOSURE,
              'loaded_supervisor_source_sha256': host['LOADED_SOURCE_DIGEST'],
              'toolchain_sha256': sha('/toolchain.json'), 'checks': [], 'commands': [],
              'installed_clay_files': [], 'generated_source_files_sha256': {},
              'tasks': [{'id': name, 'status': 'not_run'} for name in names],
              'limits': ['Synthetic native fixture only; no browser/live-network/production proof.',
                         'Equal model/context/budget and independent review are external required evidence.']}
    binary = '/runtime/' + host['LOCK']['runtime']['binary']
    kernel = Path('/kernel')
    helper = (kernel / 'pkg/base-dev/lib/test.hoon').read_text()
    report['native_dependencies_sha256'] = {str(path): sha(path) for path in (
        kernel / 'pkg/base-dev/lib/test.hoon', kernel / 'pkg/base-dev/lib/default-agent.hoon',
        kernel / 'pkg/arvo/sys/vane/gall.hoon', kernel / 'pkg/arvo/lib/test/ames-gall.hoon')}

    def checkpoint(stage):
        report['stage'] = stage
        execution_policy.write_json(report_path, report)

    def check(name, passed):
        report['checks'].append({'name': name, 'passed': bool(passed)})
        if not passed:
            raise AssertionError(name)

    def command(source):
        host['execution_check']()
        record = {'kind': 'native-dojo', 'source': source, 'status': 'running'}
        report['commands'].append(record)
        checkpoint('before-native-dojo')
        try:
            raw = host['dojo']('zod', source)
            record.update(status='completed', stdout=raw)
        except Exception as error:
            record.update(status='failed', error=type(error).__name__ + ': ' + str(error))
            checkpoint('native-dojo-failed')
            raise
        checkpoint('native-execution')
        return raw.strip()

    def install(mapping, desk='base'):
        target = host['LIVE'] / 'zod' / desk
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Expected owned disposable desk mount missing')
        for name, raw in mapping.items():
            path = target / name
            if Path(name).is_absolute() or '..' in Path(name).parts or any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError('Redirected/escaping installed path')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            check('installed-file:' + desk + ':' + name, sha(path) == digest(raw))
        command('|commit %' + desk)
        readbacks = {}
        for name, raw in mapping.items():
            if desk == 'skill-eval' and name in T06_METADATA_CHECKS:
                # These marks store parsed nouns in Clay, not their source
                # text. Exact assembled/mounted bytes are checked separately.
                check('loaded-clay-metadata:' + desk + ':' + name,
                      command(T06_METADATA_CHECKS[name]) == '%.y')
                readbacks[name] = 'typed-native-noun'
                continue
            stem, suffix = name.rsplit('.', 1)
            if suffix != 'hoon':
                raise ValueError('No reviewed native readback for installed mark: ' + suffix)
            clay = '/' + stem + '/' + suffix
            atom = core_conn.atom(bytes.fromhex(digest(raw))[::-1])
            query = f'=/  raw=@t  .^(@t %cx /={desk}={clay})  =({atom} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))'
            check('loaded-clay-file:' + desk + ':' + name, command(query) == '%.y')
            readbacks[name] = 'native-text-sha256'
        report['installed_clay_files'].append({'desk': desk, 'files_sha256': hashes(mapping),
                                               'native_readback': readbacks})

    def native(source, label, *, rejection=False):
        host['execution_check']()
        path = work / (label + '.hoon')
        path.write_text(source)
        report['generated_source_files_sha256'][path.name] = digest(source.encode())
        record = {'kind': 'native-pure-evaluator', 'label': label, 'input_path': str(path),
                  'input_sha256': digest(source.encode()), 'status': 'running'}
        report['commands'].append(record)
        checkpoint('before-native-evaluator')
        try:
            exit_code, stdout, stderr = evaluate_source(binary, source, record)
        except BaseException:
            checkpoint('native-evaluator-failed')
            raise
        checkpoint('native-execution')
        host['execution_check']()
        if rejection:
            check(label + ':actual-compiler-rejection', compiler_rejection(exit_code, stdout, stderr))
            return record
        check(label + ':native-evaluator-success', exit_code == 0 and 'eval: bail:' not in stderr)
        return observe(stdout, label)

    def observe(stdout, label):
        raw = result_jam(stdout)
        check(label + ':exact-nonempty-result-frame', True)
        frame = b'\0' + len(raw).to_bytes(4, 'little') + raw
        record = {'label': label, 'actual_jam_hex': raw.hex(), 'actual_jam_sha256': digest(raw)}
        observed = {'kind': 'native-observed-noun', 'status': 'running', **record}
        report['commands'].append(observed)
        checkpoint('before-native-noun-decode')
        try:
            decoded, diagnostics = core_conn.evaluate(binary, '-cn', frame)
            record.update(actual_noun=decoded.decode('utf-8', errors='strict'),
                          decode_stderr=diagnostics.decode('utf-8', errors='strict'))
            observed.update(status='completed', **record)
        except BaseException as error:
            observed.update(status='failed', error=type(error).__name__ + ': ' + str(error),
                            decode_argv=[binary, 'eval', '--loom', '29', '-cn'],
                            timed_out=isinstance(error, subprocess.TimeoutExpired))
            for key, data in (('stdout', locals().get('decoded', getattr(error, 'output', b''))),
                              ('stderr', locals().get('diagnostics', getattr(error, 'stderr', b'')))):
                observed[key + '_prefix_hex'] = (data or b'')[:FAILURE_PREFIX].hex()
            if hasattr(error, 'eval_failure'):
                observed['evaluator_limit'] = error.eval_failure
            checkpoint('native-noun-decode-failed')
            raise
        checkpoint('native-execution')
        return record

    def generator(source, label):
        raw = source.encode()
        (work / (label + '.hoon')).write_bytes(raw)
        report['generated_source_files_sha256'][label + '.hoon'] = digest(raw)
        install({'gen/skill-eval-check.hoon': raw})
        result = command('+skill-eval-check')
        return observe(result, label)

    try:
        checkpoint('admission')
        lease = host['execution_check'](preflight=True)
        report['execution_guard'] = {key: lease[key] for key in ('run_id', 'generation', 'guard_sha256', 'policy_sha256', 'policy')}
        check('loaded-adapter-closure-current', closure() == LOADED_CLOSURE)
        check('loaded-supervisor-current', source_sha(Path(core_conn.__file__).parent) == host['LOADED_SOURCE_DIGEST'])
        if not prequalify:
            report['prior_prequalification'] = require_prequalification(host, lease['policy'], content, oracles)
        report['evaluator_controls'] = core_conn.evaluator_controls(binary)
        check('actual-evaluator-controls', report['evaluator_controls']['status'] == 'passed')
        host['all_stop']()
        host['copy_seed_to_live']()
        for ship in host['SHIPS']:
            host['launch'](ship)
            host['wait_ready'](ship)
        control = '=/  test\n' + helper + '\n=/  result  (expect:test !>(=(1 2)))\n?>  ?=(^ result)\n^-  [@tas @ud]\n[%skill-result (jam result)]\n'
        report['failure_control'] = native(control, 'deliberate-false-native-expectation')
        if prequalify:
            starter = content['public/starters/T02/lib/eval-maybe.hoon'].decode()
            native('=>\n' + starter + '\n(maybe-count %.y 7)\n', 'T02-starter-rejection', rejection=True)
        if public:
            report['public_command_start'] = len(report['commands'])
        for task, row in zip(plan, report['tasks'], strict=True):
            name, selected = task['id'], candidates[task['id']]
            checkpoint(name)
            try:
                allowed = set(task['editable_files'])
                if name == 'T05':
                    allowed.add('lib/eval-authorization.hoon')
                check(name + ':exact-file-inventory', set(selected) == allowed)
                if name in ('T03', 'T04'):
                    path = task['editable_files'][0]
                    text = selected[path].decode()
                    starter = content['public/starters/' + name + '/' + path].decode()
                    check(name + ':ten-Gall-arms', len(arm_names(text)) == 10)
                    check(name + ':only-authorized-arms-edited', arm_skeleton(text, task['editable_arms']) == arm_skeleton(starter, task['editable_arms']))
                if name != 'T06':
                    install({path: raw for path, raw in selected.items() if path.endswith('.hoon')})
                results = []
                if name in ('T01', 'T02'):
                    source = selected[task['editable_files'][0]].decode()
                    check(name + ':declared-public-interface', declared_gate(source, name))
                    arm = task['arm'].split(':')[0]
                    for case in task['cases']:
                        program = ('=>\n' + source + '\n' + f"=/  actual  ({arm} {case['sample']})\n"
                                   + f"?>  =({case['expected']} actual)\n^-  [@tas @ud]\n[%skill-result (jam actual)]\n")
                        results.append(native(program, name + '-' + case['id']))
                    row['expected_cases'] = [case['id'] for case in task['cases']]
                elif name == 'T03':
                    if prequalify:
                        label = name + '-initial-save-probe'
                        diagnostic = generator(t03_initial_program(), label)
                        report['prequalification_diagnostics'] = {label: diagnostic}
                        check(label + ':initial-saved-noun', initial_saved_noun(diagnostic))
                        checkpoint(label + '-passed')
                    results.append(generator(t03_program(task), name + '-all-load-cases'))
                    row['expected_cases'] = [case['id'] for case in task['cases']]
                elif name == 'T04':
                    results.append(generator(t04_program(task['public_scenario']), name + '-public-Gall'))
                    row['expected_cases'] = ['public-' + str(i) for i in range(len(task['public_scenario']))]
                    if not public:
                        results.append(generator(t04_program(task['private_scenario']), name + '-private-Gall'))
                        row['expected_cases'] += [case['id'] for case in task['private_scenario']]
                elif name == 'T05':
                    subject = selected['lib/eval-authorization.hoon']
                    check('T05:immutable-subject', subject == content[task['immutable_subject']])
                    tests = selected['tests/eval-coverage.hoon'].decode()
                    header, body = tests.split('\n', 1)
                    check('T05:exact-test-imports', header == '/+  *test, eval-authorization')
                    arms = tuple(arm for arm in arm_names(body) if arm.startswith('test-'))
                    minimum = len(task['preserved_test_arms']) if public else 4
                    check('T05:nonempty-complete-arm-inventory', len(arms) >= minimum and set(task['preserved_test_arms']).issubset(arms))
                    original_tests = content['public/starters/T05/tests/eval-coverage.hoon'].decode()
                    for original_arm in task['preserved_test_arms']:
                        check('T05:original-arm-retained:' + original_arm,
                              arm_block(tests, original_arm) == arm_block(original_tests, original_arm))
                    coverage = json_bytes(selected['coverage.json'])
                    check('T05:coverage-report', bool(coverage.get('missing_behavior')) and bool(coverage.get('why_existing_tests_miss_it'))
                          and set(coverage.get('added_arms', [])) == set(arms) - set(task['preserved_test_arms']))
                    subjects = [('correct', subject)] + [(Path(path).stem, content['reviewer/' + path]) for path in task['mutants']]
                    for label, actual_subject in subjects:
                        prefix = '=/  test\n' + helper + '\n=/  eval-authorization\n' + actual_subject.decode() + '\n=,  test\n=>\n' + body
                        values = '~[' + ' '.join("['" + arm + "' " + arm + ']' for arm in arms) + ']'
                        program = prefix + '\n=/  observed=(list [@t tang])  ' + values + '\n'
                        program += '=/  failures  (skim observed |=([name=@t result=tang] !=(~ result)))\n'
                        program += ('?>  =(~ failures)\n' if label == 'correct' else '?>  ?=(^ failures)\n')
                        program += '^-  [@tas @ud]\n[%skill-result (jam observed)]\n'
                        results.append(native(program, 'T05-' + label))
                    row['expected_cases'] = list(arms)
                    row['mutants'] = [label for label, _ in subjects[1:]]
                    row['requires_independent_test_semantics_review'] = True
                else:
                    expected = {path: content[source] for path, source in task['source_mapping'].items()}
                    check('T06:exact-supplied-bytes', all(selected[path] == raw for path, raw in expected.items()))
                    manifest = json_bytes(selected['assembly.json'])
                    wanted = {'protocol': task['manifest_protocol'], 'kernel_commit': task['kernel_commit'],
                              'kelvin': 408, 'dependencies': [],
                              'files': {name.removeprefix('desk/'): digest(raw) for name, raw in expected.items()}}
                    check('T06:exact-assembly-manifest', manifest == wanted)
                    for number in (1, 2):
                        stage = work / ('assembly-' + str(number))
                        stage.mkdir()
                        for path, raw in expected.items():
                            dest = stage / path.removeprefix('desk/')
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(raw)
                    check('T06:repeat-empty-assembly', files(work / 'assembly-1') == files(work / 'assembly-2') == {name.removeprefix('desk/'): raw for name, raw in expected.items()})
                    command('|new-desk %skill-eval')
                    command('|mount %skill-eval')
                    baseline = {name: (kernel / 'pkg/arvo' / name).read_bytes()
                                for name in T06_PLATFORM_BASELINE}
                    additions = {name: (kernel / 'pkg/arvo' / name).read_bytes()
                                 for name in T06_PLATFORM_ADDITIONS}
                    check('T06:pinned-platform-baseline', files(host['LIVE'] / 'zod/skill-eval') == baseline)
                    report['native_dependencies_sha256'].update(
                        {str(kernel / 'pkg/arvo' / name): digest(raw)
                         for name, raw in (baseline | additions).items()})
                    report['desk_platform'] = {
                        'classification': 'pinned-standard-platform-scaffold-not-candidate-files',
                        'initial_files_sha256': hashes(baseline),
                        'added_files_sha256': hashes(additions)}
                    # Establish the bill mark before importing desk.bill.
                    install(additions, 'skill-eval')
                    assembled = {name.removeprefix('desk/'): raw for name, raw in expected.items()}
                    install(assembled, 'skill-eval')
                    check('T06:exact-native-mounted-desk', files(host['LIVE'] / 'zod/skill-eval')
                          == baseline | additions | assembled)
                    report['desk_platform']['mounted_files_sha256'] = hashes(baseline | additions | assembled)
                    actual = command('+skill-eval!eval-desk-probe')
                    check('T06:native-clean-generator-result', actual == '42')
                    results.append({'label': 'T06-native-clean-generator', 'actual_noun': actual})
                    row['expected_cases'] = ['assembly-bytes', 'repeat-empty-assembly', 'native-clean-generator']
                check(name + ':nonzero-native-results', bool(results) and bool(row['expected_cases']))
                row.update(status='passed', classification=task['classification'], results=results,
                           observed_cases=list(row['expected_cases']))
            except Exception as error:
                row.update(status='failed', error=type(error).__name__ + ': ' + str(error))
                if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)):
                    # A timed-out Lens request may still be evaluating inside
                    # the ship. Do not queue another task on that uncertain
                    # runtime; retain the failure and immediately enter cleanup.
                    report['native_execution_interrupted'] = {'task': name, 'error': row['error']}
                    checkpoint(name + '-aborted-native-timeout')
                    raise
                host['execution_check']()
            checkpoint(name + '-finished')
        host['execution_check']()
        verify_package(package_root)
        check('candidate-inputs-unchanged', original == {task: hashes(value) for task, value in select_inputs(content, candidate_root, prequalify, feedback_task).items()})
        check('loaded-adapter-closure-still-current', closure() == LOADED_CLOSURE)
        check('loaded-supervisor-still-current', source_sha(Path(core_conn.__file__).parent) == host['LOADED_SOURCE_DIGEST'])
        check('selected-public-task-passed' if public else 'all-six-native-tasks-passed',
              [row['id'] for row in report['tasks']] == names and all(row['status'] == 'passed' for row in report['tasks']))
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        try:
            host['all_stop']()
        except Exception as error:
            report['status'] = 'fail'
            report['cleanup_error'] = type(error).__name__ + ': ' + str(error)
        try:
            verify_package(package_root)
            report['candidate_inputs_after'] = {task: hashes(value) for task, value in select_inputs(content, candidate_root, prequalify, feedback_task).items()}
            report['loaded_closure_after'] = closure()
            report['generated_source_files_after'] = hashes({path.name: path.read_bytes() for path in work.glob('*.hoon')})
            if (report['candidate_inputs_after'] != original or report['loaded_closure_after'] != LOADED_CLOSURE
                    or report['generated_source_files_after'] != report['generated_source_files_sha256']
                    or sha('/toolchain.json') != report['toolchain_sha256']
                    or source_sha(Path(core_conn.__file__).parent) != host['LOADED_SOURCE_DIGEST']):
                raise ValueError('Inputs or generated native probes changed during evaluation')
        except Exception as error:
            report['status'] = 'fail'
            report['final_binding_error'] = type(error).__name__ + ': ' + str(error)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        checkpoint('finished-pending-outer-guard' if report['status'] == 'pass' else 'failed')
    result = {'status': report['status'], 'qualifies_phase': False, 'outer_guard_status': 'pending',
            'condition': condition, 'error': report.get('error'),
            'tasks_passed': sum(row['status'] == 'passed' for row in report['tasks']),
            'evidence_file': '.piers/fakes/logs/' + report_path.name}
    if public:
        feedback = report_path.with_name(report_path.stem + '-feedback.json')
        execution_policy.write_json(feedback, public_feedback_projection(report))
        result['feedback_file'] = '.piers/fakes/logs/' + feedback.name
    return result

#!/usr/bin/env python3
"""Run original pure Hoon object builders against stock Git; no ship boot.

The pinned Vere evaluator compiles source with its ivory Hoon environment.
This verifies pure constructors and test arms, not Gall installation or state.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

import toolchain

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / 'native/core/desk/lib/stead-git.hoon'
TESTS = ROOT / 'native/core/desk/tests/stead-git.hoon'
ARMS = (
    'test-empty-blob', 'test-trailing-zero-blob', 'test-all-zero-blob',
    'test-blob-width-rejected', 'test-object-kind-rejected', 'test-empty-tree',
    'test-tree-byte-order', 'test-tree-duplicate-rejected', 'test-tree-path-rejected',
    'test-tree-uppercase-rejected', 'test-tree-uuid-version-rejected',
    'test-tree-oid-width-rejected', 'test-tree-at-bound', 'test-tree-over-bound-rejected',
    'test-oid-leading-zero-padding', 'test-commit-no-parent',
    'test-commit-invalid-principal-rejected', 'test-commit-zero-revision-rejected',
    'test-commit-parent-width-rejected', 'test-commit-time-overflow-rejected',
)
PRINCIPAL = '019939ba-4000-7000-8000-000000000102'
DOCUMENT = '019939ba-4000-7000-8000-000000000002'
SECOND = '019939bb-4000-7000-8000-000000000001'
TIMESTAMP = 1789171200
ANSI = re.compile(r'\x1b\[[0-9;]*m')
OBJECT_OUTPUT = re.compile(
    r'\[\s*~\.(blob|tree|commit)\s+~\.([0-9.]+)\s+'
    r'~\.0x([0-9a-f.]+)\s+~\.0x([0-9a-f.]+)\s*\]')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def literal(value):
    digits = format(value, 'x')
    groups = []
    while digits:
        groups.insert(0, digits[-4:])
        digits = digits[:-4]
    return '0x' + '.'.join(groups)


def parse_object(output):
    match = OBJECT_OUTPUT.fullmatch(output)
    if not match:
        raise ValueError('Native result is not one complete object tuple')
    kind, width, value, oid = match.groups()
    width, value, oid = int(width.replace('.', '')), int(value.replace('.', ''), 16), int(oid.replace('.', ''), 16)
    if width > 8388608 or value.bit_length() > 8 * width or oid.bit_length() > 160:
        raise ValueError('Native object outside explicit width bounds')
    return kind, value.to_bytes(width, 'little'), f'{oid:040x}'


def tree_bytes(entries):
    return b''.join(b'100644 ' + name.encode('ascii') + b'\0' + bytes.fromhex(oid)
                    for name, oid in sorted(entries, key=lambda item: item[0].encode('ascii')))


def tree_expression(entries):
    nouns = ' '.join("['" + name + "' " + literal(int(oid, 16)) + ']' for name, oid in entries)
    return '(make-tree ~[' + nouns + '])' if entries else '(make-tree ~)'


def commit_bytes(tree, parent, timestamp=TIMESTAMP, revision=1):
    identity = f'Stead Fixture <{PRINCIPAL}@stead.invalid> {timestamp} +0000\n'
    return (f'tree {tree}\n' + (f'parent {parent}\n' if parent else '')
            + 'author ' + identity + 'committer ' + identity
            + f'\nSave {DOCUMENT} revision {revision}\n').encode('ascii')


def commit_expression(tree, parent, timestamp=TIMESTAMP, revision=1):
    parent_noun = '[~ ' + literal(int(parent, 16)) + ']' if parent else '~'
    return (f'(make-commit {literal(int(tree, 16))} {parent_noun} '
            f"'{PRINCIPAL}' {timestamp:,} '{DOCUMENT}' {revision:,})").replace(',', '.')


def main():
    allowed = {'https://github.com/ScottTpirate/stead-urbit.git', 'git@github.com:ScottTpirate/stead-urbit.git'}
    for options in ([], ['--push']):
        remote = subprocess.check_output(['git', 'remote', 'get-url', *options, 'origin'], cwd=ROOT, text=True).strip()
        if remote not in allowed:
            raise ValueError('Origin is not the authorized derivative')
    lock = toolchain.verify()
    binary = toolchain.CACHE / lock['runtime']['binary']
    helper_path = toolchain.CACHE / lock['kernel']['directory'] / 'pkg/base-dev/lib/test.hoon'
    library, tests, helper = LIBRARY.read_text(), TESTS.read_text(), helper_path.read_text()
    header, tests_body = tests.split('\n', 1)
    if header != '/+  *test, stead-git' or tuple(re.findall(r'^\+\+  (test-[a-z-]+)$', tests, re.M)) != ARMS:
        raise ValueError('Missing or unexpected Hoon test arm/header')
    prefix = '=>\n' + library + '\n'
    tests_prefix = '=/  test\n' + helper + '\n=/  stead-git\n' + library + '\n=,  test\n=>\n' + tests_body + '\n'
    base = ROOT / '.runtime/git-object-vectors'
    if any(path.is_symlink() for path in (base, *base.parents)):
        raise ValueError('Redirected fixture directory')
    if subprocess.run(['git', 'check-ignore', '-q', '.runtime/git-object-vectors/probe'], cwd=ROOT).returncode:
        raise ValueError('Fixture directory must be ignored')
    base.mkdir(mode=0o700, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=base))
    (run / '.stead-disposable.json').write_text(json.dumps({'format': 1, 'purpose': 'pure Git-object vectors; no pier'}) + '\n')
    print('Evidence: ' + str(run), flush=True)
    cpu = max(os.sched_getaffinity(0))
    records, checks = [], []
    report = {'status': 'failed', 'scope': 'real local pure Hoon and stock Git; no Gall/HTTP/live-network test',
              'checks': checks, 'sources_sha256': {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in (LIBRARY, TESTS, Path(__file__))},
              'toolchain_lock_sha256': sha256(toolchain.LOCK_PATH.read_bytes()),
              'native_test_helper_sha256': sha256(helper_path.read_bytes()), 'cpu_affinity': [cpu],
              'loom_exponent': 29, 'uname': list(os.uname())}
    git_env = {'PATH': '/usr/bin', 'HOME': str(run / 'empty-home'), 'LANG': 'C.UTF-8',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}
    (run / 'empty-home').mkdir()

    def check(name, passed, **details):
        checks.append({'name': name, 'passed': bool(passed), **details})
        if not passed:
            raise AssertionError(name)

    def native(source, label):
        started = time.monotonic()
        result = subprocess.run([str(binary), 'eval', '--loom', '29'], input=source.encode(),
                                capture_output=True, timeout=30,
                                preexec_fn=lambda: os.sched_setaffinity(0, {cpu}))
        output = ANSI.sub('', result.stdout.decode()).strip()
        error = ANSI.sub('', result.stderr.decode()).strip()
        records.append({'kind': 'pure-native', 'label': label, 'argv': [str(binary.relative_to(ROOT)), 'eval', '--loom', '29'],
                        'source_sha256': sha256(source.encode()), 'exit_code': result.returncode,
                        'stdout': output, 'stderr': error, 'elapsed_seconds': round(time.monotonic() - started, 3)})
        return output, result.returncode == 0 and 'eval: bail:' not in error

    def git(*args, input=None):
        command = ['/usr/bin/git', '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null', *args]
        result = subprocess.run(command, input=input, capture_output=True, cwd=run, env=git_env, timeout=30)
        records.append({'kind': 'stock-git', 'argv': command, 'input_sha256': sha256(input) if input is not None else None,
                        'exit_code': result.returncode, 'stdout': result.stdout.decode(errors='backslashreplace'),
                        'stderr': result.stderr.decode(errors='backslashreplace')})
        if result.returncode:
            raise RuntimeError('Stock Git command failed')
        return result.stdout

    objects = []

    def object_case(name, expression, kind, expected):
        source = (prefix + '=/  value  ' + expression + '\n^-  [@ta @ta @ta @ta]\n'
                  + '[(scot %tas kind.value) (scot %ud length.body.value) (scot %ux data.body.value) (scot %ux oid.value)]\n')
        output, valid = native(source, name)
        if not valid:
            raise ValueError('Native constructor failed: ' + name)
        actual_kind, body, oid = parse_object(output)
        stock_oid = git('--git-dir=objects.git', 'hash-object', '-t', kind, '--stdin', input=expected).decode().strip()
        check(name, actual_kind == kind and body == expected and oid == stock_oid,
              kind=kind, bytes=len(body), oid=oid, body_sha256=sha256(body))
        written = git('--git-dir=objects.git', 'hash-object', '-w', '-t', kind, '--stdin', input=body).decode().strip()
        recovered = git('--git-dir=objects.git', 'cat-file', kind, written)
        check(name + '-stock-roundtrip', written == oid and recovered == body)
        objects.append({'name': name, 'kind': kind, 'body_hex': body.hex(), 'oid': oid})
        return oid

    try:
        git('init', '--bare', '--template=', '--initial-branch=main', 'objects.git')
        for arm in ARMS:
            output, valid = native(tests_prefix + arm + '\n', arm)
            check(arm, valid and output == '~', output=output)
        output, valid = native(tests_prefix + 'failure-control\n', 'deliberately failing tang control')
        check('failing-tang-control-detected', valid and output != '~' and 'expected' in output and 'actual' in output)
        output, valid = native('(invalid-unterminated\n', 'deliberately invalid compiler control')
        check('compiler-failure-control-detected', not valid and 'syntax error' in output)
        blobs = {}
        bodies = {'empty': b'', 'trailing-zero': b'a\0', 'all-zero': b'\0\0',
                  'binary': b'\xff\0\x01\0', 'markdown': b'---\nid: synthetic\n---\nSnowman: \xe2\x98\x83\n'}
        for edge in ('leading', 'trailing'):
            for counter in range(4096):
                body = f'OID {edge} zero vector {counter}\n'.encode()
                digest = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).digest()
                if digest[0 if edge == 'leading' else -1] == 0:
                    bodies['oid-' + edge + '-zero'] = body
                    break
            else:
                raise ValueError('Bounded edge vector search exhausted')
        for name, body in bodies.items():
            expression = f'(make-blob [{len(body)} {literal(int.from_bytes(body, "little"))}])'
            blobs[name] = object_case('blob-' + name, expression, 'blob', body)
        empty_tree = object_case('tree-empty', '(make-tree ~)', 'tree', b'')
        entries = [(SECOND + '.md', blobs['oid-trailing-zero']), (DOCUMENT + '.md', blobs['oid-leading-zero'])]
        tree = object_case('tree-byte-order', tree_expression(entries), 'tree', tree_bytes(entries))
        object_case('tree-reversed-input', tree_expression(list(reversed(entries))), 'tree', tree_bytes(entries))
        wide = [(f'019939ba-4000-7000-8000-{index:012x}.md', blobs['empty']) for index in range(32)]
        object_case('tree-32-entries', tree_expression(list(reversed(wide))), 'tree', tree_bytes(wide))
        first = object_case('commit-first', commit_expression(empty_tree, None), 'commit', commit_bytes(empty_tree, None))
        second = object_case('commit-parent', commit_expression(tree, first, revision=2), 'commit', commit_bytes(tree, first, revision=2))
        object_case('commit-decimal-fields', commit_expression(tree, second, timestamp=0, revision=1000), 'commit', commit_bytes(tree, second, timestamp=0, revision=1000))
        git('--git-dir=objects.git', 'update-ref', 'refs/heads/main', second)
        git('--git-dir=objects.git', 'fsck', '--full', '--strict')
        check('native-object-graph-stock-fsck', True, expected_notice='extra vectors may be dangling objects')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
    finally:
        (run / 'commands.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records))
        (run / 'objects.json').write_text(json.dumps(objects, indent=2) + '\n')
        (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        (run / 'SHA256SUMS.json').write_text(json.dumps({p.name: sha256(p.read_bytes()) for p in sorted(run.iterdir()) if p.is_file()}, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'passed': sum(item['passed'] for item in checks),
                      'checks': len(checks), 'evidence': str(run)}, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

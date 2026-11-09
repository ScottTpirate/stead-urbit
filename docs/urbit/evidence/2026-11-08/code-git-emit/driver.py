#!/usr/bin/env python3
"""Fixed guarded native emitter vectors and stock-Git readback. No ship boot."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import code_git_vectors as vectors
import execution_policy

ROOT = Path(__file__).resolve().parent.parent.parent
ARMS = (
    'test-emit-empty-pack', 'test-emit-blob-golden', 'test-emit-ordinary-kinds',
    'test-emit-deterministic-order', 'test-emit-reject-declared-hash', 'test-emit-reject-wide-oid',
    'test-emit-reject-duplicate', 'test-emit-reject-kind', 'test-emit-reject-body-width',
    'test-emit-reject-body-bound', 'test-emit-count-at-bound', 'test-emit-count-over-bound',
    'test-emit-size-at-bound', 'test-emit-size-over-bound', 'test-emit-header-empty-kinds',
    'test-emit-header-first-boundary', 'test-emit-header-next-boundary', 'test-emit-header-size-bound',
    'test-emit-adler-empty', 'test-emit-adler-known', 'test-emit-adler-width',
    'test-emit-zlib-empty', 'test-emit-zlib-literal', 'test-emit-zlib-trailing-zero',
    'test-emit-zlib-all-zero', 'test-emit-zlib-last-full-block', 'test-emit-zlib-split-block',
    'test-emit-zlib-over-bound',
)
EXTRA = ('failing-tang-control-detected', 'compiler-failure-control-detected',
         'native-pack-sha1-envelope', 'stock-index-pack-accepts-native-bytes',
         'stock-fsck-native-objects', 'stock-exact-object-inventory',
         'stock-exact-blob-bytes-and-oid', 'stock-exact-tree-bytes-and-oid',
         'stock-exact-commit-bytes-and-oid', 'stock-exact-tag-bytes-and-oid',
         'stock-rejects-corrupt-native-trailer')
EXPECTED = ARMS + EXTRA
IMPORTS = {
    'stead-git': '',
    'stead-code-git-objects': '/+  stead-git\n',
    'stead-code-git-pack': '',
    'stead-code-git-emit': '/+  stead-git, stead-code-git-objects\n',
}
TESTS = 'native/core/desk/tests/stead-code-git-emit.hoon'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fixture():
    """Independent exact bytes/OIDs, not objects returned by the Hoon helper."""
    objects = {}
    def add(kind, body):
        oid = hashlib.sha1(kind.encode() + b' ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        objects[oid] = (kind, body)
        return oid
    add('blob', b'a\0\0')
    tree = add('tree', b'')
    commit = add('commit', (f'tree {tree}\nauthor Fixture <fixture@example.invalid> 0 +0000\n'
        'committer Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic pack fixture\n').encode())
    tag = add('tag', (f'object {commit}\ntype commit\ntag v1\n'
        'tagger Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic annotated tag\n').encode())
    return objects, commit, tag


def prefix():
    value = '=/  test\n' + Path('/input/test-helper.hoon').read_text() + '\n'
    for name, declaration in IMPORTS.items():
        body = Path(f'/input/{name}.hoon').read_text()
        found = re.findall(r'^/\+  .*\n', body, re.M)
        require(found == ([declaration] if declaration else []), 'Unexpected library imports')
        value += f'=/  {name}\n' + body.replace(declaration, '', 1) if declaration else f'=/  {name}\n' + body
        value += '\n'
    tests = Path('/input/tests.hoon').read_text()
    declaration, body = tests.split('\n', 1)
    require(declaration == '/+  *test, stead-git, stead-code-git-objects, stead-code-git-pack, stead-code-git-emit', 'Unexpected tests import')
    require(tuple(re.findall(r'^\+\+  (test-[a-z0-9-]+)$', tests, re.M)) == ARMS
            and tests.count('++  failure-control\n') == 1, 'Unexpected native test inventory')
    return value + '=,  test\n=>\n' + body + '\n'


def inside():
    execution_policy.require_lease(Path('/execution'), read_only=True)
    report = {'status': 'failed', 'scope': 'pure native outbound SHA-1 packs and stock Git readback; no service or accepted write',
              'qualifies_phase': False, 'checks': [], 'records': []}
    def check(name, passed, **details):
        report['checks'].append({'name': name, 'passed': bool(passed), **details})
        require(passed, 'Failed check: ' + name)
    def native(source, label):
        execution_policy.require_lease(Path('/execution'), read_only=True)
        require(len(source.encode()) <= vectors.MAX_OUTPUT, 'Native source bound')
        Path('/output/' + label + '.hoon').write_text(source)
        try:
            result = subprocess.run(['/runtime/vere', 'eval', '--loom', '29'], input=source.encode(), capture_output=True, timeout=40)
        except subprocess.TimeoutExpired as error:
            report['records'].append({'kind': 'native', 'label': label, 'timeout_seconds': 40,
                'stdout': (error.stdout or b'')[:vectors.MAX_OUTPUT].decode(errors='replace'),
                'stderr': (error.stderr or b'')[:vectors.MAX_OUTPUT].decode(errors='replace')})
            raise
        require(len(result.stdout) + len(result.stderr) <= vectors.MAX_OUTPUT, 'Native output bound')
        stdout, stderr = (vectors.ANSI.sub('', raw.decode()).strip() for raw in (result.stdout, result.stderr))
        report['records'].append({'kind': 'native', 'label': label, 'source_sha256': vectors.digest(source.encode()),
            'exit_code': result.returncode, 'stdout': stdout, 'stderr': stderr})
        execution_policy.require_lease(Path('/execution'), read_only=True)
        return stdout, result.returncode == 0 and 'eval: bail:' not in stderr
    def git(*args, data=None, rejected=False):
        execution_policy.require_lease(Path('/execution'), read_only=True)
        environment = {'HOME': '/tmp/empty-home', 'PATH': '/usr/bin', 'LANG': 'C.UTF-8',
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_REPLACE_OBJECTS': '1'}
        command = ['/runtime/git', '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null', *args]
        result = subprocess.run(command, input=data, capture_output=True, timeout=10, env=environment)
        require(len(result.stdout) + len(result.stderr) <= vectors.MAX_OUTPUT, 'Stock output bound')
        report['records'].append({'kind': 'stock-git', 'argv': command, 'input_sha256': vectors.digest(data) if data is not None else None,
            'exit_code': result.returncode, 'stdout_hex': result.stdout.hex(), 'stderr': result.stderr.decode()})
        require(rejected or result.returncode == 0, 'Stock Git failed')
        return result
    try:
        source = prefix()
        names = ARMS + ('failure-control',)
        expression = '^-  (list [@ta @ta])\n:~  ' + '\n    '.join(f'[(scot %tas %{name}) (scot %ud (lent {name}))]' for name in names) + '\n==\n'
        output, valid = native(source + expression, 'unit-inventory')
        rows = vectors.parse_rows(output, 2) if valid else []
        require(tuple(name for name, _ in rows) == names, 'Native compiler/result inventory differs')
        for name, count in rows[:-1]:
            check(name, count == '0', tang_lines=count)
        check(EXTRA[0], re.fullmatch(r'[1-9][0-9]*', rows[-1][1]) is not None)
        output, valid = native('(invalid-unterminated\n', 'invalid-compiler-control')
        check(EXTRA[1], not valid and 'syntax error' in output)
        output, valid = native(source + '=/  pack  interoperability\n^-  (list [@ta @ta])\n~[[(scot %ud length.pack) (scot %ux data.pack)]]\n', 'emitted-pack')
        rows = vectors.parse_rows(output, 2) if valid else []
        require(len(rows) == 1, 'Native emitted pack missing')
        pack = vectors.native_bytes(*rows[0])
        Path('/output/native.pack').write_bytes(pack)
        check(EXTRA[2], pack[:12] == b'PACK\0\0\0\2\0\0\0\4' and hashlib.sha1(pack[:-20]).digest() == pack[-20:])
        objects, commit, tag = fixture()
        git('init', '--bare', '--template=', '--object-format=sha1', '--initial-branch=main', '/work/export.git')
        indexed = git('--git-dir=/work/export.git', 'index-pack', '--stdin', '--strict', data=pack)
        check(EXTRA[3], indexed.stdout == b'pack\t' + pack[-20:].hex().encode() + b'\n')
        git('--git-dir=/work/export.git', 'update-ref', 'refs/heads/main', commit)
        git('--git-dir=/work/export.git', 'update-ref', 'refs/tags/v1', tag)
        fsck = git('--git-dir=/work/export.git', 'fsck', '--full', '--strict')
        check(EXTRA[4], fsck.returncode == 0)
        inventory = git('--git-dir=/work/export.git', 'cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype) %(objectsize)').stdout.decode().splitlines()
        check(EXTRA[5], sorted(inventory) == sorted(f'{oid} {kind} {len(body)}' for oid, (kind, body) in objects.items()))
        for kind in ('blob', 'tree', 'commit', 'tag'):
            oid, (_, expected) = next((oid, value) for oid, value in objects.items() if value[0] == kind)
            body = git('--git-dir=/work/export.git', 'cat-file', kind, oid).stdout
            check(f'stock-exact-{kind}-bytes-and-oid', body == expected
                  and hashlib.sha1(kind.encode() + b' ' + str(len(body)).encode() + b'\0' + body).hexdigest() == oid,
                  oid=oid, bytes=len(body))
        corrupted = pack[:-1] + bytes([pack[-1] ^ 1])
        rejected = git('--git-dir=/work/export.git', 'index-pack', '--stdin', '--strict', data=corrupted, rejected=True)
        check(EXTRA[-1], rejected.returncode > 0)
        report['status'] = 'passed'
        vectors.validate_report(report, EXPECTED)
    finally:
        Path('/output/report.json').write_text(json.dumps(report, indent=2) + '\n')


def main():
    import toolchain
    for flags in ([], ['--push']):
        require(subprocess.check_output(['git', 'remote', 'get-url', *flags, 'origin'], cwd=ROOT, text=True).strip()
                in {'https://github.com/ScottTpirate/stead-urbit.git', 'git@github.com:ScottTpirate/stead-urbit.git'}, 'Wrong derivative remote')
    lock = toolchain.verify()
    git_binary = Path(shutil.which('git')).resolve(strict=True)
    base = ROOT / '.runtime/code-git-emit'
    require(not any(path.is_symlink() for path in (base, *base.parents)), 'Redirected diagnostic path')
    require(subprocess.run(['git', 'check-ignore', '-q', str(base / 'probe')], cwd=ROOT).returncode == 0, 'Diagnostic path must be ignored')
    base.mkdir(mode=0o700, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=base))
    for name in ('input', 'output', 'code', 'work'):
        (run / name).mkdir(mode=0o700)
    helper = toolchain.CACHE / lock['kernel']['directory'] / 'pkg/base-dev/lib/test.hoon'
    copies = [(ROOT / f'native/core/desk/lib/{name}.hoon', f'input/{name}.hoon') for name in IMPORTS]
    copies += [(ROOT / TESTS, 'input/tests.hoon'), (helper, 'input/test-helper.hoon'),
               (Path(__file__), 'code/code_git_emit_check.py'), (Path(vectors.__file__), 'code/code_git_vectors.py'),
               (Path(execution_policy.__file__), 'code/execution_policy.py')]
    before = {str(source): vectors.digest(source.read_bytes()) for source, _ in copies}
    for source, target in copies:
        with (run / target).open('xb') as stream:
            stream.write(source.read_bytes())
    inputs = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'before': before, 'toolchain_sha256': vectors.digest(toolchain.LOCK_PATH.read_bytes()),
              'git_sha256': vectors.digest(git_binary.read_bytes()), 'git_version': lock['host_tools']['git'],
              'expected': EXPECTED, 'scope': 'pure native emitter and stock readback; no ship boot, route, or accepted write'}
    execution_policy.write_json(run / '.stead-disposable.json', {'format': 1, 'purpose': 'fixed bounded emitter diagnostic'})
    execution_policy.write_json(run / 'inputs.json', inputs)
    print('Evidence: ' + str(run), flush=True)
    def command(control, run_id):
        return ['/usr/bin/bwrap', '--unshare-all', '--new-session', '--clearenv', '--ro-bind', '/usr', '/usr',
            '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64', '--symlink', 'usr/bin', '/bin',
            '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/tmp/empty-home',
            '--setenv', 'HOME', '/tmp/empty-home', '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'PATH', '/usr/bin',
            '--setenv', 'STEAD_EXECUTION_ID', run_id, '--ro-bind', str(control), '/execution',
            '--ro-bind', str(run / 'code'), '/code', '--ro-bind', str(run / 'input'), '/input',
            '--bind', str(run / 'output'), '/output', '--bind', str(run / 'work'), '/work',
            '--ro-bind', str(git_binary), '/runtime/git', '--ro-bind', str(toolchain.CACHE / lock['runtime']['binary']), '/runtime/vere',
            '--chdir', '/work', '/usr/bin/python3', '/code/code_git_emit_check.py', '_inside']
    with (run / 'console.log').open('xb') as console:
        guard = execution_policy.run_guarded(command, root=ROOT, label='code-git-emit', timeout=120, console=console)
    inputs['guard_report'] = guard['run_directory'] + '/report.json'
    inputs['after'] = {str(source): vectors.digest(source.read_bytes()) for source, _ in copies}
    execution_policy.write_json(run / 'inputs.json', inputs)
    require(guard['status'] == 'completed' and inputs['before'] == inputs['after'], 'Native guard/source check failed')
    report = execution_policy.read_json(run / 'output/report.json', maximum=vectors.MAX_OUTPUT)
    vectors.validate_report(report, EXPECTED)
    print(f'PASS {len(EXPECTED)} checks; native emitter/stock readback only', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['_inside']:
        inside()
    elif sys.argv[1:]:
        raise SystemExit('No caller-selected inputs or commands are accepted')
    else:
        main()

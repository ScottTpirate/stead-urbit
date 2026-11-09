#!/usr/bin/env python3
"""Fixed guarded native fetch selection and stock-Git readback. No ship boot."""
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
ARMS = ('test-fetch-round-nak', 'test-fetch-round-ack', 'test-fetch-round-first-common', 'test-fetch-round-unknown-have', 'test-fetch-round-private-have', 'test-fetch-round-unwanted-advertised-have', 'test-fetch-done-closure', 'test-fetch-done-tag-closure', 'test-fetch-done-ack', 'test-fetch-duplicate-wants', 'test-fetch-offset-flag-preserves-pack', 'test-fetch-private-have-preserves-pack', 'test-fetch-unwanted-advertised-object-omitted', 'test-fetch-have-current-tip-full-pack', 'test-fetch-unadvertised-ancestor', 'test-fetch-unadvertised-reachable-blob', 'test-fetch-unadvertised-private', 'test-fetch-revoked-current-advertisement', 'test-fetch-mixed-wants-denied', 'test-fetch-missing-want', 'test-fetch-zero-want', 'test-fetch-wide-want', 'test-fetch-zero-have', 'test-fetch-wide-have', 'test-fetch-want-count-over', 'test-fetch-have-count-over', 'test-fetch-advertisement-count-over', 'test-fetch-advertisement-zero', 'test-fetch-advertisement-wide', 'test-fetch-advertisement-conflicting-kind', 'test-fetch-advertisement-wrong-kind', 'test-fetch-missing-object', 'test-fetch-corrupt-object', 'test-fetch-mismatched-loader', 'test-fetch-want-count-at', 'test-fetch-have-count-at', 'test-fetch-advertisement-count-at', 'test-fetch-inventory-object-bound', 'test-fetch-wire-round', 'test-fetch-wire-done', 'test-fetch-wire-malformed', 'test-fetch-wire-unadvertised-capability', 'test-fetch-done-blob-golden')
EXTRA = ('failing-tang-control-detected', 'compiler-failure-control-detected', 'nak-native-prefix-and-pack-envelope', 'nak-stock-negotiation-prefix', 'nak-stock-index-pack', 'nak-stock-fsck', 'nak-stock-exact-inventory', 'nak-stock-exact-bodies', 'nak-stock-corrupt-rejected', 'ack-native-prefix-and-pack-envelope', 'ack-stock-negotiation-prefix', 'ack-stock-index-pack', 'ack-stock-fsck', 'ack-stock-exact-inventory', 'ack-stock-exact-bodies', 'ack-stock-corrupt-rejected')
EXPECTED = ARMS + EXTRA
IMPORTS = {'stead-git': '', 'stead-code-git-objects': '/+  stead-git\n', 'stead-code-git-pkt': '', 'stead-code-git-response': '/+  stead-git, stead-code-git-objects, stead-code-git-pkt\n', 'stead-code-fetch-wire': '/+  stead-code-git-pkt, stead-code-git-objects\n', 'stead-code-git-graph': '/+  stead-code-git-objects\n', 'stead-code-git-emit': '/+  stead-git, stead-code-git-objects\n', 'stead-code-fetch': '/+  stead-git, stead-code-fetch-wire, stead-code-git-response, stead-code-git-graph, stead-code-git-emit\n'}
TESTS = "native/core/desk/tests/stead-code-fetch.hoon"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fixture():
    objects = {}
    def add(kind, body):
        oid = hashlib.sha1(kind.encode() + b' ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        objects[oid] = (kind, body)
        return oid
    blob = add('blob', b'abc')
    tree = add('tree', b'100644 file.txt\0' + bytes.fromhex(blob))
    first = add('commit', (f'tree {tree}\nauthor Test <test@example.invalid> 1 +0000\n'
        'committer Test <test@example.invalid> 1 +0000\n\nfirst\n').encode())
    tip = add('commit', (f'tree {tree}\nparent {first}\nauthor Test <test@example.invalid> 2 +0000\n'
        'committer Test <test@example.invalid> 2 +0000\n\nsecond\n').encode())
    tag = add('tag', (f'object {tip}\ntype commit\ntag v1\n'
        'tagger Test <test@example.invalid> 2 +0000\n\ntag message\n').encode())
    return objects, first, tip, tag


def pkt(body):
    return f'{len(body)+4:04x}'.encode() + body


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
    require(declaration == '/+  *test, stead-git, stead-code-git-objects, stead-code-git-pkt, stead-code-git-response, stead-code-fetch-wire, stead-code-git-graph, stead-code-git-emit, stead-code-fetch', 'Unexpected tests import')
    require(tuple(re.findall(r'^\+\+  (test-[a-z0-9-]+)$', tests, re.M)) == ARMS
            and tests.count('++  failure-control\n') == 1, 'Unexpected native test inventory')
    return value + '=,  test\n=>\n' + body + '\n'


def inside():
    execution_policy.require_lease(Path('/execution'), read_only=True)
    report = {'status': 'failed', 'scope': 'pure bounded authorized-input fetch selection and stock Git readback; no listener or policy integration',
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
        expression = ('=/  nak-body  interoperability\n=/  ack-body  interoperability-ack\n'
            '^-  (list [@ta @ta @ta @ta])\n'
            '~[[~.nak (scot %ud length.nak-body) (scot %ux data.nak-body) ~.body] '
            '[~.ack (scot %ud length.ack-body) (scot %ux data.ack-body) ~.body]]\n')
        output, valid = native(source + expression, 'fetch-bodies')
        rows = vectors.parse_rows(output, 4) if valid else []
        require(tuple(row[0] for row in rows) == ('nak', 'ack'), 'Native fetch bodies missing')
        objects, first, tip, tag = fixture()
        for label, width, value, marker in rows:
            require(marker == 'body', 'Native body marker changed')
            body = vectors.native_bytes(width, value)
            expected_prefix = pkt(b'NAK\n') if label == 'nak' else pkt(f'ACK {first}\n'.encode())
            pack = body[len(expected_prefix):]
            Path('/output/' + label + '.response').write_bytes(body)
            Path('/output/' + label + '.pack').write_bytes(pack)
            check(label + '-native-prefix-and-pack-envelope', body.startswith(expected_prefix)
                and pack[:12] == b'PACK\0\0\0\2\0\0\0\5'
                and hashlib.sha1(pack[:-20]).digest() == pack[-20:])
            repository = '/work/' + label + '.git'
            git('init', '--bare', '--template=', '--object-format=sha1', '--initial-branch=main', repository)
            indexed = git('--git-dir=' + repository, 'index-pack', '--stdin', '--strict', data=pack)
            index_ok = indexed.stdout == b'pack\t' + pack[-20:].hex().encode() + b'\n'
            git('--git-dir=' + repository, 'update-ref', 'refs/heads/main', tip)
            git('--git-dir=' + repository, 'update-ref', 'refs/tags/v1', tag)
            request = pkt(f'want {tag} ofs-delta\n'.encode()) + b'0000'
            if label == 'ack':
                request += pkt(f'have {first}\n'.encode())
            request += pkt(b'done\n')
            stock = git('upload-pack', '--stateless-rpc', repository, data=request)
            check(label + '-stock-negotiation-prefix', stock.stdout.startswith(expected_prefix)
                  and stock.stdout[len(expected_prefix):len(expected_prefix)+4] == b'PACK')
            check(label + '-stock-index-pack', index_ok)
            fsck = git('--git-dir=' + repository, 'fsck', '--full', '--strict')
            check(label + '-stock-fsck', fsck.returncode == 0)
            inventory = git('--git-dir=' + repository, 'cat-file', '--batch-all-objects',
                '--batch-check=%(objectname) %(objecttype) %(objectsize)').stdout.decode().splitlines()
            check(label + '-stock-exact-inventory', sorted(inventory) == sorted(
                f'{oid} {kind} {len(data)}' for oid, (kind, data) in objects.items()))
            all_exact = True
            for oid, (kind, expected) in objects.items():
                actual = git('--git-dir=' + repository, 'cat-file', kind, oid).stdout
                all_exact &= actual == expected and hashlib.sha1(kind.encode() + b' ' +
                    str(len(actual)).encode() + b'\0' + actual).hexdigest() == oid
            check(label + '-stock-exact-bodies', all_exact, objects=len(objects))
            corrupted = pack[:-1] + bytes([pack[-1] ^ 1])
            bad = git('--git-dir=' + repository, 'index-pack', '--stdin', '--strict', data=corrupted, rejected=True)
            check(label + '-stock-corrupt-rejected', bad.returncode > 0)
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
    base = ROOT / '.runtime/code-fetch'
    require(not any(path.is_symlink() for path in (base, *base.parents)), 'Redirected diagnostic path')
    require(subprocess.run(['git', 'check-ignore', '-q', str(base / 'probe')], cwd=ROOT).returncode == 0, 'Diagnostic path must be ignored')
    base.mkdir(mode=0o700, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=base))
    for name in ('input', 'output', 'code', 'work'):
        (run / name).mkdir(mode=0o700)
    helper = toolchain.CACHE / lock['kernel']['directory'] / 'pkg/base-dev/lib/test.hoon'
    copies = [(ROOT / f'native/core/desk/lib/{name}.hoon', f'input/{name}.hoon') for name in IMPORTS]
    copies += [(ROOT / TESTS, 'input/tests.hoon'), (helper, 'input/test-helper.hoon'),
               (Path(__file__), 'code/code_fetch_check.py'), (Path(vectors.__file__), 'code/code_git_vectors.py'),
               (Path(execution_policy.__file__), 'code/execution_policy.py')]
    before = {str(source): vectors.digest(source.read_bytes()) for source, _ in copies}
    for source, target in copies:
        with (run / target).open('xb') as stream:
            stream.write(source.read_bytes())
    inputs = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'before': before, 'toolchain_sha256': vectors.digest(toolchain.LOCK_PATH.read_bytes()),
              'git_sha256': vectors.digest(git_binary.read_bytes()), 'git_version': lock['host_tools']['git'],
              'expected': EXPECTED, 'scope': 'pure native fetch response and stock readback; no ship boot, route, policy or accepted write'}
    execution_policy.write_json(run / '.stead-disposable.json', {'format': 1, 'purpose': 'fixed bounded pure fetch diagnostic'})
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
            '--chdir', '/work', '/usr/bin/python3', '/code/code_fetch_check.py', '_inside']
    with (run / 'console.log').open('xb') as console:
        guard = execution_policy.run_guarded(command, root=ROOT, label='code-fetch', timeout=120, console=console)
    inputs['guard_report'] = guard['run_directory'] + '/report.json'
    inputs['after'] = {str(source): vectors.digest(source.read_bytes()) for source, _ in copies}
    execution_policy.write_json(run / 'inputs.json', inputs)
    require(guard['status'] == 'completed' and inputs['before'] == inputs['after'], 'Native guard/source check failed')
    report = execution_policy.read_json(run / 'output/report.json', maximum=vectors.MAX_OUTPUT)
    vectors.validate_report(report, EXPECTED)
    print(f'PASS {len(EXPECTED)} checks; native fetch/stock readback only', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['_inside']:
        inside()
    elif sys.argv[1:]:
        raise SystemExit('No caller-selected inputs or commands are accepted')
    else:
        main()

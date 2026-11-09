"""Synthetic real Git clients against the owned native Home browser fixture."""
import base64
from contextlib import closing
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
from portable_recovery import session_file, HTTPSQueries


def pkt(body):
    return f'{len(body) + 4:04x}'.encode() + body


def exercise(session, ca, project, output, checks, *, reuse_empty=False, reviewer=None, work=None):
    credentials = session_file(session)
    assert credentials['origin'] == 'https://home.localhost:8443'
    assert re.fullmatch(r'[0-9a-f-]{36}', project)
    origin = credentials['origin']
    transport = HTTPSQueries(credentials, ca_file=ca)
    context = ssl.create_default_context(cafile=ca)
    root = Path(tempfile.mkdtemp(prefix='native-code-', dir=output))
    git_root = ROOT / '.runtime/tooling/git-2.55.0'
    git = git_root / 'bin/git'
    helper = git_root / 'lib/git-core/git-remote-http'
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == '23f747f69b5293b9f531cc17205eab792eb92075e92f99a8d6bc2b51cf007230'
    assert (helper.parent / 'git-remote-https').resolve(strict=True) == helper
    assert hashlib.sha256(git.read_bytes()).hexdigest() == '93473c28694fd72bd889364107cd2770514de59780885a6a4aafca4d602e30ad'
    assert subprocess.check_output([git, '--version']).strip() == b'git version 2.55.0'
    remote = f'/stead/git/{project}.git'
    ask = root / 'ask'
    ask.write_text('#!/bin/sh\ncase "$1" in Username*) printf "stead\\n";; Password*) cat "$STEAD_GIT_SECRET_FILE";; *) exit 1;; esac\n')
    ask.chmod(0o700)
    password = root / 'secret'
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C.UTF-8',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_EXEC_PATH': str(helper.parent), 'GIT_SSL_CAINFO': str(ca),
           'GIT_ASKPASS': str(ask), 'STEAD_GIT_SECRET_FILE': str(password),
           'GIT_AUTHOR_NAME': 'Stead Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
           'GIT_COMMITTER_NAME': 'Stead Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}

    def manage(action, **kwargs):
        value = json.loads(transport._post('/stead/api/code', {'protocol': 'stead.code/1',
                           'project_id': project, 'action': action, **kwargs}))
        assert value['protocol'] == 'stead.code/1'
        return value

    def command(*args, cwd=root, data=None, ok=True):
        result = subprocess.run([git, '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null', *args],
                                cwd=cwd, env=env, input=data, capture_output=True, timeout=20)
        assert len(result.stdout) + len(result.stderr) <= 524288
        if (result.returncode == 0) != ok:
            message = re.sub(r'[0-9a-f]{64}', '[redacted]', result.stderr.decode(errors='replace'))
            raise RuntimeError(f'{args[0]} returned {result.returncode}: {message[:400]}')
        return result.stdout

    def connected():
        conn = http.client.HTTPSConnection('home.localhost', 8443, context=context, timeout=10)
        conn.connect()
        assert ipaddress.ip_address(conn.sock.getpeername()[0]).is_loopback
        return conn

    def request(method, path, data=None, bearer=None):
        headers = {}
        if bearer:
            headers['Authorization'] = 'Basic ' + base64.b64encode(f'stead:{bearer}'.encode()).decode()
        if data is not None:
            headers['Content-Type'] = 'application/x-git-receive-pack-request'
        with closing(connected()) as conn:
            conn.request(method, remote + path, data, headers)
            response = conn.getresponse()
            raw = response.read(524289)
            assert len(raw) <= 524288
            return response.status, raw

    assert manage('status')['status'] == ('ready' if reuse_empty else 'disabled')
    if not reuse_empty:
        assert manage('create')['status'] == 'ready'
    assert request('GET', '/info/refs?service=git-upload-pack')[0] == 401
    checks.append('no anonymous discovery')
    write = manage('issue', access='write')
    try:
        with password.open('x') as stream:
            stream.write(write['bearer'] + '\n')
        password.chmod(0o600)
        command('clone', origin + remote, 'empty')
        assert command('show-ref', cwd=root / 'empty', ok=False) == b''
        checks.append('stock clone of empty native repository')
        source = root / 'source'
        source.mkdir()
        command('init', '--initial-branch=main', '--object-format=sha1', cwd=source)
        (source / 'hello.txt').write_bytes(b'Stead\x00 native Git\n')
        command('add', 'hello.txt', cwd=source)
        command('commit', '-m', 'First fixture commit', cwd=source)
        first = command('rev-parse', 'HEAD', cwd=source).strip()
        command('tag', '-a', 'v1', '-m', 'Signed by the fixture', cwd=source)
        tag = command('rev-parse', 'v1', cwd=source).strip()
        command('push', '--atomic', origin + remote, 'main', 'v1', cwd=source)
        checks.append('atomic stock push of branch and annotated tag')
        command('clone', origin + remote, 'clone')
        clone = root / 'clone'
        assert command('rev-parse', 'HEAD', cwd=clone).strip() == first
        assert command('rev-parse', 'v1', cwd=clone).strip() == tag
        assert (clone / 'hello.txt').read_bytes() == (source / 'hello.txt').read_bytes()
        command('fsck', '--full', '--strict', cwd=clone)
        checks.append('stock clone exact commit tag and blob bytes, strict fsck')
        (source / 'hello.txt').write_bytes(b'Fast forward\x00\n')
        command('commit', '-am', 'Second fixture commit', cwd=source)
        second = command('rev-parse', 'HEAD', cwd=source).strip()
        command('push', origin + remote, 'main', cwd=source)
        command('fetch', 'origin', cwd=clone)
        assert command('rev-parse', 'refs/remotes/origin/main', cwd=clone).strip() == second
        checks.append('stock fast-forward push and fetch exact new OID')

        def update(old, tip, ref=b'refs/heads/main'):
            return pkt(old + b' ' + tip + b' ' + ref + b'\x00report-status\n') + b'0000'

        stale = update(first, second) + command('pack-objects', '--stdout', cwd=source, data=b'')
        status, body = request('POST', '/git-receive-pack', stale, write['bearer'])
        assert status == 200 and b'ng refs/heads/main stale-ref' in body
        checks.append('stale CAS rejected by Home')
        bad = update(second, first) + b'not a pack'
        status, body = request('POST', '/git-receive-pack', bad, write['bearer'])
        assert status == 200 and b'unpack invalid or oversized pack' in body
        checks.append('malformed pack rejected by Home')
        assert manage('protect', ref='refs/heads/main')['status'] == 'protected'
        (source / 'hello.txt').write_bytes(b'Protected fast-forward attempt\n')
        command('commit', '-am', 'Protected fixture attempt', cwd=source)
        command('push', origin + remote, 'main', cwd=source, ok=False)
        command('push', origin + remote, ':refs/heads/main', cwd=source, ok=False)
        checks.append('protected fast-forward and deletion rejected by stock transport')

        body = update(second, b'0' * 40)
        auth = 'Basic ' + base64.b64encode(f"stead:{write['bearer']}".encode()).decode()
        with closing(connected()) as conn:
            conn.putrequest('POST', remote + '/git-receive-pack')
            conn.putheader('Authorization', auth)
            conn.putheader('Content-Type', 'application/x-git-receive-pack-request')
            conn.putheader('Content-Length', str(len(body)))
            conn.endheaders()
            conn.send(body[:20])
            assert manage('revoke', handle=write['handle'])['status'] == 'revoked'
            conn.send(body[20:])
            assert conn.getresponse().status == 401
        checks.append('credential revoked before upload finishes')
        read = manage('issue', access='read')
        password.write_text(read['bearer'] + '\n')
        command('fetch', 'origin', cwd=clone)
        assert command('rev-parse', 'refs/remotes/origin/main', cwd=clone).strip() == second
        command('push', origin + remote, 'main:refs/heads/denied', cwd=source, ok=False)
        assert manage('revoke', handle=read['handle'])['status'] == 'revoked'
        checks.append('read-only credential can fetch but cannot push')
        result = {'first_oid': first.decode(), 'head_oid': second.decode(), 'tag_oid': tag.decode()}
        if reviewer:
            result['review'] = review_proof(
                credentials, session_file(reviewer), ca, project, work, origin + remote,
                source, clone, second, manage, command, password, checks)
        return result
    finally:
        password.unlink(missing_ok=True)


def review_proof(owner, reviewer, ca, project, work, remote, source, clone, base, manage,
                 command, password, checks):
    """Real second principal and protected branch on the same native Home."""
    assert owner['origin'] == reviewer['origin'] and owner['principal_id'] != reviewer['principal_id']
    assert re.fullmatch(r'[0-9a-f-]{36}', work)
    source_transport = HTTPSQueries(owner, ca_file=ca)
    reviewer_transport = HTTPSQueries(reviewer, ca_file=ca)
    make_id = lambda: str(uuid.uuid7())
    proposal = make_id()
    grant = make_id()
    receipt_id = make_id()

    def code(transport, action, expected=200, **fields):
        with closing(transport._connection(15)) as connection:
            body = {'protocol': 'stead.code/1', 'project_id': project, 'action': action, **fields}
            current = transport.credentials
            connection.request('POST', '/stead/api/code', json.dumps(body).encode(), {
                'Origin': current['origin'], 'Content-Type': 'application/json',
                'Cookie': '__Host-stead-session=' + current['session'], 'X-Stead-CSRF': current['csrf'],
                'Accept-Encoding': 'identity', 'Cache-Control': 'no-store'})
            response = connection.getresponse()
            value = json.loads(response.read(16385))
            if response.status != expected:
                error = value.get('error', 'unexpected')
                if not isinstance(error, str) or not re.fullmatch(r'[a-z0-9_-]{1,80}', error):
                    error = 'unexpected'
                raise RuntimeError(f'review {action} returned {response.status}: {error}')
            return value

    def policy(action, payload):
        value = json.loads(source_transport({'protocol': 'stead.query/3', 'request_id': make_id(),
            'kind': 'project', 'project_id': project, 'resource_id': '', 'container_id': '', 'cursor': '', 'search': ''}))
        assert value['status'] == 'read' and len(value['rows']) == 1
        row = next(iter(value['rows'].values()))
        outcome = json.loads(source_transport._post('/stead/api/command', {
            'protocol': 'stead.command/3', 'request_id': make_id(), 'project_id': project,
            'resource_id': project, 'expected_revision': row['policy_revision'],
            'authority_epoch': row['authority_epoch'], 'operation': action, 'payload': payload}))
        if outcome['status'] != 'accepted':
            raise RuntimeError(f'{action} fixture grant change was rejected')

    write = manage('issue', access='write')
    granted = False
    try:
        password.write_text(write['bearer'] + '\n')
        head = command('rev-parse', 'HEAD', cwd=source).strip().decode()
        command('push', remote, 'HEAD:refs/heads/review-proof', cwd=source)
        selection = {'proposal_id': proposal, 'revision': '1'}
        submitted = code(source_transport, 'submit', **selection, work_id=work, ref='refs/heads/main',
                         base_oid=base.decode(), head_oid=head, delegation_id='')
        assert submitted['status'] == 'accepted'
        code(source_transport, 'approve', expected=409, **selection)
        code(reviewer_transport, 'approve', expected=409, **selection)
        code(reviewer_transport, 'merge', expected=409, request_id=receipt_id, **selection)
        checks.append('self and reader cannot approve or merge the proposal')
        policy('policy.grant', {'grant_id': grant, 'principal_id': reviewer['principal_id'],
                                'role': 'maintainer', 'expires_at_ms': str(int(time.time() * 1000) + 1800000)})
        granted = True
        assert code(reviewer_transport, 'approve', **selection)['status'] == 'accepted'
        view = code(reviewer_transport, 'proposal', **selection)
        assert view['head_oid'] == head and view['base_oid'] == base.decode()
        assert view['reviewer'] == reviewer['principal_id']
        accepted = code(reviewer_transport, 'merge', request_id=receipt_id, **selection)
        assert accepted['status'] == 'accepted'
        replayed = code(reviewer_transport, 'merge', request_id=receipt_id, **selection)
        assert replayed['status'] == 'replayed'
        assert replayed['repository_revision'] == accepted['repository_revision']
        command('fetch', 'origin', cwd=clone)
        assert command('rev-parse', 'refs/remotes/origin/main', cwd=clone).strip().decode() == head
        command('fsck', '--full', '--strict', cwd=clone)
        checks.append('exact approved protected ref commits once and stock fetch observes the original OID')
        build = build_proof(code, source_transport, reviewer_transport, project, selection, head, source, command)
        checks.append('assigned worker lease and verified offline artifact finish exactly once')
        policy('policy.revoke', {'grant_id': grant})
        granted = False
        code(reviewer_transport, 'merge', expected=409, request_id=receipt_id, **selection)
        checks.append('revoked reviewer cannot replay a protected merge receipt')
        return {'proposal': proposal, 'head_oid': head, 'repository_revision': accepted['repository_revision'],
                'build': build}
    finally:
        if granted:
            policy('policy.revoke', {'grant_id': grant})
        manage('revoke', handle=write['handle'])


def build_proof(code, requester, runner, project, selection, head, source, command):
    recipe = '9dfe50f0b7df0c270bff4c06a67251eac3e94476c034e4e3d0209fa8aa96fc6e'
    job_id = str(uuid.uuid7())
    job = code(requester, 'build-queue', job_id=job_id, recipe=recipe, worker_ship='~nec', **selection)
    assert job['transition'] == 'accepted' and job['status'] == 'queued'
    code(requester, 'build-claim', expected=409, job_id=job_id, expected_attempt='0')
    claim = code(runner, 'build-claim', job_id=job_id, expected_attempt='0')
    assert claim['status'] == 'leased' and claim['attempt'] == '1' and claim['commit'] == head
    bundle = source.parent / 'build-input.bundle'
    command('bundle', 'create', str(bundle), 'refs/heads/main', cwd=source)
    bundle.chmod(0o600)
    job_path = source.parent / 'build-job.json'
    job_raw = json.dumps({'protocol': 'stead.build-job/1', 'project_id': project, 'job_id': job_id,
        'proposal_id': selection['proposal_id'], 'proposal_revision': 1, 'attempt': 1,
        'commit': head, 'source': claim['source'], 'recipe': recipe,
        'bundle_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest()}, sort_keys=True).encode()
    job_path.write_bytes(job_raw)
    git = ROOT / '.runtime/tooling/git-2.55.0/bin/git'
    output = source.parent / 'build-output'
    result = subprocess.run(['/usr/bin/python3', '-B', str(ROOT / 'scripts/urbit/code_build_worker.py'), 'run',
        '--job', str(job_path), '--job-sha256', hashlib.sha256(job_raw).hexdigest(),
        '--bundle', str(bundle), '--git-binary', str(git),
        '--git-sha256', '93473c28694fd72bd889364107cd2770514de59780885a6a4aafca4d602e30ad',
        '--output', str(output)], capture_output=True, timeout=40)
    if result.returncode:
        raise RuntimeError('isolated build worker failed')
    receipt = json.loads((output / 'result.json').read_bytes())
    proof = receipt['attestation']
    artifact = (output / 'tree-manifest.json').read_bytes()
    assert proof['source'] == claim['source'] and proof['recipe'] == recipe and proof['outcome'] == 'passed'
    assert hashlib.sha256(artifact).hexdigest() == proof['output']
    fields = {'job_id': job_id, 'attempt': '1', **proof, 'artifact_base64': base64.b64encode(artifact).decode()}
    code(runner, 'build-finish', expected=409, **(fields | {'output': 'a' * 64}))
    accepted = code(runner, 'build-finish', **fields)
    assert accepted['transition'] == 'accepted' and accepted['status'] == 'finished'
    assert code(runner, 'build-finish', **fields)['transition'] == 'replayed'
    code(requester, 'build-release', expected=409, job_id=job_id, request_id=str(uuid.uuid7()))
    return {'job_id': job_id, 'attempt': 1, 'commit': head, 'artifact_sha256': proof['output']}


if __name__ == '__main__':
    args = sys.argv[5:]
    assert args in ([], ['--reuse-empty']) or (len(args) == 4 and args[:2] == ['--reuse-empty', '--review'])
    os.umask(0o077)
    checks = []
    try:
        reviewer = Path(args[2]) if len(args) == 4 else None
        work = args[3] if reviewer else None
        oids = exercise(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]), checks,
                        reuse_empty=bool(args), reviewer=reviewer, work=work)
    except Exception as error:
        detail = str(error) if type(error) is RuntimeError else type(error).__name__
        print(json.dumps({'status': 'fail', 'checks': checks, 'error': detail}))
    else:
        print(json.dumps({'status': 'pass', 'checks': checks, **oids}))

"""Synthetic real Git clients against the owned native Home browser fixture."""
import base64
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
from portable_recovery import session_file, HTTPSQueries


def pkt(body):
    return f'{len(body) + 4:04x}'.encode() + body


def exercise(session, ca, project, output, checks):
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
        with connected() as conn:
            conn.request(method, remote + path, data, headers)
            response = conn.getresponse()
            raw = response.read(524289)
            assert len(raw) <= 524288
            return response.status, raw

    assert manage('status')['status'] == 'disabled'
    assert manage('create')['status'] == 'ready'
    assert request('GET', '/info/refs?service=git-upload-pack')[0] == 401
    checks.append('no anonymous discovery')
    write = manage('issue', access='write')
    try:
        with password.open('x') as stream:
            stream.write(write['bearer'] + '\n')
        password.chmod(0o600)
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
        command('push', origin + remote, ':refs/heads/main', cwd=source, ok=False)
        checks.append('protected deletion rejected by stock transport')

        body = update(second, b'0' * 40)
        auth = 'Basic ' + base64.b64encode(f"stead:{write['bearer']}".encode()).decode()
        with connected() as conn:
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
        checks.append('reader can fetch but cannot push')
        return {'first_oid': first.decode(), 'head_oid': second.decode(), 'tag_oid': tag.decode()}
    finally:
        password.unlink(missing_ok=True)


if __name__ == '__main__':
    assert len(sys.argv) == 5
    os.umask(0o077)
    checks = []
    try:
        oids = exercise(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]), checks)
    except Exception as error:
        detail = str(error) if type(error) is RuntimeError else type(error).__name__
        print(json.dumps({'status': 'fail', 'checks': checks, 'error': detail}))
    else:
        print(json.dumps({'status': 'pass', 'checks': checks, **oids}))

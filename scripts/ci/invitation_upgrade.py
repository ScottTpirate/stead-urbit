"""Isolated, synthetic saved-v8 Home upgrade and stopped-checkpoint rollback.

Run only inside the disposable worker. The outer runner provides pinned Home
archives and a public synthetic seed. No production pier or credential is an
input. The only retained result is an aggregate JSON receipt.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import sys
import tarfile
import time

sys.path.insert(0, "/src/scripts")
import release_install as release
from native import Native, inventory
import native_tls
import team_conn

STATE = Path('/state')
INPUT = Path('/src/rehearsal')
PROJECT = '019939ba-4000-7000-8000-000000000001'
SAVED = '=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)  ?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  '
CLEAN = {'clean': True, 'reaped': True, 'premature': False, 'forced': False, 'exit_code': 0}


def require(ok, label):
    if not ok:
        raise ValueError(label)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(name, pin):
    path = INPUT / (name + '.tar')
    require(path.stat().st_size == pin['bytes'] <= 8 * 1024 * 1024 and digest(path.read_bytes()) == pin['sha256'],
            'release archive does not match the pinned bytes')
    root = STATE / (name + '-package')
    root.mkdir()
    with tarfile.open(path, 'r:') as archive:
        members = archive.getmembers()
        names = [entry.name for entry in members]
        require(0 < len(members) <= 256 and len(names) == len(set(names)), 'archive inventory')
        for entry in members:
            require(entry.isfile() and entry.name.startswith('stead-release/') and
                    not any(part in ('', '.', '..') for part in entry.name.split('/')) and entry.size <= 524288,
                    'unexpected archive entry')
        manifest = json.load(archive.extractfile('stead-release/manifest.json'))
        require(manifest['source_commit'] == pin['source_commit'] and manifest['role'] == 'home',
                'wrong commit or package role')
        require(set(names) == {'stead-release/manifest.json'} | {'stead-release/' + n for n in manifest['files']},
                'manifest inventory')
        for entry in members:
            name = entry.name.removeprefix('stead-release/')
            if name == 'manifest.json':
                continue
            data = archive.extractfile(entry).read()
            require(manifest['files'][name] == dict(bytes=len(data), sha256=digest(data)), 'source digest')
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return root, inventory(root / 'desk')


class Home(release.ReleaseNative):
    def __init__(self, sealed=None):
        self.sealed = sealed
        super().__init__('zod', 31337, lambda: None)

    def _check_pier(self):
        if self.sealed is None:
            return super()._check_pier()
        require(release.checkpoint_tree(self.pier, installed=True) == self.sealed, 'cold-start checkpoint differs')

    def _arguments(self):
        if self.sealed is None:
            return super()._arguments()
        return [self.binary, '-t', '-L', '--no-dock', '--loom', '31', '-b', '127.0.0.1', '-p', '31337',
                '--http-port', '18080', '--https-port', '18443', str(self.pier)]


def suspend(home):
    home.dojo('|rein %release-test [%.n %stead-home]')
    release.wait_agent(home, 'stead-home', False)
    require(home.dojo('.^(desk %gd /=stead-home=/$)').strip() == '%release-test', 'wrong agent desk')


def capture(home, version):
    shape = '[* *] * * * * *' + ('' if version == 8 else ' * *')
    prefix = SAVED + f'?>  ?=([%stead-home %{version} {shape}] q.saved)  '
    tail = '' if version == 8 else ' boards=* offers=*'
    prefix += '=/  parts=[team=[db=* projection=*] code=* mode=* retired=* packs=* external=*' + tail + ']  +>.q.saved  '
    def pin(expression):
        output = home.dojo(prefix + '^-  @ux  (shax (jam ' + expression + '))')
        token = ''.join(output.split())
        if not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', token) or len(token) > 82:
            terms = re.findall(r'nest-fail|find-(?:fork|limb)|mint-(?:nice|vain)|syntax error|exit', output[:2000])
            raise ValueError(f'invalid {expression} fingerprint ({terms[:4]})')
        value = int(token.replace('.', ''), 16)
        require(value.bit_length() <= 256, 'fingerprint exceeds 256 bits')
        return f'{value:064x}'
    if version == 11:
        require(home.dojo(prefix + '=/  offers  ;;((map @t *) offers.parts)  =(1 ~(wyt by offers))').strip() == '%.y', 'expected one durable offer')
    return dict(version=version, saved=pin('saved'), core=pin('[db.team.parts code.parts mode.parts retired.parts packs.parts]'),
                external=pin('external.parts'))


def http(ca, path, payload, jar, csrf='', method='POST'):
    connection = http.client.HTTPConnection('127.0.0.1', release.TLS_PORT, timeout=10)
    try:
        connection.connect()
        connection.sock = ssl.create_default_context(cafile=str(ca)).wrap_socket(connection.sock, server_hostname=release.TLS_HOST)
        headers = {'Host': 'home.localhost:18443', 'Origin': release.HTTP_ORIGIN, 'Content-Type': 'application/json'}
        if jar:
            headers['Cookie'] = '; '.join(key + '=' + value for key, value in jar.items())
        if csrf:
            headers['x-stead-csrf'] = csrf
        connection.request(method, path, json.dumps(payload).encode() if payload is not None else None, headers)
        res = connection.getresponse()
        raw = res.read(524289)
        require(res.status == 200 and len(raw) <= 524288, 'Home HTTP request failed: ' + path)
        for key, val in res.getheaders():
            if key.lower() == 'set-cookie':
                name, value = val.split(';', 1)[0].split('=', 1)
                if name.startswith('__Host-stead-'):
                    jar[name] = value
        return json.loads(raw) if payload is not None else raw
    finally:
        connection.close()


def resume(home, ca, package, supports_invites):
    home.dojo('|rein %release-test [%.y %stead-home]')
    release.wait_agent(home, 'stead-home', True)
    # The v8 seed contains a populated project, so full journal recovery can
    # take several events. Poll its owner-authorized bootstrap to readiness.
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        token = secrets.token_hex(32)
        result = release.owner_call(home, 'home', 'bootstrap', {'protocol': 'stead.bootstrap/1', 'nonce': token},
                                    '/bootstrap/' + token)
        if result.get('status') == 'ready' and result.get('nonce') == token:
            break
        time.sleep(.5)
    else:
        raise TimeoutError('Home restore never reached bootstrap readiness')
    # Source-owned archive and served content must match after each boot.
    routes = json.loads((package / 'source/frontend.json').read_bytes())['routes']
    for item in routes:
        if item['route'].startswith('/stead/'):
            raw = http(ca, item['route'], None, {}, method='GET')
            require(len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'served route differs')
    caps = http(ca, '/stead/api/capabilities', {'protocol': 'stead.capabilities/3'}, {})
    require((caps.get('invitations') == 'stead.invitation/1') == supports_invites, 'wrong invitation capability')


def member_session(member, ca):
    jar = {}
    value = {'protocol': 'stead.auth/1', 'identity_ship': '~bus'}
    challenge = http(ca, '/stead/auth/start', value, jar)
    require(challenge.get('status') == 'pending', 'synthetic member challenge failed')
    approval = {'protocol': 'stead.auth/1', 'purpose': 'member-session', 'challenge_id': challenge['challenge_id'],
                'home': '~zod', 'origin': release.HTTP_ORIGIN, 'identity_ship': '~bus',
                'principal_id': '019939ba-4000-7000-8000-000000000002',
                'binding_id': '019939ba-4000-7000-8000-000000000003', 'binding_revision': '1',
                'expires_at_ms': challenge['expires_at_ms']}
    team_conn.run(member.binary, member.pier / '.urb/conn.sock', 'approve', '/',
                  json.dumps(approval, sort_keys=True, separators=(',', ':')).encode(), target='zod')
    body = {'protocol': 'stead.auth/1', 'challenge_id': challenge['challenge_id']}
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if http(ca, '/stead/auth/status', body, jar).get('status') == 'approved':
            break
        time.sleep(.4)
    else:
        raise TimeoutError('synthetic member did not receive native approval')
    accepted = http(ca, '/stead/auth/consume', body, jar)
    require(accepted.get('status') == 'authenticated', 'synthetic member session failed')
    return jar, accepted['csrf']


def run():
    require(Path.cwd() != STATE and os.getuid() != 0 and set(os.listdir('/sys/class/net')) == {'lo'},
            'requires an isolated unprivileged synthetic worker')
    os.umask(0o077)
    pins = json.loads((INPUT / 'inputs.json').read_bytes())
    require(pins['previous']['sha256'] == '7fb6222a2b2f6aabb4e02565014eeafa3fa880ae27220b2a9dca70d293b0faf2',
            'wrong named Home predecessor')
    previous, old = extract('previous', pins['previous'])
    candidate, new = extract('candidate', pins['candidate'])
    require(inventory(INPUT / 'seed') == pins['seed'] and inventory(INPUT / 'drivers') == pins['drivers'], 'fixture source inventory')
    seed = STATE / 'seed-desk'
    shutil.copytree(previous / 'desk', seed)
    shutil.copytree(INPUT / 'seed', seed, dirs_exist_ok=True)
    seeded = inventory(seed)
    require(seeded == old | pins['seed'], 'seed overlay inventory')
    home = Home()
    peer = None
    stopped = STATE / 'predecessor-checkpoint'
    receipt = {'protocol': 'stead.invitation-upgrade/1', 'inputs': pins, 'stages': {}}
    def record(stage, data):
        receipt['stages'][stage] = data
        print(stage, flush=True)
    def cold(expected, label):
        nonlocal home
        require(home.stop() == CLEAN, 'unclean Vere stop')
        home.logpath.rename(STATE / ('home-' + label + '.log'))
        sealed = release.stopped_home_checkpoint(home.pier, expected)
        home = Home(sealed)
        home.start()
        return sealed
    try:
        print('Starting synthetic predecessor', flush=True)
        home.start()
        home.install(INPUT / 'drivers')
        release.install_desk(home, 'stead-home', seed)
        release.wait_agent(home, 'stead-home', True)
        suspend(home)
        print('Suspended synthetic v8 seed', flush=True)
        seeded_state = capture(home, 8)
        release.replace_clay_files(home, seeded, old, package=previous / 'desk')
        certs = native_tls.create(STATE / 'certs')
        ca = certs / 'ca.pem'
        native_tls.install(home.binary, home.pier / '.urb/conn.sock', certs, 'zod')
        resume(home, ca, previous, False)
        suspend(home)
        before = capture(home, 8)
        require(before['core'] == seeded_state['core'] and before['external'] == seeded_state['external'], 'predecessor changed seed')
        record('populated-predecessor', before)
        require(home.stop() == CLEAN, 'predecessor not stopped')
        home.logpath.rename(STATE / 'home-before-checkpoint.log')
        sealed = release.stopped_home_checkpoint(home.pier, old)
        require(release.checkpoint_tree(home.pier, stopped, installed=True) == sealed
                and release.checkpoint_tree(stopped, installed=True) == sealed, 'checkpoint copy differs')
        record('stopped-independent-copy', sealed)
        home = Home(sealed); home.start()
        require(capture(home, 8)['saved'] == before['saved'], 'checkpoint resume changed saved state')
        release.replace_clay_files(home, old, new, package=candidate / 'desk')
        resume(home, ca, candidate, True)
        suspend(home)
        migrated = capture(home, 8)
        require(migrated['core'] == before['core'] and migrated['external'] == before['external'], 'migration changed legacy state')
        record('candidate-loaded-predecessor', migrated)
        resume(home, ca, candidate, True)
        peer = Native('bus', 31519, lambda: None)
        peer.start(); peer.install(INPUT / 'drivers')
        jar, csrf = member_session(peer, ca)
        request = {'protocol': 'stead.invitation/1', 'action': 'issue', 'project_id': PROJECT,
                   'mode': 'personal', 'identity_ship': '~nec', 'role': 'reader', 'expires_at_ms': '', 'use_limit': '1'}
        issued = http(ca, '/stead/api/invitations', request, jar, csrf)
        require(issued.get('status') == 'issued', 'ordinary maintainer could not issue a durable invitation')
        suspend(home)
        invited = capture(home, 11)
        require(invited['core'] == before['core'], 'issuing invitation changed predecessor core')
        record('candidate-saved-invitation', invited)
        cold(new, 'candidate')
        require(capture(home, 11) == invited, 'candidate cold restart changed its saved state')
        resume(home, ca, candidate, True)
        jar, csrf = member_session(peer, ca)
        listed = http(ca, '/stead/api/invitations', {'protocol': 'stead.invitation/1', 'action': 'list', 'project_id': PROJECT}, jar, csrf)
        require(issued['invitation_id'] in listed['invitations'], 'durable invitation missing after restart')
        record('candidate-cold-invitation-readback', True)
        suspend(home)
        require(home.stop() == CLEAN, 'candidate not stopped')
        home.logpath.rename(STATE / 'home-before-rollback.log')
        # Never boot the backup directly. Only one fake ~zod process exists.
        home.pier.rename(STATE / 'retired-candidate-pier')
        require(release.checkpoint_tree(stopped, home.pier, installed=True) == sealed
                and release.stopped_home_checkpoint(home.pier, old) == sealed, 'independent rollback copy differs')
        home = Home(sealed); home.start()
        require(capture(home, 8) == before, 'restored v8 vase mismatch')
        resume(home, ca, previous, False)
        member_session(peer, ca)
        record('checkpoint-restored-predecessor-signin', True)
        receipt['status'] = 'pass'
    finally:
        clean = home.stop()
        member_clean = None if peer is None else peer.stop()
        receipt['clean_shutdown'] = clean == CLEAN and member_clean in (None, CLEAN)
        (STATE / 'upgrade-result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True))
        require(receipt['clean_shutdown'], 'native worker cleanup incomplete')


if __name__ == '__main__':
    run()

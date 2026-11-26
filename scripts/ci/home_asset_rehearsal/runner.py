"""Fixed disposable saved8 rehearsal, called only by a reviewed hosted worker.

There is no local CLI, arbitrary pier, ship, version, package or noun argument.
The outer guardian owns admission, exact source/runtime mounts, renewable lease,
process lifetime and final EOF/cgroup cleanup. A passing inner result alone is
not release approval. Only the fixed synthetic seed is ever installed.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import stat
import tarfile
import time
import types

from . import evidence as E

BASE = 'a0e90ef29389077d453ec2a775cd8fd69f711727'
TARGET = '51d608cb81955c35a021247697bdcc9a0936a4c5'
ARCHIVES = {
    'previous': (1392640, 'baa226f22bc1950981628486539fa1f087d2e6544c12a18c1d15e144b082e7da', BASE),
    'target': (1648640, '17c4932589c75d132416746c748c8acd0aecc5c7394c5766155eaab692839d97', TARGET),
}
SEED = {
    'app/stead-home.hoon': 'd6d15bc9514001a2edcdcb67384881826215e7fd40c08465edc74962d8b70fdd',
    'lib/stead-home-ui-seed.hoon': '4021487a4d7878461e02951a8e00ccd28b1b9eb2346ec3a09f596ca93bc131e4',
}
DRIVER_NAMES = frozenset(('gen/home-ui-capture.hoon', 'lib/stead-codec.hoon',
    'lib/stead-delivery.hoon', 'ted/stead-team-client.hoon', 'ted/stead-local-tls.hoon'))
SOURCE_NAMES = {
    '/ci': {'home_asset_rehearsal/runner.py', 'home_asset_rehearsal/evidence.py',
            'home_asset_rehearsal/capture.hoon'},
    '/code': {'release_install.py'},
    '/helpers': {'execution_policy.py', 'core_conn.py', 'conn.py', 'owned_child.py',
                 'native_tls.py', 'team_conn.py'},
    '/support': {'native.py'},
}
RUNTIME = 'f7f0d3b3c0480fc10f887dfbc09bde56a81d723a803541c7886c538a0675d833'
PILL = 'b4babd14e9f1acbdb421b3c31c215ee637ad6691b7e382b99c6fd8991e623708'
KERNEL = '5a187fededc4582a34fcd6055c67bb63e0917b94'
CLEAN_STOP = {'clean': True, 'exit_code': 0, 'forced': False, 'premature': False, 'reaped': True}
MAX_SECONDS = 3600
OPERATIONS = ('admission', 'seed-package', 'fresh-boot', 'driver-install', 'seed-install',
    'seed-ready', 'seed-suspend', 'capture-seed8', 'predecessor-replace', 'tls',
    'predecessor-resume', 'predecessor-routes', 'predecessor-suspend', 'capture-a0-loaded',
    'cold-restart', 'cold-resume', 'cold-suspend', 'capture-a0-cold', 'asset-replace',
    'asset-resume', 'asset-routes', 'asset-suspend', 'capture-assets-loaded',
    'rollback-replace', 'rollback-resume', 'rollback-routes', 'rollback-suspend',
    'capture-rollback-loaded', 'rollback-restart', 'rollback-cold-resume',
    'rollback-cold-suspend', 'final-inputs')
DIAGNOSTIC_SOURCES = {
    'runner': ('/ci', 'home_asset_rehearsal/runner.py'),
    'evidence': ('/ci', 'home_asset_rehearsal/evidence.py'),
    'release_install': ('/code', 'release_install.py'),
    'native': ('/support', 'native.py'),
}
COMPILER_TAGS = ('mint-vain', 'mint-nice', 'nest-fail', 'find-fork', 'find-limb',
    'seek-loop', 'play-dull', 'syntax error')


def command_observation(source, output=None):
    """Only digests and finite classifications; never retain a saved noun."""
    E.require(type(source) is str)
    raw = source.encode()
    E.require(0 < len(raw) <= 65536 and (output is None or type(output) is str))
    result = {'source_sha256': E.sha(raw), 'source_bytes': len(raw),
        'completed': output is not None, 'output_sha256': None, 'output_bytes': None,
        'output_kind': 'unobserved'}
    if output is not None:
        value = output.encode()
        E.require(len(value) <= 1000000)
        text = output.strip()
        kind = {'': 'empty', '%.y': 'yes', '%.n': 'no', '%release-test': 'release-desk'}.get(text)
        if kind is None:
            kind = 'hex-atom' if re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', text) else 'other'
        result.update(output_sha256=E.sha(value), output_bytes=len(value), output_kind=kind)
        if source in (E.FINGERPRINT, E.TOTAL, *E.CONDITIONS.values()) and kind == 'other':
            # Frozen commands return only a boolean or digest/length. Retain
            # compiler vocabulary and coordinates; arbitrary text and nouns stay private.
            result['compiler'] = E.fixed_compiler_terms(text)
    return result



def failure_positions(error, sources):
    """Match exact captured code, excluding messages, locals and arbitrary frames."""
    E.require(type(sources) is dict and set(sources) == set(DIAGNOSTIC_SOURCES))
    allowed, hashes = {}, {}
    for label, item in sources.items():
        E.require(type(item) is dict and set(item) == {'raw', 'filename', 'sha256'})
        raw, filename = item['raw'], item['filename']
        E.require(type(raw) is bytes and 0 < len(raw) <= 262144 and E.sha(raw) == item['sha256']
            and type(filename) is str and 0 < len(filename) <= 4096)
        pending, codes = [compile(raw, filename, 'exec', dont_inherit=True)], []
        while pending:
            code = pending.pop()
            E.require(len(codes) < 256)
            codes.append(code)
            pending.extend(value for value in code.co_consts if type(value) is types.CodeType)
        allowed[label] = (filename, codes, len(raw.splitlines()))
        hashes[label] = item['sha256']
    trace, inspected, locations, seen, truncated = error.__traceback__, 0, [], set(), False
    while trace is not None and inspected < 64:
        inspected += 1
        code, line = trace.tb_frame.f_code, trace.tb_lineno
        for label, (filename, codes, count) in allowed.items():
            key = (label, code.co_name, line)
            if (code.co_filename == filename and code in codes and 1 <= line <= count
                    and re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}', code.co_name) and key not in seen):
                seen.add(key)
                if len(locations) < 16:
                    locations.append({'source': label, 'function': code.co_name, 'line': line})
                else:
                    truncated = True
        trace = trace.tb_next
    return {'source_sha256': hashes, 'locations': locations, 'frames_inspected': inspected,
        'truncated': truncated or trace is not None}


def compiler_projection(raw):
    """Closed location/tag projection from a bounded native log tail, not raw logs."""
    E.require(type(raw) is bytes and len(raw) <= 65536)
    text = re.sub(r'\x1b\[[0-9;]*m', '', raw.decode('utf-8', errors='replace'))
    tags, positions = [], []
    # Only native source paths, numbers and known compiler labels are exported.
    span = re.compile(r'(/[a-z0-9~/._-]{1,192})(?:::|:)<?\[([0-9,]+) ([0-9,]+)\]\.\[([0-9,]+) ([0-9,]+)\]>?')
    for line in text.splitlines():
        if len(line) > 1024:
            continue
        token = line.strip()
        if token in COMPILER_TAGS and token not in tags:
            tags.append(token)
        match = span.fullmatch(token)
        if match and len(positions) < 16:
            path, *values = match.groups()
            numbers = [int(value.replace(',', '')) for value in values]
            if all(0 < value <= 1000000 for value in numbers):
                row = {'path': path, 'line': numbers[0], 'column': numbers[1],
                    'end_line': numbers[2], 'end_column': numbers[3]}
                if row not in positions:
                    positions.append(row)
    return {'tail_bytes': len(raw), 'tail_sha256': E.sha(raw), 'tags': tags, 'locations': positions}


def log_observation(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        E.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= 16777216)
        stream.seek(max(0, before.st_size - 65536))
        raw = stream.read(65537)
        after = os.fstat(stream.fileno())
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        E.require(len(raw) == min(before.st_size, 65536)
            and all(getattr(before, key) == getattr(after, key) for key in fields))
    return {'bytes': before.st_size, **compiler_projection(raw)}


def read_regular(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        E.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= maximum)
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        E.require(len(raw) == before.st_size
            and all(getattr(before, field) == getattr(after, field) for field in fields))
    return raw


def package(name, inventory):
    E.require(name in ARCHIVES)
    size, digest, commit = ARCHIVES[name]
    root = Path('/rehearsal') / name
    E.require(os.statvfs(root).f_flag & os.ST_RDONLY
        and os.statvfs(Path('/rehearsal') / (name + '.tar')).f_flag & os.ST_RDONLY)
    raw = read_regular(Path('/rehearsal') / (name + '.tar'), size)
    E.require(len(raw) == size and E.sha(raw) == digest)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        members = archive.getmembers()
        E.require(0 < len(members) <= 128 and len({m.name for m in members}) == len(members))
        files = {}
        for member in members:
            E.require(member.isfile() and member.name.startswith('stead-release/')
                and all(part not in ('', '.', '..') for part in member.name.split('/'))
                and 0 < member.size <= 524288)
            files[member.name[len('stead-release/'):]] = archive.extractfile(member).read()
    E.require(inventory(root) == {name: E.sha(data) for name, data in files.items()})
    manifest = json.loads(files['manifest.json'], object_pairs_hook=E.unique)
    E.require(manifest['source_commit'] == commit and manifest['role'] == 'home'
        and manifest['agents'] == ['stead-home'] and type(manifest['saved_state_version']) is int
        and manifest['saved_state_version'] == 9
        and manifest['compatibility']['kernel_commit'] == KERNEL
        and manifest['compatibility']['runtime_binary_sha256'] == RUNTIME)
    E.require(manifest['files'] == {name: {'bytes': len(data), 'sha256': E.sha(data)}
        for name, data in files.items() if name != 'manifest.json'})
    desk = {name[5:]: E.sha(data) for name, data in files.items() if name.startswith('desk/')}
    E.require(len(desk) == (116 if name == 'previous' else 118))
    return manifest, desk


def inputs(context, inventory):
    E.require(type(context) is dict and set(context) == {
        'protocol', 'run_id', 'controller_commit', 'inputs_sha256', 'host_namespaces',
        'driver_files', 'source_files', 'runtime_sha256', 'pill_sha256', 'kernel_commit'})
    E.require(context['protocol'] == 'stead.saved8-rehearsal-context/1'
        and type(context['run_id']) is str and re.fullmatch('[0-9a-f]{32}', context['run_id'])
        and context['run_id'] == os.environ.get('STEAD_EXECUTION_ID')
        and type(context['controller_commit']) is str and re.fullmatch('[0-9a-f]{40}', context['controller_commit'])
        and E.digest(context['inputs_sha256']) and context['runtime_sha256'] == RUNTIME
        and context['pill_sha256'] == PILL and context['kernel_commit'] == KERNEL)
    E.require(type(context['host_namespaces']) is dict
        and set(context['host_namespaces']) == {'net', 'mnt', 'user', 'pid'})
    for name, prior in context['host_namespaces'].items():
        E.require(type(prior) is str and os.readlink('/proc/self/ns/' + name) != prior)
    E.require([name for _, name in socket.if_nameindex()] == ['lo']
        and not any(Path(path).exists() for path in ('/home', '/piers', '/root/.ssh'))
        and not Path('/state/zod').exists() and not Path('/state/zod').is_symlink())
    for name in ('previous', 'target', 'seed', 'drivers'):
        E.require(os.statvfs('/rehearsal/' + name).f_flag & os.ST_RDONLY)
    E.require(inventory('/rehearsal/seed') == SEED
        and type(context['driver_files']) is dict and set(context['driver_files']) == DRIVER_NAMES
        and all(E.digest(v) for v in context['driver_files'].values())
        and inventory('/rehearsal/drivers') == context['driver_files'])
    # The outer owner pins every controller/helper import; these exact mounts
    # are checked again before launch and after all native stages.
    E.require(os.environ.get('STEAD_RELEASE_INSTALL_CHILD') == '1'
        and type(context['source_files']) is dict and set(context['source_files']) == set(SOURCE_NAMES))
    for path, expected in context['source_files'].items():
        E.require(type(expected) is dict and set(expected) == SOURCE_NAMES[path]
            and all(E.digest(value) for value in expected.values())
            and os.statvfs(path).f_flag & os.ST_RDONLY
            and inventory(path) == expected)
    previous, old = package('previous', inventory)
    target, new = package('target', inventory)
    for field in ('agents', 'role', 'compatibility', 'saved_state_version', 'toolchain_sha256',
                  'contract_sha256', 'packager_sha256', 'shared_packager_sha256', 'qualification'):
        E.require(previous[field] == target[field])
    return previous, old, target, new


def native_class(release):
    class OwnedNative(release.ReleaseNative):
        def __init__(self, guard, sealed=None, expected=None):
            self.sealed, self.expected = sealed, expected
            self.last_command = None
            super().__init__('zod', 31337, guard)

        def _check_pier(self):
            if self.sealed is None:
                return super()._check_pier()
            E.require(self.expected is not None
                and release.stopped_home_checkpoint(self.pier, self.expected) == self.sealed)

        def _arguments(self):
            if self.sealed is None:
                return super()._arguments()
            return [self.binary, '-t', '-L', '--no-dock', '--loom', '31', '-b', '127.0.0.1',
                '-p', '31337', '--http-port', '18080', '--https-port', '18443', str(self.pier)]

        def dojo(self, source, timeout=60):
            E.require(type(source) is str and 0 < len(source.encode()) <= 65536
                and type(timeout) in (int, float) and 0 < timeout <= 180)
            count = len(self.commands)
            self.last_command = None
            try:
                self.last_command = command_observation(source)
            except BaseException:
                pass
            try:
                value = super().dojo(source, timeout=min(timeout, 60))
                try:
                    self.last_command = command_observation(source, value)
                except BaseException:
                    pass
                self.check()
                return value
            finally:
                # Native.dojo temporarily holds actual output in memory. The
                # retained command list contains hashes only, including chunks.
                for row in self.commands[count:]:
                    raw = row.pop('output').encode()
                    text = row.pop('source').encode()
                    row.update(source_sha256=E.sha(text), source_bytes=len(text),
                        output_sha256=E.sha(raw), output_bytes=len(raw))
                E.require(len(self.commands) <= 4096)
    return OwnedNative


def bootstrap(native, team_conn, prior):
    nonce, deadline = secrets.token_hex(32), time.monotonic() + 60
    raw = E.canonical({'protocol': 'stead.bootstrap/1', 'nonce': nonce})
    while (remaining := deadline - time.monotonic()) > 0:
        native.check()
        result = team_conn.run(native.binary, native.pier / '.urb/conn.sock', 'bootstrap',
            '/bootstrap/' + nonce, raw, target='zod', app='stead-home', timeout=min(15, remaining))
        native.check()
        value = (result.get('outcome') or {}).get('json')
        E.require(type(value) is dict)
        if (set(value) == {'protocol', 'status', 'home', 'nonce', 'incarnation'}
                and value['protocol'] == 'stead.bootstrap/1' and value['status'] == 'ready'
                and value['home'] == '~zod' and value['nonce'] == nonce
                and E.digest(value['incarnation'])):
            E.require(value['incarnation'] not in prior and time.monotonic() <= deadline)
            prior.add(value['incarnation'])
            return value
        E.require(value.get('protocol') == 'stead.test-terminal/1'
            and value.get('status') == 'failed' and value.get('kind') == 'poke-fail')
        time.sleep(.1)
    raise TimeoutError('Fixed saved8 restore readiness deadline')


def routes(native, release, ca, package_root):
    frontend = json.loads(read_regular(package_root / 'source/frontend.json', 262144), object_pairs_hook=E.unique)
    rows = [row for row in frontend['routes'] if row['route'].startswith('/stead/')]
    E.require(0 < len(rows) <= 32 and any(row['route'] == '/stead/' for row in rows))
    result = {'assets': [], 'denials': [], 'native_tls': True, 'browser_authentication': False}
    for row in rows:
        response = release.request_role(native, ca, 'GET', row['route'])
        release.assert_http(response, 200, mime=row['mime'], digest=row['sha256'], size=row['bytes'])
        result['assets'].append({'route': row['route'], 'sha256': row['sha256'], 'bytes': row['bytes']})
    common = {'Origin': release.HTTP_ORIGIN, 'Content-Type': 'application/json'}
    denied = [('wrong-host', 'GET', '/stead/', None, {'Host': 'foreign.invalid:18443'}, True),
        ('wrong-origin', 'GET', '/stead/', None, {'Origin': 'https://foreign.invalid'}, True),
        ('unknown-path', 'GET', '/stead/not-in-package', None, {}, True),
        ('query-string', 'GET', '/stead/?test=1', None, {}, True),
        ('unsupported-method', 'PUT', '/stead/', b'{}', common, True),
        ('post-to-asset', 'POST', '/stead/', b'{}', common, True),
        ('get-body', 'GET', '/stead/', b'{}', {}, True),
        ('forwarded-header', 'GET', '/stead/', None, {'Forwarded': 'proto=https'}, True),
        ('spoofed-plain-tls', 'GET', '/stead/', None, {'Forwarded': 'proto=https'}, False)]
    for name, method, route, body, headers, secure in denied:
        response = release.request_role(native, ca, method, route, body=body, headers=headers, secure=secure)
        release.assert_http(response, 403, mime='application/json', error='invalid_http_request')
        result['denials'].append(name)
    response = release.request_role(native, ca, 'GET', '/stead/', secure=False)
    E.require(response['status'] == 301 and response['headers'].get('location') == release.HTTP_ORIGIN + '/stead/'
              and response['body'] == b'')
    result['denials'].append('plain-http')
    response = release.request_role(native, ca, 'POST', '/stead/api/query', body=b'{}', headers=common)
    release.assert_http(response, 401, mime='application/json', error='session_required')
    result['denials'].append('anonymous-protected-api')
    response = release.request_role(native, ca, 'POST', '/stead/api/capabilities',
        body=b'{"protocol":"stead.capabilities/3"}', headers=common)
    release.assert_http(response, 200, mime='application/json')
    result['capabilities'] = E.capabilities(json.loads(response['body'], object_pairs_hook=E.unique))
    return result


def run(guard):
    """One fixed hosted child invocation; caller must still prove outer cleanup."""
    # The later fixed entry adds only /ci and /code before importing this
    # package. release_install's existing child loader adds /helpers,/support.
    E.require(os.environ.get('STEAD_RELEASE_INSTALL_CHILD') == '1')
    import release_install as release
    import execution_policy
    import native_tls
    import team_conn

    start = time.monotonic()
    native, finished, failed = None, False, False
    operation, context = 'admission', None
    rows, incarnations = {}, set()
    report = {'protocol': 'stead.saved8-asset-rehearsal/1', 'status': 'fail',
        'classification': 'disposable-synthetic-saved8-only', 'saved_version': 8,
        'qualifies_phase': False, 'live_pier_used': False, 'browser_authentication': False,
        'error_class': 'none', 'cleanup_error_class': 'none', 'phases': [], 'captures': {},
        'capture_custody': {}, 'commands': [], 'restarts': []}

    def current():
        guard()
        if time.monotonic() - start >= MAX_SECONDS:
            raise TimeoutError('Fixed saved8 total deadline')

    def suspend():
        native.dojo('|rein %release-test [%.n %stead-home]')
        release.wait_agent(native, 'stead-home', False, timeout=60)
        E.require(native.dojo(E.DESK).strip() == '%release-test')

    def resume():
        native.dojo('|rein %release-test [%.y %stead-home]')
        release.wait_agent(native, 'stead-home', True, timeout=60)
        return bootstrap(native, team_conn, incarnations)

    def retained(stage):
        nonlocal operation
        operation = 'capture-' + stage
        E.require(stage not in rows)
        before = native.proof()
        pid = native.process.pid
        value = E.collect(native.dojo, stage)
        after = native.proof()
        E.require(native.process.pid == pid and E.canonical(before) == E.canonical(after))
        rows[stage] = value
        report['captures'][stage] = E.metadata(value)
        active = seed_inventory if stage == 'seed8' else new if stage == 'assets-loaded' else old
        report['capture_custody'][stage] = {'pid': pid, 'process_proof_sha256': E.sha(E.canonical(after)),
            'desk_inventory_sha256': E.sha(E.canonical(active)),
            'context_sha256': E.sha(E.canonical(context))}
        return value

    def restart(expected, label, prior):
        nonlocal native
        current()
        E.require(label in ('cold', 'rollback-cold'))
        E.require(native.dojo(E.SUSPENDED).strip() == '%.n' and E.fingerprint(native.dojo) == prior)
        stopped = native.stop()
        E.require(E.canonical(stopped) == E.canonical(CLEAN_STOP))
        report['commands'].extend(native.commands)
        sealed = release.stopped_home_checkpoint(native.pier, expected)
        native.logpath.rename(Path('/state/zod-before-' + label + '.log'))
        current()
        native = Native(current, sealed=sealed, expected=expected)
        boot = native.start()
        E.require(native.dojo(E.SUSPENDED).strip() == '%.n' and E.fingerprint(native.dojo) == prior)
        release.clay_readback(native, expected, 'stead-home')
        E.require(native.readback(context['driver_files']))
        report['restarts'].append({'stage': label, 'cleanup': stopped, 'checkpoint': sealed, 'boot': boot})

    try:
        current()
        context = execution_policy.read_json('/execution/home-asset-rehearsal.json', maximum=1048576)
        previous, old, target, new = inputs(context, release.inventory)
        removed, replaced = release.asset_delta(old, new)
        report.update(run_id=context['run_id'], controller_commit=context['controller_commit'],
            inputs_sha256=context['inputs_sha256'], previous_artifact=ARCHIVES['previous'][1],
            target_artifact=ARCHIVES['target'][1], asset_delta={'removed': removed, 'updated': replaced})
        operation = 'seed-package'
        seed = Path('/state/seed-package')
        seed.mkdir(mode=0o700)
        for name in old:
            path = seed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path('/rehearsal/previous/desk') / name, path)
        for name in SEED:
            shutil.copyfile(Path('/rehearsal/seed') / name, seed / name)
        seed_inventory = dict(old) | SEED
        E.require(len(seed_inventory) == 117 and release.inventory(seed) == seed_inventory)
        Native = native_class(release)
        native = Native(current)
        E.require(native.lock['runtime']['binary_sha256'] == RUNTIME
            and native.lock['boot_artifact']['sha256'] == PILL and native.lock['kernel']['commit'] == KERNEL)
        operation = 'fresh-boot'
        report['boot'] = native.start()
        operation = 'driver-install'
        E.require(native.install(Path('/rehearsal/drivers')) == context['driver_files'])
        operation = 'seed-install'
        E.require(release.install_desk(native, 'stead-home', seed) == seed_inventory)
        operation = 'seed-ready'
        release.wait_agent(native, 'stead-home', True, timeout=300)
        operation = 'seed-suspend'
        suspend()
        first = retained('seed8')
        report['phases'].append('fresh-seed8')
        operation = 'predecessor-replace'
        release.replace_clay_files(native, seed_inventory, old, package=Path('/rehearsal/previous/desk'))
        E.require(native.dojo(E.SUSPENDED).strip() == '%.n'
            and E.fingerprint(native.dojo) == first['vase_fingerprint']
            and native.dojo('.^(? %cu /=release-test=/lib/stead-home-ui-seed/hoon)').strip() == '%.n')
        operation = 'tls'
        certificates = native_tls.create('/state/certificates')
        native_tls.install(native.binary, native.pier / '.urb/conn.sock', certificates, 'zod')
        report['tls'] = native_tls.verify(native.process, certificates, 'zod', native.check)
        operation = 'predecessor-resume'
        report['bootstrap_a0'] = resume()
        operation = 'predecessor-routes'
        report['routes_a0'] = routes(native, release, certificates / 'ca.pem', Path('/rehearsal/previous'))
        operation = 'predecessor-suspend'
        suspend()
        loaded = retained('a0-loaded')
        E.preserved(first, loaded, complete=False)
        report['phases'].append('actual-a0-predecessor')
        operation = 'cold-restart'
        restart(old, 'cold', loaded['vase_fingerprint'])
        native_tls.install(native.binary, native.pier / '.urb/conn.sock', certificates, 'zod')
        operation = 'cold-resume'
        report['bootstrap_cold'] = resume()
        operation = 'cold-suspend'
        suspend()
        E.preserved(loaded, retained('a0-cold'), complete=True)
        report['phases'].append('cold-repeat')
        operation = 'asset-replace'
        release.replace_clay_assets(native, old, new, package=Path('/rehearsal/target/desk'))
        E.require(native.dojo(E.SUSPENDED).strip() == '%.n' and E.fingerprint(native.dojo) == loaded['vase_fingerprint'])
        operation = 'asset-resume'
        report['bootstrap_assets'] = resume()
        operation = 'asset-routes'
        report['routes_assets'] = routes(native, release, certificates / 'ca.pem', Path('/rehearsal/target'))
        operation = 'asset-suspend'
        suspend()
        assets = retained('assets-loaded')
        E.preserved(loaded, assets, complete=False)
        operation = 'rollback-replace'
        release.replace_clay_assets(native, new, old, package=Path('/rehearsal/previous/desk'))
        E.require(native.dojo(E.SUSPENDED).strip() == '%.n' and E.fingerprint(native.dojo) == assets['vase_fingerprint'])
        operation = 'rollback-resume'
        report['bootstrap_rollback'] = resume()
        operation = 'rollback-routes'
        report['routes_rollback'] = routes(native, release, certificates / 'ca.pem', Path('/rehearsal/previous'))
        operation = 'rollback-suspend'
        suspend()
        rollback = retained('rollback-loaded')
        E.preserved(loaded, rollback, complete=False)
        operation = 'rollback-restart'
        restart(old, 'rollback-cold', rollback['vase_fingerprint'])
        native_tls.install(native.binary, native.pier / '.urb/conn.sock', certificates, 'zod')
        operation = 'rollback-cold-resume'
        report['bootstrap_rollback_cold'] = resume()
        operation = 'rollback-cold-suspend'
        suspend()
        E.require(E.fingerprint(native.dojo) == rollback['vase_fingerprint'])
        report['phases'].append('assets-and-rollback')
        operation = 'final-inputs'
        E.complete_stages(rows)
        # Recheck all immutable input bytes; the fresh-pier-only admission
        # predicate intentionally cannot be called after boot.
        package('previous', release.inventory)
        package('target', release.inventory)
        E.require(release.inventory('/rehearsal/seed') == SEED
            and release.inventory('/rehearsal/drivers') == context['driver_files'])
        for path, expected in context['source_files'].items():
            E.require(release.inventory(path) == expected)
        current()
        finished = True
    except BaseException as error:
        failed = True
        name = type(error).__name__
        report['error_class'] = name if name in ('ValueError', 'TimeoutError', 'RuntimeError', 'OSError', 'InterruptedError') else 'other'
        # Failure-only observations cannot replace the original failure or
        # relax cleanup/admission. No exception message, local or raw noun leaves.
        report['diagnostic'] = {'operation': operation, 'last_command': None,
            'positions': None, 'native_log': None}
        try:
            if native is not None:
                report['diagnostic']['last_command'] = native.last_command
            if hasattr(error, 'projection_results'):
                report['diagnostic']['conditions'] = error.projection_results
                report['diagnostic']['condition_errors'] = error.projection_diagnostics
            sources = {}
            for label, (root, path) in DIAGNOSTIC_SOURCES.items():
                raw = read_regular(Path(root) / path, 262144)
                sources[label] = {'raw': raw, 'filename': str(Path(root) / path),
                    'sha256': context['source_files'][root][path]}
            report['diagnostic']['positions'] = failure_positions(error, sources)
        except BaseException:
            pass
    finally:
        if native is not None:
            try:
                report['cleanup'] = native.stop()
                report['commands'].extend(native.commands)
                E.require(E.canonical(report['cleanup']) == E.canonical(CLEAN_STOP))
            except BaseException:
                report['cleanup_error_class'] = 'cleanup-refusal'
        else:
            report['cleanup'] = {'started': False, 'reaped': True}
        if failed and native is not None and report.get('cleanup', {}).get('reaped') is True:
            try:
                report['diagnostic']['native_log'] = log_observation(native.logpath)
            except BaseException:
                pass
        if finished and not failed and report['error_class'] == report['cleanup_error_class'] == 'none':
            try:
                # Exclusive, fixed artifacts are written only after clean child
                # reap. The outer guardian must still prove its whole cgroup.
                current()
                destination = Path('/state/home-captures')
                destination.mkdir(mode=0o700)
                for stage in E.STAGES:
                    value = rows[stage]
                    descriptor = E.metadata(value) | {'run_id': context['run_id'],
                        'controller_commit': context['controller_commit'], 'inputs_sha256': context['inputs_sha256'],
                        'previous_artifact_sha256': ARCHIVES['previous'][1], 'target_artifact_sha256': ARCHIVES['target'][1],
                        'runtime_sha256': RUNTIME, 'kernel_commit': KERNEL,
                        'capture_custody': report['capture_custody'][stage],
                        'qualifies_phase': False, 'classification': 'synthetic-actual-saved8-rehearsal'}
                    for suffix, data in (('.jam', value['data']), ('.json', E.canonical(descriptor) + b'\n')):
                        with (destination / (stage + suffix)).open('xb') as stream:
                            os.fchmod(stream.fileno(), 0o600)
                            stream.write(data)
                            stream.flush()
                            os.fsync(stream.fileno())
                descriptor = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                current()
                E.require(len(E.canonical(report)) <= 4 * 1024 * 1024)
                report['status'] = 'pass'
            except BaseException:
                report['cleanup_error_class'] = 'artifact-refusal'
        report['elapsed_ms'] = int((time.monotonic() - start) * 1000)
    return report

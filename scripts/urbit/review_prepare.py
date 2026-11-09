"""Manual synthetic review initialization; never a qualification runner.

Resume trusts a checked stopped-pier snapshot, then proves startup suspension
and supported saved-state shape before reloading the same native application.
No browser session, draft, grant or accepted command is replayed here.
"""
from pathlib import Path
import json
import re
import shutil

import execution_policy
import native_install
import native_tls
import team_check
import team_conn
import team_lifecycle
from digests import sha, tree_sha


def hoon_inventory(native):
    return {str(p.relative_to(native)): sha(p) for p in sorted(Path(native).rglob('*.hoon'))
            if p.relative_to(native).as_posix() != 'web/stead/inventory.hoon'}


def durable_fingerprint(ship, dojo):
    """Hash retained authority/content, excluding the home's derived index.

    Clay can revive an idle app while importing changed asset dependencies.
    Home on-load rebuilds its projection, but on-save retains the original
    target db throughout restoration. A v4 Home also retains its Code repos.
    Identity persists only config/counter.
    Typed extraction still rejects a foreign/future saved-state envelope.
    """
    app = team_lifecycle.APPS[ship]
    if dojo(ship, f'.^(desk %gd /={app}=/$)').strip() != '%base':
        raise ValueError('Review durable state is not on the verified desk')
    source = (f'=/  egg=egg-any:gall  .^(egg-any:gall %gv /={app}=/$)  '
              f'?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  '
              '^-  @ux  ')
    if ship == 'zod':
        source += (
            '?:  ?=([%stead-home %3 *] q.saved)  '
            '=/  stored  !<([%stead-home %3 db=* projection=*] saved)  '
            '(shax (jam db.stored))  '
            '?>  ?=([%stead-home %4 *] q.saved)  '
            '=/  stored  !<([%stead-home %4 team=[db=* projection=*] code=*] saved)  '
            '(shax (jam [db.team.stored code.stored]))')
    else:
        source += ('=/  stored  !<([%stead-identity %1 config=* counter=@ud] saved)  '
                   '(shax (jam stored))')
    result = dojo(ship, source).strip()
    if not re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*', result):
        raise ValueError('Native durable-state fingerprint is not a hash')
    value = int(result.replace('.', ''), 16)
    if value >= 2 ** 256:
        raise ValueError('Native durable-state fingerprint exceeds SHA-256')
    return f'{value:064x}'


def verify_durable_before_admission(host, expected, call, require):
    """Finish every restore and compare all retained state before any release."""
    team = host['TEAM']
    acknowledgements = {}
    for ship in host['SHIPS']:
        acknowledgements[ship] = team_check.bootstrap_ready(team, ship, call, host['execution_check'])
        if ship in expected:
            observed = durable_fingerprint(ship, host['dojo'])
            require(ship + ' durable state unchanged after asset reload and restore', observed == expected[ship])
            host['record']('review durable state preserved ' + ship,
                           {'before_sha256': expected[ship], 'after_sha256': observed,
                            'home_projection_rebuilt': ship == 'zod'})
    return acknowledgements


class ReviewLifecycle(team_lifecycle.TeamLifecycle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.review = execution_policy.read_json('/state/review.json')
        certificates = Path('/state/review-tls')
        if not certificates.exists():
            shutil.copytree(self.certificates, certificates)
            certificates.chmod(0o700)
        else:
            with execution_policy.directory_fd(certificates):
                if certificates.stat().st_mode & 0o077:
                    raise ValueError('Review TLS trust must be private')
                for source in certificates.iterdir():
                    if source.is_symlink() or not source.is_file() or source.stat().st_mode & 0o077:
                        raise ValueError('Review TLS trust contains an unsafe entry')
            # Keep the run-local fixture contract pointing at the actual native
            # TLS identity. The newly generated, unused bootstrap keys remain
            # private evidence; no prior user trust material is removed.
            self.certificates.rename(self.directory / 'unused-bootstrap-tls')
            shutil.copytree(certificates, self.certificates)
        if certificates.is_symlink() or certificates.stat().st_mode & 0o077:
            raise ValueError('Review certificates must be private and unredirected')
        for ship in native_tls.HOSTS:
            native_tls.pem(certificates / (ship + '-key.pem'), private=True)
            native_tls.pem(certificates / (ship + '.pem'), private=False)
        native_tls.pem(certificates / 'ca.pem', private=False)
        # Existing certificate verification/ingress readers use this run path.
        # The bytes remain identical to the stable private review trust root.

    def launch(self, ship, arguments, **kwargs):
        if self.review['mode'] == 'resume':
            expected = self.review['stopped_piers'][ship]
            if tree_sha(Path('/state/live') / ship) != expected:
                raise ValueError('Stopped review pier changed after admission')
            # The ordinary lane requires a pre-captured native saved hash. A
            # recovered review instead starts from exact inspected disk bytes.
            # Its app remains suspended and fenced until the checks below.
            self.restart_expected[ship] = 'checked-stopped-review'
        return super().launch(ship, arguments, **kwargs)

    def suspension_checkpoint(self, ship, dojo):
        if self.review['mode'] == 'resume':
            if dojo(ship, f'.^(? %gu /={team_lifecycle.APPS[ship]}=/$)').strip() != '%.n':
                raise ValueError('Recovered review application was not suspended')
            if not self.exists_on_base(ship, dojo):
                raise ValueError('Recovered review application is missing')
            self.restart_expected[ship] = self.saved_fingerprint(ship, dojo)
            self.record('review recovered saved state ' + ship,
                        {'saved_vase_sha256': self.restart_expected[ship],
                         'stopped_pier_sha256': self.review['stopped_piers'][ship]})
        super().suspension_checkpoint(ship, dojo)


def run(host):
    state = host['STATE']
    metadata = execution_policy.read_json(state / 'review.json')
    if metadata['toolchain_sha256'] != sha('/toolchain.json'):
        raise ValueError('Review toolchain changed; explicit migration is required')
    if metadata['native_hoon'] != hoon_inventory(Path('/native/core/desk')):
        raise ValueError('Review native code changed; explicit migration is required')
    team = host['TEAM']
    fresh = metadata['mode'] == 'new'
    before = host['execution_check'](preflight=True)
    binary = '/runtime/' + host['LOCK']['runtime']['binary']
    retained = {}

    def require(name, condition):
        if not condition:
            raise ValueError('Review startup failed: ' + name)

    def command(ship, source, expected=None):
        result = host['dojo'](ship, source)
        if expected is not None:
            require(ship + ' native readback', result.strip() == expected)
        return result

    def call(ship, mode, value, *, target='zod', app='stead-home', route=None, timeout=75):
        host['execution_check']()
        result = team_conn.run(binary, host['LIVE'] / ship / '.urb/conn.sock', mode,
                              route or '/', team_check.canonical(value), target=target, app=app, timeout=timeout)
        outcome = (result.get('outcome') or {}).get('json')
        require(ship + ' native response', isinstance(outcome, dict))
        return outcome

    if fresh:
        if host['LIVE'].exists():
            raise ValueError('Fresh review refuses an existing live directory')
        host['copy_seed_to_live']()
    for ship in host['SHIPS']:
        host['PROGRESS']['stage'] = 'preparing review ~' + ship
        host['launch'](ship, fresh=fresh)
        host['wait_ready'](ship)
        if not fresh:
            retained[ship] = durable_fingerprint(ship, host['dojo'])
            host['record']('review retained state before asset import ' + ship,
                           {'durable_sha256': retained[ship]})
        native_install.install(host, ship, command, require)
        if not fresh:
            # A Clay dependency update may already have revived this agent.
            # The supported rein sequence suspends and reloads it again while
            # ingress/peers remain blocked. Derived projection bytes may change.
            team.reinstall(ship, host['dojo'])
        else:
            command(ship, '|start %' + team_lifecycle.APPS[ship])

    if fresh:
        now = int(command('zod', '(div (mul 1.000 (sub now ~1970.1.1)) ~s1)').strip().replace('.', ''))
        config = team_check.configuration(now)
        # Long-lived synthetic membership is distinct from the guarded two-hour
        # native execution. Existing adopted authority is never renewed here.
        for binding in config['bindings'].values():
            binding['expires_at_ms'] = str(now + 7 * 86400000)
        require('home configuration', call('zod', 'configure', config) == {})
        for offset, ship in enumerate(('bus', 'nec', 'bud'), start=8444):
            personal = {'protocol': 'stead.identity-config/1', 'expected_revision': '0',
                        'home': '~zod', 'home_origin': config['origin'],
                        'origin': f'https://{ship}.localhost:{offset}'}
            require(ship + ' identity configuration', call(ship, 'identity-config', personal,
                    target=ship, app='stead-identity') == {})
        metadata['binding_expires_at_ms'] = now + 7 * 86400000
    acknowledgements = verify_durable_before_admission(host, retained, call, require)
    for ship in host['SHIPS']:
        native_tls.install(binary, host['LIVE'] / ship / '.urb/conn.sock', team.certificates, ship)
    for ship in host['SHIPS']:
        team.admit(ship, acknowledgements[ship], host['dojo'])
    execution_policy.write_json(team.directory / 'browser-fixture.json', {
        'format': 1, 'classification': 'private-disposable-browser-fixture',
        'execution_id': before['run_id'], 'origin': 'https://home.localhost:8443',
        'identities': {ship: {'hostname': native_tls.HOSTS[ship],
                             'code': host['dojo'](ship, '+code').strip().strip('~')}
                       for ship in ('bus', 'nec', 'bud')}})
    metadata['initialized'] = True
    execution_policy.write_json(state / 'review.json', metadata)
    (state / 'unclean-live.json').unlink(missing_ok=True)

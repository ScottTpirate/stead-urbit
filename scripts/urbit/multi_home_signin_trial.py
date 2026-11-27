"""Exercise two running Homes with one independently enrolled planet on an isolated worker."""
from pathlib import Path
import re
import time

import native_tls
from solo_signin_trial import (
    INVITATION, Site, SoftwareAuthenticator, bootstrap, certificates, check,
    owner_call, projects, sign_in, uid, wait_for,
)


def configure(native, home_name, identity_name, suffix):
    """Install distinct web origins and give only the site's own planet a founding membership."""
    ship = '~' + native.ship
    check(native.pier == Path('/state') / native.ship, 'disposable pier')
    check(native.dojo('.^(? %j /(scot %p our)/fake/(scot %da now))').strip() == '%.y', 'fake guard')
    ca = certificates(native, home_name, identity_name)
    port = native_tls.PORTS[native.ship]
    home, identity = Site(home_name, ca, port), Site(identity_name, ca, port)
    for app in ('stead-home', 'stead-identity'):
        native.dojo(f'|rein %base [%.y %{app}]')
        wait_for(lambda: native.dojo(f'.^(? %gu /={app}=/$)').strip(),
                 lambda value: value == '%.y', app + ' running', 90)
    principal = uid(suffix + 1)
    org, team = uid(suffix + 2), uid(suffix + 3)
    config = {
        'protocol': 'stead.team-config/1', 'expected_revision': '0', 'home': ship, 'origin': home.origin,
        'organization_id': org, 'team_id': team, 'custody': 'local-disposable', 'runtime': 'isolated-fake',
        'bindings': {ship: {'principal_id': principal, 'binding_id': uid(suffix + 4),
                            'binding_revision': '1', 'active': 'yes', 'display_name': 'Founding member',
                            'expires_at_ms': str(int(time.time() * 1000) + 14 * 86400000)}},
        'project_creators': {principal: 'yes'},
    }
    check(owner_call(native, 'home', 'configure', config) == {}, 'explicit founder')
    check(owner_call(native, 'identity', 'identity-config', {
        'protocol': 'stead.identity-config/2', 'expected_revision': '0', 'origin': identity.origin,
    }) == {}, 'independent Identity origin')
    for app in ('home', 'identity'):
        bootstrap(native, app)
    code = native.dojo('+code').strip().lstrip('~')
    check(re.fullmatch(r'[a-z]{6}(?:-[a-z]{6}){3}', code), 'disposable owner login')
    status, _ = identity.request('POST', '/~/login', {'password': code, 'redirect': '/stead-identity/'}, form=True)
    check(status in (200, 302, 303) and any(k.startswith('urbauth-') for k in identity.cookies), 'owner login')
    sign_in(home, identity, member_ship=ship, home_ship=ship, previously_trusted=False)
    project = uid(suffix + 5)
    command = {'protocol': 'stead.command/3', 'request_id': uid(suffix + 6),
               'project_id': project, 'resource_id': project, 'expected_revision': '0',
               'authority_epoch': '1', 'operation': 'project.create', 'payload': {
                   'organization_id': org, 'owning_team_id': team, 'project_key': 'EXAMPLE',
                   'title': 'Private project', 'preset': 'general'}}
    check(home.post('/stead/api/command', command).get('status') == 'accepted', 'founder project')
    return ca, home, identity, project


def run(first, second):
    check((first.ship, second.ship) == ('zod', 'nec'), 'designated disposable fixtures')
    ca_a, home_a, identity, project_a = configure(first, 'home.localhost', 'identity.localhost', 400)
    ca_b, owner_b, identity_b, project_b = configure(second, 'nec.localhost', 'id-nec.localhost', 500)
    print('Two Homes and four independent HTTPS origins ready', flush=True)
    authenticator = SoftwareAuthenticator(first, identity, ca_a)
    authenticator.enroll()
    issue = owner_b.post('/stead/api/invitations', {
        'protocol': INVITATION, 'action': 'issue', 'project_id': project_b, 'role': 'reader',
        'mode': 'personal', 'identity_ship': '~zod', 'expires_at_ms': '', 'use_limit': '1',
    })
    check(issue.get('status') == 'issued', 'guest-specific link')
    check(owner_b.post('/stead/auth/logout', {'protocol': 'stead.auth/1'}).get('status') == 'logged_out',
          'inviter has signed out')
    guest = Site(owner_b.host, ca_b, owner_b.port)
    receipt = sign_in(guest, identity, invite=issue['token'], home_ship='~nec', previously_trusted=False)
    check(receipt.get('project_id') == project_b, 'invited project')
    check({(r['project_id'], r['role']) for r in projects(guest, 601).values()} == {(project_b, 'reader')},
          'guest receives one Reader grant')
    for number, (founder, ca, ship, project, role) in enumerate((
        (owner_b, ca_b, '~nec', project_b, 'reader'), (home_a, ca_a, '~zod', project_a, 'maintainer'),
    ), start=602):
        returning = Site(founder.host, ca, founder.port)
        sign_in(returning, identity, authenticator=authenticator, home_ship=ship, previously_trusted=True)
        check({(r['project_id'], r['role']) for r in projects(returning, number).values()} == {(project, role)},
              'current authority on the selected Home')
    check(guest.post('/stead/auth/devices', {'protocol': 'stead.devices/1', 'action': 'remember',
                                            'value': 'Remembered guest'})['status'] == 'remembered',
          'explicit device trust on the guest Home')
    authenticator.remove()
    fallback = Site(owner_b.host, ca_b, owner_b.port)
    sign_in(fallback, identity, home_ship='~nec', previously_trusted=True)
    check(projects(fallback, 605), 'native recovery after passkey removal')
    maintainer = Site(owner_b.host, ca_b, owner_b.port)
    sign_in(maintainer, identity_b, member_ship='~nec', home_ship='~nec', previously_trusted=True)
    removed = maintainer.post('/stead/api/invitations', {
        'protocol': INVITATION, 'action': 'remove', 'project_id': project_b,
        'invitation_id': issue['invitation_id'], 'identity_ship': '~zod',
    })
    check(removed['status'] == 'removed' and not projects(guest, 606) and not projects(fallback, 607),
          'grant removal cuts access in both the remembered and ordinary guest sessions')
    check({r['project_id'] for r in projects(home_a, 608).values()} == {project_a}, 'other Home stays accessible')
    print('Passed two-Home sign-in, single enrollment, offline inviter, scoped roles and ordinary recovery', flush=True)

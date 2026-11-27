"""Exercise a real Home and Identity on one isolated, disposable fake planet.

The caller installs the exact candidate desk and starts its pinned Native
fixture with --https-port 18443. All requests remain on the worker's loopback.
Only stage names and assertions are intended for the qualification transcript.
"""
import hashlib
import http.client
from http.cookies import SimpleCookie
import json
from pathlib import Path
import re
import secrets
import socket
import ssl
import sys
import subprocess
import time
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

import core_conn
import native_tls
import team_conn

PORT = 18443
HOME = 'home.localhost'
IDENTITY = 'identity.localhost'
SHIP = '~zod'
PROTOCOL = 'stead.auth/2'
INVITATION = 'stead.invitation/1'


def check(condition, name):
    if not condition:
        raise ValueError('Solo fixture: ' + name)


def wait_for(observe, predicate, name, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = observe()
        if predicate(value):
            return value
        time.sleep(.15)
    raise TimeoutError('Solo fixture: ' + name)


def uid(n):
    return '019939ba-4000-7000-8000-' + str(n).zfill(12)


class Site:
    def __init__(self, host, ca, port=PORT):
        self.host = host
        self.port = port
        self.origin = f'https://{host}:{port}'
        self.context = ssl.create_default_context(cafile=str(ca))
        self.cookies = {}
        self.cookie_ttls = {}
        self.csrf = ''

    def request(self, method, path, data=None, form=False):
        check(path.startswith('/'), 'site-relative request')
        headers = {'Host': f'{self.host}:{self.port}', 'Origin': self.origin}
        if self.cookies:
            headers['Cookie'] = '; '.join(name + '=' + value for name, value in self.cookies.items())
        if self.csrf:
            headers['X-Stead-CSRF'] = self.csrf
        body = None
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
            body = (urlencode(data) if form else json.dumps(data,separators=(',',':'))).encode()
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=8)
        try:
            raw = socket.create_connection(('127.0.0.1', self.port), timeout=5)
            connection.sock = self.context.wrap_socket(raw, server_hostname=self.host)
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            result = response.read(262145)
            check(len(result) <= 262144, 'bounded response')
            for cookie in response.headers.get_all('Set-Cookie') or []:
                pair = SimpleCookie(cookie)
                for name, field in pair.items():
                    check(not field['domain'], 'host-only cookie')
                    if field.value and field['max-age'] != '0':
                        self.cookies[name] = field.value
                        if field['max-age']:
                            self.cookie_ttls[name] = int(field['max-age'])
                    else:
                        self.cookies.pop(name, None)
                        self.cookie_ttls.pop(name, None)
            return response.status, result
        finally:
            connection.close()

    def post(self, path, payload):
        status, result = self.request('POST',path,payload)
        check(status == 200, f'{path} returned {status}')
        value = json.loads(result)
        check(isinstance(value, dict), 'JSON object')
        return value


def certificates(native, home_host=HOME, identity_host=IDENTITY):
    directory = Path('/state') / ('solo-certificates-' + native.ship)
    hosts = [home_host, identity_host, native_tls.HOSTS[native.ship]]
    check(all(re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+',host) for host in hosts),
          'synthetic DNS names')
    alt_names = ','.join('DNS:'+host for host in dict.fromkeys(hosts))
    # The pinned Eyre TLS listener serves exactly one native certificate. Give
    # the synthetic certificate SANs for the two independent browser hosts.
    directory.mkdir(mode=0o700)
    ca = directory / 'ca.pem'
    key = directory / (native.ship+'-key.pem')
    csr = directory / (native.ship+'.csr')
    crt = directory / (native.ship+'.pem')
    native_tls.openssl('req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes',
                       '-x509','-days','1','-subj','/CN=Stead solo fixture CA','-addext','basicConstraints=critical,CA:true',
                       '-keyout',directory/'ca-key.pem','-out',ca)
    native_tls.openssl('req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes',
                       '-subj','/CN='+home_host,'-keyout',key,'-out',csr)
    extension = directory / 'server.ext'
    extension.write_text('basicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\n'
                         f'subjectAltName={alt_names}\n')
    native_tls.openssl('x509','-req','-days','1','-in',csr,'-CA',ca,'-CAkey',directory/'ca-key.pem',
                       '-set_serial','1','-extfile',extension,'-out',crt)
    for path in directory.iterdir():
        path.chmod(0o600)
    native_tls.install(native.binary, native.pier/'.urb/conn.sock', directory, native.ship)
    native_tls.verify(native.process, directory, native.ship, native.check)
    return ca


def owner_call(native, app, mode, value, path='/'):
    out = team_conn.run(native.binary, native.pier/'.urb/conn.sock', mode, path,
                        json.dumps(value, separators=(',',':')).encode(), target=native.ship, app='stead-'+app)
    result = (out.get('outcome') or {}).get('json')
    check(isinstance(result, dict), 'owner-local command returned a JSON object')
    return result


def bootstrap(native, app):
    def attempt():
        nonce = secrets.token_hex(32)
        return owner_call(native, app, 'bootstrap', {'protocol':'stead.bootstrap/1','nonce':nonce}, '/bootstrap/'+nonce)
    wait_for(attempt, lambda value:value.get('status') == 'ready', app+' bootstrap',60)


def sign_in(home, identity, invite=None, authenticator=None, *, previously_trusted=None,
            member_ship=SHIP, home_ship=SHIP):
    protocol = INVITATION if invite else PROTOCOL
    path = '/stead/auth/invite/' if invite else '/stead/auth/'
    payload = {'protocol':protocol,'identity_ship':member_ship}
    if invite:
        payload['token'] = invite
    begun = home.post(path+'start',payload)
    key = begun.get('challenge_id','')
    check(begun.get('status') == 'pending' and re.fullmatch(r'[0-9a-f]{64}',key), 'pending challenge')
    attempt = {'protocol':protocol, 'challenge_id':key}
    wait_for(lambda:home.post(path+'status',attempt),
             lambda value:value.get('identity_origin') == identity.origin, 'native address discovery')
    listed = identity.post('/stead-identity/api/list',{'protocol':'stead.identity/2'})
    row = listed['requests'][key]
    check(row['origin'] == home.origin and row['home'] == home_ship and row['identity_ship'] == member_ship and row['direct'] == 'yes',
          'native Home and member identities and isolated origins')
    check(row['purpose'] == ('project-invitation' if invite else 'member-session'), 'correct purpose')
    trusted = bool(invite) if previously_trusted is None else previously_trusted
    check(row['trusted'] == ('yes' if trusted else 'no'), 'explicit consent persisted for this Home')
    if authenticator is None:
        approved = identity.post('/stead-identity/api/approve',{
            'protocol':'stead.identity/1' if trusted else 'stead.identity-consent/1', 'challenge_id':key,
            'origin':row['origin'], 'csrf':row['csrf'], 'comparison_code':row['comparison_code']})
        check(approved.get('status') == 'sent', 'owner approved')
    else:
        approved = authenticator.sign(key)
        check(approved.get('status') == 'ok' and approved.get('challenge_id') == key
              and approved.get('origin') == home.origin and approved.get('home') == home_ship,
              'real passkey verifier approved native request')
    proof = approved.get('return_proof','')
    check(re.fullmatch(r'[0-9a-f]{64}', proof), 'approving-browser return proof')
    observed = wait_for(lambda:home.post(path+'status',attempt),lambda value:value.get('status') == 'approved',
                        'native ship approval')
    check('return_proof' not in observed and 'return_digest' not in observed, 'status contains no return secret')
    failed, body = home.request('POST', path+'consume',dict(attempt,return_proof='0'*64))
    check(failed >= 400 or json.loads(body).get('status') != 'authenticated', 'reject incorrect return proof')
    accepted = home.post(path+'consume',dict(attempt,return_proof=proof))
    check(accepted.get('status') == 'authenticated', 'accepted Home session')
    home.csrf = accepted['csrf']
    return accepted


def projects(site, request):
    query = {'protocol':'stead.query/3','kind':'projects','request_id':uid(request),
             'project_id':'','resource_id':'','container_id':'','search':'','cursor':''}
    return site.post('/stead/api/query',query)['rows']


def configure_verifier(native, secret):
    wire = core_conn.atom(json.dumps({'protocol':'stead.verifier-config/1','secret':secret}).encode())
    noun = f'[32 %fyrd [%base %stead-pilot-owner %noun [%noun [~{native.ship} %stead-identity %verifier-config ~ {wire}]]]]'
    try:
        result = core_conn.exchange(native.binary, native.pier/'.urb/conn.sock', noun)
        check((result.get('outcome') or {}).get('json') == {}, 'owner configured verifier')
    except Exception:
        raise RuntimeError('Solo fixture: verifier configuration failed') from None


class SoftwareAuthenticator:
    """Only the exercising key is synthetic. Both verifiers are production code."""

    def __init__(self, native, identity, ca):
        sys.path[:0] = ['/runtime/solo-python','/src/passkey-src']
        from cryptography.hazmat.primitives.asymmetric import ec
        from fido2.cose import ES256
        from fido2.webauthn import AttestedCredentialData
        from stead_identity_passkeys.bridge import LocalIdentity
        from stead_identity_passkeys.verifier import Verifier
        self.identity = identity
        secret = secrets.token_hex(32)
        configure_verifier(native, secret)
        self.verifier = Verifier(Path('/state/solo-passkeys.db'),'~'+native.ship,identity.origin,
                                 LocalIdentity(identity.origin,identity.port,secret,ca))
        self.counter = 0
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential = AttestedCredentialData.create(bytes(16),secrets.token_bytes(32),
                                                        ES256.from_cryptography_key(self.key.public_key()))

    def ticket(self, action):
        value = self.identity.post('/stead-identity/api/ticket',{'protocol':'stead.passkey-ticket/1','action':action})
        check(value.get('status')=='ok','native owner ticket')
        return value['ticket']

    def response(self, options, register):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from fido2.utils import websafe_encode
        from fido2.webauthn import AttestationObject, AuthenticatorData, CollectedClientData
        client = CollectedClientData.create('webauthn.create' if register else 'webauthn.get',
                                             options['publicKey']['challenge'],self.identity.origin)
        flags = AuthenticatorData.FLAG.UP | AuthenticatorData.FLAG.UV
        data = AuthenticatorData.create(hashlib.sha256(self.identity.host.encode()).digest(),
                                        flags | AuthenticatorData.FLAG.AT if register else flags,
                                        0 if register else self.counter, self.credential if register else b'')
        response = {'clientDataJSON':client.b64}
        if register:
            response['attestationObject'] = websafe_encode(AttestationObject.create('none',data,{}))
        else:
            response.update(authenticatorData=websafe_encode(data),userHandle=websafe_encode(self.verifier.user.id),
                            signature=websafe_encode(self.key.sign(data+client.hash,ec.ECDSA(hashes.SHA256()))))
        key = websafe_encode(self.credential.credential_id)
        return {'ceremony':options['ceremony'],'credential':{'id':key,'rawId':key,'type':'public-key','response':response}}

    def enroll(self):
        options = self.verifier.dispatch('register/begin',{'ticket':self.ticket('register'),'label':'Synthetic hardware'})
        check(self.verifier.dispatch('register/finish', self.response(options,True))['status']=='ok','real FIDO enrollment')

    def sign(self, challenge):
        self.counter += 1
        options = self.verifier.dispatch('authenticate/begin',{'challenge_id':challenge})
        return self.verifier.dispatch('authenticate/finish',self.response(options,False))

    def remove(self):
        keys = self.verifier.dispatch('list',{'ticket':self.ticket('list')})['credentials']
        check(len(keys)==1,'list enrolled software credential')
        result = self.verifier.dispatch('revoke',{'ticket':self.ticket('revoke'),'id':keys[0]['id']})
        check(result.get('status')=='ok' and not self.verifier.dispatch('list',{'ticket':self.ticket('list')})['credentials'],
              'native owner removal')


def git_credentials(home, project):
    envelope = {'protocol':'stead.code/1', 'project_id':project}
    result = home.post('/stead/api/code', dict(envelope, action='create'))
    check(result.get('status')=='ready', 'create Code repository')
    result = home.post('/stead/api/code', dict(envelope, action='issue', access='read'))
    bearer = result.get('bearer','')
    check(re.fullmatch(r'[0-9a-f]{64}',bearer), 'issue scoped Git credential')
    return bearer


def git_refs(home, project, ca, bearer=None):
    with TemporaryDirectory(dir='/state') as directory:
        root = Path(directory)
        ask = root/'prompt'
        ask.write_text('#!/bin/sh\ncase "$1" in Username*) echo stead;; Password*) cat "$STEAD_TEST_KEY";; *) exit 1;; esac\n')
        ask.chmod(0o700)
        key = root/'credential'
        if bearer:
            key.write_text(bearer)
            key.chmod(0o600)
        env = {'PATH':'/usr/bin:/bin', 'HOME':directory, 'LANG':'C', 'GIT_CONFIG_NOSYSTEM':'1',
               'GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0','GIT_ALLOW_PROTOCOL':'https',
               'GIT_ASKPASS':str(ask) if bearer else '/bin/false','GIT_SSL_CAINFO':str(ca),
               'STEAD_TEST_KEY':str(key)}
        command = ['/usr/bin/git','-c','credential.helper=','-c','http.followRedirects=false',
                   '-c',f'http.curloptResolve={home.host}:{home.port}:127.0.0.1','ls-remote',home.origin+'/stead/git/'+project+'.git']
        child = subprocess.run(command,env=env,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL,timeout=15)
        check((child.returncode==0) == bool(bearer),'Git credential admission')
        check(len(child.stdout)<=8192,'bounded Git ref list')
        return child.stdout


def run(native):
    check(native.ship == 'zod' and native.pier == Path('/state/zod'), 'fresh pinned fake only')
    check(native.dojo('.^(? %j /(scot %p our)/fake/(scot %da now))').strip() == '%.y','fake guard')
    ca = certificates(native)
    owner, identity = Site(HOME,ca), Site(IDENTITY,ca)
    for app in ('stead-home','stead-identity'):
        native.dojo(f'|rein %base [%.y %{app}]')
        wait_for(lambda:native.dojo(f'.^(? %gu /={app}=/$)').strip(), lambda value:value=='%.y', app+' live',60)
    print('Solo setup: native Home and Identity started on one fake planet',flush=True)
    config = {'protocol':'stead.team-config/1','expected_revision':'0','home':SHIP,'origin':owner.origin,
              'organization_id':uid(5),'team_id':uid(6),'custody':'local-disposable','runtime':'isolated-fake',
              'bindings':{SHIP:{'principal_id':uid(102),'binding_id':uid(202),'binding_revision':'1','active':'yes',
                                'expires_at_ms':str(int(time.time()*1000)+14*86400000),'display_name':'Solo owner'}},
              'project_creators':{uid(102):'yes'}}
    check(owner_call(native,'home','configure',config) == {},'explicit Home owner binding')
    check(owner_call(native,'identity','identity-config',{'protocol':'stead.identity-config/2',
          'expected_revision':'0','origin':identity.origin}) == {},'standalone Identity configured')
    bootstrap(native,'home')
    bootstrap(native,'identity')
    for site, page in ((owner,'/stead/'),(identity,'/stead-identity/')):
        code, html = site.request('GET',page)
        check(code==200 and b'<html' in html.lower(), 'served '+page)
    before, _ = identity.request('POST','/stead-identity/api/list',{'protocol':'stead.identity/2'})
    check(before == 401,'owner approval requires ship login')
    password = native.dojo('+code').strip().lstrip('~')
    check(re.fullmatch(r'[a-z]{6}(?:-[a-z]{6}){3}',password), 'synthetic personal ship code')
    status,_ = identity.request('POST','/~/login',{'password':password, 'redirect':'/stead-identity/'},form=True)
    check(status in (200,302,303) and any(k.startswith('urbauth-') for k in identity.cookies),'ordinary ship-owner login')

    sign_in(owner,identity)
    check(owner.cookie_ttls.get('__Host-stead-session') == 1800, 'default thirty-minute session')
    check(not projects(owner,301), 'ship ownership gives no implicit projects')
    project = uid(1)
    command = {'protocol':'stead.command/3','request_id':uid(302),'project_id':project,'resource_id':project,
               'expected_revision':'0','authority_epoch':'1','operation':'project.create',
               'payload':{'organization_id':uid(5),'owning_team_id':uid(6),'project_key':'SOLO',
                          'title':'Solo invitation trial','preset':'general'}}
    response = owner.post('/stead/api/command', command)
    check(response.get('status')=='accepted','granted owner creates project')
    check(any(r.get('role')=='maintainer' for r in projects(owner,303).values()),'maintainer grant')
    bearer = git_credentials(owner, project)
    git_refs(owner, project, ca)
    before_refs = git_refs(owner, project, ca, bearer)
    issue = owner.post('/stead/api/invitations', {'protocol':INVITATION,'action':'issue','project_id':project,
                       'role':'reader','mode':'personal','identity_ship':SHIP,'expires_at_ms':'','use_limit':'1'})
    check(issue.get('status') == 'issued','personal invitation issued')
    guest = Site(HOME,ca)
    wrong,denied = guest.request('POST','/stead/auth/invite/start',{'protocol':INVITATION,'token':issue['token'],'identity_ship':'~bus'})
    check(wrong >= 400 or json.loads(denied).get('status') != 'pending','forwarded invitation refused')
    authenticator = SoftwareAuthenticator(native,identity,ca)
    authenticator.enroll()
    second = sign_in(guest,identity,issue['token'],authenticator)
    authenticator.remove()
    check(second.get('project_id') == project,'invite delivers intended project')
    for site,n in ((owner,304),(guest,305)):
        check(any(r.get('project_id') == project and r.get('role')=='maintainer' for r in projects(site,n).values()),
              'prior and redeemed sessions preserve role')
    check(git_refs(owner, project, ca, bearer) == before_refs, 'existing Git password survives redemption')
    # Eyre sets its own host-only urbauth cookie even for an anonymous guest.
    # Only the owner session's value must stay on the Identity hostname.
    personal = identity.cookies.get('urbauth-'+SHIP)
    check(personal and all(personal not in site.cookies.values() for site in (owner, guest)),
          'authenticated ship-owner cookie confined to Identity')
    check(not any(key.startswith('__Host-stead-') for key in identity.cookies),
          'workspace credentials confined to Home')
    anonymous = Site(IDENTITY,ca)
    anonymous.request('GET','/stead-identity/')
    denied,_ = anonymous.request('POST','/stead-identity/api/list',{'protocol':'stead.identity/2'})
    check(denied==401,'ordinary Eyre guest remains unauthorized')
    def device(site, action, value=''):
        return site.post('/stead/auth/devices', {'protocol':'stead.devices/1','action':action,'value':value})
    check(device(guest,'remember','Temporary laptop')['status']=='remembered','explicit device trust')
    check(604700 <= guest.cookie_ttls.get('__Host-stead-session',0) <= 604800,'seven-day personal device')
    devices = device(owner,'list')['devices']
    target = next(key for key,row in devices.items() if row['label']=='Temporary laptop' and row['current']=='no')
    check(device(owner,'revoke',target)['status']=='revoked','remote device revocation')
    revoked,_ = guest.request('POST','/stead/auth/resume',{'protocol':'stead.auth/1'})
    check(revoked == 401 and projects(owner,306),'revoked guest device and live first session')
    configure_verifier(native, '')
    fallback = Site(HOME,ca)
    sign_in(fallback,identity,previously_trusted=True)
    check(projects(fallback,307),'ordinary sign-in after disabling companion')
    check(device(fallback,'remember','Recovery browser')['status']=='remembered','remember recovery browser')
    check(fallback.post('/stead/auth/logout',{'protocol':'stead.auth/1'}).get('status')=='logged_out','ordinary signout')
    check(all(row['label']!='Recovery browser' for row in device(owner,'list')['devices'].values()),'signout removes trust')
    report = {'status':'passed','planet':'~zod','native_apps':2,'verified_https_origins':2,
              'explicit_membership':True,'discovered_personal_address':True,'ordinary_owner_approval':True,
              'forwarded_personal_link_denied':True,'wrong_return_proof_denied':True,'project_role':'maintainer',
              'unrelated_browser_session_survived':True,'existing_stock_git_credential_survived':True,
              'native_owner_ticket_and_signed_software_authenticator':True,'credential_removed':True,'remembered_device_revoked':True,
              'ordinary_approval_after_disabling_verifier':True,'signout_removed_device_trust':True,
              'default_session_seconds':1800,'remembered_session_days':7}
    print('Solo native HTTP result',json.dumps(report,sort_keys=True),flush=True)
    return report

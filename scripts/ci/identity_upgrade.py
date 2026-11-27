"""Rehearse an Identity upgrade and cold rollback using only a disposable ship."""
import json
import re
import sys

sys.path[:0] = ['/src/scripts/ci', '/src/scripts', '/src/scripts/urbit', '/src/scripts/sdk_native']
from invitation_upgrade import CLEAN, INPUT, STATE, Home, digest, extract, require
import native_tls
import release_install as release
from solo_signin_trial import Site

AGENT = 'stead-identity'
SAVED = ('=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-identity=/$)  '
         '?>  ?=([%20 %live *] egg)  =/  saved=vase  +.old-state.egg  ')
CONFIG = '[revision=@ud home=@p home-origin=@t origin=@t]'


def stop_agent(ship):
    ship.dojo('|rein %release-test [%.n %stead-identity]')
    release.wait_agent(ship, AGENT, False)
    require(ship.dojo('.^(desk %gd /=stead-identity=/$)').strip()=='%release-test', 'wrong Identity desk')


def fingerprint(ship, version):
    extra = '' if version == 1 else ' trusted=(map @p @t) verifier=@t'
    prefix = SAVED + f'=/  row  !<([%stead-identity %{version} config=(unit {CONFIG}) counter=@ud{extra}] saved)  '
    prefix += ('?>  ?=(^ config.row)  ?>  &(=(~bus home.u.config.row) =(1 revision.u.config.row)  '
               "=('https://bus.localhost:18444' home-origin.u.config.row) =('https://home.localhost:18443' origin.u.config.row))  ")
    if version == 2:
        prefix += ("?>  &(=(1 ~(wyt by trusted.row)) =('' verifier.row) "
                   "=('https://bus.localhost:18444' (~(got by trusted.row) ~bus)))  ")
    def measure(item):
        output = ''.join(ship.dojo(prefix + f'^-  @ux  (shax (jam {item}))').split())
        require(re.fullmatch(r'0x[0-9a-f]+(?:\.[0-9a-f]+)*',output) and len(output)<=82,
                'Identity saved-state fingerprint failed for '+item)
        return f'{int(output.replace(".",""),16):064x}'
    return {'version':version,'saved':measure('q.saved'),'config_and_counter':measure('[config.row counter.row]')}


def resume(ship, ca, package, version, *, already_running=False):
    if not already_running:
        ship.dojo('|rein %release-test [%.y %stead-identity]')
    release.wait_agent(ship, AGENT, True)
    release.bootstrap_role(ship, 'identity')
    site = Site(release.TLS_HOST,ca)
    routes = json.loads((package/'source/frontend.json').read_bytes())['routes']
    served = []
    for route in routes:
        path = route['route']
        if not path.startswith('/stead-identity/'):
            continue
        status,raw = site.request('GET',path)
        require(status==200 and len(raw)==route['bytes'] and digest(raw)==route['sha256'],'Identity route mismatch')
        served.append(path)
    require('/stead-identity/' in served,'missing Identity homepage')
    protocol = f'stead.identity/{version}'
    payload = {'protocol':protocol}
    code,_ = site.request('POST','/stead-identity/api/list',payload)
    require(code==401,'ordinary visitor can see private Identity requests')
    password = ship.dojo('+code').strip().strip('~')
    require(re.fullmatch(r'[a-z]{6}(?:-[a-z]{6}){3}',password),'expected synthetic ship code')
    status,_ = site.request('POST','/~/login',{'password':password,'redirect':'/stead-identity/'},form=True)
    require(status in (200,302,303),'owner login')
    listed = site.post('/stead-identity/api/list',payload)
    require(listed.get('protocol')==protocol and listed.get('status')=='read' and listed.get('requests')=={},
            'Identity seat and volatile request reset')
    return len(served)


def run():
    pins = json.loads((INPUT/'pins.json').read_bytes())
    previous, old = extract('previous',pins['previous'],'identity')
    candidate, new = extract('candidate',pins['candidate'],'identity')
    ship = Home()
    receipt = {'profile':'synthetic-identity-upgrade/1','archives':pins,'events':{},'status':'failed'}
    def record(label,value):
        receipt['events'][label] = value
        print(label,json.dumps(value, sort_keys=True),flush=True)
    def stop(label):
        require(ship.stop()==CLEAN,'native ship did not stop cleanly')
        ship.logpath.rename(STATE/(label+'.log'))
    def restart(expected,label):
        nonlocal ship
        stop(label)
        sealed = release.stopped_home_checkpoint(ship.pier, expected)
        ship = Home(sealed)
        ship.start()
        native_tls.install(ship.binary,ship.pier/'.urb/conn.sock',certs,'zod')
        return sealed
    checkpoint = STATE/'verified-predecessor-checkpoint'
    try:
        ship.start()
        require(ship.dojo('.^(? %j /(scot %p our)/fake/(scot %da now))').strip()=='%.y','fresh fake only')
        ship.install(INPUT/'drivers')
        require(release.install_desk(ship,AGENT,package=previous/'desk')==old,'old archive materialization')
        release.wait_agent(ship,AGENT,True)
        config = release.role_configuration('identity',0)
        require(release.owner_call(ship,'identity','identity-config',config)=={},'v1 configuration')
        certs = native_tls.create(STATE/'certs')
        ca = certs/'ca.pem'
        native_tls.install(ship.binary,ship.pier/'.urb/conn.sock',certs,'zod')
        native_tls.verify(ship.process,certs,'zod',ship.check)
        record('predecessor-served-assets',resume(ship,ca,previous,1,already_running=True))
        stop_agent(ship)
        before = fingerprint(ship,1)
        record('original-configured-v1',before)
        stop('before-upgrade')
        sealed = release.stopped_home_checkpoint(ship.pier,old)
        require(release.checkpoint_tree(ship.pier,checkpoint,installed=True)==sealed
                and release.checkpoint_tree(checkpoint,installed=True)==sealed,'independent stopped checkpoint')
        record('stopped-v1-copy',sealed['sha256'] if 'sha256' in sealed else sealed)
        ship=Home(sealed)
        ship.start()
        native_tls.install(ship.binary,ship.pier/'.urb/conn.sock',certs,'zod')
        require(fingerprint(ship,1)==before,'cold predecessor changed')
        release.replace_clay_files(ship,old,new,package=candidate/'desk',agent=AGENT)
        record('upgraded-served-assets',resume(ship,ca,candidate,2))
        stop_agent(ship)
        migrated = fingerprint(ship,2)
        require(migrated['config_and_counter']==before['config_and_counter'],'existing configuration or counter changed')
        record('upgraded-v2-with-original-home',migrated)
        restart(new,'before-candidate-cold-boot')
        require(fingerprint(ship,2)==migrated,'v2 saved state changed after cold boot')
        record('cold-v2-served-assets',resume(ship,ca,candidate,2))
        stop_agent(ship)
        stop('retired-upgrade')
        ship.pier.rename(STATE/'retired-candidate')
        require(release.checkpoint_tree(checkpoint,ship.pier,installed=True)==sealed and
                release.stopped_home_checkpoint(ship.pier,old)==sealed,'restored checkpoint bytes differ')
        ship=Home(sealed)
        ship.start()
        native_tls.install(ship.binary,ship.pier/'.urb/conn.sock',certs,'zod')
        require(fingerprint(ship,1)==before,'rollback changed predecessor state')
        record('restored-original-v1-served-assets',resume(ship,ca,previous,1))
        receipt['status']='passed'
    finally:
        receipt['clean_shutdown'] = ship.stop()==CLEAN
        (STATE/'identity-upgrade-result.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        require(receipt['clean_shutdown'],'final native cleanup incomplete')


if __name__=='__main__':
    run()

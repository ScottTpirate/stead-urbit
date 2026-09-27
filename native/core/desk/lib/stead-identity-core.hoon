::  Individual owner approval metadata. No business bodies or browser bearers.
/+  stead-codec, stead-session, stead-http, stead-browser
=,  stead-codec
|%
+$  configuration  [revision=@ud home=@p home-origin=@t origin=@t]
+$  request  [raw=@t expires=@ud nonce=@t status=@t]
+$  state  [config=(unit configuration) requests=(map @t request) counter=@ud]
++  valid-configuration
  |=  [value=configuration our=@p]
  ^-  ?
  ?.  &((gth revision.value 0) (lte revision.value 18.446.744.073.709.551.615) !=(home.value our) (lte (met 0 home.value) 128))  |
  ?.  &((origin-valid:stead-session home-origin.value) (origin-valid:stead-session origin.value))  |
  =/  home-host  (split:stead-http (cut 3 [8 (sub (met 3 home-origin.value) 8)] home-origin.value) 58)
  =/  host  (split:stead-http (cut 3 [8 (sub (met 3 origin.value) 8)] origin.value) 58)
  &(?=(^ home-host) ?=(^ host) !=(i.home-host i.host))
++  configure
  |=  [db=state raw=@t our=@p]
  ^-  state
  =/  input  (small:stead-browser raw ~['protocol' 'expected_revision' 'home' 'home_origin' 'origin'] 'stead.identity-config/1')
  =/  expected  (uint (field input 'expected_revision'))
  ?>  &(=(expected ?~(config.db 0 revision.u.config.db)) (lth expected 18.446.744.073.709.551.615))
  =/  home  (need (slaw %p (field input 'home')))
  =/  home-origin  (field input 'home_origin')
  =/  origin  (field input 'origin')
  ?>  =((scot %p home) (field input 'home'))
  =/  config=configuration  [+(expected) home home-origin origin]
  ::  Cookie isolation requires separate hostnames, not merely separate ports.
  ?>  (valid-configuration config our)
  [[~ config] ~ counter.db]
++  prune
  |=  [db=state now=@ud]
  ^-  state
  db(requests (malt (skim ~(tap by requests.db) |=([id=@t row=request] (gth expires.row now)))))
++  receive
  |=  [db=state sender=@p our=@p raw=@t now=@ud entropy=@]
  ^-  state
  =/  config  (need config.db)
  ?>  =(sender home.config)
  =/  value  (small:stead-browser raw ~['protocol' 'purpose' 'challenge_id' 'home' 'origin' 'identity_ship' 'principal_id' 'binding_id' 'binding_revision' 'expires_at_ms'] 'stead.auth/1')
  ?>  &(=('member-session' (field value 'purpose')) =((scot %p our) (field value 'identity_ship')))
  ?>  &(=(home-origin.config (field value 'origin')) =((scot %p sender) (field value 'home')))
  ?>  &((uuid (field value 'principal_id')) (uuid (field value 'binding_id')) (gth (uint (field value 'binding_revision')) 0))
  =/  id  (field value 'challenge_id')
  =/  expires  (uint (field value 'expires_at_ms'))
  ?>  &((token-valid:stead-session id) (gth expires now) (lte expires (add now 120.000)))
  =.  db  (prune db now)
  =/  existing  (~(get by requests.db) id)
  ?^  existing
    ?>  =(raw raw.u.existing)
    db
  ?>  &((lth (lent ~(tap by requests.db)) 4) (lth counter.db 18.446.744.073.709.551.615))
  =/  counter  +(counter.db)
  =/  nonce  (token:stead-session entropy counter 'stead.identity-approval-csrf/1')
  db(counter counter, requests (~(put by requests.db) id [raw expires nonce 'pending']))
++  list-requests
  |=  [db=state now=@ud]
  ^-  @t
  =/  db  (prune db now)
  =/  rows
    %-  malt
    %+  turn  ~(tap by requests.db)
    |=  [id=@t row=request]
    =/  value  (need (parse raw.row))
    ?>  ?=([%o *] value)
    :-  id
    %-  object
    :~  ['comparison_code' (cut 3 [0 12] id)]
        ['origin' (field p.value 'origin')]
        ['identity_ship' (field p.value 'identity_ship')]
        ['home' (field p.value 'home')]
        ['principal_id' (field p.value 'principal_id')]
        ['binding_id' (field p.value 'binding_id')]
        ['binding_revision' (field p.value 'binding_revision')]
        ['expires_at_ms' (decimal expires.row)]
        ['status' status.row]
        ['csrf' ?:(=('pending' status.row) nonce.row '')]
    ==
  =/  base  (object ~[['protocol' 'stead.identity/1'] ['status' 'read']])
  ?>  ?=([%o *] base)
  (canonical [%o (~(put by p.base) 'requests' [%o rows])])
++  approve
  |=  [db=state raw=@t now=@ud]
  ^-  [next=state id=@t outgoing=@t]
  =/  input  (small:stead-browser raw ~['protocol' 'challenge_id' 'csrf' 'comparison_code' 'origin'] 'stead.identity/1')
  =/  config  (need config.db)
  =/  id  (field input 'challenge_id')
  ?>  (token-valid:stead-session id)
  =.  db  (prune db now)
  =/  row  (~(got by requests.db) id)
  ?>  &(=('pending' status.row) (token-valid:stead-session nonce.row) =(nonce.row (field input 'csrf')))
  ?>  &(=((cut 3 [0 12] id) (field input 'comparison_code')) =(home-origin.config (field input 'origin')))
  [db(requests (~(put by requests.db) id row(status 'sent', nonce ''))) id raw.row]
++  acknowledge
  |=  [db=state id=@t accepted=? now=@ud]
  ^-  state
  =.  db  (prune db now)
  =/  row  (~(get by requests.db) id)
  ?~  row  db
  ?.  =('sent' status.u.row)  db
  db(requests (~(put by requests.db) id u.row(status ?:(accepted 'approved' 'failed'))))
--

::  Identity holds native sign-in metadata. Home retains project authority.
/+  stead-codec, stead-session, stead-http, stead-browser
=,  stead-codec
|%
+$  configuration  [revision=@ud home=@p home-origin=@t origin=@t]
+$  request  [raw=@t expires=@ud nonce=@t status=@t home=@p origin=@t purpose=@t]
+$  ticket  [action=@t expires=@ud]
+$  homes  (map @p @t)
+$  state
  $:  config=(unit configuration)  requests=(map @t request)  counter=@ud
      trusted=homes  verifier=@t  tickets=(map @t ticket)
  ==
++  isolated
  |=  [home-origin=@t personal=@t]
  ^-  ?
  ?.  &((origin-valid:stead-session home-origin) (origin-valid:stead-session personal))  |
  =/  left  (split:stead-http (cut 3 [8 (sub (met 3 home-origin) 8)] home-origin) 58)
  =/  right  (split:stead-http (cut 3 [8 (sub (met 3 personal) 8)] personal) 58)
  &(?=(^ left) ?=(^ right) !=(i.left i.right))
++  valid-configuration
  |=  [value=configuration our=@p]
  ^-  ?
  ?.  &((gth revision.value 0) (lte revision.value 18.446.744.073.709.551.615) (lte (met 0 home.value) 128))  |
  ?:  =('' home-origin.value)  &(=(home.value our) (origin-valid:stead-session origin.value))
  (isolated home-origin.value origin.value)
++  seed
  |=  config=(unit configuration)
  ^-  homes
  ?~  config  ~
  ?:  =('' home-origin.u.config)  ~
  (~(put by *homes) home.u.config home-origin.u.config)
++  permitted-pair
  |=  [trusted=homes home=@p origin=@t]
  ^-  ?
  ::  An enrolled ship cannot replace its URL and a different ship cannot
  ::  claim a previously enrolled URL by putting it in its native message.
  =/  known  (~(get by trusted) home)
  ?^  known  =(origin u.known)
  !(lien ~(tap by trusted) |=([ship=@p url=@t] =(origin url)))
++  configure
  |=  [db=state raw=@t our=@p]
  ^-  state
  ?>  (lte (met 3 raw) 2.048)
  =/  obj  (need (parse raw))
  ?>  ?=([%o *] obj)
  =/  protocol  (field p.obj 'protocol')
  =/  expected  (uint (field p.obj 'expected_revision'))
  ?>  &(=(expected ?~(config.db 0 revision.u.config.db)) (lth expected 18.446.744.073.709.551.615))
  =/  origin  (field p.obj 'origin')
  =/  config=configuration
    ?:  =('stead.identity-config/2' protocol)
      ?>  (keys p.obj ~['protocol' 'expected_revision' 'origin'])
      [+(expected) our '' origin]
    ?>  &((keys p.obj ~['protocol' 'expected_revision' 'home' 'home_origin' 'origin']) =('stead.identity-config/1' protocol))
    =/  home  (need (slaw %p (field p.obj 'home')))
    ?>  =((scot %p home) (field p.obj 'home'))
    [+(expected) home (field p.obj 'home_origin') origin]
  ?>  (valid-configuration config our)
  [[~ config] ~ counter.db (seed [~ config]) '' ~]
++  prune
  |=  [db=state now=@ud]
  ^-  state
  =.  tickets.db  (malt (skim ~(tap by tickets.db) |=([key=@t row=ticket] (gth expires.row now))))
  db(requests (malt (skim ~(tap by requests.db) |=([id=@t row=request] (gth expires.row now)))))
++  receive
  |=  [db=state sender=@p our=@p raw=@t now=@ud entropy=@]
  ^-  state
  =/  config  (need config.db)
  =/  value  (small:stead-browser raw ~['protocol' 'purpose' 'challenge_id' 'home' 'origin' 'identity_ship' 'principal_id' 'binding_id' 'binding_revision' 'expires_at_ms'] 'stead.auth/1')
  =/  purpose  (field value 'purpose')
  ?>  =((scot %p our) (field value 'identity_ship'))
  ?>  ?|(=('member-session' purpose) =('project-invitation' purpose))
  =/  origin  (field value 'origin')
  ?>  &((isolated origin origin.config) =((scot %p sender) (field value 'home')) (lte (met 0 sender) 128))
  ?>  (permitted-pair trusted.db sender origin)
  ?>  &((uuid (field value 'principal_id')) (uuid (field value 'binding_id')) (gth (uint (field value 'binding_revision')) 0))
  =/  id  (field value 'challenge_id')
  =/  expires  (uint (field value 'expires_at_ms'))
  ?>  &((token-valid:stead-session id) (gth expires now) (lte expires (add now 120.000)))
  =.  db  (prune db now)
  =/  existing  (~(get by requests.db) id)
  ?^  existing
    ?>  =(raw raw.u.existing)
    db
  =/  known  (~(has by trusted.db) sender)
  =/  rows  ~(tap by requests.db)
  ?>  (lth (lent (skim rows |=([key=@t row=request] =(sender home.row)))) 4)
  ::  Reserve a separate pool for requests from previously consented Homes.
  ?>  (lth (lent (skim rows |=([key=@t row=request] =(known (~(has by trusted.db) home.row))))) 16)
  ?>  (lth counter.db 18.446.744.073.709.551.615)
  =/  counter  +(counter.db)
  =/  nonce  (token:stead-session entropy counter 'stead.identity-approval-csrf/1')
  db(counter counter, requests (~(put by requests.db) id [raw expires nonce 'pending' sender origin purpose]))
++  address-message
  |=  [db=state id=@t our=@p]
  ^-  @t
  =/  row  (~(got by requests.db) id)
  =/  config  (need config.db)
  %-  canonical
  (object ~[['protocol' 'stead.identity-address/1'] ['challenge_id' id] ['identity_ship' (scot %p our)] ['home' (scot %p home.row)] ['origin' origin.row] ['identity_origin' origin.config]])
++  list-requests
  |=  [db=state now=@ud]
  (render-requests db now |)
++  render-requests
  |=  [db=state now=@ud detailed=?]
  ^-  @t
  =/  db  (prune db now)
  =/  rows
    %-  malt
    %+  turn  ~(tap by requests.db)
    |=  [id=@t row=request]
    =/  value  (need (parse raw.row))
    ?>  ?=([%o *] value)
    =/  info
      %-  object
    :~  ['comparison_code' (cut 3 [0 12] id)]
        ['origin' origin.row]
        ['identity_ship' (field p.value 'identity_ship')]
        ['home' (scot %p home.row)]
        ['principal_id' (field p.value 'principal_id')]
        ['binding_id' (field p.value 'binding_id')]
        ['binding_revision' (field p.value 'binding_revision')]
        ['expires_at_ms' (decimal expires.row)]
        ['status' status.row]
        ['csrf' ?:(=('pending' status.row) nonce.row '')]
    ==
    :-  id
    ?.  detailed  info
    ?>  ?=([%o *] info)
    =/  trusted  ?:(=([~ origin.row] (~(get by trusted.db) home.row)) 'yes' 'no')
    [%o (~(put by (~(put by p.info) 'trusted' [%s trusted])) 'purpose' [%s purpose.row])]
  =/  base
    ?.  detailed  (object ~[['protocol' 'stead.identity/1'] ['status' 'read']])
    (object ~[['protocol' 'stead.identity/2'] ['status' 'read'] ['passkeys' ?:(=(verifier.db '') 'no' 'yes')]])
  ?>  ?=([%o *] base)
  (canonical [%o (~(put by p.base) 'requests' [%o rows])])
+$  approval  [next=state id=@t outgoing=@t home=@p]
++  send-approval
  |=  [db=state id=@t now=@ud]
  ^-  approval
  =.  db  (prune db now)
  =/  row  (~(got by requests.db) id)
  ?>  &(=('pending' status.row) =([~ origin.row] (~(get by trusted.db) home.row)))
  [db(requests (~(put by requests.db) id row(status 'sent', nonce ''))) id raw.row home.row]
++  approve
  |=  [db=state raw=@t now=@ud]
  ^-  approval
  ?>  (lte (met 3 raw) 2.048)
  =/  obj  (need (parse raw))
  ?>  ?=([%o *] obj)
  =/  input  p.obj
  ?>  (keys input ~['protocol' 'challenge_id' 'csrf' 'comparison_code' 'origin'])
  =/  protocol  (field input 'protocol')
  ?>  ?|(=('stead.identity/1' protocol) =('stead.identity-consent/1' protocol))
  =/  id  (field input 'challenge_id')
  ?>  (token-valid:stead-session id)
  =.  db  (prune db now)
  =/  row  (~(got by requests.db) id)
  ?>  &(=('pending' status.row) (token-valid:stead-session nonce.row) =(nonce.row (field input 'csrf')))
  ?>  &(=((cut 3 [0 12] id) (field input 'comparison_code')) =(origin.row (field input 'origin')))
  ?>  (permitted-pair trusted.db home.row origin.row)
  ?.  (~(has by trusted.db) home.row)
    ?>  &(=('stead.identity-consent/1' protocol) (lth (lent ~(tap by trusted.db)) 32))
    (send-approval db(trusted (~(put by trusted.db) home.row origin.row)) id now)
  (send-approval db id now)
++  acknowledge
  |=  [db=state id=@t accepted=? now=@ud]
  ^-  state
  =.  db  (prune db now)
  =/  row  (~(get by requests.db) id)
  ?~  row  db
  ?.  =('sent' status.u.row)  db
  db(requests (~(put by requests.db) id u.row(status ?:(accepted 'approved' 'failed'))))
++  configure-verifier
  |=  [db=state raw=@t]
  ^-  state
  =/  input  (small:stead-browser raw ~['protocol' 'secret'] 'stead.verifier-config/1')
  =/  secret  (field input 'secret')
  ?>  ?|(=('' secret) (token-valid:stead-session secret))
  db(verifier ?:(=('' secret) '' (digest:stead-session 'stead.verifier/1' secret)), tickets ~)
++  owner-ticket
  |=  [db=state action=@t now=@ud entropy=@]
  ^-  [next=state value=@t]
  ?>  &(!=('' verifier.db) (lth counter.db 18.446.744.073.709.551.615))
  ?>  ?|(=('register' action) =('revoke' action) =('list' action))
  =.  db  (prune db now)
  ?>  (lth (lent ~(tap by tickets.db)) 16)
  =/  count  +(counter.db)
  =/  value  (token:stead-session entropy count 'stead.passkey-ticket/1')
  =/  key  (digest:stead-session 'stead.passkey-ticket/1' value)
  [db(counter count, tickets (~(put by tickets.db) key [action (add now 60.000)])) value]
++  consume-ticket
  |=  [db=state action=@t value=@t now=@ud]
  ^-  state
  ?>  (token-valid:stead-session value)
  =/  key  (digest:stead-session 'stead.passkey-ticket/1' value)
  =/  row  (~(got by tickets.db) key)
  ?>  &(=(action action.row) (gth expires.row now))
  db(tickets (~(del by tickets.db) key))
--

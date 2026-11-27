::  Home's durable project offers. Only the hash of the link secret is retained.
::  Browser proof travels separately. A pending request carries its proven binding.
/+  stead-codec, stead-core, stead-team, stead-team-config, stead-team-codec, stead-session, stead-http, stead-browser, stead-projection, stead-updates, stead-project-retirement
=,  stead-codec
|%
+$  guest  [identity=actor:stead-session accepted=?]
+$  offer
  $:  project=@t  epoch=@ud  issuer=actor:stead-session  mode=@t  target=@t
      role=@t  expires=@ud  limit=@ud  revoked=?  guests=(map @p guest)  blocked=(set @p)
  ==
+$  book  (map @t offer)
+$  flight  [offer-id=@t row=challenge:stead-session]
+$  flights  (map @t flight)
+$  changes  [offers=book pending=flights db=state:stead-team auth=state:stead-session]
+$  result  [next=changes bytes=@t cookies=(list @t) outgoing=(unit [ship=@p bytes=@t])]
++  domain  'stead.invitation/1'
++  answer
  |=  [status=@t fields=(list [@t @t])]
  (canonical (object [['protocol' domain] ['status' status] fields]))
++  route
  |=  path=@t
  (~(has in (silt ~['/stead/api/invitations' '/stead/auth/invite/start' '/stead/auth/invite/status' '/stead/auth/invite/consume'])) path)
++  identifier
  |=  [purpose=@t seed=*]
  ^-  @t
  =/  h  (hash purpose (bytes-hex (jam seed)))
  (rap 3 ~[(cut 3 [0 8] h) '-' (cut 3 [8 4] h) '-7' (cut 3 [13 3] h) '-8' (cut 3 [17 3] h) '-' (cut 3 [20 12] h)])
++  ship-name
  |=  name=@t
  ^-  @p
  =/  who  (need (slaw %p name))
  ?>  &((lte (met 0 who) 32) =((scot %p who) name))
  who
++  eligible
  |=  [who=@p runtime=@t]
  ^-  ?
  ?&  (lte (met 0 who) 32)
      ?|(=('isolated-fake' runtime) &(=('live-synthetic' runtime) (gth (met 0 who) 16)))
  ==
++  role-valid
  |=  role=@t
  (~(has in (silt ~['reader' 'contributor' 'maintainer'])) role)
++  uses
  |=  row=offer
  (lent (skim ~(tap by guests.row) |=([ship=@p guest=guest] accepted.guest)))
++  valid
  |=  [db=state:stead-team offers=book]
  ^-  ?
  =/  config  (need current.registry.db)
  ?>  (lte ~(wyt by offers) 128)
  %+  levy  ~(tap by offers)
  |=  [id=@t row=offer]
  ?>  &((token-valid:stead-session id) (uuid project.row) (gth epoch.row 0) (live:stead-session issuer.row 0))
  ?>  &((~(has by projects.data.db) project.row) (role-valid role.row) (gth expires.row 0) (lte expires.row 18.446.744.073.709.551.615))
  ?>  &((gth limit.row 0) (lte limit.row 32) (lte ~(wyt by guests.row) 32) (lte (uses row) limit.row) (lte ~(wyt in blocked.row) 128))
  ?>  ?:  =('personal' mode.row)
        &(=(limit.row 1) (eligible (ship-name target.row) runtime.config))
      &(?|(=('reader' mode.row) =('request' mode.row)) =('' target.row) =('reader' role.row))
  %+  levy  ~(tap by guests.row)
  |=  [ship=@p guest=guest]
  ?>  &((eligible ship runtime.config) =(ship ship.identity.guest) (live:stead-session identity.guest 0) ?|(=('' target.row) =(target.row (scot %p ship))))
  ?.  accepted.guest  =('request' mode.row)
  =/  grant-id  (identifier 'stead.invitation-grant/1' [id ship])
  =/  g  (~(get by grants.data.db) (scope-key:stead-core project.row grant-id))
  ?~(g | &(=(project.row project.u.g) =(principal.identity.guest principal.u.g)))
++  available
  |=  [row=offer who=@p now=@ud]
  ^-  ?
  ?&  !revoked.row  !(~(has in blocked.row) who)  (gth expires.row now)
      ?|(=('' target.row) =(target.row (scot %p who)))
      ?|  (lth (uses row) limit.row)
          =/  guest  (~(get by guests.row) who)
          ?~(guest | accepted.u.guest)
      ==
  ==
++  after-config
  ::  Close earlier offers for departed or rebound ships, preserving other recipients.
  |=  [offers=book prior=registry:stead-team-config next=registry:stead-team-config]
  ^-  book
  ?~  current.prior  offers
  =/  config  (need current.next)
  =/  removed=(set @p)
    %-  silt
    %+  turn
      %+  skip  ~(tap by members.u.current.prior)
      |=  [ship=@p before=member:stead-team-config]
      =/  after  (~(get by members.config) ship)
      ?~  after  |
      &((same-actor:stead-session identity.before identity.u.after) active.identity.u.after)
    |=([ship=@p before=member:stead-team-config] ship)
  %-  ~(run by offers)
  |=  row=offer
  =/  blocked  (~(uni in blocked.row) removed)
  ?:  (gth ~(wyt in blocked) 128)  row(revoked &)
  row(blocked blocked)
++  after-renewal
  ::  Retain offers and verified access requests for an owner-extended
  ::  lease on this exact binding. In-flight browser proofs start afresh.
  |=  [offers=book before=actor:stead-session after=actor:stead-session]
  ^-  book
  %-  ~(run by offers)
  |=  row=offer
  =.  issuer.row  ?:(=(issuer.row before) after issuer.row)
  =/  guest  (~(get by guests.row) ship.before)
  ?~  guest  row
  ?.  =(identity.u.guest before)  row
  row(guests (~(put by guests.row) ship.before u.guest(identity after)))
++  authority
  |=  [db=state:stead-team row=offer retired=ledger:stead-project-retirement now=@ud]
  ^-  authentication:stead-team
  ?>  !(~(has by retired) project.row)
  =/  actor  (need (native-context:stead-team db ship.issuer.row now))
  ?>  (same-actor:stead-session issuer.row identity.actor)
  ?>  =(epoch.row epoch:(~(got by projects.data.db) project.row))
  ?>  =(3 (role:stead-team db actor project.row now))
  actor
++  resolve
  |=  [db=state:stead-team who=@p now=@ud]
  ^-  actor:stead-session
  =/  config  (need current.registry.db)
  =/  existing  (~(get by members.config) who)
  ?^  existing
    ?>  (live:stead-session identity.u.existing now)
    identity.u.existing
  =/  scope  [home.config organization.config team.config who]
  =/  principal  (identifier 'stead.invitation-principal/1' scope)
  =/  binding  (identifier 'stead.invitation-binding/1' scope)
  ::  Missing identities with historical ownership must be reinstated explicitly.
  ?>  &(!(~(has by revisions.registry.db) principal) !(~(has by owners.registry.db) binding))
  [who principal binding 1 & 18.446.744.073.709.551.615]
++  enroll
  |=  [db=state:stead-team person=actor:stead-session now=@ud]
  ^-  state:stead-team
  ?>  =(person (resolve db ship.person now))
  =/  reg  registry.db
  =/  config  (need current.reg)
  ?:  (~(has by members.config) ship.person)  db
  ?>  &((lth ~(wyt by members.config) 32) (lth ~(wyt by revisions.reg) 128) (lth ~(wyt by owners.reg) 256) (lth revision.config 18.446.744.073.709.551.615))
  =.  members.config  (~(put by members.config) ship.person [person (scot %p ship.person)])
  =.  reg  reg(current (some config(revision +(revision.config))), revisions (~(put by revisions.reg) principal.person revision.person), owners (~(put by owners.reg) binding.person principal.person))
  db(registry reg)
++  admit
  |=  [db=state:stead-team id=@t row=offer who=actor:stead-session role=@t retired=ledger:stead-project-retirement now=@ud]
  ^-  [next=state:stead-team changed=offer]
  =/  issuer  (authority db row retired now)
  ?>  &((available row ship.who now) (role-valid role))
  =/  past  (~(get by guests.row) ship.who)
  ?^  past
    ?>  =(who identity.u.past)
    ?:  accepted.u.past
      =/  id-grant  (identifier 'stead.invitation-grant/1' [id ship.who])
      =/  g  (~(got by grants.data.db) (scope-key:stead-core project.row id-grant))
      ?>  &(!revoked.g (gth expires.g now) =(principal.who principal.g))
      =/  existing  (need (native-context:stead-team db ship.who now))
      ?>  &((same-actor:stead-session who identity.existing) (gth (role:stead-team db existing project.row now) 0))
      [db row]
    (grant db id row who role issuer now)
  (grant db id row who role issuer now)
++  grant
  |=  [db=state:stead-team id=@t row=offer who=actor:stead-session role=@t issuer=authentication:stead-team now=@ud]
  ^-  [next=state:stead-team changed=offer]
  =.  db  (enroll db who now)
  =/  grant-id  (identifier 'stead.invitation-grant/1' [id ship.who])
  =/  project  (~(got by projects.data.db) project.row)
  =/  mine
    %+  skim  ~(tap by grants.data.db)
    |=  [key=@t g=grant-state:stead-core]
    &(!revoked.g =(project.row project.g) =(principal.issuer.row principal.g) =('maintainer' role.g))
  =/  deadline  (min expires.who (min expires.identity.issuer (roll mine |=([pair=[@t grant-state:stead-core] limit=@ud] (max limit expires.+.pair)))))
  =/  data  (object ~[['grant_id' grant-id] ['principal_id' principal.who] ['role' role] ['expires_at_ms' (decimal deadline)]])
  =/  cmd
    (object ~[['protocol' 'stead.command/3'] ['request_id' grant-id] ['project_id' project.row] ['resource_id' project.row] ['operation' 'policy.grant'] ['authority_epoch' (decimal epoch.project)] ['expected_revision' (decimal policy.project)]])
  ?>  ?=([%o *] cmd)
  =/  decoded  (decode:stead-team-codec (canonical [%o (~(put by p.cmd) 'payload' data)]))
  =/  delegated  issuer(method 'project-invitation/1', strength 'delegated-invitation', audit id, expires (min expires.issuer expires.row))
  =/  changed  (apply-command:stead-team db delegated decoded now)
  ?>  !=(db next.changed)
  [next.changed row(guests (~(put by guests.row) ship.who [who &]))]
++  proof-message
  |=  [id=@t ch=challenge:stead-session]
  ^-  @t
  =/  value  (need (parse (approval-message:stead-browser id ch)))
  ?>  ?=([%o *] value)
  (canonical [%o (~(put by p.value) 'purpose' [%s 'project-invitation'])])
++  approve-proof
  |=  [pending=flights sender=@p raw=@t now=@ud]
  ^-  flights
  =/  obj  (need (parse raw))
  ?>  ?=([%o *] obj)
  =/  id  (field p.obj 'challenge_id')
  =/  found  (~(got by pending) id)
  =/  return-hash  (field p.obj 'return_digest')
  ?>  (token-valid:stead-session return-hash)
  =/  original  (canonical [%o (~(del by p.obj) 'return_digest')])
  ?>  &(!approved.row.found (gth expires.row.found now) =(sender ship.identity.row.found) =(original (proof-message id row.found)))
  (~(put by pending) id found(row row.found(approved &, return-digest (some return-hash))))
++  prune-book
  ::  Link expiry ends admission. Its still-active project grants keep their
  ::  administrative handles so a maintainer can revoke one after the link closes.
  |=  [offers=book db=state:stead-team now=@ud]
  ^-  book
  =/  rows  ~(tap by offers)
  =/  kept=book  ~
  |-
  ?~  rows  kept
  =/  [id=@t row=offer]  i.rows
  ?:  &(!revoked.row (gth expires.row now))
    $(rows t.rows, kept (~(put by kept) id row))
  =/  active=(map @p guest)
    %-  malt
    %+  skim  ~(tap by guests.row)
    |=  [ship=@p g=guest]
    ?.  accepted.g  |
    =/  gid  (identifier 'stead.invitation-grant/1' [id ship])
    =/  grant  (~(get by grants.data.db) (scope-key:stead-core project.row gid))
    ?~(grant | &(!revoked.u.grant (gth expires.u.grant now)))
  ?~  active  $(rows t.rows)
  $(rows t.rows, kept (~(put by kept) id row(guests active, blocked ~)))
++  list-rows
  |=  [offers=book db=state:stead-team project=@t now=@ud]
  ^-  @t
  =/  output=(map @t json)  ~
  =/  rows  ~(tap by offers)
  |-
  ?~  rows
    =/  base  (object ~[['protocol' domain] ['status' 'read']])
    ?>  ?=([%o *] base)
    (canonical [%o (~(put by p.base) 'invitations' [%o output])])
  =/  [id=@t row=offer]  i.rows
  ?.  =(project project.row)  $(rows t.rows)
  =/  detail  (object ~[['mode' mode.row] ['role' role.row] ['identity_ship' target.row] ['expires_at_ms' (decimal expires.row)] ['use_limit' (decimal limit.row)] ['uses' (decimal (uses row))] ['status' ?:(revoked.row 'revoked' ?:((lte expires.row now) 'expired' 'open'))]])
  ?>  ?=([%o *] detail)
  =/  requests
    %-  object
    %+  turn  ~(tap by guests.row)
    |=  [ship=@p g=guest]
    :-  (scot %p ship)
    ?.  accepted.g  'pending'
    =/  grant-id  (identifier 'stead.invitation-grant/1' [id ship])
    =/  record  (~(got by grants.data.db) (scope-key:stead-core project grant-id))
    ?:(revoked.record 'removed' 'accepted')
  $(rows t.rows, output (~(put by output) id [%o (~(put by p.detail) 'requests' requests)]))
++  manage
  |=  [s=changes input=object-map req=incoming:stead-http retired=ledger:stead-project-retirement now=@ud entropy=@]
  ^-  result
  =/  config  (need current.registry.db.s)
  =/  existing  (~(got by sessions.auth.s) (digest:stead-session 'stead.session/1' session.req))
  =/  actor  (need (browser-context:stead-team db.s existing now))
  ?>  ?=(^ (authorize:stead-session auth.s session.req csrf.req identity.actor home.config origin.config now))
  =/  project  (field input 'project_id')
  ?>  &(!(~(has by retired) project) =(3 (role:stead-team db.s actor project now)))
  =/  action  (field input 'action')
  ?:  =('list' action)
    ?>  (keys input ~['protocol' 'action' 'project_id'])
    [s (list-rows offers.s db.s project now) ~ ~]
  ?:  =('issue' action)
    ?>  (keys input ~['protocol' 'action' 'project_id' 'mode' 'identity_ship' 'role' 'expires_at_ms' 'use_limit'])
    =/  mode  (field input 'mode')
    =/  name  (field input 'identity_ship')
    =/  limit  (uint (field input 'use_limit'))
    =/  role  (field input 'role')
    =/  expiry  (field input 'expires_at_ms')
    =/  expires  ?:(=('' expiry) (add now 604.800.000) (uint expiry))
    ?>  &((gth expires now) (lte expires (add now 2.592.000.000)) (gth limit 0) (lte limit 32) (role-valid role))
    ?>  ?:  =('personal' mode)
          &(=(limit 1) (eligible (ship-name name) runtime.config))
        &(?|(=('reader' mode) =('request' mode)) =('' name) =('reader' role))
    =/  live  (prune-book offers.s db.s now)
    ?>  (lth ~(wyt by live) 128)
    =/  token  (token:stead-session entropy now 'stead.invitation-secret/1')
    =/  id  (digest:stead-session 'stead.invitation-lookup/1' token)
    ?>  !(~(has by live) id)
    =/  row=offer  [project epoch:(~(got by projects.data.db.s) project) identity.actor mode name role expires limit | ~ ~]
    [s(offers (~(put by live) id row)) (answer 'issued' ~[['token' token] ['invitation_id' id]]) ~ ~]
  =/  id  (field input 'invitation_id')
  =/  row  (~(got by offers.s) id)
  ?>  =(project project.row)
  ?:  =('revoke' action)
    ?>  (keys input ~['protocol' 'action' 'project_id' 'invitation_id'])
    [s(offers (~(put by offers.s) id row(revoked &))) (answer 'revoked' ~) ~ ~]
  ?:  =('remove' action)
    ?>  (keys input ~['protocol' 'action' 'project_id' 'invitation_id' 'identity_ship'])
    =/  who  (ship-name (field input 'identity_ship'))
    =/  guest  (~(got by guests.row) who)
    ?>  accepted.guest
    =/  grant-id  (identifier 'stead.invitation-grant/1' [id who])
    =/  g  (~(got by grants.data.db.s) (scope-key:stead-core project grant-id))
    ?>  =(principal.identity.guest principal.g)
    ?:  revoked.g  [s (answer 'removed' ~) ~ ~]
    =/  pro  (~(got by projects.data.db.s) project)
    =/  key  (identifier 'stead.invitation-remove/1' [id who])
    =/  cmd  (object ~[['protocol' 'stead.command/3'] ['request_id' key] ['project_id' project] ['resource_id' project] ['operation' 'policy.revoke'] ['authority_epoch' (decimal epoch.pro)] ['expected_revision' (decimal policy.pro)]])
    ?>  ?=([%o *] cmd)
    =/  payload  (object ~[['grant_id' grant-id]])
    =/  decoded  (decode:stead-team-codec (canonical [%o (~(put by p.cmd) 'payload' payload)]))
    =/  applied  (apply-command:stead-team db.s actor decoded now)
    ?>  !=(next.applied db.s)
    [s(db next.applied) (answer 'removed' ~) ~ ~]
  ?>  &(=('approve' action) =('request' mode.row) (keys input ~['protocol' 'action' 'project_id' 'invitation_id' 'identity_ship' 'role']))
  =/  who  (ship-name (field input 'identity_ship'))
  =/  guest  (~(got by guests.row) who)
  =/  out  (admit db.s id row identity.guest (field input 'role') retired now)
  [s(db next.out, offers (~(put by offers.s) id changed.out)) (answer 'approved' ~) ~ ~]
++  call
  |=  [s=changes req=incoming:stead-http retired=ledger:stead-project-retirement now=@ud entropy=@]
  ^-  result
  ?>  (lte (met 3 body.req) 2.048)
  =/  value  (need (parse body.req))
  ?>  ?=([%o *] value)
  =/  input  p.value
  ?>  =(domain (field input 'protocol'))
  ?:  =('/stead/api/invitations' route.req)  (manage s input req retired now entropy)
  =/  config  (need current.registry.db.s)
  =.  pending.s  (malt (skim ~(tap by pending.s) |=([id=@t f=flight] (gth expires.row.f now))))
  ?:  =('/stead/auth/invite/start' route.req)
    ?>  (keys input ~['protocol' 'token' 'identity_ship'])
    =/  token  (field input 'token')
    ?>  (token-valid:stead-session token)
    =/  id  (digest:stead-session 'stead.invitation-lookup/1' token)
    =/  offer  (~(got by offers.s) id)
    =/  who  (ship-name (field input 'identity_ship'))
    ?>  (eligible who runtime.config)
    ?>  (available offer who now)
    ?>  (same-actor:stead-session issuer.offer identity:(authority db.s offer retired now))
    =/  previous  (~(get by sessions.auth.s) (digest:stead-session 'stead.session/1' session.req))
    ?>  ?~(previous & ?|((lte expires.u.previous now) =(who ship.identity.u.previous)))
    =/  identity  (resolve db.s who now)
    =/  seen  (~(get by guests.offer) who)
    ?>  ?~(seen & =(identity identity.u.seen))
    =/  shadow=state:stead-session  [counter.auth.s (~(run by pending.s) |=(f=flight row.f)) ~]
    =/  started  (begin-as:stead-session shadow identity home.config origin.config now entropy &)
    ?>  =(%pending status.started)
    =/  ch  (~(got by challenges.next.started) id.started)
    =/  result  (answer 'pending' ~[['challenge_id' id.started] ['comparison_code' (cut 3 [0 12] id.started)] ['home' (scot %p home.config)] ['origin' origin.config] ['expires_at_ms' (decimal expires.ch)]])
    [s(auth auth.s(counter counter.next.started), pending (~(put by pending.s) id.started [id ch])) result ~[(cookie:stead-http & cookie.started |)] [~ who (proof-message id.started ch)]]
  ?>  (keys input ?:(=('/stead/auth/invite/consume' route.req) ~['protocol' 'challenge_id' 'return_proof'] ~['protocol' 'challenge_id']))
  =/  id  (field input 'challenge_id')
  =/  f  (~(got by pending.s) id)
  =/  ch  row.f
  ?>  &((token-valid:stead-session pending.req) =(browser.ch (digest:stead-session 'stead.browser-binding/1' pending.req)) =(home.ch home.config) =(origin.ch origin.config))
  =/  offer  (~(got by offers.s) offer-id.f)
  ?>  (same-actor:stead-session issuer.offer identity:(authority db.s offer retired now))
  =/  person  identity.ch
  =/  old-key  (digest:stead-session 'stead.session/1' session.req)
  =/  previous  (~(get by sessions.auth.s) old-key)
  ?>  ?~(previous & ?|((lte expires.u.previous now) (same-actor:stead-session person identity.u.previous)))
  ?>  &((available offer ship.person now) =(person (resolve db.s ship.person now)))
  ?:  =('/stead/auth/invite/status' route.req)
    [s (answer ?:(approved.ch 'approved' 'pending') ~[['challenge_id' id]]) ~ ~]
  ?>  &(=('/stead/auth/invite/consume' route.req) approved.ch)
  =/  returned  (field input 'return_proof')
  ?>  (proves-return:stead-session return-digest.ch returned)
  =.  pending.s  (~(del by pending.s) id)
  =/  seen  (~(get by guests.offer) ship.person)
  ?>  ?~(seen & =(person identity.u.seen))
  ?:  &(=('request' mode.offer) ?~(seen & !accepted.u.seen))
    ?>  ?|(?=(^ seen) (lth ~(wyt by guests.offer) 32))
    =.  guests.offer  (~(put by guests.offer) ship.person [person |])
    [s(offers (~(put by offers.s) offer-id.f offer)) (answer 'requested' ~) ~[(cookie:stead-http & '' &)] ~]
  =/  out  (admit db.s offer-id.f offer person role.offer retired now)
  ::  An authenticated browser exchanging its own cookie loses its old trust
  ::  only on successful issuance. Preserve all unrelated member/device sessions.
  =/  sessions  ?~(previous sessions.auth.s (~(del by sessions.auth.s) old-key))
  =/  staged  auth.s(challenges (~(put by challenges.auth.s) id ch), sessions sessions)
  =/  session  (consume-bound:stead-session staged id pending.req person home.config origin.config now entropy returned)
  ?>  =(%accepted status.session)
  =.  s  s(db next.out, auth next.session, offers (~(put by offers.s) offer-id.f changed.out))
  [s (answer 'authenticated' ~[['csrf' csrf.session] ['project_id' project.offer]]) ~[(cookie:stead-http | cookie.session |) (cookie:stead-http & '' &)] ~]
--

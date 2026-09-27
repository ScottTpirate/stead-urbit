::  Pure browser API orchestration. The Gall owner enforces the Eyre boundary.
/+  stead-codec, stead-team, stead-team-codec, stead-team-config, stead-session, stead-http, stead-projection, stead-views, stead-updates, stead-update-codec
=,  stead-codec
|%
+$  ephemeral  [auth=state:stead-session pages=state:stead-views updates=state:stead-updates]
+$  result
  $:  status=@ud  bytes=@t  cookies=(list @t)  outgoing=(unit [ship=@p bytes=@t])
      db=state:stead-team  view=state:stead-projection  transient=ephemeral
  ==
++  reply
  |=  [db=state:stead-team view=state:stead-projection transient=ephemeral status=@ud bytes=@t]
  ^-  result
  [status bytes ~ ~ db view transient]
++  small
  |=  [raw=@t expected=(list @t) protocol=@t]
  ^-  object-map
  ?>  (lte (met 3 raw) 2.048)
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  ?>  &((keys p.value expected) =(protocol (field p.value 'protocol')))
  p.value
++  approval-message
  |=  [id=@t row=challenge:stead-session]
  ^-  @t
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.auth/1']  ['purpose' 'member-session']
      ['challenge_id' id]  ['home' (scot %p home.row)]  ['origin' origin.row]
      ['identity_ship' (scot %p ship.identity.row)]
      ['principal_id' principal.identity.row]  ['binding_id' binding.identity.row]
      ['binding_revision' (decimal revision.identity.row)]  ['expires_at_ms' (decimal expires.row)]
  ==
++  approve
  |=  [db=state:stead-team transient=ephemeral sender=@p raw=@t now=@ud]
  ^-  ephemeral
  =/  value  (small raw ~['protocol' 'purpose' 'challenge_id' 'home' 'origin' 'identity_ship' 'principal_id' 'binding_id' 'binding_revision' 'expires_at_ms'] 'stead.auth/1')
  =/  who  (need (identity:stead-team-config registry.db sender now))
  =/  config  (need current.registry.db)
  ?>  &(=(principal.identity.who (field value 'principal_id')) =(binding.identity.who (field value 'binding_id')))
  ?>  &(=(revision.identity.who (uint (field value 'binding_revision'))) =((scot %p sender) (field value 'identity_ship')))
  ?>  =((scot %p home.config) (field value 'home'))
  =/  accepted  (approve:stead-session auth.transient (field value 'challenge_id') sender identity.who home.config (field value 'origin') (field value 'protocol') (field value 'purpose') (uint (field value 'expires_at_ms')) now)
  ?>  =(%approved status.accepted)
  transient(auth next.accepted)
++  correlated-error
  |=  [raw=@t error=@t]
  ^-  @t
  =/  base  (need (parse-result (error:stead-team error)))
  ?>  ?=([%o *] base)
  =/  attempted
    %-  mule
    |.
    =/  obj  (need (parse raw))
    ?>  ?=([%o *] obj)
    =/  request  (field p.obj 'request_id')
    ?>  (uuid request)
    (canonical [%o (~(put by (~(put by p.base) 'request_id' [%s request])) 'canonical_sha256' [%s (hash 'stead.command/3' (canonical obj))])])
  ?:  ?=(%| -.attempted)  (canonical base)
  p.attempted
++  call
  |=  [db=state:stead-team view=state:stead-projection transient=ephemeral request=incoming:stead-http now=@ud entropy=@]
  ^-  result
  =/  config  (need current.registry.db)
  =/  route  route.request
  =/  raw  body.request
  ?:  =('/stead/api/capabilities' route)
    =/  input  (small raw ~['protocol'] 'stead.capabilities/3')
    (reply db view transient 200 (canonical (object ~[['protocol' 'stead.capabilities/3'] ['profile' 'configured-team'] ['commands' 'stead.command/3'] ['queries' 'stead.query/3'] ['updates' 'stead.updates/3'] ['authentication' 'native-approved-browser/1'] ['max_request_bytes' '65536'] ['max_response_bytes' '262144'] ['page_size' '20'] ['runtime' runtime.config]])))
  ?:  =('/stead/auth/start' route)
    =/  input  (small raw ~['protocol' 'identity_ship'] 'stead.auth/1')
    =/  ship  (need (slaw %p (field input 'identity_ship')))
    ?>  =((scot %p ship) (field input 'identity_ship'))
    =/  who  (identity:stead-team-config registry.db ship now)
    ?~  who  (reply db view transient 200 (error:stead-team 'denied_or_not_found'))
    =/  previous  (~(get by sessions.auth.transient) (digest:stead-session 'stead.session/1' session.request))
    ?:  &(?=(^ previous) (gth expires.u.previous now))
      (reply db view transient 200 (error:stead-team 'logout_required'))
    =/  started  (begin:stead-session auth.transient identity.u.who home.config origin.config now entropy)
    ?.  =(%pending status.started)  (reply db view transient 200 (error:stead-team 'capacity_exceeded'))
    =/  challenge  (~(got by challenges.next.started) id.started)
    =/  response  (canonical (object ~[['protocol' 'stead.auth/1'] ['status' 'pending'] ['challenge_id' id.started] ['comparison_code' (cut 3 [0 12] id.started)] ['home' (scot %p home.config)] ['origin' origin.config] ['expires_at_ms' (decimal expires.challenge)]]))
    =/  out  (reply db view transient(auth next.started) 200 response)
    out(cookies ~[(cookie:stead-http & cookie.started |)], outgoing [~ [ship (approval-message id.started challenge)]])
  ?:  ?|(=('/stead/auth/status' route) =('/stead/auth/consume' route))
    =/  input  (small raw ~['protocol' 'challenge_id'] 'stead.auth/1')
    =/  id  (field input 'challenge_id')
    =/  found  (~(get by challenges.auth.transient) id)
    ?~  found  (reply db view transient 401 (error:stead-team 'session_required'))
    =/  row  u.found
    =/  who  (identity:stead-team-config registry.db ship.identity.row now)
    ?~  who  (reply db view transient 401 (error:stead-team 'session_required'))
    ?.  ?&  (gth expires.row now)  (token-valid:stead-session pending.request)
            =(browser.row (digest:stead-session 'stead.browser-binding/1' pending.request))
            (same-actor:stead-session identity.row identity.u.who)
            =(origin.row origin.config)  =(home.row home.config)
        ==
      (reply db view transient 401 (error:stead-team 'session_required'))
    ?:  =('/stead/auth/status' route)
      (reply db view transient 200 (canonical (object ~[['protocol' 'stead.auth/1'] ['status' ?:(approved.row 'approved' 'pending')] ['challenge_id' id]])))
    =/  consumed  (consume:stead-session auth.transient id pending.request identity.u.who home.config origin.config now entropy)
    ?.  =(%accepted status.consumed)  (reply db view transient 200 (error:stead-team 'denied_or_not_found'))
    =/  out  (reply db view transient(auth next.consumed) 200 (canonical (object ~[['protocol' 'stead.auth/1'] ['status' 'authenticated'] ['csrf' csrf.consumed]])))
    out(cookies ~[(cookie:stead-http | cookie.consumed |) (cookie:stead-http & '' &)])
  =/  existing  (~(get by sessions.auth.transient) (digest:stead-session 'stead.session/1' session.request))
  ?~  existing  (reply db view transient 401 (error:stead-team 'session_required'))
  =/  member  (identity:stead-team-config registry.db ship.identity.u.existing now)
  ?~  member  (reply db view transient 401 (error:stead-team 'session_required'))
  =/  actor  (browser-context:stead-team db u.existing now)
  ?~  actor  (reply db view transient 401 (error:stead-team 'session_required'))
  ?:  =('/stead/auth/resume' route)
    =/  input  (small raw ~['protocol'] 'stead.auth/1')
    =/  resumed  (resume:stead-session auth.transient session.request identity.u.member home.config origin.config now entropy)
    ?.  =(%authenticated status.resumed)  (reply db view transient 401 (error:stead-team 'session_required'))
    =/  cleaned  (forget-session:stead-updates updates.transient pages.transient audit.u.actor)
    (reply db view transient(auth next.resumed, pages pages.cleaned, updates next.cleaned) 200 (canonical (object ~[['protocol' 'stead.auth/1'] ['status' 'authenticated'] ['csrf' csrf.resumed]])))
  =/  authenticated  (authorize:stead-session auth.transient session.request csrf.request identity.u.member home.config origin.config now)
  ?~  authenticated
    (reply db view transient 403 ?:(=('/stead/api/command' route) (correlated-error raw 'invalid_csrf') (error:stead-team 'invalid_csrf')))
  ?:  =('/stead/auth/logout' route)
    =/  input  (small raw ~['protocol'] 'stead.auth/1')
    =/  ended  (logout:stead-session auth.transient session.request csrf.request identity.u.member home.config origin.config now)
    ?>  =(%logged-out status.ended)
    =/  cursors  (malt (skip ~(tap by cursors.pages.transient) |=([key=@t val=cursor-record:stead-views] =(audit.u.actor audit.actor.val))))
    =/  cleaned  (prune:stead-updates db next.ended updates.transient pages.transient(cursors cursors) now)
    =/  out  (reply db view transient(auth next.ended, pages pages.cleaned, updates next.cleaned) 200 (canonical (object ~[['protocol' 'stead.auth/1'] ['status' 'logged_out']])))
    out(cookies ~[(cookie:stead-http | '' &) (cookie:stead-http & '' &)])
  :: Correlate version rejection only after current session and CSRF admission.
  =/  domain
    ?+  route  ''
      '/stead/api/command'  'stead.command/3'
      '/stead/api/query'  'stead.query/3'
      '/stead/api/updates'  'stead.updates/3'
    ==
  =/  unsupported=(unit @t)
    ?:  =('' domain)  ~
    =/  attempted  (mule |.((version-error:stead-team-codec (need (parse raw)) domain)))
    ?:  ?=(%| -.attempted)  ~
    p.attempted
  ?^  unsupported  (reply db view transient 200 u.unsupported)
  ?:  =('/stead/api/command' route)
    =/  decoded  (mule |.((decode:stead-team-codec raw)))
    ?:  ?=(%| -.decoded)  (reply db view transient 200 (correlated-error raw 'invalid_command'))
    =/  result  (apply-command:stead-team db u.actor p.decoded now)
    =/  projected
      ?:  =(db next.result)  view
      ?>  ?=(^ journal.data.next.result)
      (append:stead-projection view i.journal.data.next.result)
    =/  advanced=[next=state:stead-updates pages=state:stead-views]
      ?:  (ready:stead-projection next.result projected)
        (advance:stead-updates next.result auth.transient updates.transient pages.transient now)
      [*state:stead-updates *state:stead-views]
    (reply next.result projected transient(updates next.advanced, pages pages.advanced) 200 response.result)
  ?:  =('/stead/api/updates' route)
    =/  decoded  (mule |.((decode:stead-update-codec raw)))
    ?:  ?=(%| -.decoded)  (reply db view transient 200 (error:stead-team 'invalid_update'))
    =/  result  (execute:stead-updates db view auth.transient updates.transient pages.transient u.actor p.decoded now entropy)
    (reply db view transient(updates next.result, pages pages.result) 200 response.result)
  ?:  =('/stead/api/query' route)
    =/  decoded  (mule |.((decode-query:stead-team-codec raw)))
    ?:  ?=(%| -.decoded)  (reply db view transient 200 (error:stead-team 'invalid_query'))
    =/  result  (execute:stead-views db view pages.transient u.actor p.decoded now entropy)
    (reply db view transient(pages next.result) 200 response.result)
  (reply db view transient 200 (error:stead-team 'unsupported_version'))
--

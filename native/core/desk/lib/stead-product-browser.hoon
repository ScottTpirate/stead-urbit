::  Browser carrier for the explicitly activated native-human-doc/1 Home.
::  Existing verified challenge/session/CSRF machinery is reused. New bodies
::  reach only the single product dispatcher; no legacy mutation fallback.
/+  stead-codec, stead-team, stead-team-config, stead-session, stead-http, stead-browser, stead-projection, stead-views, stead-updates, stead-product-home, stead-product-history
=,  stead-codec
|%
+$  result
  $:  status=@ud  bytes=@t  cookies=(list @t)  outgoing=(unit [ship=@p bytes=@t])
      next=pair:stead-product-home  view=state:stead-projection  transient=ephemeral:stead-browser
  ==
++  reply
  |=  [data=pair:stead-product-home view=state:stead-projection transient=ephemeral:stead-browser status=@ud bytes=@t]
  ^-  result
  [status bytes ~ ~ data view transient]
++  active-auth
  |=  [data=pair:stead-product-home transient=ephemeral:stead-browser request=incoming:stead-http now=@ud]
  ^-  ?
  =/  ship=(unit @p)
    ?:  =('/stead/auth/start' route.request)
      =/  value  (small:stead-browser body.request ~['protocol' 'identity_ship'] (auth-version:stead-browser body.request))
      =/  who  (slaw %p (field value 'identity_ship'))
      ?~  who  ~
      ?.  =((scot %p u.who) (field value 'identity_ship'))  ~
      who
    ?:  ?|(=('/stead/auth/status' route.request) =('/stead/auth/consume' route.request))
      =/  value  (small:stead-browser body.request (consume-fields:stead-browser (auth-version:stead-browser body.request) route.request) (auth-version:stead-browser body.request))
      =/  found  (~(get by challenges.auth.transient) (field value 'challenge_id'))
      ?~(found ~ (some ship.identity.u.found))
    =/  found  (~(get by sessions.auth.transient) (digest:stead-session 'stead.session/1' session.request))
    ?~(found ~ (some ship.identity.u.found))
  ?~  ship  |
  =/  actor  (native-context:stead-team db.data u.ship now)
  ?~(actor | (active-member:stead-product-history (current:stead-product-home data) u.actor now))
++  call
  |=  [data=pair:stead-product-home view=state:stead-projection transient=ephemeral:stead-browser request=incoming:stead-http now=@ud entropy=@]
  ^-  result
  ?>  (ready:stead-product-home phase.data)
  =/  route  route.request
  ?:  =('/stead/api/capabilities' route)
    =/  checked  (small:stead-browser body.request ~['protocol'] 'stead.capabilities/3')
    (reply data view transient 200 (capabilities:stead-product-home db.data))
  ?:  (~(has in (silt ~['/stead/auth/start' '/stead/auth/status' '/stead/auth/consume' '/stead/auth/resume' '/stead/auth/devices' '/stead/auth/logout'])) route)
    ::  Logout can erase an inactive member's session; it grants no content.
    ?.  ?|(=('/stead/auth/logout' route) (active-auth data transient request now))
      (reply data view transient 401 (error:stead-team 'session_required'))
    =/  out  (call:stead-browser db.data view transient request now entropy)
    ?>  =(db.data db.out)
    [status.out bytes.out cookies.out outgoing.out data view.out transient.out]
  =/  existing  (~(get by sessions.auth.transient) (digest:stead-session 'stead.session/1' session.request))
  ?~  existing  (reply data view transient 401 (error:stead-team 'session_required'))
  =/  actor  (browser-context:stead-team db.data u.existing now)
  ?~  actor  (reply data view transient 401 (error:stead-team 'session_required'))
  ?.  (active-member:stead-product-history (current:stead-product-home data) u.actor now)
    (reply data view transient 401 (error:stead-team 'session_required'))
  =/  config  (need current.registry.db.data)
  =/  authorized  (authorize:stead-session auth.transient session.request csrf.request identity.u.actor home.config origin.config now)
  ?~  authorized  (reply data view transient 403 (error:stead-team 'invalid_csrf'))
  ?:  =('/stead/api/command' route)
    =/  out  (command:stead-product-home data u.actor body.request now)
    =/  projected  (projected:stead-product-home db.data db.next.out view)
    (reply next.out projected transient(updates *state:stead-updates) 200 response.out)
  ?:  =('/stead/api/query' route)
    =/  out  (query:stead-product-home data view pages.transient u.actor body.request now entropy)
    (reply data view transient(pages next.out) 200 response.out)
  (reply data view transient 200 (error:stead-team 'unsupported_version'))
--

::  Pure bounded transitions. The home supplies verified actors and Gall
::  entropy. This library is not an authentication endpoint.
/+  stead-codec
|%
+$  actor  [ship=@p principal=@t binding=@t revision=@ud active=? expires=@ud]
+$  challenge
  [identity=actor home=@p origin=@t browser=@t expires=@ud approved=?]
+$  session
  [identity=actor home=@p origin=@t browser=@t csrf=@t audit=@t expires=@ud]
+$  state
  [counter=@ud challenges=(map @t challenge) sessions=(map @t session)]
+$  result  [status=@tas id=@t cookie=@t csrf=@t next=state]
++  digest
  |=  [purpose=@t text=@t]
  ^-  @t
  (hash:stead-codec purpose text)
++  token
  |=  [entropy=@ counter=@ud purpose=@t]
  ^-  @t
  (digest purpose (bytes-hex:stead-codec (jam [entropy counter])))
++  live
  |=  [identity=actor now=@ud]
  ^-  ?
  ?&  active.identity  (gth expires.identity now)
      (lte expires.identity 18.446.744.073.709.551.615)
      (gth revision.identity 0)  (lte revision.identity 18.446.744.073.709.551.615)
      (uuid:stead-codec principal.identity)  (uuid:stead-codec binding.identity)
  ==
++  same-actor
  |=  [left=actor right=actor]
  ^-  ?
  ?&  (live right 0)  =(ship.left ship.right)  =(principal.left principal.right)
      =(binding.left binding.right)  =(revision.left revision.right)
  ==
++  origin-valid
  |=  origin=@t
  ^-  ?
  ?.  &((gth (met 3 origin) 8) (lte (met 3 origin) 256))  |
  ?.  =('https://' (cut 3 [0 8] origin))  |
  =/  chars  (rip 3 (cut 3 [8 (sub (met 3 origin) 8)] origin))
  =/  label=@ud  0
  =/  previous=@  0
  |-
  ?~  chars  &((gth label 0) !=(previous 45))
  =/  c  i.chars
  ?:  =(c 58)
    ?.  &((gth label 0) !=(previous 45) ?=(^ t.chars))  |
    (port-valid t.chars)
  ?:  =(c 46)
    ?.  &((gth label 0) !=(previous 45))  |
    $(chars t.chars, label 0, previous c)
  ?.  ?|  &((gte c 97) (lte c 122))  &((gte c 48) (lte c 57))
          &(=(c 45) (gth label 0))
      ==
    |
  ?:  (gte label 63)  |
  $(chars t.chars, label +(label), previous c)
++  port-valid
  |=  digits=(list @)
  ^-  ?
  =/  count=@ud  0
  =/  port=@ud  0
  |-
  ?~  digits  &((gth count 0) (gth port 0) (lte port 65.535) !=(port 443))
  ?:  (gte count 5)  |
  ?.  &((gte i.digits 48) (lte i.digits 57))  |
  ?:  &(=(count 0) =(i.digits 48))  |
  $(digits t.digits, count +(count), port (add (mul port 10) (sub i.digits 48)))
++  token-valid
  |=  value=@t
  ^-  ?
  ?&  =(64 (met 3 value))
      %+  levy  (rip 3 value)
      |=(c=@ ?|(&((gte c 48) (lte c 57)) &((gte c 97) (lte c 102))))
  ==
++  prune
  |=  [db=state now=@ud]
  ^-  state
  =.  challenges.db
    (malt (skim ~(tap by challenges.db) |=([key=@t val=challenge] (gth expires.val now))))
  db(sessions (malt (skim ~(tap by sessions.db) |=([key=@t val=session] (gth expires.val now)))))
++  reject
  |=  [db=state why=@tas]
  ^-  result
  [why '' '' '' db]
++  begin
  |=  [db=state identity=actor home=@p origin=@t now=@ud entropy=@]
  ^-  result
  =.  db  (prune db now)
  ?.  &((live identity now) (origin-valid origin) !=(ship.identity home))  (reject db %denied)
  ?:  ?|  (gte counter.db 18.446.744.073.709.551.615)
          (gte (lent ~(tap by challenges.db)) 32)
          (gte (lent (skim ~(tap by challenges.db) |=([key=@t val=challenge] =(principal.identity principal.identity.val)))) 4)
      ==
    (reject db %capacity)
  =.  counter.db  +(counter.db)
  =/  id  (token entropy counter.db 'stead.challenge/1')
  =/  cookie  (token entropy counter.db 'stead.browser-binding/1')
  =/  row=challenge
    [identity home origin (digest 'stead.browser-binding/1' cookie) (min expires.identity (add now 120.000)) |]
  ?:  (~(has by challenges.db) id)  (reject db %capacity)
  [%pending id cookie '' db(challenges (~(put by challenges.db) id row))]
++  approve
  |=  [db=state id=@t sender=@p identity=actor home=@p origin=@t protocol=@t purpose=@t expires=@ud now=@ud]
  ^-  result
  =.  db  (prune db now)
  ?.  (token-valid id)  (reject db %denied)
  =/  found  (~(get by challenges.db) id)
  ?~  found  (reject db %denied)
  =/  row  u.found
  ?.  ?&  !approved.row  =(sender ship.identity.row)
          (same-actor identity.row identity)  (live identity now)
          =(home home.row)  =(origin origin.row)  =(expires expires.row)
          =('stead.auth/1' protocol)  =('member-session' purpose)
      ==
    (reject db %denied)
  [%approved id '' '' db(challenges (~(put by challenges.db) id row(approved &)))]
++  consume
  |=  [db=state id=@t cookie=@t identity=actor home=@p origin=@t now=@ud entropy=@]
  ^-  result
  =.  db  (prune db now)
  ?.  &((token-valid id) (token-valid cookie))  (reject db %denied)
  =/  found  (~(get by challenges.db) id)
  ?~  found  (reject db %denied)
  =/  row  u.found
  ?.  ?&  approved.row  (live identity now)  (same-actor identity.row identity)
          =(home home.row)  =(origin origin.row)
          =(browser.row (digest 'stead.browser-binding/1' cookie))
      ==
    (reject db %denied)
  =/  before  db
  =.  sessions.db
    (malt (skip ~(tap by sessions.db) |=([key=@t val=session] =(browser.row browser.val))))
  ?:  ?|  (gte counter.db 18.446.744.073.709.551.615)
          (gte (lent ~(tap by sessions.db)) 64)
          (gte (lent (skim ~(tap by sessions.db) |=([key=@t val=session] =(principal.identity principal.identity.val)))) 4)
      ==
    (reject before %capacity)
  =.  counter.db  +(counter.db)
  =/  bearer  (token entropy counter.db 'stead.session/1')
  =/  csrf  (token entropy counter.db 'stead.csrf/1')
  =/  key  (digest 'stead.session/1' bearer)
  =/  audit  (token entropy counter.db 'stead.session-audit/1')
  =/  logged=session
    [identity home origin browser.row (digest 'stead.csrf/1' csrf) audit (min expires.identity (add now 1.800.000))]
  ?:  (~(has by sessions.db) key)  (reject before %capacity)
  =.  challenges.db  (~(del by challenges.db) id)
  [%accepted audit bearer csrf db(sessions (~(put by sessions.db) key logged))]
++  authorize
  |=  [db=state cookie=@t csrf=@t identity=actor home=@p origin=@t now=@ud]
  ^-  (unit session)
  ?.  &((token-valid cookie) (token-valid csrf))  ~
  =/  found  (~(get by sessions.db) (digest 'stead.session/1' cookie))
  ?~  found  ~
  =/  row  u.found
  ?.  ?&  (gth expires.row now)  (live identity now)
          (same-actor identity.row identity)  =(home home.row)  =(origin origin.row)
          =(csrf.row (digest 'stead.csrf/1' csrf))
      ==
    ~
  found
++  logout
  |=  [db=state cookie=@t csrf=@t identity=actor home=@p origin=@t now=@ud]
  ^-  result
  =/  found  (authorize db cookie csrf identity home origin now)
  ?~  found  (reject db %denied)
  [%logged-out '' '' '' (invalidate-browser db browser.u.found)]
++  resume
  ::  The HTTP owner must first require native TLS and exact Host/Origin for
  ::  this explicit CSRF exception. No session extension or bearer rotation.
  |=  [db=state cookie=@t identity=actor home=@p origin=@t now=@ud entropy=@]
  ^-  result
  ?.  (token-valid cookie)  (reject db %denied)
  =/  key  (digest 'stead.session/1' cookie)
  =/  found  (~(get by sessions.db) key)
  ?~  found  (reject db %denied)
  =/  row  u.found
  ?.  ?&  (gth expires.row now)  (live identity now)
          (same-actor identity.row identity)  =(home home.row)  =(origin origin.row)
      ==
    (reject db %denied)
  ?:  (gte counter.db 18.446.744.073.709.551.615)  (reject db %capacity)
  =/  counter  +(counter.db)
  =/  csrf  (token entropy counter 'stead.csrf/1')
  =/  hashed  (digest 'stead.csrf/1' csrf)
  ?:  =(hashed csrf.row)  (reject db %capacity)
  [%authenticated '' '' csrf db(counter counter, sessions (~(put by sessions.db) key row(csrf hashed)))]
++  replace
  ::  Caller resolves both actors from current home bindings. Browser hashes
  ::  never authorize revocation: only the prior cookie plus CSRF does.
  |=  [db=state cookie=@t csrf=@t prior=actor identity=actor home=@p origin=@t now=@ud entropy=@]
  ^-  result
  =/  found  (authorize db cookie csrf prior home origin now)
  ?~  found  (reject db %denied)
  =/  staged  (begin (invalidate-browser db browser.u.found) identity home origin now entropy)
  ?.  =(%pending status.staged)  (reject db status.staged)
  staged
++  invalidate-browser
  |=  [db=state browser=@t]
  ^-  state
  =.  challenges.db
    (malt (skip ~(tap by challenges.db) |=([key=@t val=challenge] =(browser browser.val))))
  db(sessions (malt (skip ~(tap by sessions.db) |=([key=@t val=session] =(browser browser.val)))))
++  invalidate-actor
  |=  [db=state principal=@t]
  ^-  state
  =.  challenges.db
    (malt (skip ~(tap by challenges.db) |=([key=@t val=challenge] =(principal principal.identity.val))))
  db(sessions (malt (skip ~(tap by sessions.db) |=([key=@t val=session] =(principal principal.identity.val)))))
--

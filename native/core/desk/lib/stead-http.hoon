::  Pure application HTTP boundary. Only the owner agent handles Eyre events.
::  Host/Origin checks do not prove TLS: require Eyre secure and reject its
::  loopback Forwarded override inputs before trusting that bit.
/+  stead-session
|%
+$  incoming  [route=@t body=@t session=@t pending=@t csrf=@t]
++  lower
  |=  text=@t
  ^-  @t
  (crip (cass (trip text)))
++  split
  |=  [text=@t delimiter=@]
  ^-  (list @t)
  =/  chars  (rip 3 text)
  =/  part=@t  ''
  =/  out=(list @t)  ~
  |-
  ?~  chars  (flop [part out])
  ?:  =(i.chars delimiter)  $(chars t.chars, part '', out [part out])
  $(chars t.chars, part (cat 3 part i.chars))
++  trim
  |=  text=@t
  ^-  @t
  =/  chars  (rip 3 text)
  =/  backwards=?  |
  |-
  ?~  chars  ''
  ?:  =(32 i.chars)  $(chars t.chars)
  ?:  backwards  (rap 3 (flop chars))
  $(chars (flop chars), backwards &)
++  headers
  |=  rows=(list [key=@t value=@t])
  ^-  (unit (map @t @t))
  =/  count=@ud  0
  =/  size=@ud  0
  =/  result=(map @t @t)  ~
  |-
  ?~  rows  (some result)
  =/  value  value.i.rows
  ?:  (gte count 32)  ~
  =.  size  (add size (add (met 3 key.i.rows) (met 3 value)))
  ?.  &((lte size 8.192) (gth (met 3 key.i.rows) 0))  ~
  =/  key  (lower key.i.rows)
  ?:  ?|  &((~(has by result) key) !=('cookie' key))  =('forwarded' key)
          =('x-forwarded-' (cut 3 [0 12] key))
      ==
    ~
  ?.  (levy (rip 3 key) |=(c=@ ?|(&((gte c 97) (lte c 122)) &((gte c 48) (lte c 57)) =(c 45))))  ~
  ?.  (levy (rip 3 value) |=(c=@ &((gte c 32) !=(c 127))))  ~
  ::  Browsers may split Cookie into separate transport fields. Validate the
  ::  complete combined jar below: duplicate names never select a credential.
  =/  prior  (~(get by result) key)
  =/  combined  ?~(prior value (rap 3 ~[u.prior '; ' value]))
  $(rows t.rows, count +(count), result (~(put by result) key combined))
++  cookie-pair
  |=  text=@t
  ^-  (unit [name=@t value=@t])
  =/  chars  (rip 3 text)
  =/  name=@t  ''
  |-
  ?~  chars  ~
  ?:  =(61 i.chars)  (some [name (rap 3 t.chars)])
  $(chars t.chars, name (cat 3 name i.chars))
++  cookies
  |=  text=@t
  ^-  (unit (map @t @t))
  ?.  (lte (met 3 text) 8.192)  ~
  ?:  =('' text)  (some *(map @t @t))
  =/  parts  (split text 59)
  ?.  (lte (lent parts) 32)  ~
  =/  result=(map @t @t)  ~
  |-
  ?~  parts  (some result)
  =/  pair  (cookie-pair (trim i.parts))
  ?~  pair  ~
  =/  name  name.u.pair
  =/  value  value.u.pair
  ?.  &((gth (met 3 name) 0) !(~(has by result) name))  ~
  ?.  %+  levy  (rip 3 name)
      |=  c=@
      ?|  &((gte c 48) (lte c 57))  &((gte c 65) (lte c 90))
          &((gte c 97) (lte c 122))
          (~(has in (silt ~[33 35 36 37 38 39 42 43 45 46 94 95 96 124 126])) c)
      ==
    ~
  ::  Strict unquoted RFC 6265 cookie-octet subset, for unknown pairs too.
  ?.  %+  levy  (rip 3 value)
      |=  c=@
      ?|  =(c 33)  &((gte c 35) (lte c 43))  &((gte c 45) (lte c 58))
          &((gte c 60) (lte c 91))  &((gte c 93) (lte c 126))
      ==
    ~
  ?:  ?|  =('__Host-stead-session' name)  =('__Host-stead-pending' name)
      ==
    ?.  (token-valid:stead-session value)  ~
    $(parts t.parts, result (~(put by result) name value))
  $(parts t.parts, result (~(put by result) name value))
++  field
  |=  [values=(map @t @t) key=@t]
  ^-  @t
  =/  found  (~(get by values) key)
  ?~(found '' u.found)
++  validate
  |=  [request=inbound-request:eyre origin=@t assets=(set @t)]
  ^-  (unit incoming)
  (validate-routes request origin (~(put in assets) '/stead/') (silt ~['/stead/auth/start' '/stead/auth/status' '/stead/auth/consume' '/stead/auth/logout' '/stead/auth/resume' '/stead/api/capabilities' '/stead/api/command' '/stead/api/query' '/stead/api/updates']))
++  validate-routes
  |=  [request=inbound-request:eyre origin=@t assets=(set @t) posts=(set @t)]
  ^-  (unit incoming)
  ?.  &(secure.request (origin-valid:stead-session origin))  ~
  =/  req  request.request
  ?.  (lte (met 3 url.req) 512)  ~
  =/  parsed  (headers header-list.req)
  ?~  parsed  ~
  =/  values  u.parsed
  ?.  =((cut 3 [8 (sub (met 3 origin) 8)] origin) (field values 'host'))  ~
  =/  jar  (cookies (field values 'cookie'))
  ?~  jar  ~
  =/  csrf  (field values 'x-stead-csrf')
  ?.  ?|  =('' csrf)  (token-valid:stead-session csrf)
      ==
    ~
  ?:  =(%'GET' method.req)
    ?.  (~(has in assets) url.req)
      ~
    ?.  ?~(body.req & =([0 0] u.body.req))  ~
    ?.  ?|  =('' (field values 'origin'))  =(origin (field values 'origin'))
        ==
      ~
    (some [url.req '' '' '' ''])
  ?.  =(%'POST' method.req)  ~
  ?.  (~(has in posts) url.req)  ~
  ?.  &(=(origin (field values 'origin')) =('application/json' (field values 'content-type')))  ~
  ?~  body.req  ~
  ?.  &((gth p.u.body.req 0) (lte p.u.body.req 65.536) =(p.u.body.req (met 3 q.u.body.req)))  ~
  (some [url.req q.u.body.req (field u.jar '__Host-stead-session') (field u.jar '__Host-stead-pending') csrf])
++  security-headers
  ^-  (list [@t @t])
  :~  ['cache-control' 'no-store']
      ['content-security-policy' (crip "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")]
      ['x-content-type-options' 'nosniff']
      ['x-frame-options' 'DENY']
      ['referrer-policy' 'no-referrer']
      ['cross-origin-resource-policy' 'same-origin']
  ==
++  cookie
  |=  [pending=? value=@t clear=?]
  ^-  @t
  ?>  ?:(clear =('' value) (token-valid:stead-session value))
  (rap 3 ~[?:(pending '__Host-stead-pending=' '__Host-stead-session=') value '; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=' ?:(clear '0' ?:(pending '120' '1800'))])
--

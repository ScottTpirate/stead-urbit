::  Pure helper controls; actual Eyre owner and Gall transport need team-check.
/+  stead-codec, stead-session, stead-browser, stead-identity-core, stead-http, stead-eyre
=,  stead-identity-core
=/  principal  '019939ba-4000-7000-8000-000000000102'
=/  binding  '019939ba-4000-7000-8000-000000000202'
=/  origin  'https://home.localhost:8443'
=/  personal  'https://bus.localhost:8444'
=/  config-raw  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.identity-config/1'] ['expected_revision' '0'] ['home' '~zod'] ['home_origin' origin] ['origin' personal]]))
=/  configured  (configure *state config-raw ~bus)
=/  enrollment  (need config.configured)
=/  actor=actor:stead-session  [~bus principal binding 1 & 9.999.999]
=/  challenge  (begin:stead-session *state:stead-session actor ~zod origin 1.000 1)
=/  id  id.challenge
=/  metadata  (approval-message:stead-browser id (~(got by challenges.next.challenge) id))
=/  received  (receive configured ~zod ~bus metadata 1.001 2)
=/  approval  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.identity/1'] ['challenge_id' id] ['csrf' nonce:(~(got by requests.received) id)] ['comparison_code' (cut 3 [0 12] id)] ['origin' origin]]))
|%
++  rejected
  |=  candidate=(trap)
  ^-  ?
  =/  outcome  (mule candidate)
  ?=(%| -.outcome)
++  test-identity-configuration
  ^-  tang
  ?>  =(1 revision.enrollment)
  ?>  (valid-configuration enrollment ~bus)
  ?>  !(valid-configuration enrollment ~zod)
  ?>  !(valid-configuration enrollment(revision 0) ~bus)
  ?>  !(valid-configuration enrollment(revision 18.446.744.073.709.551.616) ~bus)
  ?>  (rejected |.((configure configured config-raw ~bus)))
  ~
++  test-identity-origin-isolation
  ^-  tang
  ?>  !(valid-configuration enrollment(origin 'https://home.localhost:8444') ~bus)
  ?>  !(valid-configuration enrollment(origin 'http://bus.localhost:8444') ~bus)
  ?>  !(valid-configuration enrollment(home-origin 'https://home.localhost:8443/') ~bus)
  ~
++  test-identity-sender-and-metadata
  ^-  tang
  ?>  (rejected |.((receive configured ~nec ~bus metadata 1.001 2)))
  ?>  (rejected |.((receive configured ~zod ~nec metadata 1.001 2)))
  ?>  (rejected |.((receive configured ~zod ~bus (cat 3 metadata 'x') 1.001 2)))
  =/  value  (need (parse:stead-codec metadata))
  ?>  ?=([%o *] value)
  =/  wrong  (canonical:stead-codec [%o (~(put by p.value) 'purpose' [%s 'owner-session'])])
  ?>  (rejected |.((receive configured ~zod ~bus wrong 1.001 2)))
  ~
++  test-identity-native-expiry
  ^-  tang
  ?>  (rejected |.((receive configured ~zod ~bus metadata 121.000 2)))
  ?>  (rejected |.((receive configured ~zod ~bus metadata 999 2)))
  ?>  (rejected |.((approve received approval 121.000)))
  ?>  =(0 (lent ~(tap by requests:(prune received 121.000))))
  ~
++  test-identity-owner-display
  ^-  tang
  =/  value  (need (parse-result:stead-codec (list-requests received 1.002)))
  ?>  ?=([%o *] value)
  =/  rows  (~(got by p.value) 'requests')
  ?>  ?=([%o *] rows)
  =/  row  (~(got by p.rows) id)
  ?>  ?=([%o *] row)
  ?>  (keys:stead-codec p.row ~['comparison_code' 'origin' 'identity_ship' 'home' 'principal_id' 'binding_id' 'binding_revision' 'expires_at_ms' 'status' 'csrf'])
  ?>  =(principal (field:stead-codec p.row 'principal_id'))
  ?>  =(binding (field:stead-codec p.row 'binding_id'))
  ?>  =('121000' (field:stead-codec p.row 'expires_at_ms'))
  ~
++  test-identity-duplicate-bounds
  ^-  tang
  ?>  =(received (receive received ~zod ~bus metadata 1.002 99))
  =/  db  received
  =/  n=@ud  2
  |-
  ?:  =(n 6)  ~
  =/  next  (begin:stead-session *state:stead-session actor ~zod origin 1.000 n)
  =/  raw  (approval-message:stead-browser id.next (~(got by challenges.next.next) id.next))
  ?:  =(n 5)
    ?>  (rejected |.((receive db ~zod ~bus raw 1.001 n)))
    ~
  $(db (receive db ~zod ~bus raw 1.001 n), n +(n))
++  test-identity-single-use-approval
  ^-  tang
  =/  out  (approve received approval 1.002)
  =/  spent=state  next.out
  =/  replay  (mule |.((approve spent approval 1.003)))
  ?>  ?=(%| -.replay)
  ?>  =(metadata outgoing.out)
  ?>  =('sent' status:(~(got by requests.next.out) id))
  ?>  =('' nonce:(~(got by requests.next.out) id))
  ~
++  test-identity-code-origin-csrf
  ^-  tang
  =/  value  (need (parse:stead-codec approval))
  ?>  ?=([%o *] value)
  ?>  %+  levy  `(list @t)`~['csrf' 'comparison_code' 'origin']
      |=  field=@t
      =/  raw  (canonical:stead-codec [%o (~(put by p.value) field [%s 'wrong'])])
      (rejected |.((approve received raw 1.002)))
  ~
++  test-identity-acknowledgement
  ^-  tang
  ?>  =(received (acknowledge received id & 1.002))
  =/  sent  next:(approve received approval 1.002)
  =/  yes  (acknowledge sent id & 1.003)
  =/  no  (acknowledge sent id | 1.003)
  ?>  =('approved' status:(~(got by requests.yes) id))
  ?>  =('failed' status:(~(got by requests.no) id))
  ?>  =(yes (acknowledge yes id | 1.004))
  ?>  =(~ requests:(acknowledge sent id & 121.000))
  ~
++  test-identity-http-route-isolation
  ^-  tang
  =/  headers=(list [@t @t])  ~[['Host' 'bus.localhost:8444'] ['Origin' personal] ['Content-Type' 'application/json']]
  =/  request=inbound-request:eyre  [& & *address:eyre [%'POST' '/stead-identity/api/list' headers `[2 '{}']]]
  =/  paths=(set @t)  (silt ~['/stead-identity/'])
  =/  posts=(set @t)  (silt ~['/stead-identity/api/list' '/stead-identity/api/approve'])
  ?>  ?=(^ (validate-routes:stead-http request personal paths posts))
  ?>  ?=(~ (validate-routes:stead-http request origin paths posts))
  ?>  ?=(~ (validate-routes:stead-http request(secure |) personal paths posts))
  ?>  ?=(~ (validate-routes:stead-http request(url.request '/stead/api/command') personal paths posts))
  ?>  ?=(~ (validate-routes:stead-http request(header-list.request [['Forwarded' 'proto=https'] headers]) personal paths posts))
  ~
++  test-identity-eyre-response-duct-binding
  ^-  tang
  =/  route=path  /http-response/123
  =/  key=duct  ~[/eyre/watch-response/123]
  =/  subscriptions=(map duct [ship=@p route=path])  (~(put by *(map duct [ship=@p route=path])) key [~bus route])
  ?>  (response-source:stead-eyre subscriptions ~bus ~.123)
  ?>  !(response-source:stead-eyre subscriptions ~nec ~.123)
  ?>  !(response-source:stead-eyre subscriptions ~bus ~.124)
  ?>  !(response-source:stead-eyre *(map duct [ship=@p route=path]) ~bus ~.123)
  =/  forged=(map duct [ship=@p route=path])  (~(put by *(map duct [ship=@p route=path])) ~[/gall/evil] [~bus route])
  ?>  !(response-source:stead-eyre forged ~bus ~.123)
  ?>  !(response-source:stead-eyre (~(put by subscriptions) ~[/gall/evil] [~bus route]) ~bus ~.123)
  ~
--

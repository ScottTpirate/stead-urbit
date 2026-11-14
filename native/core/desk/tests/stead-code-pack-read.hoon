/+  *test, stead-codec, stead-code-home, stead-code-http, stead-code-pack-anchor, stead-code-credentials, stead-http, stead-session, stead-team, stead-team-config, stead-core
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  other=@t  '019939ba-4000-7000-8000-000000000005'
=/  request-id=@t  '019939ba-4000-7000-8000-000000000004'
=/  who=actor:stead-session
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
=/  origin=@t  'https://home.localhost:8443'
=/  config=config:stead-team-config
  :*  1  ~zod  origin  project  other  'local-disposable'  'isolated-fake'
      (malt ~[[~bus [who 'Test member']]])  ~
  ==
=/  registry=registry:stead-team-config  [[~ config] ~ ~]
=/  project-row=project-state:stead-core  [1 1 1 ~]
=/  grant=grant-state:stead-core  [project principal.who 'reader' 2.000.000 |]
=/  core=state:stead-core  *state:stead-core
=.  core  core(initialized &, projects (malt ~[[project project-row] [other project-row]]), grants (malt ~[[request-id grant]]))
=/  team=state:stead-team  [registry core ~ ~ ~ ~]
=/  destination=scope:stead-code-credentials  [~zod project project 1]
=/  expected=@t  'd0644338c8d3e787eefe9b23c7ee213d2cc8e451ec64b993b184afc1f2a0208a'
=/  pack=manifest:stead-code-pack-anchor
  :*  destination  expected  '726566732f68656164732f31'
      %-  malt
      :-  ['726566732f746167732f76' 'dddddddddddddddddddddddddddddddddddddddd']
      %+  turn  (gulf 1 17)
      |=  number=@ud
      [(bytes-hex:stead-codec (cat 3 'refs/heads/' (decimal:stead-codec number))) 'cccccccccccccccccccccccccccccccccccccccc']
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'  400
      7.000  700.000  'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
  ==
=/  staged  (stage:stead-code-pack-anchor ~ pack ~zod 1)
?>  ?=(%& -.staged)
=/  accepted  (accept:stead-code-pack-anchor next.p.staged destination who 3 2 expected request-id |)
?>  ?=(%& -.accepted)
=/  code=state:stead-code-home  *state:stead-code-home
=.  code  code(packs next.p.accepted)
=/  cookie=@t  (token:stead-session 11 1 'test')
=/  csrf=@t  (token:stead-session 11 2 'test')
=/  sess=session:stead-session
  [who ~zod origin cookie (digest:stead-session 'stead.csrf/1' csrf) cookie 1.000.000]
=/  auth=state:stead-session  [0 ~ (malt ~[[(digest:stead-session 'stead.session/1' cookie) sess]])]
=/  unfenced=$-(@t ?)  |=(id=@t |)
=/  manage-call
  |=  [app=state:stead-code-home action=@t field-name=@t value=@t]
  =/  body
    (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.code/1'] ['action' action] ['project_id' project] [field-name value]]))
  (manage:stead-code-home team app auth ['/stead/api/code' body cookie '' csrf] 10 12 unfenced)
=/  issued  (manage-call code 'issue' 'access' 'read')
=/  payload
  |=  out=result:stead-code-home
  =/  parsed  (need (parse-result:stead-codec data.body.out))
  ?>  ?=([%o *] parsed)
  p.parsed
=/  secret  (field:stead-codec (payload issued) 'bearer')
=/  handle  (field:stead-codec (payload issued) 'handle')
=/  path=@t  (rap 3 ~['/stead/git/' project '.git/stead-snapshot'])
=/  headers=(list [@t @t])
  ~[['Host' 'home.localhost:8443'] ['Authorization' (cat 3 'Basic ' (en:base64:mimes:html [70 (cat 3 'stead:' secret)]))]]
=/  packet=inbound-request:eyre  [| & *address:eyre [%'GET' path headers ~]]
|%
++  test-pack-read-authenticated-exact-metadata
  ^-  tang
  ?>  =(200 status.issued)
  ?>  (token-valid:stead-session secret)
  =/  parsed  (need (validate:stead-code-http packet origin))
  ?>  =([project [%pack-read ~] secret [0 0]] parsed)
  =/  out  (serve:stead-code-home team next.issued parsed 11 '')
  ?>  =(200 status.out)
  ?>  =(next.issued next.out)
  =/  facts  (payload out)
  ?>  (keys:stead-codec facts ~['protocol' 'home' 'project_id' 'repository_id' 'authority_epoch' 'snapshot' 'head' 'refs' 'pack_sha256' 'pack_bytes' 'object_count' 'object_bytes' 'object_ids_sha256' 'principal_id' 'binding_id' 'binding_revision' 'identity_ship'])
  ?>  =('stead.code-pack-read/1' (field:stead-codec facts 'protocol'))
  ?>  =(expected (field:stead-codec facts 'snapshot'))
  ?>  =(principal.who (field:stead-codec facts 'principal_id'))
  ?>  =(binding.who (field:stead-codec facts 'binding_id'))
  ?>  =((canonical:stead-codec (object:stead-codec ~(tap by refs.pack))) (field:stead-codec facts 'refs'))
  ~
++  test-pack-read-https-get-without-browser-headers-or-body
  ^-  tang
  ?>  ?=(~ (validate:stead-code-http packet(method.request %'POST') origin))
  ?>  ?=(~ (validate:stead-code-http packet(secure |) origin))
  ?>  ?=(~ (validate:stead-code-http packet(body.request `[0 0]) origin))
  ?>  ?=(~ (validate:stead-code-http packet(url.request (cat 3 path '?x')) origin))
  ?>  ?=(~ (validate:stead-code-http packet(header-list.request ~[['Host' 'wrong.localhost']]) origin))
  ?>  %+  levy  `(list @t)`~['Cookie' 'X-Stead-CSRF' 'Origin' 'Content-Type' 'Forwarded' 'Authorization']
  |=(key=@t ?=(~ (validate:stead-code-http packet(header-list.request [[key ''] headers]) origin)))
  ~
++  test-pack-read-refuses-staged-cross-scope-expired-and-write
  ^-  tang
  ?>  =(404 status:(manage-call code 'issue' 'access' 'write'))
  ?>  =(404 status:(manage-call code(packs next.p.staged) 'issue' 'access' 'read'))
  =/  app  next.issued
  =/  denied  (read-pack:stead-code-home team app project '' 11)
  ?>  =(401 status.denied)
  ?>  =(denied (read-pack:stead-code-home team app other secret 11))
  ?>  =(body.denied body:(read-pack:stead-code-home team app(packs next.p.staged) project secret 11))
  ?>  =(denied (read-pack:stead-code-home team app project secret 900.010))
  ?>  =(denied (read-pack:stead-code-home team app project handle 11))
  ?>  =(401 status:(serve:stead-code-home team app [project [%advertise %git-receive-pack] secret [0 0]] 11 ''))
  ~
++  test-pack-read-current-grants-bindings-and-revocation
  ^-  tang
  =/  app  next.issued
  =/  revoked  (manage-call app 'revoke' 'handle' handle)
  ?>  =(200 status.revoked)
  ?>  =(401 status:(read-pack:stead-code-home team next.revoked project secret 11))
  ?>  =(401 status:(read-pack:stead-code-home team(data core(grants ~)) app project secret 11))
  =/  changed  config(members (malt ~[[~bus [who(revision 2) 'Test member']]]))
  ?>  =(401 status:(read-pack:stead-code-home team(registry registry(current [~ changed])) app project secret 11))
  =/  stale  core(projects (malt ~[[project project-row(epoch 2)]]))
  ?>  =(401 status:(read-pack:stead-code-home team(data stale) app project secret 11))
  ~
++  test-pack-read-selected-pointer-matches-browser-and-git
  ^-  tang
  =/  advanced  pack(refs (~(put by refs.pack) head.pack 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'))
  =/  raw  (snapshot-bytes:stead-code-pack-anchor advanced)
  =/  size  (met 3 raw)
  =.  advanced  advanced(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
  =/  changed=pack-selection:stead-code-home  [advanced other 5 1]
  =/  select=$-(@t (unit pack-selection:stead-code-home))
    |=(id=@t ?:(=(id project) [~ changed] ~))
  =/  app  next.issued
  =/  body  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.code/1'] ['action' 'pack-view'] ['project_id' project]]))
  =/  browser  (manage-selected:stead-code-home team app auth ['/stead/api/code' body cookie '' csrf] 11 12 unfenced select)
  =/  wire  (read-selected:stead-code-home team app project secret 11 [~ changed])
  ?>  &(=(200 status.browser) =(200 status.wire))
  ?>  =(snapshot.advanced (field:stead-codec (payload browser) 'snapshot'))
  ?>  =(snapshot.advanced (field:stead-codec (payload wire) 'snapshot'))
  ?>  =(other (field:stead-codec (payload browser) 'request_id'))
  ?>  =('1' (field:stead-codec (payload browser) 'generation'))
  ?>  =(epoch.destination (uint:stead-codec (field:stead-codec (payload wire) 'authority_epoch')))
  =/  mismatched  advanced(destination destination(epoch 2))
  ?>  =(401 status:(read-selected:stead-code-home team app project secret 11 [~ mismatched other 5 1]))
  ~
--

::  Individual identity Gall driver; only its owner app calls this state.
/+  stead-codec, stead-team, stead-session, stead-http, stead-browser, stead-identity-core, stead-eyre, stead-assets, server
|%
+$  state  [db=state:stead-identity-core files=cache:stead-assets incarnation=@t]
+$  saved  [%stead-identity %1 config=(unit configuration:stead-identity-core) counter=@ud]
++  now-ms
  |=  now=@da
  (div (mul 1.000 (sub now ~1970.1.1)) ~s1)
++  driver
  |=  owner=state
  =*  db  db.owner
  =*  files  files.owner
  =*  incarnation  incarnation.owner
  |_  =bowl:gall
  ++  kicks
    ^-  (list card:agent:gall)
    =/  paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p route=path]] route)))
    (turn ~(tap in paths) |=(route=path [%give %kick [route ~] ~]))
  ++  bind
    ^-  card:agent:gall
    [%pass /stead-identity-http %arvo %e %connect [~ /stead-identity] dap.bowl]
  ++  respond
    |=  [id=@ta status=@ud mime=@t raw=@t]
    ^-  (list card:agent:gall)
    =/  headers  [['content-type' mime] security-headers:stead-http]
    (give-simple-payload:app:server id [[status headers] [~ [(met 3 raw) raw]]])
  ++  response
    |=  [id=@ta status=@ud raw=@t]
    ^-  (list card:agent:gall)
    (respond id status 'application/json' raw)
  ++  available
    ^-  ?
    &(?=(^ config.db) !=('' incarnation) !?=(~ files))
  ++  http
    |=  [id=@ta request=inbound-request:eyre]
    ^-  (quip card:agent:gall state)
    ?.  available
      [(response id 503 (error:stead-team 'unavailable')) owner]
    =/  config  (need config.db)
    =/  parsed  (validate-routes:stead-http request origin.config (paths:stead-assets '/stead-identity/') (silt ~['/stead-identity/api/list' '/stead-identity/api/approve']))
    ?~  parsed  [(response id 403 (error:stead-team 'invalid_http_request')) owner]
    ?:  =(%'GET' method.request.request)
      =/  entry  (~(get by files) route.u.parsed)
      ?~  entry  [(respond id 404 'text/plain' 'Not found') owner]
      [(respond id 200 mime.u.entry bytes.u.entry) owner]
    ?.  &(authenticated.request =(src.bowl our.bowl) =(sap.bowl /eyre))
      [(response id 401 (error:stead-team 'owner_required')) owner]
    ?:  =('/stead-identity/api/list' route.u.parsed)
      =/  input  (small:stead-browser body.u.parsed ~['protocol'] 'stead.identity/1')
      =/  next  (prune:stead-identity-core db (now-ms now.bowl))
      [(response id 200 (list-requests:stead-identity-core next (now-ms now.bowl))) owner(db next)]
    =/  out  (approve:stead-identity-core db body.u.parsed (now-ms now.bowl))
    =/  raw  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.identity/1'] ['status' 'sent'] ['challenge_id' id.out]]))
    =/  card=card:agent:gall
      [%pass [%stead-owner-approval incarnation (scot %p home.config) id.out ~] %agent [home.config %stead-home] %poke %stead-auth-approval-1 !>(outgoing.out)]
    [(weld (response id 200 raw) [card ~]) owner(db next.out)]
  ++  init
    [[bind ~] owner]
  ++  save
    !>([%stead-identity %1 config.db counter.db])
  ++  load
    |=  old=vase
    =/  loaded  !<(saved old)
    ?>  (lte counter.loaded 18.446.744.073.709.551.615)
    =/  config  config.loaded
    ?^  config
      ?>  (valid-configuration:stead-identity-core u.config our.bowl)
      [(weld kicks [bind ~]) owner(db [config ~ counter.loaded], files ~, incarnation '')]
    [(weld kicks [bind ~]) owner(db [~ ~ counter.loaded], files ~, incarnation '')]
  ++  poke
    |=  [=mark =vase]
    ^-  (quip card:agent:gall state)
    ?:  =(%stead-identity-config-1 mark)
      ?>  =(src.bowl our.bowl)
      =/  next  (configure:stead-identity-core db !<(@t vase) our.bowl)
      [(weld kicks [bind ~]) owner(db next, files ~, incarnation '')]
    ?:  =(%stead-bootstrap-1 mark)
      ?>  &(=(src.bowl our.bowl) ?=(^ config.db))
      =/  value  (small:stead-browser !<(@t vase) ~['protocol' 'nonce'] 'stead.bootstrap/1')
      =/  nonce  (field:stead-codec value 'nonce')
      ?>  (token-valid:stead-session nonce)
      =/  route=path  [%bootstrap nonce ~]
      ?>  (lien ~(tap by sup.bowl) |=([duct [ship=@p path=path]] &(=(ship our.bowl) =(path route))))
      =/  loaded  (load:stead-assets byk.bowl '/stead-identity/')
      =/  incarnation  (token:stead-session eny.bowl act.bowl 'stead.identity-incarnation/1')
      =/  raw  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.bootstrap/1'] ['status' 'ready'] ['home' (scot %p our.bowl)] ['nonce' nonce] ['incarnation' incarnation]]))
      =/  other-paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p path=path]] path)))
      =/  retired=(list card:agent:gall)
        (turn (skip ~(tap in other-paths) |=(old=path =(old route))) |=(old=path [%give %kick [old ~] ~]))
      =/  replies=(list card:agent:gall)
        ~[[%give %fact [route ~] %stead-result-3 !>(raw)] [%give %kick [route ~] ~]]
      [(weld retired replies) owner(db db(requests ~), files loaded, incarnation incarnation)]
    ?:  =(%handle-http-request mark)
      =/  [id=@ta request=inbound-request:eyre]  !<([@ta inbound-request:eyre] vase)
      ?>  (response-source:stead-eyre sup.bowl src.bowl id)
      =/  out  (mule |.((http id request)))
      ?:  ?=(%| -.out)
        [(response id 400 (error:stead-team 'invalid_request')) owner]
      p.out
    ?>  &(!=('' incarnation) !?=(~ files))
    ?>  =(%stead-auth-challenge-1 mark)
    `owner(db (receive:stead-identity-core db src.bowl our.bowl !<(@t vase) (now-ms now.bowl) eny.bowl))
  ++  watch
    |=  route=path
    ?>  &((lte (lent route) 2) (levy route |=(part=@t (lte (met 3 part) 128))) (lte (lent ~(tap by sup.bowl)) 128))
    ?:  ?=([%http-response @ ~] route)
      ?>  (response-source:stead-eyre sup.bowl src.bowl i.t.route)
      `owner
    ?>  &(?=([%bootstrap @ ~] route) =(src.bowl our.bowl) (token-valid:stead-session i.t.route))
    `owner
  ++  agent
    |=  [=wire =sign:agent:gall]
    ?.  &(?=([%stead-owner-approval @ @ @ ~] wire) ?=(^ config.db) !=('' incarnation))  `owner
    ?.  &(=(i.t.wire incarnation) =(i.t.t.wire (scot %p home.u.config.db)) =(src.bowl home.u.config.db) ?=(%poke-ack -.sign))  `owner
    `owner(db (acknowledge:stead-identity-core db i.t.t.t.wire ?=(~ p.sign) (now-ms now.bowl)))
  ++  arvo
    |=  [=wire =sign-arvo]
    ?>  &(?=([%eyre %bound *] sign-arvo) accepted.sign-arvo)
    `owner
  --
--

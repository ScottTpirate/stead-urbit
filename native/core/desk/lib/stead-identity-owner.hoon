::  Individual identity Gall driver; only its owner app calls this state.
/+  stead-codec, stead-team, stead-session, stead-http, stead-browser, stead-identity-core, stead-eyre, stead-assets, server
|%
+$  state  [db=state:stead-identity-core files=cache:stead-assets incarnation=@t]
+$  previous  [%stead-identity %1 config=(unit configuration:stead-identity-core) counter=@ud]
+$  saved  [%stead-identity %2 config=(unit configuration:stead-identity-core) counter=@ud trusted=homes:stead-identity-core verifier=@t]
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
  ++  deliver
    |=  [id=@ta out=approval:stead-identity-core reply=@t]
    ^-  (quip card:agent:gall state)
    =/  card=card:agent:gall
      [%pass [%stead-owner-approval incarnation (scot %p home.out) id.out ~] %agent [home.out %stead-home] %poke %stead-auth-approval-1 !>(outgoing.out)]
    [(weld (response id 200 reply) [card ~]) owner(db next.out)]
  ++  verifier-call
    |=  [id=@ta raw=@t now=@ud]
    ^-  (quip card:agent:gall state)
    =/  input  (small:stead-browser raw ~['protocol' 'secret' 'action' 'challenge_id' 'ticket'] 'stead.passkey-bridge/1')
    =/  secret  (field:stead-codec input 'secret')
    ?>  &((token-valid:stead-session secret) =(verifier.db (digest:stead-session 'stead.verifier/1' secret)))
    =/  action  (field:stead-codec input 'action')
    =/  key  (field:stead-codec input 'challenge_id')
    =/  ticket  (field:stead-codec input 'ticket')
    ?:  =('owner' action)
      =/  next  (consume-ticket:stead-identity-core db key ticket now)
      =/  reply  (canonical:stead-codec (object:stead-codec ~[['status' 'ok'] ['planet' (scot %p our.bowl)]]))
      [(response id 200 reply) owner(db next)]
    ?>  &(=('' ticket) (token-valid:stead-session key))
    =/  row  (~(got by requests.db) key)
    ?>  &(direct.row (gth expires.row now) =('pending' status.row) =([~ origin.row] (~(get by trusted.db) home.row)))
    =/  reply  (canonical:stead-codec (object:stead-codec ~[['status' 'ok'] ['planet' (scot %p our.bowl)] ['home' (scot %p home.row)] ['origin' origin.row] ['challenge_id' key]]))
    ?:  =('context' action)  [(response id 200 reply) owner]
    ?>  =('approve' action)
    =/  out  (send-approval:stead-identity-core db key now eny.bowl)
    =/  result  (need (parse:stead-codec reply))
    ?>  ?=([%o *] result)
    =/  completed  (canonical:stead-codec [%o (~(put by p.result) 'return_proof' [%s proof.out])])
    (deliver id out completed)
  ++  http
    |=  [id=@ta request=inbound-request:eyre]
    ^-  (quip card:agent:gall state)
    ?.  available
      [(response id 503 (error:stead-team 'unavailable')) owner]
    =/  config  (need config.db)
    =/  parsed  (validate-routes:stead-http request origin.config (paths:stead-assets '/stead-identity/') (silt ~['/stead-identity/api/list' '/stead-identity/api/approve' '/stead-identity/api/challenge' '/stead-identity/api/ticket' '/stead-identity/api/verifier']))
    ?~  parsed  [(response id 403 (error:stead-team 'invalid_http_request')) owner]
    ?:  =(%'GET' method.request.request)
      =/  entry  (~(get by files) route.u.parsed)
      ?~  entry  [(respond id 404 'text/plain' 'Not found') owner]
      [(respond id 200 mime.u.entry bytes.u.entry) owner]
    =/  now  (now-ms now.bowl)
    ?:  =('/stead-identity/api/verifier' route.u.parsed)
      (verifier-call id body.u.parsed now)
    ?:  =('/stead-identity/api/challenge' route.u.parsed)
      =/  input  (small:stead-browser body.u.parsed ~['protocol' 'challenge_id'] 'stead.identity/1')
      =/  key  (field:stead-codec input 'challenge_id')
      ?>  (token-valid:stead-session key)
      =/  row  (~(got by requests.db) key)
      ?>  (gth expires.row now)
      =/  enabled  &(direct.row !=('' verifier.db) =([~ origin.row] (~(get by trusted.db) home.row)))
      =/  reply  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.identity/1'] ['status' status.row] ['challenge_id' key] ['home' (scot %p home.row)] ['origin' origin.row] ['identity_ship' (scot %p our.bowl)] ['passkeys' ?:(enabled 'yes' 'no')]]))
      [(response id 200 reply) owner]
    ?.  &(authenticated.request =(src.bowl our.bowl) =(sap.bowl /eyre))
      [(response id 401 (error:stead-team 'owner_required')) owner]
    ?:  =('/stead-identity/api/list' route.u.parsed)
      =/  value  (need (parse:stead-codec body.u.parsed))
      ?>  ?=([%o *] value)
      ?>  (keys:stead-codec p.value ~['protocol'])
      =/  protocol  (field:stead-codec p.value 'protocol')
      ?>  ?|(=('stead.identity/1' protocol) =('stead.identity/2' protocol))
      =/  next  (prune:stead-identity-core db now)
      [(response id 200 (render-requests:stead-identity-core next now =('stead.identity/2' protocol))) owner(db next)]
    ?:  =('/stead-identity/api/ticket' route.u.parsed)
      =/  input  (small:stead-browser body.u.parsed ~['protocol' 'action'] 'stead.passkey-ticket/1')
      =/  out  (owner-ticket:stead-identity-core db (field:stead-codec input 'action') now eny.bowl)
      =/  raw  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.passkey-ticket/1'] ['status' 'ok'] ['ticket' value.out]]))
      [(response id 200 raw) owner(db next.out)]
    =/  out  (approve:stead-identity-core db body.u.parsed now eny.bowl)
    =/  raw  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.identity/1'] ['status' 'sent'] ['challenge_id' id.out]]))
    ?:  =('' proof.out)  (deliver id out raw)
    =/  result  (need (parse:stead-codec raw))
    ?>  ?=([%o *] result)
    (deliver id out (canonical:stead-codec [%o (~(put by p.result) 'return_proof' [%s proof.out])]))
  ++  init
    [[bind ~] owner]
  ++  save
    !>([%stead-identity %2 config.db counter.db trusted.db verifier.db])
  ++  load
    |=  old=vase
    =/  loaded=saved
      ?:  ?=([%stead-identity %1 *] q.old)
        =/  before  !<(previous old)
        [%stead-identity %2 config.before counter.before (seed:stead-identity-core config.before) '']
      !<(saved old)
    ?>  (lte counter.loaded 18.446.744.073.709.551.615)
    =/  config  config.loaded
    ?>  ?~(config & (valid-configuration:stead-identity-core u.config our.bowl))
    =/  initial  (seed:stead-identity-core config)
    =/  fresh=state:stead-identity-core
      ?>  ?|(=('' verifier.loaded) (token-valid:stead-session verifier.loaded))
      ?>  (lte ~(wyt by trusted.loaded) 32)
      ?~  config
        ?>  &(?=(~ trusted.loaded) =('' verifier.loaded))
        [~ ~ counter.loaded ~ '' ~]
      ?>  (levy ~(tap by initial) |=([home=@p url=@t] =([~ url] (~(get by trusted.loaded) home))))
      ?>  %+  levy  ~(tap by trusted.loaded)
          |=  [home=@p url=@t]
          ?&  (lte (met 0 home) 128)
              (isolated:stead-identity-core url origin.u.config)
              (permitted-pair:stead-identity-core (~(del by trusted.loaded) home) home url)
          ==
      [config ~ counter.loaded trusted.loaded verifier.loaded ~]
    [(weld kicks [bind ~]) owner(db fresh, files ~, incarnation '')]
  ++  poke
    |=  [=mark =vase]
    ^-  (quip card:agent:gall state)
    ?:  =(%stead-identity-config-1 mark)
      ?>  =(src.bowl our.bowl)
      =/  next  (configure:stead-identity-core db !<(@t vase) our.bowl)
      [(weld kicks [bind ~]) owner(db next, files ~, incarnation '')]
    ?:  =(%stead-verifier-config-1 mark)
      ?>  &(=(src.bowl our.bowl) ?=(^ config.db))
      `owner(db (configure-verifier:stead-identity-core db !<(@t vase)))
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
      [(weld retired replies) owner(db db(requests ~, tickets ~), files loaded, incarnation incarnation)]
    ?:  =(%handle-http-request mark)
      =/  [id=@ta request=inbound-request:eyre]  !<([@ta inbound-request:eyre] vase)
      ?>  (response-source:stead-eyre sup.bowl src.bowl id)
      =/  out  (mule |.((http id request)))
      ?:  ?=(%| -.out)
        [(response id 400 (error:stead-team 'invalid_request')) owner]
      p.out
    ?>  &(!=('' incarnation) !?=(~ files))
    ?>  =(%stead-auth-challenge-1 mark)
    =/  raw  !<(@t vase)
    =/  next  (receive:stead-identity-core db src.bowl our.bowl raw (now-ms now.bowl) eny.bowl)
    =/  value  (need (parse:stead-codec raw))
    ?>  ?=([%o *] value)
    =/  key  (field:stead-codec p.value 'challenge_id')
    =/  address  (address-message:stead-identity-core next key our.bowl)
    =/  card=card:agent:gall
      [%pass [%stead-identity-address incarnation key ~] %agent [src.bowl %stead-home] %poke %stead-identity-address-1 !>(address)]
    [[card ~] owner(db next)]
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
    ?.  &(=(i.t.wire incarnation) =(i.t.t.wire (scot %p src.bowl)) ?=(%poke-ack -.sign))  `owner
    =/  row  (~(get by requests.db) i.t.t.t.wire)
    ?~  row  `owner
    ?.  =(src.bowl home.u.row)  `owner
    `owner(db (acknowledge:stead-identity-core db i.t.t.t.wire ?=(~ p.sign) (now-ms now.bowl)))
  ++  arvo
    |=  [=wire =sign-arvo]
    ?>  &(?=([%eyre %bound *] sign-arvo) accepted.sign-arvo)
    `owner
  --
--

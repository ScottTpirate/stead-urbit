::  Configured-team Gall driver. Only stead-home owns and calls this state.
/+  stead-codec, stead-core, stead-team, stead-team-config, stead-team-codec, stead-session, stead-http, stead-browser, stead-projection, stead-views, stead-restore, stead-eyre, stead-assets, server
=,  stead-codec
|%
+$  pending-entry  [actor=authentication:stead-team expires=@ud]
+$  state
  $:  db=state:stead-team  view=state:stead-projection
      transient=ephemeral:stead-browser  restoring=(unit job:stead-restore)
      job=@t  incarnation=@t  pending=(map path pending-entry)
      files=(map @t [mime=@t bytes=@t])
  ==
+$  saved  [db=state:stead-team projection=state:stead-projection]
++  empty
  ^-  state
  =/  view=state:stead-projection
    [*index:stead-projection *index:stead-projection ~ | |]
  [empty:stead-team view *ephemeral:stead-browser ~ '' '' ~ ~]
++  now-ms
  |=  now=@da
  (div (mul 1.000 (sub now ~1970.1.1)) ~s1)
++  driver
  |=  owner=state
  |_  bowl=bowl:gall
  ++  kicks
    ^-  (list card:agent:gall)
    =/  paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p route=path]] route)))
    (turn ~(tap in paths) |=(route=path [%give %kick [route ~] ~]))
  ++  bind
    ^-  card:agent:gall
    [%pass /stead-http %arvo %e %connect [~ /stead] dap.bowl]
  ++  wait
    ^-  card:agent:gall
    [%pass [%stead-rebuild job.owner ~] %arvo %b %wait (add now.bowl (div ~s1 100))]
  ++  save
    ^-  saved
    [?~(restoring.owner db.owner target.u.restoring.owner) view.owner]
  ++  load
    |=  old=saved
    ^-  (quip card:agent:gall state)
    ?>  ?=(^ current.registry.db.old)
    =/  staged  (begin:stead-restore db.old our.bowl)
    =/  job  (token:stead-session eny.bowl act.bowl 'stead.restore-job/1')
    =/  fresh=state
      [empty:stead-team *state:stead-projection *ephemeral:stead-browser [~ staged] job '' ~ ~]
    =.  owner  fresh
    [(weld kicks ~[bind wait]) owner]
  ++  configured
    |=  raw=@t
    ^-  (quip card:agent:gall state)
    ?.  =(src.bowl our.bowl)
      ~|  %stead-owner-required
      !!
    ?>  &(?=(~ restoring.owner) !rebuilding.view.owner)
    =/  next  (configure:stead-team db.owner raw our.bowl (now-ms now.bowl))
    =/  view  (begin:stead-projection next view.owner)
    =/  job  (token:stead-session eny.bowl act.bowl 'stead.projection-job/1')
    =.  owner  owner(db next, view view, transient *ephemeral:stead-browser, pending ~, incarnation '', job job, files ~)
    [(weld kicks ~[bind wait]) owner]
  ++  load-assets
    ^-  (map @t [mime=@t bytes=@t])
    (load:stead-assets byk.bowl '/stead/')
  ++  bootstrap
    |=  raw=@t
    ^-  (quip card:agent:gall state)
    ?>  =(src.bowl our.bowl)
    =/  value  (small:stead-browser raw ~['protocol' 'nonce'] 'stead.bootstrap/1')
    =/  nonce  (field value 'nonce')
    ?>  (token-valid:stead-session nonce)
    ?>  &(?=(~ restoring.owner) (ready:stead-projection db.owner view.owner))
    =/  route=path  [%bootstrap nonce ~]
    ?>  (lien ~(tap by sup.bowl) |=([duct [ship=@p path=path]] &(=(ship our.bowl) =(path route))))
    =/  files  load-assets
    =/  incarnation  (token:stead-session eny.bowl act.bowl 'stead.home-incarnation/1')
    =/  response  (canonical (object ~[['protocol' 'stead.bootstrap/1'] ['status' 'ready'] ['home' (scot %p our.bowl)] ['nonce' nonce] ['incarnation' incarnation]]))
    ::  Invalidate first, then acknowledge this exact native owner-local exchange.
    =/  old-paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p path=path]] path)))
    =/  retired=(list card:agent:gall)
      (turn (skip ~(tap in old-paths) |=(old=path =(old route))) |=(old=path [%give %kick [old ~] ~]))
    =/  replies=(list card:agent:gall)
      ~[[%give %fact [route ~] %stead-result-3 !>(response)] [%give %kick [route ~] ~]]
    :_  owner(transient *ephemeral:stead-browser, pending ~, incarnation incarnation, files files)
    (weld retired replies)
  ++  available
    ^-  ?
    &(!=('' incarnation.owner) ?=(~ restoring.owner) (ready:stead-projection db.owner view.owner) !?=(~ files.owner))
  ++  response
    |=  [id=@ta status=@ud mime=@t bytes=@t cookies=(list @t)]
    ^-  (list card:agent:gall)
    =/  headers  (weld security-headers:stead-http [['content-type' mime] (turn cookies |=(text=@t ['set-cookie' text]))])
    (give-simple-payload:app:server id [[status headers] [~ [(met 3 bytes) bytes]]])
  ++  http
    |=  [id=@ta request=inbound-request:eyre]
    ^-  (quip card:agent:gall state)
    ?>  (response-source:stead-eyre sup.bowl src.bowl id)
    =/  out  (mule |.((http-body id request)))
    ?:  ?=(%| -.out)
      [(response id 400 'application/json' (error:stead-team 'invalid_request') ~) owner]
    p.out
  ++  http-body
    |=  [id=@ta request=inbound-request:eyre]
    ^-  (quip card:agent:gall state)
    ?.  available  [(response id 503 'application/json' (error:stead-team 'projection_unavailable') ~) owner]
    =/  config  (need current.registry.db.owner)
    =/  parsed  (validate:stead-http request origin.config (paths:stead-assets '/stead/'))
    ?~  parsed  [(response id 403 'application/json' (error:stead-team 'invalid_http_request') ~) owner]
    ?:  =(%'GET' method.request.request)
      =/  entry  (~(get by files.owner) route.u.parsed)
      ?~  entry  [(response id 404 'text/plain' 'Not found' ~) owner]
      [(response id 200 mime.u.entry bytes.u.entry ~) owner]
    =/  attempted  (mule |.((call:stead-browser db.owner view.owner transient.owner u.parsed (now-ms now.bowl) eny.bowl)))
    ?:  ?=(%| -.attempted)  [(response id 400 'application/json' (error:stead-team 'invalid_request') ~) owner]
    =/  out  p.attempted
    =/  cards  (response id status.out 'application/json' bytes.out cookies.out)
    =?  cards  ?=(^ outgoing.out)
      =/  challenge=card:agent:gall
        [%pass [%stead-approval (decimal act.bowl) ~] %agent [ship.u.outgoing.out %stead-identity] %poke %stead-auth-challenge-1 !>(bytes.u.outgoing.out)]
      (weld cards [challenge ~])
    [cards owner(db db.out, view view.out, transient transient.out)]
  ++  poke
    |=  [mark=mark vase=vase]
    ^-  (quip card:agent:gall state)
    ?:  =(%stead-team-config-1 mark)  (configured !<(@t vase))
    ?:  =(%stead-bootstrap-1 mark)  (bootstrap !<(@t vase))
    ?:  =(%handle-http-request mark)  (http !<([@ta inbound-request:eyre] vase))
    ?>  available
    ?:  =(%stead-auth-approval-1 mark)
      [~ owner(transient (approve:stead-browser db.owner transient.owner src.bowl !<(@t vase) (now-ms now.bowl)))]
    ?>  ?|  =(%stead-command-3 mark)  =(%stead-query-3 mark)
        ==
    =/  actor  native-actor
    =/  raw  !<(@t vase)
    ?>  (lte (met 3 raw) 65.536)
    =/  value  (need (parse raw))
    ?>  ?=([%o *] value)
    =/  request  (field p.value 'request_id')
    ?>  (uuid request)
    =/  digest  (hash ?:(=(%stead-command-3 mark) 'stead.command/3' 'stead.query/3') (canonical value))
    =/  route=path  [%v3 %result (scot %p src.bowl) binding.identity.actor (decimal revision.identity.actor) request digest ~]
    =/  reserved  (need (~(get by pending.owner) route))
    ?>  &(=(actor actor.reserved) (gth expires.reserved (now-ms now.bowl)))
    =/  outcome
      ?:  =(%stead-command-3 mark)
        =/  cmd  (decode:stead-team-codec raw)
        =/  out  (apply-command:stead-team db.owner actor cmd (now-ms now.bowl))
        =/  view
          ?:  =(db.owner next.out)  view.owner
          ?>  ?=(^ journal.data.next.out)
          (append:stead-projection view.owner i.journal.data.next.out)
        [response.out owner(db next.out, view view)]
      =/  query  (decode-query:stead-team-codec raw)
      =/  out  (execute:stead-views db.owner view.owner pages.transient.owner actor query (now-ms now.bowl) eny.bowl)
      [response.out owner(transient transient.owner(pages next.out))]
    =/  body=@t  -.outcome
    =/  next=state  +.outcome
    :_  next(pending (~(del by pending.next) route))
    :~  [%give %fact [route ~] %stead-result-3 !>(body)]
        [%give %kick [route ~] ~]
    ==
  ++  watch
    |=  route=path
    ^-  (quip card:agent:gall state)
    ?>  &((lte (lent route) 8) (levy route |=(part=@t (lte (met 3 part) 128))))
    ?>  (lte (lent ~(tap by sup.bowl)) 128)
    ?:  ?=([%http-response @ ~] route)
      ?>  (response-source:stead-eyre sup.bowl src.bowl i.t.route)
      [~ owner]
    ?:  ?=([%bootstrap @ ~] route)
      ?>  &(=(src.bowl our.bowl) (token-valid:stead-session i.t.route))
      ?>  (lte (lent ~(tap by sup.bowl)) 128)
      [~ owner]
    ?>  &(available ?=([%v3 %result @ @ @ @ @ ~] route))
    =/  actor  native-actor
    ?>  &(=(i.t.t.route (scot %p src.bowl)) =(i.t.t.t.route binding.identity.actor))
    ?>  &(=(i.t.t.t.t.route (decimal revision.identity.actor)) (uuid i.t.t.t.t.t.route) (token-valid:stead-session i.t.t.t.t.t.t.route))
    =/  stale  (skim ~(tap by pending.owner) |=([key=path val=pending-entry] (lte expires.val (now-ms now.bowl))))
    =/  pending  (malt (skip ~(tap by pending.owner) |=([key=path val=pending-entry] (lte expires.val (now-ms now.bowl)))))
    =/  cards  (turn stale |=([key=path val=pending-entry] [%give %kick [key ~] ~]))
    ?:  (lien stale |=([key=path val=pending-entry] =(key route)))  [cards owner(pending pending)]
    ?>  !(~(has by pending) route)
    ?>  (lth (lent ~(tap by pending)) 64)
    ?>  (lth (lent (skim ~(tap by pending) |=([key=path val=pending-entry] =(actor actor.val)))) 4)
    [cards owner(pending (~(put by pending) route [actor (add (now-ms now.bowl) 60.000)]))]
  ++  native-actor
    ^-  authentication:stead-team
    =/  who  (native-context:stead-team db.owner src.bowl (now-ms now.bowl))
    ~|  %stead-current-member-required
    (need who)
  ++  leave
    |=  route=path
    ^-  (quip card:agent:gall state)
    =/  found  (~(get by pending.owner) route)
    ?~  found  [~ owner]
    ?.  =(src.bowl ship.identity.actor.u.found)  [~ owner]
    [~ owner(pending (~(del by pending.owner) route))]
  ++  arvo
    |=  [wire=wire sign=sign-arvo]
    ^-  (quip card:agent:gall state)
    ?:  ?=([%eyre %bound *] sign)
      ?>  accepted.sign
      [~ owner]
    ?.  &(?=([%stead-rebuild @ ~] wire) =(i.t.wire job.owner) ?=([%behn %wake ~] sign))
      [~ owner]
    ?^  restoring.owner
      =/  job  (step:stead-restore u.restoring.owner)
      ?:  =(%invalid status.job)  [~ owner(restoring [~ job], incarnation '')]
      ?:  =(%pending status.job)
        [[wait ~] owner(restoring [~ job])]
      =/  next  (need (result:stead-restore job))
      [[wait ~] owner(db next, restoring ~, view (begin:stead-projection next *state:stead-projection))]
    ?:  rebuilding.view.owner
      =/  view  (batch:stead-projection db.owner view.owner)
      [?:(&(!poisoned.view rebuilding.view) [wait ~] ~) owner(view view)]
    [~ owner]
  --
--

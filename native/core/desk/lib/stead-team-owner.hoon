::  Configured-team Gall driver. Only stead-home owns and calls this state.
/+  stead-codec, stead-core, stead-team, stead-team-config, stead-team-codec, stead-session, stead-http, stead-browser, stead-projection, stead-views, stead-restore, stead-eyre, stead-assets, server, stead-updates, stead-update-codec, stead-code-home, stead-code-http, stead-code-credentials, stead-project-retirement, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-owner, stead-code-pack-control, stead-code-receive, stead-code-pack-relay, stead-code-pack-relay-pin, stead-code-pack-relay-http, stead-code-pack-relay-wire, stead-code-pack-review, stead-code-pack-review-board, stead-code-pack-review-api, stead-code-pack-review-proof, stead-code-pack-promotion, stead-code-pack-proof, stead-product-home, stead-product-browser, stead-product-history, stead-product-codec, stead-product-owner-codec
=,  stead-codec
|%
+$  pending-entry  [actor=authentication:stead-team expires=@ud]
+$  git-reply  [id=@ta sender=@p bearer=@t nonce=@t]
+$  external-writes  (map @t ledger:stead-code-pack-ledger)
+$  external-writes-v1  (map @t ledger-v1:stead-code-pack-ledger)
+$  pack-boards  (map @t state:stead-code-pack-review-board)
+$  state
  $:  db=state:stead-team  view=state:stead-projection
      transient=ephemeral:stead-browser  restoring=(unit job:stead-restore)
      job=@t  incarnation=@t  pending=(map path pending-entry)
      files=(map @t [mime=@t bytes=@t])
      code=state:stead-code-home  git-waiting=(map @t git-reply)
      retired=ledger:stead-project-retirement
      external=external-writes  relay=state:stead-code-pack-relay-pin  pack-reviews=pack-boards
      product=(unit stage:stead-product-home)
  ==
+$  saved  [db=state:stead-team projection=state:stead-projection]
++  empty
  ^-  state
  =/  view=state:stead-projection
    [*index:stead-projection *index:stead-projection ~ | |]
  [empty:stead-team view *ephemeral:stead-browser ~ '' '' ~ ~ *state:stead-code-home ~ ~ ~ [%closed 0 ~] ~ ~]
++  now-ms
  |=  now=@da
  (div (mul 1.000 (sub now ~1970.1.1)) ~s1)
++  frozen-journal-page
  |=  [home=@p owner=state raw=@t offset=@t]
  ^-  @t
  =/  intent  (decode:stead-project-retirement raw)
  =/  retired  (~(got by retired.owner) project.intent)
  ?>  =(request.retired intent)
  =/  data  data.db.owner
  ?>  (current:stead-project-retirement data intent)
  =/  start  (uint offset)
  =/  stream-limit  journal-max-stream-bytes:stead-project-retirement
  ?>  (lth start stream-limit)
  =/  rows
    (flop (skim journal.data |=([project=@t bytes=@t digest=@t] =(project project.intent))))
  =/  count  (lent rows)
  ?>  &((gth count 0) (lte count journal-max-rows:stead-project-retirement))
  =/  [done=? body=@]
    =/  skip=@ud  start
    =/  room=@ud  (min 32.768 (sub stream-limit start))
    =/  chunks=(list [@ud @])  ~
    |-
    ^-  [done=? body=@]
    ?~  rows
      ?>  =(0 skip)
      [%.y (can 3 (flop chunks))]
    ?:  =(0 room)  [%.n (can 3 (flop chunks))]
    =/  width  +((met 3 bytes.i.rows))
    ?:  (gte skip width)  $(rows t.rows, skip (sub skip width))
    =/  remaining  (sub width skip)
    =/  taking  (min room remaining)
    =/  piece  (cut 3 [skip taking] (cat 3 bytes.i.rows 10))
    =.  chunks  [[taking piece] chunks]
    ?:  (lth taking remaining)  [%.n (can 3 (flop chunks))]
    $(rows t.rows, skip 0, room (sub room taking))
  ?>  (gth (met 3 body) 0)
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.project-journal-page/1']
      ['home' (scot %p home)]
      ['project_id' project.intent]
      ['migration_id' migration.intent]
      ['authority_epoch' (decimal epoch.intent)]
      ['destination_home' (scot %p destination.intent)]
      ['journal_head' journal-head.intent]
      ['journal_count' (decimal count)]
      ['offset' offset]
      ['done' ?:(done 'yes' 'no')]
      ['data_base64' (en:base64:mimes:html [(met 3 body) body])]
  ==
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
  ++  product-pair
    ^-  pair:stead-product-home
    [db.owner (need product.owner)]
  ++  save-product
    ^-  target:stead-product-home
    (snapshot:stead-product-home product-pair)
  ++  product-ready
    ^-  ?
    ?~(product.owner & (ready:stead-product-home u.product.owner))
  ++  no-code
    ^-  ?
    ?&  ?=(~ repos.code.owner)  ?=(~ uploads.code.owner)
        ?=(~ reviews.code.owner)  ?=(~ builds.code.owner)
        ?=(~ packs.code.owner)  ?=(~ retired.owner)
        ?=(~ external.owner)  ?=(~ pack-reviews.owner)
    ==
  ++  fake-ship
    ^-  ?
    .^(? %j /(scot %p our.bowl)/fake/(scot %da now.bowl))
  ++  runtime-matches
    |=  config=config:stead-team-config
    ^-  ?
    =(fake-ship =('isolated-fake' runtime.config))
  ++  load
    |=  [old=saved code=persisted:stead-code-home]
    ^-  (quip card:agent:gall state)
    ?>  ?=(^ current.registry.db.old)
    ?>  (validate-persisted:stead-code-home db.old code)
    =/  staged  (begin:stead-restore db.old our.bowl)
    =/  job  (token:stead-session eny.bowl act.bowl 'stead.restore-job/1')
    =/  fresh=state
      [empty:stead-team *state:stead-projection *ephemeral:stead-browser [~ staged] job '' ~ ~ [repos.code *ledger:stead-code-credentials uploads.code reviews.code builds.code ~] ~ ~ ~ [%closed 0 ~] ~ ~]
    =.  owner  fresh
    [(weld kicks ~[bind wait]) owner]
  ++  load-v7
    |=  [old=saved code=persisted:stead-code-home packs=state:stead-code-pack-anchor]
    ^-  (quip card:agent:gall state)
    ?>  (validate-packs:stead-code-home db.old repos.code packs)
    =/  [cards=(list card:agent:gall) next=state]  (load old code)
    [cards next(code code.next(packs packs))]
  ++  load-v8
    |=  [old=saved code=persisted:stead-code-home packs=state:stead-code-pack-anchor external=external-writes-v1]
    ^-  (quip card:agent:gall state)
    (load-v9 old code packs (~(run by external) from-v1:stead-code-pack-ledger) ~)
  ++  load-v9
    |=  [old=saved code=persisted:stead-code-home packs=state:stead-code-pack-anchor external=external-writes boards=pack-boards]
    ^-  (quip card:agent:gall state)
    =/  count  ~(wyt by external)
    ?>  &(|((gth count 0) ?=(^ boards)) (lte count 4) (lte ~(wyt by boards) 4))
    ?>  %+  levy  ~(tap by external)
        |=  [id=@t row=ledger:stead-code-pack-ledger]
        =/  genesis  (~(get by packs) id)
        ?~  genesis  |
        ?.  (valid:stead-code-pack-ledger row u.genesis)  |
        ?~  promotions.row  &
        =/  board  (~(get by boards) id)
        ?~  board  |
        =(promotions.row promotions.u.board)
    ?>  %+  levy  ~(tap by boards)
        |=  [id=@t row=state:stead-code-pack-review-board]
        =/  genesis  (~(get by packs) id)
        ?.  ?=([~ %accepted *] genesis)  |
        ?.  =(destination.row destination.pack.row.u.genesis)  |
        ?.  (valid:stead-code-pack-review-board row)  |
        ?.  (gth ~(wyt by requests.row) 0)  |
        =/  ledger  (~(get by external) id)
        =(promotions.row ?~(ledger ~ promotions.u.ledger))
    =/  [cards=(list card:agent:gall) next=state]  (load-v7 old code packs)
    [cards next(external external, pack-reviews boards)]
  ++  load-product
    |=  source=target:stead-product-home
    ^-  (quip card:agent:gall state)
    ?>  fake-ship
    =/  db  ?:(?=(%predecessor -.source) db.source db.value.source)
    =/  config  (need current.registry.db)
    ?>  &(=('isolated-fake' runtime.config) =('local-disposable' custody.config))
    =/  started  (begin:stead-product-home source our.bowl)
    =/  token  (token:stead-session eny.bowl act.bowl 'stead.product-restore-job/1')
    =.  owner  empty(product (some phase.started), job token)
    [(weld kicks ~[bind wait]) owner]
  ++  activate-product
    |=  raw=@t
    ^-  (quip card:agent:gall state)
    ?>  &(=(src.bowl our.bowl) ?=(~ product.owner) ?=(~ restoring.owner) (ready:stead-projection db.owner view.owner) no-code fake-ship)
    =/  config  (need current.registry.db.owner)
    ?>  &(=('isolated-fake' runtime.config) =('local-disposable' custody.config))
    =/  input  (small:stead-browser raw ~['protocol' 'profile' 'expected_config_revision' 'predecessor_sha256'] 'stead.product-activate/1')
    ?>  &(=(profile:stead-product-home (field input 'profile')) =(revision.config (uint (field input 'expected_config_revision'))))
    ?>  =((hash 'stead.product-predecessor/1' (bytes-hex (jam db.owner))) (field input 'predecessor_sha256'))
    (load-product [%predecessor db.owner])
  ++  configured
    |=  raw=@t
    ^-  (quip card:agent:gall state)
    ?.  =(src.bowl our.bowl)
      ~|  %stead-owner-required
      !!
    ?>  ?=(~ product.owner)
    ?>  &(?=(~ restoring.owner) !rebuilding.view.owner)
    =/  next  (configure:stead-team db.owner raw our.bowl (now-ms now.bowl))
    =/  config  (need current.registry.next)
    ::  A live label requires Jael's current ship state even before bootstrap.
    ::  Historical fixture configuration is also exercised as a pure transition.
    ~|  %stead-runtime-profile-mismatch
    ?>  ?|(=('isolated-fake' runtime.config) (runtime-matches config))
    =/  view  (begin:stead-projection next view.owner)
    =/  job  (token:stead-session eny.bowl act.bowl 'stead.projection-job/1')
    =.  owner  owner(db next, view view, transient *ephemeral:stead-browser, pending ~, incarnation '', job job, files ~, code code.owner(book *ledger:stead-code-credentials), git-waiting ~, relay (reset:stead-code-pack-relay-pin relay.owner))
    [(weld kicks ~[bind wait]) owner]
  ++  load-assets
    ^-  (map @t [mime=@t bytes=@t])
    (load:stead-assets byk.bowl '/stead/')
  ++  bootstrap
    |=  raw=@t
    ^-  (quip card:agent:gall state)
    ?>  =(src.bowl our.bowl)
    ?>  &(?=(~ restoring.owner) product-ready (ready:stead-projection db.owner view.owner))
    =/  config  (need current.registry.db.owner)
    ~|  %stead-runtime-profile-mismatch
    ?>  (runtime-matches config)
    =/  live-pilot  =('live-synthetic' runtime.config)
    =/  protocol  ?:(live-pilot 'stead.bootstrap/2' 'stead.bootstrap/1')
    =/  keys=(list @t)  ?:(live-pilot ~['protocol' 'nonce' 'expected_revision'] ~['protocol' 'nonce'])
    =/  value  (small:stead-browser raw keys protocol)
    ?>  ?|(!live-pilot =(revision.config (uint (field value 'expected_revision'))))
    =/  nonce  (field value 'nonce')
    ?>  (token-valid:stead-session nonce)
    =/  route=path  [%bootstrap nonce ~]
    ?>  (lien ~(tap by sup.bowl) |=([duct [ship=@p path=path]] &(=(ship our.bowl) =(path route))))
    =/  files  load-assets
    =/  incarnation  (token:stead-session eny.bowl act.bowl 'stead.home-incarnation/1')
    =/  fields=(list [@t @t])
      ~[['protocol' protocol] ['status' 'ready'] ['home' (scot %p our.bowl)] ['nonce' nonce] ['incarnation' incarnation]]
    =?  fields  live-pilot
      [['runtime' runtime.config] ['config_revision' (decimal revision.config)] fields]
    =/  response  (canonical (object fields))
    ::  Invalidate first, then acknowledge this exact native owner-local exchange.
    =/  old-paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p path=path]] path)))
    =/  retired=(list card:agent:gall)
      (turn (skip ~(tap in old-paths) |=(old=path =(old route))) |=(old=path [%give %kick [old ~] ~]))
    =/  replies=(list card:agent:gall)
      ~[[%give %fact [route ~] %stead-result-3 !>(response)] [%give %kick [route ~] ~]]
    :_  owner(transient *ephemeral:stead-browser, pending ~, incarnation incarnation, files files, code code.owner(book *ledger:stead-code-credentials), git-waiting ~, relay (reset:stead-code-pack-relay-pin relay.owner))
    (weld retired replies)
  ++  available
    ^-  ?
    &(!=('' incarnation.owner) ?=(~ restoring.owner) product-ready (ready:stead-projection db.owner view.owner) !?=(~ files.owner))
  ++  retired-project
    |=  project=@t
    (~(has by retired.owner) project)
  ++  pack-local-ready
    ^-  ?
    ?&  available
        ?=(~ product.owner)
        =('isolated-fake' runtime:(need current.registry.db.owner))
        fake-ship
    ==
  ++  pack-write-ready
    |=  project=@t
    ^-  ?
    =/  newest  (~(get by external.owner) project)
    ?:  &(?=(^ newest) (gte generation.u.newest max-advances:stead-code-pack-ledger))  |
    ?:  pack-local-ready  &
    =/  selected  (target:stead-code-home db.owner project)
    ?~  selected  |
    (matches:stead-code-pack-relay-pin relay.owner u.selected incarnation.owner)
  ++  pack-local
    |=  cmd=command:stead-code-pack-owner
    ^-  (quip card:agent:gall state)
    ?>  &(pack-local-ready =(src.bowl our.bowl))
    ?>  &((token-valid:stead-session nonce.cmd) (uuid project.cmd))
    =/  route=path  [%pack-local nonce.cmd ~]
    ?>  (lien ~(tap by sup.bowl) |=([duct [ship=@p path=path]] &(=(ship our.bowl) =(path route))))
    =/  scope  (target:stead-code-home db.owner project.cmd)
    =/  seed  (~(get by packs.code.owner) project.cmd)
    =/  now  (now-ms now.bowl)
    =/  answer
      ^-  response:stead-code-pack-owner
      ?:  (retired-project project.cmd)  (refused:stead-code-pack-owner %denied)
      ?:  ?=(%advertise -.task.cmd)
        =/  out  (pack-for:stead-code-home db.owner code.owner project.cmd bearer.cmd now (external-selection project.cmd) %write)
        ?:  !=(200 status.out)  (refused:stead-code-pack-owner %denied)
        [data.body.out ~]
      ?.  &(?=(^ scope) ?=(^ seed))  (refused:stead-code-pack-owner %denied)
      =/  gates=context:stead-code-pack-control
        :*  u.scope  now  incarnation.owner  available  |  (retired-project project.cmd)
            book.code.owner  (member:stead-code-home db.owner now)  (allowed:stead-code-home db.owner now)
            |=([action:stead-code-receive update:stead-code-pack-ledger] &)
            ~
            ::  Proof comes from the authenticated local fixture owner. Bind it
            ::  to the checked upload and candidate in addition to carrier checks.
            |=  [row=admission:stead-code-pack-ledger evidence=checked:stead-code-pack-ledger]
            ?&  (proof-matches:stead-code-pack-ledger claim.row evidence)
                (valid-manifest:stead-code-pack-anchor pack.evidence)
            ==
        ==
      (apply:stead-code-pack-owner (~(get by external.owner) project.cmd) u.seed gates cmd)
    =?  owner  ?=(^ changed.answer)
      owner(external (~(put by external.owner) project.cmd u.changed.answer))
    :_  owner
    :~  [%give %fact [route ~] %stead-result-3 !>(body.answer)]
        [%give %kick [route ~] ~]
    ==
  ++  inspect
    |=  nonce=@t
    ^-  (quip card:agent:gall state)
    ~|  %stead-owner-required
    ?>  &(=(src.bowl our.bowl) (token-valid:stead-session nonce))
    =/  config  (need current.registry.db.owner)
    =/  response
      %-  canonical
      %-  object
      :~  ['protocol' 'stead.operator-status/1']
          ['home' (scot %p our.bowl)]
          ['nonce' nonce]
          ['origin' origin.config]
          ['custody' custody.config]
          ['runtime' runtime.config]
          ['config_revision' (decimal revision.config)]
          ['runtime_matches' ?:((runtime-matches config) 'yes' 'no')]
          ['projection_ready' ?:((ready:stead-projection db.owner view.owner) 'yes' 'no')]
          ['available' ?:(available 'yes' 'no')]
          ['incarnation' incarnation.owner]
      ==
    :_  owner
    :~  [%give %fact ~ %stead-result-3 !>(response)]
        [%give %kick ~ ~]
    ==
  ++  inspect-relay
    ^-  (quip card:agent:gall state)
    ?>  =(src.bowl our.bowl)
    =/  status  ?:(?=(%open -.relay.owner) 'open' 'closed')
    =/  raw
      %-  canonical  %-  object
      ~[['protocol' 'stead.git-pack-relay-status/1'] ['status' status] ['generation' (decimal generation.relay.owner)] ['incarnation' incarnation.owner]]
    :_  owner
    :~  [%give %fact ~ %stead-result-3 !>(raw)]
        [%give %kick ~ ~]
    ==
  ++  inspect-pack-selection
    |=  project=@t
    ^-  (quip card:agent:gall state)
    ?>  &((uuid project) =(src.bowl our.bowl))
    =/  selected=(unit manifest:stead-code-pack-anchor)
      ?.  &(available !(retired-project project))  ~
      =/  destination  (target:stead-code-home db.owner project)
      ?~  destination  ~
      ?.  (matches:stead-code-pack-relay-pin relay.owner u.destination incarnation.owner)  ~
      =/  entry  (~(get by packs.code.owner) project)
      ?.  ?=([~ %accepted *] entry)  ~
      =/  pack
        =/  current  (~(get by external.owner) project)
        ?~  current  pack.row.u.entry
        current.u.current
      ?.(=(destination.pack u.destination) ~ [~ pack])
    =/  raw
      %-  canonical  %-  object
      :~  ['protocol' 'stead.git-pack-projection-selection/1']
          ['status' ?~(selected 'closed' 'open')]
          ['incarnation' incarnation.owner]
          ['relay_generation' (decimal generation.relay.owner)]
          ['snapshot' ?~(selected '' snapshot.u.selected)]
          ['manifest' ?~(selected '' (snapshot-bytes:stead-code-pack-anchor u.selected))]
      ==
    :_  owner
    :~  [%give %fact ~ %stead-result-3 !>(raw)]
        [%give %kick ~ ~]
    ==
  ++  response
    |=  [id=@ta status=@ud mime=@t bytes=@t cookies=(list @t)]
    ^-  (list card:agent:gall)
    =/  headers  (weld security-headers:stead-http [['content-type' mime] (turn cookies |=(text=@t ['set-cookie' text]))])
    (give-simple-payload:app:server id [[status headers] [~ [(met 3 bytes) bytes]]])
  ++  code-response
    |=  [id=@ta out=result:stead-code-home]
    ^-  (quip card:agent:gall state)
    =/  headers  (weld security-headers:stead-http ~[['content-type' mime.out]])
    =?  headers  =(401 status.out)
      [['www-authenticate' 'Basic realm="Stead Git"'] headers]
    :_  owner(code next.out)
    (give-simple-payload:app:server id [[status.out headers] [~ body.out]])
  ++  review-http
    |=  [id=@ta incoming=incoming:stead-http values=object-map]
    ^-  (quip card:agent:gall state)
    =/  denied  [(response id 404 'application/json' (error:stead-team 'denied_or_not_found') ~) owner]
    =/  project  (field values 'project_id')
    ?.  &((uuid project) !(retired-project project))  denied
    =/  now  (now-ms now.bowl)
    =/  session  (browser-session:stead-code-home db.owner auth.transient.owner incoming now)
    ?~  session  denied
    =/  auth  (browser-context:stead-team db.owner u.session now)
    ?~  auth  denied
    =/  action  (field values 'action')
    =/  minimum  ?:(|(=('external-proposal' action) =('external-list' action)) 1 ?:(=('external-submit' action) 2 3))
    ?.  (gte (role:stead-team db.owner u.auth project now) minimum)  denied
    =/  target  (target:stead-code-home db.owner project)
    ?~  target  denied
    =/  seed  (~(get by packs.code.owner) project)
    ?~  seed  denied
    =/  fresh  (open:stead-code-pack-ledger u.seed)
    ?~  fresh  denied
    =/  current  (fall (~(get by external.owner) project) u.fresh)
    ?.  =(u.target destination.current.current)  denied
    =/  book  (fall (~(get by pack-reviews.owner) project) (empty:stead-code-pack-review-board u.target))
    ?:  =('external-merge' action)
      (review-merge id u.auth u.target current book now values)
    =/  out  (run:stead-code-pack-review-api db.owner book u.auth u.target current.current generation.current now values (member:stead-code-home db.owner now))
    =?  owner  ?=(^ next.out)
      owner(pack-reviews (~(put by pack-reviews.owner) project u.next.out))
    [(response id status.out 'application/json' body.out ~) owner]
  ++  review-merge
    |=  $:  id=@ta  auth=authentication:stead-team  destination=scope:stead-code-credentials
            current=ledger:stead-code-pack-ledger  book=state:stead-code-pack-review-board
            now=@ud  values=object-map
        ==
    ^-  (quip card:agent:gall state)
    =/  failure
      |=  reason=@t
      ^-  (quip card:agent:gall state)
      [(response id 409 'application/json' (error:stead-team reason) ~) owner]
    ?.  (keys values ~['protocol' 'action' 'project_id' 'proposal_id' 'revision' 'request_id' 'worker_generation' 'worker_signature' 'proof'])
      (failure 'invalid_request')
    =/  proposal  (field values 'proposal_id')
    =/  request  (field values 'request_id')
    ?.  &((uuid proposal) (uuid request))  (failure 'invalid_request')
    =/  prior  (~(get by promotions.current) request)
    =/  row=(unit proposal:stead-code-pack-review)
      ?~  prior  (~(get by proposals.book) proposal)
      [~ reviewed.review.candidate.u.prior]
    ?~  row  (failure 'proposal_unavailable')
    ?.  &(=(proposal id.item.u.row) =((uint (field values 'revision')) number.change.item.u.row))
      (failure 'stale_review')
    =/  raw  (field values 'proof')
    =/  checked=(unit checked:stead-code-pack-ledger)
      ?^  prior
        ?.  =((hash-wire:stead-code-pack-proof raw) wire.decision.candidate.u.prior)  ~
        [~ (evidence:stead-code-pack-promotion u.prior)]
      =/  worker  (current-key:stead-code-pack-relay-pin relay.owner destination incarnation.owner)
      ?~  worker  ~
      (decode:stead-code-pack-review-proof raw u.row current.current request u.worker (uint (field values 'worker_generation')) (field values 'worker_signature'))
    ?~  checked  (failure 'worker_proof_denied')
    =/  environment  (env:stead-code-pack-review-api db.owner destination now (member:stead-code-home db.owner now))
    =/  out
      (accept:stead-code-pack-review-board book environment generation.current current.current identity.auth request u.row u.checked prior)
    ?:  ?=(%rejected -.out)  (failure reason.out)
    =/  promoted=(each ledger:stead-code-pack-ledger @tas)
      ?:  ?=(%replayed -.out)  [%& current]
      (promote:stead-code-pack-ledger current saved.out now)
    ?:  ?=(%| -.promoted)  (failure p.promoted)
    =/  project  project.destination
    =?  owner  ?=(%applied -.out)
      owner(pack-reviews (~(put by pack-reviews.owner) project next.out), external (~(put by external.owner) project p.promoted))
    =/  body
      %-  canonical  %-  object
      :~  ['protocol' 'stead.code/1']  ['status' 'merged']  ['request_id' request]
          ['proposal_id' proposal]  ['snapshot' snapshot.pack.decision.candidate.saved.out]
          ['generation' (decimal generation.decision.candidate.saved.out)]
      ==
    [(response id 200 'application/json' body ~) owner]
  ++  external-selection
    |=  project=@t
    ^-  (unit pack-selection:stead-code-home)
    =/  row  (~(get by external.owner) project)
    ?~  row  ~
    ?~  journal.u.row  ~
    =/  recent  (need (history:stead-code-pack-ledger u.row i.journal.u.row))
    [~ current.u.row i.journal.u.row accepted.recent generation.u.row]
  ++  relay-http
    |=  [id=@ta incoming=inbound-request:eyre]
    ^-  (quip card:agent:gall state)
    =/  denied  [(response id 403 'application/json' (error:stead-team 'denied_or_not_found') ~) owner]
    ?.  ?=(%open -.relay.owner)  denied
    =/  config  (need current.registry.db.owner)
    =/  input  (validate:stead-code-pack-relay-http incoming origin.config)
    ?~  input  denied
    =/  project  project.u.input
    =/  scope  (target:stead-code-home db.owner project)
    =/  seed  (~(get by packs.code.owner) project)
    ?.  &(?=(^ scope) ?=(^ seed) !(retired-project project))  denied
    =/  worker  (allowed:stead-code-pack-relay-pin relay.owner u.scope incarnation.owner capability.u.input)
    ?~  worker  denied
    =/  now  (now-ms now.bowl)
    =/  resolve  (member:stead-code-home db.owner now)
    =/  allows  (allowed:stead-code-home db.owner now)
    ?.  ?=(^ (check:stead-code-credentials book.code.owner bearer.u.input u.scope %write now resolve allows))
      denied
    =/  frame  (decode:stead-code-pack-relay-wire raw.u.input)
    ?~  frame  denied
    ?:  ?=(%advertise -.task.u.frame)
      (code-response id (pack-for:stead-code-home db.owner code.owner project bearer.u.input now (external-selection project) %write))
    =/  gates=context:stead-code-pack-control
      :*  u.scope  now  incarnation.owner  available  |  |
          book.code.owner  resolve  allows
          |=([action:stead-code-receive update:stead-code-pack-ledger] &)
          ~
          |=([admission:stead-code-pack-ledger checked:stead-code-pack-ledger] |)
      ==
    =/  out
      (write:stead-code-pack-relay gates (~(get by external.owner) project) u.seed project bearer.u.input u.worker u.frame)
    =?  owner  ?=(^ changed.out)
      owner(external (~(put by external.owner) project u.changed.out))
    [(response id 200 'application/json' body.out ~) owner]
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
    ?:  &(?=(^ product.owner) ?|((route:stead-code-pack-relay-http url.request.request) (git-path:stead-code-http url.request.request)))
      [(response id 403 'application/json' (error:stead-team 'unsupported_profile') ~) owner]
    ?:  (route:stead-code-pack-relay-http url.request.request)
      (relay-http id request)
    ?:  (git-path:stead-code-http url.request.request)
      =/  input  (validate:stead-code-http request origin.config)
      ?~  input  [(response id 403 'application/json' (error:stead-team 'invalid_http_request') ~) owner]
      ?:  ?=(%pack-read -.operation.u.input)
        =/  project  project.u.input
        (code-response id (read-selected:stead-code-home db.owner code.owner project bearer.u.input (now-ms now.bowl) (external-selection project)))
      ?:  &((retired-project project.u.input) ?|(?=(%receive -.operation.u.input) ?=([%advertise %git-receive-pack] operation.u.input)))
        (code-response id (error:stead-code-home code.owner 401 'denied_or_not_found'))
      ?:  ?=(%receive -.operation.u.input)  (queue-git id u.input)
      (code-response id (serve:stead-code-home db.owner code.owner u.input (now-ms now.bowl) ''))
    =/  parsed  (validate:stead-http request origin.config (paths:stead-assets '/stead/'))
    ?~  parsed  [(response id 403 'application/json' (error:stead-team 'invalid_http_request') ~) owner]
    ?:  =('/stead/api/code' route.u.parsed)
      ?^  product.owner
        [(response id 403 'application/json' (error:stead-team 'unsupported_profile') ~) owner]
      =/  review=(unit object-map)
        ?.  (lte (met 3 body.u.parsed) 8.192)  ~
        =/  json  (parse body.u.parsed)
        ?.  ?=([~ %o *] json)  ~
        =/  obj  p.u.json
        =/  action  (~(get by obj) 'action')
        ?.  ?=([~ %s *] action)  ~
        ?.  ?&  =([~ %s 'stead.code/1'] (~(get by obj) 'protocol'))
                ?|  =('external-proposal' p.u.action)  =('external-submit' p.u.action)
                    =('external-approve' p.u.action)  =('external-merge' p.u.action)
                    =('external-list' p.u.action)
                ==
            ==
          ~
        [~ obj]
      ?^  review  (review-http id u.parsed u.review)
      (code-response id (manage-with-worker:stead-code-home db.owner code.owner auth.transient.owner u.parsed (now-ms now.bowl) eny.bowl retired-project external-selection pack-write-ready))
    ?:  =(%'GET' method.request.request)
      =/  entry  (~(get by files.owner) route.u.parsed)
      ?~  entry  [(response id 404 'text/plain' 'Not found' ~) owner]
      [(response id 200 mime.u.entry bytes.u.entry ~) owner]
    ?^  product.owner
      =/  out  (call:stead-product-browser product-pair view.owner transient.owner u.parsed (now-ms now.bowl) eny.bowl)
      =/  cards  (response id status.out 'application/json' bytes.out cookies.out)
      =?  cards  ?=(^ outgoing.out)
        =/  challenge=card:agent:gall
          [%pass [%stead-approval (decimal act.bowl) ~] %agent [ship.u.outgoing.out %stead-identity] %poke %stead-auth-challenge-1 !>(bytes.u.outgoing.out)]
        (weld cards [challenge ~])
      [cards owner(db db.next.out, product (some phase.next.out), view view.out, transient transient.out)]
    =/  attempted  (mule |.((call-fenced:stead-browser db.owner view.owner transient.owner u.parsed (now-ms now.bowl) eny.bowl retired.owner)))
    ?:  ?=(%| -.attempted)  [(response id 400 'application/json' (error:stead-team 'invalid_request') ~) owner]
    =/  out  p.attempted
    =/  cards  (response id status.out 'application/json' bytes.out cookies.out)
    =?  cards  ?=(^ outgoing.out)
      =/  challenge=card:agent:gall
        [%pass [%stead-approval (decimal act.bowl) ~] %agent [ship.u.outgoing.out %stead-identity] %poke %stead-auth-challenge-1 !>(bytes.u.outgoing.out)]
      (weld cards [challenge ~])
    [cards owner(db db.out, view view.out, transient transient.out)]
  ++  queue-git
    |=  [id=@ta input=incoming:stead-code-http]
    ^-  (quip card:agent:gall state)
    =/  request  (request-id:stead-code-home eny.bowl act.bowl)
    =/  queued  (quarantine:stead-code-home db.owner code.owner input (now-ms now.bowl) request)
    ?:  ?=(%refused -.queued)  (code-response id out.queued)
    ?:  |((~(has by git-waiting.owner) key.queued) (gte ~(wyt by git-waiting.owner) 4))
      (code-response id (error:stead-code-home code.owner 409 'upload_in_progress'))
    =/  nonce  (token:stead-session eny.bowl act.bowl 'stead.git-lease/1')
    =/  route=wire  [%stead-git key.queued nonce ~]
    =/  wake=card:agent:gall  [%pass route %arvo %b %wait (add now.bowl (div ~s1 10))]
    [[wake ~] owner(code next.queued, git-waiting (~(put by git-waiting.owner) key.queued [id src.bowl bearer.input nonce]))]
  ++  finish-git
    |=  [key=@t nonce=@t]
    ^-  (quip card:agent:gall state)
    =/  found  (~(get by git-waiting.owner) key)
    ?~  found  [~ owner]
    ?.  =(nonce nonce.u.found)  [~ owner]
    =/  next  owner(git-waiting (~(del by git-waiting.owner) key))
    ?.  (response-source:stead-eyre sup.bowl sender.u.found id.u.found)  [~ next]
    =/  out
      ?.  available  (error:stead-code-home code.owner 503 'projection_unavailable')
      =/  job  (~(get by uploads.code.owner) key)
      ?:  &(?=(^ job) (retired-project project.destination.u.job))
        (error:stead-code-home code.owner 401 'denied_or_not_found')
      =/  attempted
        (mule |.((finish-upload:stead-code-home db.owner code.owner key bearer.u.found (now-ms now.bowl))))
      ?:  ?=(%| -.attempted)  (error:stead-code-home code.owner 400 'invalid_request')
      p.attempted
    =/  [cards=(list card:agent:gall) changed=state]  (code-response id.u.found out)
    [cards changed(git-waiting git-waiting.next)]
  ++  poke
    |=  [mark=mark vase=vase]
    ^-  (quip card:agent:gall state)
    ?:  =(%stead-product-activate-1 mark)  (activate-product !<(@t vase))
    ?:  =(%stead-owner-command-1 mark)
      ?>  &(=(src.bowl our.bowl) ?=(^ product.owner) product-ready)
      =/  before  registry.db.owner
      =/  out  (owner-command:stead-product-home product-pair !<(@t vase) our.bowl src.bowl (now-ms now.bowl))
      =/  projected  (projected:stead-product-home db.owner db.next.out view.owner)
      =/  next  owner(db db.next.out, product (some phase.next.out), view projected)
      ?:  =(before registry.db.next)  [~ next]
      ::  Configuration/custody rotation invalidates every transient reader.
      [kicks next(transient *ephemeral:stead-browser, pending ~, incarnation '', files ~, code code.next(book *ledger:stead-code-credentials), git-waiting ~, relay [%closed 0 ~])]
    ?:  =(%stead-team-config-1 mark)  (configured !<(@t vase))
    ?:  =(%stead-bootstrap-1 mark)  (bootstrap !<(@t vase))
    ?:  =(%handle-http-request mark)  (http !<([@ta inbound-request:eyre] vase))
    ?>  available
    ?:  =(%noun mark)
      ?>  ?=(~ product.owner)
      ?>  =(src.bowl our.bowl)
      ?:  ?=([~ %stead-pack-relay-policy *] q.vase)
        =/  [~ %stead-pack-relay-policy cmd=command:stead-code-pack-relay-pin]
          ;;([~ %stead-pack-relay-policy command:stead-code-pack-relay-pin] q.vase)
        =/  selected
          ^-  (unit scope:stead-code-credentials)
          ?:  ?=(%close -.cmd)  [~ *scope:stead-code-credentials]
          =/  project  project.destination.desired.cmd
          ?>  !(retired-project project)
          ?>  ?=([~ %accepted *] (~(get by packs.code.owner) project))
          (target:stead-code-home db.owner project)
        ?>  ?=(^ selected)
        =/  next  (transition:stead-code-pack-relay-pin relay.owner u.selected incarnation.owner cmd)
        ?>  ?=(^ next)
        [~ owner(relay u.next)]
      ?>  pack-local-ready
      =/  [~ %stead-pack-local cmd=command:stead-code-pack-owner]
        ;;([~ %stead-pack-local command:stead-code-pack-owner] q.vase)
      (pack-local cmd)
    ?:  =(%stead-code-pack-stage-1 mark)
      ?>  ?=(~ product.owner)
      ?>  =(src.bowl our.bowl)
      =/  pack  (decode:stead-code-pack-anchor !<(@t vase))
      ?>  !(retired-project project.destination.pack)
      =/  next  (stage-pack:stead-code-home db.owner code.owner pack src.bowl (now-ms now.bowl))
      ?>  ?=(^ next)
      [~ owner(code u.next)]
    ?:  =(%stead-auth-approval-1 mark)
      =/  admitted
        ?~  product.owner  &
        (active-member:stead-product-history (current:stead-product-home product-pair) native-actor (now-ms now.bowl))
      ?>  admitted
      [~ owner(transient (approve:stead-browser db.owner transient.owner src.bowl !<(@t vase) (now-ms now.bowl)))]
    ?^  product.owner  (product-native mark !<(@t vase))
    ?>  ?|  =(%stead-command-3 mark)  =(%stead-query-3 mark)  =(%stead-updates-3 mark)
        ==
    =/  actor  native-actor
    =/  raw  !<(@t vase)
    ?>  (lte (met 3 raw) 65.536)
    =/  value  (need (parse raw))
    ?>  ?=([%o *] value)
    =/  request  (field p.value 'request_id')
    ?>  (uuid request)
    =/  domain  ?:(=(%stead-command-3 mark) 'stead.command/3' ?:(=(%stead-query-3 mark) 'stead.query/3' 'stead.updates/3'))
    =/  digest  (hash domain (canonical value))
    =/  route=path  [%v3 %result (scot %p src.bowl) binding.identity.actor (decimal revision.identity.actor) request digest ~]
    =/  reserved  (need (~(get by pending.owner) route))
    ?>  &(=(actor actor.reserved) (gth expires.reserved (now-ms now.bowl)))
    =/  outcome
      =/  unsupported  (version-error:stead-team-codec value domain)
      ?^  unsupported  [u.unsupported owner]
      ?:  =(%stead-command-3 mark)
        =/  cmd  (decode:stead-team-codec raw)
        =/  out  (apply:stead-project-retirement retired.owner db.owner actor cmd (now-ms now.bowl))
        =/  view
          ?:  =(db.owner next.out)  view.owner
          ?>  ?=(^ journal.data.next.out)
          (append:stead-projection view.owner i.journal.data.next.out)
        =/  advanced=[next=state:stead-updates pages=state:stead-views]
          ?:  (ready:stead-projection next.out view)
            (advance:stead-updates next.out auth.transient.owner updates.transient.owner pages.transient.owner (now-ms now.bowl))
          [*state:stead-updates *state:stead-views]
        [response.out owner(db next.out, view view, transient transient.owner(updates next.advanced, pages pages.advanced))]
      ?:  =(%stead-updates-3 mark)
        =/  input  (decode:stead-update-codec raw)
        =/  out  (execute:stead-updates db.owner view.owner auth.transient.owner updates.transient.owner pages.transient.owner actor input (now-ms now.bowl) eny.bowl)
        [response.out owner(transient transient.owner(updates next.out, pages pages.out))]
      =/  query  (decode-query:stead-team-codec raw)
      =/  out  (execute:stead-views db.owner view.owner pages.transient.owner actor query (now-ms now.bowl) eny.bowl)
      [response.out owner(transient transient.owner(pages next.out))]
    =/  body=@t  -.outcome
    =/  next=state  +.outcome
    :_  next(pending (~(del by pending.next) route))
    :~  [%give %fact [route ~] %stead-result-3 !>(body)]
        [%give %kick [route ~] ~]
    ==
  ++  product-native
    |=  [mark=mark raw=@t]
    ^-  (quip card:agent:gall state)
    =/  domain
      ?:  =(%stead-command-3 mark)  'stead.command/3'
      ?:  =(%stead-query-3 mark)  'stead.query/3'
      ?:  =(%stead-updates-3 mark)  'stead.updates/3'
      ?:  =(%stead-command-4 mark)  'stead.command/4'
      ?:  =(%stead-query-4 mark)  'stead.query/4'
      ?:  =(%stead-doc-change-1 mark)  'stead.doc-change/1'
      ?>  =(%stead-doc-change-query-1 mark)
      'stead.doc-change-query/1'
    =/  actor  native-actor
    =/  value  (need (parse-product:stead-product-codec raw))
    ?>  ?=([%o *] value)
    ?>  =(domain (field p.value 'protocol'))
    =/  request  (field p.value 'request_id')
    ?>  (uuid request)
    =/  digest  (hash domain (canonical value))
    =/  family  ?:((~(has in (silt ~['stead.command/3' 'stead.query/3' 'stead.updates/3'])) domain) %v3 %product)
    =/  route=path  [family %result (scot %p src.bowl) binding.identity.actor (decimal revision.identity.actor) request digest ~]
    =/  reserved  (need (~(get by pending.owner) route))
    ?>  &(=(actor actor.reserved) (gth expires.reserved (now-ms now.bowl)))
    =/  outcome=[body=@t next=state]
      ?:  (~(has in (silt ~['stead.command/3' 'stead.command/4' 'stead.doc-change/1'])) domain)
        =/  out  (command:stead-product-home product-pair actor raw (now-ms now.bowl))
        =/  view  (projected:stead-product-home db.owner db.next.out view.owner)
        [response.out owner(db db.next.out, product (some phase.next.out), view view, transient transient.owner(updates *state:stead-updates))]
      ?:  =('stead.updates/3' domain)
        [(error:stead-team 'unsupported_version') owner]
      =/  out  (query:stead-product-home product-pair view.owner pages.transient.owner actor raw (now-ms now.bowl) eny.bowl)
      [response.out owner(transient transient.owner(pages next.out))]
    ?>  (lte (met 3 body.outcome) 262.144)
    :_  next.outcome(pending (~(del by pending.next.outcome) route))
    :~  [%give %fact [route ~] %stead-result-3 !>(body.outcome)]
        [%give %kick [route ~] ~]
    ==
  ++  watch
    |=  route=path
    ^-  (quip card:agent:gall state)
    ?>  &((lte (lent route) 8) (levy route |=(part=@t (lte (met 3 part) 128))))
    ?>  (lte (lent ~(tap by sup.bowl)) 128)
    ?:  ?=([%product-owner-receipt @ @ ~] route)
      ?>  &(=(src.bowl our.bowl) ?=(^ product.owner) product-ready (uuid i.t.route) (token-valid:stead-session i.t.t.route))
      =/  current  (current:stead-product-home product-pair)
      =/  found  (~(get by ledger.current) i.t.route)
      =/  body
        ?~  found  (error:stead-team 'denied_or_not_found')
        ?:  !=(digest.u.found i.t.t.route)  (error:stead-team 'denied_or_not_found')
        receipt.u.found
      [~[[%give %fact [route ~] %stead-result-3 !>(body)] [%give %kick [route ~] ~]] owner]
    ?:  ?=([%http-response @ ~] route)
      ?>  (response-source:stead-eyre sup.bowl src.bowl i.t.route)
      [~ owner]
    ?:  ?=([%bootstrap @ ~] route)
      ?>  &(=(src.bowl our.bowl) (token-valid:stead-session i.t.route))
      ?>  (lte (lent ~(tap by sup.bowl)) 128)
      [~ owner]
    ?:  ?=([%operator @ ~] route)  (inspect i.t.route)
    ?:  =(route /pack-relay/status)  inspect-relay
    ?:  ?=([%pack-selection @ ~] route)  (inspect-pack-selection i.t.route)
    ?:  ?=([%pack-local @ ~] route)
      ?>  &(pack-local-ready =(src.bowl our.bowl) (token-valid:stead-session i.t.route))
      ?>  (lte (lent (skim ~(tap by sup.bowl) |=([duct [ship=@p prior=path]] =(prior route)))) 1)
      [~ owner]
    ?>  &(available ?|(?=([%v3 %result @ @ @ @ @ ~] route) &(?=(^ product.owner) ?=([%product %result @ @ @ @ @ ~] route))))
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
    =/  actor  (need who)
    ?>  ?~  product.owner  &
        &(product-ready (active-member:stead-product-history (current:stead-product-home product-pair) actor (now-ms now.bowl)))
    actor
  ++  leave
    |=  route=path
    ^-  (quip card:agent:gall state)
    ?:  ?=([%http-response @ ~] route)
      =/  active
        %+  skip  ~(tap by git-waiting.owner)
        |=  [key=@t row=git-reply]
        &(=(id.row i.t.route) =(sender.row src.bowl))
      [~ owner(git-waiting (malt active))]
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
    ?:  &(?=([%stead-git @ @ ~] wire) ?=([%behn %wake ~] sign))
      ?^  product.owner  [~ owner]
      (finish-git i.t.wire i.t.t.wire)
    ?.  &(?=([%stead-rebuild @ ~] wire) =(i.t.wire job.owner) ?=([%behn %wake ~] sign))
      [~ owner]
    ?:  &(?=(^ product.owner) !product-ready)
      =/  next  (step:stead-product-home product-pair our.bowl)
      ?:  (invalid:stead-product-home phase.next)
        [~ owner(product (some phase.next), incarnation '')]
      ?.  (ready:stead-product-home phase.next)
        [[wait ~] owner(product (some phase.next))]
      [[wait ~] owner(db db.next, product (some phase.next), view (begin:stead-projection db.next *state:stead-projection))]
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

::  One authoritative owner. Configured v4 with Code, v3 without Code.
/+  default-agent, stead-core, stead-codec, stead-core-v1, stead-codec-v1, stead-team-owner, stead-code-home, stead-home-handoff, stead-browser, stead-code-credentials, stead-project-retirement, stead-code-pack-anchor
=>
|%
+$  saved
  $:  %stead-home
      $%  [%1 db=state:stead-core-v1]
          [%2 db=state:stead-core]
          [%3 team=saved:stead-team-owner]
          [%4 team=saved:stead-team-owner code=saved:stead-code-home]
          [%5 team=saved:stead-team-owner code=persisted:stead-code-home]
          [%6 team=saved:stead-team-owner code=persisted:stead-code-home mode=phase:stead-home-handoff]
          [%7 team=saved:stead-team-owner code=persisted:stead-code-home mode=phase:stead-home-handoff retired=ledger:stead-project-retirement packs=state:stead-code-pack-anchor]
      ==
  ==
+$  pending-entry  [sender=@p expires=@da]
++  now-ms
  |=  now=@da
  (div (mul 1.000 (sub now ~1970.1.1)) ~s1)
++  prune
  |=  [pending=(map path pending-entry) now=@da]
  ^-  [(list card:agent:gall) (map path pending-entry)]
  =/  pairs  ~(tap by pending)
  =/  stale  (skim pairs |=([key=path val=pending-entry] (lte expires.val now)))
  =/  fresh  (skip pairs |=([key=path val=pending-entry] (lte expires.val now)))
  [(turn stale |=([key=path val=pending-entry] [%give %kick [key ~] ~])) (malt fresh)]
++  snapshot
  |=  [db=state:stead-core now=@ud]
  ^-  @t
  =/  pairs=(list [@t @t])  ~
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by projects.db)
    |=  [id=@t val=project-state:stead-core]
    ^-  [@t @t]
    [(cat 3 'policy/' id) (decimal:stead-codec policy.val)]
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by projects.db)
    |=  [id=@t val=project-state:stead-core]
    ^-  [@t @t]
    [(cat 3 'project/' id) (decimal:stead-codec revision.val)]
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by works.db)
    |=  [[project=@t id=@t] val=work-state:stead-core]
    ^-  [@t @t]
    [(cat 3 'work/' (scope-key:stead-core project id)) (decimal:stead-codec revision.val)]
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by documents.db)
    |=  [[project=@t id=@t] val=document-state:stead-core]
    ^-  [@t @t]
    =/  local-id  (cut 3 [(sub (met 3 id) 36) 36] id)
    [(cat 3 'document/' (scope-key:stead-core project (scope-key:stead-core container.val local-id))) (decimal:stead-codec revision.val)]
  =/  revisions  (object:stead-codec pairs)
  =/  base
    %-  object:stead-codec
    :~  ['protocol' 'stead.fixture-snapshot/1']
        ['now_ms' (decimal:stead-codec now)]
        ['state_jam_sha256' (hex:stead-codec 64 (sha-256:sha (rev 3 (met 3 (jam db)) (jam db))))]
        ['projects' (decimal:stead-codec (lent ~(tap by projects.db)))]
        ['work_items' (decimal:stead-codec (lent ~(tap by works.db)))]
        ['documents' (decimal:stead-codec (lent ~(tap by documents.db)))]
        ['grants' (decimal:stead-codec (lent ~(tap by grants.db)))]
        ['objects' (decimal:stead-codec (lent ~(tap by objects.db)))]
        ['object_bytes' (decimal:stead-codec object-bytes.db)]
        ['journal_events' (decimal:stead-codec (lent journal.db))]
        ['receipts' (decimal:stead-codec (lent ~(tap by receipts.db)))]
        ['last_journal_record' ?~(journal.db '' bytes.i.journal.db)]
        ['last_journal_digest' ?~(journal.db '' digest.i.journal.db)]
        ['journal_sha256' (noun-hash journal.db)]
        ['receipts_sha256' (noun-hash receipts.db)]
        ['objects_sha256' (noun-hash objects.db)]
        ['bindings_sha256' (noun-hash bindings.db)]
        ['containers_sha256' (noun-hash containers.db)]
        ['reachable_sha256' (noun-hash reachable.db)]
        ['ordinary_count' (decimal:stead-codec (ordinary-count:stead-core db))]
    ==
  ?>  ?=([%o *] base)
  =/  security
    %-  object:stead-codec
    %+  turn  ~(tap by projects.db)
    |=  [id=@t val=project-state:stead-core]
    [id (decimal:stead-codec (security-count:stead-core db id))]
  (canonical:stead-codec [%o (~(put by (~(put by p.base) 'revisions' revisions)) 'security_counts' security)])
++  noun-hash
  |=  value=*
  =/  bytes  (jam value)
  (hex:stead-codec 64 (sha-256l:sha [(met 3 bytes) (rev 3 (met 3 bytes) bytes)]))
++  pending-snapshot
  |=  [pending=(map path pending-entry) now=@da incoming=(map duct [ship=@p watched=path])]
  ^-  @t
  ::  Administrative observations do not prune; expiry is lazy, not a timer.
  =/  entries  ~(tap by pending)
  ?>  (lte (lent entries) 64)
  =/  base  (object:stead-codec ~[['protocol' 'stead.fixture-pending/1'] ['now_ms' (decimal:stead-codec (now-ms now))] ['total' (decimal:stead-codec (lent entries))]])
  ?>  ?=([%o *] base)
  =/  by-ship
    %-  object:stead-codec
    %+  turn  ~[~zod ~bus ~nec ~bud]
    |=  ship=@p
    =/  name  (scot %p ship)
    [(cut 3 [1 (dec (met 3 name))] name) (decimal:stead-codec (lent (skim entries |=([key=path val=pending-entry] =(ship sender.val)))))]
  =/  rows
    %-  malt
    %+  turn  entries
    |=  [route=path val=pending-entry]
    =/  ducts  (skim ~(tap by incoming) |=([duct [ship=@p watched=path]] =(route watched)))
    [(rap 3 (turn route |=(part=@t (cat 3 '/' part)))) (object:stead-codec ~[['sender' (scot %p sender.val)] ['expires_at_ms' (decimal:stead-codec (now-ms expires.val))] ['incoming_ducts' (decimal:stead-codec (lent ducts))]])]
  (canonical:stead-codec [%o (~(put by (~(put by p.base) 'by_ship' by-ship)) 'entries' [%o rows])])
--
=|  db=state:stead-core
=.  initialized.db  |
=/  owner  empty:stead-team-owner
=/  handoff=phase:stead-home-handoff  [%open 1 ~]
=|  pending=(map path pending-entry)
::  Disposable predecessor builder; never an employee interface or accepted home.
=|  predecessor=state:stead-core-v1
=.  initialized.predecessor  |
=|  predecessor-response=@t
=|  batch-response=@t
=|  hold-outsider=(unit @t)
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def  ~(. (default-agent this %|) bowl)
    team  ~(. (driver:stead-team-owner owner) bowl)
    configured  ?|(?=(^ current.registry.db.owner) ?=(^ restoring.owner))
    sealed  ?=(%sealed -.handoff)
++  on-init
  `this
++  on-save
  ?:  configured
    =/  code=persisted:stead-code-home  [repos.code.owner uploads.code.owner reviews.code.owner builds.code.owner]
    ?:  ?|(?=(^ retired.owner) ?=(^ packs.code.owner))
      !>([%stead-home %7 save:team code handoff retired.owner packs.code.owner])
    ?:  !=(handoff [%open 1 ~])
      !>([%stead-home %6 save:team code handoff])
    ?:  |(?=(^ uploads.code.owner) ?=(^ reviews.code.owner))
      !>([%stead-home %5 save:team code])
    ?:  ?=(~ repos.code.owner)  !>([%stead-home %3 save:team])
    !>([%stead-home %4 save:team repos.code.owner])
  !>([%stead-home %2 db])
++  on-load
  |=  old=vase
  ~|  %stead-unsupported-state
  =/  restored  !<(saved old)
  ?:  ?=([%stead-home %7 *] restored)
    ?>  (valid:stead-home-handoff mode.restored)
    ?>  ?|(?=(^ retired.restored) ?=(^ packs.restored))
    ?>  (validate:stead-project-retirement our.bowl data.db.team.restored retired.restored)
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (load-v7:team team.restored code.restored packs.restored)
    [cards this(owner next(retired retired.restored), pending ~, handoff mode.restored)]
  ?:  ?=([%stead-home %6 *] restored)
    ?>  (valid:stead-home-handoff mode.restored)
    ?>  (gth generation.mode.restored 1)
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (load:team team.restored code.restored)
    [cards this(owner next, pending ~, handoff mode.restored)]
  ?:  ?=([%stead-home %5 *] restored)
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (load:team team.restored code.restored)
    [cards this(owner next, pending ~, handoff [%open 1 ~])]
  ?:  ?=([%stead-home %4 *] restored)
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (load:team team.restored [code.restored ~ ~ ~])
    [cards this(owner next, pending ~, handoff [%open 1 ~])]
  ?:  ?=([%stead-home %3 *] restored)
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (load:team team.restored [~ ~ ~ ~])
    [cards this(owner next, pending ~, handoff [%open 1 ~])]
  =/  next=state:stead-core
    ?:  ?=([%stead-home %1 *] restored)  (migrate-v1:stead-core db.restored)
    db.restored
  ::  Counter/future state is rejected; pending replies never survive an upgrade.
  =/  paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p route=path]] route)))
  =/  cards=(list card:agent:gall)
    (turn ~(tap in paths) |=(route=path [%give %kick [route ~] ~]))
  [cards this(db next, pending ~, owner empty:stead-team-owner, handoff [%open 1 ~])]
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card:agent:gall _this)
  ?:  =(%stead-project-retirement-1 mark)
    ~|  %stead-project-retirement-denied
    ?>  &(configured =(src.bowl our.bowl) !sealed ?=(~ restoring.owner))
    =/  request  (decode:stead-project-retirement !<(@t vase))
    =/  next  (retire:stead-project-retirement our.bowl data.db.owner retired.owner request (now-ms now.bowl))
    ?>  ?=(^ next)
    `this(owner owner(retired u.next))
  ?:  =(%stead-home-handoff-1 mark)
    ?>  &(configured =(src.bowl our.bowl) ?=(~ restoring.owner))
    =/  next  (transition:stead-home-handoff our.bowl handoff !<(command:stead-home-handoff vase))
    ?>  ?=(^ next)
    [kicks:team this(handoff u.next, owner owner(transient *ephemeral:stead-browser, pending ~, incarnation '', files ~, code code.owner(book *ledger:stead-code-credentials), git-waiting ~))]
  ?:  ?|(configured =(%stead-team-config-1 mark))
    ?>  |(!sealed =(%handle-http-request mark))
    ?>  ?|(configured !initialized.db)
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (poke:team mark vase)
    [cards this(owner next, pending ~)]
  ?:  =(%stead-fixture-1 mark)
    ~|  %stead-fixture-denied
    ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl) !initialized.db)
    =/  raw  !<(@t vase)
    `this(db (initialize:stead-core raw))
  ?:  =(%stead-control-1 mark)
    ~|  %stead-fixture-denied
    ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl) initialized.db)
    =/  [op=@tas ship=@p key=@t value=@t]  !<([@tas @p @t @t] vase)
    ?:  =(%roundtrip op)  (on-load on-save)
    ?:  =(%load-future op)  (on-load !>([%stead-home %8 db]))
    ?:  =(%load-counter op)  (on-load !>([%0 0]))
    ?:  =(%hold-outsider-read op)
      ?>  &(=(ship ~bud) (lte (met 3 key) 1.024))
      `this(hold-outsider [~ key])
    ?:  =(%legacy-init op)
      `this(predecessor (initialize:stead-core-v1 value), predecessor-response '')
    ?:  =(%legacy-read op)
      ?>  &(initialized.predecessor (lte (met 3 value) 512))
      =/  input  (need (parse-result:stead-codec value))
      ?>  ?=([%o *] input)
      ?>  (keys:stead-codec p.input ~['project' 'resource'])
      =/  project  (field:stead-codec p.input 'project')
      =/  resource  (field:stead-codec p.input 'resource')
      ?>  &((uuid:stead-codec project) (uuid:stead-codec resource))
      =/  route=path
        ?:  =('project' key)  [%v1 %project project ~]
        ?:  =('work' key)  [%v1 %work project resource ~]
        ?:  =('document' key)  [%v1 %document project resource ~]
        !!
      `this(predecessor-response (read:stead-core-v1 predecessor ship (now-ms now.bowl) route))
    ?:  =(%legacy-batch op)
      ?>  initialized.predecessor
      ?>  (lte (met 3 value) 65.536)
      =/  inputs  (need (parse-result:stead-codec value))
      ?>  ?=([%o *] inputs)
      =/  count  (lent ~(tap by p.inputs))
      ?>  &((gth count 0) (lte count 32))
      =/  index=@ud  0
      |-  ^-  (quip card:agent:gall _this)
      ?:  =(index count)  `this
      =/  raw  (field:stead-codec p.inputs (decimal:stead-codec index))
      =/  cmd  (decode:stead-codec-v1 raw)
      =/  result  (apply-command:stead-core-v1 predecessor ship (now-ms now.bowl) cmd)
      ?>  ?|  !=('all' key)
              =/  parsed  (need (parse-result:stead-codec response.result))
              ?>  ?=([%o *] parsed)
              =('accepted' (field:stead-codec p.parsed 'status'))
          ==
      $(index +(index), predecessor next.result, predecessor-response response.result)
    ?:  =(%native-batch op)
      ?>  (lte (met 3 value) 65.536)
      =/  inputs  (need (parse-result:stead-codec value))
      ?>  ?=([%o *] inputs)
      =/  count  (lent ~(tap by p.inputs))
      ?>  &((gth count 0) (lte count 32))
      =/  index=@ud  0
      |-  ^-  (quip card:agent:gall _this)
      ?:  =(index count)  `this
      =/  raw  (field:stead-codec p.inputs (decimal:stead-codec index))
      =/  cmd  (decode:stead-codec raw)
      =/  result  (apply-command:stead-core db ship (now-ms now.bowl) cmd)
      ?>  ?|  !=('all' key)
              =/  parsed  (need (parse-result:stead-codec response.result))
              ?>  ?=([%o *] parsed)
              =('accepted' (field:stead-codec p.parsed 'status'))
          ==
      $(index +(index), db next.result, batch-response response.result)
    ?:  =(%migrate-legacy op)
      ?>  initialized.predecessor
      (on-load !>([%stead-home %1 predecessor]))
    ?:  =(%load-bad-legacy op)
      ?>  initialized.predecessor
      =/  bad  predecessor
      =.  bad
        ?:  =('policy' key)
          =/  pid  (fixture-id:stead-core '000000000001')
          =/  project  (~(got by projects.bad) pid)
          bad(projects (~(put by projects.bad) pid project(policy +(policy.project))))
        ?:  =('grant' key)
          =/  entries  ~(tap by grants.bad)
          ?>  ?=(^ entries)
          =/  first  i.entries
          bad(grants (~(put by grants.bad) p.first q.first(principal (fixture-id:stead-core '000000000104'))))
        ?:  =('reachable' key)
          =/  entries  ~(tap by reachable.bad)
          ?>  ?=(^ entries)
          =/  first  i.entries
          bad(reachable (~(put by reachable.bad) p.first (~(put in q.first) 0x0)))
        ?:  =('initialized' key)  bad(initialized |)
        bad(receipts ~)
      (on-load !>([%stead-home %1 bad]))
    ?:  =(%binding-drop op)
      ?>  =(ship ~bus)
      `this(db db(bindings (~(del by bindings.db) ~bus)))
    ?:  =(%binding-restore op)
      ?>  =(ship ~bus)
      =/  actor=binding:stead-core
        [(fixture-id:stead-core '000000000102') (fixture-id:stead-core '000000000202') 'person' | & 4.102.444.800.000 profile:stead-core]
      `this(db db(bindings (~(put by bindings.db) ~bus actor)))
    =/  actor  (~(got by bindings.db) ship)
    =.  actor
      ?+  op  !!
        %profile  actor(profile (~(put by profile.actor) key [%s value]))
        %missing  actor(profile (~(del by profile.actor) key))
        %active   actor(active =('yes' value))
        %expiry   actor(expires (uint:stead-codec value))
        %kind     actor(kind value)
      ==
    `this(db db(bindings (~(put by bindings.db) ship actor)))
  ?>  ?|(=(%stead-command-1 mark) =(%stead-command-2 mark))
  =/  cmd
    ~|  %stead-invalid-command
    (decode:stead-codec !<(@t vase))
  ?>  ?|(!=(mark %stead-command-1) =('stead.command/1' protocol.cmd))
  =/  [cards=(list card:agent:gall) fresh=(map path pending-entry)]  (prune pending now.bowl)
  =/  outcome  (apply-command:stead-core db src.bowl (now-ms now.bowl) cmd)
  ::  The sender/binding comes exclusively from current home state + Gall.
  =/  identity  (~(get by bindings.db) src.bowl)
  ?~  identity  [cards this(db next.outcome, pending fresh)]
  =/  route=path
    /v2/result/(scot %p src.bowl)/[id.u.identity]/[project.cmd]/[request.cmd]/[digest.cmd]
  =/  channel  (~(get by fresh) route)
  ?~  channel  [cards this(db next.outcome, pending fresh)]
  ?>  =(src.bowl sender.u.channel)
  ?>  (lte (met 3 response.outcome) 262.144)
  =/  answer=(list card:agent:gall)
    :~  [%give %fact [route ~] %stead-result-2 !>(response.outcome)]
        [%give %kick [route ~] ~]
    ==
  [(weld cards answer) this(db next.outcome, pending (~(del by fresh) route))]
++  on-watch
  |=  route=path
  ^-  (quip card:agent:gall _this)
  ?:  ?=([%project-retirement @ ~] route)
    ~|  %stead-project-retirement-denied
    ?>  &(configured =(src.bowl our.bowl) ?=(~ restoring.owner))
    ?>  (uuid:stead-codec i.t.route)
    =/  body  (need (status:stead-project-retirement our.bowl data.db.owner retired.owner i.t.route))
    :_  this
    :~  [%give %fact ~ %stead-result-3 !>(body)]
        [%give %kick ~ ~]
    ==
  ?:  =(route /home-handoff/status)
    ?>  &(configured =(src.bowl our.bowl))
    =/  body  (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.home-handoff/1'] ['home' (scot %p our.bowl)] ['phase' ?:(sealed 'sealed' 'open')] ['generation' (decimal:stead-codec generation.handoff)]]))
    :_  this
    :~  [%give %fact ~ %stead-result-3 !>(body)]
        [%give %kick ~ ~]
    ==
  ?:  configured
    ?>  |(!sealed ?=([%http-response @ ~] route))
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (watch:team route)
    [cards this(owner next)]
  ~|  %stead-watch-denied
  ?>  (lte (lent route) 8)
  ?>  (levy route |=(segment=@t (lte (met 3 segment) 128)))
  ?:  ?=([%v2 %result @ @ @ @ @ ~] route)
    =/  identity  (context:stead-core db src.bowl (now-ms now.bowl))
    ?>  ?=(^ identity)
    ?>  =((scot %p src.bowl) i.t.t.route)
    ?>  =(id.u.identity i.t.t.t.route)
    ?>  &((uuid:stead-codec i.t.t.t.t.route) (uuid:stead-codec i.t.t.t.t.t.route))
    =/  digest  i.t.t.t.t.t.t.route
    ?>  &(=(64 (met 3 digest)) (levy (rip 3 digest) |=(c=@ ?|(&((gte c 48) (lte c 57)) &((gte c 97) (lte c 102))))))
    =/  [cards=(list card:agent:gall) fresh=(map path pending-entry)]  (prune pending now.bowl)
    ::  Gall already inserted this watch's duct. A named expiry kick also
    ::  retires that new duct: finish retirement without leaving a phantom row.
    ::  A subsequent fresh registration can then reserve this path normally.
    =/  previous  (~(get by pending) route)
    ?:  &(?=(^ previous) (lte expires.u.previous now.bowl))
      [cards this(pending fresh)]
    ?>  !(~(has by fresh) route)
    ?>  (lth (lent ~(tap by fresh)) 64)
    =/  own  (skim ~(tap by fresh) |=([key=path val=pending-entry] =(src.bowl sender.val)))
    ?>  (lth (lent own) 16)
    [cards this(pending (~(put by fresh) route [src.bowl (add now.bowl ~m1)]))]
  ?:  ?&  =(src.bowl ~bud)
          ?=(^ hold-outsider)
          =(u.hold-outsider (rap 3 (turn route |=(part=@t (cat 3 '/' part)))))
      ==
    ::  One owner-arranged outsider duct is held solely to test overlapping
    ::  subscriptions. No body is persisted and no business state changes.
    `this(hold-outsider ~)
  =/  response=@t
    ?:  =(route /v1/pending-snapshot)
      ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl))
      (pending-snapshot pending now.bowl sup.bowl)
    ?:  =(route /v1/batch-response)
      ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl))
      (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.fixture-predecessor/1'] ['response' batch-response]]))
    ?:  =(route /v1/predecessor-snapshot)
      ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl))
      (snapshot predecessor (now-ms now.bowl))
    ?:  =(route /v1/predecessor-response)
      ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl))
      (canonical:stead-codec (object:stead-codec ~[['protocol' 'stead.fixture-predecessor/1'] ['response' predecessor-response]]))
    ?:  =(route /v1/fixture-snapshot)
      ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl))
      (snapshot db (now-ms now.bowl))
    (read:stead-core db src.bowl (now-ms now.bowl) route)
  ?>  (lte (met 3 response) 262.144)
  ::  Empty paths address only this request duct, never other same-path readers.
  :_  this
  :~  [%give %fact ~ %stead-result-2 !>(response)]
      [%give %kick ~ ~]
  ==
++  on-leave
  |=  route=path
  ?:  configured
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (leave:team route)
    [cards this(owner next)]
  =/  found  (~(get by pending) route)
  ?~  found  `this
  ?.  =(src.bowl sender.u.found)  `this
  `this(pending (~(del by pending) route))
++  on-peek   on-peek:def
++  on-agent  on-agent:def
++  on-arvo
  |=  [=wire =sign-arvo]
  ?:  configured
    =/  [cards=(list card:agent:gall) next=state:stead-team-owner]  (arvo:team wire sign-arvo)
    [cards this(owner next)]
  (on-arvo:def wire sign-arvo)
++  on-fail   on-fail:def
--

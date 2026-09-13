::  Public/synthetic fake-ship profile. One mutation owner, no HTTP or scries.
/+  default-agent, stead-core, stead-codec
=>
|%
+$  saved  [%stead-home %1 db=state:stead-core]
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
    [id (decimal:stead-codec policy.val)]
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by projects.db)
    |=  [id=@t val=project-state:stead-core]
    ^-  [@t @t]
    [(cat 3 id (cat 3 '/' id)) (decimal:stead-codec revision.val)]
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by works.db)
    |=  [[project=@t id=@t] val=work-state:stead-core]
    ^-  [@t @t]
    [(cat 3 project (cat 3 '/' id)) (decimal:stead-codec revision.val)]
  =.  pairs
    %+  weld  pairs
    %+  turn  ~(tap by documents.db)
    |=  [[project=@t id=@t] val=document-state:stead-core]
    ^-  [@t @t]
    [(cat 3 project (cat 3 '/' id)) (decimal:stead-codec revision.val)]
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
    ==
  ?>  ?=([%o *] base)
  (canonical:stead-codec [%o (~(put by p.base) 'revisions' revisions)])
--
=|  db=state:stead-core
=.  initialized.db  |
=|  pending=(map path pending-entry)
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def  ~(. (default-agent this %|) bowl)
++  on-init
  ?>  =(our.bowl ~zod)
  `this
++  on-save
  !>([%stead-home %1 db])
++  on-load
  |=  old=vase
  ~|  %stead-unsupported-state
  =/  restored  !<(saved old)
  ::  Saved product state is distinct from counter %0. Pending replies are lost.
  =/  paths  (silt (turn ~(tap by sup.bowl) |=([duct [ship=@p route=path]] route)))
  =/  cards=(list card:agent:gall)
    (turn ~(tap in paths) |=(route=path [%give %kick [route ~] ~]))
  [cards this(db db.restored, pending ~)]
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card:agent:gall _this)
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
    ?:  =(%load-future op)  (on-load !>([%stead-home %2 db]))
    ?:  =(%load-counter op)  (on-load !>([%0 0]))
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
  ?>  =(%stead-command-1 mark)
  =/  cmd
    ~|  %stead-invalid-command
    (decode:stead-codec !<(@t vase))
  =/  [cards=(list card:agent:gall) fresh=(map path pending-entry)]  (prune pending now.bowl)
  =/  outcome  (apply-command:stead-core db src.bowl (now-ms now.bowl) cmd)
  ::  The sender/binding comes exclusively from current home state + Gall.
  =/  identity  (~(get by bindings.db) src.bowl)
  ?~  identity  [cards this(db next.outcome, pending fresh)]
  =/  route=path
    /v1/result/(scot %p src.bowl)/[id.u.identity]/[project.cmd]/[request.cmd]/[digest.cmd]
  =/  channel  (~(get by fresh) route)
  ?~  channel  [cards this(db next.outcome, pending fresh)]
  ?>  =(src.bowl sender.u.channel)
  ?>  (lte (met 3 response.outcome) 262.144)
  =/  answer=(list card:agent:gall)
    :~  [%give %fact [route ~] %stead-result-1 !>(response.outcome)]
        [%give %kick [route ~] ~]
    ==
  [(weld cards answer) this(db next.outcome, pending (~(del by fresh) route))]
++  on-watch
  |=  route=path
  ^-  (quip card:agent:gall _this)
  ~|  %stead-watch-denied
  ?>  (lte (lent route) 8)
  ?>  (levy route |=(segment=@t (lte (met 3 segment) 128)))
  ?:  ?=([%v1 %result @ @ @ @ @ ~] route)
    =/  identity  (context:stead-core db src.bowl (now-ms now.bowl))
    ?>  ?=(^ identity)
    ?>  =((scot %p src.bowl) i.t.t.route)
    ?>  =(id.u.identity i.t.t.t.route)
    ?>  &((uuid:stead-codec i.t.t.t.t.route) (uuid:stead-codec i.t.t.t.t.t.route))
    =/  digest  i.t.t.t.t.t.t.route
    ?>  &(=(64 (met 3 digest)) (levy (rip 3 digest) |=(c=@ ?|(&((gte c 48) (lte c 57)) &((gte c 97) (lte c 102))))))
    =/  [cards=(list card:agent:gall) fresh=(map path pending-entry)]  (prune pending now.bowl)
    ?>  !(~(has by fresh) route)
    ?>  (lth (lent ~(tap by fresh)) 64)
    =/  own  (skim ~(tap by fresh) |=([key=path val=pending-entry] =(src.bowl sender.val)))
    ?>  (lth (lent own) 16)
    [cards this(pending (~(put by fresh) route [src.bowl (add now.bowl ~m1)]))]
  =/  response=@t
    ?:  =(route /v1/fixture-snapshot)
      ?>  &(=(our.bowl ~zod) =(src.bowl our.bowl))
      (snapshot db (now-ms now.bowl))
    (read:stead-core db src.bowl (now-ms now.bowl) route)
  ?>  (lte (met 3 response) 262.144)
  ::  Empty paths address only this request duct, never other same-path readers.
  :_  this
  :~  [%give %fact ~ %stead-result-1 !>(response)]
      [%give %kick ~ ~]
  ==
++  on-leave
  |=  route=path
  =/  found  (~(get by pending) route)
  ?~  found  `this
  ?.  =(src.bowl sender.u.found)  `this
  `this(pending (~(del by pending) route))
++  on-peek   on-peek:def
++  on-agent  on-agent:def
++  on-arvo   on-arvo:def
++  on-fail   on-fail:def
--

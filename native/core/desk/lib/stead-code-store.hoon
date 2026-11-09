::  PRIVATE PROTOTYPE: pure repository acceptance, no Gall persistence/routes.
::  Home owns this versioned state and pending jobs. No raw pack input exists.
::  Small synchronous proof quotas; production requires durable staged work.
/+  stead-git, stead-codec, stead-session, stead-code-credentials, stead-code-git-objects, stead-code-git-graph, stead-code-receive, stead-code-ancestry
|%
+$  scope  scope:stead-code-credentials
+$  actor  actor:stead-session
+$  object  object:stead-code-git-objects
+$  objects  (map @ux object)
+$  refs  refs:stead-code-receive
+$  update  update:stead-code-receive
+$  action  action:stead-code-receive
+$  ref-policy  $-([actor scope action update] ?)
+$  payload  [destination=scope id=@t owner=actor changes=(list update) items=(list object)]
+$  staged  [digest=@t body=payload]
+$  receipt  [version=@ud destination=scope id=@t digest=@t owner=actor revision=@ud changes=(list update)]
+$  state
  $:  version=@ud  destination=scope  revision=@ud
      objects=objects  refs=refs  pending=(map @t staged)
      receipts=(map @t receipt)  journal=(list @t)
  ==
+$  result
  $%  [%applied next=state accepted=receipt]
      [%replayed next=state accepted=receipt]
      [%rejected next=state reason=@tas]
  ==
++  empty
  |=  destination=scope
  ^-  state
  [1 destination 0 ~ ~ ~ ~ ~]
++  reject
  |=  [db=state why=@tas]
  ^-  result
  [%rejected db why]
::  Internal: only call after payload-bounds. Exact post-parser payload only.
::  Future staged admission must separately bind raw-pack digest and expiry.
++  fingerprint
  |=  body=payload
  ^-  @t
  (hash:stead-codec 'stead.code-stage/1' (bytes-hex:stead-codec (jam body)))
++  payload-bounds
  |=  body=payload
  ^-  ?
  ?.  &((scope-valid:stead-code-credentials destination.body) (uuid:stead-codec id.body) (live:stead-session owner.body 0) (lte (met 0 ship.owner.body) 128))  |
  ?.  &((lte (lent (scag 9 changes.body)) 8) (lte (lent (scag 17 items.body)) 16))  |
  ?.  (levy changes.body |=([change=update] &((lte (met 3 name.change) 128) (lte (met 3 prior.change) 20) (lte (met 3 target.change) 20))))  |
  =/  pending=(list object)  items.body
  =/  bytes=@ud  0
  |-  ^-  ?
  ?~  pending  &
  ?.  &((valid-octets:stead-git body.i.pending) ?=(?(%blob %tree %commit %tag) kind.i.pending) (lte (met 3 oid.i.pending) 20))  |
  =/  total  (add bytes length.body.i.pending)
  ?:  (gth total 65.536)  |
  $(pending t.pending, bytes total)
::  Rehash every candidate, detect collisions, enforce repository body quota.
++  combine
  |=  [current=objects incoming=(list object)]
  ^-  (each objects @tas)
  ?:  (gth ~(wyt by current) 64)  [%| %object-capacity]
  ?.  (levy ~(tap by current) |=([oid=@ux item=object] &(=(oid oid.item) (valid-octets:stead-git body.item))))  [%| %invalid-store]
  =/  bytes=@ud
    (roll ~(tap by current) |=([[oid=@ux item=object] sum=@ud] (add sum length.body.item)))
  ?:  (gth bytes 262.144)  [%| %object-capacity]
  =/  out=objects  current
  |-  ^-  (each objects @tas)
  ?~  incoming  [%& out]
  =/  item  i.incoming
  =/  verified  (inspect:stead-code-git-graph item)
  ?:  ?=(%| -.verified)  [%| %invalid-object]
  =/  prior  (~(get by out) oid.item)
  ?^  prior
    ?.  =(u.prior item)  [%| %oid-collision]
    $(incoming t.incoming)
  ?:  (gte ~(wyt by out) 64)  [%| %object-capacity]
  =/  next=@ud  (add bytes length.body.item)
  ?:  (gth next 262.144)  [%| %object-capacity]
  $(incoming t.incoming, bytes next, out (~(put by out) oid.item item))
::  Parent edges only; no caller-provided ancestry predicate is accepted.
++  descends
  |=  [base=@ux tip=@ux load=reader:stead-code-git-graph]
  ^-  ?
  =/  work  (begin:stead-code-ancestry base tip)
  ?:  ?=(%walking -.work)  (search work(steps 128, bytes 262.144) load 129)
  |
++  search
  |=  [work=search:stead-code-ancestry load=reader:stead-code-git-graph turns=@ud]
  ^-  ?
  ?:  ?=(%ancestor -.work)  &
  ?.  ?=(%walking -.work)  |
  ?:  |(=(0 turns) (gth queued.work 256))  |
  $(work (step:stead-code-ancestry work load), turns (dec turns))
++  closure
  |=  [references=refs load=reader:stead-code-git-graph]
  ^-  (each (map @ux object-kind:stead-code-git-graph) @tas)
  =/  roots=(list edge:stead-code-git-graph)  ~
  =/  pending  ~(tap by references)
  |-  ^-  (each (map @ux object-kind:stead-code-git-graph) @tas)
  ?~  pending  (close roots load)
  =/  item  (load q.i.pending)
  ?~  item  [%| %missing-object]
  ?.  ?=(object-kind:stead-code-git-graph kind.u.item)  [%| %invalid-object]
  $(pending t.pending, roots [[q.i.pending kind.u.item] roots])
++  close
  |=  [roots=(list edge:stead-code-git-graph) load=reader:stead-code-git-graph]
  ^-  (each (map @ux object-kind:stead-code-git-graph) @tas)
  =/  work=closure:stead-code-git-graph
    =/  fresh  (start:stead-code-git-graph roots)
    ?:  ?=(%checking -.fresh)  fresh(visits 512, bytes 262.144)
    fresh
  =/  turns=@ud  1.025
  |-  ^-  (each (map @ux object-kind:stead-code-git-graph) @tas)
  ?:  ?=(%verified -.work)  [%& reachable.work]
  ?.  ?=(%checking -.work)  [%| %invalid-graph]
  ?:  =(0 turns)  [%| %graph-bound]
  $(work (walk:stead-code-git-graph work load), turns (dec turns))
++  accept
  |=  $:  db=state  current=scope  book=ledger:stead-code-credentials
          bearer=@t  id=@t  digest=@t  now=@ud
          resolve=membership:stead-code-credentials
          allows=allowance:stead-code-credentials
          policy=ref-policy  protected=(set @t)
      ==
  ^-  result
  ::  Authorization precedes even the first receipt lookup.
  =/  identity  (check:stead-code-credentials book bearer current %write now resolve allows)
  ?~  identity  (reject db %denied)
  ?.  &(=(1 version.db) =(destination.db current))  (reject db %store-scope)
  ?.  &((uuid:stead-codec id) (token-valid:stead-session digest))  (reject db %invalid-request)
  ?:  |((gth ~(wyt by objects.db) 64) (gth ~(wyt by refs.db) 16) (gth ~(wyt by receipts.db) 32) (gth ~(wyt by pending.db) 4) (gth (lent (scag 33 journal.db)) 32))  (reject db %capacity)
  =/  authorize=$-([action update] ?)
    |=  [intent=action change=update]
    ?.  (~(has in protected) name.change)  (policy u.identity current intent change)
    |
  =/  prior  (~(get by receipts.db) id)
  ?^  prior
    =/  accepted  u.prior
    ?.  &((same-actor:stead-session owner.accepted u.identity) =(1 version.accepted) =(destination.accepted current) =(id id.accepted))  (reject db %denied)
    ?.  &((gth revision.accepted 0) (lte revision.accepted revision.db) (gth (lent (scag 9 changes.accepted)) 0) (lte (lent (scag 9 changes.accepted)) 8))  (reject db %denied)
    ?.  (levy changes.accepted |=([change=update] (authorize ?:(=(0 prior.change) %create ?:(=(0 target.change) %delete %advance)) change)))  (reject db %denied)
    ?.  =(digest digest.accepted)  (reject db %request-id-reused)
    [%replayed db accepted]
  ?:  |((gth ~(wyt by pending.db) 4) (gte ~(wyt by receipts.db) 32) (gte revision.db 18.446.744.073.709.551.615) (gth ~(wyt by refs.db) 16))  (reject db %capacity)
  ?.  =(~(wyt by receipts.db) (lent (scag 33 journal.db)))  (reject db %journal-state)
  =/  found  (~(get by pending.db) id)
  ?~  found  (reject db %missing-stage)
  =/  job  u.found
  ?.  &((same-actor:stead-session owner.body.job u.identity) =(current destination.body.job) =(id id.body.job))  (reject db %stage-scope)
  ?.  (payload-bounds body.job)  (reject db %stage-bound)
  ?.  &(=(digest digest.job) =(digest (fingerprint body.job)))  (reject db %stage-digest)
  =/  joined  (combine objects.db items.body.job)
  ?:  ?=(%| -.joined)  (reject db p.joined)
  =/  load=reader:stead-code-git-graph
    |=  oid=@ux
    (~(get by p.joined) oid)
  =/  kind=$-(@ux (unit @tas))
    |=  oid=@ux
    =/  item  (load oid)
    ?~  item  ~
    [~ kind.u.item]
  =/  lineage=$-([@ux @ux] ?)
    |=  [base=@ux tip=@ux]
    (descends base tip load)
  =/  next  (decide:stead-code-receive refs.db epoch.current epoch.destination.body.job changes.body.job protected authorize kind lineage)
  ?:  ?=(%| -.next)  (reject db p.next)
  ?:  (gth ~(wyt by p.next) 16)  (reject db %ref-capacity)
  =/  graph  (closure p.next load)
  ?:  ?=(%| -.graph)  (reject db p.graph)
  ?.  (levy items.body.job |=([item=object] (~(has by p.graph) oid.item)))  (reject db %unreachable-object)
  ::  Previously accepted objects may outlive refs. Future reads must still
  ::  enforce current scoped reachability, never expose the whole object map.
  =/  accepted=receipt  [1 current id digest u.identity +(revision.db) changes.body.job]
  =/  after=state
    db(revision +(revision.db), objects p.joined, refs p.next, pending (~(del by pending.db) id), receipts (~(put by receipts.db) id accepted), journal [id journal.db])
  [%applied after accepted]
--

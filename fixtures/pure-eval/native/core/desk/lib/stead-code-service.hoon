::  Native SHA-1 Smart HTTP service. The caller owns authorization, transport
::  and the Gall event that installs the returned state before sending a reply.
/+  stead-git, stead-codec, stead-code-credentials, stead-code-store, stead-code-receive-wire, stead-code-git-resolve, stead-code-git-inflate, stead-code-git-response, stead-code-git-graph, stead-code-fetch
|%
+$  repository  state:stead-code-store
+$  octets  octets:stead-git
+$  service  service:stead-code-git-response
+$  ref-row  advertised-ref:stead-code-git-response
+$  outcome  [body=octets next=repository]
++  capabilities
  |=  kind=service
  ^-  (list @t)
  ?:  =(%git-upload-pack kind)  ~['ofs-delta']
  ~['report-status' 'delete-refs' 'atomic' 'ofs-delta']
++  read-object
  |=  db=repository
  ^-  reader:stead-code-git-graph
  |=  oid=@ux
  (~(get by objects.db) oid)
++  peel
  |=  [id=@ux load=reader:stead-code-git-graph]
  ^-  @ux
  =/  remaining=@ud  64
  |-
  ?>  (gth remaining 0)
  =/  item  (need (load id))
  =/  facts  (inspect:stead-code-git-graph item)
  ?>  ?=(%& -.facts)
  ?:  ?=(%tag -.p.facts)  $(id oid.target.p.facts, remaining (dec remaining))
  id
++  advertised
  |=  [db=repository kind=service]
  ^-  (list ref-row)
  =/  load  (read-object db)
  =/  rows
    %+  sort  ~(tap by refs.db)
    |=  [left=[name=@t oid=@ux] right=[name=@t oid=@ux]]
    (aor name.left name.right)
  =/  refs=(list ref-row)
    %+  turn  rows
    |=  [name=@t oid=@ux]
    ?:  &(=(%git-upload-pack kind) =('refs/tags/' (cut 3 [0 10] name)))
      =/  target  (peel oid load)
      [name oid ?:(=(oid target) ~ [~ target])]
    [name oid ~]
  ?.  =(%git-upload-pack kind)  refs
  =/  head  (~(get by refs.db) 'refs/heads/main')
  ?^  head  [['HEAD' u.head ~] refs]
  =/  branches  (skim refs |=(ref=ref-row =('refs/heads/' (cut 3 [0 11] name.ref))))
  ?~  branches  refs
  [['HEAD' oid.i.branches ~] refs]
++  discover
  |=  [db=repository kind=service]
  ^-  octets
  =/  rows  (advertised db kind)
  ?:  &(=(%git-upload-pack kind) ?=(~ rows))
    (append:stead-git (packet:stead-code-git-response (cat 3 '# service=git-upload-pack' 10)) [8 '00000000'])
  =/  result  (discovery:stead-code-git-response kind rows (capabilities kind))
  ?>  ?=(%& -.result)
  p.result
++  fetch
  |=  [db=repository wire=octets]
  ^-  (each octets @tas)
  =/  load  (read-object db)
  =/  tips=(list edge:stead-code-git-graph)
    %-  zing
    %+  murn  (advertised db %git-upload-pack)
    |=  ref=ref-row
    ^-  (unit (list edge:stead-code-git-graph))
    =/  item  (need (load oid.ref))
    ?.  ?=(object-kind:stead-code-git-graph kind.item)  ~
    =/  primary=edge:stead-code-git-graph  [oid.ref kind.item]
    ?~  peeled.ref  [~ ~[primary]]
    =/  target  (need (load u.peeled.ref))
    ?.  ?=(object-kind:stead-code-git-graph kind.target)  ~
    [~ ~[primary [u.peeled.ref kind.target]]]
  =/  result  (from-wire:stead-code-fetch wire & tips load)
  ?:  ?=(%| -.result)  [%| p.result]
  [%& body.p.result]
++  unpack
  |=  [wire=octets load=reader:stead-code-git-graph]
  ^-  (each (list object:stead-git) @tas)
  =/  work  (begin:stead-code-git-resolve wire)
  =/  turns=@ud  96
  ?:  ?=(%scan -.work)
    ?:  (gth left.data.work 16)  [%| %object-capacity]
    (expand work(data data.work(store store.data.work(budget 65.536))) load turns)
  [%| %invalid-pack]
++  expand
  |=  [work=job:stead-code-git-resolve load=reader:stead-code-git-graph turns=@ud]
  ^-  (each (list object:stead-git) @tas)
  ?:  ?=(%rejected -.work)  [%| reason.work]
  ?:  ?=(%complete -.work)  [%& (turn ~(tap by items.work) |=([oid=@ux item=object:stead-git] item))]
  ?:  =(0 turns)  [%| %work-bound]
  $(work (step:stead-code-git-resolve work inflate:stead-code-git-inflate load), turns (dec turns))
++  statuses
  |=  [changes=(list update:stead-code-store) unpack=unpack-result:stead-code-git-response rejection=(unit @t)]
  ^-  octets
  =/  rows
    %+  turn  changes
    |=  change=update:stead-code-store
    ^-  ref-result:stead-code-git-response
    [name.change ?~(rejection [%committed ~] [%rejected u.rejection])]
  =/  result  (report:stead-code-git-response unpack rows)
  ?>  ?=(%& -.result)
  p.result
++  receive
  |=  $:  db=repository  wire=octets  id=@t  book=ledger:stead-code-credentials
          bearer=@t  now=@ud  resolve=membership:stead-code-credentials
          allows=allowance:stead-code-credentials  policy=ref-policy:stead-code-store
          protected=(set @t)
      ==
  ^-  (each outcome @tas)
  ?.  (lte length.wire 65.536)  [%| %request-bound]
  =/  who  (check:stead-code-credentials book bearer destination.db %write now resolve allows)
  ?~  who  [%| %denied]
  =/  decoded
    (decode:stead-code-receive-wire wire (silt (capabilities %git-receive-pack)))
  ?:  ?=(%| -.decoded)  [%| p.decoded]
  =/  commands  p.decoded
  ?.  (~(has in capabilities.commands) 'report-status')  [%| %report-status-required]
  =/  offset  pack-offset.commands
  =/  length=@ud  (sub length.wire offset)
  =/  deleting=?  (levy changes.commands |=(change=update:stead-code-store =(0 target.change)))
  =/  raw-view  (read-object db)
  =/  graph  (closure:stead-code-store refs.db raw-view)
  ?:  ?=(%| -.graph)  [%| %unavailable]
  =/  visible=reader:stead-code-git-graph
    |=  oid=@ux
    ?.  (~(has by p.graph) oid)  ~
    (raw-view oid)
  =/  objects=(each (list object:stead-git) @tas)
    ?:  deleting  ?:(=(0 length) [%& ~] [%| %unexpected-pack])
    (unpack [length (cut 3 [offset length] data.wire)] visible)
  ?:  ?=(%| -.objects)
    [%& (statuses changes.commands [%failed 'invalid or oversized pack'] [~ 'pack rejected']) db]
  =/  available  (silt (turn p.objects |=(item=object:stead-git oid.item)))
  =/  authorized=$-(@ux ?)
    |=  oid=@ux
    |((~(has by p.graph) oid) (~(has in available) oid))
  ?.  %+  levy  changes.commands
      |=  change=update:stead-code-store
      |(=(0 target.change) (authorized target.change))
    [%& (statuses changes.commands [%unpacked ~] [~ 'target unavailable']) db]
  ?.  %+  levy  p.objects
      |=  item=object:stead-git
      =/  facts  (inspect:stead-code-git-graph item)
      ?.  ?=(%& -.facts)  |
      (levy (edges:stead-code-git-graph p.facts) |=(edge=edge:stead-code-git-graph (authorized oid.edge)))
    [%& (statuses changes.commands [%unpacked ~] [~ 'object dependency unavailable']) db]
  =/  payload=payload:stead-code-store  [destination.db id u.who changes.commands p.objects]
  ?.  (payload-bounds:stead-code-store payload)
    [%& (statuses changes.commands [%unpacked ~] [~ 'repository limits exceeded']) db]
  =/  digest  (fingerprint:stead-code-store payload)
  =/  staging=repository  db(pending (~(put by pending.db) id [digest payload]))
  =/  committed
    (accept:stead-code-store staging destination.db book bearer id digest now resolve allows policy protected)
  ?:  ?=(%rejected -.committed)
    [%& (statuses changes.commands [%unpacked ~] [~ reason.committed]) db]
  ?:  ?=(%replayed -.committed)
    [%& (statuses changes.commands [%unpacked ~] ~) db]
  [%& (statuses changes.commands [%unpacked ~] ~) next.committed]
--

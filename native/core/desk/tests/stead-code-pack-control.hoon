/+  *test, stead-codec, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-control, stead-code-credentials, stead-code-receive, stead-session, stead-code-git-graph, stead-git
=,  stead-code-pack-control
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  destination=scope  [~zod project project 1]
=/  request=@t  '019939ba-4000-7000-8000-000000000004'
=/  bootstrap=@t  '019939ba-4000-7000-8000-000000000006'
=/  digest=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  main=@t  'refs/heads/main'
=/  topic=@t  'refs/heads/topic'
=/  main-key  (bytes-hex:stead-codec main)
=/  topic-key  (bytes-hex:stead-codec topic)
=/  seal
  |=  input=manifest:stead-code-pack-ledger
  ^-  manifest:stead-code-pack-ledger
  =/  raw  (snapshot-bytes:stead-code-pack-anchor input)
  =/  size  (met 3 raw)
  input(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
=/  current=manifest:stead-code-pack-ledger
  %-  seal
  :*  destination  ''  main-key
      (malt ~[[main-key (oid-text:stead-git 0x11)] [topic-key (oid-text:stead-git 0x11)]])
      digest  400  3  500  digest
  ==
=/  pack=manifest:stead-code-pack-ledger
  =/  refs=(map @t @t)  (~(put by refs.current) topic-key (oid-text:stead-git 0x22))
  (seal current(refs refs, objects 6))
=/  who=actor
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
=/  anchor=entry:stead-code-pack-anchor
  [%accepted [current ~zod 1 900.001] [bootstrap who 2]]
=/  base  (need (open:stead-code-pack-ledger anchor))
=/  claim=intent
  [destination snapshot.current 0 digest request 1 snapshot.pack ~[[topic 0x11 0x22]]]
=/  kinds=(list [@ux object-kind:stead-code-git-graph])  ~[[0x22 %commit]]
=/  proof=checked
  [destination snapshot.current 0 digest request changes.claim pack (malt kinds) (silt ~[[0x11 0x22]])]
=/  current-member=membership:stead-code-credentials
  |=  sender=@p
  ^-  (unit actor)
  ?.  =(ship.who sender)  ~
  [~ who]
=/  any-access=allowance:stead-code-credentials  |=([actor scope access:stead-code-credentials] &)
=/  no-access=allowance:stead-code-credentials  |=([actor scope access:stead-code-credentials] |)
=/  every-ref=allow:stead-code-pack-ledger  |=([action:stead-code-receive update:stead-code-pack-ledger] &)
=/  issued  (issue:stead-code-credentials *ledger:stead-code-credentials who destination & 1.000.000 3 42 any-access)
?>  ?=(%& -.issued)
=/  reader  (issue:stead-code-credentials *ledger:stead-code-credentials who destination | 1.000.000 3 43 any-access)
?>  ?=(%& -.reader)
=/  worker-proof=worker-check
  |=  [row=admission evidence=checked]
  &(=(claim.row claim) =(proof evidence))
=/  gate=context
  [destination 3 incarnation.claim & | | next.p.issued current-member any-access every-ref ~ worker-proof]
=/  writer  bearer.p.issued
|%
++  test-pack-control-write-and-operational-fences
  ^-  tang
  =/  input=command  [%admit claim ~]
  ?>  ?=([%pending %applied *] (apply base gate writer input))
  ?>  ?=([%refused %denied] (apply base gate '' input))
  ?>  ?=([%refused %denied] (apply base gate(book next.p.reader) bearer.p.reader input))
  ?>  ?=([%refused %denied] (apply base gate(available |) writer input))
  ?>  ?=([%refused %denied] (apply base gate(sealed &) writer input))
  ?>  ?=([%refused %denied] (apply base gate(retired &) writer input))
  ?>  ?=([%refused %denied] (apply base gate(incarnation '') writer input))
  ?>  ?=([%refused %denied] (apply base gate(now 1.000.000) writer input))
  ?>  ?=([%refused %denied] (apply base gate(selected destination(epoch 2)) writer input))
  ?>  ?=([%refused %denied] (apply base gate writer [%admit claim(destination destination(epoch 2)) ~]))
  ?>  ?=([%refused %denied] (apply base gate writer [%admit claim(changes ~[[main 0x11 0x22]]) ~]))
  ?>  ?=([%refused %denied] (apply base gate(protected (silt ~[topic])) writer input))
  ~
++  test-pack-control-checks-exact-worker-and-current-uploader
  ^-  tang
  =/  staged  (apply base gate writer [%admit claim ~])
  ?>  ?=([%pending %applied *] staged)
  =/  held  next.result.staged
  =/  worker-denied=worker-check  |=([admission checked] |)
  ?>  ?=([%refused %worker-denied] (apply held gate(now 4, worker worker-denied) writer [%verify claim proof]))
  ?>  ?=([%refused %proof-conflict] (apply held gate(now 4) writer [%verify claim proof(wire snapshot.current)]))
  ?>  ?=([%refused %denied] (apply held gate(now 4, allowed no-access) writer [%verify claim proof]))
  ?>  ?=([%committed %rejected %not-verified] (apply held gate(now 4) writer [%commit claim proof]))
  =/  verified  (apply held gate(now 4) writer [%verify claim proof])
  ?>  ?=([%pending %applied *] verified)
  =/  ready  next.result.verified
  ?>  ?=([%refused %worker-denied] (apply ready gate(now 5, worker worker-denied) writer [%commit claim proof]))
  ?>  ?=([%refused %denied] (apply ready gate(now 5, allowed no-access) writer [%commit claim proof]))
  ?>  ?=([%refused %denied] (apply ready gate(now 5, incarnation digest, worker worker-denied) writer [%commit claim proof]))
  =/  committed  (apply ready gate(now 5) writer [%commit claim proof])
  ?>  ?=([%committed %applied *] committed)
  ?>  =(pack current.next.result.committed)
  ~
++  test-pack-control-receipt-only-retries-with-new-credential
  ^-  tang
  =/  staged  (apply base gate writer [%admit claim ~])
  ?>  ?=([%pending %applied *] staged)
  =/  verified  (apply next.result.staged gate(now 4) writer [%verify claim proof])
  ?>  ?=([%pending %applied *] verified)
  =/  ready  next.result.verified
  ?>  ?=([%refused %denied] (apply ready gate(now 5) writer [%receipt claim proof]))
  =/  committed  (apply ready gate(now 5) writer [%commit claim proof])
  ?>  ?=([%committed %applied *] committed)
  =/  saved  next.result.committed
  =/  renewed  (issue:stead-code-credentials *ledger:stead-code-credentials who destination & 1.900.000 1.000.001 61 any-access)
  ?>  ?=(%& -.renewed)
  =/  worker-denied=worker-check  |=([admission checked] |)
  =/  fresh  gate(now 1.000.002, incarnation digest, book next.p.renewed, worker worker-denied)
  =/  bearer  bearer.p.renewed
  ?>  ?=([%refused %denied] (apply saved fresh writer [%receipt claim proof]))
  ?>  ?=([%refused %denied] (apply saved fresh bearer [%commit claim proof]))
  ?>  ?=([%refused %denied] (apply saved fresh bearer [%receipt claim proof(wire snapshot.current)]))
  ?>  ?=([%refused %denied] (apply saved fresh(sealed &) bearer [%receipt claim proof]))
  ?>  =([%committed %replayed saved result.result.committed] (apply saved fresh bearer [%receipt claim proof]))
  ~
--

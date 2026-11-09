/+  *test, stead-git, stead-codec, stead-session, stead-code-credentials, stead-code-git-objects, stead-code-git-graph, stead-code-receive, stead-code-ancestry, stead-code-store
=,  stead-code-store
=/  alice=actor  [~bus '019939ba-4000-7000-8000-000000000102' '019939ba-4000-7000-8000-000000000202' 1 & 2.000.000]
=/  bob=actor  [~nec '019939ba-4000-7000-8000-000000000103' '019939ba-4000-7000-8000-000000000203' 1 & 2.000.000]
=/  target=scope  [~zod '019939ba-4000-7000-8000-000000000301' '019939ba-4000-7000-8000-000000000302' 2]
=/  first-id=@t  '019939ba-4000-7000-8000-000000000401'
=/  next-id=@t  '019939ba-4000-7000-8000-000000000402'
=/  allowed=allowance:stead-code-credentials
  |=  [who=actor destination=scope operation=access:stead-code-credentials]
  &
=/  denied=allowance:stead-code-credentials
  |=  [who=actor destination=scope operation=access:stead-code-credentials]
  |
=/  member=membership:stead-code-credentials
  |=  ship=@p
  ^-  (unit actor)
  ?:  =(ship ~bus)  [~ alice]
  ?:  =(ship ~nec)  [~ bob]
  ~
=/  rotated=membership:stead-code-credentials
  |=  ship=@p
  ^-  (unit actor)
  [~ alice(revision 2)]
=/  policy=ref-policy
  |=  [who=actor destination=scope intent=action change=update]
  &
=/  no-ref=ref-policy
  |=  [who=actor destination=scope intent=action change=update]
  |
=/  issued  (issue:stead-code-credentials *ledger:stead-code-credentials alice target & 1.000.000 1.000 42 allowed)
?>  ?=(%& -.issued)
=/  book  next.p.issued
=/  bearer  bearer.p.issued
|%
++  make
  |=  [kind=@tas data=@t]
  ^-  object
  (need (hash-object:stead-code-git-objects kind [(met 3 data) data]))
++  blob
  (make %blob 'abc')
++  secret
  (make %blob 'private sibling content')
++  tree
  =/  prefix=@t  '100644 file.txt'
  =/  width=@ud  +((met 3 prefix))
  =/  body=octets:stead-git  [(add width 20) (can 3 ~[[width prefix] [20 (rev 3 20 oid:blob)]])]
  (need (hash-object:stead-code-git-objects %tree body))
++  first
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 'author Test <test@example.invalid> 1 +0000' 10 'committer Test <test@example.invalid> 1 +0000' 10 10 'first' 10]))
++  tip
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 'parent ' (oid-text:stead-git oid:first) 10 'author Test <test@example.invalid> 2 +0000' 10 'committer Test <test@example.invalid> 2 +0000' 10 10 'second' 10]))
++  tag
  (make %tag (rap 3 ~['object ' (oid-text:stead-git oid:tip) 10 'type commit' 10 'tag v1' 10 'tagger Test <test@example.invalid> 2 +0000' 10 10 'tag message' 10]))

++  seal
  |=  body=payload
  ^-  staged
  [(fingerprint body) body]
++  opening
  (seal [target first-id alice ~[['refs/heads/main' 0x0 oid:first]] ~[blob tree first]])
++  advancement
  (seal [target next-id alice ~[['refs/heads/main' oid:first oid:tip]] ~[tip]])
++  put
  |=  [db=state job=staged]
  ^-  state
  db(pending (~(put by pending.db) id.body.job job))
++  seed
  (put (empty target) opening)
++  run
  |=  [db=state id=@t digest=@t]
  ^-  result
  (accept db target book bearer id digest 1.001 member allowed policy ~)
++  base
  =/  outcome  (run seed first-id digest:opening)
  ?>  ?=(%applied -.outcome)
  next.outcome
++  advanced
  =/  outcome  (run (put base advancement) next-id digest:advancement)
  ?>  ?=(%applied -.outcome)
  next.outcome
++  rejected
  |=  [db=state outcome=result why=@tas]
  ^-  ?
  &(?=(%rejected -.outcome) =(db next.outcome) =(why reason.outcome))
++  fork
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 'author Test <test@example.invalid> 3 +0000' 10 'committer Test <test@example.invalid> 3 +0000' 10 10 'fork' 10]))
++  missing-tree
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git 0xdead) 10 'author Test <test@example.invalid> 3 +0000' 10 'committer Test <test@example.invalid> 3 +0000' 10 10 'missing' 10]))
++  filled
  =/  out=objects  ~
  =/  count=@ud  64
  |-  ^-  objects
  ?:  =(0 count)  out
  =/  value  (make %blob (cat 3 'quota' (decimal:stead-git count)))
  $(count (dec count), out (~(put by out) oid.value value))
++  test-store-apply-atomic
  =/  outcome  (run seed first-id digest:opening)
  ?>  ?=(%applied -.outcome)
  =/  db  next.outcome
  (expect !>(&(=(1 revision.db) =(3 ~(wyt by objects.db)) =([~ oid:first] (~(get by refs.db) 'refs/heads/main')) =(~ pending.db) =(~[first-id] journal.db) =(digest:opening digest.accepted.outcome))))
++  test-store-advance-parent-lineage
  =/  db  advanced
  (expect !>(&(=(2 revision.db) =(4 ~(wyt by objects.db)) =([~ oid:tip] (~(get by refs.db) 'refs/heads/main')) =(~[next-id first-id] journal.db))))
++  test-store-replay-exact
  =/  outcome  (run base first-id digest:opening)
  (expect !>(&(?=(%replayed -.outcome) =(base next.outcome) =(1 version.accepted.outcome) =(alice owner.accepted.outcome))))
++  test-store-replay-after-later-write
  =/  outcome  (run advanced first-id digest:opening)
  (expect !>(&(?=(%replayed -.outcome) =(advanced next.outcome) =(1 revision.accepted.outcome))))
++  test-store-revoked-before-replay
  =/  db  base
  (expect !>((rejected db (accept db target *ledger:stead-code-credentials bearer first-id digest:opening 1.001 member allowed policy ~) %denied)))
++  test-store-policy-revoked-before-replay
  =/  db  base
  (expect !>((rejected db (accept db target book bearer first-id digest:opening 1.001 member denied policy ~) %denied)))
++  test-store-binding-rotated-before-replay
  =/  db  base
  (expect !>((rejected db (accept db target book bearer first-id digest:opening 1.001 rotated allowed policy ~) %denied)))
++  test-store-expired-before-replay
  =/  db  base
  (expect !>((rejected db (accept db target book bearer first-id digest:opening 901.000 member allowed policy ~) %denied)))
++  test-store-current-ref-policy-before-replay
  =/  db  base
  (expect !>((rejected db (accept db target book bearer first-id digest:opening 1.001 member allowed no-ref ~) %denied)))
++  test-store-revoked-ref-hides-digest-mismatch
  =/  db  base
  (expect !>((rejected db (accept db target book bearer first-id (hash:stead-codec 'different' 'payload') 1.001 member allowed no-ref ~) %denied)))
++  test-store-receipt-owner-binding
  =/  original  base
  =/  accepted  (need (~(get by receipts.original) first-id))
  =/  db  original(receipts (~(put by receipts.original) first-id accepted(owner bob)))
  (expect !>((rejected db (run db first-id digest:opening) %denied)))
++  test-store-receipt-version
  =/  original  base
  =/  accepted  (need (~(get by receipts.original) first-id))
  =/  db  original(receipts (~(put by receipts.original) first-id accepted(version 2)))
  (expect !>((rejected db (run db first-id digest:opening) %denied)))
++  test-store-receipt-revision
  =/  original  base
  =/  accepted  (need (~(get by receipts.original) first-id))
  =/  db  original(receipts (~(put by receipts.original) first-id accepted(revision 2)))
  (expect !>((rejected db (run db first-id digest:opening) %denied)))
++  test-store-protected-before-replay
  =/  db  base
  (expect !>((rejected db (accept db target book bearer first-id digest:opening 1.001 member allowed policy (silt ~['refs/heads/main'])) %denied)))
++  test-store-request-id-reuse
  =/  db  base
  (expect !>((rejected db (run db first-id (hash:stead-codec 'different' 'payload')) %request-id-reused)))
++  test-store-version-denied
  =/  original  seed
  =/  db  original(version 2)
  (expect !>((rejected db (run db first-id digest:opening) %store-scope)))
++  test-store-current-epoch-denied
  =/  db  seed
  (expect !>((rejected db (accept db target(epoch 3) book bearer first-id digest:opening 1.001 member allowed policy ~) %denied)))
++  test-store-missing-stage
  =/  db  (empty target)
  (expect !>((rejected db (run db first-id digest:opening) %missing-stage)))
++  test-store-staged-owner
  =/  job  (seal [target first-id bob ~[['refs/heads/main' 0x0 oid:first]] ~[blob tree first]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %stage-scope)))
++  test-store-staged-other-repo
  =/  job  (seal [target(repository '019939ba-4000-7000-8000-000000000303') first-id alice ~[['refs/heads/main' 0x0 oid:first]] ~[blob tree first]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %stage-scope)))
++  test-store-staged-old-epoch
  =/  job  (seal [target(epoch 1) first-id alice ~[['refs/heads/main' 0x0 oid:first]] ~[blob tree first]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %stage-scope)))
++  test-store-unreachable-object
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 oid:first]] ~[blob tree first secret]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %unreachable-object)))
++  test-store-invalid-object
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 oid:first]] ~[blob tree [%commit [1 'x'] oid:first]]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %invalid-object)))
++  test-store-missing-graph-object
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 oid:missing-tree]] ~[missing-tree]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %invalid-graph)))
++  test-store-wrong-branch-kind
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 oid:blob]] ~[blob]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %wrong-object-kind)))
++  test-store-no-target-object
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 0xdead]] ~])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %missing-object)))
++  test-store-stage-byte-quota
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 0x1]] ~[[%blob [65.537 0] 0x1]]])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %stage-bound)))
++  test-store-stage-count-quota
  =/  job  (seal [target first-id alice ~[['refs/heads/main' 0x0 oid:first]] (reap 17 blob)])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %stage-bound)))
++  test-store-empty-ref-command
  =/  job  (seal [target first-id alice ~ ~])
  =/  db  (put (empty target) job)
  (expect !>((rejected db (run db first-id digest.job) %empty-update)))
++  test-store-stored-digest-tamper
  =/  job  opening
  =/  altered  job(digest (hash:stead-codec 'other' 'payload'))
  =/  db  (put (empty target) altered)
  (expect !>((rejected db (run db first-id digest.altered) %stage-digest)))
++  test-store-payload-tamper
  =/  job  opening
  =/  altered  job(body body.job(changes ~[['refs/heads/other' 0x0 oid:first]]))
  =/  db  (put (empty target) altered)
  (expect !>((rejected db (run db first-id digest:opening) %stage-digest)))
++  test-store-non-fast-forward
  =/  job  (seal [target next-id alice ~[['refs/heads/main' oid:first oid:fork]] ~[fork]])
  =/  db  (put base job)
  (expect !>((rejected db (run db next-id digest.job) %non-fast-forward)))
++  test-store-ref-race
  =/  job  (seal [target next-id alice ~[['refs/heads/main' oid:first oid:fork]] ~[fork]])
  =/  fresh-id=@t  '019939ba-4000-7000-8000-000000000403'
  =/  job  (seal body.job(id fresh-id))
  =/  db  (put advanced job)
  (expect !>((rejected db (run db fresh-id digest.job) %stale-ref)))
++  test-store-multi-ref-failure-is-identical
  =/  job  (seal [target next-id alice ~[['refs/heads/feature' 0x0 oid:tip] ['refs/heads/main' 0x0 oid:tip]] ~[tip]])
  =/  db  (put base job)
  (expect !>((rejected db (run db next-id digest.job) %stale-ref)))
++  test-store-protected-create
  =/  job  opening
  =/  db  (put (empty target) job)
  (expect !>((rejected db (accept db target book bearer id.body.job digest.job 1.001 member allowed policy (silt ~['refs/heads/main'])) %denied)))
++  test-store-protected-advance
  =/  job  advancement
  =/  db  (put base job)
  (expect !>((rejected db (accept db target book bearer id.body.job digest.job 1.001 member allowed policy (silt ~['refs/heads/main'])) %denied)))
++  test-store-protected-delete
  =/  job  (seal [target next-id alice ~[['refs/heads/main' oid:first 0x0]] ~])
  =/  db  (put base job)
  (expect !>((rejected db (accept db target book bearer id.body.job digest.job 1.001 member allowed policy (silt ~['refs/heads/main'])) %denied)))
++  test-store-collision-rejects-whole-state
  ::  Deliberately inconsistent prior storage, not a discovered SHA-1 collision.
  =/  original  (empty target)
  =/  wrong=object  [%blob [1 'x'] oid:blob]
  =/  db  (put original(objects (~(put by objects.original) oid:blob wrong)) opening)
  (expect !>((rejected db (run db first-id digest:opening) %oid-collision)))
++  test-store-repository-object-quota
  =/  original  (empty target)
  =/  db  (put original(objects filled) opening)
  (expect !>((rejected db (run db first-id digest:opening) %object-capacity)))
++  test-store-delete-atomic
  =/  job  (seal [target next-id alice ~[['refs/heads/main' oid:first 0x0]] ~])
  =/  db  (put base job)
  =/  outcome  (run db next-id digest.job)
  ?>  ?=(%applied -.outcome)
  (expect !>(&(=(~ refs.next.outcome) =(objects:base objects.next.outcome) =(2 revision.next.outcome))))
++  test-store-version-one-noun-roundtrip
  =/  db  advanced
  =/  restored  (cue (jam db))
  (expect !>(=(db restored)))
++  failure-control
  (expect !>(%.n))
--

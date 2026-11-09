/+  *test, stead-git, stead-code-credentials, stead-code-delivery, stead-code-git-objects, stead-code-store, stead-code-review-home
=,  stead-code-review-home
=/  where=scope  [~zod '019939ba-4000-7000-8000-000000000100' '019939ba-4000-7000-8000-000000000200' 1]
=/  work-id=@t  '019939ba-4000-7000-8000-000000000300'
=/  proposal-id=@t  '019939ba-4000-7000-8000-000000000400'
=/  grant-id=@t  '019939ba-4000-7000-8000-000000000500'
=/  seed-id=@t  '019939ba-4000-7000-8000-000000000600'
=/  merge-id=@t  '019939ba-4000-7000-8000-000000000700'
=/  retry-id=@t  '019939ba-4000-7000-8000-000000000800'
=/  main=@t  'refs/heads/main'
=/  topic=@t  'refs/heads/topic'
=/  next-ref=@t  'refs/heads/next'
=/  maker=actor  [~bus '019939ba-4000-7000-8000-000000001001' '019939ba-4000-7000-8000-000000002001' 1 & 1.000.000]
=/  worker=actor  [~nec '019939ba-4000-7000-8000-000000001002' '019939ba-4000-7000-8000-000000002002' 1 & 1.000.000]
=/  critic=actor  [~bud '019939ba-4000-7000-8000-000000001003' '019939ba-4000-7000-8000-000000002003' 1 & 1.000.000]
=/  custodian=actor  [~wes '019939ba-4000-7000-8000-000000001004' '019939ba-4000-7000-8000-000000002004' 1 & 1.000.000]
=/  reader=actor  [~sev '019939ba-4000-7000-8000-000000001005' '019939ba-4000-7000-8000-000000002005' 1 & 1.000.000]
=/  outsider=actor  [~per '019939ba-4000-7000-8000-000000001006' '019939ba-4000-7000-8000-000000002006' 1 & 1.000.000]
=/  protected=(set @t)  (silt ~[main])
|%
++  member
  |=  ship=@p
  ^-  (unit actor)
  ?:  =(ship ship.maker)      [~ maker]
  ?:  =(ship ship.worker)     [~ worker]
  ?:  =(ship ship.critic)     [~ critic]
  ?:  =(ship ship.custodian)  [~ custodian]
  ?:  =(ship ship.reader)     [~ reader]
  ~
++  policy
  |=  [who=actor loc=scope work=@t target=@t role=role:stead-code-delivery]
  ^-  ?
  ?.  &(=(loc where) =(work work-id) =(target main))  |
  ?+  role  |
    %delegate       =(who custodian)
    %propose        =(who maker)
    %agent-propose  =(who worker)
    %review         |(=(who critic) =(who maker))
    %merge          |(=(who custodian) =(who maker))
  ==
++  allowed
  |=  [who=actor loc=scope access=access:stead-code-credentials]
  ^-  ?
  &(=(loc where) =(who maker))
++  env
  ^-  authority
  :*  where
      100
      member
      policy
      |=([who=actor item=proposal] *(unit @t))
      |=(target=@t 0x0)
      |=([loc=scope recipe=@t] |)
      |=([loc=scope item=proposal] |)
      |=([loc=scope id=@t item=proposal number=@ud who=actor attestation=attestation:stead-code-delivery] |)
  ==
++  without
  |=  blocked=role:stead-code-delivery
  ^-  authority
  =/  limited=permit:stead-code-delivery
    |=  [who=actor loc=scope work=@t target=@t role=role:stead-code-delivery]
    &(!=(blocked role) (policy who loc work target role))
  =/  context=authority  env
  context(allows limited)
++  make
  |=  [kind=@tas text=@t]
  ^-  object:stead-code-store
  (need (hash-object:stead-code-git-objects kind [(met 3 text) text]))
++  tree
  (make %tree '')
++  commit
  |=  [parent=@ux text=@t]
  ^-  object:stead-code-store
  =/  prefix  ?:  =(0 parent)  ''
    (rap 3 ~['parent ' (oid-text:stead-git parent) 10])
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 prefix 'author Test <test@example.invalid> 1 +0000' 10 'committer Test <test@example.invalid> 1 +0000' 10 10 text 10]))
++  base
  (commit 0x0 'base')
++  head
  (commit oid:base 'head')
++  newer
  (commit oid:head 'newer')
++  orphan
  (commit 0x0 'unreachable')
++  proposal-row
  ^-  proposal
  [proposal-id principal.maker [project.where repository.where main] work-id [epoch.where 1 oid:base oid:head]]
++  credentials
  =/  issued  (issue:stead-code-credentials *ledger:stead-code-credentials maker where & 1.000 100 42 allowed)
  ?>  ?=(%& -.issued)
  p.issued
++  seed
  ^-  repo-state
  =/  opening=payload:stead-code-store
    [where seed-id maker ~[[main 0x0 oid:base] [topic 0x0 oid:head] [next-ref 0x0 oid:newer]] ~[tree base head newer]]
  =/  digest  (fingerprint:stead-code-store opening)
  =/  db  (empty:stead-code-store where)
  =.  pending.db  (~(put by pending.db) seed-id [digest opening])
  =/  committed
    (accept:stead-code-store db where next:credentials bearer:credentials seed-id digest 100 member allowed |=([who=actor loc=scope action=action:stead-code-store delta=update:stead-code-store] &) ~)
  ?>  ?=(%applied -.committed)
  next.committed
++  run
  |=  [db=state repo=repo-state who=actor action=command]
  ^-  result
  (perform db repo protected env who action)
++  start
  (empty where)
++  submitted
  =/  got  (run start seed maker [%submit proposal-row ~])
  ?>  ?=(%applied -.got)
  next.got
++  approved
  =/  got  (run submitted seed critic [%approve proposal-id 1])
  ?>  ?=(%applied -.got)
  next.got
++  merged
  =/  got  (run approved seed custodian [%merge proposal-id 1 merge-id])
  ?>  ?=(%applied -.got)
  got
++  viewer
  |=  [who=actor loc=scope work=@t target=@t]
  ^-  ?
  &(=(who reader) =(loc where) =(work work-id) =(target main))
++  test-review-home-submit-replay
  =/  got  (run submitted seed maker [%submit proposal-row ~])
  (expect !>(=([%replayed submitted seed ~] got)))
++  test-review-home-unreachable-head
  =/  repo  seed
  =.  objects.repo  (~(put by objects.repo) oid:orphan orphan)
  =/  item  proposal-row
  =.  head.change.item  oid:orphan
  (expect !>(=([%rejected %unavailable] (run start repo maker [%submit item ~]))))
++  test-review-home-unauthorized-submit
  (expect !>(=([%rejected %denied] (run start seed outsider [%submit proposal-row ~]))))
++  test-review-home-self-review
  (expect !>(=([%rejected %self-review] (run submitted seed maker [%approve proposal-id 1]))))
++  test-review-home-merge-requires-exact-approval
  (expect !>(=([%rejected %review-required-or-denied] (run submitted seed custodian [%merge proposal-id 1 merge-id]))))
++  test-review-home-self-merge
  (expect !>(=([%rejected %denied] (run approved seed maker [%merge proposal-id 1 merge-id]))))
++  test-review-home-atomic-receipt
  =/  original=repo-state  seed
  =/  got  merged
  =/  committed  (need receipt.got)
  =/  correct=?
    ?&  =(2 revision.repo.got)
        =(2 revision.committed)
        =(custodian owner.committed)
        =(~[merge-id seed-id] journal.repo.got)
        =([~ oid:head] (~(get by refs.repo.got) main))
        =([~ oid:head] (~(get by refs.repo.got) topic))
        =([~ [proposal-id 1]] (~(get by merges.next.got) merge-id))
        =([~ committed] (~(get by receipts.repo.got) merge-id))
        =(objects.original objects.repo.got)
        (validate-saved next.got repo.got)
    ==
  (expect !>(correct))
++  test-review-home-stock-protected-write-denied
  =/  payload=payload:stead-code-store  [where merge-id maker ~[[main oid:base oid:head]] ~]
  =/  digest  (fingerprint:stead-code-store payload)
  =/  repo  seed
  =.  pending.repo  (~(put by pending.repo) merge-id [digest payload])
  =/  result
    (accept:stead-code-store repo where next:credentials bearer:credentials merge-id digest 100 member allowed |=([who=actor loc=scope action=action:stead-code-store delta=update:stead-code-store] &) protected)
  (expect !>(&(?=(%rejected -.result) =(repo next.result))))
++  test-review-home-stale-tip
  (expect !>(=([%rejected %stale-target] (run approved repo:merged custodian [%merge proposal-id 1 retry-id]))))
++  test-review-home-revoked-reviewer
  =/  blocked  (without %review)
  (expect !>(=([%rejected %review-required-or-denied] (perform approved seed protected blocked custodian [%merge proposal-id 1 merge-id]))))
++  test-review-home-revoked-author-on-replay
  =/  got  merged
  =/  blocked  (without %propose)
  (expect !>(=([%rejected %denied] (perform next.got repo.got protected blocked custodian [%merge proposal-id 1 merge-id]))))
++  test-review-home-replay-after-revision-and-target-advance
  =/  first  merged
  =/  item  proposal-row
  =.  change.item  [epoch.where 2 oid:head oid:newer]
  =/  again  (run next.first repo.first maker [%submit item ~])
  ?>  ?=(%applied -.again)
  =/  review  (run next.again repo.again critic [%approve proposal-id 2])
  ?>  ?=(%applied -.review)
  =/  second  (run next.review repo.review custodian [%merge proposal-id 2 retry-id])
  ?>  ?=(%applied -.second)
  =/  replay  (run next.second repo.second custodian [%merge proposal-id 1 merge-id])
  (expect !>(=([%replayed next.second repo.second receipt.first] replay)))
++  test-review-home-delegation-revocation
  =/  granted  (run start seed custodian [%delegate grant-id ship.worker work-id main 200])
  ?>  ?=(%applied -.granted)
  =/  item  proposal-row
  =.  author.item  principal.worker
  =/  proposed  (run next.granted seed worker [%submit item [~ grant-id]])
  ?>  ?=(%applied -.proposed)
  =/  reviewed  (run next.proposed seed critic [%approve proposal-id 1])
  ?>  ?=(%applied -.reviewed)
  =/  revoked  (run next.reviewed seed custodian [%revoke grant-id])
  ?>  ?=(%applied -.revoked)
  (expect !>(=([%rejected %denied] (run next.revoked seed custodian [%merge proposal-id 1 merge-id]))))
++  test-review-home-saved-roundtrip-and-corruption
  =/  got  merged
  =/  saved=state  (state (cue (jam next.got)))
  =/  corrupted  saved(merges (~(put by merges.saved) retry-id [proposal-id 1]))
  (expect !>(&((validate-saved saved repo.got) !(validate-saved corrupted repo.got))))
++  test-review-home-authorized-lookup
  =/  got  merged
  =/  looked  (lookup next.got repo.got env reader viewer proposal-id 1)
  =/  denied  (lookup next.got repo.got env outsider viewer proposal-id 1)
  (expect !>(&(=([~ proposal-row [~ principal.critic] [~ 2]] looked) =(~ denied))))
++  failure-control
  (expect !>(%.n))
--

/+  *test, stead-codec, stead-code-pack-anchor, stead-code-pack-push, stead-code-pack-ledger, stead-code-receive, stead-session, stead-code-git-graph, stead-git
=,  stead-code-pack-ledger
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  destination=scope  [~zod project project 1]
=/  request=@t  '019939ba-4000-7000-8000-000000000004'
=/  bootstrap=@t  '019939ba-4000-7000-8000-000000000006'
=/  digest=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  main=@t  'refs/heads/main'
=/  tag=@t  'refs/tags/v1'
=/  exact-ref=@t  (cat 3 'refs/heads/topic-' 0xff)
=/  main-key  (bytes-hex:stead-codec main)
=/  tag-key  (bytes-hex:stead-codec tag)
=/  exact-key  '726566732f68656164732f746f7069632dff'
=/  seal
  |=  input=manifest
  ^-  manifest
  =/  raw  (snapshot-bytes:stead-code-pack-anchor input)
  =/  size  (met 3 raw)
  input(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
=/  current=manifest
  %-  seal
  :*  destination  ''  main-key
      (malt ~[[main-key (oid-text:stead-git 0x11)] [exact-key (oid-text:stead-git 0x11)]])
      digest  400  3  500  digest
  ==
=/  pack=manifest
  =/  refs=(map @t @t)
    (malt ~[[main-key (oid-text:stead-git 0x22)] [tag-key (oid-text:stead-git 0x33)] [exact-key (oid-text:stead-git 0x22)]])
  (seal current(refs refs, objects 6))
=/  kinds=(list [@ux object-kind:stead-code-git-graph])
  ~[[0x22 %commit] [0x33 %tag]]
=/  proof=checked
  :*  destination  snapshot.current  0  digest  request
      ~[[tag 0x0 0x33] [exact-ref 0x11 0x22] [main 0x11 0x22]]
      pack  (malt kinds)  (silt ~[[0x11 0x22]])
  ==
=/  allow-all=allow  |=([action:stead-code-receive update] &)
=/  deny-all=allow  |=([action:stead-code-receive update] |)
=/  who=actor
  [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
=/  anchor=entry:stead-code-pack-anchor
  [%accepted [current ~zod 1 900.001] [bootstrap who 2]]
=/  db  (need (open anchor))
=/  claim=intent
  [destination snapshot.current 0 digest request 1 snapshot.pack changes.proof]
|%
++  test-pack-ledger-stages-verifies-and-commits-atomically
  =/  staged  (admit db claim who 3 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.staged)
  =/  verified  (verify next.staged claim proof who 4 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.verified)
  =/  accepted  (commit next.verified claim proof who 5 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.accepted)
  =/  loaded=ledger  (ledger (cue (jam next.accepted)))
  =/  ok=?
    ?&  =(current.next.staged current)
        =(current.next.verified current)
        =(~[request] journal.loaded)
        =(generation.loaded 1)
        ?=(~ pending.loaded)
        =(current.loaded pack)
        (valid loaded anchor)
        =(loaded next.accepted)
    ==
  (expect !>(ok))
++  test-pack-ledger-replays-exact-attempt-with-current-authority
  =/  staged  (admit db claim who 3 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.staged)
  =/  verified  (verify next.staged claim proof who 4 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.verified)
  =/  accepted  (commit next.verified claim proof who 5 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.accepted)
  =/  saved  next.accepted
  =/  moved  pack(destination destination(epoch 2))
  =/  moved-db  saved(current moved)
  =/  ok=?
    ?&  =([%replayed saved result.accepted] (commit saved claim proof who 6 digest allow-all ~))
        ?=([%rejected %denied] (commit saved claim proof who 6 digest deny-all ~))
        ?=([%rejected %denied] (commit saved claim proof who(active |) 6 digest allow-all ~))
        ?=([%rejected %denied] (commit saved claim proof who 6 digest allow-all (silt ~[main])))
        ?=([%rejected %scope-conflict] (commit moved-db claim proof who 6 digest allow-all ~))
        ?=([%rejected %request-reused] (commit saved claim(attempt 2) proof who 6 digest allow-all ~))
        ?=([%rejected %request-reused] (commit saved claim proof who(revision 2) 6 digest allow-all ~))
        ?=([%rejected %request-reused] (commit saved claim proof(wire snapshot.current) who 6 digest allow-all ~))
    ==
  (expect !>(ok))
++  test-pack-ledger-checks-expiry-incarnation-and-final-policy
  =/  staged  (admit db claim who 3 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.staged)
  =/  held  next.staged
  =/  verified  (verify held claim proof who 4 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.verified)
  =/  ready  next.verified
  =/  replacement  claim(attempt 2, incarnation digest)
  =/  reopened  (admit ready replacement who 300.003 digest allow-all ~)
  ?>  ?=(%applied -.reopened)
  =/  ok=?
    ?&  ?=([%rejected %not-verified] (commit held claim proof who 5 incarnation.claim allow-all ~))
        ?=([%rejected %incarnation-conflict] (commit ready claim proof who 5 digest allow-all ~))
        ?=([%rejected %denied] (commit ready claim proof who 5 incarnation.claim deny-all ~))
        ?=([%rejected %attempt-conflict] (commit ready claim proof who 300.003 incarnation.claim allow-all ~))
        ?=([%rejected %proof-conflict] (verify held claim proof(wire snapshot.current) who 4 incarnation.claim allow-all ~))
        ?=([%admitted *] (need pending.next.reopened))
        (valid ready anchor)
        (valid next.reopened anchor)
    ==
  (expect !>(ok))
++  test-pack-ledger-rebuilds-lineage-and-refuses-corrupt-receipts
  =/  staged  (admit db claim who 3 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.staged)
  =/  verified  (verify next.staged claim proof who 4 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.verified)
  =/  accepted  (commit next.verified claim proof who 5 incarnation.claim allow-all ~)
  ?>  ?=(%applied -.accepted)
  =/  saved  next.accepted
  =/  found  (~(got by receipts.saved) request)
  =/  changed  found(result result.found(version 2))
  =/  invalid-ledger  saved(receipts (~(put by receipts.saved) request changed))
  =/  other-anchor=entry:stead-code-pack-anchor
    [%accepted [current ~zod 1 900.001] [request who 2]]
  =/  ok=?
    ?&  (valid saved anchor)
        !(valid saved(current current) anchor)
        !(valid saved(journal ~) anchor)
        !(valid saved(last 4) anchor)
        !(valid invalid-ledger anchor)
        !(valid saved other-anchor)
    ==
  (expect !>(ok))
--

/+  *test, stead-codec, stead-code-pack-anchor, stead-code-pack-push, stead-code-receive, stead-session, stead-code-git-graph, stead-git
=,  stead-code-pack-push
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  destination=scope  [~zod project project 1]
=/  request=@t  '019939ba-4000-7000-8000-000000000004'
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
=/  checked=evidence
  :*  destination  snapshot.current  0  digest  request
      ~[[tag 0x0 0x33] [exact-ref 0x11 0x22] [main 0x11 0x22]]
      pack  (malt kinds)  (silt ~[[0x11 0x22]])
  ==
=/  allow  |=([action:stead-code-receive update] &)
=/  deny  |=([action:stead-code-receive update] |)
|%
++  test-pack-push-keeps-order-and-advances-once
  =/  result  (decide destination 0 current checked ~ allow)
  ?>  ?=(%candidate -.result)
  =/  ok=?
    ?&  =(changes.next.result changes.checked)
        =(generation.next.result 1)
        =(base.next.result snapshot.current)
        =(pack.next.result pack)
        =(wire.next.result digest)
        =(request.next.result request)
        =((bytes-hex:stead-codec exact-ref) exact-key)
        ?=([%rejected %generation-conflict] (decide destination 1 pack checked ~ allow))
    ==
  (expect !>(ok))
++  test-pack-push-compares-scope-snapshot-and-prior-oids
  =/  stale  checked(changes ~[[tag 0x0 0x33] [main 0x55 0x22]])
  =/  ok=?
    ?&  ?=([%rejected %scope-conflict] (decide destination(epoch 2) 0 current checked ~ allow))
        ?=([%rejected %snapshot-conflict] (decide destination 0 current checked(base digest) ~ allow))
        ?=([%rejected %stale-ref] (decide destination 0 current stale ~ allow))
        ?=([%rejected %generation-conflict] (decide destination 18.446.744.073.709.551.615 current checked(generation 18.446.744.073.709.551.615) ~ allow))
    ==
  (expect !>(ok))
++  test-pack-push-denies-protected-delete-duplicate-and-unverified
  =/  removed  checked(changes ~[[main 0x11 0x0]])
  =/  duplicate  checked(changes ~[[main 0x11 0x22] [main 0x11 0x22]])
  =/  ok=?
    ?&  ?=([%rejected %denied] (decide destination 0 current checked ~ deny))
        ?=([%rejected %protected-ref] (decide destination 0 current checked (silt ~[main]) allow))
        ?=([%rejected %delete-unsupported] (decide destination 0 current removed ~ allow))
        ?=([%rejected %duplicate-ref] (decide destination 0 current duplicate ~ allow))
        ?=([%rejected %missing-object] (decide destination 0 current checked(kinds ~) ~ allow))
        ?=([%rejected %non-fast-forward] (decide destination 0 current checked(lineage ~) ~ allow))
    ==
  (expect !>(ok))
++  test-pack-push-denies-hidden-ref-change-and-tag-replacement
  =/  hidden  checked(changes ~[[main 0x11 0x22]])
  =/  extra  checked(changes ~[['refs/heads/main/nested' 0x0 0x22]])
  =/  published=manifest
    (seal current(refs (~(put by refs.current) tag-key (oid-text:stead-git 0x44))))
  =/  replace
    checked(base snapshot.published, changes ~[[tag 0x44 0x33] [main 0x11 0x22]])
  =/  ok=?
    ?&  ?=([%rejected %manifest-conflict] (decide destination 0 current hidden ~ allow))
        ?=([%rejected %ref-conflict] (decide destination 0 current extra ~ allow))
        ?=([%rejected %tag-replacement] (decide destination 0 published replace ~ allow))
    ==
  (expect !>(ok))
++  test-pack-push-receipt-is-a-separate-versioned-record
  =/  result  (decide destination 0 current checked ~ allow)
  ?>  ?=(%candidate -.result)
  =/  who=actor:stead-session
    [~bus '019939ba-4000-7000-8000-000000000002' '019939ba-4000-7000-8000-000000000003' 1 & 2.000.000]
  =/  recorded=receipt  [1 next.result who 5]
  (expect !>(=(recorded (receipt (cue (jam recorded))))))
--

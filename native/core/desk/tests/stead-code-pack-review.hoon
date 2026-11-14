::  Synthetic pure-contract cases, not stock-object or saved-state evidence.
/+  *test, stead-codec, stead-code-pack-review, stead-code-pack-anchor, stead-code-pack-push, stead-code-review, stead-code-credentials, stead-code-receive, stead-code-git-graph, stead-session, stead-git
=,  stead-code-pack-review
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  work-id=@t  '019939ba-4000-7000-8000-000000000010'
=/  proposal-id=@t  '019939ba-4000-7000-8000-000000000011'
=/  other-id=@t  '019939ba-4000-7000-8000-000000000012'
=/  request=@t  '019939ba-4000-7000-8000-000000000013'
=/  destination=scope  [~zod project project 1]
=/  digest=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  main=@t  'refs/heads/main'
=/  source=@t  (cat 3 'refs/heads/topic-' 0xff)
=/  main-key  (bytes-hex:stead-codec main)
=/  source-key  '726566732f68656164732f746f7069632dff'
=/  maker=actor  [~bus '019939ba-4000-7000-8000-000000001001' '019939ba-4000-7000-8000-000000002001' 1 & 1.000.000]
=/  critic=actor  [~nec '019939ba-4000-7000-8000-000000001002' '019939ba-4000-7000-8000-000000002002' 1 & 1.000.000]
=/  maintainer=actor  [~bud '019939ba-4000-7000-8000-000000001003' '019939ba-4000-7000-8000-000000002003' 1 & 1.000.000]
=/  reader=actor  [~wes '019939ba-4000-7000-8000-000000001004' '019939ba-4000-7000-8000-000000002004' 1 & 1.000.000]
=/  outsider=actor  [~sev '019939ba-4000-7000-8000-000000001005' '019939ba-4000-7000-8000-000000002005' 1 & 1.000.000]
=/  home-actor=actor  [~zod '019939ba-4000-7000-8000-000000001006' '019939ba-4000-7000-8000-000000002006' 1 & 1.000.000]
=/  seal
  |=  input=manifest
  ^-  manifest
  =/  raw  (snapshot-bytes:stead-code-pack-anchor input)
  =/  size  (met 3 raw)
  input(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
=/  current=manifest
  %-  seal
  :*  destination  ''  main-key
      (malt ~[[main-key (oid-text:stead-git 0x11)] [source-key (oid-text:stead-git 0x22)]])
      digest  400  3  500  digest
  ==
=/  promoted=manifest
  (seal current(refs (~(put by refs.current) main-key (oid-text:stead-git 0x22))))
=/  checked=evidence:stead-code-pack-push
  :*  destination  snapshot.current  0  digest  request
      ~[[main 0x11 0x22]]  promoted
      (malt ~[[0x22 %commit]])  (silt ~[[0x11 0x22]])
  ==
=/  item=proposal:stead-code-review
  [proposal-id principal.maker [project project main] work-id [1 1 0x11 0x22]]
|%
++  membership
  |=  ship=@p
  ^-  (unit actor)
  ?:  =(ship ship.maker)       [~ maker]
  ?:  =(ship ship.critic)      [~ critic]
  ?:  =(ship ship.maintainer)  [~ maintainer]
  ?:  =(ship ship.reader)      [~ reader]
  ::  Even a permissive resolver must not confer content authority on Home.
  ?:  =(ship ship.home-actor)  [~ home-actor]
  ~
++  policy
  |=  [who=actor where=scope work=@t target=@t capability=role]
  ^-  ?
  ?.  &(=(where destination) =(work work-id) =(target main))  |
  ?-  capability
    %propose  =(who maker)
    %review   =(who critic)
    %merge    =(who maintainer)
  ==
++  env
  ^-  authority
  [destination 100 membership policy]
++  permissive
  ^-  authority
  =/  context=authority  env
  =/  all=permit
    |=  [who=actor where=scope work=@t target=@t capability=role]
    &(=(where destination) =(work work-id) =(target main))
  context(allows all)
++  without-member
  |=  ship=@p
  ^-  authority
  =/  context=authority  env
  =/  remaining=membership:stead-code-credentials
    |=  requested=@p
    ?:  =(ship requested)  ~
    (membership requested)
  context(resolve remaining)
++  without-role
  |=  removed=role
  ^-  authority
  =/  context=authority  env
  =/  remaining=permit
    |=  [who=actor where=scope work=@t target=@t capability=role]
    &(!=(removed capability) (policy who where work target capability))
  context(allows remaining)
++  row
  ^-  proposal
  =/  result  (propose env 0 current maker source item)
  ?>  ?=(%& -.result)
  p.result
++  reviewed
  ^-  approval
  =/  result  (approve env 0 current critic row)
  ?>  ?=(%& -.result)
  p.result
++  test-pack-review-exact-selected-candidate
  =/  pinned=proposal  row
  =/  accepted=approval  reviewed
  =/  result  (preflight env 0 current maintainer row reviewed checked)
  ?>  ?=(%& -.result)
  =/  next  p.result
  =/  raw-allow  |=([action:stead-code-receive update:stead-code-receive] &)
  =/  ok=?
    ?&  =(snapshot.pinned snapshot.current)
        =(source.pinned source)
        =((bytes-hex:stead-codec source) source-key)
        =(reviewed.accepted pinned)
        =(review.next reviewed)
        =(merger.next maintainer)
        =(changes.decision.next ~[[main 0x11 0x22]])
        =(generation.decision.next 1)
        =(base.decision.next snapshot.current)
        =(pack.decision.next promoted)
        =(wire.decision.next digest)
        =(request.decision.next request)
        ?=([%rejected %protected-ref] (decide:stead-code-pack-push destination 0 current checked (silt ~[main]) raw-allow))
    ==
  (expect !>(ok))
++  test-pack-review-pins-proposal-source-and-target
  =/  wrong-base  item(change change.item(base 0x33))
  =/  unknown-head  item(change change.item(head 0x33))
  =/  wrong-target  item(location location.item(target source))
  =/  wrong-project  item(location location.item(project other-id))
  =/  wrong-repo  item(location location.item(repo other-id))
  =/  wrong-epoch  item(change change.item(epoch 2))
  =/  ok=?
    ?&  ?=([%| %stale-target] (propose env 0 current maker source wrong-base))
        ?=([%| %source-conflict] (propose env 0 current maker source unknown-head))
        ?=([%| %source-conflict] (propose env 0 current maker 'refs/heads/missing' item))
        ?=([%| %invalid-proposal] (propose env 0 current maker 'refs/tags/v1' item))
        ?=([%| %invalid-proposal] (propose env 0 current maker source wrong-target))
        ?=([%| %invalid-proposal] (propose env 0 current maker source wrong-project))
        ?=([%| %invalid-proposal] (propose env 0 current maker source wrong-repo))
        ?=([%| %invalid-proposal] (propose env 0 current maker source wrong-epoch))
        ?=([%| %invalid-proposal] (propose env 0 current maker source item(author principal.critic)))
    ==
  (expect !>(ok))
++  test-pack-review-approval-binds-whole-proposal
  =/  pinned=proposal  row
  =/  accepted=approval  reviewed
  =/  changed-id  pinned(item item(id other-id))
  =/  changed-work  pinned(item item(work other-id))
  =/  changed-number  pinned(item item(change change.item(number 2)))
  =/  changed-source  pinned(source 'refs/heads/other')
  =/  changed-snapshot  pinned(snapshot digest)
  =/  changed-generation  pinned(generation 1)
  =/  changed-owner  pinned(owner maker(binding other-id))
  =/  ok=?
    ?&  ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-id) checked))
        ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-work) checked))
        ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-number) checked))
        ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-source) checked))
        ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-snapshot) checked))
        ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-generation) checked))
        ?=([%| %stale-review] (preflight env 0 current maintainer row accepted(reviewed changed-owner) checked))
        ?=([%| %invalid-approval] (preflight env 0 current maintainer row accepted(approved-at 101) checked))
        ?=([%| %invalid-approval] (preflight env 0 current maintainer row accepted(approved-at 0) checked))
    ==
  (expect !>(ok))
++  test-pack-review-rechecks-members-policy-and-owner-separation
  =/  context=authority  env
  =/  accepted=approval  reviewed
  =/  self-reviewed  accepted(reviewer maker)
  =/  home-reviewed  accepted(reviewer home-actor)
  =/  ok=?
    ?&  ?=([%| %denied] (propose permissive 0 current home-actor source item(author principal.home-actor)))
        ?=([%| %denied] (approve permissive 0 current home-actor row))
        ?=([%| %denied] (preflight permissive 0 current home-actor row reviewed checked))
        ?=([%| %denied] (preflight permissive 0 current maintainer row home-reviewed checked))
        ?=([%| %self-review] (approve permissive 0 current maker row))
        ?=([%| %self-review] (preflight permissive 0 current maintainer row self-reviewed checked))
        ?=([%| %self-merge] (preflight permissive 0 current maker row reviewed checked))
        ?=([%| %denied] (approve env 0 current reader row))
        ?=([%| %denied] (approve permissive 0 current outsider row))
        ?=([%| %denied] (preflight (without-member ship.maker) 0 current maintainer row reviewed checked))
        ?=([%| %denied] (preflight (without-member ship.critic) 0 current maintainer row reviewed checked))
        ?=([%| %denied] (preflight (without-member ship.maintainer) 0 current maintainer row reviewed checked))
        ?=([%| %denied] (preflight (without-role %propose) 0 current maintainer row reviewed checked))
        ?=([%| %denied] (preflight (without-role %review) 0 current maintainer row reviewed checked))
        ?=([%| %denied] (preflight (without-role %merge) 0 current maintainer row reviewed checked))
        ?=([%| %denied] (preflight env 0 current maintainer(binding other-id) row reviewed checked))
        ?=([%| %denied] (preflight env 0 current maintainer row accepted(reviewer critic(revision 2)) checked))
        ?=([%| %denied] (preflight context(now 1.000.000) 0 current maintainer row reviewed checked))
    ==
  (expect !>(ok))
++  test-pack-review-rejects-stale-selection-and-worker-scope
  =/  context=authority  env
  =/  pinned=proposal  row
  =/  moved=manifest
    (seal current(refs (~(put by refs.current) source-key (oid-text:stead-git 0x33))))
  =/  advanced=authority  context(destination destination(epoch 2))
  =/  ok=?
    ?&  ?=([%| %stale-selection] (approve env 1 current critic row))
        ?=([%| %stale-selection] (preflight env 0 moved maintainer row reviewed checked))
        ?=([%| %invalid-selection] (preflight advanced 0 current maintainer row reviewed checked))
        ?=([%| %stale-selection] (approve env 0 current critic pinned(destination destination(epoch 2))))
        ?=([%| %snapshot-conflict] (preflight env 0 current maintainer row reviewed checked(base digest)))
        ?=([%| %generation-conflict] (preflight env 0 current maintainer row reviewed checked(generation 1)))
        ?=([%| %scope-conflict] (preflight env 0 current maintainer row reviewed checked(destination destination(epoch 2))))
        ?=([%| %invalid-candidate] (preflight env 0 current maintainer row reviewed checked(request 'bad')))
    ==
  (expect !>(ok))
++  test-pack-review-requires-commit-ancestry-and-exact-pack
  =/  extra  checked(changes ~[[main 0x11 0x22] [source 0x22 0x33]])
  =/  hidden=manifest
    (seal promoted(refs (~(put by refs.promoted) source-key (oid-text:stead-git 0x33))))
  =/  repacked=manifest  (seal promoted(pack-bytes 401))
  =/  new-objects=manifest  (seal promoted(objects 4))
  =/  wrong-kind  checked(kinds (malt ~[[0x22 %blob]]))
  =/  wrong-direction  checked(lineage (silt ~[[0x22 0x11]]))
  =/  ok=?
    ?&  ?=([%| %missing-object] (preflight env 0 current maintainer row reviewed checked(kinds ~)))
        ?=([%| %wrong-object-kind] (preflight env 0 current maintainer row reviewed wrong-kind))
        ?=([%| %non-fast-forward] (preflight env 0 current maintainer row reviewed checked(lineage ~)))
        ?=([%| %non-fast-forward] (preflight env 0 current maintainer row reviewed wrong-direction))
        ?=([%| %review-change-conflict] (preflight env 0 current maintainer row reviewed extra))
        ?=([%| %review-change-conflict] (preflight env 0 current maintainer row reviewed checked(changes ~[[main 0x11 0x33]])))
        ?=([%| %review-change-conflict] (preflight env 0 current maintainer row reviewed checked(changes ~[[main 0x11 0x0]])))
        ?=([%| %manifest-conflict] (preflight env 0 current maintainer row reviewed checked(pack hidden)))
        ?=([%| %pack-conflict] (preflight env 0 current maintainer row reviewed checked(pack repacked)))
        ?=([%| %pack-conflict] (preflight env 0 current maintainer row reviewed checked(pack new-objects)))
    ==
  (expect !>(ok))
++  test-pack-review-bounds-time-revision-and-generation
  =/  context=authority  env
  =/  invalid-number  item(change change.item(number 0))
  =/  too-many  item(change change.item(number 65))
  =/  ok=?
    ?&  ?=([%| %invalid-proposal] (propose env 0 current maker source invalid-number))
        ?=([%| %invalid-proposal] (propose env 0 current maker source too-many))
        ?=([%| %invalid-proposal] (propose env 0 current maker source item(id 'not-a-uuid')))
        ?=([%| %invalid-proposal] (propose env 0 current maker source item(work 'not-a-uuid')))
        ?=([%| %invalid-selection] (propose context(now 0) 0 current maker source item))
        ?=([%| %invalid-selection] (propose env 18.446.744.073.709.551.615 current maker source item))
    ==
  (expect !>(ok))
--

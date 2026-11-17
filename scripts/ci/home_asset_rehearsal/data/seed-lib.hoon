::  Fixed synthetic a0 predecessor data. No I/O, caller noun or authority grant.
::  External pack evidence is synthetic; no stock-Git/disk custody is asserted.
/+  stead-team, stead-team-codec, stead-team-config, stead-team-owner, stead-code-home, stead-codec, stead-projection, stead-session, stead-home-handoff, stead-project-retirement, stead-code-store, stead-code-credentials, stead-code-git-objects, stead-code-git-graph, stead-code-receive, stead-git, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-push, stead-code-pack-review, stead-code-pack-review-board, stead-code-pack-promotion, stead-code-review
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  inline-project=@t  '019939ba-4000-7000-8000-000000000100'
=/  retired-project=@t  '019939ba-4000-7000-8000-000000000101'
=/  work=@t  '019939ba-4000-7000-8000-000000000010'
=/  container=@t  '019939ba-4000-7000-8000-000000000020'
=/  document=@t  '019939ba-4000-7000-8000-000000000021'
=/  destination=scope:stead-code-credentials  [~zod project project 1]
=/  main=@t  'refs/heads/main'
=/  topic=@t  'refs/heads/topic'
=/  main-key=@t  (bytes-hex:stead-codec main)
=/  topic-key=@t  (bytes-hex:stead-codec topic)
=/  digest=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  bootstrap=@t  '019939ba-4000-7000-8000-000000000006'
=/  raw-id=@t  '019939ba-4000-7000-8000-000000000040'
=/  submit-id=@t  '019939ba-4000-7000-8000-000000000014'
=/  approve-id=@t  '019939ba-4000-7000-8000-000000000015'
=/  merge-id=@t  '019939ba-4000-7000-8000-000000000013'
|%
+$  parts
  $:  team=saved:stead-team-owner  code=persisted:stead-code-home
      mode=phase:stead-home-handoff  retired=ledger:stead-project-retirement
      packs=state:stead-code-pack-anchor  external=external-writes:stead-team-owner
      reviews=pack-boards:stead-team-owner
  ==
+$  eight
  $:  %stead-home  %8  team=saved:stead-team-owner
      code=persisted:stead-code-home  mode=phase:stead-home-handoff
      retired=ledger:stead-project-retirement  packs=state:stead-code-pack-anchor
      external=external-writes-v1:stead-team-owner
  ==
+$  nine
  $:  %stead-home  %9  team=saved:stead-team-owner
      code=persisted:stead-code-home  mode=phase:stead-home-handoff
      retired=ledger:stead-project-retirement  packs=state:stead-code-pack-anchor
      external=external-writes:stead-team-owner  reviews=pack-boards:stead-team-owner
  ==
++  checked-command
  |=  [prior=state:stead-team raw=@t now=@ud]
  ^-  state:stead-team
  =/  actor  (need (native-context:stead-team prior ~bus now))
  =/  command  (decode:stead-team-codec raw)
  =/  out  (apply-command:stead-team prior actor command now)
  =/  parsed  (need (parse-result:stead-codec response.out))
  ?>  ?=([%o *] parsed)
  ?>  =('accepted' (field:stead-codec p.parsed 'status'))
  next.out
++  company
  ^-  state:stead-team
  =/  configured
    (configure:stead-team empty:stead-team config ~zod 1)
  =/  pending=(list @t)  commands
  =/  now=@ud  100
  |-  ^-  state:stead-team
  ?~  pending  configured
  $(configured (checked-command configured i.pending now), pending t.pending, now +(now))
++  config
  '{"bindings":{"~bud":{"active":"yes","binding_id":"019939ba-4000-7000-8000-000000000204","binding_revision":"1","display_name":"Synthetic bud","expires_at_ms":"4102444800000","principal_id":"019939ba-4000-7000-8000-000000000104"},"~bus":{"active":"yes","binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"1","display_name":"Synthetic bus","expires_at_ms":"4102444800000","principal_id":"019939ba-4000-7000-8000-000000000002"},"~nec":{"active":"yes","binding_id":"019939ba-4000-7000-8000-000000000203","binding_revision":"1","display_name":"Synthetic nec","expires_at_ms":"4102444800000","principal_id":"019939ba-4000-7000-8000-000000000103"}},"custody":"local-disposable","expected_revision":"0","home":"~zod","organization_id":"019939ba-4000-7000-8000-000000000005","origin":"https://home.localhost:18443","project_creators":{"019939ba-4000-7000-8000-000000000002":"yes"},"protocol":"stead.team-config/1","runtime":"isolated-fake","team_id":"019939ba-4000-7000-8000-000000000006"}'
++  commands
  ^-  (list @t)
  :~  '{"authority_epoch":"1","expected_revision":"0","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","preset":"general","project_key":"EXT","title":"Preserved external review"},"project_id":"019939ba-4000-7000-8000-000000000001","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000700","resource_id":"019939ba-4000-7000-8000-000000000001"}'
      '{"authority_epoch":"1","expected_revision":"0","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","preset":"general","project_key":"INLINE","title":"Preserved inline source"},"project_id":"019939ba-4000-7000-8000-000000000100","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000701","resource_id":"019939ba-4000-7000-8000-000000000100"}'
      '{"authority_epoch":"1","expected_revision":"0","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","preset":"general","project_key":"RETIRED","title":"Preserved retired project"},"project_id":"019939ba-4000-7000-8000-000000000101","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000702","resource_id":"019939ba-4000-7000-8000-000000000101"}'
      '{"authority_epoch":"1","expected_revision":"1","operation":"policy.grant","payload":{"expires_at_ms":"4102444800000","grant_id":"019939ba-4000-7000-8000-000000000301","principal_id":"019939ba-4000-7000-8000-000000000103","role":"maintainer"},"project_id":"019939ba-4000-7000-8000-000000000001","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000703","resource_id":"019939ba-4000-7000-8000-000000000001"}'
      '{"authority_epoch":"1","expected_revision":"2","operation":"policy.grant","payload":{"expires_at_ms":"4102444800000","grant_id":"019939ba-4000-7000-8000-000000000302","principal_id":"019939ba-4000-7000-8000-000000000104","role":"maintainer"},"project_id":"019939ba-4000-7000-8000-000000000001","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000704","resource_id":"019939ba-4000-7000-8000-000000000001"}'
      '{"authority_epoch":"1","expected_revision":"0","operation":"work.create","payload":{"description":"Synthetic asset rehearsal Work","priority":"medium","status":"todo","title":"Preserved Work","type":"task"},"project_id":"019939ba-4000-7000-8000-000000000001","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000705","resource_id":"019939ba-4000-7000-8000-000000000010"}'
      '{"authority_epoch":"1","expected_revision":"0","operation":"container.create","payload":{"title":"Shared rehearsal Docs","visibility":"shared"},"project_id":"019939ba-4000-7000-8000-000000000001","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000706","resource_id":"019939ba-4000-7000-8000-000000000020"}'
      '{"authority_epoch":"1","expected_revision":"0","operation":"document.save","payload":{"container_id":"019939ba-4000-7000-8000-000000000020","markdown":"---\\nid: 019939ba-4000-7000-8000-000000000021\\ntype: page\\nstate: published\\n---\\n# Preserved Doc\\n\\nExact synthetic Markdown.\\n"},"project_id":"019939ba-4000-7000-8000-000000000001","protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000707","resource_id":"019939ba-4000-7000-8000-000000000021"}'
  ==
++  expected-markdown
  (cat 3 (header:stead-team document 'published') (rap 3 ~['# Preserved Doc' 10 10 'Exact synthetic Markdown.' 10]))
++  actor
  |=  ship=@p
  ^-  actor:stead-session
  identity:(need (native-context:stead-team company ship 1.000))
++  make-object
  |=  [kind=@tas bytes=@t]
  ^-  object:stead-git
  (need (hash-object:stead-code-git-objects kind [(met 3 bytes) bytes]))
++  blob
  (make-object %blob (rap 3 ~['synthetic preserved source' 10]))
++  tree
  ^-  object:stead-git
  =/  prefix=@t  '100644 file.txt'
  =/  width=@ud  +((met 3 prefix))
  =/  body=octets:stead-git
    [(add width 20) (can 3 ~[[width prefix] [20 (rev 3 20 oid:blob)]])]
  (need (hash-object:stead-code-git-objects %tree body))
++  first-commit
  (make-object %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 'author Test <test@example.invalid> 1 +0000' 10 'committer Test <test@example.invalid> 1 +0000' 10 10 'seed' 10]))
++  inline-repository
  ^-  state:stead-code-store
  =/  scope=scope:stead-code-credentials  [~zod inline-project inline-project 1]
  =/  who=actor:stead-session  (actor ~bus)
  =/  permits=allowance:stead-code-credentials  (allowed:stead-code-home company 1.000)
  =/  members=membership:stead-code-credentials  (member:stead-code-home company 1.000)
  =/  issued  (issue:stead-code-credentials *ledger:stead-code-credentials who scope & 100.000 1.000 42 permits)
  ?>  ?=(%& -.issued)
  =/  id=@t  '019939ba-4000-7000-8000-000000000401'
  =/  body=payload:stead-code-store
    [scope id who ~[[main 0x0 oid:first-commit]] ~[blob tree first-commit]]
  =/  fingerprint=@t  (fingerprint:stead-code-store body)
  =/  fresh=state:stead-code-store  (empty:stead-code-store scope)
  =.  pending.fresh  (~(put by pending.fresh) id [fingerprint body])
  =/  policy=ref-policy:stead-code-store
    |=  [caller=actor:stead-session target=scope:stead-code-credentials action=action:stead-code-receive change=update:stead-code-receive]
    &((same-actor:stead-session caller who) =(target scope) =(name.change main))
  =/  accepted
    (accept:stead-code-store fresh scope next.p.issued bearer.p.issued id fingerprint 1.000 members permits policy ~)
  ?>  ?=(%applied -.accepted)
  next.accepted
++  code
  ^-  persisted:stead-code-home
  [(malt ~[[inline-project [inline-repository *(set @t)]]]) ~ ~ ~]
++  mode
  ^-  phase:stead-home-handoff
  =/  challenge  (challenge-for:stead-home-handoff ~zod 2 digest)
  =/  sealed
    (need (transition:stead-home-handoff ~zod [%open 1 ~] [%seal 1 challenge]))
  (need (transition:stead-home-handoff ~zod sealed [%activate 2 digest]))
++  retired
  ^-  ledger:stead-project-retirement
  =/  db=state:stead-team  company
  =/  tip=@t  (need (head:stead-project-retirement data.db retired-project))
  =/  intent=intent:stead-project-retirement
    [retired-project '019939ba-4000-7000-8000-000000000400' 1 ~nec tip]
  (need (retire:stead-project-retirement ~zod data.db ~ intent 3.000))
++  seal
  |=  input=manifest:stead-code-pack-anchor
  ^-  manifest:stead-code-pack-anchor
  =/  raw  (snapshot-bytes:stead-code-pack-anchor input)
  =/  size  (met 3 raw)
  input(snapshot (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size raw)])))
++  current
  ^-  manifest:stead-code-pack-anchor
  %-  seal
  :*  destination  ''  main-key
      (malt ~[[main-key (oid-text:stead-git 0x11)] [topic-key (oid-text:stead-git 0x22)]])
      digest  400  3  500  digest
  ==
++  promoted
  ^-  manifest:stead-code-pack-anchor
  =/  prior=manifest:stead-code-pack-anchor  current
  (seal prior(refs (~(put by refs.prior) main-key (oid-text:stead-git 0x22))))
++  anchor
  ^-  entry:stead-code-pack-anchor
  [%accepted [current ~zod 1.900 901.900] [bootstrap (actor ~bus) 2.000]]
++  packs
  ^-  state:stead-code-pack-anchor
  (malt ~[[project anchor]])
++  proof
  |=  request=@t
  ^-  evidence:stead-code-pack-push
  :*  destination  snapshot:current  0  digest  request
      ~[[main 0x11 0x22]]  promoted
      (malt ~[[0x22 %commit]])  (silt ~[[0x11 0x22]])
  ==
++  raw-ledger
  ^-  ledger:stead-code-pack-ledger
  =/  db  (need (open:stead-code-pack-ledger anchor))
  =/  checked=evidence:stead-code-pack-push  (proof raw-id)
  =/  claim=intent:stead-code-pack-ledger
    [destination snapshot:current 0 digest raw-id 1 digest changes.checked]
  =/  allowed=allow:stead-code-pack-ledger
    |=  [action:stead-code-receive change=update:stead-code-receive]
    =(name.change main)
  =/  staged  (admit:stead-code-pack-ledger db claim (actor ~bus) 2.100 digest allowed ~)
  ?>  ?=(%applied -.staged)
  =/  verified  (verify:stead-code-pack-ledger next.staged claim checked (actor ~bus) 2.101 digest allowed ~)
  ?>  ?=(%applied -.verified)
  =/  committed  (commit:stead-code-pack-ledger next.verified claim checked (actor ~bus) 2.102 digest allowed ~)
  ?>  ?=(%applied -.committed)
  next.committed
++  review-authority
  ^-  authority:stead-code-pack-review
  =/  members=membership:stead-code-credentials  (member:stead-code-home company 2.200)
  =/  permits=permit:stead-code-pack-review
    |=  [who=actor:stead-session scope=scope:stead-code-credentials item=@t branch=@t role=role:stead-code-pack-review]
    ?.  &(=(scope destination) =(item work) =(branch main))  |
    ?.  (gte (rank:stead-code-home company who scope 2.200) 2)  |
    ?-  role
      %propose  (same-actor:stead-session who (actor ~bus))
      %review   (same-actor:stead-session who (actor ~nec))
      %merge    (same-actor:stead-session who (actor ~bud))
    ==
  [destination 2.200 members permits]
++  review-result
  ^-  promotion-result:stead-code-pack-review-board
  =/  item=proposal:stead-code-review
    ['019939ba-4000-7000-8000-000000000011' principal:(actor ~bus) [project project main] work [1 1 0x11 0x22]]
  =/  start  (empty:stead-code-pack-review-board destination)
  =/  proposed  (submit:stead-code-pack-review-board start review-authority 0 current (actor ~bus) submit-id topic item)
  ?>  ?=(%applied -.proposed)
  =/  row  (~(got by proposals.next.proposed) id.item)
  =/  approved  (approve:stead-code-pack-review-board next.proposed review-authority 0 current (actor ~nec) approve-id row)
  ?>  ?=(%applied -.approved)
  (accept:stead-code-pack-review-board next.approved review-authority 0 current (actor ~bud) merge-id row (proof merge-id) ~)
++  common
  ^-  parts
  =/  company=state:stead-team  company
  =/  code=persisted:stead-code-home  code
  =/  retired=ledger:stead-project-retirement  retired
  =/  packs=state:stead-code-pack-anchor  packs
  ?>  (validate-persisted:stead-code-home company code)
  ?>  (validate-packs:stead-code-home company repos.code packs)
  ?>  (validate:stead-project-retirement ~zod data.company retired)
  ?>  (valid:stead-home-handoff mode)
  [[company *state:stead-projection] code mode retired packs ~ ~]
++  data-eight
  ^-  parts
  =/  base=parts  common
  =/  ledger=ledger:stead-code-pack-ledger  raw-ledger
  ?>  (valid:stead-code-pack-ledger ledger anchor)
  base(external (malt ~[[project ledger]]))
++  data-nine
  ^-  parts
  =/  base=parts  common
  =/  result  review-result
  ?>  ?=(%applied -.result)
  =/  accepted  (promote:stead-code-pack-ledger (need (open:stead-code-pack-ledger anchor)) saved.result accepted-at.saved.result)
  ?>  ?=(%& -.accepted)
  ?>  (valid:stead-code-pack-ledger p.accepted anchor)
  ?>  (valid:stead-code-pack-review-board next.result)
  ?>  =(promotions.p.accepted promotions.next.result)
  base(external (malt ~[[project p.accepted]]), reviews (malt ~[[project next.result]]))
++  saved-eight
  ^-  vase
  =/  value=parts  data-eight
  =/  external=external-writes-v1:stead-team-owner
    (~(run by external.value) as-v1:stead-code-pack-ledger)
  !>([%stead-home %8 team.value code.value mode.value retired.value packs.value external])
++  saved-nine
  ^-  vase
  =/  value=parts  data-nine
  !>([%stead-home %9 team.value code.value mode.value retired.value packs.value external.value reviews.value])
++  durable-eight
  |=  saved=vase
  =/  value  !<(eight saved)
  (shax (jam [db.team.value code.value mode.value retired.value packs.value external.value]))
++  durable-nine
  |=  saved=vase
  =/  value  !<(nine saved)
  (shax (jam [db.team.value code.value mode.value retired.value packs.value external.value reviews.value]))
--

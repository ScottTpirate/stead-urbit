:: PRIVATE exact predecessor tests; authored/uncompiled/unregistered.
:: Fixture cores below retain the real inline accept/review and external
:: propose/approve/promote paths from existing native tests. Scope literals
:: alone are changed to the actual two configured legacy projects here.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-git, stead-session, stead-code-credentials, stead-code-delivery, stead-code-git-objects, stead-code-store, stead-code-review, stead-code-review-home, stead-code-home, stead-code-upload, stead-code-build-home, stead-code-pack-review-board, stead-code-pack-promotion, stead-code-pack-review, stead-code-pack-anchor, stead-code-pack-push, stead-code-pack-ledger, stead-repository-catalog, stead-repository-import
=/  inline
  =,  stead-code-review-home
  =/  where=scope  [~zod '019939ba-4000-7000-8000-000000000100' '019939ba-4000-7000-8000-000000000100' 1]
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
  ++  retained
    ^-  persisted:stead-code-home
    =/  out  merged
    =/  queued
      (stage:stead-code-upload ~ where maker [4 '0000'] 100 '019939ba-4000-7000-8000-000000000900')
    ?>  ?=(%& -.queued)
    :*  (malt ~[[project.where [repo.out protected]]])
        next.p.queued
        (malt ~[[project.where next.out]])
        (malt ~[[project.where *state:stead-code-build-home]])
    ==
  ++  saved-owner  maker
  ++  saved-scope  where
  ++  stored-repository  repo:merged
  --
=/  external
  =,  stead-code-pack-review-board
  =/  submit-id=@t  '019939ba-4000-7000-8000-000000000014'
  =/  approve-id=@t  '019939ba-4000-7000-8000-000000000015'
  =/  replace-id=@t  '019939ba-4000-7000-8000-000000000016'
  =/  next-approve=@t  '019939ba-4000-7000-8000-000000000017'
  =/  project=@t  '019939ba-4000-7000-8000-000000000101'
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
    ?:  =(ship ship.home-actor)  [~ home-actor]
    ~
  ++  policy
    |=  [who=actor where=scope work=@t target=@t capability=role:stead-code-pack-review]
    ^-  ?
    ?.  &(=(where destination) =(work work-id) =(target main))  |
    ?-  capability
      %propose  (same-actor:stead-session who maker)
      %review   (same-actor:stead-session who critic)
      %merge    (same-actor:stead-session who maintainer)
    ==
  ++  env
    ^-  authority
    [destination 100 membership policy]
  ++  permissive
    ^-  authority
    =/  context=authority  env
    =/  all=permit:stead-code-pack-review
      |=  [actor scope @t @t role:stead-code-pack-review]
      &
    context(allows all)
  ++  without-role
    |=  removed=role:stead-code-pack-review
    ^-  authority
    =/  context=authority  env
    =/  remaining=permit:stead-code-pack-review
      |=  [who=actor where=scope work=@t target=@t capability=role:stead-code-pack-review]
      &(!=(removed capability) (policy who where work target capability))
    context(allows remaining)
  ++  without-member
    |=  ship=@p
    ^-  authority
    =/  context=authority  env
    =/  remaining=membership:stead-code-credentials
      |=  requested=@p
      ?:  =(requested ship)  ~
      (membership requested)
    context(resolve remaining)
  ++  board
    ^-  state
    (empty destination)
  ++  applied
    |=  outcome=result
    ^-  state
    ?>  ?=(%applied -.outcome)
    next.outcome
  ++  proposed-state
    ^-  state
    (applied (submit board env 0 current maker submit-id source item))
  ++  proposal-row
    ^-  proposal
    =/  db=state  proposed-state
    (~(got by proposals.db) proposal-id)
  ++  approved-state
    ^-  state
    (applied (approve proposed-state env 0 current critic approve-id proposal-row))
  ++  saved-result
    ^-  promotion-result
    (accept approved-state env 0 current maintainer request proposal-row checked ~)
  ++  saved-board
    ^-  state
    =/  outcome  saved-result
    ?>  ?=(%applied -.outcome)
    next.outcome
  ++  saved-record
    ^-  record
    =/  outcome  saved-result
    ?>  ?=(%applied -.outcome)
    saved.outcome
  ++  readable
    |=  [who=actor where=scope work=@t target=@t]
    ^-  ?
    &(=(where destination) =(work work-id) =(target main))
  ++  request-id
    |=  number=@ud
    ^-  @t
    (cat 3 '019939ba-4000-7000-8000-' (hex:stead-codec 12 number))
  ++  genesis
    ^-  entry:stead-code-pack-anchor
    [%accepted [current ~zod 1 900.001] ['019939ba-4000-7000-8000-000000000099' maker 2]]
  ++  retained-ledger
    ^-  ledger:stead-code-pack-ledger
    =/  initial  (need (open:stead-code-pack-ledger genesis))
    =/  out  (promote:stead-code-pack-ledger initial saved-record 100)
    ?>  ?=(%& -.out)
    p.out
  ++  retained-board  saved-board
  ++  saved-scope  destination
  --
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  project-command
  |=  [request=@ud project=@ud key=@t]
  ^-  command:stead-codec
  =/  base
    (object ~[['protocol' 'stead.command/3'] ['request_id' (id request)] ['project_id' (id project)] ['resource_id' (id project)] ['expected_revision' '0'] ['authority_epoch' '1'] ['operation' 'project.create']])
  ?>  ?=([%o *] base)
  =/  payload
    (object ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' key] ['project_key' key] ['preset' 'general']])
  (decode:stead-team-codec (canonical [%o (~(put by p.base) 'payload' payload)]))
--
=/  configuration
  %-  rap
  :-  3
  :~  '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{'
      '"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000102","binding_id":"019939ba-4000-7000-8000-000000000202","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Alice"}'
      '},"project_creators":{"019939ba-4000-7000-8000-000000000102":"yes"}}'
  ==
=/  initial  (configure:stead-team empty:stead-team configuration ~zod 1.000)
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  first-project  (apply-command:stead-team initial alice (project-command 301 100 'INLINE') 1.002)
=/  second-project  (apply-command:stead-team next.first-project alice (project-command 302 101 'PACK') 1.003)
=/  team  next.second-project
=>
|%
++  import-inline
  (import-legacy:stead-repository-import team retained:inline ~ ~ ~)
++  import-external
  (import-legacy:stead-repository-import team *persisted:stead-code-home (malt ~[[(id 101) genesis:external]]) (malt ~[[(id 101) retained-ledger:external]]) (malt ~[[(id 101) retained-board:external]]))
++  added-wire
  (canonical (object ~[['request_id' (id 401)] ['project_id' (id 100)] ['repository_id' (id 210)] ['expected_catalog_revision' '1'] ['authority_epoch' '1'] ['display_name' 'Independent source']]))
++  current
  ::  Fixture-only abstract seam. Native/browser current authority is separate.
  ^-  current:stead-repository-catalog
  |=  [who=actor:stead-session project=@t now=@ud]
  ^-  (unit facts:stead-repository-catalog)
  ?.  &((same-actor:stead-session who identity.alice) =(project (id 100)))  ~
  [~ ~zod 1 3 |]
++  denied
  |=  result=(each imported:stead-repository-import @tas)
  ^-  ?
  ?=([%| %invalid-predecessor] result)
--
|%
++  test-repository-import-inline-exact-refs-reviews-uploads-and-alias
  ^-  tang
  =/  source  retained:inline
  ?>  (validate-persisted:stead-code-home team source)
  =/  out  import-inline
  ?>  ?=(%& -.out)
  ?>  =(source code.p.out)
  ?>  &(=(1 revision.catalog.p.out) =(~ creates.catalog.p.out))
  =/  row  (~(got by entries.catalog.p.out) (id 100))
  ?>  &(=(%inline-sha1-v1 profile.row) legacy-alias.row =('' name.row))
  =/  old  (need (legacy-resolve:stead-repository-catalog catalog.p.out (id 100) identity.alice %read 1.004 current))
  ?>  =(saved-scope:inline destination.old)
  =/  added  (create:stead-repository-catalog catalog.p.out added-wire identity.alice 1.004 current)
  ?>  ?=(%accepted -.added)
  ?>  =(old (need (legacy-resolve:stead-repository-catalog next.added (id 100) identity.alice %read 1.005 current)))
  ?>  =((empty:stead-code-store [~zod (id 100) (id 210) 1]) initial.added)
  ?>  =(source code.p.out)
  ?>  &(=(2 revision.data:(~(got by repos.code.p.out) (id 100))) =(1 ~(wyt by uploads.code.p.out)))
  ?>  &(?=(^ reviews.code.p.out) ?=(^ builds.code.p.out))
  ~
++  test-repository-import-external-exact-promotion-and-snapshot
  ^-  tang
  =/  ledger  retained-ledger:external
  =/  board  retained-board:external
  ?>  (valid:stead-code-pack-ledger ledger genesis:external)
  ?>  (valid:stead-code-pack-review-board board)
  ?>  &(?=(^ promotions.ledger) =(promotions.ledger promotions.board))
  =/  out  import-external
  ?>  ?=(%& -.out)
  ?>  =((malt ~[[(id 101) genesis:external]]) packs.p.out)
  ?>  =((malt ~[[(id 101) ledger]]) external.p.out)
  ?>  =((malt ~[[(id 101) board]]) boards.p.out)
  =/  row  (~(got by entries.catalog.p.out) (id 101))
  ?>  &(=(%external-sha1-pack-v1 profile.row) legacy-alias.row =(%legacy -.origin.row))
  ?>  =(snapshot.current.ledger snapshot.current:(~(got by external.p.out) (id 101)))
  =/  value  (need (parse added-wire))
  ?>  ?=([%o *] value)
  =/  unsupported  (canonical [%o (~(put by p.value) 'profile' [%s 'external-sha1-pack-v1'])])
  ?>  =([%denied %invalid-command] (create:stead-repository-catalog catalog.p.out unsupported identity.alice 1.004 current))
  ~
++  test-repository-import-refuses-orphan-corrupt-and-cross-scope-tails
  ^-  tang
  =/  source  retained:inline
  =/  original  (~(got by repos.source) (id 100))
  =/  orphan-board  source(reviews (~(put by reviews.source) (id 101) (~(got by reviews.source) (id 100))))
  ?>  (denied (import-legacy:stead-repository-import team orphan-board ~ ~ ~))
  =/  queued
    (stage:stead-code-upload ~ [~zod (id 101) (id 101) 1] saved-owner:inline [4 '0000'] 100 (id 901))
  ?>  ?=(%& -.queued)
  ?>  (valid:stead-code-upload next.p.queued)
  ?>  (denied (import-legacy:stead-repository-import team source(uploads next.p.queued) ~ ~ ~))
  =/  wrong  original(data data.original(destination [~zod (id 100) (id 101) 1]))
  ?>  (denied (import-legacy:stead-repository-import team source(repos (~(put by repos.source) (id 100) wrong)) ~ ~ ~))
  =/  missing  original(data data.original(journal ~))
  ?>  (denied (import-legacy:stead-repository-import team source(repos (~(put by repos.source) (id 100) missing)) ~ ~ ~))
  ?>  ?=(^ journal.data.original)
  =/  receipt-id  i.journal.data.original
  =/  receipt  (~(got by receipts.data.original) receipt-id)
  =/  forged  original(data data.original(receipts (~(put by receipts.data.original) receipt-id receipt(version 2))))
  ?>  (denied (import-legacy:stead-repository-import team source(repos (~(put by repos.source) (id 100) forged)) ~ ~ ~))
  =/  tree=object:stead-code-store  tree:inline
  =/  object-id  oid.tree
  =/  item  (~(got by objects.data.original) object-id)
  =/  broken  original(data data.original(objects (~(put by objects.data.original) object-id item(body [1 'x']))))
  ?>  (denied (import-legacy:stead-repository-import team source(repos (~(put by repos.source) (id 100) broken)) ~ ~ ~))
  =/  packs  (malt ~[[(id 101) genesis:external]])
  =/  ledger  (malt ~[[(id 101) retained-ledger:external]])
  =/  boards  (malt ~[[(id 101) retained-board:external]])
  ?>  (denied (import-legacy:stead-repository-import team *persisted:stead-code-home ~ ledger boards))
  ?>  (denied (import-legacy:stead-repository-import team *persisted:stead-code-home packs ledger ~))
  ?>  (denied (import-legacy:stead-repository-import team *persisted:stead-code-home packs ~ boards))
  =/  mismatch  retained-ledger:external
  =.  promotions.mismatch  ~
  ?>  (denied (import-legacy:stead-repository-import team *persisted:stead-code-home packs (malt ~[[(id 101) mismatch]]) boards))
  ?>  (denied (import-legacy:stead-repository-import team source (malt ~[[(id 100) genesis:external]]) ~ ~))
  ~
++  test-repository-import-empty-and-full-pure-roundtrip
  ^-  tang
  =/  empty  (import-legacy:stead-repository-import team *persisted:stead-code-home ~ ~ ~)
  ?>  ?=(%& -.empty)
  ?>  =(*catalog:stead-repository-catalog catalog.p.empty)
  ?>  =(*persisted:stead-code-home code.p.empty)
  =/  out
    (import-legacy:stead-repository-import team retained:inline (malt ~[[(id 101) genesis:external]]) (malt ~[[(id 101) retained-ledger:external]]) (malt ~[[(id 101) retained-board:external]]))
  ?>  ?=(%& -.out)
  =/  roundtrip  !<(imported:stead-repository-import (cue (jam !>(p.out))))
  ?>  =(p.out roundtrip)
  ?>  =(2 revision.catalog.roundtrip)
  ?>  =(retained:inline code.roundtrip)
  ?>  =((hash 'stead.repository-import-fixture/1' (bytes-hex (jam p.out))) (hash 'stead.repository-import-fixture/1' (bytes-hex (jam roundtrip))))
  ?>  =((~(got by external.p.out) (id 101)) (~(got by external.roundtrip) (id 101)))
  ::  Pure noun roundtrip only; no actual Gall/cold restart has run.
  ~
--

::  PRIVATE eight authored closure cases; no native execution/registration.
::  Existing importer fixture cores below exercise real store/review/pack
::  transitions. Inline scope is the sole parameterization of that fixture.
/+  *test, stead-actor, stead-code-build-home, stead-code-credentials, stead-code-delivery, stead-code-git-objects, stead-code-home, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-promotion, stead-code-pack-push, stead-code-pack-review, stead-code-pack-review-board, stead-code-receive, stead-code-review, stead-code-review-home, stead-code-store, stead-code-upload, stead-codec, stead-core, stead-git, stead-principals, stead-project-retirement, stead-repository-authority, stead-repository-catalog, stead-repository-import, stead-repository-store, stead-session, stead-team, stead-team-codec, stead-team-config
=/  inline
  |=  where=scope:stead-code-credentials
  =,  stead-code-review-home
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
  ++  continued-ledger
    ::  Actual second transition after the protected promotion: an ordinary
    ::  scoped topic advance, leaving the original promotion/board unchanged.
    ::  Exact synthetic worker evidence, as in the old pure ledger fixture;
    ::  this does not assert an external pack was fetched or inspected.
    ^-  ledger:stead-code-pack-ledger
    =/  prior  retained-ledger
    =/  after  (seal current.prior(refs (~(put by refs.current.prior) source-key (oid-text:stead-git 0x33)), objects +(objects.current.prior)))
    =/  changes=(list update:stead-code-pack-push)  ~[[source 0x22 0x33]]
    =/  request  (request-id 901)
    =/  claim=intent:stead-code-pack-ledger
      [destination snapshot.current.prior generation.prior digest request 1 digest changes]
    =/  proof=evidence:stead-code-pack-push
      [destination snapshot.current.prior generation.prior digest request changes after (malt ~[[0x33 %commit]]) (silt ~[[0x22 0x33]])]
    =/  permit=allow:stead-code-pack-ledger
      |=  [action=action:stead-code-receive change=update:stead-code-pack-push]
      &(=(%advance action) =(change [source 0x22 0x33]))
    =/  admitted  (admit:stead-code-pack-ledger prior claim maker 101 digest permit ~)
    ?>  ?=(%applied -.admitted)
    =/  verified  (verify:stead-code-pack-ledger next.admitted claim proof maker 102 digest permit ~)
    ?>  ?=(%applied -.verified)
    =/  committed  (commit:stead-code-pack-ledger next.verified claim proof maker 103 digest permit ~)
    ?>  ?=(%applied -.committed)
    next.committed
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
++  put
  |=  [value=json key=@t item=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key item)]
++  person
  |=  [principal=@ud binding=@ud revision=@ud active=@t expires=@ud display=@t]
  ^-  json
  (object ~[['principal_id' (id principal)] ['binding_id' (id binding)] ['binding_revision' (decimal revision)] ['active' active] ['expires_at_ms' (decimal expires)] ['display_name' display]])
++  config-wire
  |=  [prior=registry:stead-team-config people=(map @t json)]
  ^-  @t
  =/  raw
    %-  object
    :~  ['protocol' 'stead.team-config/1']
        ['expected_revision' (decimal ?~(current.prior 0 revision.u.current.prior))]
        ['home' '~zod']  ['origin' 'https://home.test']
        ['organization_id' '019939ba-4000-7000-8000-000000000005']
        ['team_id' '019939ba-4000-7000-8000-000000000006']
        ['custody' 'local-disposable']  ['runtime' 'isolated-fake']
    ==
  =/  wire  (put (put raw 'bindings' [%o people]) 'project_creators' (object ~[[(id 102) 'yes']]))
  (canonical wire)
++  config
  |=  [prior=registry:stead-team-config people=(map @t json) now=@ud]
  ^-  registry:stead-team-config
  (decode:stead-team-config (config-wire prior people) prior ~zod now)
++  command
  |=  [request=@ud project=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  raw  (object ~[['protocol' 'stead.command/3'] ['request_id' (id request)] ['project_id' (id project)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
  (decode:stead-team-codec (canonical (put raw 'payload' (object payload))))
++  project-command
  |=  [request=@ud project=@ud name=@t]
  ^-  command:stead-codec
  (command request project project 0 'project.create' ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' name] ['project_key' name] ['preset' 'general']])
++  accepted
  |=  out=transition:stead-team
  ^-  state:stead-team
  =/  value  (need (parse-result response.out))
  ?>  ?=([%o *] value)
  ?>  =('accepted' (field p.value 'status'))
  next.out
++  wire
  |=  [request=@ud project=@ud repository=@ud revision=@ud name=@t]
  ^-  @t
  (canonical (object ~[['request_id' (id request)] ['project_id' (id project)] ['repository_id' (id repository)] ['expected_catalog_revision' (decimal revision)] ['authority_epoch' '1'] ['display_name' name]]))
++  login
  |=  [state=snapshot:stead-repository-authority sender=@p now=@ud]
  ^-  result:stead-session
  =/  context  (need (native-context:stead-team db.state sender now))
  =/  begun  (begin:stead-session sessions.state identity.context home.state 'https://home.test' now 0x111)
  ?>  =(%pending status.begun)
  =/  challenge  (~(got by challenges.next.begun) id.begun)
  =/  approved  (approve:stead-session next.begun id.begun sender identity.context home.state 'https://home.test' 'stead.auth/1' 'member-session' expires.challenge +(now))
  ?>  =(%approved status.approved)
  =/  consumed  (consume:stead-session next.approved id.begun cookie.begun identity.context home.state 'https://home.test' (add now 2) 0x222)
  ?>  =(%accepted status.consumed)
  consumed
--
=/  bindings
  %-  malt
  :~  ['~bus' (person 102 202 1 'yes' 9.999.999 'Alice')]
      ['~nec' (person 103 203 1 'yes' 9.999.999 'Bob')]
      ['~bud' (person 104 204 1 'yes' 9.999.999 'Carol')]
      ['~wes' (person 105 205 1 'yes' 9.999.999 'Outside')]
  ==
=/  initial=state:stead-team
  (configure:stead-team empty:stead-team (config-wire *registry:stead-team-config bindings) ~zod 1.000)
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  bob  (need (native-context:stead-team initial ~nec 1.001))
=/  carol  (need (native-context:stead-team initial ~bud 1.001))
=/  one  (accepted (apply-command:stead-team initial alice (project-command 301 100 'ONE') 1.002))
=/  two  (accepted (apply-command:stead-team one alice (project-command 302 101 'TWO') 1.003))
=/  editor  (accepted (apply-command:stead-team two alice (command 303 100 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' (id 103)] ['role' 'contributor'] ['expires_at_ms' '8000000']]) 1.004))
=/  db  (accepted (apply-command:stead-team editor alice (command 304 100 100 2 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' (id 104)] ['role' 'reader'] ['expires_at_ms' '5000']]) 1.005))
=/  imported  (import:stead-principals registry.db ~zod)
=/  a  (declare:stead-principals imported ~zod ~zod (id 102) 1 %person 'Alice' & 1.010)
=/  b  (declare:stead-principals next.a ~zod ~zod (id 103) 1 %person 'Bob' & 1.011)
=/  c  (declare:stead-principals next.b ~zod ~zod (id 104) 1 %person 'Carol' & 1.012)
=/  d  (declare:stead-principals next.c ~zod ~zod (id 105) 1 %person 'Outside' & 1.013)
?>  ?&  =(%accepted status.a)  =(%accepted status.b)
        =(%accepted status.c)  =(%accepted status.d)
    ==
=/  base=snapshot:stead-repository-authority  [~zod db next.d *catalog:stead-repository-catalog ~ *state:stead-session]
=/  raw  (wire 701 100 210 0 'Source')
=/  first  (create:stead-repository-authority base [%native ~bus] raw 1.500)
?>  ?=(%accepted -.first)
=/  first-state  base(repositories next.first)
=/  second  (create:stead-repository-authority first-state [%native ~bus] (wire 702 100 211 1 'Docs') 1.501)
?>  ?=(%accepted -.second)
=/  second-state  base(repositories next.second)
=/  authority  second-state
=/  legacy-inline  (inline [~zod (id 100) (id 100) 1])
=/  target=ref:stead-repository-catalog  [(id 100) (id 210)]
=>
|%
++  advance
  ::  Real current-human credentials and actual store acceptance, not facts=&.
  |=  [current=snapshot:stead-repository-authority repo=state:stead-code-store request=@ud label=@t]
  ^-  state:stead-code-store
  =/  destination  destination.repo
  =/  issued
    (issue:stead-repository-authority current *ledger:stead-code-credentials [%native ~bus] [project.destination repository.destination] & 2.000 0x991)
  ?>  ?=(%& -.issued)
  =/  previous  (fall (~(get by refs.repo) 'refs/heads/main') 0x0)
  =/  fixture  (inline destination)
  =/  tree  tree:fixture
  =/  commit  (commit:fixture previous label)
  =/  body=payload:stead-code-store
    [destination (id request) identity.alice ~[['refs/heads/main' previous oid.commit]] ~[tree commit]]
  =/  digest  (fingerprint:stead-code-store body)
  =/  staged  repo(pending (~(put by pending.repo) (id request) [digest body]))
  =/  allows  (allowed:stead-repository-authority current 2.001)
  =/  policy=ref-policy:stead-code-store
    |=  [who=actor:stead-session scope=scope:stead-code-credentials action=action:stead-code-store update=update:stead-code-store]
    (allows who scope %write)
  =/  out
    (accept:stead-code-store staged destination next.p.issued bearer.p.issued (id request) digest 2.001 (member:stead-repository-authority current 2.001) allows policy ~)
  ?>  ?=(%applied -.out)
  next.out
++  value
  ^-  state:stead-repository-store
  =/  one  (advance authority initial.first 801 'Repository one')
  =/  two  (advance authority initial.second 802 'Repository two')
  [repositories.authority [(malt ~[[(id 210) [one ~]] [(id 211) [two ~]]]) ~ ~ ~] ~ ~ ~]
++  replace
  |=  [before=state:stead-repository-store id=@t repo=repository:stead-code-home]
  ^-  state:stead-repository-store
  before(code code.before(repos (~(put by repos.code.before) id repo)))
++  valid
  |=  current=state:stead-repository-store
  ^-  ?
  (valid:stead-repository-store ~zod db current)
++  selected
  |=  [current=state:stead-repository-store source=source:stead-repository-authority target=ref:stead-repository-catalog access=access:stead-repository-catalog]
  (select-inline:stead-repository-store authority current source target access 2.100)
++  mixed
  ^-  state:stead-repository-store
  =/  out
    (import-legacy:stead-repository-store ~zod db retained:legacy-inline (malt ~[[(id 101) genesis:external]]) (malt ~[[(id 101) retained-ledger:external]]) (malt ~[[(id 101) retained-board:external]]))
  ?>  ?=(%& -.out)
  p.out
++  append
  ::  Fixture composition only, not a new history/carrier atomic create gate.
  |=  [before=state:stead-repository-store raw=@t]
  ^-  state:stead-repository-store
  =/  snapshot  authority(repositories catalog.before)
  =/  created  (create:stead-repository-authority snapshot [%native ~bus] raw 2.000)
  ?>  ?=(%accepted -.created)
  before(catalog next.created, code code.before(repos (~(put by repos.code.before) repository.receipt.created [initial.created ~])))
++  refused-import
  |=  out=(each state:stead-repository-store @tas)
  ^-  ?
  ?=([%| %invalid-predecessor] out)
--
|%
++  test-repository-store-two-inline-current-scope
  ^-  tang
  =/  before  value
  ?>  (valid before)
  =/  one  (need (selected before [%native ~bus] target %manage))
  =/  two  (need (selected before [%native ~nec] [(id 100) (id 211)] %write))
  ?>  ?&  =([~zod (id 100) (id 210) 1] destination.resolved.one)
          =([~zod (id 100) (id 211) 1] destination.resolved.two)
          !=(refs.data.repository.one refs.data.repository.two)
          =(1 revision.data.repository.one)  =(1 revision.data.repository.two)
      ==
  =/  advanced  (advance authority data.repository.one 803 'Next revision of one')
  =/  after  (replace before (id 210) repository.one(data advanced))
  ?>  ?&  (valid after)  =(2 revision.advanced)
          =((~(get by repos.code.before) (id 211)) (~(get by repos.code.after) (id 211)))
          =(catalog.before catalog.after)
          ?=(~ (selected after [%native ~bus] [(id 101) (id 210)] %read))
      ==
  ~
++  test-repository-store-import-exact-mixed-four-roots
  ^-  tang
  =/  original  mixed
  ?>  ?&  (valid original)  =(retained:legacy-inline code.original)
          =((malt ~[[(id 101) genesis:external]]) packs.original)
          =((malt ~[[(id 101) retained-ledger:external]]) external.original)
          =((malt ~[[(id 101) retained-board:external]]) boards.original)
      ==
  =/  one  (append original (wire 704 100 210 2 'Independent one'))
  =/  four  (append one (wire 705 100 211 3 'Independent two'))
  =/  rounded  !<(state:stead-repository-store (cue (jam !>(four))))
  ?>  ?&  (valid four)  =(four rounded)  =(4 revision.catalog.four)
          =((~(get by repos.code.original) (id 100)) (~(get by repos.code.four) (id 100)))
          =(uploads.code.original uploads.code.four)
          =(reviews.code.original reviews.code.four)  =(builds.code.original builds.code.four)
          =(packs.original packs.four)  =(external.original external.four)  =(boards.original boards.four)
      ==
  ::  Advancing an independent root also preserves every imported tail.
  =/  created  (~(got by repos.code.four) (id 210))
  =/  grown  (replace four (id 210) created(data (advance authority(repositories catalog.four) data.created 804 'New independent content')))
  ?>  ?&  (valid grown)
          =((~(get by repos.code.original) (id 100)) (~(get by repos.code.grown) (id 100)))
          =(uploads.code.original uploads.code.grown)
          =(reviews.code.original reviews.code.grown)  =(builds.code.original builds.code.grown)
          =(packs.original packs.grown)  =(external.original external.grown)  =(boards.original boards.grown)
      ==
  ~
++  test-repository-store-catalog-key-profile-and-epoch
  ^-  tang
  =/  before  value
  =/  repo  (~(got by repos.code.before) (id 210))
  =/  row  (~(got by entries.catalog.before) (id 210))
  =/  partial  before(code code.before(repos (~(del by repos.code.before) (id 210))))
  =/  orphan  before(code code.before(repos (~(put by repos.code.before) (id 299) repo)))
  =/  missing  before(catalog *catalog:stead-repository-catalog)
  =/  twin  before(packs (malt ~[[(id 210) genesis:external]]))
  =/  crossed  repo(data data.repo(destination [~zod (id 101) (id 210) 1]))
  =/  away  repo(data data.repo(destination [~nec (id 100) (id 210) 1]))
  =/  stale  repo(data data.repo(destination [~zod (id 100) (id 210) 2]))
  =/  swapped  repo(data data.repo(destination [~zod (id 100) (id 211) 1]))
  =/  forged  before(catalog catalog.before(entries (~(put by entries.catalog.before) (id 210) row(legacy-alias &))))
  =/  external-created  before(catalog catalog.before(entries (~(put by entries.catalog.before) (id 210) row(profile %external-sha1-pack-v1))))
  ?>  ?&  !(valid partial)  !(valid orphan)  !(valid missing)  !(valid twin)
          !(valid (replace before (id 210) crossed))  !(valid (replace before (id 210) away))
          !(valid (replace before (id 210) stale))  !(valid (replace before (id 210) swapped))
          !(valid forged)  !(valid external-created)
          !(valid:stead-repository-store ~nec db before)
      ==
  =/  equal  (append before (wire 706 100 101 2 'Typed namespace'))
  =/  fresh  authority(repositories catalog.equal)
  ?>  ?&  (valid equal)
          ?=(^ (select-inline:stead-repository-store fresh equal [%native ~bus] [(id 100) (id 101)] %read 2.100))
          ?=(~ (legacy-resolve:stead-repository-authority fresh [%native ~bus] (id 101)  %read 2.100))
      ==
  ::  Synthetic lifecycle mutation tests retained closure, not a close command.
  =/  tomb  before(catalog catalog.before(entries (~(put by entries.catalog.before) (id 210) row(lifecycle %tombstone))))
  ?>  ?&  (valid tomb)
          ?=(~ (select-inline:stead-repository-store authority(repositories catalog.tomb) tomb [%native ~bus] target %read 2.100))
      ==
  ~
++  test-repository-store-object-journal-and-ref-integrity
  ^-  tang
  =/  before  value
  =/  repo  (~(got by repos.code.before) (id 210))
  =/  tip  (~(got by refs.data.repo) 'refs/heads/main')
  =/  object  (~(got by objects.data.repo) tip)
  =/  receipt  (~(got by receipts.data.repo) (id 801))
  =/  corrupt  object(body [1 'x'])
  =/  bad-object  repo(data data.repo(objects (~(put by objects.data.repo) tip corrupt)))
  =/  no-object  repo(data data.repo(objects (~(del by objects.data.repo) tip)))
  =/  bad-receipt  repo(data data.repo(receipts (~(put by receipts.data.repo) (id 801) receipt(destination [~zod (id 100) (id 211) 1]))))
  =/  bad-number  repo(data data.repo(receipts (~(put by receipts.data.repo) (id 801) receipt(revision 2))))
  =/  bad-protected  repo(protected (silt ~['refs/tags/release']))
  =/  duplicate  repo(data data.repo(journal ~[(id 801) (id 801)], revision 2))
  ?>  ?&  !(valid (replace before (id 210) bad-object))
          !(valid (replace before (id 210) no-object))
          !(valid (replace before (id 210) bad-receipt))
          !(valid (replace before (id 210) bad-number))
          !(valid (replace before (id 210) bad-protected))
          !(valid (replace before (id 210) duplicate))
      ==
  =/  advanced  (advance authority data.repo 805 'Actual second event')
  =/  backwards  repo(data advanced(journal (flop journal.advanced)))
  ?>  !(valid (replace before (id 210) backwards))
  ~
++  test-repository-store-review-build-cross-scope
  ^-  tang
  ::  Actual original pure review/merge fixtures; not a new current Work policy.
  =/  a  (inline [~zod (id 100) (id 210) 1])
  =/  b  (inline [~zod (id 100) (id 211) 1])
  =/  merged-a  merged:a
  =/  merged-b  merged:b
  =/  seed  value
  =/  repos
    (malt ~[[(id 210) [repo.merged-a (silt ~['refs/heads/main'])]] [(id 211) [repo.merged-b (silt ~['refs/heads/main'])]]])
  =/  reviews  (malt ~[[(id 210) next.merged-a] [(id 211) next.merged-b]])
  =/  good  seed(code [repos ~ reviews ~])
  ?>  (valid good)
  =/  crossed  good(code code.good(reviews (~(put by reviews) (id 210) next.merged-b)))
  =/  orphan  good(code code.good(builds (malt ~[[(id 299) *state:stead-code-build-home]])))
  =/  extra=state:stead-code-build-home
    [(malt ~[[(id 901) saved-owner:a]]) ~]
  =/  unmatched  good(code code.good(builds (malt ~[[(id 210) extra]])))
  =/  board  next.merged-a
  =/  bad-merge  board(merges (~(put by merges.board) (id 902) [(id 400) 1]))
  ?>  ?&  !(valid crossed)  !(valid orphan)  !(valid unmatched)
          !(valid good(code code.good(reviews (~(put by reviews) (id 210) bad-merge))))
      ==
  ~
++  test-repository-store-upload-scope-and-lossless-import
  ^-  tang
  =/  before  value
  =/  scope=scope:stead-code-credentials  [~zod (id 100) (id 210) 1]
  =/  queued  (stage:stead-code-upload ~ scope identity.alice [4 '0000'] 2.000 (id 903))
  ?>  ?=(%& -.queued)
  =/  good  before(code code.before(uploads next.p.queued))
  =/  job  (~(got by uploads.code.good) key.p.queued)
  ?>  ?&  (valid good)  =(wire.job [4 '0000'])  =(identity.alice owner.job)
          =(302.000 until.job)  =((id 903) request.job)
      ==
  =/  scopes=(list scope:stead-code-credentials)
    ~[[~zod (id 100) (id 299) 1] [~zod (id 101) (id 210) 1] [~nec (id 100) (id 210) 1] [~zod (id 100) (id 210) 2]]
  ?>  %+  levy  scopes
      |=  wrong=scope:stead-code-credentials
      =/  swapped  job(destination wrong)
      =/  key  (key:stead-code-upload wrong owner.swapped wire.swapped)
      !(valid good(code code.good(uploads (malt ~[[key swapped]]))))
  ::  Changing only the embedded scope, retaining its old key, also refuses.
  =/  swapped  job(destination [~zod (id 100) (id 211) 1])
  ?>  !(valid good(code code.good(uploads (malt ~[[key.p.queued swapped]]))))
  =/  original  retained:legacy-inline
  =/  imported  (import-legacy:stead-repository-store ~zod db original ~ ~ ~)
  ?>  ?=(%& -.imported)
  ?>  ?&  =(uploads.original uploads.code.p.imported)
          (valid p.imported)
          ?=(^ (select-inline:stead-repository-store authority(repositories catalog.p.imported) p.imported [%native ~bus] [(id 100) (id 100)] %read 400.000))
          =(uploads.original uploads.code.p.imported)
      ==
  ~
++  test-repository-store-external-closure-stays-legacy
  ^-  tang
  =/  original  mixed
  =/  before  original(external (malt ~[[(id 101) continued-ledger:external]]))
  =/  ledger  (~(got by external.before) (id 101))
  =/  board  (~(got by boards.before) (id 101))
  =/  anchor  (~(got by packs.before) (id 101))
  =/  row  (~(got by entries.catalog.before) (id 101))
  ?>  ?=(^ journal.ledger)
  ?>  =(2 (lent journal.ledger))
  =/  dropped  ledger(journal t.journal.ledger)
  =/  reversed  ledger(journal (flop journal.ledger))
  =/  no-promotions  board(promotions ~)
  =/  destination  destination.pack.row.anchor
  =/  wrong  anchor(row row.anchor(pack pack.row.anchor(destination destination(repository (id 212)))))
  ?>  ?&  (valid before)
          !(valid before(packs ~))  !(valid before(boards ~))  !(valid before(external ~))
          !(valid before(external (~(put by external.before) (id 101) dropped)))
          !(valid before(external (~(put by external.before) (id 101) reversed)))
          !(valid before(boards (~(put by boards.before) (id 101) no-promotions)))
          !(valid before(packs (~(put by packs.before) (id 101) wrong)))
          !(valid before(catalog catalog.before(entries (~(put by entries.catalog.before) (id 101) row(project (id 100))))))
          ?=(~ (select-inline:stead-repository-store authority(repositories catalog.before) before [%native ~bus] [(id 101) (id 101)] %read 2.100))
      ==
  ?>  (refused-import (import-legacy:stead-repository-store ~zod db code.before packs.before external.before ~))
  ~
++  test-repository-store-current-access-not-old-history
  ^-  tang
  =/  before  value
  =/  logged  (login authority ~bus 2.100)
  =/  open  authority(sessions next.logged)
  =/  browser=source:stead-repository-authority  [%browser cookie.logged csrf.logged]
  ?>  ?=(^ (select-inline:stead-repository-store open before browser target %write 2.104))
  =/  closed  (logout:stead-session next.logged cookie.logged csrf.logged identity.alice ~zod 'https://home.test' 2.105)
  =/  revoked  (accepted (apply-command:stead-team db alice (command 308 100 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 2.110))
  =/  people  (~(put by bindings) '~bus' (person 102 213 2 'yes' 9.999.999 'Alice'))
  =/  rotated  (configure:stead-team db (config-wire registry.db people) ~zod 2.120)
  =/  tip  (need (head:stead-project-retirement data.db (id 100)))
  =/  retired  (need (retire:stead-project-retirement ~zod data.db ~ [(id 100) (id 904) 1 ~nec tip] 2.130))
  =/  disabled  (declare:stead-principals principals.authority ~zod ~zod (id 102) 2 %person 'Alice' | 2.140)
  ::  Kind is immutable: this is a separately declared actual imported branch.
  =/  agent  (declare:stead-principals imported ~zod ~zod (id 102) 1 %agent 'Alice' & 2.140)
  ?>  ?&  =(%logged-out status.closed)  =(%accepted status.disabled)  =(%accepted status.agent)
          ?=(~ (select-inline:stead-repository-store open(sessions next.closed) before browser target %read 2.106))
          ?=(~ (select-inline:stead-repository-store authority(db revoked) before [%native ~nec] target %read 2.111))
          ?=(~ (select-inline:stead-repository-store open(db rotated) before browser target %read 2.121))
          ?=(~ (select-inline:stead-repository-store authority(retired retired) before [%native ~bus] target %write 2.131))
          ?=(^ (select-inline:stead-repository-store authority(retired retired) before [%native ~bud] target %read 2.131))
          ?=(~ (select-inline:stead-repository-store authority(principals next.disabled) before [%native ~bus] target %read 2.141))
          ?=(~ (select-inline:stead-repository-store authority(principals next.agent) before [%native ~bus] target %read 2.141))
          ?=(^ (selected before [%native ~bud] target %read))
          ?=(~ (selected before [%native ~bud] target %write))
          ?=(~ (selected before [%native ~bud] target %manage))
          ?=(~ (select-inline:stead-repository-store authority before [%native ~bud] target %read 5.000))
          ?=(~ (select-inline:stead-repository-store base before [%native ~bus] target %read 2.100))
          (valid before)  =(before value)
      ==
  ~
--

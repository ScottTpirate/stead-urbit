/+  *test, stead-code-delivery
=,  stead-code-delivery
=/  where=scope  [~zod '019939ba-4000-7000-8000-000000000100' '019939ba-4000-7000-8000-000000000200' 1]
=/  work-id=@t  '019939ba-4000-7000-8000-000000000300'
=/  proposal-id=@t  '019939ba-4000-7000-8000-000000000400'
=/  grant-id=@t  '019939ba-4000-7000-8000-000000000500'
=/  job-id=@t  '019939ba-4000-7000-8000-000000000600'
=/  release-id=@t  '019939ba-4000-7000-8000-000000000700'
=/  other-id=@t  '019939ba-4000-7000-8000-000000000800'
=/  ref=@t  'refs/heads/main'
=/  maker=actor  [~bus '019939ba-4000-7000-8000-000000001001' '019939ba-4000-7000-8000-000000002001' 1 & 1.000.000]
=/  coder=actor  [~nec '019939ba-4000-7000-8000-000000001002' '019939ba-4000-7000-8000-000000002002' 1 & 1.000.000]
=/  critic=actor  [~bud '019939ba-4000-7000-8000-000000001003' '019939ba-4000-7000-8000-000000002003' 1 & 1.000.000]
=/  custodian=actor  [~wes '019939ba-4000-7000-8000-000000001004' '019939ba-4000-7000-8000-000000002004' 1 & 1.000.000]
=/  runner=actor  [~sev '019939ba-4000-7000-8000-000000001005' '019939ba-4000-7000-8000-000000002005' 1 & 1.000.000]
=/  fallback=actor  [~per '019939ba-4000-7000-8000-000000001006' '019939ba-4000-7000-8000-000000002006' 1 & 1.000.000]
=/  head-pin=@ux  0x98b.b7f9.7a35.bcf9.2f3b.2418.8045.b8d0.1deb.b723
=/  recipe-pin=@t  'b5695ad2e2e3afb3c395d385031c24690fdf405074ec7c7e7241cda2d2024478'
=/  source-pin=@t  'dfca78ddbd1cda487f706a3b48b6ece879fdee074d8c8ea4a70603ae0ea68ebc'
=/  artifact-pin=@t  '4866318a75a3ab86fe176fc3c0cc4a433b90d43dd8a7f73f4604b421044761a3'
|%
++  membership
  |=  ship=@p
  ^-  (unit actor)
  ?:  =(ship ship.maker)      [~ maker]
  ?:  =(ship ship.coder)      [~ coder]
  ?:  =(ship ship.critic)     [~ critic]
  ?:  =(ship ship.custodian)  [~ custodian]
  ?:  =(ship ship.runner)     [~ runner]
  ?:  =(ship ship.fallback)   [~ fallback]
  ~
++  policy
  |=  [who=actor loc=scope work=@t target=@t capability=role]
  ^-  ?
  ?.  &(=(loc where) =(work work-id) =(target ref))  |
  ?-  capability
    %delegate       =(who maker)
    %propose        =(who maker)
    %agent-propose  =(who coder)
    %review         =(who critic)
    %merge          =(who custodian)
    %queue-build    =(who maker)
    %run-build      |(=(who runner) =(who fallback))
    %release        =(who custodian)
  ==
++  source-view
  |=  [who=actor item=proposal]
  ^-  (unit @t)
  ?:  &(=(work.item work-id) |(=(head-pin head.change.item) =(0x3 head.change.item)))
    [~ source-pin]
  ~
++  recipe-view
  |=  [loc=scope pin=@t]
  ^-  ?
  &(=(loc where) =(pin recipe-pin))
++  clock
  |=  [now=@ud tip=@ux]
  ^-  authority
  =/  observe=refs
    |=  target=@t
    ?:(=(target ref) tip 0x0)
  =/  accepted=$-([scope proposal] ?)
    |=  [loc=scope item=proposal]
    &(=(loc where) =(tip head-pin) =(item change))
  =/  checked=verify-output
    |=  [loc=scope id=@t item=proposal attempt=@ud by=actor proof=attestation]
    ?&  =(loc where)
        =(id job-id)
        |(=(item change) =(item delegated))
        |(=(by runner) =(by fallback))
        |(=(attempt 1) =(attempt 2))
        =(source.proof source-pin)
        =(recipe.proof recipe-pin)
        =(output.proof artifact-pin)
    ==
  [where now membership policy source-view observe recipe-view accepted checked]
++  env
  ^-  authority
  (clock 100 0x1)
++  released-env
  ^-  authority
  (clock 100 head-pin)
++  without
  |=  [context=authority revoked=role]
  ^-  authority
  =/  restricted=permit
    |=  [who=actor loc=scope work=@t target=@t capability=role]
    &(!=(revoked capability) (policy who loc work target capability))
  context(allows restricted)
++  board
  ^-  state
  (empty where)
++  change
  ^-  proposal
  [proposal-id principal.maker [project.where repository.where ref] work-id [1 1 0x1 head-pin]]
++  newer
  ^-  proposal
  =/  prior=proposal  change
  prior(change [1 2 0x1 0x3])
++  delegated
  ^-  proposal
  =/  prior=proposal  change
  prior(author principal.coder)
++  scope-grant
  ^-  delegation
  [grant-id maker coder work-id ref 200]
++  verdict
  ^-  attestation
  [source-pin recipe-pin artifact-pin %passed]
++  committed
  |=  value=result
  ^-  state
  ?>  ?=(%applied -.value)
  next.value
++  proposed
  ^-  state
  (committed (submit board env maker change ~))
++  reviewed
  ^-  state
  (committed (approve proposed env critic proposal-id 1))
++  queued
  ^-  state
  (committed (queue reviewed env maker job-id proposal-id 1 recipe-pin))
++  leased
  ^-  state
  (committed (claim queued env runner job-id 0))
++  complete
  ^-  state
  (committed (finish leased env runner job-id 1 verdict))
++  released
  ^-  state
  (committed (release-intent complete released-env custodian release-id job-id))
++  granted
  ^-  state
  (committed (delegate board env maker scope-grant))
++  agent-proposed
  ^-  state
  (committed (submit granted env coder delegated [~ grant-id]))
++  test-delivery-proposal-recorded
  =/  db=state  proposed
  (expect !>(=([~ [change maker ~]] (~(get by revisions.db) [proposal-id 1]))))
++  test-delivery-proposal-replay
  (expect !>(=([%replayed proposed] (submit proposed env maker change ~))))
++  test-delivery-proposal-different-input
  =/  prior=proposal  change
  (expect !>(=([%rejected %id-conflict] (submit proposed env maker prior(change [1 1 0x1 0x3]) ~))))
++  test-delivery-proposal-ref-cas
  (expect !>(=([%rejected %stale-target] (submit board released-env maker change ~))))
++  test-delivery-agent-needs-delegation
  (expect !>(=([%rejected %denied] (submit board env coder delegated ~))))
++  test-delivery-agent-cannot-grant
  (expect !>(=([%rejected %denied] (delegate board env coder scope-grant))))
++  test-delivery-delegation-scoped-to-work
  =/  prior=proposal  delegated
  (expect !>(=([%rejected %denied] (submit granted env coder prior(work other-id) [~ grant-id]))))
++  test-delivery-agent-cannot-review
  (expect !>(=([%rejected %denied] (approve agent-proposed env coder proposal-id 1))))
++  test-delivery-agent-cannot-merge
  (expect !>(=([%| %denied] (merge-candidate agent-proposed env coder proposal-id 1))))
++  test-delivery-delegation-revoked
  =/  revoked  (committed (revoke agent-proposed env maker grant-id))
  (expect !>(=([%rejected %denied] (approve revoked env critic proposal-id 1))))
++  test-delivery-delegation-expired
  (expect !>(=([%rejected %denied] (approve agent-proposed (clock 200 0x1) critic proposal-id 1))))
++  test-delivery-review-required
  (expect !>(=([%| %review-required] (merge-candidate proposed env custodian proposal-id 1))))
++  test-delivery-review-replay
  (expect !>(=([%replayed reviewed] (approve reviewed env critic proposal-id 1))))
++  test-delivery-review-exact-candidate
  (expect !>(=([%& ref 0x1 head-pin] (merge-candidate reviewed env custodian proposal-id 1))))
++  test-delivery-review-stale-tip
  (expect !>(=([%| %stale-target] (merge-candidate reviewed released-env custodian proposal-id 1))))
++  test-delivery-review-edited
  =/  edited  (committed (submit reviewed env maker newer ~))
  =/  ok=?
    ?&  ?=(^ (~(get by reviews.edited) [proposal-id 1]))
        =([%| %denied] (merge-candidate edited env custodian proposal-id 1))
        =([%| %review-required] (merge-candidate edited env custodian proposal-id 2))
    ==
  (expect !>(ok))
++  test-delivery-review-revoked
  =/  restricted=permit
    |=  [who=actor loc=scope work=@t target=@t capability=role]
    &(!=(%review capability) (policy who loc work target capability))
  =/  context=authority  env
  =/  changed  context(allows restricted)
  (expect !>(=([%| %review-denied] (merge-candidate reviewed changed custodian proposal-id 1))))
++  test-delivery-build-recipe-allowlist
  (expect !>(=([%rejected %recipe-denied] (queue reviewed env maker job-id proposal-id 1 source-pin))))
++  test-delivery-build-queue-replay
  (expect !>(=([%replayed queued] (queue queued env maker job-id proposal-id 1 recipe-pin))))
++  test-delivery-build-worker-only
  (expect !>(=([%rejected %denied] (claim queued env maker job-id 0))))
++  test-delivery-build-claim-replay
  (expect !>(=([%replayed leased] (claim leased env runner job-id 0))))
++  test-delivery-build-lease-single-runner
  (expect !>(=([%rejected %leased] (claim leased env fallback job-id 0))))
++  test-delivery-build-wrong-source
  =/  prior=attestation  verdict
  (expect !>(=([%rejected %wrong-input] (finish leased env runner job-id 1 prior(source artifact-pin)))))
++  test-delivery-build-wrong-recipe
  =/  prior=attestation  verdict
  (expect !>(=([%rejected %wrong-input] (finish leased env runner job-id 1 prior(recipe artifact-pin)))))
++  test-delivery-build-artifact-unverified
  =/  prior=attestation  verdict
  (expect !>(=([%rejected %artifact-unverified] (finish leased env runner job-id 1 prior(output recipe-pin)))))
++  test-delivery-build-lease-expired
  (expect !>(=([%rejected %stale-lease] (finish leased (clock 120.100 0x1) runner job-id 1 verdict))))
++  test-delivery-build-lease-retry
  =/  reclaimed  (committed (claim leased (clock 120.100 0x1) fallback job-id 1))
  =/  new-attempt  (finish reclaimed (clock 120.100 0x1) fallback job-id 2 verdict)
  =/  old-attempt  (finish reclaimed (clock 120.100 0x1) runner job-id 1 verdict)
  (expect !>(&(?=(%applied -.new-attempt) =([%rejected %stale-lease] old-attempt))))
++  test-delivery-build-completion-replay
  (expect !>(=([%replayed complete] (finish complete env runner job-id 1 verdict))))
++  test-delivery-build-replay-after-edit
  =/  edited  (committed (submit complete env maker newer ~))
  =/  advanced=authority  (clock 120.100 0x3)
  =/  unavailable  advanced(source |=([who=actor item=proposal] `(unit @t)`~))
  =/  ok=?
    ?&  =([%replayed edited] (finish edited unavailable runner job-id 1 verdict))
        =([%rejected %id-conflict] (finish edited unavailable fallback job-id 1 verdict))
        =([%rejected %id-conflict] (finish edited unavailable runner job-id 2 verdict))
    ==
  (expect !>(ok))
++  test-delivery-build-replay-current-permissions
  =/  edited  (committed (submit complete env maker newer ~))
  =/  advanced=authority  (clock 120.100 0x3)
  =/  current-member=$-(@p (unit actor))
    |=  ship=@p
    ?:(=(ship ship.runner) ~ (membership ship))
  =/  removed  advanced(resolve current-member)
  =/  ok=?
    ?&  =([%rejected %denied] (finish edited removed runner job-id 1 verdict))
        =([%rejected %denied] (finish edited (without advanced %run-build) runner job-id 1 verdict))
        =([%rejected %denied] (finish edited (without advanced %queue-build) runner job-id 1 verdict))
        =([%rejected %denied] (finish edited (without advanced %propose) runner job-id 1 verdict))
    ==
  (expect !>(ok))
++  test-delivery-build-replay-revoked-delegation
  =/  wait  (committed (queue agent-proposed env maker job-id proposal-id 1 recipe-pin))
  =/  working  (committed (claim wait env runner job-id 0))
  =/  done  (committed (finish working env runner job-id 1 verdict))
  =/  revoked  (committed (revoke done env maker grant-id))
  (expect !>(=([%rejected %denied] (finish revoked env runner job-id 1 verdict))))
++  test-delivery-build-completion-conflict
  =/  prior=attestation  verdict
  (expect !>(=([%rejected %id-conflict] (finish complete env runner job-id 1 prior(output source-pin)))))
++  test-delivery-build-edit-invalidates-lease
  =/  edited  (committed (submit leased env maker newer ~))
  (expect !>(=([%rejected %denied] (finish edited env runner job-id 1 verdict))))
++  test-delivery-build-cancelled-terminal
  =/  cancelled  (committed (cancel leased env maker job-id))
  (expect !>(=([%rejected %terminal] (claim cancelled env runner job-id 1))))
++  test-delivery-release-needs-accepted-head
  (expect !>(=([%rejected %unaccepted-head] (release-intent complete env custodian release-id job-id))))
++  test-delivery-release-needs-acceptance-receipt
  =/  context=authority  released-env
  =/  missing  context(accepted |=([loc=scope item=proposal] |))
  (expect !>(=([%rejected %acceptance-required] (release-intent complete missing custodian release-id job-id))))
++  test-delivery-release-worker-denied
  (expect !>(=([%rejected %denied] (release-intent complete released-env runner release-id job-id))))
++  test-delivery-release-failed-build
  =/  prior=attestation  verdict
  =/  failed  (committed (finish leased env runner job-id 1 prior(outcome %failed)))
  (expect !>(=([%rejected %build-required] (release-intent failed released-env custodian release-id job-id))))
++  test-delivery-release-exact-record
  =/  sealed=state  released
  =/  ok=?
    ?&  ?=(^ (~(get by releases.sealed) release-id))
        =([%replayed sealed] (release-intent sealed released-env custodian release-id job-id))
        =([%rejected %already-released] (release-intent sealed released-env custodian other-id job-id))
    ==
  (expect !>(ok))
++  test-delivery-release-replay-after-tip-moves
  =/  advanced  (clock 100 0x3)
  =/  ok=?
    ?&  =([%replayed released] (release-intent released advanced custodian release-id job-id))
        =([%rejected %unaccepted-head] (release-intent released advanced custodian other-id job-id))
    ==
  (expect !>(ok))
++  test-delivery-release-replay-after-edit
  =/  revision=proposal  newer
  =/  edited  (committed (submit released released-env maker revision(change [1 2 head-pin 0x3]) ~))
  =/  advanced  (clock 100 0x3)
  =/  ok=?
    ?&  =([%replayed edited] (release-intent edited advanced custodian release-id job-id))
        =([%rejected %denied] (release-intent edited advanced custodian other-id job-id))
    ==
  (expect !>(ok))
++  test-delivery-release-replay-current-permissions
  =/  advanced  (clock 100 0x3)
  =/  ok=?
    ?&  =([%rejected %denied] (release-intent released (without advanced %release) custodian release-id job-id))
        =([%rejected %denied] (release-intent released (without advanced %run-build) custodian release-id job-id))
        =([%rejected %review-denied] (release-intent released (without advanced %review) custodian release-id job-id))
    ==
  (expect !>(ok))
++  test-delivery-replay-still-verifies-artifact
  =/  advanced=authority  (clock 100 0x3)
  =/  unavailable=verify-output
    |=  [loc=scope id=@t item=proposal attempt=@ud by=actor proof=attestation]
    |
  =/  closed  advanced(verify unavailable)
  =/  ok=?
    ?&  =([%rejected %id-conflict] (finish complete closed runner job-id 1 verdict))
        =([%rejected %artifact-unverified] (release-intent released closed custodian release-id job-id))
    ==
  (expect !>(ok))
++  test-delivery-versioned-replay-roundtrip
  (expect !>(=((jam reviewed) (jam (cue (jam reviewed))))))
++  failure-control
  (expect !>(%.n))
--

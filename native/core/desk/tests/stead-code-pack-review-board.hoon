::  Pure board transitions and historical record checks, no Home persistence.
/+  *test, stead-codec, stead-code-pack-review-board, stead-code-pack-promotion, stead-code-pack-review, stead-code-pack-anchor, stead-code-pack-push, stead-code-review, stead-code-credentials, stead-session, stead-git
=,  stead-code-pack-review-board
=/  submit-id=@t  '019939ba-4000-7000-8000-000000000014'
=/  approve-id=@t  '019939ba-4000-7000-8000-000000000015'
=/  replace-id=@t  '019939ba-4000-7000-8000-000000000016'
=/  next-approve=@t  '019939ba-4000-7000-8000-000000000017'
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
++  test-pack-board-records-exact-promotion-and-replays-history
  =/  db=state  saved-board
  =/  saved=record  saved-record
  =/  repeated  (accept db env 1 promoted maintainer request proposal-row checked [~ saved])
  ?>  ?=(%replayed -.repeated)
  =/  ok=?
    ?&  (valid board)  (valid proposed-state)  (valid approved-state)  (valid db)
        (valid:stead-code-pack-promotion saved)
        =(checked (evidence:stead-code-pack-promotion saved))
        =(saved saved.repeated)  =(db next.repeated)
        =(request request.saved)  =(merger.saved maintainer)
        =(accepted-at.saved 100)  =(base.saved current)
        =(pack.decision.candidate.saved promoted)
        =(generation.decision.candidate.saved 1)
        =(db (state (cue (jam db))))
        ?=  [%rejected %proposal-merged]
          (submit db env 1 promoted maker replace-id source item(change change.item(number 2)))
    ==
  (expect !>(ok))
++  test-pack-board-owner-revision-and-approval-replacement
  =/  next-item  item(change change.item(number 2))
  =/  next-db  (applied (submit approved-state env 0 current maker replace-id source next-item))
  =/  next-row  (~(got by proposals.next-db) proposal-id)
  =/  another  item(author principal.critic, change change.item(number 2))
  =/  wrong-work  next-item(work other-id)
  =/  skipped  item(change change.item(number 3))
  =/  ok=?
    ?&  (valid next-db)
        ?=(~ (~(get by approvals.next-db) proposal-id))
        =(number.change.item.next-row 2)
        ?=([%replayed *] (submit proposed-state env 0 current maker submit-id source item))
        ?=([%rejected %id-owner-conflict] (submit proposed-state permissive 0 current critic replace-id source another))
        ?=([%rejected %proposal-id-conflict] (submit proposed-state permissive 0 current maker replace-id source wrong-work))
        ?=([%rejected %stale-revision] (submit proposed-state env 0 current maker replace-id source skipped))
        ?=([%rejected %stale-revision] (submit next-db env 0 current maker submit-id source item))
        ?=([%rejected %stale-proposal] (approve next-db env 0 current critic approve-id proposal-row))
        ?=([%applied *] (approve next-db env 0 current critic next-approve next-row))
    ==
  (expect !>(ok))
++  test-pack-board-request-ids-and-current-exact-approval
  =/  row=proposal  proposal-row
  =/  context=authority  env
  =/  next-item  item(change change.item(number 2))
  =/  later  (approve approved-state context(now 200) 0 current critic approve-id row)
  ?>  ?=(%replayed -.later)
  =/  ok=?
    ?&  =(next.later approved-state)
        ?=([%rejected %request-reused] (submit proposed-state env 0 current maker submit-id source next-item))
        ?=([%rejected %request-reused] (approve proposed-state env 0 current critic submit-id row))
        ?=([%rejected %stale-proposal] (approve proposed-state env 0 current critic approve-id row(source 'refs/heads/other')))
        ?=([%rejected %already-reviewed] (approve approved-state env 0 current critic next-approve row))
        ?=([%rejected %denied] (approve approved-state (without-role %review) 0 current critic approve-id row))
        ?=([%rejected %denied] (approve proposed-state permissive 0 current home-actor approve-id row))
        ?=([%rejected %self-review] (approve proposed-state permissive 0 current maker approve-id row))
    ==
  (expect !>(ok))
++  test-pack-board-preflight-rejects-unreviewed-stale-and-unproved
  =/  moved=manifest
    (seal current(refs (~(put by refs.current) source-key (oid-text:stead-git 0x33))))
  =/  ok=?
    ?&  ?=([%rejected %approval-required] (accept proposed-state env 0 current maintainer request proposal-row checked ~))
        ?=([%rejected %stale-selection] (accept approved-state env 1 current maintainer request proposal-row checked ~))
        ?=([%rejected %stale-selection] (accept approved-state env 0 moved maintainer request proposal-row checked ~))
        ?=([%rejected %missing-object] (accept approved-state env 0 current maintainer request proposal-row checked(kinds ~) ~))
        ?=([%rejected %non-fast-forward] (accept approved-state env 0 current maintainer request proposal-row checked(lineage ~) ~))
        ?=([%rejected %invalid-board-context] (accept approved-state env 0 current maintainer other-id proposal-row checked ~))
        ?=([%rejected %self-merge] (accept approved-state permissive 0 current maker request proposal-row checked ~))
        ?=([%rejected %denied] (accept approved-state permissive 0 current home-actor request proposal-row checked ~))
    ==
  (expect !>(ok))
++  test-pack-board-replay-needs-authoritative-record-and-current-policy
  =/  db=state  saved-board
  =/  saved=record  saved-record
  =/  context=authority  env
  =/  ok=?
    ?&  ?=([%rejected %history-conflict] (accept db env 1 promoted maintainer request proposal-row checked ~))
        ?=([%rejected %history-conflict] (accept db env 1 promoted maintainer request proposal-row checked [~ saved(accepted-at 101)]))
        ?=([%rejected %request-reused] (accept db env 1 promoted maintainer request proposal-row checked(wire snapshot.current) [~ saved]))
        ?=([%rejected %request-reused] (accept db env 1 promoted critic request proposal-row checked [~ saved]))
        ?=([%rejected %denied] (accept db (without-role %propose) 1 promoted maintainer request proposal-row checked [~ saved]))
        ?=([%rejected %denied] (accept db (without-role %review) 1 promoted maintainer request proposal-row checked [~ saved]))
        ?=([%rejected %denied] (accept db (without-role %merge) 1 promoted maintainer request proposal-row checked [~ saved]))
        ?=([%rejected %denied] (accept db (without-member ship.maintainer) 1 promoted maintainer request proposal-row checked [~ saved]))
        ?=([%rejected %denied] (accept db context(now 1.000.000) 1 promoted maintainer request proposal-row checked [~ saved]))
        (valid db)
    ==
  (expect !>(ok))
++  test-pack-board-history-validation-refuses-corrupted-bindings
  =/  db=state  saved-board
  =/  saved=record  saved-record
  =/  row=proposal  proposal-row
  =/  review=approval  (~(got by approvals.db) proposal-id)
  =/  altered  review(reviewed row(source 'refs/heads/other'))
  =/  bad  db(approvals (~(put by approvals.db) proposal-id altered))
  =/  ok=?
    ?&  !(valid bad)
        !(valid db(requests (~(del by requests.db) submit-id)))
        !(valid:stead-code-pack-promotion saved(request other-id))
        !(valid:stead-code-pack-promotion saved(merger maker))
        !(valid:stead-code-pack-promotion saved(lineage ~))
        !(valid:stead-code-pack-promotion saved(base current(snapshot digest)))
        !(valid:stead-code-pack-promotion saved(accepted-at 99))
        ?=([%rejected %invalid-board-context] (submit db(version 2) env 1 promoted maker replace-id source item))
    ==
  (expect !>(ok))
++  test-pack-board-read-policy-and-fixed-request-capacity
  =/  row=proposal  proposal-row
  =/  requests=(map @t operation)
    %-  malt
    %+  turn  (gulf 1 192)
    |=  number=@ud
    [(request-id number) [%proposed row]]
  =/  db=state  proposed-state
  =/  full  db(requests requests)
  =/  deny=$-([actor scope @t @t] ?)
    |=  [actor scope @t @t]
    |
  =/  context=authority  env
  =/  ok=?
    ?&  (valid full)
        =(~(wyt by requests.full) 192)
        ?=([%replayed *] (submit full env 0 current maker (request-id 1) source item))
        ?=([%rejected %request-capacity] (submit full env 0 current maker (request-id 193) source item))
        ?=(^ (read approved-state env 0 current reader proposal-id readable))
        ?=(~ (read approved-state env 0 current reader proposal-id deny))
        ?=(~ (read approved-state permissive 0 current home-actor proposal-id readable))
        ?=(~ (read approved-state permissive 0 current outsider proposal-id readable))
        ?=(~ (read approved-state (without-member ship.reader) 0 current reader proposal-id readable))
        ?=([%rejected %invalid-board-context] (submit proposed-state context(now 99) 0 current maker replace-id source item))
    ==
  (expect !>(ok))
++  test-pack-board-revision-history-is-dense-and-unambiguous
  =/  first=proposal  proposal-row
  =/  reviewed=state  approved-state
  =/  prior-review  (~(got by approvals.reviewed) proposal-id)
  =/  next-item  item(change change.item(number 2))
  =/  db  (applied (submit approved-state env 0 current maker replace-id source next-item))
  =/  missing  db(requests (~(del by requests.db) submit-id))
  =/  altered  first(source 'refs/heads/another')
  =/  conflicting  db(requests (~(put by requests.db) other-id [%proposed altered]))
  =/  conflicting-review
    db(requests (~(put by requests.db) approve-id [%approved prior-review(reviewed altered)]))
  =/  alias  db(requests (~(put by requests.db) other-id [%proposed first]))
  =/  ok=?
    ?&  (valid db)
        !(valid missing)
        !(valid conflicting)
        !(valid conflicting-review)
        (valid alias)
        ?=([%rejected %invalid-board-context] (approve conflicting env 0 current critic next-approve (~(got by proposals.db) proposal-id)))
    ==
  (expect !>(ok))
--

::  Bounded per-project review board. These are pure candidate transitions.
::  Home owns this state, current membership/policy and authenticated evidence.
::  A promotion result must be persisted atomically with the unified pack
::  history; returning this candidate alone is never business acceptance.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-review, stead-code-pack-review, stead-code-pack-promotion, stead-code-pack-push, stead-code-pack-anchor
|%
+$  scope  scope:stead-code-credentials
+$  actor  actor:stead-session
+$  authority  authority:stead-code-pack-review
+$  manifest  manifest:stead-code-pack-anchor
+$  proposal  proposal:stead-code-pack-review
+$  approval  approval:stead-code-pack-review
+$  record  record:stead-code-pack-promotion
+$  commit-proof  [expected=proposal checked=evidence:stead-code-pack-push]
+$  view  [row=proposal approved=(unit approval)]
+$  operation
  $%  [%proposed row=proposal]
      [%approved row=approval]
      [%promoted id=@t]
  ==
+$  state
  $:  version=@ud  destination=scope  last=@ud
      proposals=(map @t proposal)  approvals=(map @t approval)
      requests=(map @t operation)  promotions=(map @t record)
  ==
+$  result
  $%([%applied next=state] [%replayed next=state] [%rejected reason=@tas])
+$  promotion-result
  $%  [%applied next=state saved=record]
      [%replayed next=state saved=record]
      [%rejected reason=@tas]
  ==
++  empty
  |=  destination=scope
  ^-  state
  [1 destination 0 ~ ~ ~ ~]
++  same-proposal
  |=  [left=proposal right=proposal]
  ^-  ?
  ?&  =(destination.left destination.right)
      =(snapshot.left snapshot.right)  =(generation.left generation.right)
      =(source.left source.right)  =(item.left item.right)
      (same-actor:stead-session owner.left owner.right)
  ==
++  lineage
  |=  [db=state row=proposal]
  ^-  ?
  =/  latest  (~(get by proposals.db) id.item.row)
  ?~  latest  |
  ?&  =(destination.row destination.db)
      (same-actor:stead-session owner.row owner.u.latest)
      =(work.item.row work.item.u.latest)
      =(location.item.row location.item.u.latest)
      (lte number.change.item.row number.change.item.u.latest)
      ?:  =(number.change.item.row number.change.item.u.latest)
        (same-proposal row u.latest)
      &
  ==
++  revisions-valid
  |=  db=state
  ^-  ?
  ::  Index at most 192 receipts once. Approvals and promotions must refer
  ::  to the same exact revision noun; request aliases do not add revisions.
  ?.  (lte ~(wyt by requests.db) 192)  |
  =/  entries  ~(tap by requests.db)
  =/  seen=(map [@t @ud] proposal)  ~
  =/  offered=(set [@t @ud])  ~
  =/  counts=(map @t @ud)  ~
  |-  ^-  ?
  ?~  entries
    %+  levy  ~(tap by proposals.db)
    |=  [id=@t row=proposal]
    ?&  =((fall (~(get by counts) id) 0) number.change.item.row)
        =((~(get by seen) [id number.change.item.row]) [~ row])
    ==
  =/  entry  q.i.entries
  ?.  ?:  ?=(%promoted -.entry)
        (~(has by promotions.db) id.entry)
      &
    |
  =/  row=proposal
    ?-  -.entry
      %proposed  row.entry
      %approved  reviewed.row.entry
      %promoted
        =/  saved  (~(got by promotions.db) id.entry)
        reviewed.review.candidate.saved
    ==
  =/  id  id.item.row
  =/  key  [id number.change.item.row]
  =/  prior  (~(get by seen) key)
  ?.  ?~(prior & =(u.prior row))  |
  =.  seen  (~(put by seen) key row)
  ?:  |(!?=(%proposed -.entry) (~(has in offered) key))
    $(entries t.entries)
  =/  count  (fall (~(get by counts) id) 0)
  $(entries t.entries, offered (~(put in offered) key), counts (~(put by counts) id +(count)))
++  valid
  |=  db=state
  ^-  ?
  ?.  ?&  =(1 version.db)
          (scope-valid:stead-code-credentials destination.db)
          =(project.destination.db repository.destination.db)
          (lte last.db 18.446.744.073.709.551.615)
          (lte ~(wyt by proposals.db) 64)
          (lte ~(wyt by approvals.db) 64)
          (lte ~(wyt by requests.db) 192)
          (lte ~(wyt by promotions.db) 7)
          |(=(0 ~(wyt by requests.db)) (gth last.db 0))
      ==
    |
  ?.  %+  levy  ~(tap by proposals.db)
      |=  [id=@t row=proposal]
      ?&  =(id id.item.row)  =(destination.row destination.db)
          (proposal-valid:stead-code-pack-promotion row)
          %+  lien  ~(tap by requests.db)
          |=  [request=@t entry=operation]
          ?.  ?=(%proposed -.entry)  |
          (same-proposal row row.entry)
      ==
    |
  ?.  %+  levy  ~(tap by approvals.db)
      |=  [id=@t row=approval]
      ?&  =(id id.item.reviewed.row)
          =((~(get by proposals.db) id) [~ reviewed.row])
          (approval-valid:stead-code-pack-promotion row)
          (lte approved-at.row last.db)
          %+  lien  ~(tap by requests.db)
          |=  [request=@t entry=operation]
          ?.  ?=(%approved -.entry)  |
          =(row row.entry)
      ==
    |
  ?.  %+  levy  ~(tap by requests.db)
      |=  [request=@t entry=operation]
      ?.  (uuid:stead-codec request)  |
      ?-  -.entry
        %proposed
          &((proposal-valid:stead-code-pack-promotion row.entry) (lineage db row.entry))
        %approved
          ?&  (approval-valid:stead-code-pack-promotion row.entry)
              (lineage db reviewed.row.entry)
              (lte approved-at.row.entry last.db)
          ==
        %promoted
          &(=(request id.entry) (~(has by promotions.db) request))
      ==
    |
  ::  Every recorded revision is already in 1..latest above, so the exact
  ::  unique count proves a dense chain without a nested revision walk.
  ?.  (revisions-valid db)  |
  %+  levy  ~(tap by promotions.db)
  |=  [request=@t saved=record]
  ?&  =(request request.saved)
      =((~(get by requests.db) request) [~ %promoted request])
      =(destination.db destination.decision.candidate.saved)
      (lineage db reviewed.review.candidate.saved)
      (lte accepted-at.saved last.db)
      (valid:stead-code-pack-promotion saved)
  ==
++  scoped
  |=  [db=state env=authority generation=@ud current=manifest]
  ^-  ?
  ?&  (valid db)
      =(destination.db destination.env)
      =(destination.db destination.current)
      (valid-manifest:stead-code-pack-anchor current)
      (lth generation 18.446.744.073.709.551.615)
      (gth now.env 0)  (lte now.env 18.446.744.073.709.551.615)
      (gte now.env last.db)
  ==
++  submit
  |=  $:  db=state  env=authority  generation=@ud  current=manifest
          caller=actor  request=@t  source=@t  item=proposal:stead-code-review
      ==
  ^-  result
  ?.  &((scoped db env generation current) (uuid:stead-codec request))
    [%rejected %invalid-board-context]
  =/  checked  (propose:stead-code-pack-review env generation current caller source item)
  ?:  ?=(%| -.checked)  [%rejected p.checked]
  =/  row  p.checked
  =/  receipt  (~(get by requests.db) request)
  ?^  receipt
    ?.  ?=(%proposed -.u.receipt)  [%rejected %request-reused]
    ?.  (same-proposal row row.u.receipt)  [%rejected %request-reused]
    =/  latest  (~(get by proposals.db) id.item)
    ?~  latest  [%rejected %stale-revision]
    ?.  (same-proposal row u.latest)  [%rejected %stale-revision]
    [%replayed db]
  ?:  (gte ~(wyt by requests.db) 192)  [%rejected %request-capacity]
  =/  prior  (~(get by proposals.db) id.item)
  ?^  prior
    ?.  (same-actor:stead-session owner.u.prior owner.row)  [%rejected %id-owner-conflict]
    ?.  &(=(work.item work.item.u.prior) =(location.item location.item.u.prior))
      [%rejected %proposal-id-conflict]
    ?:  (same-proposal row u.prior)
      [%applied db(last now.env, requests (~(put by requests.db) request [%proposed u.prior]))]
    ?.  =(number.change.item +(number.change.item.u.prior))  [%rejected %stale-revision]
    [%applied db(last now.env, proposals (~(put by proposals.db) id.item row), approvals (~(del by approvals.db) id.item), requests (~(put by requests.db) request [%proposed row]))]
  ?.  =(1 number.change.item)  [%rejected %stale-revision]
  ?:  (gte ~(wyt by proposals.db) 64)  [%rejected %proposal-capacity]
  [%applied db(last now.env, proposals (~(put by proposals.db) id.item row), requests (~(put by requests.db) request [%proposed row]))]
++  approve
  |=  $:  db=state  env=authority  generation=@ud  current=manifest
          caller=actor  request=@t  expected=proposal
      ==
  ^-  result
  ?.  &((scoped db env generation current) (uuid:stead-codec request))
    [%rejected %invalid-board-context]
  =/  id  id.item.expected
  =/  row  (~(get by proposals.db) id)
  ?~  row  [%rejected %proposal-unavailable]
  ?.  =(u.row expected)  [%rejected %stale-proposal]
  =/  checked  (approve:stead-code-pack-review env generation current caller u.row)
  ?:  ?=(%| -.checked)  [%rejected p.checked]
  =/  receipt  (~(get by requests.db) request)
  ?^  receipt
    ?.  ?=(%approved -.u.receipt)  [%rejected %request-reused]
    ?.  ?&  =(reviewed.row.u.receipt expected)
            (same-actor:stead-session reviewer.row.u.receipt reviewer.p.checked)
        ==
      [%rejected %request-reused]
    ?.  =((~(get by approvals.db) id) [~ row.u.receipt])  [%rejected %stale-review]
    [%replayed db]
  ?:  (~(has by approvals.db) id)  [%rejected %already-reviewed]
  ?:  (gte ~(wyt by requests.db) 192)  [%rejected %request-capacity]
  [%applied db(last now.env, approvals (~(put by approvals.db) id p.checked), requests (~(put by requests.db) request [%approved p.checked]))]
++  accept
  |=  $:  db=state  env=authority  generation=@ud  current=manifest
          caller=actor  request=@t  expected=proposal
          checked=evidence:stead-code-pack-push  committed=(unit record)
      ==
  ^-  promotion-result
  ?.  ?&  (scoped db env generation current)
          (uuid:stead-codec request)  =(request request.checked)
      ==
    [%rejected %invalid-board-context]
  =/  receipt  (~(get by requests.db) request)
  ?^  receipt
    ?.  ?=(%promoted -.u.receipt)  [%rejected %request-reused]
    =/  prior  (~(get by promotions.db) request)
    ?~  prior  [%rejected %history-conflict]
    ?~  committed  [%rejected %history-conflict]
    ?.  =(u.prior u.committed)  [%rejected %history-conflict]
    =/  saved  u.prior
    =/  original  candidate.saved
    ?.  ?&  =(expected reviewed.review.original)
            =(checked (evidence:stead-code-pack-promotion saved))
            (same-actor:stead-session merger.saved caller)
            (gte generation generation.decision.original)
            (gte now.env accepted-at.saved)
        ==
      [%rejected %request-reused]
    ::  A historical base is legal only for this exact authoritative receipt.
    ::  Fresh membership and all three current roles still gate the replay.
    =/  ready
      (preflight:stead-code-pack-review env generation.expected base.saved caller expected review.original checked)
    ?:  ?=(%| -.ready)  [%rejected p.ready]
    ?.  &(=(decision.p.ready decision.original) =(review.p.ready review.original))
      [%rejected %history-conflict]
    [%replayed db saved]
  ?^  committed  [%rejected %history-conflict]
  =/  id  id.item.expected
  =/  row  (~(get by proposals.db) id)
  ?~  row  [%rejected %proposal-unavailable]
  ?.  =(u.row expected)  [%rejected %stale-proposal]
  =/  review  (~(get by approvals.db) id)
  ?~  review  [%rejected %approval-required]
  =/  ready  (preflight:stead-code-pack-review env generation current caller u.row u.review checked)
  ?:  ?=(%| -.ready)  [%rejected p.ready]
  ?:  (gte ~(wyt by requests.db) 192)  [%rejected %request-capacity]
  ?:  (gte ~(wyt by promotions.db) 7)  [%rejected %promotion-capacity]
  =/  saved=record
    [1 request merger.p.ready now.env current p.ready kinds.checked lineage.checked]
  ?.  (valid:stead-code-pack-promotion saved)  [%rejected %invalid-promotion]
  =/  next=state
    db(last now.env, requests (~(put by requests.db) request [%promoted request]), promotions (~(put by promotions.db) request saved))
  [%applied next saved]
++  read
  |=  $:  db=state  env=authority  generation=@ud  current=manifest
          caller=actor  id=@t
          readable=$-([actor scope @t @t] ?)
      ==
  ^-  (unit view)
  ?.  &((scoped db env generation current) (uuid:stead-codec id))  ~
  =/  who  (active:stead-code-pack-review env caller)
  ?~  who  ~
  =/  row  (~(get by proposals.db) id)
  ?~  row  ~
  ?.  (readable u.who destination.db work.item.u.row target.location.item.u.row)  ~
  [~ u.row (~(get by approvals.db) id)]
--

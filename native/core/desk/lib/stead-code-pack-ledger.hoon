::  Durable, single-project transitions for immutable external Git snapshots.
::  The caller supplies authenticated member, worker evidence, and current policy.
/+  stead-codec, stead-code-pack-push, stead-code-pack-anchor, stead-code-receive, stead-session, stead-code-pack-promotion
|%
+$  scope  scope:stead-code-pack-push
+$  actor  actor:stead-session
+$  manifest  manifest:stead-code-pack-push
+$  checked  evidence:stead-code-pack-push
+$  receipt  receipt:stead-code-pack-push
+$  update  update:stead-code-receive
+$  allow  $-([action:stead-code-receive update] ?)
+$  intent
  [destination=scope base=@t generation=@ud wire=@t request=@t attempt=@ud incarnation=@t changes=(list update)]
+$  admission  [claim=intent owner=actor since=@ud until=@ud]
+$  job  $%([%admitted row=admission ~] [%verified row=admission proof=checked])
+$  record  [row=admission proof=checked result=receipt]
+$  promotion  record:stead-code-pack-promotion
+$  ledger-v1
  $:  version=@ud  seed=@t  seed-request=@t  birth=@ud  last=@ud
      current=manifest  generation=@ud  serial=@ud
      pending=(unit job)  receipts=(map @t record)  journal=(list @t)
  ==
+$  ledger
  $:  version=@ud  seed=@t  seed-request=@t  birth=@ud  last=@ud
      current=manifest  generation=@ud  serial=@ud
      pending=(unit job)  receipts=(map @t record)  journal=(list @t)
      promotions=(map @t promotion)
  ==
+$  pending-result  $%([%applied next=ledger] [%replayed next=ledger] [%rejected reason=@tas])
+$  commit-result
  $%([%applied next=ledger result=receipt] [%replayed next=ledger result=receipt] [%rejected reason=@tas])
++  max-advances  7
++  max-number  18.446.744.073.709.551.615
++  seed-id
  |=  anchor=entry:stead-code-pack-anchor
  (hash:stead-codec 'stead.git-pack-seed/1' (bytes-hex:stead-codec (jam anchor)))
++  open
  |=  anchor=entry:stead-code-pack-anchor
  ^-  (unit ledger)
  ?.  &(?=(%accepted -.anchor) (valid:stead-code-pack-anchor anchor))  ~
  =/  born  accepted-at.proof.anchor
  [~ 2 (seed-id anchor) request.proof.anchor born born pack.row.anchor 0 0 ~ ~ ~ ~]
++  from-v1
  |=  old=ledger-v1
  ^-  ledger
  ?>  =(version.old 1)
  [2 seed.old seed-request.old birth.old last.old current.old generation.old serial.old pending.old receipts.old journal.old ~]
++  as-v1
  |=  db=ledger
  ^-  ledger-v1
  ?>  &(=(version.db 2) ?=(~ promotions.db))
  [1 seed.db seed-request.db birth.db last.db current.db generation.db serial.db pending.db receipts.db journal.db]
++  used
  |=  [db=ledger request=@t]
  |(=(seed-request.db request) (~(has by receipts.db) request) (~(has by promotions.db) request))
++  history
  |=  [db=ledger request=@t]
  ^-  (unit [pack=manifest generation=@ud accepted=@ud])
  =/  pushed  (~(get by receipts.db) request)
  ?^  pushed
    [~ pack.decision.result.u.pushed generation.decision.result.u.pushed accepted-at.result.u.pushed]
  =/  promoted  (~(get by promotions.db) request)
  ?~  promoted  ~
  [~ pack.decision.candidate.u.promoted generation.decision.candidate.u.promoted accepted-at.u.promoted]
++  action-of
  |=  change=update
  ^-  action:stead-code-receive
  ?:  =(0 prior.change)  %create
  %advance
++  valid-intent
  |=  claim=intent
  ^-  ?
  ?&  (uuid:stead-codec request.claim)
      (token-valid:stead-session base.claim)
      (token-valid:stead-session wire.claim)
      (token-valid:stead-session incarnation.claim)
      (gth attempt.claim 0)
      (lte attempt.claim max-number)
      (lte generation.claim max-advances)
      (lte (lent (scag 33 changes.claim)) 32)
      !=(0 (lent (scag 1 changes.claim)))
      %+  levy  changes.claim
      |=  change=update
      ?&  (lte (met 3 name.change) 1.024)
          (lte (met 3 prior.change) 20)
          (lte (met 3 target.change) 20)
          !=(0 target.change)
      ==
  ==
++  scope-matches
  |=  [db=ledger claim=intent]
  ?&  =(destination.claim destination.current.db)
      =(base.claim snapshot.current.db)
      =(generation.claim generation.db)
  ==
++  proof-matches
  |=  [claim=intent proof=checked]
  ?&  =(destination.claim destination.proof)
      =(base.claim base.proof)
      =(generation.claim generation.proof)
      =(wire.claim wire.proof)
      =(request.claim request.proof)
      =(changes.claim changes.proof)
  ==
++  approved
  |=  [who=actor now=@ud permitted=allow protected=(set @t) claim=intent]
  ^-  ?
  ?&  (live:stead-session who now)
      !=(ship.who home.destination.claim)
      (lte ~(wyt in protected) 16)
      %+  levy  changes.claim
      |=  change=update
      &(!(~(has in protected) name.change) (permitted (action-of change) change))
  ==
++  valid-admission
  |=  row=admission
  ^-  ?
  ?&  (valid-intent claim.row)
      (gth since.row 0)
      (lte until.row max-number)
      (lth since.row until.row)
      (lte until.row (add since.row 300.000))
      (lte until.row expires.owner.row)
      (live:stead-session owner.row since.row)
      !=(ship.owner.row home.destination.claim.row)
  ==
++  owner-matches
  |=  [row=admission claim=intent who=actor now=@ud]
  &((same-actor:stead-session owner.row who) =(claim.row claim) (gte now since.row) (lth now until.row))
++  admit
  |=  [db=ledger claim=intent who=actor now=@ud incarnation=@t permitted=allow protected=(set @t)]
  ^-  pending-result
  ?.  (valid-intent claim)  [%rejected %invalid-intent]
  ?.  (approved who now permitted protected claim)  [%rejected %denied]
  ?.  =(incarnation incarnation.claim)  [%rejected %incarnation-conflict]
  ?.  (scope-matches db claim)  [%rejected %stale-base]
  ?.  (gte now last.db)  [%rejected %clock-conflict]
  ?:  (used db request.claim)
    [%rejected %request-reused]
  ?:  (gte generation.db max-advances)  [%rejected %history-capacity]
  =?  db  ?~(pending.db | (gte now until.row.u.pending.db))
    db(pending ~)
  ?^  pending.db
    ?:  (owner-matches row.u.pending.db claim who now)  [%replayed db]
    [%rejected %pending-conflict]
  ?.  &((lth serial.db max-number) =(attempt.claim +(serial.db)))  [%rejected %attempt-conflict]
  =/  row=admission  [claim who now (min expires.who (add now 300.000))]
  ?.  (valid-admission row)  [%rejected %invalid-intent]
  [%applied db(serial attempt.claim, pending [~ %admitted row ~])]
++  verify
  |=  $:  db=ledger  claim=intent  proof=checked  who=actor  now=@ud  incarnation=@t
          permitted=allow  protected=(set @t)
      ==
  ^-  pending-result
  ?.  (valid-intent claim)  [%rejected %invalid-intent]
  ?.  (approved who now permitted protected claim)  [%rejected %denied]
  ?.  =(incarnation incarnation.claim)  [%rejected %incarnation-conflict]
  ?.  (scope-matches db claim)  [%rejected %stale-base]
  ?~  pending.db  [%rejected %no-pending]
  ?.  (owner-matches row.u.pending.db claim who now)  [%rejected %attempt-conflict]
  ?.  (proof-matches claim proof)  [%rejected %proof-conflict]
  ?:  ?=(%verified -.u.pending.db)
    ?:  =(proof proof.u.pending.db)  [%replayed db]
    [%rejected %proof-conflict]
  =/  decision
    (decide:stead-code-pack-push destination.claim generation.db current.db proof protected permitted)
  ?:  ?=(%rejected -.decision)  [%rejected reason.decision]
  [%applied db(pending [~ %verified row.u.pending.db proof])]
++  commit
  |=  $:  db=ledger  claim=intent  proof=checked  who=actor  now=@ud  incarnation=@t
          permitted=allow  protected=(set @t)
      ==
  ^-  commit-result
  ?.  (valid-intent claim)  [%rejected %invalid-intent]
  ?.  (approved who now permitted protected claim)  [%rejected %denied]
  ?.  (token-valid:stead-session incarnation)  [%rejected %incarnation-conflict]
  ?.  =(destination.claim destination.current.db)  [%rejected %scope-conflict]
  =/  prior  (~(get by receipts.db) request.claim)
  ?^  prior
    ?:  ?&  =(claim claim.row.u.prior)
            (same-actor:stead-session owner.row.u.prior who)
            =(proof proof.u.prior)
            (gte now accepted-at.result.u.prior)
        ==
      [%replayed db result.u.prior]
    [%rejected %request-reused]
  ?:  (used db request.claim)  [%rejected %request-reused]
  ?.  =(incarnation incarnation.claim)  [%rejected %incarnation-conflict]
  ?.  (scope-matches db claim)  [%rejected %stale-base]
  ?:  (gte generation.db max-advances)  [%rejected %history-capacity]
  ?~  pending.db  [%rejected %no-pending]
  ?.  (owner-matches row.u.pending.db claim who now)  [%rejected %attempt-conflict]
  ?.  ?=(%verified -.u.pending.db)  [%rejected %not-verified]
  ?.  &((proof-matches claim proof) =(proof proof.u.pending.db))  [%rejected %proof-conflict]
  =/  decision
    (decide:stead-code-pack-push destination.claim generation.db current.db proof protected permitted)
  ?:  ?=(%rejected -.decision)  [%rejected reason.decision]
  =/  accepted=receipt  [1 next.decision who now]
  =/  saved=record  [row.u.pending.db proof accepted]
  =/  next-receipts  (~(put by receipts.db) request.claim saved)
  =/  next-journal  [request.claim journal.db]
  =/  next=ledger
    %=  db
      current  pack.next.decision
      generation  generation.next.decision
      last  now
      pending  ~
      receipts  next-receipts
      journal  next-journal
    ==
  [%applied next accepted]
++  promote
  |=  [db=ledger row=promotion now=@ud]
  ^-  (each ledger @tas)
  ?.  (valid:stead-code-pack-promotion row)  [%| %invalid-promotion]
  ?.  =(now accepted-at.row)  [%| %clock-conflict]
  ?:  (used db request.row)  [%| %request-reused]
  ?.  &((gte now last.db) =(base.row current.db))  [%| %stale-base]
  ?.  (lth generation.db max-advances)  [%| %history-capacity]
  ?.  =(generation.decision.candidate.row +(generation.db))  [%| %generation-conflict]
  ?:  &(?=(^ pending.db) (lth now until.row.u.pending.db))
    [%| %pending-conflict]
  =/  next
    %=  db
      current     pack.decision.candidate.row
      generation  +(generation.db)
      last        now
      pending     ~
      promotions  (~(put by promotions.db) request.row row)
      journal     [request.row journal.db]
    ==
  [%& next]
++  still
  |=  [current=manifest generation=@ud row=admission proof=checked]
  ^-  outcome:stead-code-pack-push
  =/  claim  claim.row
  ?.  (proof-matches claim proof)  [%rejected %proof-conflict]
  ::  Historical validation reconstructs structure. Current role or protection
  ::  may have changed after a valid receipt was issued.
  (decide:stead-code-pack-push destination.claim generation current proof ~ |=([action:stead-code-receive update] &))
++  valid
  |=  [db=ledger anchor=entry:stead-code-pack-anchor]
  ^-  ?
  =/  seed  (open anchor)
  ?~  seed  |
  ?.  ?&  =(2 version.db)
          =(seed.db seed.u.seed)
          =(seed-request.db seed-request.u.seed)
          =(birth.db birth.u.seed)
          (lte generation.db max-advances)
          (lte serial.db max-number)
          =(generation.db (add ~(wyt by receipts.db) ~(wyt by promotions.db)))
          =(generation.db (lent (scag +(max-advances) journal.db)))
      ==
    |
  =/  current  current.u.seed
  =/  sequence  (flop journal.db)
  =/  generation=@ud  0
  =/  attempt=@ud  0
  =/  accepted-at=@ud  birth.u.seed
  |-
  ^-  ?
  ?~  sequence
    ?.  &(=(current current.db) =(accepted-at last.db))  |
    ?~  pending.db  (gte serial.db attempt)
    =/  row  row.u.pending.db
    ?.  ?&  (valid-admission row)
            (scope-matches db claim.row)
            (gth serial.db attempt)
            =(serial.db attempt.claim.row)
            (gte since.row accepted-at)
            !(used db request.claim.row)
        ==
      |
    ?:  ?=(%admitted -.u.pending.db)  &
    =/  expected  (still current generation row proof.u.pending.db)
    ?=(%candidate -.expected)
  =/  found  (~(get by receipts.db) i.sequence)
  =/  promoted  (~(get by promotions.db) i.sequence)
  ?^  promoted
    ?.  ?&  ?=(~ found)  (valid:stead-code-pack-promotion u.promoted)
            =(request.u.promoted i.sequence)  !=(seed-request.db i.sequence)
            =(base.u.promoted current)  (gte accepted-at.u.promoted accepted-at)
            =(generation.decision.candidate.u.promoted +(generation))
        ==
      |
    %=  $
      sequence     t.sequence
      current      pack.decision.candidate.u.promoted
      generation   +(generation)
      accepted-at  accepted-at.u.promoted
    ==
  ?~  found  |
  =/  row  row.u.found
  =/  out  result.u.found
  ?.  ?&  (valid-admission row)
          =(i.sequence request.claim.row)
          !=(seed-request.db i.sequence)
          =(1 version.out)
          (gth attempt.claim.row attempt)
          (gte since.row accepted-at)
          (owner-matches row claim.row owner.out accepted-at.out)
          (live:stead-session owner.out accepted-at.out)
      ==
    |
  =/  expected  (still current generation row proof.u.found)
  ?.  ?=(%candidate -.expected)  |
  ?.  =(next.expected decision.out)  |
  %=  $
    sequence     t.sequence
    current      pack.next.expected
    generation   +(generation)
    attempt      attempt.claim.row
    accepted-at  accepted-at.out
  ==
--

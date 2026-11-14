::  Pure control carrier for canonical private messages. Transport must
::  authenticate the worker and supply the ledger and anchor selected by Home.
/+  stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-control, stead-code-pack-proof, stead-code-credentials, stead-session, stead-codec
|%
+$  state-ledger  ledger:stead-code-pack-ledger
+$  anchor  entry:stead-code-pack-anchor
+$  manifest  manifest:stead-code-pack-anchor
+$  actor  actor:stead-session
+$  context  context:stead-code-pack-control
+$  outcome  outcome:stead-code-pack-control
+$  mode  ?(%admit %verify %commit %receipt)
+$  input
  [step=mode request=@t admission=@t digest=@t proof=(unit @t)]
++  pin
  |=  who=actor
  ^-  pin:stead-code-pack-proof
  [ship.who principal.who binding.who revision.who]
++  historical-base
  |=  [db=state-ledger seed=anchor generation=@ud]
  ^-  (unit manifest)
  ?:  =(generation 0)  [~ pack.row.seed]
  ?.  (lte generation generation.db)  ~
  =/  index  (sub generation.db generation)
  =/  entries  (slag index journal.db)
  ?~  entries  ~
  =/  found  (history:stead-code-pack-ledger db i.entries)
  ?~  found  ~
  ?.  =(generation generation.u.found)  ~
  [~ pack.u.found]
++  same-admission
  |=  [view=admission-view:stead-code-pack-proof row=admission:stead-code-pack-ledger]
  ^-  ?
  ?&  =(claim.view claim.row)
      =(since.view since.row)
      =(until.view until.row)
      =(who.view (pin owner.row))
  ==
++  apply
  |=  [prior=(unit state-ledger) seed=anchor gates=context bearer=@t message=input]
  ^-  outcome
  ?.  ?&  available.gates  !sealed.gates  !retired.gates
          (token-valid:stead-session incarnation.gates)
          =(selected.gates destination.pack.row.seed)
      ==
    [%refused %denied]
  =/  who
    (check:stead-code-credentials book.gates bearer selected.gates %write now.gates member.gates allowed.gates)
  ?~  who  [%refused %denied]
  ?.  (uuid:stead-codec request.message)  [%refused %invalid-admission]
  =/  seed-state  (open:stead-code-pack-ledger seed)
  ?~  seed-state  [%refused %denied]
  =/  db
    ?~(prior u.seed-state u.prior)
  ?.  (valid:stead-code-pack-ledger db seed)  [%refused %invalid-ledger]
  ?:  ?=(%receipt step.message)
    (replay db seed gates bearer u.who message)
  =/  decoded
    (decode-admission:stead-code-pack-proof admission.message digest.message current.db)
  ?~  decoded  [%refused %invalid-admission]
  =/  claim  claim.u.decoded
  ?.  ?&  =(who.u.decoded (pin u.who))
          =(request.claim request.message)
          =(generation.claim generation.db)
          =(incarnation.claim incarnation.gates)
      ==
    [%refused %denied]
  ?:  ?=(%admit step.message)
    ::  For a new job, Home must construct the canonical admission within
    ::  this event. A remote caller cannot choose Home's admission clock.
    ?.  ?=(~ proof.message)  [%refused %invalid-admission]
    =/  reused
      ?~  pending.db  |
      (same-admission u.decoded row.u.pending.db)
    ?.  ?|  reused
            ?&  =(since.u.decoded now.gates)
                =(until.u.decoded (min expires.u.who (add now.gates 300.000)))
            ==
          ==
      [%refused %invalid-admission]
    (apply:stead-code-pack-control db gates bearer [%admit claim ~])
  ?~  proof.message  [%refused %invalid-proof]
  ?~  pending.db  [%refused %denied]
  ?.  (same-admission u.decoded row.u.pending.db)  [%refused %denied]
  =/  evidence
    (decode-proof:stead-code-pack-proof u.proof.message admission.message digest.message current.db)
  ?~  evidence  [%refused %invalid-proof]
  ?:  ?=(%verify step.message)
    (apply:stead-code-pack-control db gates bearer [%verify claim u.evidence])
  (apply:stead-code-pack-control db gates bearer [%commit claim u.evidence])
++  replay
  |=  [db=state-ledger seed=anchor gates=context bearer=@t who=actor message=input]
  ^-  outcome
  ?~  proof.message  [%refused %invalid-proof]
  ::  The request selects one indexed row. Only an exact canonical admission
  ::  matching it can subsequently recover the receipt or its historical base.
  =/  prior  (~(get by receipts.db) request.message)
  ?~  prior  [%refused %denied]
  =/  row  row.u.prior
  ?.  =((pin who) (pin owner.row))
    [%refused %denied]
  =/  base  (historical-base db seed generation.claim.row)
  ?~  base  [%refused %invalid-ledger]
  =/  decoded
    (decode-admission:stead-code-pack-proof admission.message digest.message u.base)
  ?~  decoded  [%refused %denied]
  ?.  (same-admission u.decoded row)  [%refused %denied]
  =/  evidence
    (decode-proof:stead-code-pack-proof u.proof.message admission.message digest.message u.base)
  ?~  evidence  [%refused %invalid-proof]
  (apply:stead-code-pack-control db gates bearer [%receipt claim.row u.evidence])
--

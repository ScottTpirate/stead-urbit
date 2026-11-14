::  Typed control gate for a single Home-selected external Git ledger.
::  No endpoint or bearer issuance is provided here. The eventual private
::  carrier must supply a pure worker predicate from its authenticated response.
::  The predicate must have no side effects and must bind the exact admission.
/+  stead-code-credentials, stead-code-pack-ledger, stead-codec, stead-session, stead-code-receive
|%
+$  state-ledger  ledger:stead-code-pack-ledger
+$  scope  scope:stead-code-credentials
+$  intent  intent:stead-code-pack-ledger
+$  checked  checked:stead-code-pack-ledger
+$  admission  admission:stead-code-pack-ledger
+$  actor  actor:stead-session
+$  worker-check  $-([admission checked] ?)
+$  context
  $:  selected=scope  now=@ud  incarnation=@t
      available=?  sealed=?  retired=?
      book=ledger:stead-code-credentials
      member=membership:stead-code-credentials
      allowed=allowance:stead-code-credentials
      permitted=allow:stead-code-pack-ledger  protected=(set @t)
      worker=worker-check
  ==
+$  command
  $%  [%admit claim=intent ~]
      [%verify claim=intent proof=checked]
      [%commit claim=intent proof=checked]
      [%receipt claim=intent proof=checked]
  ==
+$  outcome
  $%  [%pending result=pending-result:stead-code-pack-ledger]
      [%committed result=commit-result:stead-code-pack-ledger]
      [%refused reason=@tas]
  ==
++  worker-admission
  |=  [db=state-ledger claim=intent current=actor now=@ud]
  ^-  (unit admission)
  ?~  pending.db  ~
  =/  row  row.u.pending.db
  ?.  (owner-matches:stead-code-pack-ledger row claim current now)  ~
  [~ row]
++  apply
  |=  [db=state-ledger gates=context bearer=@t input=command]
  ^-  outcome
  ?.  ?&  available.gates  !sealed.gates  !retired.gates
          (token-valid:stead-session incarnation.gates)
          =(selected.gates destination.current.db)
          =(selected.gates destination.claim.input)
      ==
    [%refused %denied]
  =/  who
    (check:stead-code-credentials book.gates bearer selected.gates %write now.gates member.gates allowed.gates)
  ?~  who  [%refused %denied]
  =/  claim  claim.input
  ?.  (valid-intent:stead-code-pack-ledger claim)  [%refused %invalid-intent]
  ::  Check the manifest's byte-hex HEAD separately to keep the reducer's
  ::  existing bound on extra protected refs. It is immutable in this profile.
  =/  permitted=allow:stead-code-pack-ledger
    |=  [action=action:stead-code-receive change=update:stead-code-pack-ledger]
    &(!=((bytes-hex:stead-codec name.change) head.current.db) (permitted.gates action change))
  ?.  (approved:stead-code-pack-ledger u.who now.gates permitted protected.gates claim)
    [%refused %denied]
  ?:  ?=(%admit -.input)
    [%pending (admit:stead-code-pack-ledger db claim u.who now.gates incarnation.gates permitted protected.gates)]
  ::  A committed receipt can outlive its worker attempt. Require current
  ::  uploader authority and exact original evidence, from the stored row.
  ::  In this arm there is no reducer path to new acceptance.
  ?:  ?=(%receipt -.input)
    =/  prior  (~(get by receipts.db) request.claim)
    ?~  prior  [%refused %denied]
    ?.  ?&  =(claim.row.u.prior claim)
            (same-actor:stead-session owner.row.u.prior u.who)
            =(proof.u.prior proof.input)
            (gte now.gates accepted-at.result.u.prior)
        ==
      [%refused %denied]
    [%committed [%replayed db result.u.prior]]
  ?.  =(incarnation.gates incarnation.claim)  [%refused %denied]
  =/  row  (worker-admission db claim u.who now.gates)
  ?~  row  [%refused %denied]
  ?.  (proof-matches:stead-code-pack-ledger claim proof.input)  [%refused %proof-conflict]
  ?.  (worker.gates u.row proof.input)  [%refused %worker-denied]
  ?:  ?=(%commit -.input)
    [%committed (commit:stead-code-pack-ledger db claim proof.input u.who now.gates incarnation.gates permitted protected.gates)]
  [%pending (verify:stead-code-pack-ledger db claim proof.input u.who now.gates incarnation.gates permitted protected.gates)]
--

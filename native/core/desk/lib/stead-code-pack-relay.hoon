::  Apply one relay write under the operator's current per-incarnation pin.
::  Availability, selected anchor, membership and policy still come from Home.
/+  stead-code-pack-relay-wire, stead-code-pack-owner, stead-code-pack-control, stead-code-pack-ledger, stead-code-pack-anchor, stead-code-pack-worker-signature
|%
++  write
  |=  $:  gates=context:stead-code-pack-control
          prior=(unit ledger:stead-code-pack-ledger)  genesis=entry:stead-code-pack-anchor
          project=@t  bearer=@t  worker=pin:stead-code-pack-worker-signature  frame=input:stead-code-pack-relay-wire
      ==
  ^-  response:stead-code-pack-owner
  ?.  =(project project.selected.gates)  (refused:stead-code-pack-owner %denied)
  =/  task  task.frame
  ?:  ?=(%advertise -.task)  (refused:stead-code-pack-owner %denied)
  ?:  ?=([?(%verify %commit) *] task)
    =/  attestation  attestation.frame
    ?~  attestation  (refused:stead-code-pack-owner %worker-denied)
    =/  bytes=@t  +>+.task
    ?.  (verify:stead-code-pack-worker-signature worker generation.u.attestation bytes signature.u.attestation)
      (refused:stead-code-pack-owner %worker-denied)
    =/  accept=worker-check:stead-code-pack-control
      |=  [row=admission:stead-code-pack-ledger proof=checked:stead-code-pack-ledger]
      (proof-matches:stead-code-pack-ledger claim.row proof)
    (apply:stead-code-pack-owner prior genesis gates(worker accept) ['' project bearer request.frame task])
  ?.  ?=(~ attestation.frame)  (refused:stead-code-pack-owner %denied)
  (apply:stead-code-pack-owner prior genesis gates ['' project bearer request.frame task])
--

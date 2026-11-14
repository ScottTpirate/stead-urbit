::  The owner-local pack control for the isolated fake installation profile.
::  The Gall driver must authenticate the same-ship worker before calling it.
/+  stead-codec, stead-code-credentials, stead-code-pack-anchor, stead-code-pack-admit, stead-code-pack-carrier, stead-code-pack-control, stead-code-pack-ledger, stead-code-pack-proof, stead-git, stead-session
=,  stead-codec
|%
+$  scope  scope:stead-code-credentials
+$  ledger  ledger:stead-code-pack-ledger
+$  receipt  receipt:stead-code-pack-ledger
+$  update  update:stead-code-pack-ledger
+$  task
  $%  [%admit wire=@t changes=(list update)]
      [%verify admission=@t digest=@t proof=@t]
      [%commit admission=@t digest=@t proof=@t]
      [%receipt admission=@t digest=@t proof=@t]
      [%advertise ~]
  ==
+$  command  [nonce=@t project=@t bearer=@t request=@t task=task]
+$  response  [body=@t changed=(unit ledger)]
++  refused
  |=  reason=@tas
  ^-  response
  [(canonical (object ~[['status' 'refused'] ['reason' reason]])) ~]
++  accepted
  |=  [raw=@t digest=@t result=receipt]
  ^-  @t
  =/  source  (read-wire:stead-code-pack-proof raw)
  =/  fields  ~['scope' 'actor' 'request_id' 'wire_sha256' 'changes' 'update_count']
  =/  saved=(list [@t json])
    (turn fields |=(key=@t [key (~(got by source) key)]))
  =/  metadata
    %-  object
    :~  ['protocol' 'stead.git-pack-accepted/1']
        ['status' 'accepted']
        ['admission_sha256' digest]
        ['candidate_snapshot' snapshot.pack.decision.result]
        ['generation' (decimal generation.decision.result)]
        ['accepted_at_ms' (decimal accepted-at.result)]
    ==
  ?>  ?=([%o *] metadata)
  =/  claim  (~(uni by p.metadata) (malt saved))
  (cat 3 (canonical [%o claim]) 10)
++  fresh-admission
  |=  [db=ledger gates=context:stead-code-pack-control cmd=command]
  ^-  (unit result:stead-code-pack-admit)
  ?>  ?=(%admit -.task.cmd)
  =/  who
    (check:stead-code-credentials book.gates bearer.cmd selected.gates %write now.gates member.gates allowed.gates)
  ?~  who  ~
  =/  changes  changes.task.cmd
  ?.  (lte (lent (scag 33 changes)) 32)  ~
  ?.  %+  levy  changes
      |=  change=update
      ?&  (lte (met 3 name.change) 1.024)
          (lte (met 3 prior.change) 20)
          (lte (met 3 target.change) 20)
          =((oid-text:stead-git prior.change) (fall (~(get by refs.current.db) (bytes-hex name.change)) (oid-text:stead-git 0x0)))
      ==
    ~
  =/  resumed=(unit admission:stead-code-pack-ledger)
    ?~  pending.db  ~
    ?.  ?&  =(request.cmd request.claim.row.u.pending.db)
        (lth now.gates until.row.u.pending.db)
        ==
      ~
    [~ row.u.pending.db]
  =/  attempt  ?~(resumed +(serial.db) attempt.claim.u.resumed)
  =/  when  ?~(resumed now.gates since.u.resumed)
  =/  author  ?~(resumed u.who owner.u.resumed)
  =/  claim=intent:stead-code-pack-ledger
    [selected.gates snapshot.current.db generation.db wire.task.cmd request.cmd attempt incarnation.gates changes]
  (build:stead-code-pack-admit selected.gates claim author when current.db)
++  apply
  |=  [prior=(unit ledger) seed=entry:stead-code-pack-anchor gates=context:stead-code-pack-control cmd=command]
  ^-  response
  =/  has-state  (open:stead-code-pack-ledger seed)
  ?~  has-state  (refused %denied)
  =/  db  ?~(prior u.has-state u.prior)
  =/  message
    ^-  (unit input:stead-code-pack-carrier)
    ?:  ?=(%advertise -.task.cmd)  ~
    ?:  ?=(%admit -.task.cmd)
      =/  made  (fresh-admission db gates cmd)
      ?~  made  ~
      [~ %admit request.cmd wire.u.made digest.u.made ~]
    [~ -.task.cmd request.cmd admission.task.cmd digest.task.cmd [~ proof.task.cmd]]
  ?~  message  (refused %denied)
  =/  out  (apply:stead-code-pack-carrier prior seed gates bearer.cmd u.message)
  ?:  ?=(%refused -.out)  (refused reason.out)
  ?:  ?=(%pending -.out)
    ?:  ?=(%rejected -.result.out)  (refused reason.result.out)
    =/  body
      ?:  ?=(%admit step.u.message)  admission.u.message
      (canonical (object ~[['status' 'verified']]))
    [body ?:(?=(%applied -.result.out) [~ next.result.out] ~)]
  ?:  ?=(%rejected -.result.out)  (refused reason.result.out)
  :_  ?:(?=(%applied -.result.out) [~ next.result.out] ~)
  (accepted admission.u.message digest.u.message result.result.out)
--

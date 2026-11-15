::  Reserved pure run transitions. No wire, timer, process or Home route invokes
::  this core. Gates are trusted internal adapters, never caller assertions.
::  A returned intent is candidate data. The eventual single-history wrapper
::  must commit its real Work/Inbox/Doc effect plus this transition atomically.
/+  stead-codec, stead-core, stead-actor, stead-run-state
=,  stead-codec
=,  stead-run-state
=>
|%
+$  staged
  [db=state book=live intents=(list candidate-intent) error=@t]
++  named
  |=  raw=@t
  ^-  ?
  &((gth (met 3 raw) 0) (prose raw 256))
++  question-valid
  |=  raw=@t
  ^-  ?
  &((gth (met 3 raw) 0) (prose raw 2.048))
++  binding
  |=  actor=verified:stead-actor
  ^-  [id=@t revision=@ud expires=@ud]
  ?:  ?=(%native -.actor)
    [binding.identity.context.actor revision.identity.context.actor expires.context.actor]
  [binding.context.actor revision.context.actor expires.context.actor]
++  contract-valid
  |=  [item=contract now=@ud]
  ^-  ?
  =/  contract-ids=(list @t)
    ~[project.item work.item requester.item owner.item worker.item binding.item definition.item runtime.item]
  =/  contract-revisions=(list @ud)
    ~[epoch.item execution-revision.item binding-revision.item definition-revision.item runtime-revision.item]
  ?&  (lte (met 0 home.item) 128)
      (levy contract-ids uuid)
      !=(owner.item worker.item)
      (levy contract-revisions |=(n=@ud &((gth n 0) (uint64 n))))
      (digest-valid execution-digest.item)  (digest-valid context.item)
      (gth duration.budget.item 0)  (lte duration.budget.item 3.600.000)
      (usage-valid limits.budget.item)
      ?:  (gth network.limits.budget.item 0)
        &((gth tokens.limits.budget.item 0) (gth cost.limits.budget.item 0))
      &(=(0 tokens.limits.budget.item) =(0 cost.limits.budget.item))
      (gth deadline.item now)  (uint64 deadline.item)
      (lte deadline.item (add now duration.budget.item))
      (lte deadline.item expires.grant.item)  (uint64 expires.grant.item)
      =(project.item project.grant.item)  =(worker.item principal.grant.item)
      !revoked.grant.item
      ?|(=('contributor' role.grant.item) =('maintainer' role.grant.item))
      =(73 (met 3 grant-key.item))
      =((scope-key:stead-core project.item (cut 3 [37 36] grant-key.item)) grant-key.item)
      (uuid (cut 3 [37 36] grant-key.item))
      (gth (lent targets.item) 0)  (lte (lent targets.item) 4)
      =((lent targets.item) (lent ~(tap in (silt (turn targets.item |=(row=target outcome.row))))))
      =((lent targets.item) (lent ~(tap in (silt (turn targets.item |=(row=target [collection.row document.row]))))))
      %+  levy  targets.item
      |=  row=target
      ?&  (uuid outcome.row)  (uuid collection.row)  (uuid document.row)
          (uint64 revision.row)
          ?:(=(0 revision.row) =('' markdown.row) (digest-valid markdown.row))
      ==
  ==
++  deny
  |=  [db=state book=live cmd=command reason=@t]
  ^-  transition
  =/  body
    %-  canonical  %-  object
    :~  ['protocol' 'stead.run-result/1']  ['status' 'rejected']
        ['request_id' request.cmd]  ['canonical_sha256' (hash 'stead.run-command/1' (command-bytes cmd))]
        ['error' reason]
    ==
  [body db book ~ ~]
++  terminal
  |=  value=phase
  ^-  ?
  ?=(?(%submitted %failed %canceled) value)
++  worker
  |=  [actor=verified:stead-actor item=contract]
  ^-  ?
  =/  who  (binding actor)
  &(=(worker.item (principal:stead-actor actor)) =(binding.item id.who) =(binding-revision.item revision.who))
++  lease-live
  |=  [db=state book=live key=run-key row=head now=@ud]
  ^-  ?
  =/  current  (~(get by leases.book) key)
  ?~  current  |
  ?.  &(=(attempt.row attempt.u.current) =(incarnation.book incarnation.u.current))  |
  =/  claim  (~(get by attempts.db) [key attempt.row])
  ?~  claim  |
  &((gth until.u.claim now) (lte heartbeat.u.claim now) ?=(?(%running %waiting) disposition.u.claim))
++  effects-for
  |=  [db=state key=run-key number=@ud]
  ^-  (list [[key=run-key attempt=@ud id=@t] effect])
  %+  skim  ~(tap by effects.db)
  |=  [entry=[key=run-key attempt=@ud id=@t] value=effect]
  &(=(key key.entry) =(number attempt.entry))
++  settled-all
  |=  [db=state key=run-key number=@ud]
  ^-  ?
  (levy (effects-for db key number) |=([entry=[run-key @ud @t] row=effect] =(%settled status.row)))
++  spend
  |=  [used=usage extra=usage limits=usage]
  ^-  (unit usage)
  =/  total=usage
    [(add tools.used tools.extra) (add network.used network.extra) (add tokens.used tokens.extra) (add cost.used cost.extra) (add input.used input.extra) (add output.used output.extra)]
  ?.  ?&  (lte tools.total tools.limits)  (lte network.total network.limits)
          (lte tokens.total tokens.limits)  (lte cost.total cost.limits)
          (lte input.total input.limits)  (lte output.total output.limits)
      ==  ~
  (some total)
++  intent-valid
  |=  [item=intent issued=contract]
  ^-  ?
  ?.  &((uuid id.item) (usage-valid charge.item))  |
  ?:  =(%provider-call kind.item)
    ?&  (uuid provider.item)  (digest-valid request-digest.item)  ?=(~ result.item)
        =(1 network.charge.item)  (gth tokens.charge.item 0)  (gth cost.charge.item 0)
        (gth network.limits.budget.issued 0)
    ==
  ?~  result.item  |
  ?&  =('' provider.item)  =('' request-digest.item)
      (result-valid u.result.item)
      (lien targets.issued |=(row=target =(outcome.row outcome.u.result.item)))
      =(0 network.charge.item)  =(0 tokens.charge.item)  =(0 cost.charge.item)
  ==
++  finish-head
  |=  [db=state book=live key=run-key row=head disposition=?(%submitted %failed %canceled)]
  ^-  [db=state book=live]
  =.  db  db(heads (~(put by heads.db) key row(phase disposition)))
  =/  previous  (~(get by attempts.db) [key attempt.row])
  =?  db  ?=(^ previous)
    db(attempts (~(put by attempts.db) [key attempt.row] u.previous(disposition ?:(=(%submitted disposition) %submitted ?:(=(%failed disposition) %failed %canceled)))))
  [db book(leases (~(del by leases.book) key))]
++  next-claim
  |=  [db=state book=live key=run-key row=head actor=verified:stead-actor admitted=membership now=@ud]
  ^-  staged
  =/  number  +(attempt.row)
  ?:  (gth number 3)  [db book ~ 'attempt_limit']
  =/  until
    (min (add now 120.000) (min expires:(binding actor) (min expires.admitted (min deadline.contract.row expires.grant.contract.row))))
  ?:  (lte until now)  [db book ~ 'expired_authority']
  =/  previous  (~(get by attempts.db) [key attempt.row])
  =?  db  ?=(^ previous)
    db(attempts (~(put by attempts.db) [key attempt.row] u.previous(disposition %replaced)))
  =/  current=attempt
    [(principal:stead-actor actor) binding.contract.row binding-revision.contract.row (audit-bytes:stead-actor actor) now now until %running]
  =.  db  db(attempts (~(put by attempts.db) [key number] current), heads (~(put by heads.db) key row(phase %running, attempt number)))
  =.  book  book(leases (~(put by leases.book) key [number incarnation.book]))
  [db book ~[[%execution key number 0 digest.row]] '']
++  mutate
  |=  [db=state book=live cmd=command actor=verified:stead-actor admitted=membership now=@ud gates=gates row=head]
  ^-  staged
  =/  key=run-key  [project.cmd run.cmd]
  =/  op  operation.cmd
  =/  issued  contract.row
  ?:  ?=(%cancel -.op)
    ?:  (terminal phase.row)  [db book ~ 'terminal_run']
    ?.  (named reason.op)  [db book ~ 'invalid_reason']
    =/  next  (finish-head db book key row %canceled)
    [db.next book.next ~[[%stop key attempt.row]] '']
  ?:  ?=(%reconcile -.op)
    =/  prior  (~(get by effects.db) [key attempt.row id.item.op])
    ?~  prior  [db book ~ 'unknown_effect']
    ?.  &(=(%settled status.item.op) (digest-valid evidence.item.op) (digest-valid result-digest.item.op))
      [db book ~ 'invalid_reconciliation']
    ?:  =(%settled status.u.prior)
      [db book ~ ?:(&(=(evidence.u.prior evidence.item.op) =(result-digest.u.prior result-digest.item.op)) '' 'effect_conflict')]
    ?.  (settled.gates issued attempt.row u.prior item.op now)  [db book ~ 'unverified_reconciliation']
    [db(effects (~(put by effects.db) [key attempt.row id.item.op] u.prior(status %settled, evidence evidence.item.op, result-digest result-digest.item.op))) book ~ '']
  ?:  (terminal phase.row)  [db book ~ 'terminal_run']
  ?.  &((pins.gates issued %execute now) (original.gates issued now))  [db book ~ 'stale_contract_or_authority']
  ?:  ?|((gte now deadline.issued) (gte now expires.grant.issued))  [db book ~ 'expired_authority']
  ?:  ?=(%answer -.op)
    ?.  &(human.admitted =(%waiting phase.row) =(question.row question.op) (question-valid text.op))
      [db book ~ 'invalid_answer']
    =/  prior  (~(get by questions.db) [key question.op])
    ?~  prior  [db book ~ 'unknown_question']
    ?^  answer.u.prior  [db book ~ 'already_answered']
    =/  who  (principal:stead-actor actor)
    [db(questions (~(put by questions.db) [key question.op] u.prior(answer (some [text.op who now])))) book ~[[%answer key question.op who text.op]] '']
  ?.  (worker actor issued)  [db book ~ 'wrong_worker']
  ?:  ?=(%claim -.op)
    ?.  &(=(%queued phase.row) =(0 attempt.row))  [db book ~ 'already_claimed']
    (next-claim db book key row actor admitted now)
  ?:  ?=(%replace -.op)
    ?.  &((gth attempt.row 0) (digest-valid evidence.op))  [db book ~ 'invalid_replacement']
    ?:  (lease-live db book key row now)  [db book ~ 'live_attempt']
    ?.  (settled-all db key attempt.row)  [db book ~ 'effects_unresolved']
    =/  effects-digest  (hash 'stead.run-effects/1' (bytes-hex (jam (effects-for db key attempt.row))))
    ?.  (reconciled.gates issued attempt.row effects-digest evidence.op now)  [db book ~ 'reconciliation_required']
    (next-claim db book key row actor admitted now)
  ?.  (lease-live db book key row now)  [db book ~ 'stale_lease']
  =/  claim  (~(got by attempts.db) [key attempt.row])
  ::  Credential replacement cannot extend an old attempt merely because the
  ::  stable principal/binding still matches. Reconcile and claim a new attempt.
  ?.  =(audit.claim (audit-bytes:stead-actor actor))  [db book ~ 'stale_lease']
  ?:  ?=(%heartbeat -.op)
    =/  until  (min (add now 120.000) (min expires:(binding actor) (min expires.admitted (min deadline.issued expires.grant.issued))))
    [db(attempts (~(put by attempts.db) [key attempt.row] claim(heartbeat now, until until))) book ~ '']
  ?:  ?=(%resume -.op)
    ?.  &(=(%waiting phase.row) =(question.row question.op))  [db book ~ 'not_clarification_wait']
    =/  prior  (~(get by questions.db) [key question.op])
    ?~  prior  [db book ~ 'unknown_question']
    ?~  answer.u.prior  [db book ~ 'answer_required']
    [db(heads (~(put by heads.db) key row(phase %running)), attempts (~(put by attempts.db) [key attempt.row] claim(disposition %running))) book ~[[%execution key attempt.row question.op digest.row]] '']
  ?.  =(%running phase.row)  [db book ~ 'not_running']
  ?:  ?=(%wait -.op)
    ?.  (question-valid text.op)  [db book ~ 'invalid_question']
    ?:  (gte (lent ~(tap by questions.db)) 4.096)  [db book ~ 'capacity_exceeded']
    =/  sequence  +(question.row)
    =/  who  (principal:stead-actor actor)
    [db(heads (~(put by heads.db) key row(phase %waiting, question sequence)), attempts (~(put by attempts.db) [key attempt.row] claim(disposition %waiting)), questions (~(put by questions.db) [key sequence] [text.op who now ~])) book ~[[%question key sequence who text.op]] '']
  ?:  ?=(%fail -.op)
    ?.  &((named reason.op) (digest-valid evidence.op))  [db book ~ 'invalid_failure']
    =/  next  (finish-head db book key row %failed)
    [db.next book.next ~ '']
  ?:  ?=(%finish -.op)
    ?.  (result-valid result.op)  [db book ~ 'invalid_result']
    ?.  (lien targets.issued |=(target=target =(outcome.target outcome.result.op)))
      [db book ~ 'result_scope_conflict']
    ?.  (settled-all db key attempt.row)  [db book ~ 'effects_unresolved']
    ?.  (result.gates issued attempt.row result.op now)  [db book ~ 'unverified_result']
    =/  next  (finish-head db book key row(result (some result.op)) %submitted)
    [db.next book.next ~[[%submitted key attempt.row result.op]] '']
  ?:  ?=(%intent -.op)
    ?.  (intent-valid item.op issued)  [db book ~ 'invalid_effect']
    =/  prior  (~(get by effects.db) [key attempt.row id.item.op])
    ?^  prior  [db book ~ ?:(=(intent.u.prior item.op) '' 'effect_conflict')]
    ::  Bind approved provider, sealed request/context/egress and exact reserved
    ::  charge before an effect exists. A Doc proposal binds its actual scoped
    ::  destination and result. Settlement alone cannot authorize dispatch.
    ?.  (effect.gates actor issued attempt.row item.op now)
      [db book ~ 'effect_authority_denied']
    ?:  ?|((gte (lent ~(tap by effects.db)) 4.096) (gte (lent (effects-for db key attempt.row)) 32))
      [db book ~ 'capacity_exceeded']
    =/  spent  (spend used.row charge.item.op limits.budget.issued)
    ?~  spent  [db book ~ 'budget_exhausted']
    [db(heads (~(put by heads.db) key row(used u.spent)), effects (~(put by effects.db) [key attempt.row id.item.op] [item.op %pending '' ''])) book ~[[%effect key attempt.row item.op]] '']
  ?:  ?=(%settle -.op)
    =/  prior  (~(get by effects.db) [key attempt.row id.item.op])
    ?~  prior  [db book ~ 'unknown_effect']
    ?.  &((digest-valid evidence.item.op) ?:(=(%settled status.item.op) (digest-valid result-digest.item.op) =('' result-digest.item.op)))
      [db book ~ 'invalid_settlement']
    ?:  !=(%pending status.u.prior)
      [db book ~ ?:(&(=(status.u.prior status.item.op) =(evidence.u.prior evidence.item.op) =(result-digest.u.prior result-digest.item.op)) '' 'reconciliation_required')]
    ?.  (settled.gates issued attempt.row u.prior item.op now)  [db book ~ 'unverified_settlement']
    [db(effects (~(put by effects.db) [key attempt.row id.item.op] u.prior(status status.item.op, evidence evidence.item.op, result-digest result-digest.item.op))) book ~ '']
  [db book ~ 'unsupported_operation']
++  commit
  |=  [old=state before=live changed=staged cmd=command actor=verified:stead-actor now=@ud capacity=shared-budget]
  ^-  transition
  =/  key=run-key  [project.cmd run.cmd]
  =/  prior  (~(get by heads.old) key)
  =/  reduction
    ?~  prior  |
    ?&  =('' error.changed)  ?=(%cancel -.operation.cmd)
        !(terminal phase.u.prior)
        (gth deadline.contract.u.prior now)  (gth expires.grant.contract.u.prior now)
    ==
  =/  reserved  (gte ordinary.capacity 4.096)
  ?:  &(reserved !&(reduction (lth security.capacity 2.048) (lth project-security.capacity 128)))
    (deny old before cmd 'capacity_exceeded')
  ?:  (gte (lent ~(tap by requests.old)) 6.144)  (deny old before cmd 'capacity_exceeded')
  =/  db  db.changed
  =/  current  (~(get by heads.db) key)
  =/  revision=@ud
    ?~  current  0
    ?:  !=('' error.changed)  revision.u.current
    ?~  prior  1
    +(revision.u.prior)
  ?:  !(uint64 revision)  (deny old before cmd 'capacity_exceeded')
  =?  db  &(?=(^ current) =('' error.changed))
    db(heads (~(put by heads.db) key u.current(revision revision)))
  =/  raw  (command-bytes cmd)
  =/  digest  (hash 'stead.run-command/1' raw)
  =/  response
    %-  canonical  %-  object
    :~  ['protocol' 'stead.run-result/1']  ['status' ?:(=('' error.changed) 'accepted' 'rejected')]
        ['request_id' request.cmd]  ['canonical_sha256' digest]  ['error' error.changed]
        ['run_id' run.cmd]  ['run_revision' (decimal revision)]
        ['attempt' ?~(current '0' (decimal attempt.u.current))]
        ['phase' ?~(current '' (scot %tas phase.u.current))]
    ==
  =/  record
    %-  canonical  %-  object
    :~  ['protocol' 'stead.run-event/1']  ['canonical_command' raw]
        ['authentication_context' (audit-bytes:stead-actor actor)]
        ['accepted_at_ms' (decimal now)]  ['receipt' response]
        ['capacity_class' ?:(reserved 'security' 'ordinary')]
    ==
  =/  request-key=request-key  [project.cmd (principal:stead-actor actor) request.cmd]
  =.  db  db(requests (~(put by requests.db) request-key [digest raw response]))
  [response db book.changed (some record) intents.changed]
--
|%
++  deny-gates
  ^-  gates
  :*  |=([actor=verified:stead-actor item=contract now=@ud] *(unit membership))
      |=([actor=verified:stead-actor item=contract operation=@tas now=@ud] |)
      |=([item=contract mode=?(%execute %read) now=@ud] |)
      |=([item=contract now=@ud] |)
      |=([actor=verified:stead-actor item=contract attempt=@ud proposal=intent now=@ud] |)
      |=([item=contract attempt=@ud reference=result-reference now=@ud] |)
      |=([item=contract attempt=@ud effect=effect resolution=settlement now=@ud] |)
      |=([item=contract attempt=@ud effects-digest=@t evidence=@t now=@ud] |)
      |=(key=request-key |)
  ==
++  empty-live
  |=  incarnation=@t
  ^-  live
  ?>  (digest-valid incarnation)
  [incarnation ~]
++  apply
  |=  [db=state book=live actor=verified:stead-actor cmd=command now=@ud gates=gates capacity=shared-budget]
  ^-  transition
  ?.  &((uuid request.cmd) (uuid project.cmd) (uuid run.cmd) (uint64 expected.cmd) (lte attempt.cmd 3) (gth now 0) (uint64 now) (digest-valid incarnation.book))
    (deny db book cmd 'invalid_request')
  ?.  &((lte ordinary.capacity 4.096) (lte security.capacity 2.048) (lte project-security.capacity 128))
    (deny db book cmd 'invalid_capacity')
  =/  raw  (command-bytes cmd)
  ?:  (gth (met 3 raw) 65.536)  (deny db book cmd 'invalid_request')
  =/  key=run-key  [project.cmd run.cmd]
  =/  prior  (~(get by heads.db) key)
  ?:  &(!?=(%issue -.operation.cmd) ?=(~ prior))
    (deny db book cmd 'denied_or_not_found')
  =/  item=contract
    ?:  ?=(%issue -.operation.cmd)  (normalize-contract item.operation.cmd)
    ?>  ?=(^ prior)
    contract.u.prior
  ::  Missing runs disclose no retained response. Callers must resolve a read
  ::  scope before entering this core; malformed typed commands still fail shut.
  ?.  =(project.item project.cmd)  (deny db book cmd 'denied_or_not_found')
  =/  admitted  (member.gates actor item now)
  ?~  admitted  (deny db book cmd 'denied_or_not_found')
  ?.  &((gth expires.u.admitted now) (pins.gates item %read now) (policy.gates actor item %read now))
    (deny db book cmd 'denied_or_not_found')
  =/  request-key=request-key  [project.cmd (principal:stead-actor actor) request.cmd]
  ?:  (used.gates request-key)  (deny db book cmd 'request_id_reuse')
  =/  previous  (~(get by requests.db) request-key)
  ?^  previous
    ?.  =(raw command.u.previous)  (deny db book cmd 'request_id_reuse')
    [response.u.previous db book ~ ~]
  ?.  (policy.gates actor item -.operation.cmd now)  (deny db book cmd 'denied_or_not_found')
  =/  changed=staged
    ?:  ?=(%issue -.operation.cmd)
      ?^  prior  [db book ~ 'run_id_reuse']
      ?.  &(=(0 expected.cmd) =(0 attempt.cmd))  [db book ~ 'revision_conflict']
      ?.  &((contract-valid item now) human.u.admitted =(requester.item (principal:stead-actor actor)) (pins.gates item %execute now) (original.gates item now))
        [db book ~ 'invalid_contract_or_authority']
      =/  project-runs  (skim ~(tap by heads.db) |=([key=run-key row=head] =(project.key project.cmd)))
      ?:  (gte (lent project-runs) 32)  [db book ~ 'capacity_exceeded']
      =/  projects  (silt (turn ~(tap by heads.db) |=([key=run-key row=head] project.key)))
      ?:  &(!(~(has in projects) project.cmd) (gte (lent ~(tap in projects)) 16))  [db book ~ 'capacity_exceeded']
      =/  row=head  [item (hash 'stead.run-contract/1' (contract-bytes item)) now 1 %queued 0 0 *usage ~]
      [db(heads (~(put by heads.db) key row)) book ~ '']
    ?~  prior  [db book ~ 'denied_or_not_found']
    ?:  (lth now issued.u.prior)  [db book ~ 'invalid_time']
    ?.  &(=(expected.cmd revision.u.prior) =(attempt.cmd attempt.u.prior))  [db book ~ 'revision_conflict']
    (mutate db book cmd actor u.admitted now gates u.prior)
  (commit db book changed cmd actor now capacity)
++  bounded
  ::  The Home's aggregate noun bound must precede this typed map traversal.
  ::  Whole ordered-history regeneration is still required after admission.
  |=  db=state
  ^-  ?
  ?.  ?&  (lte (lent ~(tap by heads.db)) 512)
          (lte (lent ~(tap by attempts.db)) 1.536)
          (lte (lent ~(tap by questions.db)) 4.096)
          (lte (lent ~(tap by effects.db)) 4.096)
          (lte (lent ~(tap by requests.db)) 6.144)
      ==  |
  =/  projects  (silt (turn ~(tap by heads.db) |=([key=run-key row=head] project.key)))
  ?.  (lte (lent ~(tap in projects)) 16)  |
  ?&  %+  levy  ~(tap in projects)
      |=  project=@t
      (lte (lent (skim ~(tap by heads.db) |=([key=run-key row=head] =(project.key project)))) 32)
      %+  levy  ~(tap by heads.db)
      |=  [key=run-key row=head]
      ?&  (uuid run.key)  =(project.key project.contract.row)
          =(contract.row (normalize-contract contract.row))
          (contract-valid contract.row issued.row)  (gth issued.row 0)  (uint64 issued.row)
          =(digest.row (hash 'stead.run-contract/1' (contract-bytes contract.row)))
          (gth revision.row 0)  (uint64 revision.row)  (lte attempt.row 3)
          (lte question.row 4.096)  (usage-valid used.row)
          ?=(^ (spend *usage used.row limits.budget.contract.row))
          ?~(result.row !?=(%submitted phase.row) &(?=(%submitted phase.row) (result-valid u.result.row)))
      ==
      %+  levy  ~(tap by attempts.db)
      |=  [entry=[key=run-key attempt=@ud] row=attempt]
      =/  parent  (~(get by heads.db) key.entry)
      ?~  parent  |
      ?&  (gth attempt.entry 0)  (lte attempt.entry attempt.u.parent)
          =(principal.row worker.contract.u.parent)
          =(binding.row binding.contract.u.parent)  =(binding-revision.row binding-revision.contract.u.parent)
          (lte (met 3 audit.row) 8.192)  (gth (met 3 audit.row) 0)
          (lte issued.u.parent started.row)  (lte started.row heartbeat.row)
          (lte heartbeat.row until.row)  (lte until.row deadline.contract.u.parent)
          (lte until.row expires.grant.contract.u.parent)
      ==
      %+  levy  ~(tap by questions.db)
      |=  [entry=[key=run-key sequence=@ud] row=question]
      =/  parent  (~(get by heads.db) key.entry)
      ?~  parent  |
      ?&  (gth sequence.entry 0)  (lte sequence.entry question.u.parent)
          (question-valid text.row)  (uuid principal.row)  (uint64 at.row)
          ?~  answer.row  &
          &((question-valid text.u.answer.row) (uuid principal.u.answer.row) (uint64 at.u.answer.row))
      ==
      %+  levy  ~(tap by effects.db)
      |=  [entry=[key=run-key attempt=@ud id=@t] row=effect]
      =/  parent  (~(get by heads.db) key.entry)
      ?~  parent  |
      ?&  (~(has by attempts.db) [key.entry attempt.entry])
          =(id.entry id.intent.row)  (intent-valid intent.row contract.u.parent)
          ?:  =(%pending status.row)
            &(=('' evidence.row) =('' result-digest.row))
          &((digest-valid evidence.row) ?:(=(%settled status.row) (digest-valid result-digest.row) =('' result-digest.row)))
      ==
      %+  levy  ~(tap by requests.db)
      |=  [key=request-key row=receipt]
      ?&  (uuid project.key)  (uuid principal.key)  (uuid request.key)
          (lte (met 3 command.row) 65.536)  (lte (met 3 response.row) 8.192)
          =(digest.row (hash 'stead.run-command/1' command.row))
      ==
  ==
++  restart
  ::  Admission only. No historical authority proof and no dispatch/recovery
  ::  action. The integrator must independently validate the ordered history.
  |=  [db=state incarnation=@t]
  ^-  [db=state book=live intents=(list candidate-intent)]
  ?>  (bounded db)
  [db (empty-live incarnation) ~]
--

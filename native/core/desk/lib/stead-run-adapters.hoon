::  Reserved native run authority. Inputs are validated Home state or one
::  atomic candidate produced by the real reducers, never wire assertions.
::  No provider dispatch, service credential, restore or saved route is added.
::  Home admits bounded Run/Doc state and authenticates its single history
::  before constructing these adapters. This module is not a restore proof.
/+  stead-codec, stead-core, stead-team, stead-principals, stead-actor, stead-product-codec, stead-product-state, stead-product-owner, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-run-state, stead-run
=,  stead-codec
=>
|%
+$  authority-snapshot
  $:  db=state:stead-team  product=state:stead-product-state
      catalog=state:stead-principals  ledger=ledger:stead-product-owner
      changes=state:stead-doc-change-state
  ==
+$  contract  contract:stead-run-state
+$  target  target:stead-run-state
+$  context-value  [bytes=@t digest=@t]
++  target-json
  |=  [project=@t row=target]
  ^-  json
  (object ~[['kind' 'document'] ['project_id' project] ['collection_id' collection.row] ['document_id' document.row] ['expected_revision' (decimal revision.row)] ['base_markdown_sha256' markdown.row]])
++  visible
  |=  [db=state:stead-team actor=authentication:stead-team item=contract now=@ud]
  ^-  ?
  ?&  =(home.item home.actor)
      (subject:stead-team db actor project.item 'work' '' work.item now)
      (gth (lent targets.item) 0)  (lte (lent targets.item) 4)
      %+  levy  targets.item
      |=  row=target
      =/  box  (~(get by boxes.db) collection.row)
      ?~  box  |
      ?&  =(project.item project.u.box)  =('shared' visibility.u.box)
          (box-access:stead-team db actor project.item collection.row now)
          !(~(has in tombs.db) [project.item 'document' collection.row document.row])
      ==
  ==
++  member
  |=  [state=authority-snapshot actor=verified:stead-actor item=contract now=@ud]
  ^-  (unit membership:stead-run-state)
  ?.  ?=(%native -.actor)  ~
  ?~  (verify-native:stead-actor db.state catalog.state context.actor now)  ~
  =/  kind  (native-kind:stead-principals catalog.state registry.db.state principal.identity.context.actor now)
  ?~  kind  ~
  ?.  ?=(?(%person %agent) u.kind)  ~
  ?.  (visible db.state context.actor item now)  ~
  =/  grants  ~(tap by grants.data.db.state)
  =/  expires=@ud  0
  |-
  ?~  grants
    ?:  (lte expires now)  ~
    (some [(min expires expires.context.actor) =(%person u.kind)])
  =/  row  q.i.grants
  =/  allowed
    ?&  =(project.item project.row)  =(principal.identity.context.actor principal.row)
        !revoked.row  (gth expires.row now)
        ?|(=('reader' role.row) =('contributor' role.row) =('maintainer' role.row))
    ==
  $(grants t.grants, expires ?:(allowed (max expires expires.row) expires))
++  accountable
  |=  [state=authority-snapshot actor=verified:stead-actor item=contract now=@ud]
  ^-  ?
  ?.  (native-human:stead-actor db.state catalog.state actor now)  |
  ?>  ?=(%native -.actor)
  =/  work  (~(get by works.data.db.state) [project.item work.item])
  ?~  work  |
  ?&  (gte (role:stead-team db.state context.actor project.item now) 2)
      ?|  =(principal.identity.context.actor (field data.u.work 'owner_principal_id'))
          (gte (role:stead-team db.state context.actor project.item now) 3)
      ==
  ==
++  policy
  |=  [state=authority-snapshot actor=verified:stead-actor item=contract operation=@tas now=@ud]
  ^-  ?
  ?~  (member state actor item now)  |
  ?:  =(%read operation)  &
  ?:  =(%issue operation)
    &((accountable state actor item now) =(requester.item (principal:stead-actor actor)))
  ?:  ?=(?(%answer %cancel) operation)  (accountable state actor item now)
  ?.  ?=(?(%claim %heartbeat %wait %resume %fail %finish) operation)  |
  ?>  ?=(%native -.actor)
  ?&  =(worker.item principal.identity.context.actor)
      =(binding.item binding.identity.context.actor)
      =(binding-revision.item revision.identity.context.actor)
      =((some %agent) (native-kind:stead-principals catalog.state registry.db.state worker.item now))
      (gte (role:stead-team db.state context.actor project.item now) 2)
  ==
++  original
  |=  [state=authority-snapshot item=contract now=@ud]
  ^-  ?
  =/  worker  (active-member:stead-team db.state worker.item now)
  =/  grant  (~(get by grants.data.db.state) grant-key.item)
  ?.  &(?=(^ worker) ?=(^ grant))  |
  ?&  =((some %agent) (native-kind:stead-principals catalog.state registry.db.state worker.item now))
      =(binding.item binding.identity.u.worker)
      =(binding-revision.item revision.identity.u.worker)
      =(grant.item u.grant)  !revoked.u.grant
      =(project.item project.u.grant)  =(worker.item principal.u.grant)
      ?|(=('contributor' role.u.grant) =('maintainer' role.u.grant))
      (gth expires.u.grant now)
  ==
++  base
  |=  [state=authority-snapshot item=contract now=@ud]
  ^-  ?
  =/  work  (~(get by works.data.db.state) [project.item work.item])
  =/  metadata  (~(get by works.product.state) [project.item work.item])
  =/  project  (~(get by projects.data.db.state) project.item)
  ?.  &(?=(^ work) ?=(^ metadata) ?=(^ project))  |
  =/  worker  (active-member:stead-team db.state worker.item now)
  =/  owner  (active-member:stead-team db.state owner.item now)
  ?.  &(?=(^ worker) ?=(^ owner))  |
  =/  worker-actor  (need (native-context:stead-team db.state ship.identity.u.worker now))
  =/  owner-actor  (need (native-context:stead-team db.state ship.identity.u.owner now))
  =/  definition  (~(get by definitions.catalog.state) [definition.item definition-revision.item])
  =/  runtime  (~(get by runtimes.catalog.state) [runtime.item runtime-revision.item])
  ?.  &(?=(^ definition) ?=(^ runtime))  |
  ?&  =(home.item home.worker-actor)  =(epoch.item epoch.u.project)
      =(%explicit owner-source.item)
      =(owner.item (field data.u.work 'owner_principal_id'))
      =(worker.item (field data.u.work 'worker_principal_id'))
      =((some %person) (native-kind:stead-principals catalog.state registry.db.state owner.item now))
      (gte (role:stead-team db.state owner-actor project.item now) 2)
      (original state item now)
      (visible db.state worker-actor item now)
      =(worker.item principal.u.definition)  =(definition-revision.item revision.u.definition)
      =(runtime.item runtime-id.u.definition)  =(runtime-revision.item runtime-revision.u.definition)
      =(worker.item principal.u.runtime)  =(runtime-revision.item revision.u.runtime)
      =(execution-revision.item execution-revision.u.metadata)
      =(execution-digest.item execution-digest.u.metadata)
      =(execution-digest.item (contract-digest:stead-product-state [project.item work.item] execution-revision.item data.u.work))
      (~(has in (silt ~['backlog' 'todo' 'in_progress' 'in_review'])) (field data.u.work 'status'))
      =('' (field data.u.work 'blocked_reason'))
      ?~(legacy-blocked.u.metadata & resolved.u.legacy-blocked.u.metadata)
      ?~(legacy-assignee.u.metadata & resolved.u.legacy-assignee.u.metadata)
      =((targets-bytes:stead-run-state project.item targets.item) (canonical (~(got by data.u.work) 'required_outcomes')))
      %+  levy  targets.item
      |=  row=target
      (current-target:stead-product-adapters db.state worker-actor project.item work.item worker.item (target-json project.item row) now)
  ==
++  context-checked
  |=  [state=authority-snapshot item=contract now=@ud]
  ^-  context-value
  ?>  (base state item now)
  =/  work  (~(got by works.data.db.state) [project.item work.item])
  =/  definition  (~(got by definitions.catalog.state) [definition.item definition-revision.item])
  =/  runtime  (~(got by runtimes.catalog.state) [runtime.item runtime-revision.item])
  =/  docs
    %+  turn  targets.item
    |=  row=target
    =/  markdown
      ?:  =(revision.row 0)  ''
      =/  document  (~(got by documents.data.db.state) [project.item (scope-key:stead-core collection.row document.row)])
      =/  blob  (~(got by objects.data.db.state) blob.document)
      ?>  =(%blob kind.blob)
      data.body.blob
    [outcome.row (object ~[['target' (canonical (target-json project.item row))] ['markdown' markdown]])]
  =/  bytes
    %-  canonical
    (object ~[['protocol' 'stead.run-context/1'] ['project_id' project.item] ['work_id' work.item] ['execution_contract_revision' (decimal execution-revision.item)] ['execution_contract_digest' execution-digest.item] ['title' (field data.work 'title')] ['description' (field data.work 'description')] ['acceptance_criteria' (field data.work 'acceptance_criteria')] ['instructions_digest' instructions-digest.definition] ['runtime_policy_digest' policy-digest.runtime] ['documents' (canonical [%o (malt docs)])]])
  ?>  &((lte (met 3 bytes) 65.536) (lte (met 3 bytes) input.limits.budget.item))
  [bytes (hash 'stead.run-context/1' bytes)]
++  context-value-of
  |=  [state=authority-snapshot item=contract now=@ud]
  ^-  (unit context-value)
  =/  checked  (mule |.((context-checked state item now)))
  ?:  ?=(%| -.checked)  ~
  (some p.checked)
++  execute
  |=  [state=authority-snapshot item=contract now=@ud]
  ^-  ?
  =/  context  (context-value-of state item now)
  ?~(context | =(context.item digest.u.context))
++  read-pins
  |=  [state=authority-snapshot item=contract]
  ^-  ?
  ::  Visibility belongs to the actual current member callback. A changed
  ::  goal, assignee or Doc head invalidates execution, not retained history.
  ?&  (~(has by works.data.db.state) [project.item work.item])
      !(~(has in tombs.db.state) [project.item 'work' '' work.item])
      !(closed:stead-core data.db.state project.item)
  ==
++  output-pin
  |=  [item=contract output=output:stead-doc-change-state]
  ^-  ?
  ?&  (result-valid:stead-run-state [change.output revision.output digest.output outcome.output])
      =(project.item project.output)  =(work.item work.output)
      =(epoch.item epoch.output)  =(execution-revision.item execution.output)
      =(execution-digest.item execution-digest.output)
      =(worker.item principal.identity.producer.output)
      =(binding.item binding.identity.producer.output)
      =(binding-revision.item revision.identity.producer.output)
      =(grant-key.item grant-id.output)  =(grant.item grant.output)
      =(digest.output (output-digest:stead-doc-change-state output))
      %+  lien  targets.item
      |=  row=target
      &(=(outcome.row outcome.output) =((target-json project.item row) target.output))
  ==
++  run-authority
  |=  [state=authority-snapshot runs=state:stead-run-state book=live:stead-run-state output=output:stead-doc-change-state now=@ud]
  ^-  authority:stead-doc-change
  =/  key=run-key:stead-run-state  [project.output run.output]
  =/  found  (~(get by heads.runs) key)
  ?~  found  %unknown
  =/  head  u.found
  =/  item  contract.head
  =/  attempt  (~(get by attempts.runs) [key attempt.output])
  ?~  attempt  %unknown
  ?.  ?&  =(attempt.output attempt.head)  (gth attempt.output 0)
          =(digest.head (hash 'stead.run-contract/1' (contract-bytes:stead-run-state item)))
          (output-pin item output)
          =(audit.u.attempt (authentication-json:stead-team producer.output))
          =(worker.item principal.u.attempt)
          =(binding.item binding.u.attempt)  =(binding-revision.item binding-revision.u.attempt)
          (gte submitted-at.output started.u.attempt)  (lte submitted-at.output now)
          (lth submitted-at.output until.u.attempt)
          (current:stead-team db.state producer.output 0)
          (original state item 0)  (execute state item 0)
      ==
    %revoked
  ?:  ?=(?(%canceled %failed) phase.head)  %revoked
  ?:  =(%submitted phase.head)
    ?~  result.head  %unknown
    ?.  ?&  =(change.output change.u.result.head)  =(revision.output revision.u.result.head)
            =(digest.output digest.u.result.head)  =(outcome.output outcome.u.result.head)
            =(%submitted disposition.u.attempt)
        ==
      %revoked
    ?:  ?|  (lte deadline.item now)  (lte expires.grant.item now)
            (lte expires.producer.output now)  (lte expires.identity.producer.output now)
        ==  %expired
    %live
  ?.  &(?=(?(%running %waiting) phase.head) ?=(?(%running %waiting) disposition.u.attempt))  %revoked
  =/  lease  (~(get by leases.book) key)
  ?~  lease  %unknown
  ?.  &(=(attempt.output attempt.u.lease) =(incarnation.book incarnation.u.lease))  %unknown
  ?:  ?|  (lte until.u.attempt now)  (lte deadline.item now)
          (lte expires.grant.item now)  (lte expires.producer.output now)
          (lte expires.identity.producer.output now)
      ==  %expired
  ?.  &((current:stead-team db.state producer.output now) (execute state item now))  %revoked
  %live
++  submission-receipt
  |=  [state=authority-snapshot output=output:stead-doc-change-state request=@t entry=attempt:stead-doc-change-state]
  ^-  ?
  =/  cmd  (decode:stead-doc-change-codec command.entry)
  =/  receipt  (need (parse-result receipt.entry))
  ?>  ?=([%o *] receipt)
  ?>  (keys p.receipt ~['protocol' 'status' 'request_id' 'canonical_sha256' 'project_id' 'work_id' 'change_id' 'authority_epoch' 'operation' 'expected_revision' 'resulting_revision' 'result_revision' 'result_digest' 'change_status' 'recorded_at_ms' 'error'])
  ?>  (levy ~(tap by p.receipt) |=([key=@t value=json] ?=([%s *] value)))
  =/  body  (~(get by bodies.changes.state) markdown-sha256.output)
  ?~  body  |
  ?&  =('change.submit' operation.entry)  =('change.submit' operation.cmd)
      =(work.output work.entry)  =(change.output change.entry)
      =(project.output project.cmd)  =(work.output work.cmd)  =(change.output change.cmd)
      =(request request.cmd)
      =(digest.cmd digest.entry)  =(canonical-bytes.cmd command.entry)
      =((canonical receipt) receipt.entry)
      =('accepted' (field p.receipt 'status'))
      =('' (field p.receipt 'error'))
      =('submitted' (field p.receipt 'change_status'))
      =('stead.doc-change-receipt/1' (field p.receipt 'protocol'))
      =(project.output (field p.receipt 'project_id'))
      =(work.output (field p.receipt 'work_id'))
      =(change.output (field p.receipt 'change_id'))
      =('change.submit' (field p.receipt 'operation'))
      =(epoch.output (uint (field p.receipt 'authority_epoch')))
      =(expected.cmd (uint (field p.receipt 'expected_revision')))
      =(+(expected.cmd) (uint (field p.receipt 'resulting_revision')))
      =(request.cmd (field p.receipt 'request_id'))
      =(digest.cmd (field p.receipt 'canonical_sha256'))
      =(revision.output (uint (field p.receipt 'result_revision')))
      =(digest.output (field p.receipt 'result_digest'))
      =(submitted-at.output (uint (field p.receipt 'recorded_at_ms')))
      =(epoch.output epoch.cmd)  =(outcome.output (field payload.cmd 'outcome_id'))
      =(run.output (field payload.cmd 'run_id'))  =(attempt.output (uint (field payload.cmd 'attempt')))
      =(execution.output (uint (field payload.cmd 'execution_contract_revision')))
      =(execution-digest.output (field payload.cmd 'execution_contract_digest'))
      =(target.output (~(got by payload.cmd) 'target'))
      =(summary.output (field payload.cmd 'summary'))
      =(u.body (field payload.cmd 'markdown'))
      =(markdown-sha256.output (markdown-sha256:stead-product-adapters [(met 3 u.body) u.body]))
  ==
++  actual-result
  |=  [state=authority-snapshot runs=state:stead-run-state book=live:stead-run-state key=run-key:stead-run-state item=contract number=@ud reference=result-reference:stead-run-state now=@ud]
  ^-  ?
  =/  head  (~(get by heads.changes.state) [project.key change.reference])
  =/  output  (~(get by results.changes.state) [project.key change.reference revision.reference])
  ?.  &(?=(^ head) ?=(^ output))  |
  =/  value  u.output
  ?.  ?&  =(project.item project.key)  =(run.key run.value)
          =(number attempt.value)  =(outcome.reference outcome.value)
          =(digest.reference digest.value)  =(revision.reference output-revision.u.head)
          =(digest.reference output-digest.u.head)
          =(worker.item producer.u.head)  =(work.item work.u.head)
          ?=(?(%submitted %approved) status.u.head)
          (output-pin item value)
          =(%live (run-authority state runs book value now))
      ==  |
  =/  attempts  ~(tap by attempts.changes.state)
  ?>  (lte (lent attempts) 4.096)
  |-
  ?~  attempts  |
  ?:  &(=(project.key project.p.i.attempts) =(worker.item principal.p.i.attempts))
    =/  checked  (mule |.((submission-receipt state value request.p.i.attempts q.i.attempts)))
    ?:  ?=([%& %.y] checked)  &
    $(attempts t.attempts)
  $(attempts t.attempts)
--
|%
+$  snapshot  authority-snapshot
++  context
  |=  [state=snapshot item=contract now=@ud]
  ^-  (unit context-value)
  (context-value-of state item now)
++  doc-runs
  |=  [state=snapshot runs=state:stead-run-state book=live:stead-run-state]
  ^-  run-resolver:stead-doc-change
  |=  [output=output:stead-doc-change-state now=@ud]
  =/  checked  (mule |.((run-authority state runs book output now)))
  ?:  ?=(%| -.checked)  %unknown
  p.checked
++  current
  |=  [state=snapshot runs=state:stead-run-state book=live:stead-run-state key=run-key:stead-run-state]
  ^-  gates:stead-run-state
  =/  gates  deny-gates:stead-run
  =.  member.gates
    |=  [actor=verified:stead-actor item=contract now=@ud]
    ?.  =(project.key project.item)  *(unit membership:stead-run-state)
    (member state actor item now)
  =.  policy.gates
    |=  [actor=verified:stead-actor item=contract operation=@tas now=@ud]
    &(=(project.key project.item) (policy state actor item operation now))
  =.  pins.gates
    |=  [item=contract mode=?(%execute %read) now=@ud]
    ?.  =(project.key project.item)  |
    ?:  =(%read mode)  (read-pins state item)
    (execute state item now)
  =.  original.gates
    |=  [item=contract now=@ud]
    &(=(project.key project.item) (original state item now))
  =.  result.gates
    |=  [item=contract attempt=@ud reference=result-reference:stead-run-state now=@ud]
    =/  checked  (mule |.((actual-result state runs book key item attempt reference now)))
    ?:  ?=(%| -.checked)  |
    p.checked
  =.  used.gates
    |=  request=request-key:stead-run-state
    ?|  (~(has by receipts.data.db.state) request)
        (~(has by attempts.product.state) request)
        (~(has by attempts.changes.state) request)
        (~(has by ledger.state) request.request)
    ==
  gates
--

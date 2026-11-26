::  Reserved no-Code run profile. These are durable candidate data, not a
::  serving Home save format or permission store. There is no event journal
::  here: the eventual Home wrapper owns the single ordered product history.
/+  stead-codec, stead-core, stead-actor
=,  stead-codec
|%
+$  run-key  [project=@t run=@t]
+$  usage
  [tools=@ud network=@ud tokens=@ud cost=@ud input=@ud output=@ud]
+$  budget  [duration=@ud limits=usage]
+$  target
  [outcome=@t collection=@t document=@t revision=@ud markdown=@t]
+$  contract
  $:  home=@p  project=@t  work=@t  epoch=@ud
      execution-revision=@ud  execution-digest=@t
      requester=@t  owner=@t  owner-source=?(%explicit %steward)
      worker=@t  binding=@t  binding-revision=@ud
      definition=@t  definition-revision=@ud  runtime=@t  runtime-revision=@ud
      grant-key=@t  grant=grant-state:stead-core
      context=@t  targets=(list target)  budget=budget  deadline=@ud
  ==
+$  result-reference
  [change=@t revision=@ud digest=@t outcome=@t]
+$  phase  ?(%queued %running %waiting %submitted %failed %canceled)
+$  head
  $:  contract=contract  digest=@t  issued=@ud  revision=@ud
      phase=phase  attempt=@ud  question=@ud  used=usage
      result=(unit result-reference)
  ==
+$  attempt
  $:  principal=@t  binding=@t  binding-revision=@ud  audit=@t
      started=@ud  heartbeat=@ud  until=@ud
      disposition=?(%running %waiting %submitted %failed %canceled %replaced)
  ==
+$  question
  [text=@t principal=@t at=@ud answer=(unit [text=@t principal=@t at=@ud])]
+$  intent
  $:  id=@t  kind=?(%provider-call %doc-proposal)
      provider=@t  request-digest=@t  result=(unit result-reference)
      charge=usage
  ==
+$  effect
  [intent=intent status=?(%pending %unknown %settled) evidence=@t result-digest=@t]
+$  settlement
  [id=@t status=?(%unknown %settled) evidence=@t result-digest=@t]
+$  operation
  $%  [%issue item=contract]
      [%claim ~]  [%replace evidence=@t]  [%heartbeat ~]
      [%wait text=@t]  [%answer question=@ud text=@t]
      [%resume question=@ud]  [%cancel reason=@t]
      [%fail reason=@t evidence=@t]  [%finish result=result-reference]
      [%intent item=intent]  [%settle item=settlement]
      [%reconcile item=settlement]
  ==
+$  command
  [request=@t project=@t run=@t expected=@ud attempt=@ud operation=operation]
+$  request-key  [project=@t principal=@t request=@t]
+$  receipt  [digest=@t command=@t response=@t]
+$  state
  $:  heads=(map run-key head)
      attempts=(map [key=run-key attempt=@ud] attempt)
      questions=(map [key=run-key sequence=@ud] question)
      effects=(map [key=run-key attempt=@ud id=@t] effect)
      requests=(map request-key receipt)
  ==
+$  live
  [incarnation=@t leases=(map run-key [attempt=@ud incarnation=@t])]
+$  membership  [expires=@ud human=?]
+$  gates
  ::  All functions are Home-internal and default deny. The carrier constructs
  ::  verified actors; typed values or recorded audit bytes prove nothing alone.
  $:  member=$-([actor=verified:stead-actor item=contract now=@ud] (unit membership))
      policy=$-([actor=verified:stead-actor item=contract operation=@tas now=@ud] ?)
      pins=$-([item=contract mode=?(%execute %read) now=@ud] ?)
      original=$-([item=contract now=@ud] ?)
      effect=$-([actor=verified:stead-actor item=contract attempt=@ud proposal=intent now=@ud] ?)
      result=$-([item=contract attempt=@ud reference=result-reference now=@ud] ?)
      settled=$-([item=contract attempt=@ud effect=effect resolution=settlement now=@ud] ?)
      reconciled=$-([item=contract attempt=@ud effects-digest=@t evidence=@t now=@ud] ?)
      used=$-(request-key ?)
  ==
+$  shared-budget
  ::  Integrator supplies combined retained counts INCLUDING these requests.
  ::  Project security includes actual core policy revocations; no new pool.
  [ordinary=@ud security=@ud project-security=@ud]
+$  candidate-intent
  $%  [%execution key=run-key attempt=@ud continuation=@ud contract-digest=@t]
      [%question key=run-key sequence=@ud principal=@t text=@t]
      [%answer key=run-key sequence=@ud principal=@t text=@t]
      [%effect key=run-key attempt=@ud item=intent]
      [%submitted key=run-key attempt=@ud result=result-reference]
      [%stop key=run-key attempt=@ud]
  ==
+$  transition
  $:  response=@t  next=state  live=live  record=(unit @t)
      intents=(list candidate-intent)
  ==
++  uint64
  |=  n=@ud
  (lte n 18.446.744.073.709.551.615)
++  digest-valid
  |=  raw=@t
  ^-  ?
  &(=(64 (met 3 raw)) (levy (trip raw) |=(c=@t ?|(&((gte c '0') (lte c '9')) &((gte c 'a') (lte c 'f'))))))
++  usage-valid
  |=  row=usage
  ^-  ?
  ?&  (lte tools.row 32)  (lte network.row 8)
      (uint64 tokens.row)  (uint64 cost.row)
      (lte input.row 65.536)  (lte output.row 32.768)
  ==
++  result-valid
  |=  row=result-reference
  ^-  ?
  &((uuid change.row) (gth revision.row 0) (uint64 revision.row) (digest-valid digest.row) (uuid outcome.row))
++  result-bytes
  |=  row=result-reference
  ^-  @t
  (canonical (object ~[['change_id' change.row] ['result_revision' (decimal revision.row)] ['result_digest' digest.row] ['outcome_id' outcome.row]]))
++  usage-bytes
  |=  row=usage
  ^-  @t
  (canonical (object ~[['tool_calls' (decimal tools.row)] ['network_calls' (decimal network.row)] ['token_units' (decimal tokens.row)] ['cost_units' (decimal cost.row)] ['input_bytes' (decimal input.row)] ['output_bytes' (decimal output.row)]]))
++  grant-bytes
  |=  row=grant-state:stead-core
  ^-  @t
  (canonical (object ~[['project_id' project.row] ['principal_id' principal.row] ['role' role.row] ['expires_at_ms' (decimal expires.row)] ['revoked' ?:(revoked.row 'yes' 'no')]]))
++  targets-bytes
  |=  [project=@t rows=(list target)]
  ^-  @t
  =/  pairs
    %+  turn  rows
    |=  row=target
    [outcome.row (object ~[['kind' 'document'] ['project_id' project] ['collection_id' collection.row] ['document_id' document.row] ['expected_revision' (decimal revision.row)] ['base_markdown_sha256' markdown.row]])]
  (canonical [%o (malt pairs)])
++  normalize-contract
  ::  Target order has no portable meaning. Store the same deterministic list
  ::  that a future strict keyed-object decoder will reconstruct for replay.
  |=  row=contract
  ^-  contract
  row(targets (sort targets.row |=([a=target b=target] (aor outcome.a outcome.b))))
++  contract-bytes
  |=  row=contract
  ^-  @t
  =/  values=(list [@t @t])
    :~  ['home' (scot %p home.row)]  ['project_id' project.row]  ['work_id' work.row]
        ['authority_epoch' (decimal epoch.row)]
        ['execution_contract_revision' (decimal execution-revision.row)]
        ['execution_contract_digest' execution-digest.row]
        ['requester_id' requester.row]  ['owner_id' owner.row]
        ['owner_source' (scot %tas owner-source.row)]  ['worker_id' worker.row]
        ['binding_id' binding.row]  ['binding_revision' (decimal binding-revision.row)]
        ['definition_id' definition.row]  ['definition_revision' (decimal definition-revision.row)]
        ['runtime_id' runtime.row]  ['runtime_revision' (decimal runtime-revision.row)]
        ['grant_key' grant-key.row]  ['grant' (grant-bytes grant.row)]
        ['context_digest' context.row]  ['targets' (targets-bytes project.row targets.row)]
        ['duration_ms' (decimal duration.budget.row)]
        ['budget' (usage-bytes limits.budget.row)]  ['deadline_ms' (decimal deadline.row)]
    ==
  (canonical (object values))
++  intent-bytes
  |=  row=intent
  ^-  @t
  (canonical (object ~[['effect_id' id.row] ['kind' (scot %tas kind.row)] ['provider_id' provider.row] ['request_digest' request-digest.row] ['result' ?~(result.row '' (result-bytes u.result.row))] ['charge' (usage-bytes charge.row)]]))
++  operation-bytes
  |=  op=operation
  ^-  @t
  ?-  -.op
    %issue  (contract-bytes item.op)
    %claim  ''
    %replace  evidence.op
    %heartbeat  ''
    %wait  text.op
    %answer  (canonical (object ~[['question' (decimal question.op)] ['text' text.op]]))
    %resume  (decimal question.op)
    %cancel  reason.op
    %fail  (canonical (object ~[['reason' reason.op] ['evidence' evidence.op]]))
    %finish  (result-bytes result.op)
    %intent  (intent-bytes item.op)
    %settle  (canonical (object ~[['effect_id' id.item.op] ['status' (scot %tas status.item.op)] ['evidence' evidence.item.op] ['result_digest' result-digest.item.op]]))
    %reconcile  (canonical (object ~[['effect_id' id.item.op] ['status' (scot %tas status.item.op)] ['evidence' evidence.item.op] ['result_digest' result-digest.item.op]]))
  ==
++  command-bytes
  |=  cmd=command
  ^-  @t
  (canonical (object ~[['protocol' 'stead.run-command/1'] ['request_id' request.cmd] ['project_id' project.cmd] ['run_id' run.cmd] ['expected_revision' (decimal expected.cmd)] ['expected_attempt' (decimal attempt.cmd)] ['operation' (scot %tas -.operation.cmd)] ['payload' (operation-bytes operation.cmd)]]))
--

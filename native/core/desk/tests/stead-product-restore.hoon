/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract, stead-product-work, stead-product-codec, stead-product-restore
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  command
  |=  [req=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  value
    (object ~[['protocol' 'stead.command/3'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
  ?>  ?=([%o *] value)
  (decode:stead-team-codec (canonical [%o (~(put by p.value) 'payload' (object payload))]))
++  result-field
  |=  [raw=@t name=@t]
  ^-  @t
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (field p.value name)
++  finished
  |=  db=state:stead-team
  ^-  job:stead-product-migrate
  =/  job  (begin:stead-product-migrate db ~zod)
  =/  budget=@ud  1.024
  |-
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  job
  ?>  (gth budget 0)
  $(job (step:stead-product-migrate job), budget (dec budget))
++  migrate
  |=  db=state:stead-team
  ^-  migrated:stead-product-migrate
  (need (result:stead-product-migrate (finished db)))
++  command-four
  |=  [req=@ud work=@ud operation=@t expected=(list [@t @t]) payload=json]
  ^-  command:stead-product-codec
  =/  value  (object ~[['protocol' 'stead.command/4'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id work)] ['authority_epoch' '1'] ['operation' operation]])
  ?>  ?=([%o *] value)
  =/  fields  (~(put by p.value) 'expected' (object expected))
  (decode:stead-product-codec (canonical [%o (~(put by fields) 'payload' payload)]))
++  props
  |=  [status=@t priority=@t owner=@t worker=@t reason=@t]
  ^-  json
  (object ~[['type' 'task'] ['status' status] ['priority' priority] ['owner_principal_id' owner] ['worker_principal_id' worker] ['blocked_reason' reason]])
++  goal
  |=  [title=@t outcomes=json]
  ^-  json
  =/  value  (object ~[['title' title] ['description' 'Notes'] ['acceptance_criteria' '']])
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) 'required_outcomes' outcomes)]
++  create-four
  |=  [req=@ud work=@ud outcomes=json]
  ^-  command:stead-product-codec
  =/  properties  (props 'todo' 'none' '' '' '')
  =/  contract  (goal 'Draft' outcomes)
  ?>  &(?=([%o *] properties) ?=([%o *] contract))
  (command-four req work 'work.create' ~[['work_revision' '0'] ['execution_contract_revision' '0']] [%o (~(uni by p.properties) p.contract)])
++  fixture-kind
  |=  [project=@t principal=@t now=@ud]
  ^-  (unit principal-kind:stead-product-work)
  ?:  =(principal (id 103))  (some %agent)
  ?:  ?|(=(principal (id 102)) =(principal (id 104)))  (some %person)
  ~
++  fixture-target
  |=  [project=@t work=@t principal=@t target=json now=@ud]
  ^-  ?
  ::  Explicit trusted test adapter; not evidence of a live Home target check.
  ?.  ?=([%o *] target)  |
  ?.  &(=(project (id 100)) =('document' (field p.target 'kind')) =((id 200) (field p.target 'collection_id')))  |
  ?:  =('0' (field p.target 'expected_revision'))  =('' (field p.target 'base_markdown_sha256'))
  ?&  =('1' (field p.target 'expected_revision'))
      =((id 201) (field p.target 'document_id'))
      =('5246215a4c9b7427c502a531ef372f676b3d005f8d26c4f0e166aae2bd6b9c4b' (field p.target 'base_markdown_sha256'))
  ==
++  no-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  ~
++  profile
  ^-  resolvers:stead-product-work
  [fixture-kind fixture-target no-proof]
++  meta
  |=  [product=state:stead-product-state work=@ud]
  ^-  metadata:stead-product-state
  (~(got by works.product) [(id 100) (id work)])
++  run
  |=  [state=migrated:stead-product-migrate actor=authentication:stead-team cmd=command:stead-product-codec now=@ud resolvers=resolvers:stead-product-work]
  ^-  transition:stead-product-work
  (apply-command:stead-product-work db.state product.state actor cmd now resolvers)
++  historical
  |=  request=evidence-request:stead-product-restore
  ^-  (unit resolvers:stead-product-work)
  ::  Fixed test evidence: the fixture authority declared Alice human and Bob
  ::  agent for this interval. Not a real catalog or Change history adapter.
  ?.  &(=(project.command.request (id 100)) (lth now.request 5.000))  ~
  ?.  ?|  =(principal.identity.actor.request (id 102))
          =(principal.identity.actor.request (id 103))
      ==
    ~
  (some profile)
++  missing-history
  |=  request=evidence-request:stead-product-restore
  ^-  (unit resolvers:stead-product-work)
  ~
++  restored
  |=  [target=migrated:stead-product-migrate adapter=adapter:stead-product-restore]
  ^-  job:stead-product-restore
  =/  job  (begin:stead-product-restore target ~zod)
  =/  budget=@ud  1.024
  |-
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  job
  ?>  (gth budget 0)
  $(job (step:stead-product-restore job adapter), budget (dec budget))
++  rejected
  |=  target=migrated:stead-product-migrate
  ^-  ?
  =/  attempted  (mule |.((restored target historical)))
  ?:  ?=(%| -.attempted)  &
  =(%invalid phase.p.attempted)
++  admission-refused
  |=  target=migrated:stead-product-migrate
  ^-  ?
  ?=([%| *] (mule |.((begin:stead-product-restore target ~zod))))
++  value
  |=  raw=@t
  ^-  object-map
  =/  parsed  (need (parse-result raw))
  ?>  ?=([%o *] parsed)
  p.parsed
++  newest-body
  |=  product=state:stead-product-state
  ^-  @t
  ?>  ?=(^ events.product)
  (field (value bytes.i.events.product) 'body')
++  body-replaced
  |=  [product=state:stead-product-state body=@t]
  ^-  state:stead-product-state
  ?>  ?=(^ events.product)
  =/  event  i.events.product
  =/  envelope  (~(put by (value bytes.event)) 'body' [%s body])
  =/  bytes  (canonical [%o envelope])
  product(events [event(bytes bytes, digest (hash 'stead.product-event/1' bytes)) t.events.product])
++  record-replaced
  |=  [product=state:stead-product-state name=@t content=@t]
  ^-  state:stead-product-state
  =/  body  (canonical [%o (~(put by (value (newest-body product))) name [%s content])])
  (body-replaced product body)
++  rechain
  |=  [product=state:stead-product-state events=(list event:stead-product-state)]
  ^-  state:stead-product-state
  =/  next  product(events ~)
  =/  remaining  (flop events)
  |-
  ?~  remaining  next
  =/  body  (field (value bytes.i.remaining) 'body')
  $(remaining t.remaining, next (append-event:stead-product-state next family.i.remaining body))
--
=/  configuration
  %-  rap
  :-  3
  :~  '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{'
      '"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000102","binding_id":"019939ba-4000-7000-8000-000000000202","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Alice"},'
      '"~nec":{"principal_id":"019939ba-4000-7000-8000-000000000103","binding_id":"019939ba-4000-7000-8000-000000000203","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Bob"},'
      '"~bud":{"principal_id":"019939ba-4000-7000-8000-000000000104","binding_id":"019939ba-4000-7000-8000-000000000204","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Carol"}'
      '},"project_creators":{"019939ba-4000-7000-8000-000000000102":"yes"}}'
  ==
=/  initial  (configure:stead-team empty:stead-team configuration ~zod 1.000)
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  bob  (need (native-context:stead-team initial ~nec 1.001))
=/  carol  (need (native-context:stead-team initial ~bud 1.001))
=/  make-project  (command 301 100 0 'project.create' ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' 'Stead'] ['project_key' 'STEAD'] ['preset' 'general']])
=/  project  (apply-command:stead-team initial alice make-project 1.002)
=/  grant-editor  (command 302 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' principal.identity.bob] ['role' 'contributor'] ['expires_at_ms' '8000000']])
=/  editor  (apply-command:stead-team next.project alice grant-editor 1.003)
=/  grant-reader  (command 303 100 2 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' principal.identity.carol] ['role' 'reader'] ['expires_at_ms' '5000']])
=/  reader  (apply-command:stead-team next.editor alice grant-reader 1.004)
=/  work-fields  ~[['title' 'Draft'] ['description' 'Notes'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
=/  create  (apply-command:stead-team next.reader alice (command 304 101 0 'work.create' work-fields) 1.005)
=/  db  next.create
=/  policies  profile
=/  shared-box  (apply-command:stead-team db alice (command 351 200 0 'container.create' ~[['title' 'Shared'] ['visibility' 'shared']]) 1.006)
=/  private-box  (apply-command:stead-team next.shared-box alice (command 352 202 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.007)
=/  initial-product  (migrate next.private-box)
=/  comment-a  (command-four 401 101 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'First question']]))
=/  properties-a  (command-four 402 101 'work.update-properties' ~[['work_revision' '1']] (props 'in_progress' 'high' '' '' ''))
=/  doc-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '0'] ['base_markdown_sha256' '']])
=/  outcomes  [%o (malt ~[[(id 500) doc-target]])]
=/  question  (run initial-product alice comment-a 2.000 policies)
=/  container  (apply-legacy:stead-product-work db.question product.question alice (command 450 250 0 'container.create' ~[['title' 'More Docs'] ['visibility' 'shared']]) 2.001)
=/  changed  (run [db.container product.container] alice (command-four 451 101 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Revised draft' [%o ~])) 2.002 policies)
=/  stale  (run [db.changed product.changed] alice (command-four 452 101 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'Stale question']])) 2.003 policies)
=/  completion-command  (command-four 453 101 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '2']] (object ~[['basis' 'human-note'] ['note' 'Confirmed with the customer.']]))
=/  completed  (run [db.stale product.stale] alice completion-command 2.004 policies)
=/  snapshot=migrated:stead-product-migrate  [db.completed product.completed]
|%
++  test-product-restore-old-history-path-retains-predecessor-semantics
  =/  source  next.private-box
  =/  old  (step:stead-restore (begin:stead-restore source ~zod))
  =/  history  (step-history:stead-restore (begin-history:stead-restore registry.source journal.data.source ~zod))
  =/  legacy-work  (~(got by works.data.source) [(id 100) (id 101)])
  =/  tampered  source(data data.source(works (~(put by works.data.source) [(id 100) (id 101)] legacy-work(revision 99))))
  =/  refused  (step:stead-restore (begin:stead-restore tampered ~zod))
  %-  expect
  !>  ?&  =((some source) (result:stead-restore old))
          =((some source) (result-history:stead-restore history))
          =(%invalid status.refused)  ?=(~ (result:stead-restore refused))
      ==
++  test-product-restore-mixed-replay-is-exact-and-retains-rejected-attempts
  =/  result  (restored snapshot historical)
  =/  retry  (run snapshot alice completion-command 2.005 policies)
  =/  rejected-attempt  (~(got by attempts.product.rebuilt.result) [(id 100) principal.identity.alice (id 452)])
  %-  expect
  !>  ?&  =('accepted' (result-field response.completed 'status'))
          =('revision_conflict' (result-field response.stale 'error'))
          =(%valid phase.result)
          =((some snapshot) (result:stead-product-restore result))
          =(snapshot rebuilt.result)
          =(5 (lent events.product.rebuilt.result))
          =(response.stale receipt.rejected-attempt)
          =(response.completed response.retry)  =(snapshot [db.retry product.retry])
      ==
++  test-product-restore-rejects-rehashed-command-receipt-and-completion-changes
  =/  record  (value (newest-body product.snapshot))
  =/  wire  (need (parse-product:stead-product-codec canonical-bytes.completion-command))
  ?>  ?=([%o *] wire)
  =/  payload  (object-field:stead-product-codec p.wire 'payload')
  =/  changed-payload  (~(put by payload) 'note' [%s 'Changed command note'])
  =/  changed-wire  (canonical [%o (~(put by p.wire) 'payload' [%o changed-payload])])
  =/  command-damage  (record-replaced product.snapshot 'canonical_command' changed-wire)
  =/  receipt  (value (field record 'receipt'))
  =/  changed-receipt  (canonical [%o (~(put by receipt) 'status' [%s 'rejected'])])
  =/  receipt-damage  (record-replaced product.snapshot 'receipt' changed-receipt)
  =/  completion  (value (field record 'completion'))
  =/  changed-completion  (canonical [%o (~(put by completion) 'evidence' [%s 'Forged completion evidence'])])
  =/  evidence-damage  (record-replaced product.snapshot 'completion' changed-completion)
  %-  expect
  !>  ?&  (rejected snapshot(product command-damage))
          (rejected snapshot(product receipt-damage))
          (rejected snapshot(product evidence-damage))
      ==
++  test-product-restore-rejects-reordered-dropped-and-noncanonical-events
  =/  product  product.snapshot
  =/  events  events.product
  ?>  &(?=(^ events) ?=(^ t.events))
  =/  swapped  product(events [i.t.events [i.events t.t.events]])
  =/  dropped  (rechain product t.events)
  =/  noncanonical  (body-replaced product (cat 3 ' ' (newest-body product)))
  %-  expect
  !>  ?&  (rejected snapshot(product swapped))
          (rejected snapshot(product dropped))
          (rejected snapshot(product noncanonical))
      ==
++  test-product-restore-missing-history-and-unrecorded-configuration-fail-closed
  =/  missing  (restored snapshot missing-history)
  =/  config  (value configuration)
  =/  next-config  (canonical [%o (~(put by config) 'expected_revision' [%s '1'])])
  =/  changed-db  (configure:stead-team db.snapshot next-config ~zod 2.005)
  =/  forged-kind  (record-replaced product.snapshot 'principal_kind' 'agent')
  %-  expect
  !>  ?&  =(%invalid phase.missing)  ?=(~ (result:stead-product-restore missing))
          !=(registry.db.snapshot registry.changed-db)
          (rejected snapshot(db changed-db))
          (rejected snapshot(product forged-kind))
      ==
++  test-product-restore-boundary-and-current-state-must-match-reconstruction
  =/  boundary  (need migration.product.snapshot)
  =/  changed-boundary  (boundary-of:stead-product-state journal-count.boundary heads.boundary predecessor-registry.boundary (hex 64 0))
  =/  product  product.snapshot(migration (some changed-boundary))
  =/  meta  (meta product.snapshot 101)
  =/  altered  product.snapshot(works (~(put by works.product.snapshot) [(id 100) (id 101)] meta(discussion-sequence 2)))
  =/  old  (~(got by works.data.db.snapshot) [(id 100) (id 101)])
  =/  db  db.snapshot(data data.db.snapshot(works (~(put by works.data.db.snapshot) [(id 100) (id 101)] old(revision +(revision.old)))))
  %-  expect
  !>  ?&  (rejected snapshot(product product))
          (rejected snapshot(product altered))
          (rejected snapshot(db db))
      ==
++  test-product-restore-incremental-checkpoint-exposes-no-partial-state
  =/  first  (begin:stead-product-restore snapshot ~zod)
  =/  next  (step:stead-product-restore first historical)
  =/  checkpoint  !<(job:stead-product-restore (cue (jam !>(next))))
  =/  resumed
    =/  job  checkpoint
    =/  budget=@ud  1.024
    |-
    ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  job
    ?>  (gth budget 0)
    $(job (step:stead-product-restore job historical), budget (dec budget))
  %-  expect
  !>  ?&  ?=(~ (result:stead-product-restore first))
          ?=(~ (result:stead-product-restore next))
          =(next checkpoint)
          =((some snapshot) (result:stead-product-restore resumed))
          =(resumed (step:stead-product-restore resumed missing-history))
      ==
++  test-product-restore-admission-retains-core-and-sidecar-record-bounds
  =/  db  db.snapshot
  =/  too-many-bytes  db(data data.db(object-bytes 8.388.609))
  =/  product  product.snapshot
  =/  request-key  [(id 100) principal.identity.alice (id 453)]
  =/  attempt  (~(got by attempts.product) request-key)
  =/  big-command  attempt(command (rap 3 (reap 65.537 'x')))
  =/  big-receipt  attempt(receipt (rap 3 (reap 8.193 'x')))
  =/  with-command  product(attempts (~(put by attempts.product) request-key big-command))
  =/  with-receipt  product(attempts (~(put by attempts.product) request-key big-receipt))
  =/  comment-key  [(id 100) (id 101) 1]
  =/  comment  (~(got by comments.product) comment-key)
  =/  big-auth  comment(authentication (rap 3 (reap 4.097 'x')))
  =/  big-body  comment(body (rap 3 (reap 2.049 'x')))
  =/  with-auth  product(comments (~(put by comments.product) comment-key big-auth))
  =/  with-body  product(comments (~(put by comments.product) comment-key big-body))
  %-  expect
  !>  ?&  (admission-refused snapshot(db too-many-bytes))
          (admission-refused snapshot(product with-command))
          (admission-refused snapshot(product with-receipt))
          (admission-refused snapshot(product with-auth))
          (admission-refused snapshot(product with-body))
      ==
--

/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract, stead-product-work, stead-product-codec
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
++  result-count
  |=  raw=@t
  ^-  @ud
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  result  (~(got by p.value) 'rows')
  ?>  ?=([%o *] result)
  (lent ~(tap by p.result))
++  indexed
  |=  db=state:stead-team
  ^-  state:stead-projection
  (batch:stead-projection db (batch:stead-projection db (batch:stead-projection db (begin:stead-projection db *state:stead-projection))))
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
++  human-kind
  |=  [project=@t principal=@t now=@ud]
  ^-  (unit principal-kind:stead-product-work)
  ?:  =(principal (id 103))  (some %person)
  (fixture-kind project principal now)
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
++  permissive-target
  |=  [project=@t work=@t principal=@t target=json now=@ud]
  ^-  ?
  &
++  absent-target
  |=  [project=@t work=@t principal=@t target=json now=@ud]
  ^-  ?
  |
++  no-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  ~
++  fixture-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  ::  Models an independently accepted result/check record inside the authority.
  (some [project.request work.request epoch.request execution.request digest.request (outcome-digest:stead-product-work outcomes.request) 'fixture accepted output and check receipts'])
++  wrong-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  =/  saved  (need (fixture-proof request))
  (some saved(work (id 999)))
++  wrong-pin-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  =/  saved  (need (fixture-proof request))
  (some saved(digest (hex 64 0)))
++  wrong-outcomes-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  =/  saved  (need (fixture-proof request))
  (some saved(outcomes-digest (hex 64 0)))
++  event-evidence
  |=  product=state:stead-product-state
  ^-  @t
  ?>  ?=(^ events.product)
  =/  body  (result-field bytes.i.events.product 'body')
  =/  completion  (result-field body 'completion')
  ?>  !=('' completion)
  (result-field completion 'evidence')
++  profile
  ^-  resolvers:stead-product-work
  [fixture-kind fixture-target no-proof]
++  meta
  |=  [product=state:stead-product-state work=@ud]
  ^-  metadata:stead-product-state
  (~(got by works.product) [(id 100) (id work)])
++  row
  |=  [db=state:stead-team work=@ud]
  ^-  work-state:stead-core
  (~(got by works.data.db) [(id 100) (id work)])
++  run
  |=  [state=migrated:stead-product-migrate actor=authentication:stead-team cmd=command:stead-product-codec now=@ud resolvers=resolvers:stead-product-work]
  ^-  transition:stead-product-work
  (apply-command:stead-product-work db.state product.state actor cmd now resolvers)
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
|%
++  test-product-work-comment-and-properties-commute-with-stable-contract
  =/  a  (run initial-product alice comment-a 2.000 policies)
  =/  ab  (run [db.a product.a] alice properties-a 2.001 policies)
  =/  b  (run initial-product alice properties-a 2.000 policies)
  =/  ba  (run [db.b product.b] alice comment-a 2.001 policies)
  =/  retry  (run [db.ab product.ab] alice comment-a 2.002 policies)
  =/  before  (meta product.initial-product 101)
  =/  after  (meta product.ab 101)
  %-  expect
  !>  ?&  =('accepted' (result-field response.a 'status'))
          =('accepted' (result-field response.ab 'status'))
          =('accepted' (result-field response.ba 'status'))
          =((meta product.ab 101) (meta product.ba 101))
          =((row db.ab 101) (row db.ba 101))
          =(2 work-revision.after)  =(1 discussion-sequence.after)
          =(execution-digest.before execution-digest.after)
          =(response.a response.retry)  =(db.ab db.retry)  =(product.ab product.retry)
          =(2 (lent events.product.ab))
      ==
++  test-product-work-comment-race-retains-rejection-and-requires-new-id
  =/  a  (run initial-product alice comment-a 2.000 policies)
  =/  stale  (command-four 403 101 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'Concurrent question']]))
  =/  b  (run [db.a product.a] bob stale 2.001 policies)
  =/  retry  (run [db.b product.b] bob stale 2.002 policies)
  =/  amended  (command-four 403 101 'work.comment' ~[['discussion_sequence' '1']] (object ~[['body' 'Concurrent question']]))
  =/  reuse  (run [db.b product.b] bob amended 2.003 policies)
  =/  fresh  (command-four 404 101 'work.comment' ~[['discussion_sequence' '1']] (object ~[['body' 'Concurrent question']]))
  =/  accepted  (run [db.b product.b] bob fresh 2.004 policies)
  =/  current  (meta product.accepted 101)
  %-  expect
  !>  ?&  =('revision_conflict' (result-field response.b 'error'))
          =(db.a db.b)  =(response.b response.retry)  =(product.b product.retry)
          =('request_id_reuse' (result-field response.reuse 'error'))
          =(product.b product.reuse)
          =('accepted' (result-field response.accepted 'status'))
          =(2 discussion-sequence.current)  =(1 work-revision.current)
          =(3 (lent events.product.accepted))
          =(2 (lent ~(tap by comments.product.accepted)))
      ==
++  test-product-work-goal-cas-and-revert-never-revive-old-pin
  =/  a  (run initial-product alice comment-a 2.000 policies)
  =/  update  (command-four 403 101 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Revised goal' (object ~)))
  =/  edited  (run [db.a product.a] alice update 2.001 policies)
  =/  stale  (command-four 404 101 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Draft' (object ~)))
  =/  conflict  (run [db.edited product.edited] alice stale 2.002 policies)
  =/  restore  (command-four 405 101 'work.update-contract' ~[['execution_contract_revision' '2']] (goal 'Draft' (object ~)))
  =/  restored  (run [db.conflict product.conflict] alice restore 2.003 policies)
  =/  property-edit  (run [db.restored product.restored] alice properties-a 2.004 policies)
  =/  before  (meta product.initial-product 101)
  =/  after  (meta product.property-edit 101)
  %-  expect
  !>  ?&  =('accepted' (result-field response.edited 'status'))
          =('revision_conflict' (result-field response.conflict 'error'))
          =(db.edited db.conflict)
          =('accepted' (result-field response.restored 'status'))
          =('accepted' (result-field response.property-edit 'status'))
          =(3 execution-revision.after)  =(2 work-revision.after)
          =(1 discussion-sequence.after)
          !=(execution-digest.before execution-digest.after)
      ==
++  test-product-work-current-authority-kinds-and-targets-fail-closed
  =/  reader  (run initial-product carol comment-a 2.000 policies)
  =/  expired  (run initial-product alice comment-a 10.000.000 policies)
  =/  agent-owner  (command-four 403 101 'work.update-properties' ~[['work_revision' '1']] (props 'todo' 'none' (id 103) '' ''))
  =/  denied-owner  (run initial-product alice agent-owner 2.000 policies)
  =/  agent-worker  (command-four 404 101 'work.update-properties' ~[['work_revision' '1']] (props 'todo' 'none' '' (id 103) ''))
  =/  worker  (run initial-product alice agent-worker 2.000 policies)
  =/  denied-target  (run initial-product alice (create-four 405 102 outcomes) 2.000 policies(target absent-target))
  =/  accepted-target  (run initial-product alice (create-four 406 102 outcomes) 2.000 policies)
  =/  private-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 202)] ['document_id' (id 201)] ['expected_revision' '0'] ['base_markdown_sha256' '']])
  =/  private-outcomes  [%o (malt ~[[(id 500) private-target]])]
  =/  private-denied  (run initial-product alice (create-four 408 103 private-outcomes) 2.000 policies(target permissive-target))
  =/  markdown  (cat 3 (header:stead-team (id 201) 'published') 'Saved shared Markdown')
  =/  saved-document  (apply-legacy:stead-product-work db.initial-product product.initial-product alice (command 409 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]]) 2.000)
  =/  existing-denied  (run [db.saved-document product.saved-document] alice (create-four 410 103 outcomes) 2.001 policies(target permissive-target))
  =/  exact-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '1'] ['base_markdown_sha256' '5246215a4c9b7427c502a531ef372f676b3d005f8d26c4f0e166aae2bd6b9c4b']])
  =/  exact-outcomes  [%o (malt ~[[(id 500) exact-target]])]
  =/  exact  (run [db.saved-document product.saved-document] alice (create-four 411 104 exact-outcomes) 2.001 policies)
  ?>  ?=([%o *] exact-target)
  =/  stale-target  [%o (~(put by p.exact-target) 'expected_revision' [%s '2'])]
  =/  stale-outcomes  [%o (malt ~[[(id 500) stale-target]])]
  =/  stale-denied  (run [db.saved-document product.saved-document] alice (create-four 413 106 stale-outcomes) 2.001 policies(target permissive-target))
  =/  code-target  (object ~[['kind' 'code'] ['project_id' (id 100)] ['repository_id' (id 203)] ['target_ref' 'refs/heads/main'] ['base_oid' 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb']])
  =/  code-outcomes  [%o (malt ~[[(id 500) code-target]])]
  =/  code-denied  (run initial-product alice (create-four 412 105 code-outcomes) 2.000 policies(target permissive-target))
  =/  bob-comment  (run [db.worker product.worker] bob comment-a 2.001 policies)
  =/  revoked  (apply-legacy:stead-product-work db.bob-comment product.bob-comment alice (command 407 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 2.002)
  =/  hidden-retry  (run [db.revoked product.revoked] bob comment-a 2.003 policies)
  =/  wire  (need (parse-product:stead-product-codec canonical-bytes.comment-a))
  ?>  ?=([%o *] wire)
  =/  wrong-epoch  (decode:stead-product-codec (canonical [%o (~(put by p.wire) 'authority_epoch' [%s '2'])]))
  =/  epoch-denied  (run initial-product alice wrong-epoch 2.000 policies)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.reader 'error'))
          =('denied_or_not_found' (result-field response.expired 'error'))
          =(product.initial-product product.reader)  =(product.initial-product product.expired)
          =('ineligible_assignment' (result-field response.denied-owner 'error'))
          =('accepted' (result-field response.worker 'status'))
          =('target_unavailable' (result-field response.denied-target 'error'))
          !(~(has by works.data.db.denied-target) [(id 100) (id 102)])
          =('accepted' (result-field response.accepted-target 'status'))
          (box-access:stead-team db.initial-product alice (id 100) (id 202) 2.000)
          =('target_unavailable' (result-field response.private-denied 'error'))
          =('accepted' (result-field response.saved-document 'status'))
          =('target_unavailable' (result-field response.existing-denied 'error'))
          =('accepted' (result-field response.exact 'status'))
          =('target_unavailable' (result-field response.stale-denied 'error'))
          =('target_unavailable' (result-field response.code-denied 'error'))
          =('accepted' (result-field response.bob-comment 'status'))
          =('denied_or_not_found' (result-field response.hidden-retry 'error'))
          =('authority_epoch_conflict' (result-field response.epoch-denied 'error'))
          =(db.initial-product db.epoch-denied)
      ==
++  test-product-work-human-completion-retention-and-explicit-reopen
  =/  complete  (command-four 403 101 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'human-note'] ['note' 'Resolved directly with the customer.']]))
  =/  agent  (run initial-product bob complete 2.000 policies)
  =/  human  (run initial-product bob complete 2.000 policies(kind human-kind))
  =/  direct-done  (command-four 409 101 'work.update-properties' ~[['work_revision' '1']] (props 'done' 'none' '' '' ''))
  =/  shortcut  (run initial-product alice direct-done 2.000 policies)
  =/  own  (command-four 410 101 'work.update-properties' ~[['work_revision' '1']] (props 'todo' 'none' (id 102) '' ''))
  =/  owned  (run initial-product alice own 2.000 policies)
  =/  owner-note  (command-four 411 101 'work.complete' ~[['work_revision' '2'] ['execution_contract_revision' '1']] (object ~[['basis' 'human-note'] ['note' 'Needs the owner.']]))
  =/  nonowner  (run [db.owned product.owned] bob owner-note 2.001 policies(kind human-kind))
  =/  before  (meta product.human 101)
  =/  priority  (command-four 404 101 'work.update-properties' ~[['work_revision' '2']] (props 'done' 'high' '' '' ''))
  =/  retained  (run [db.human product.human] alice priority 2.001 policies)
  =/  noop  (command-four 405 101 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Draft' (object ~)))
  =/  unchanged  (run [db.retained product.retained] alice noop 2.002 policies)
  =/  edit  (command-four 406 101 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Changed after Done' (object ~)))
  =/  blocked  (run [db.unchanged product.unchanged] alice edit 2.003 policies)
  =/  reopen  (command-four 407 101 'work.update-properties' ~[['work_revision' '3']] (props 'in_progress' 'high' '' '' ''))
  =/  reopened  (run [db.blocked product.blocked] alice reopen 2.004 policies)
  =/  fresh-edit  (command-four 408 101 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Changed after Done' (object ~)))
  =/  changed  (run [db.reopened product.reopened] alice fresh-edit 2.005 policies)
  =/  after  (meta product.retained 101)
  =/  final  (meta product.changed 101)
  %-  expect
  !>  ?&  =('human_completion_required' (result-field response.agent 'error'))
          =('completion_required' (result-field response.shortcut 'error'))
          =('owner_completion_required' (result-field response.nonowner 'error'))
          =('accepted' (result-field response.human 'status'))
          =(%human completion-basis.before)
          =((id 103) principal:(need completion.before))
          =('Resolved directly with the customer.' (event-evidence product.human))
          =(completion.before completion.after)
          =('accepted' (result-field response.unchanged 'status'))
          =('reopen_required' (result-field response.blocked 'error'))
          =('accepted' (result-field response.changed 'status'))
          =(%none completion-basis.final)  ?=(~ completion.final)
          =(2 execution-revision.final)
      ==
++  test-product-work-required-outcomes-need-exact-accepted-proof
  =/  created  (run initial-product alice (create-four 401 102 outcomes) 2.000 policies)
  =/  note  (command-four 402 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'human-note'] ['note' 'Cannot override the declared output.']]))
  =/  denied-note  (run [db.created product.created] alice note 2.001 policies)
  =/  pending  (command-four 403 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  absent  (run [db.denied-note product.denied-note] alice pending 2.002 policies)
  =/  bad-command  (command-four 404 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  wrong  (run [db.absent product.absent] alice bad-command 2.003 policies(accepted wrong-proof))
  =/  pin-command  (command-four 406 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  pin  (run [db.wrong product.wrong] alice pin-command 2.004 policies(accepted wrong-pin-proof))
  =/  outcomes-command  (command-four 407 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  wrong-outcomes  (run [db.pin product.pin] alice outcomes-command 2.005 policies(accepted wrong-outcomes-proof))
  =/  good-command  (command-four 405 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  accepted  (run [db.wrong-outcomes product.wrong-outcomes] alice good-command 2.006 policies(accepted fixture-proof))
  =/  current  (meta product.accepted 102)
  %-  expect
  !>  ?&  =('required_outcomes_pending' (result-field response.denied-note 'error'))
          =('required_outcomes_pending' (result-field response.absent 'error'))
          =('required_outcomes_pending' (result-field response.wrong 'error'))
          =('required_outcomes_pending' (result-field response.pin 'error'))
          =('required_outcomes_pending' (result-field response.wrong-outcomes 'error'))
          =(db.created db.wrong)
          =('accepted' (result-field response.accepted 'status'))
          =('done' (field data:(row db.accepted 102) 'status'))
          =(%outcomes completion-basis.current)
          ?=(^ completion.current)
          =((event-evidence product.accepted) evidence:(need completion.current))
          =('fixture accepted output and check receipts' (result-field (event-evidence product.accepted) 'receipt'))
      ==
++  test-product-work-explicit-legacy-assignee-clear-preserves-provenance
  =/  assigned  (apply-command:stead-team db alice (command 350 101 1 'work.assign' ~[['assignee_principal_id' (id 103)]]) 1.006)
  =/  converted  (migrate next.assigned)
  =/  original  (meta product.converted 101)
  =/  priority  (command-four 401 101 'work.update-properties' ~[['work_revision' '2']] (props 'todo' 'high' '' '' ''))
  =/  unchanged  (run converted alice priority 2.000 policies)
  =/  old  (meta product.unchanged 101)
  =/  comment  (command-four 402 101 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'Assignment discussion']]))
  =/  posted  (run [db.unchanged product.unchanged] bob comment 2.001 policies)
  =/  clear  (command-four 403 101 'work.resolve-legacy-assignee' ~[['work_revision' '3']] (object ~[['owner_principal_id' ''] ['worker_principal_id' '']]))
  =/  cleared  (run [db.posted product.posted] alice clear 2.002 policies)
  =/  replay  (run [db.cleared product.cleared] alice clear 2.003 policies)
  =/  stale  (command-four 404 101 'work.resolve-legacy-assignee' ~[['work_revision' '3']] (object ~[['owner_principal_id' ''] ['worker_principal_id' '']]))
  =/  conflict  (run [db.cleared product.cleared] alice stale 2.003 policies)
  =/  repeated  (command-four 405 101 'work.resolve-legacy-assignee' ~[['work_revision' '4']] (object ~[['owner_principal_id' ''] ['worker_principal_id' '']]))
  =/  unavailable  (run [db.cleared product.cleared] alice repeated 2.003 policies)
  =/  implicit  (command-four 406 101 'work.update-properties' ~[['work_revision' '3']] (props 'todo' 'high' (id 102) '' ''))
  =/  denied  (run [db.posted product.posted] alice implicit 2.002 policies)
  =/  current  (meta product.cleared 101)
  =/  legacy  (need legacy-assignee.original)
  %-  expect
  !>  ?&  =('accepted' (result-field response.unchanged 'status'))
          !resolved:(need legacy-assignee.old)
          =('accepted' (result-field response.cleared 'status'))
          =(legacy(resolved &) (need legacy-assignee.current))
          =(4 work-revision.current)  =(1 discussion-sequence.current)
          =(execution-digest.original execution-digest.current)
          =(comments.product.posted comments.product.cleared)
          =('' (field data:(row db.cleared 101) 'owner_principal_id'))
          =('' (field data:(row db.cleared 101) 'worker_principal_id'))
          =(response.cleared response.replay)  =(product.cleared product.replay)
          =('revision_conflict' (result-field response.conflict 'error'))
          =('legacy_resolution_unavailable' (result-field response.unavailable 'error'))
          =('legacy_resolution_required' (result-field response.denied 'error'))
      ==
++  test-product-work-explicit-legacy-resolution-and-immutable-deletion
  =/  blocked-fields  ~[['title' 'Draft'] ['description' 'Notes'] ['type' 'task'] ['status' 'blocked'] ['priority' 'none']]
  =/  legacy-blocked  (apply-command:stead-team db alice (command 350 101 1 'work.update' blocked-fields) 1.006)
  =/  converted  (migrate next.legacy-blocked)
  =/  note  (command-four 401 101 'work.complete' ~[['work_revision' '2'] ['execution_contract_revision' '1']] (object ~[['basis' 'human-note'] ['note' 'Still unresolved.']]))
  =/  denied  (run converted alice note 2.000 policies)
  =/  resolve  (command-four 402 101 'work.resolve-legacy-blocked' ~[['work_revision' '2']] (object ~[['status' 'todo'] ['blocked_reason' '']]))
  =/  resolved  (run [db.denied product.denied] alice resolve 2.001 policies)
  =/  known  (meta product.resolved 101)
  =/  comment  (run initial-product alice comment-a 2.000 policies)
  =/  deletion  (command-four 403 101 'work.delete' ~[['work_revision' '1'] ['execution_contract_revision' '1'] ['discussion_sequence' '1']] (object ~))
  =/  deleted  (run [db.comment product.comment] alice deletion 2.001 policies)
  =/  replay  (run [db.deleted product.deleted] alice deletion 2.002 policies)
  =/  reuse  (run [db.deleted product.deleted] alice (create-four 404 101 (object ~)) 2.003 policies)
  %-  expect
  !>  ?&  =('completion_blocked' (result-field response.denied 'error'))
          =('accepted' (result-field response.resolved 'status'))
          resolved:(need legacy-blocked.known)
          =('blocked' raw-status:(need legacy-blocked.known))
          =('accepted' (result-field response.deleted 'status'))
          =(response.deleted response.replay)  =(product.deleted product.replay)
          (~(has in tombs.db.deleted) [(id 100) 'work' '' (id 101)])
          =(comments.product.comment comments.product.deleted)
          =('revision_conflict' (result-field response.reuse 'error'))
      ==
++  test-product-work-one-mixed-timeline-and-cross-protocol-idempotency
  =/  a  (run initial-product alice comment-a 2.000 policies)
  =/  container  (command 402 250 0 'container.create' ~[['title' 'Docs'] ['visibility' 'shared']])
  =/  legacy  (apply-legacy:stead-product-work db.a product.a alice container 2.001)
  =/  collision  (run [db.legacy product.legacy] alice properties-a 2.002 policies)
  =/  old-collision  (apply-legacy:stead-product-work db.legacy product.legacy alice (command 401 251 0 'container.create' ~[['title' 'Other'] ['visibility' 'shared']]) 2.003)
  =/  old-work  (apply-legacy:stead-product-work db.legacy product.legacy alice (command 403 101 2 'work.update' work-fields) 2.004)
  =/  old-retry  (apply-legacy:stead-product-work db.legacy product.legacy alice (command 304 101 0 'work.create' work-fields) 2.005)
  =/  events  events.product.legacy
  ?>  &(?=(^ events) ?=(^ t.events))
  ?>  ?=(^ journal.data.db.legacy)
  %-  expect
  !>  ?&  =('accepted' (result-field response.legacy 'status'))
          =(%v3 family.i.events)  =(%v4 family.i.t.events)
          =(digest.i.t.events (result-field bytes.i.events 'previous_digest'))
          =(journal.data.db.initial-product t.journal.data.db.legacy)
          =('request_id_reuse' (result-field response.collision 'error'))
          =('request_id_reuse' (result-field response.old-collision 'error'))
          =('unsupported_version' (result-field response.old-work 'error'))
          =(response.create response.old-retry)
          =(product.legacy product.old-retry)  =(db.legacy db.old-retry)
      ==
++  test-product-work-atomic-rollback-on-generation-exhaustion
  ::  Inject the existing uint64 generation boundary to exercise staged rollback.
  =/  before  db.initial-product(generations (~(put by generations.db.initial-product) [(id 100) ''] 18.446.744.073.709.551.615))
  =/  refused  (run [before product.initial-product] alice comment-a 2.000 policies)
  %-  expect
  !>  ?&  =('capacity_exceeded' (result-field response.refused 'error'))
          =(before db.refused)  =(product.initial-product product.refused)
          ?=(~ events.product.refused)  ?=(~ comments.product.refused)
      ==
--

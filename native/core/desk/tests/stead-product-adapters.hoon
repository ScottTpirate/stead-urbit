/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract, stead-product-work, stead-product-codec, stead-principals, stead-product-adapters
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
++  meta
  |=  [product=state:stead-product-state work=@ud]
  ^-  metadata:stead-product-state
  (~(got by works.product) [(id 100) (id work)])
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
=/  shared-box  (apply-command:stead-team db alice (command 351 200 0 'container.create' ~[['title' 'Shared'] ['visibility' 'shared']]) 1.006)
=/  private-box  (apply-command:stead-team next.shared-box alice (command 352 202 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.007)
=/  initial-product  (migrate next.private-box)
=/  comment-a  (command-four 401 101 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'First question']]))
=/  properties-a  (command-four 402 101 'work.update-properties' ~[['work_revision' '1']] (props 'in_progress' 'high' '' '' ''))
=/  doc-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '0'] ['base_markdown_sha256' '']])
=/  outcomes  [%o (malt ~[[(id 500) doc-target]])]
=/  imported  (import:stead-principals registry.db.initial-product ~zod)
=/  person  (declare:stead-principals imported ~zod ~zod (id 102) 1 %person 'Alice' & 1.010)
=/  agent  (declare:stead-principals next.person ~zod ~zod (id 103) 1 %agent 'Bob worker' & 1.011)
=/  declared-reader  (declare:stead-principals next.agent ~zod ~zod (id 104) 1 %person 'Carol' & 1.012)
=/  catalog  next.declared-reader
=/  markdown  (cat 3 (header:stead-team (id 201) 'published') 'Saved shared Markdown')
=/  saved  (apply-legacy:stead-product-work db.initial-product product.initial-product alice (command 450 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]]) 2.000)
=/  exact-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '1'] ['base_markdown_sha256' '5246215a4c9b7427c502a531ef372f676b3d005f8d26c4f0e166aae2bd6b9c4b']])
|%
++  test-product-adapters-hash-exact-markdown-and-stored-length
  =/  hash  (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])
  =/  newline  (cat 3 markdown 10)
  %-  expect
  !>  ?&  =('5246215a4c9b7427c502a531ef372f676b3d005f8d26c4f0e166aae2bd6b9c4b' hash)
          =('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' (markdown-sha256:stead-product-adapters [0 0]))
          !=(hash (markdown-sha256:stead-product-adapters [(met 3 newline) newline]))
          !=(hash (markdown-sha256:stead-product-adapters [+((met 3 markdown)) markdown]))
      ==
++  test-product-adapters-kind-requires-declaration-current-binding-and-grant
  =/  db  db.initial-product
  =/  revoked  (apply-legacy:stead-product-work db product.initial-product alice (command 451 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 2.001)
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 103) 2 %agent 'Bob worker' | 2.001)
  %-  expect
  !>  ?&  ?=(~ (current-kind:stead-product-adapters db imported (id 100) (id 102) 2.000))
          =((some %person) (current-kind:stead-product-adapters db catalog (id 100) (id 102) 2.000))
          =((some %agent) (current-kind:stead-product-adapters db catalog (id 100) (id 103) 2.000))
          ?=(~ (current-kind:stead-product-adapters db catalog (id 100) (id 104) 2.000))
          ?=(~ (current-kind:stead-product-adapters db catalog (id 999) (id 102) 2.000))
          ?=(~ (current-kind:stead-product-adapters db catalog (id 100) (id 999) 2.000))
          ?=(~ (current-kind:stead-product-adapters db catalog (id 100) (id 102) 10.000.000))
          ?=(~ (current-kind:stead-product-adapters db.revoked catalog (id 100) (id 103) 2.002))
          ?=(~ (current-kind:stead-product-adapters db next.disabled (id 100) (id 103) 2.002))
      ==
++  test-product-adapters-target-rechecks-exact-base-audience-and-verified-actor
  ?>  ?=([%o *] exact-target)
  =/  wrong-hash  [%o (~(put by p.exact-target) 'base_markdown_sha256' [%s (hex 64 0)])]
  =/  wrong-revision  [%o (~(put by p.exact-target) 'expected_revision' [%s '2'])]
  =/  private  [%o (~(put by p.exact-target) 'collection_id' [%s (id 202)])]
  =/  malformed  [%o (~(put by p.exact-target) 'expected_revision' [%s '01'])]
  =/  spoof  alice(identity identity.alice(binding (id 999)))
  =/  edited  (cat 3 markdown ' ')
  =/  advanced  (apply-legacy:stead-product-work db.saved product.saved alice (command 452 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' edited]]) 2.002)
  %-  expect
  !>  ?&  =('accepted' (result-field response.saved 'status'))
          (current-target:stead-product-adapters db.initial-product alice (id 100) (id 101) (id 102) doc-target 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) doc-target 2.001)
          (current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) exact-target 2.001)
          (current-target:stead-product-adapters db.saved bob (id 100) (id 101) (id 103) exact-target 2.001)
          !(current-target:stead-product-adapters db.saved carol (id 100) (id 101) (id 104) exact-target 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 103) exact-target 2.001)
          !(current-target:stead-product-adapters db.saved spoof (id 100) (id 101) (id 102) exact-target 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 999) (id 101) (id 102) exact-target 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) wrong-hash 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) wrong-revision 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) private 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) malformed 2.001)
          !(current-target:stead-product-adapters db.saved alice (id 100) (id 101) (id 102) exact-target 10.000.000)
          =('accepted' (result-field response.advanced 'status'))
          !(current-target:stead-product-adapters db.advanced alice (id 100) (id 101) (id 102) exact-target 2.003)
      ==
++  test-product-adapters-real-work-flow-keeps-accepted-output-proof-required
  =/  real  (current:stead-product-adapters db.initial-product catalog alice)
  =/  unknown  (current:stead-product-adapters db.initial-product imported alice)
  =/  assign  (command-four 460 101 'work.update-properties' ~[['work_revision' '1']] (props 'todo' 'none' (id 102) (id 103) ''))
  =/  denied  (run initial-product alice assign 2.000 unknown)
  =/  assigned  (run initial-product alice assign 2.000 real)
  =/  created  (run initial-product alice (create-four 461 102 outcomes) 2.000 real)
  =/  required  (command-four 462 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  completion  (run [db.created product.created] alice required 2.001 (current:stead-product-adapters db.created catalog alice))
  =/  note  (command-four 463 102 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'human-note'] ['note' 'Not an accepted output']]))
  =/  bypass  (run [db.created product.created] alice note 2.001 (current:stead-product-adapters db.created catalog alice))
  =/  ordinary  (command-four 464 101 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'human-note'] ['note' 'Resolved with the customer']]))
  =/  undeclared  (run initial-product alice ordinary 2.000 unknown)
  =/  human  (run initial-product alice ordinary 2.000 real)
  %-  expect
  !>  ?&  =('ineligible_assignment' (result-field response.denied 'error'))
          =('accepted' (result-field response.assigned 'status'))
          =('accepted' (result-field response.created 'status'))
          =('required_outcomes_pending' (result-field response.completion 'error'))
          =('required_outcomes_pending' (result-field response.bypass 'error'))
          =('human_completion_required' (result-field response.undeclared 'error'))
          =('accepted' (result-field response.human 'status'))
      ==
--

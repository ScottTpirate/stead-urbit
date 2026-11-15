::  Real pure reducer fixtures; no Home route, native execution or restored
::  live authority is claimed. All identities and documents are disposable.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-principals, stead-actor, stead-product-codec, stead-product-state, stead-product-migrate, stead-product-work, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-run-state, stead-run, stead-run-adapters
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  result-field
  |=  [raw=@t name=@t]
  ^-  @t
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (field p.value name)
++  put
  |=  [value=json key=@t next=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key next)]
++  command
  |=  [req=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  base  (object ~[['protocol' 'stead.command/3'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
  (decode:stead-team-codec (canonical (put base 'payload' (object payload))))
++  four
  |=  [req=@ud operation=@t expected=(list [@t @t]) payload=json]
  ^-  command:stead-product-codec
  =/  base  (object ~[['protocol' 'stead.command/4'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id 111)] ['authority_epoch' '1'] ['operation' operation]])
  (decode:stead-product-codec (canonical (put (put base 'expected' (object expected)) 'payload' payload)))
++  properties
  |=  [owner=@t worker=@t]
  ^-  json
  (object ~[['type' 'task'] ['status' 'todo'] ['priority' 'none'] ['owner_principal_id' owner] ['worker_principal_id' worker] ['blocked_reason' '']])
++  goal
  |=  [title=@t outcomes=json]
  ^-  json
  (put (object ~[['title' title] ['description' 'Use the exact shared source.'] ['acceptance_criteria' 'Independent human review.']]) 'required_outcomes' outcomes)
++  migrate
  |=  db=state:stead-team
  ^-  migrated:stead-product-migrate
  =/  job  (begin:stead-product-migrate db ~zod)
  =/  left=@ud  1.024
  |-
  ?:  ?|(=(%valid phase.job) =(%invalid phase.job))  (need (result:stead-product-migrate job))
  ?>  (gth left 0)
  $(job (step:stead-product-migrate job), left (dec left))
++  target
  |=  [document=@ud revision=@ud markdown=@t]
  ^-  json
  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id document)] ['expected_revision' (decimal revision)] ['base_markdown_sha256' markdown]])
++  change-work
  |=  [state=snapshot:stead-run-adapters actor=authentication:stead-team cmd=command:stead-product-codec now=@ud]
  ^-  snapshot:stead-run-adapters
  =/  out  (apply-command:stead-product-work db.state product.state actor cmd now (current:stead-product-adapters db.state catalog.state actor))
  ?>  =('accepted' (result-field response.out 'status'))
  state(db db.out, product product.out)
++  legacy
  |=  [state=snapshot:stead-run-adapters actor=authentication:stead-team cmd=command:stead-codec now=@ud]
  ^-  snapshot:stead-run-adapters
  =/  out  (apply-legacy:stead-product-work db.state product.state actor cmd now)
  ?>  =('accepted' (result-field response.out 'status'))
  state(db db.out, product product.out)
++  run-command
  |=  [req=@ud expected=@ud attempt=@ud operation=operation:stead-run-state]
  ^-  command:stead-run-state
  [(id req) (id 100) (id 600) expected attempt operation]
++  gates
  |=  [state=snapshot:stead-run-adapters runs=state:stead-run-state book=live:stead-run-state]
  ^-  gates:stead-run-state
  (current:stead-run-adapters state runs book [(id 100) (id 600)])
++  apply-run
  |=  [state=snapshot:stead-run-adapters prior=transition:stead-run-state actor=verified:stead-actor cmd=command:stead-run-state now=@ud]
  ^-  transition:stead-run-state
  (apply:stead-run next.prior live.prior actor cmd now (gates state next.prior live.prior) [0 0 0])
++  doc-command
  |=  [item=contract:stead-run-state markdown=@t]
  ^-  command:stead-doc-change-codec
  =/  base  (object ~[['protocol' 'stead.doc-change/1'] ['request_id' (id 750)] ['project_id' (id 100)] ['work_id' (id 111)] ['change_id' (id 601)] ['authority_epoch' '1'] ['expected_revision' '0'] ['operation' 'change.submit']])
  ?>  ?=(^ targets.item)
  =/  payload  (object ~[['outcome_id' (id 500)] ['markdown' markdown] ['summary' 'An exact agent proposal'] ['execution_contract_revision' (decimal execution-revision.item)] ['execution_contract_digest' execution-digest.item] ['run_id' (id 600)] ['attempt' '1']])
  (decode:stead-doc-change-codec (canonical (put base 'payload' (put payload 'target' (target 201 revision.i.targets.item markdown.i.targets.item)))))
--
=/  configuration
  %-  rap
  :-  3
  :~  '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{'
      '"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000102","binding_id":"019939ba-4000-7000-8000-000000000202","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Alice"},'
      '"~nec":{"principal_id":"019939ba-4000-7000-8000-000000000103","binding_id":"019939ba-4000-7000-8000-000000000203","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Worker"},'
      '"~bud":{"principal_id":"019939ba-4000-7000-8000-000000000104","binding_id":"019939ba-4000-7000-8000-000000000204","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Carol"}'
      '},"project_creators":{"019939ba-4000-7000-8000-000000000102":"yes"}}'
  ==
=/  initial  (configure:stead-team empty:stead-team configuration ~zod 1.000)
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  bob  (need (native-context:stead-team initial ~nec 1.001))
=/  carol  (need (native-context:stead-team initial ~bud 1.001))
=/  project  (apply-command:stead-team initial alice (command 301 100 0 'project.create' ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' 'Stead'] ['project_key' 'STEAD'] ['preset' 'general']]) 1.002)
=/  editor  (apply-command:stead-team next.project alice (command 302 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' (id 103)] ['role' 'contributor'] ['expires_at_ms' '8000000']]) 1.003)
=/  reader  (apply-command:stead-team next.editor alice (command 303 100 2 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' (id 104)] ['role' 'reader'] ['expires_at_ms' '5000']]) 1.004)
=/  shared  (apply-command:stead-team next.reader alice (command 351 200 0 'container.create' ~[['title' 'Shared'] ['visibility' 'shared']]) 1.005)
=/  private  (apply-command:stead-team next.shared alice (command 352 202 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.006)
=/  markdown  (cat 3 (header:stead-team (id 201) 'published') 'Shared original Markdown')
=/  saved  (apply-command:stead-team next.private alice (command 353 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]]) 1.007)
=/  pair  (migrate next.saved)
=/  imported  (import:stead-principals registry.db.pair ~zod)
=/  human  (declare:stead-principals imported ~zod ~zod (id 102) 1 %person 'Alice' & 2.000)
=/  agent  (declare:stead-principals next.human ~zod ~zod (id 103) 1 %agent 'Named agent' & 2.001)
=/  person  (declare:stead-principals next.agent ~zod ~zod (id 104) 1 %person 'Carol' & 2.002)
=/  runtime  (runtime-put:stead-principals next.person ~zod ~zod (id 701) 0 (id 103) 'native-pilot' (hex 64 71) 2.003)
=/  definition  (definition-put:stead-principals next.runtime ~zod ~zod (id 702) 0 (id 103) (hex 64 72) (id 701) 1 2.004)
=/  base=snapshot:stead-run-adapters  [db.pair product.pair next.definition ~ empty:stead-doc-change-state]
=/  sha  (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])
=/  outcomes  [%o (malt ~[[(id 500) (target 201 1 sha)]])]
=/  create
  =/  props  (properties (id 102) (id 103))
  =/  contract  (goal 'Revise the shared guide' outcomes)
  ?>  &(?=([%o *] props) ?=([%o *] contract))
  (four 401 'work.create' ~[['work_revision' '0'] ['execution_contract_revision' '0']] [%o (~(uni by p.props) p.contract)])
=/  prepared  (change-work base alice create 2.100)
=/  metadata  (~(got by works.product.prepared) [(id 100) (id 111)])
=/  unsealed=contract:stead-run-state
  :*  ~zod  (id 100)  (id 111)  1  execution-revision.metadata  execution-digest.metadata
      (id 102)  (id 102)  %explicit  (id 103)  (id 203)  1
      (id 702)  1  (id 701)  1
      (scope-key:stead-core (id 100) (id 501))
      (~(got by grants.data.db.prepared) (scope-key:stead-core (id 100) (id 501)))
      (hex 64 0)  ~[[(id 500) (id 200) (id 201) 1 sha]]
      [600.000 [8 0 0 0 65.536 32.768]]  600.000
  ==
=/  context  (need (context:stead-run-adapters prepared unsealed 2.101))
=/  task  unsealed(context digest.context)
=/  book  (empty-live:stead-run (hex 64 700))
=/  empty=transition:stead-run-state  ['' *state:stead-run-state book ~ ~]
=/  issue-command  (run-command 701 0 0 [%issue task])
=/  issued  (apply-run prepared empty [%native alice] issue-command 3.000)
=/  claim-command  (run-command 702 1 0 [%claim ~])
=/  claimed  (apply-run prepared issued [%native bob] claim-command 3.001)
|%
++  test-run-adapters-real-owner-issue-and-named-agent-claim
  =/  repeated  (apply-run prepared claimed [%native bob] claim-command 3.002)
  =/  human-claim  (apply-run prepared issued [%native alice] claim-command 3.002)
  =/  reader-issue  (apply-run prepared empty [%native carol] (run-command 703 0 0 [%issue task(requester (id 104))]) 3.002)
  =/  read  (gates prepared next.claimed live.claimed)
  %-  expect
  !>  ?&  =('accepted' (result-field response.issued 'status'))
          =('accepted' (result-field response.claimed 'status'))
          =('rejected' (result-field response.human-claim 'status'))
          =('rejected' (result-field response.reader-issue 'status'))
          =(response.claimed response.repeated)  ?=(~ intents.repeated)
          =(1 (lent intents.claimed))
          (policy.read [%native carol] task %read 3.002)
          !(policy.read [%native carol] task %answer 3.002)
          !(policy.read [%native bob] task %issue 3.002)
          =(digest.context (hash 'stead.run-context/1' bytes.context))
      ==
++  test-run-adapters-comment-stable-but-changed-goal-not-executable
  =/  commented  (change-work prepared bob (four 402 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'Clarify the audience.']])) 3.010)
  =/  edited  (change-work commented alice (four 403 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Changed execution goal' outcomes)) 3.011)
  =/  same  (gates commented next.claimed live.claimed)
  =/  stale  (gates edited next.claimed live.claimed)
  =/  heartbeat  (apply-run edited claimed [%native bob] (run-command 704 2 1 [%heartbeat ~]) 3.012)
  %-  expect
  !>  ?&  =((some context) (context:stead-run-adapters commented task 3.011))
          (pins.same task %execute 3.011)
          !(pins.stale task %execute 3.012)  (pins.stale task %read 3.012)
          (policy.stale [%native bob] task %read 3.012)
          =('rejected' (result-field response.heartbeat 'status'))
          =(heads.next.claimed heads.next.heartbeat)
          =(attempts.next.claimed attempts.next.heartbeat)
          =(live.claimed live.heartbeat)  ?=(~ intents.heartbeat)
          ?=(^ record.heartbeat)
      ==
++  test-run-adapters-assignment-and-base-changes-retain-visible-history
  =/  unassigned  (change-work prepared alice (four 404 'work.update-properties' ~[['work_revision' '1']] (properties (id 102) '')) 3.010)
  =/  ownerless  (change-work prepared alice (four 405 'work.update-properties' ~[['work_revision' '1']] (properties '' (id 103))) 3.010)
  =/  changed  (legacy prepared alice (command 406 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' (cat 3 markdown ' changed')]]) 3.010)
  =/  assigned  (gates unassigned next.claimed live.claimed)
  =/  advanced  (gates changed next.claimed live.claimed)
  =/  absent  (gates ownerless next.claimed live.claimed)
  %-  expect
  !>  ?&  !(pins.assigned task %execute 3.011)
          (pins.assigned task %read 3.011)  (policy.assigned [%native bob] task %read 3.011)
          !(pins.advanced task %execute 3.011)
          (policy.advanced [%native bob] task %read 3.011)
          !(pins.absent task %execute 3.011)
          !(pins.absent task(owner-source %steward) %execute 3.011)
          !(pins.assigned task(owner (id 104)) %execute 3.011)
      ==
++  test-run-adapters-current-catalog-grant-and-original-expiry
  =/  disabled  (declare:stead-principals catalog.prepared ~zod ~zod (id 103) 2 %agent 'Named agent' | 3.010)
  =/  revoked  (legacy prepared alice (command 407 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 3.010)
  =/  extra  (legacy prepared alice (command 408 100 3 'policy.grant' ~[['grant_id' (id 503)] ['principal_id' (id 103)] ['role' 'contributor'] ['expires_at_ms' '9000000']]) 3.010)
  =/  old-revoked  (legacy extra alice (command 409 100 4 'policy.revoke' ~[['grant_id' (id 501)]]) 3.011)
  =/  inactive  (gates prepared(catalog next.disabled) next.claimed live.claimed)
  =/  denied  (gates revoked next.claimed live.claimed)
  =/  renewed  (gates old-revoked next.claimed live.claimed)
  =/  current  (gates prepared next.claimed live.claimed)
  %-  expect
  !>  ?&  ?=(~ (member.inactive [%native bob] task 3.012))
          ?=(~ (member.denied [%native bob] task 3.012))
          ?=(^ (member.renewed [%native bob] task 3.012))
          !(original.renewed task 3.012)  !(pins.renewed task %execute 3.012)
          ?=(~ (member.current [%native bob] task 8.000.000))
          ?=(~ (member.current [%native carol] task 5.000))
          !(original.current task 8.000.000)
      ==
++  test-run-adapters-versioned-runtime-pins-and-default-deny-effects
  =/  next-runtime  (runtime-put:stead-principals catalog.prepared ~zod ~zod (id 701) 1 (id 103) 'native-pilot-v2' (hex 64 73) 3.010)
  =/  next-definition  (definition-put:stead-principals next.next-runtime ~zod ~zod (id 702) 1 (id 103) (hex 64 74) (id 701) 2 3.011)
  =/  current  (gates prepared(catalog next.next-definition) next.claimed live.claimed)
  =/  intent=intent:stead-run-state  [(id 710) %provider-call (id 711) (hex 64 1) ~ [1 1 1 1 1 1]]
  =/  effect=effect:stead-run-state  [intent %pending '' '']
  =/  resolution=settlement:stead-run-state  [(id 710) %settled (hex 64 2) (hex 64 3)]
  %-  expect
  !>  ?&  (pins.current task %execute 3.012)
          !(pins.current task(definition-revision 2) %execute 3.012)
          !(pins.current task(runtime-revision 2) %execute 3.012)
          !(effect.current [%native bob] task 1 intent 3.012)
          !(settled.current task 1 effect resolution 3.012)
          !(reconciled.current task 1 (hex 64 1) (hex 64 2) 3.012)
          !(policy.current [%native bob] task %replace 3.012)
          !(policy.current [%service *service:stead-actor] task %read 3.012)
      ==
++  test-run-adapters-actual-doc-receipt-required-before-finish
  =/  draft  (cat 3 markdown ' proposed')
  =/  cmd  (doc-command task draft)
  =/  submitted  (apply:stead-doc-change [db.prepared product.prepared changes.prepared] catalog.prepared bob cmd 3.010 (doc-runs:stead-run-adapters prepared next.claimed live.claimed) no-other:stead-doc-change)
  =/  candidate  prepared(db db.next.submitted, product product.next.submitted, changes changes.next.submitted)
  =/  head  (~(got by heads.changes.candidate) [(id 100) (id 601)])
  =/  output  (~(got by results.changes.candidate) [(id 100) (id 601) 1])
  =/  reference=result-reference:stead-run-state  [(id 601) 1 output-digest.head (id 500)]
  =/  current  (gates candidate next.claimed live.claimed)
  =/  forged  (gates candidate(changes changes.candidate(attempts ~)) next.claimed live.claimed)
  =/  entry  (~(got by attempts.changes.candidate) [(id 100) (id 103) (id 750)])
  =/  receipt  (need (parse-result receipt.entry))
  =/  extra  (canonical (put receipt 'claimed_authority' [%s 'yes']))
  =/  wrong-revision  (canonical (put receipt 'resulting_revision' [%s '0']))
  =/  wrong-error  (canonical (put receipt 'error' [%s 'producer_unavailable']))
  =/  rejects
    %+  levy  ~[extra wrong-revision wrong-error]
    |=  raw=@t
    =/  altered  candidate(changes changes.candidate(attempts (~(put by attempts.changes.candidate) [(id 100) (id 103) (id 750)] entry(receipt raw))))
    =/  check  (gates altered next.claimed live.claimed)
    !(result.check task 1 reference 3.011)
  =/  finished  (apply-run candidate claimed [%native bob] (run-command 705 2 1 [%finish reference]) 3.011)
  =/  after  (doc-runs:stead-run-adapters candidate next.finished live.finished)
  =/  stopped  (doc-runs:stead-run-adapters candidate next.claimed book)
  %-  expect
  !>  ?&  =('accepted' (result-field response.submitted 'status'))
          ?=(^ record.submitted)
          (result.current task 1 reference 3.011)
          !(result.current task 1 reference(outcome (id 599)) 3.011)
          !(result.current task 2 reference 3.011)
          !(result.forged task 1 reference 3.011)
          rejects
          =('accepted' (result-field response.finished 'status'))
          =(%live (after output 3.012))
          =(%expired (after output 600.000))
          =(%unknown (stopped output 3.012))
      ==
++  test-run-adapters-context-is-shared-scoped-and-byte-bounded
  =/  current  (gates prepared next.claimed live.claimed)
  =/  private-task  task(targets ~[[(id 500) (id 202) (id 201) 1 sha]])
  =/  big  (cat 3 (header:stead-team (id 201) 'published') (fil 3 32.600 'a'))
  =/  other  (cat 3 (header:stead-team (id 205) 'published') (fil 3 32.600 'b'))
  =/  first  (legacy prepared alice (command 410 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' big]]) 3.010)
  =/  second  (legacy first alice (command 411 205 0 'document.save' ~[['container_id' (id 200)] ['markdown' other]]) 3.011)
  =/  big-sha  (markdown-sha256:stead-product-adapters [(met 3 big) big])
  =/  other-sha  (markdown-sha256:stead-product-adapters [(met 3 other) other])
  =/  targets  [%o (malt ~[[(id 500) (target 201 2 big-sha)] [(id 501) (target 205 1 other-sha)]])]
  =/  expanded  (change-work second alice (four 412 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Large context' targets)) 3.012)
  =/  meta  (~(got by works.product.expanded) [(id 100) (id 111)])
  =/  large  task(execution-revision execution-revision.meta, execution-digest execution-digest.meta, targets ~[[(id 500) (id 200) (id 201) 2 big-sha] [(id 501) (id 200) (id 205) 1 other-sha]])
  %-  expect
  !>  ?&  ?=(~ (context:stead-run-adapters prepared private-task 3.010))
          ?=(~ (member.current [%native alice] private-task 3.010))
          ?=(~ (context:stead-run-adapters prepared task(budget budget.task(limits limits.budget.task(input 1))) 3.010))
          ?=(~ (context:stead-run-adapters expanded large 3.013))
          (lte (met 3 bytes.context) 65.536)
      ==
++  test-run-adapters-current-authority-before-retries-and-clarification
  =/  waiting  (apply-run prepared claimed [%native bob] (run-command 706 2 1 [%wait 'Which audience?']) 3.010)
  =/  wrong  (apply-run prepared waiting [%native bob] (run-command 707 3 1 [%answer 1 'I decide.']) 3.011)
  =/  answered  (apply-run prepared waiting [%native alice] (run-command 708 3 1 [%answer 1 'New members.']) 3.011)
  =/  resumed  (apply-run prepared answered [%native bob] (run-command 709 4 1 [%resume 1]) 3.012)
  =/  disabled  (declare:stead-principals catalog.prepared ~zod ~zod (id 103) 2 %agent 'Named agent' | 3.013)
  =/  retry  (apply-run prepared(catalog next.disabled) claimed [%native bob] claim-command 3.014)
  =/  current  (gates prepared next.claimed live.claimed)
  %-  expect
  !>  ?&  =('accepted' (result-field response.waiting 'status'))
          =('rejected' (result-field response.wrong 'status'))
          =('accepted' (result-field response.answered 'status'))
          =('accepted' (result-field response.resumed 'status'))
          =('rejected' (result-field response.retry 'status'))
          !=(response.claimed response.retry)  ?=(~ intents.retry)
          (used.current [(id 100) (id 102) (id 401)])
          !(used.current [(id 100) (id 102) (id 999)])
      ==
--

::  Reserved run read fixtures; real pure reducers prepare disposable data.
::  No native execution, public route or automatic dispatch is claimed.
/+  *test, stead-views, stead-run-query, stead-run-views, stead-codec, stead-core, stead-team, stead-team-codec, stead-principals, stead-actor, stead-product-codec, stead-product-state, stead-product-migrate, stead-product-work, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-run-state, stead-run, stead-run-adapters
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
++  query
  |=  [kind=@t run=@t cursor=@t]
  ^-  query:stead-run-query
  [(id 950) kind (id 100) (id 111) run cursor]
++  read
  |=  [state=snapshot:stead-run-adapters runs=state:stead-run-state live=live:stead-run-state pages=state:stead-views actor=authentication:stead-team request=query:stead-run-query now=@ud]
  ^-  result:stead-run-views
  (execute:stead-run-views state runs live pages actor request now 0xaaaa)
++  parsed
  |=  raw=@t
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  p.value
++  rows
  |=  raw=@t
  ^-  object-map
  =/  value  (~(got by (parsed raw)) 'rows')
  ?>  ?=([%o *] value)
  p.value
++  first-row
  |=  raw=@t
  ^-  object-map
  =/  value  (~(got by (rows raw)) '0')
  ?>  ?=([%o *] value)
  p.value
++  refused
  |=  raw=@t
  ^-  ?
  ?=([%| *] (mule |.((decode:stead-run-query raw))))
++  many
  ^-  state:stead-run-state
  =/  runs  *state:stead-run-state
  =/  index=@ud  0
  |-
  ?:  =(index 22)  runs
  =/  key=run-key:stead-run-state  [(id 100) (id (add 600 index))]
  =/  cmd=command:stead-run-state  [(id (add 800 index)) (id 100) run.key 0 0 [%issue task]]
  =/  out  (apply:stead-run runs book [%native alice] cmd (add 4.000 index) (current:stead-run-adapters prepared runs book key) [index 0 0])
  ?>  =('accepted' (result-field response.out 'status'))
  $(runs next.out, index +(index))
++  test-run-views-closed-seven-field-query-and-exact-scope
  =/  listing  (query 'runs' '' '')
  =/  detail  (query 'run' (id 600) '')
  =/  wire  [%o (parsed (bytes:stead-run-query listing))]
  %-  expect
  !>  ?&  =(listing (decode:stead-run-query (bytes:stead-run-query listing)))
          =(detail (decode:stead-run-query (bytes:stead-run-query detail)))
          =(7 (lent ~(tap by (parsed (bytes:stead-run-query detail)))))
          (refused (canonical (put wire 'context' [%s 'private body'])))
          (refused (canonical (put wire 'protocol' [%s 'stead.run-query/2'])))
          (refused (bytes:stead-run-query listing(work '')))
          (refused (bytes:stead-run-query listing(run (id 600))))
          (refused (bytes:stead-run-query detail(cursor (hex 64 1))))
          (refused (bytes:stead-run-query detail(kind 'all-runs')))
      ==
++  test-run-views-exact-counts-and-durable-phase-versus-live-lease
  =/  listing  (read prepared next.claimed live.claimed *state:stead-views alice (query 'runs' '' '') 3.010)
  =/  detail  (read prepared next.claimed live.claimed *state:stead-views alice (query 'run' (id 600) '') 3.010)
  =/  missing  (read prepared next.claimed book *state:stead-views alice (query 'run' (id 600) '') 3.010)
  =/  stale  (read prepared next.claimed live.claimed(incarnation (hex 64 701)) *state:stead-views alice (query 'run' (id 600) '') 3.010)
  =/  expired  (read prepared next.claimed live.claimed *state:stead-views alice (query 'run' (id 600) '') 130.000)
  =/  original  (~(got by heads.next.claimed) [(id 100) (id 600)])
  =/  damaged  next.claimed(heads (~(put by heads.next.claimed) [(id 100) (id 600)] original(phase %submitted)))
  =/  refused  (read prepared damaged live.claimed *state:stead-views alice (query 'run' (id 600) '') 3.010)
  =/  unnamed
    =/  people  principals.catalog.prepared
    =/  owner  (~(got by people) (id 102))
    =/  worker  (~(got by people) (id 103))
    =.  people  (~(put by people) (id 102) owner(display ''))
    =.  people  (~(put by people) (id 103) worker(display ''))
    prepared(catalog catalog.prepared(principals people))
  =/  retained  (read unnamed next.claimed live.claimed *state:stead-views alice (query 'run' (id 600) '') 3.010)
  =/  value  (first-row response.detail)
  =/  attempt  (parsed (field value 'current_attempt_detail'))
  %-  expect
  !>  ?&  =(19 (lent ~(tap by (first-row response.listing))))
          =(25 (lent ~(tap by value)))
          =('running' (field value 'phase'))  =('live' (field value 'lease_state'))
          =('unknown-book' (field (first-row response.missing) 'lease_state'))
          =('unknown-book' (field (first-row response.stale) 'lease_state'))
          =('expired' (field (first-row response.expired) 'lease_state'))
          =('running' (field (first-row response.expired) 'phase'))
          =('invalid_product_state' (result-field response.refused 'error'))
          =('read' (result-field response.retained 'status'))
          =('' (field (first-row response.retained) 'requester_display_name'))
          =('' (field (first-row response.retained) 'owner_display_name'))
          =('' (field (first-row response.retained) 'worker_display_name'))
          =(7 (lent ~(tap by attempt)))
          !(~(has by attempt) 'audit')  !(~(has by value) 'grant')
          !(~(has by value) 'context')  !(~(has by value) 'incarnation')
          =(*state:stead-views next.detail)
      ==
++  test-run-views-real-clarification-and-recorded-doc-result
  =/  waiting  (apply-run prepared claimed [%native bob] (run-command 706 2 1 [%wait 'Which audience?']) 3.010)
  =/  answered  (apply-run prepared waiting [%native alice] (run-command 708 3 1 [%answer 1 'New members.']) 3.011)
  =/  detail  (read prepared next.answered live.answered *state:stead-views alice (query 'run' (id 600) '') 3.012)
  =/  question  (parsed (field (first-row response.detail) 'latest_question'))
  =/  answer  (parsed (field question 'answer'))
  =/  submitted  (apply:stead-doc-change [db.prepared product.prepared changes.prepared] catalog.prepared bob (doc-command task (cat 3 markdown ' proposed')) 3.020 (doc-runs:stead-run-adapters prepared next.claimed live.claimed) no-other:stead-doc-change)
  =/  candidate  prepared(db db.next.submitted, product product.next.submitted, changes changes.next.submitted)
  =/  output  (~(got by results.changes.candidate) [(id 100) (id 601) 1])
  =/  reference=result-reference:stead-run-state  [(id 601) 1 digest.output (id 500)]
  =/  finished  (apply-run candidate claimed [%native bob] (run-command 705 2 1 [%finish reference]) 3.021)
  =/  result  (read candidate next.finished live.finished *state:stead-views alice (query 'run' (id 600) '') 600.001)
  =/  fields  (first-row response.result)
  %-  expect
  !>  ?&  =('Which audience?' (field question 'text'))
          =((id 103) (field question 'principal_id'))
          =('New members.' (field answer 'text'))
          =((id 102) (field answer 'principal_id'))
          =('waiting' (field (first-row response.detail) 'phase'))
          =('submitted' (field fields 'phase'))
          =('terminal' (field fields 'lease_state'))
          =((result-bytes:stead-run-state reference) (field fields 'result'))
          =(4 (lent ~(tap by (parsed (field fields 'result')))))
          !(~(has by fields) 'accepted')  !(~(has by fields) 'markdown')
      ==
++  test-run-views-current-revocation-and-stale-contract-are-distinct
  =/  disabled  (declare:stead-principals catalog.prepared ~zod ~zod (id 103) 2 %agent 'Named agent' | 3.010)
  =/  denied  (read prepared(catalog next.disabled) next.claimed live.claimed *state:stead-views bob (query 'run' (id 600) '') 3.011)
  =/  revoked  (legacy prepared alice (command 407 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 3.010)
  =/  removed  (read revoked next.claimed live.claimed *state:stead-views bob (query 'runs' '' '') 3.011)
  =/  expired  (read prepared next.claimed live.claimed *state:stead-views carol (query 'run' (id 600) '') 5.000)
  =/  edited  (change-work prepared alice (four 403 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Changed goal' outcomes)) 3.010)
  =/  retained  (read edited next.claimed live.claimed *state:stead-views bob (query 'run' (id 600) '') 3.011)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.denied 'error'))
          =('denied_or_not_found' (result-field response.removed 'error'))
          =('denied_or_not_found' (result-field response.expired 'error'))
          !(~(has by (parsed response.denied)) 'rows')
          =('read' (result-field response.retained 'status'))
          =('no' (field (first-row response.retained) 'execution_current'))
          =('running' (field (first-row response.retained) 'phase'))
      ==
++  test-run-views-private-writes-and-other-scope-do-not-leak
  =/  draft  (cat 3 (header:stead-team (id 206) 'draft') 'PRIVATE-ONLY-MARKER')
  =/  changed  (legacy prepared alice (command 413 206 0 'document.save' ~[['container_id' (id 202)] ['markdown' draft]]) 3.010)
  =/  before  (read prepared next.claimed live.claimed *state:stead-views bob (query 'runs' '' '') 3.011)
  =/  after  (read changed next.claimed live.claimed *state:stead-views bob (query 'runs' '' '') 3.011)
  =/  detail  (query 'run' (id 600) '')
  =/  listing  (query 'runs' '' '')
  =/  other-work  (read prepared next.claimed live.claimed *state:stead-views bob detail(work (id 999)) 3.011)
  =/  other-project  (read prepared next.claimed live.claimed *state:stead-views bob listing(project (id 999)) 3.011)
  %-  expect
  !>  ?&  =(response.before response.after)
          =('denied_or_not_found' (result-field response.other-work 'error'))
          =('denied_or_not_found' (result-field response.other-project 'error'))
          !?=(^ (find (trip 'PRIVATE-ONLY-MARKER') (trip response.after)))
          !(~(has by (first-row response.after)) 'context')
      ==
++  test-run-views-twenty-row-pages-and-one-use-cursors
  =/  runs  many
  =/  first  (read prepared runs book *state:stead-views alice (query 'runs' '' '') 4.100)
  =/  token  (result-field response.first 'cursor')
  =/  second  (read prepared runs book next.first alice (query 'runs' '' token) 4.101)
  =/  replay  (read prepared runs book next.second alice (query 'runs' '' token) 4.102)
  =/  other-actor  (read prepared runs book next.first bob (query 'runs' '' token) 4.101)
  =/  record  (~(got by cursors.next.first) token)
  =/  wrong-book  next.first(cursors (~(put by cursors.next.first) token record(purpose 'doc-change-query')))
  =/  wrong-purpose  (read prepared runs book wrong-book alice (query 'runs' '' token) 4.101)
  =/  expired  (read prepared runs book next.first alice (query 'runs' '' token) 304.100)
  %-  expect
  !>  ?&  =(20 (lent ~(tap by (rows response.first))))
          =(2 (lent ~(tap by (rows response.second))))
          !=('' token)  =('' (result-field response.second 'cursor'))
          =('stale_cursor' (result-field response.replay 'error'))
          =('stale_cursor' (result-field response.other-actor 'error'))
          =('stale_cursor' (result-field response.wrong-purpose 'error'))
          =('stale_cursor' (result-field response.expired 'error'))
          =(next.first next.other-actor)  =(wrong-book next.wrong-purpose)
          (lte (met 3 response.first) 262.144)
      ==
++  test-run-views-cursors-bind-current-generation-and-work-filter
  =/  runs  many
  =/  first  (read prepared runs book *state:stead-views alice (query 'runs' '' '') 4.100)
  =/  token  (result-field response.first 'cursor')
  =/  changed  (apply:stead-run runs book [%native bob] (run-command 850 1 0 [%claim ~]) 4.101 (gates prepared runs book) [22 0 0])
  =/  stale  (read prepared next.changed live.changed next.first alice (query 'runs' '' token) 4.102)
  =/  create-json  (need (parse-product:stead-product-codec canonical-bytes.create))
  =/  other-command  (decode:stead-product-codec (canonical (put (put create-json 'request_id' [%s (id 414)]) 'resource_id' [%s (id 112)])))
  =/  other  (change-work prepared alice other-command 4.101)
  =/  filter  (query 'runs' '' token)
  =/  crossed  (read other runs book next.first alice filter(work (id 112)) 4.102)
  %-  expect
  !>  ?&  =('accepted' (result-field response.changed 'status'))
          =('stale_cursor' (result-field response.stale 'error'))
          =('stale_cursor' (result-field response.crossed 'error'))
          =(next.first next.stale)  =(next.first next.crossed)
      ==
++  test-run-views-shared-cursor-capacity-and-expiry-cleanup
  =/  runs  many
  =/  first  (read prepared runs book *state:stead-views alice (query 'runs' '' '') 4.100)
  =/  token  (result-field response.first 'cursor')
  =/  sample  (~(got by cursors.next.first) token)
  ::  Explicit bounded count fixtures; these rows do not fabricate sessions.
  =/  four
    %-  malt
    %+  turn  ~[1 2 3 4]
    |=  n=@ud
    [(hex 64 n) sample(purpose 'query')]
  =/  per-person=state:stead-views  [0 four]
  =/  refused  (read prepared runs book per-person alice (query 'runs' '' '') 4.101)
  =/  all=(map @t cursor-record:stead-views)
    =/  count=@ud  0
    =/  rows=(map @t cursor-record:stead-views)  ~
    |-
    ?:  =(count 64)  rows
    =/  actor  alice(identity identity.alice(principal (id (add 200 count))))
    $(count +(count), rows (~(put by rows) (hex 64 +(count)) sample(actor actor, purpose 'query')))
  =/  global=state:stead-views  [0 all]
  =/  full  (read prepared runs book global alice (query 'runs' '' '') 4.101)
  =/  expired=state:stead-views  [0 (malt (turn ~(tap by all) |=([key=@t row=cursor-record:stead-views] [key row(expires 4.101)])))]
  =/  pruned  (read prepared runs book expired alice (query 'runs' '' '') 4.101)
  %-  expect
  !>  ?&  =('capacity_exceeded' (result-field response.refused 'error'))
          =('capacity_exceeded' (result-field response.full 'error'))
          =(per-person next.refused)  =(global next.full)
          =('read' (result-field response.pruned 'status'))
          =(1 (lent ~(tap by cursors.next.pruned)))
      ==
--

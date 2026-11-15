::  Reserved source-only read fixtures; synthetic pagination rows are not history proof.
/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract, stead-product-work, stead-product-codec, stead-principals, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-doc-change-proof, stead-doc-change-query, stead-doc-change-views
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
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
++  put
  |=  [value=json key=@t next=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key next)]
++  head
  |=  state=state:stead-doc-change
  ^-  head:stead-doc-change-state
  (~(got by heads.changes.state) [(id 100) (id 600)])
++  doc-wire
  |=  [req=@ud expected=@ud operation=@t payload=json]
  ^-  command:stead-doc-change-codec
  =/  value
    (object ~[['protocol' 'stead.doc-change/1'] ['request_id' (id req)] ['project_id' (id 100)] ['work_id' (id 105)] ['change_id' (id 600)] ['authority_epoch' '1'] ['expected_revision' (decimal expected)] ['operation' operation]])
  (decode:stead-doc-change-codec (canonical (put value 'payload' payload)))
++  submit-wire
  |=  [state=state:stead-doc-change req=@ud expected=@ud markdown=@t target=json run=@t attempt=@ud]
  ^-  command:stead-doc-change-codec
  =/  pin  (meta product.state 105)
  =/  payload
    (object ~[['outcome_id' (id 500)] ['markdown' markdown] ['summary' 'Update the shared guide'] ['execution_contract_revision' (decimal execution-revision.pin)] ['execution_contract_digest' execution-digest.pin] ['run_id' run] ['attempt' (decimal attempt)]])
  (doc-wire req expected 'change.submit' (put payload 'target' target))
++  action
  |=  [state=state:stead-doc-change req=@ud operation=@t]
  ^-  command:stead-doc-change-codec
  =/  current  (head state)
  (doc-wire req revision.current operation (object ~[['result_revision' (decimal output-revision.current)] ['result_digest' output-digest.current] ['note' 'Reviewed the exact retained version.']]))
++  commit-prepared
  |=  result=result:stead-doc-change
  ^-  result:stead-doc-change
  ?~  record.result  result
  result(next next.result(product (append-event:stead-product-state product.next.result %doc-change u.record.result)))
++  dispatch
  |=  [state=state:stead-doc-change catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud]
  ^-  result:stead-doc-change
  (commit-prepared (apply:stead-doc-change state catalog actor cmd now deny-run:stead-doc-change no-other:stead-doc-change))
++  wanted
  |=  [state=state:stead-doc-change actor=authentication:stead-team now=@ud]
  ^-  proof-request:stead-product-work
  =/  metadata  (meta product.state 105)
  =/  work  (~(got by works.data.db.state) [(id 100) (id 105)])
  [(id 100) (id 105) 1 execution-revision.metadata execution-digest.metadata (object-field:stead-product-codec data.work 'required_outcomes') principal.identity.actor now]
++  doc-body
  |=  state=state:stead-doc-change
  ^-  @t
  =/  doc  (~(got by documents.data.db.state) [(id 100) (scope-key:stead-core (id 200) (id 201))])
  data.body:(~(got by objects.data.db.state) blob.doc)
++  read-query
  |=  [req=@ud kind=@t change=@t revision=@ud digest=@t side=@t cursor=@t]
  ^-  query:stead-doc-change-query
  [(id req) kind (id 100) (id 105) change revision digest side cursor]
++  read-change
  |=  [state=state:stead-doc-change catalog=state:stead-principals pages=state:stead-views actor=authentication:stead-team query=query:stead-doc-change-query now=@ud]
  ^-  result:stead-doc-change-views
  (execute:stead-doc-change-views state catalog pages actor query now 777 deny-run:stead-doc-change)
++  first-row
  |=  raw=@t
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  rows  (~(got by p.value) 'rows')
  ?>  ?=([%o *] rows)
  =/  row  (~(got by p.rows) '0')
  ?>  ?=([%o *] row)
  p.row
++  count-rows
  |=  raw=@t
  ^-  @ud
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  rows  (~(got by p.value) 'rows')
  ?>  ?=([%o *] rows)
  (lent ~(tap by p.rows))
++  refused-query
  |=  raw=@t
  ^-  ?
  ?=(%| -:(mule |.((decode:stead-doc-change-query raw))))
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
=/  agent  (declare:stead-principals next.person ~zod ~zod (id 103) 1 %person 'Bob' & 1.011)
=/  declared-reader  (declare:stead-principals next.agent ~zod ~zod (id 104) 1 %person 'Carol' & 1.012)
=/  catalog  next.declared-reader
=/  markdown  (cat 3 (header:stead-team (id 201) 'published') 'Exact first draft λ.  ')
=/  second-markdown  (cat 3 markdown (cat 3 10 'Clarified final step.'))
=/  contract-work  (apply-command:stead-product-work db.initial-product product.initial-product alice (create-four 460 105 outcomes) 1.020 (current:stead-product-adapters db.initial-product catalog alice))
=/  initial-change=state:stead-doc-change  [db.contract-work product.contract-work empty:stead-doc-change-state]
=/  submit  (submit-wire initial-change 601 0 markdown doc-target '' 0)
=/  submitted  (dispatch initial-change catalog alice submit 2.000)
|%
++  test-doc-change-query-closed-scope-and-exact-body-pins
  =/  query  (read-query 701 'changes' '' 0 '' '' '')
  =/  bytes  (bytes:stead-doc-change-query query)
  =/  value  (need (parse-result bytes))
  =/  output  (~(got by results.changes.next.submitted) [(id 100) (id 600) 1])
  =/  body  (read-query 702 'body' (id 600) 1 digest.output 'after' '')
  %-  expect
  !>  ?&  =(query (decode:stead-doc-change-query bytes))
          =(body (decode:stead-doc-change-query (bytes:stead-doc-change-query body)))
          (refused-query (canonical (put value 'actor' [%s (id 102)])))
          (refused-query (bytes:stead-doc-change-query query(change (id 600))))
          (refused-query (bytes:stead-doc-change-query body(revision 0)))
          (refused-query (bytes:stead-doc-change-query body(digest '')))
          (refused-query (bytes:stead-doc-change-query body(side 'latest')))
          (refused-query (bytes:stead-doc-change-query body(cursor (hex 64 1))))
          (refused-query (cat 3 '{"protocol":"stead.doc-change-query/1",' (cut 3 [1 (dec (met 3 bytes))] bytes)))
      ==
++  test-doc-change-reader-sees-exact-scoped-metadata-and-one-body
  =/  detail  (read-query 703 'change' (id 600) 0 '' '' '')
  =/  found  (read-change next.submitted catalog *state:stead-views carol detail 2.001)
  =/  row  (first-row response.found)
  =/  body  (read-query 704 'body' (id 600) 1 (field row 'result_digest') 'after' '')
  =/  content  (read-change next.submitted catalog next.found carol body 2.002)
  =/  data  (first-row response.content)
  =/  before  (read-change next.submitted catalog next.content carol body(side 'before') 2.003)
  =/  actions  (need (parse-result (field row 'actions')))
  ?>  ?=([%o *] actions)
  =/  approve  (~(got by p.actions) 'change.approve')
  ?>  ?=([%o *] approve)
  %-  expect
  !>  ?&  =('read' (result-field response.found 'status'))
          =(1 (count-rows response.found))  =(1 (count-rows response.content))
          =(31 (lent ~(tap by row)))
          =('Alice' (field row 'producer_display_name'))
          =('ready' (field data 'body_status'))  =(markdown (field data 'markdown'))
          =('new-document' (field (first-row response.before) 'body_status'))
          =('' (field (first-row response.before) 'markdown'))
          =('blocked' (field p.approve 'status'))  =('read_only' (field p.approve 'reason'))
          !(~(has by row) 'producer_authentication')  !(~(has by row) 'producer_grant')
          !(~(has by row) 'markdown')
      ==
++  test-doc-change-current-catalog-access-and-target-visibility-fence-reads
  =/  query  (read-query 705 'change' (id 600) 0 '' '' '')
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 104) 2 %person 'Carol' | 2.001)
  =/  no-catalog  (read-change next.submitted next.disabled *state:stead-views carol query 2.002)
  =/  expired  (read-change next.submitted catalog *state:stead-views carol query 5.001)
  =/  outsider  (read-change next.submitted catalog *state:stead-views carol(identity identity.carol(ship ~zod)) query 2.002)
  =/  box  (~(got by boxes.db.next.submitted) (id 200))
  =/  private  next.submitted(db db.next.submitted(boxes (~(put by boxes.db.next.submitted) (id 200) box(visibility 'private', owner (id 102)))))
  =/  hidden  (read-change private catalog *state:stead-views carol query 2.002)
  =/  listing  (read-change private catalog *state:stead-views carol (read-query 706 'changes' '' 0 '' '' '') 2.003)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.no-catalog 'error'))
          =('denied_or_not_found' (result-field response.expired 'error'))
          =('denied_or_not_found' (result-field response.outsider 'error'))
          =('denied_or_not_found' (result-field response.hidden 'error'))
          =(0 (count-rows response.listing))
      ==
++  test-doc-change-requested-revision-feedback-never-moves-to-new-output
  =/  requested  (dispatch next.submitted catalog bob (action next.submitted 707 'change.request-changes') 2.001)
  =/  read  (read-change next.requested catalog *state:stead-views alice (read-query 708 'change' (id 600) 0 '' '' '') 2.002)
  =/  row  (first-row response.read)
  =/  feedback  (need (parse-result (field row 'latest_decision')))
  ?>  ?=([%o *] feedback)
  =/  revised  (dispatch next.requested catalog alice (submit-wire next.requested 709 2 second-markdown doc-target '' 0) 2.003)
  =/  current  (read-change next.revised catalog *state:stead-views alice (read-query 710 'change' (id 600) 0 '' '' '') 2.004)
  =/  prior  (read-change next.revised catalog *state:stead-views alice (read-query 711 'change' (id 600) 1 (field row 'result_digest') '' '') 2.004)
  =/  old-row  (first-row response.prior)
  =/  wrong  (read-change next.revised catalog *state:stead-views alice (read-query 712 'change' (id 600) 1 (hex 64 0) '' '') 2.004)
  %-  expect
  !>  ?&  =('change.request-changes' (field p.feedback 'operation'))
          =('Reviewed the exact retained version.' (field p.feedback 'note'))
          =('Bob' (field p.feedback 'display_name'))
          =('' (field (first-row response.current) 'latest_decision'))
          =('no' (field old-row 'is_current_result'))
          =((field row 'latest_decision') (field old-row 'latest_decision'))
          =('' (field old-row 'approval'))  =('' (field old-row 'adoption'))
          =('denied_or_not_found' (result-field response.wrong 'error'))
      ==
++  test-doc-change-review-advice-preserves-independent-review-and-accountability
  =/  head  (head next.submitted)
  =/  output  (~(got by results.changes.next.submitted) [(id 100) (id 600) 1])
  =/  approved  (dispatch next.submitted catalog bob (action next.submitted 713 'change.approve') 2.001)
  =/  new-head  (head next.approved)
  %-  expect
  !>  ?&  =('self_review_denied' (action-reason:stead-doc-change-views next.submitted catalog alice head output 'change.approve' 2.002 deny-run:stead-doc-change))
          =('' (action-reason:stead-doc-change-views next.submitted catalog bob head output 'change.approve' 2.002 deny-run:stead-doc-change))
          =('independent_review_required' (action-reason:stead-doc-change-views next.submitted catalog alice head output 'change.accept' 2.002 deny-run:stead-doc-change))
          =('' (action-reason:stead-doc-change-views next.approved catalog alice new-head output 'change.accept' 2.002 deny-run:stead-doc-change))
          =('accountable_human_required' (action-reason:stead-doc-change-views next.approved catalog bob new-head output 'change.accept' 2.002 deny-run:stead-doc-change))
          =('' (action-reason:stead-doc-change-views next.submitted catalog alice head output 'change.quarantine' 2.002 deny-run:stead-doc-change))
      ==
++  test-doc-change-before-uses-exact-authorized-doc-history-not-current-text
  =/  saved  (apply-legacy:stead-product-work db.initial-change product.initial-change alice (command 714 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]]) 2.001)
  =/  before  initial-change(db db.saved, product product.saved)
  =/  sha  (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])
  =/  target  (put (put doc-target 'expected_revision' [%s '1']) 'base_markdown_sha256' [%s sha])
  =/  outputs  [%o (malt ~[[(id 500) target]])]
  =/  work  (apply-command:stead-product-work db.before product.before alice (command-four 715 105 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Revise existing Doc' outputs)) 2.002 (current:stead-product-adapters db.before catalog alice))
  =/  ready  before(db db.work, product product.work)
  =/  proposed  (dispatch ready catalog alice (submit-wire ready 716 0 second-markdown target '' 0) 2.003)
  =/  moved  (apply-legacy:stead-product-work db.next.proposed product.next.proposed alice (command 717 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' (cat 3 markdown 'Later unrelated edit.')]]) 2.004)
  =/  state  next.proposed(db db.moved, product product.moved)
  =/  output  (~(got by results.changes.state) [(id 100) (id 600) 1])
  =/  query  (read-query 718 'body' (id 600) 1 digest.output 'before' '')
  =/  found  (read-change state catalog *state:stead-views carol query 2.005)
  =/  absent  state(db db.state(data data.db.state(journal ~)))
  =/  missing  (target-body:stead-doc-change-views absent output)
  %-  expect
  !>  ?&  =('ready' (field (first-row response.found) 'body_status'))
          =(markdown (field (first-row response.found) 'markdown'))
          =(sha (field (first-row response.found) 'markdown_sha256'))
          !=(markdown (doc-body state))
          =('unavailable' status.missing)  =('' markdown.missing)  =(sha digest.missing)
      ==
++  test-doc-change-pagination-is-bounded-and-current-actor-bound
  ::  Explicit synthetic map fixture exercises cursor boundaries only.
  =/  original  (~(got by results.changes.next.submitted) [(id 100) (id 600) 1])
  =/  initial-head  (head next.submitted)
  =/  many
    =/  state  next.submitted
    =/  index=@ud  1
    |-
    ?:  =(21 index)  state
    =/  change-id  (id (add 600 index))
    =/  output  original(change change-id)
    =.  digest.output  (output-digest:stead-doc-change-state output)
    =/  changes  changes.state
    =.  changes  changes(heads (~(put by heads.changes) [(id 100) change-id] initial-head(output-digest digest.output)), results (~(put by results.changes) [(id 100) change-id 1] output))
    $(index +(index), state state(changes changes))
  =/  query  (read-query 719 'changes' '' 0 '' '' '')
  =/  first  (read-change many catalog *state:stead-views alice query 2.005)
  =/  token  (result-field response.first 'cursor')
  =/  last  (read-change many catalog next.first alice query(request (id 720), cursor token) 2.006)
  =/  other  (read-change many catalog next.first bob query(cursor token) 2.006)
  =/  expired  (read-change many catalog next.first alice query(cursor token) 302.006)
  =/  changed-head  initial-head(revision 2)
  =/  changed  many(changes changes.many(heads (~(put by heads.changes.many) [(id 100) (id 600)] changed-head)))
  =/  stale  (read-change changed catalog next.first alice query(cursor token) 2.006)
  %-  expect
  !>  ?&  =(20 (count-rows response.first))  !=('' token)
          =(1 (count-rows response.last))  =('' (result-field response.last 'cursor'))
          =('stale_cursor' (result-field response.other 'error'))
          =('stale_cursor' (result-field response.expired 'error'))
          =('stale_cursor' (result-field response.stale 'error'))
      ==
--

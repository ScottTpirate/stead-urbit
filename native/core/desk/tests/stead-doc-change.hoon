/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract, stead-product-work, stead-product-codec, stead-principals, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-doc-change-proof
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
++  test-doc-change-human-revision-review-and-atomic-exact-acceptance
  =/  first  (head next.submitted)
  =/  approved-first  (dispatch next.submitted catalog bob (action next.submitted 602 'change.approve') 2.001)
  =/  reviewed-event  (need record.approved-first)
  =/  requested  (dispatch next.approved-first catalog bob (action next.approved-first 603 'change.request-changes') 2.002)
  =/  revised  (dispatch next.requested catalog alice (submit-wire next.requested 604 3 second-markdown doc-target '' 0) 2.003)
  =/  revised-head  (head next.revised)
  =/  approved  (dispatch next.revised catalog bob (action next.revised 605 'change.approve') 2.004)
  =/  accept  (action next.approved 606 'change.accept')
  =/  accepted  (dispatch next.approved catalog alice accept 2.005)
  =/  current  (head next.accepted)
  =/  events  events.product.next.accepted
  ?>  ?=(^ events)
  ?>  ?=(^ t.events)
  =/  recorded  (need (parse-result (need record.accepted)))
  ?>  ?=([%o *] recorded)
  =/  retry  (dispatch next.accepted catalog alice accept 2.006)
  =/  quarantine  (dispatch next.accepted catalog alice (action next.accepted 607 'change.quarantine') 2.006)
  %-  expect
  !>  ?&  =('accepted' (result-field response.submitted 'status'))
          =(1 output-revision.first)  =(2 output-revision.revised-head)
          ?=(~ approval.revised-head)  ?=(~ adoption.revised-head)
          =((~(got by results.changes.next.submitted) [(id 100) (id 600) 1]) (~(got by results.changes.next.accepted) [(id 100) (id 600) 1]))
          (levy events |=([family=family:stead-product-state bytes=@t digest=@t] =((hash 'stead.product-event/1' bytes) digest)))
          ::  Prior review remains an exact immutable timeline member.
          (lien events |=([family=family:stead-product-state bytes=@t digest=@t] =(reviewed-event (result-field bytes 'body'))))
          =(%accepted status.current)  =(6 revision.current)
          =(second-markdown (doc-body next.accepted))
          =(2 (lent ~(tap by bodies.changes.next.accepted)))
          =(%doc-change family.i.events)  =(%v3 family.i.t.events)
          =(bytes.i.t.events (field p.recorded 'save_event'))
          =(digest.i.t.events (field p.recorded 'save_event_digest'))
          =(response.accepted response.retry)  =(next.accepted next.retry)  ?=(~ record.retry)
          =('change_closed' (result-field response.quarantine 'error'))
          =(%accepted status:(head next.quarantine))
          =(db.next.accepted db.next.quarantine)
      ==
++  test-doc-change-independent-people-current-access-and-request-identity
  =/  self  (dispatch next.submitted catalog alice (action next.submitted 610 'change.approve') 2.001)
  =/  stranger  (dispatch next.submitted catalog carol (action next.submitted 611 'change.approve') 2.001)
  =/  replace  (dispatch next.submitted catalog bob (submit-wire next.submitted 612 1 second-markdown doc-target '' 0) 2.001)
  =/  changed-submit  (submit-wire initial-change 601 0 second-markdown doc-target '' 0)
  =/  reused  (dispatch next.submitted catalog alice changed-submit 2.001)
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 102) 2 %person 'Alice' | 2.001)
  =/  stale-retry  (dispatch next.submitted next.disabled alice submit 2.002)
  %-  expect
  !>  ?&  =('self_review_denied' (result-field response.self 'error'))
          =('denied_or_not_found' (result-field response.stranger 'error'))
          =('producer_mismatch' (result-field response.replace 'error'))
          =('request_id_reuse' (result-field response.reused 'error'))
          =(next.submitted next.reused)
          =('denied_or_not_found' (result-field response.stale-retry 'error'))
          =(next.submitted next.stale-retry)  ?=(~ record.stale-retry)
          =(heads.changes.next.submitted heads.changes.next.self)
          =(2 (lent ~(tap by attempts.changes.next.self)))
      ==
++  test-doc-change-stale-lifecycle-output-contract-and-late-replies
  =/  approve  (action next.submitted 620 'change.approve')
  =/  approved  (dispatch next.submitted catalog bob approve 2.001)
  =/  stale  (dispatch next.approved catalog bob (action next.submitted 621 'change.request-changes') 2.002)
  =/  retry  (dispatch next.stale catalog bob (action next.submitted 621 'change.request-changes') 2.003)
  =/  bad-output
    (doc-wire 622 2 'change.accept' (object ~[['result_revision' '1'] ['result_digest' (hex 64 0)] ['note' '']]))
  =/  wrong  (dispatch next.approved catalog alice bad-output 2.002)
  =/  changed  (apply-command:stead-product-work db.next.approved product.next.approved alice (command-four 623 105 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Changed acceptance goal' outcomes)) 2.002 (current:stead-product-adapters db.next.approved catalog alice))
  =/  advanced  next.approved(db db.changed, product product.changed)
  =/  conflict  (dispatch advanced catalog alice (action advanced 624 'change.accept') 2.003)
  %-  expect
  !>  ?&  =('revision_conflict' (result-field response.stale 'error'))
          =(response.stale response.retry)  =(next.stale next.retry)
          =('result_conflict' (result-field response.wrong 'error'))
          =('execution_contract_conflict' (result-field response.conflict 'error'))
          =(db.advanced db.next.conflict)
          =(heads.changes.advanced heads.changes.next.conflict)
          ?=(~ (~(get by documents.data.db.next.conflict) [(id 100) (scope-key:stead-core (id 200) (id 201))]))
      ==
++  test-doc-change-exact-base-private-target-and-comment-noninterference
  =/  private-target  (put doc-target 'collection_id' [%s (id 202)])
  =/  private  (dispatch initial-change catalog alice (submit-wire initial-change 630 0 markdown private-target '' 0) 2.000)
  =/  comment  (apply-command:stead-product-work db.next.submitted product.next.submitted bob (command-four 631 105 'work.comment' ~[['discussion_sequence' '0']] (object ~[['body' 'Please preserve the exact Markdown.']])) 2.001 (current:stead-product-adapters db.next.submitted catalog bob))
  =/  with-comment  next.submitted(db db.comment, product product.comment)
  =/  approved  (dispatch with-comment catalog bob (action with-comment 632 'change.approve') 2.002)
  =/  saved  (apply-legacy:stead-product-work db.next.approved product.next.approved alice (command 633 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' second-markdown]]) 2.003)
  =/  moved  next.approved(db db.saved, product product.saved)
  =/  conflict  (dispatch moved catalog alice (action moved 634 'change.accept') 2.004)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.private 'error'))
          =(initial-change next.private)  ?=(~ record.private)
          =('accepted' (result-field response.approved 'status'))
          =('target_base_conflict' (result-field response.conflict 'error'))
          =(second-markdown (doc-body next.conflict))
          =(db.moved db.next.conflict)
          =(execution-digest:(meta product.next.submitted 105) execution-digest:(meta product.next.approved 105))
          =(1 discussion-sequence:(meta product.next.approved 105))
      ==
++  test-doc-change-expired-output-explicit-adoption-and-no-late-worker-effects
  =/  short  bob(method 'native-approved-browser/1', strength 'native-approved-browser', audit (hex 64 1), expires 2.001)
  =/  proposed  (dispatch initial-change catalog short (submit-wire initial-change 640 0 markdown doc-target '' 0) 2.000)
  =/  approved  (dispatch next.proposed catalog alice (action next.proposed 641 'change.approve') 2.002)
  =/  denied  (dispatch next.approved catalog alice (action next.approved 642 'change.accept') 2.003)
  =/  adopted  (dispatch next.denied catalog alice (action next.denied 643 'change.adopt') 2.004)
  =/  accepted  (dispatch next.adopted catalog alice (action next.adopted 644 'change.accept') 2.005)
  =/  late  (dispatch next.adopted catalog short (submit-wire next.adopted 645 3 second-markdown doc-target '' 0) 2.005)
  =/  original  (~(got by results.changes.next.proposed) [(id 100) (id 600) 1])
  =/  accepted-head=head:stead-doc-change-state  (head next.accepted)
  %-  expect
  !>  ?&  =('accepted' (result-field response.proposed 'status'))
          =('explicit_adoption_required' (result-field response.denied 'error'))
          =('accepted' (result-field response.adopted 'status'))
          =('accepted' (result-field response.accepted 'status'))
          =(original (~(got by results.changes.next.accepted) [(id 100) (id 600) 1]))
          =(short producer.original)  =(markdown (doc-body next.accepted))
          =('denied_or_not_found' (result-field response.late 'error'))
          =(next.adopted next.late)  ?=(~ record.late)
          ?=(^ adoption.accepted-head)
      ==
++  test-doc-change-revocation-quarantines-without-renewing-original-grant
  =/  proposed  (dispatch initial-change catalog bob (submit-wire initial-change 650 0 markdown doc-target '' 0) 2.000)
  =/  revoke  (apply-legacy:stead-product-work db.next.proposed product.next.proposed alice (command 651 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 2.001)
  =/  revoked  next.proposed(db db.revoke, product product.revoke)
  =/  quarantine  (dispatch revoked catalog alice (action revoked 652 'change.approve') 2.002)
  =/  renewed  (apply-legacy:stead-product-work db.next.quarantine product.next.quarantine alice (command 653 100 4 'policy.grant' ~[['grant_id' (id 503)] ['principal_id' (id 103)] ['role' 'contributor'] ['expires_at_ms' '9000000']]) 2.003)
  =/  with-renewal  next.quarantine(db db.renewed, product product.renewed)
  =/  adoption  (dispatch with-renewal catalog alice (action with-renewal 654 'change.adopt') 2.004)
  =/  output  (~(got by results.changes.next.proposed) [(id 100) (id 600) 1])
  %-  expect
  !>  ?&  =('producer_quarantined' (result-field response.quarantine 'error'))
          =(%quarantined status:(head next.quarantine))
          =('change_closed' (result-field response.adoption 'error'))
          =(%revoked (producer-authority:stead-doc-change with-renewal catalog output 2.004 deny-run:stead-doc-change))
          =(output (~(got by results.changes.next.adoption) [(id 100) (id 600) 1]))
          ?=(~ (~(get by documents.data.db.next.adoption) [(id 100) (scope-key:stead-core (id 200) (id 201))]))
      ==
++  test-doc-change-current-reviewer-and-accountable-acceptor
  =/  approved  (dispatch next.submitted catalog bob (action next.submitted 660 'change.approve') 2.001)
  =/  contributor  (dispatch next.approved catalog bob (action next.approved 661 'change.accept') 2.002)
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 103) 2 %person 'Bob' | 2.002)
  =/  old-review  (dispatch next.approved next.disabled alice (action next.approved 662 'change.accept') 2.003)
  =/  live-adopt  (dispatch next.approved catalog bob (action next.approved 663 'change.adopt') 2.003)
  %-  expect
  !>  ?&  =('accountable_human_required' (result-field response.contributor 'error'))
          =('independent_review_required' (result-field response.old-review 'error'))
          =('adoption_requires_expiry' (result-field response.live-adopt 'error'))
          =(db.next.approved db.next.old-review)
          =(heads.changes.next.approved heads.changes.next.old-review)
      ==
++  test-doc-change-internal-save-request-fixed-vector-and-global-collision
  =/  vector  (doc-wire 650 9 'change.accept' (object ~[['result_revision' '7'] ['result_digest' 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'] ['note' '']]))
  =/  approved  (dispatch next.submitted catalog bob (action next.submitted 670 'change.approve') 2.001)
  =/  cmd  (action next.approved 671 'change.accept')
  =/  reserved  (internal-request:stead-doc-change-state cmd)
  =/  owner-used=$-(request-key:stead-doc-change ?)
    |=(key=request-key:stead-doc-change =(reserved request.key))
  =/  conflict  (commit-prepared (apply:stead-doc-change next.approved catalog alice cmd 2.002 deny-run:stead-doc-change [1 owner-used]))
  %-  expect
  !>  ?&  =('019939ba-4000-7772-87ff-9f719f96d393' (internal-request:stead-doc-change-state vector))
          =((cut 3 [0 14] request.cmd) (cut 3 [0 14] reserved))
          !=(request.cmd reserved)  (uuid reserved)
          =('internal_request_id_collision' (result-field response.conflict 'error'))
          =(db.next.approved db.next.conflict)
          =(heads.changes.next.approved heads.changes.next.conflict)
      ==
++  test-doc-change-paired-budget-and-final-object-limit-rollback
  =/  approved  (dispatch next.submitted catalog bob (action next.submitted 680 'change.approve') 2.001)
  =/  cmd  (action next.approved 681 'change.accept')
  =/  count  (ordinary-count:stead-doc-change next.approved (id 100) no-other:stead-doc-change)
  ::  Explicit capacity-boundary fixtures; these are not claimed valid replay
  ::  histories. The exact production guard must reject before committing Doc.
  =/  final-slot  [(sub 4.095 count) request-unused:stead-doc-change]
  =/  full  (commit-prepared (apply:stead-doc-change next.approved catalog alice cmd 2.002 deny-run:stead-doc-change final-slot))
  =/  tight  next.approved(changes changes.next.approved(body-bytes (sub 8.388.608 object-bytes.data.db.next.approved)))
  =/  overflow  (dispatch tight catalog alice (action tight 682 'change.accept') 2.002)
  =/  sha  markdown-sha256:(~(got by results.changes.next.submitted) [(id 100) (id 600) 1])
  =/  changed-body  (cat 3 markdown ' ')
  =/  wrong-key  next.submitted(changes changes.next.submitted(bodies (~(put by bodies.changes.next.submitted) sha changed-body), body-bytes +((met 3 markdown))))
  =/  huge-body  (rap 3 (reap 32.769 'x'))
  =/  oversized  next.submitted(changes changes.next.submitted(bodies (~(put by bodies.changes.next.submitted) sha huge-body), body-bytes 32.769))
  =/  stored  (~(got by attempts.changes.next.submitted) [(id 100) (id 102) (id 601)])
  =/  big-attempt  stored(command (rap 3 (reap 65.537 'x')))
  =/  oversized-attempt  next.submitted(changes changes.next.submitted(attempts (~(put by attempts.changes.next.submitted) [(id 100) (id 102) (id 601)] big-attempt)))
  %-  expect
  !>  ?&  =('capacity_exceeded' (result-field response.full 'error'))
          =(db.next.approved db.next.full)
          =(heads.changes.next.approved heads.changes.next.full)
          =('capacity_exceeded' (result-field response.overflow 'error'))
          =(db.tight db.next.overflow)
          =(heads.changes.tight heads.changes.next.overflow)
          =(+((lent events.product.tight)) (lent events.product.next.overflow))
          (changes-bounded:stead-doc-change next.submitted)
          !(changes-bounded:stead-doc-change tight)
          !(changes-bounded:stead-doc-change wrong-key)
          !(changes-bounded:stead-doc-change oversized)
          !(changes-bounded:stead-doc-change oversized-attempt)
      ==
++  test-doc-change-run-authority-default-deny-and-immutable-attempt-provenance
  =/  agent  (declare:stead-principals next.person ~zod ~zod (id 103) 1 %agent 'Bob worker' & 1.011)
  =/  catalog  next.agent
  =/  no-run  (dispatch initial-change catalog bob (submit-wire initial-change 690 0 markdown doc-target '' 0) 2.000)
  =/  wire  (submit-wire initial-change 691 0 markdown doc-target (id 700) 1)
  =/  denied  (dispatch initial-change catalog bob wire 2.000)
  ::  This fixture models an explicitly trusted exact historical/current run
  ::  gate. It is not evidence that a native Home run adapter exists.
  =/  live=run-resolver:stead-doc-change
    |=  [output=output:stead-doc-change-state now=@ud]
    ^-  authority:stead-doc-change
    ?:  ?&  =((id 100) project.output)  =((id 105) work.output)
            =((id 103) principal.identity.producer.output)
            =((id 700) run.output)  =(1 attempt.output)
            =(1 execution.output)  (lth now 3.000)
        ==
      %live
    %unknown
  =/  proposed  (commit-prepared (apply:stead-doc-change initial-change catalog bob wire 2.000 live no-other:stead-doc-change))
  =/  unknown  (dispatch next.proposed catalog alice (action next.proposed 692 'change.approve') 2.001)
  =/  output  (~(got by results.changes.next.proposed) [(id 100) (id 600) 1])
  %-  expect
  !>  ?&  =('producer_unavailable' (result-field response.no-run 'error'))
          =('producer_unavailable' (result-field response.denied 'error'))
          =('accepted' (result-field response.proposed 'status'))
          =((id 700) run.output)  =(1 attempt.output)
          =('producer_quarantined' (result-field response.unknown 'error'))
          =(%quarantined status:(head next.unknown))
          =(output (~(got by results.changes.next.unknown) [(id 100) (id 600) 1]))
      ==
++  test-doc-change-existing-doc-exact-hash-revision-and-canonical-markdown
  =/  saved  (apply-legacy:stead-product-work db.initial-change product.initial-change alice (command 710 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]]) 2.000)
  =/  sha  (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])
  =/  target  (put (put doc-target 'expected_revision' [%s '1']) 'base_markdown_sha256' [%s sha])
  =/  required  [%o (malt ~[[(id 500) target]])]
  =/  updated  (apply-command:stead-product-work db.saved product.saved alice (command-four 711 105 'work.update-contract' ~[['execution_contract_revision' '1']] (goal 'Revise the existing guide' required)) 2.001 (current:stead-product-adapters db.saved catalog alice))
  =/  state  initial-change(db db.updated, product product.updated)
  =/  malformed  (dispatch state catalog alice (submit-wire state 712 0 'Missing canonical frontmatter' target '' 0) 2.002)
  =/  bad-target  (put target 'base_markdown_sha256' [%s (hex 64 0)])
  =/  wrong  (dispatch state catalog alice (submit-wire state 713 0 second-markdown bad-target '' 0) 2.002)
  =/  proposed  (dispatch state catalog alice (submit-wire state 714 0 second-markdown target '' 0) 2.002)
  =/  approved  (dispatch next.proposed catalog bob (action next.proposed 715 'change.approve') 2.003)
  =/  accepted  (dispatch next.approved catalog alice (action next.approved 716 'change.accept') 2.004)
  =/  doc  (~(got by documents.data.db.next.accepted) [(id 100) (scope-key:stead-core (id 200) (id 201))])
  %-  expect
  !>  ?&  =('invalid_document' (result-field response.malformed 'error'))
          =('execution_contract_conflict' (result-field response.wrong 'error'))
          =('accepted' (result-field response.accepted 'status'))
          =(2 revision.doc)  =(second-markdown (doc-body next.accepted))
          =(2 execution:(~(got by results.changes.next.accepted) [(id 100) (id 600) 1]))
      ==
++  test-doc-change-accepted-proof-completes-real-work-with-required-outcome
  =/  approved  (dispatch next.submitted catalog bob (action next.submitted 720 'change.approve') 2.001)
  =/  accepted  (dispatch next.approved catalog alice (action next.approved 721 'change.accept') 2.002)
  =/  request  (wanted next.accepted alice 2.003)
  =/  proof  (resolve:stead-doc-change-proof next.accepted alice request)
  =/  resolvers  (current:stead-product-adapters db.next.accepted catalog alice)
  =.  accepted.resolvers  (resolver:stead-doc-change-proof next.accepted alice)
  =/  complete  (command-four 722 105 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '1']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  completed  (apply-command:stead-product-work db.next.accepted product.next.accepted alice complete 2.003 resolvers)
  =/  metadata  (meta product.completed 105)
  =/  work  (~(got by works.data.db.completed) [(id 100) (id 105)])
  %-  expect
  !>  ?&  ?=(^ proof)  =('accepted' (result-field response.completed 'status'))
          =('done' (field data.work 'status'))
          =(%outcomes completion-basis.metadata)  ?=(^ completion.metadata)
          (changes-bounded:stead-doc-change next.accepted)
      ==
++  test-doc-change-proof-rejects-uncommitted-forged-or-changed-outcomes
  =/  approved  (dispatch next.submitted catalog bob (action next.submitted 730 'change.approve') 2.001)
  =/  accepted  (dispatch next.approved catalog alice (action next.approved 731 'change.accept') 2.002)
  =/  request  (wanted next.accepted alice 2.003)
  =/  accepted-head  (head next.accepted)
  =/  forged-head  (head next.approved)
  =.  forged-head  forged-head(status %accepted, acceptance acceptance.accepted-head)
  =/  forged  next.approved(changes changes.next.approved(heads (~(put by heads.changes.next.approved) [(id 100) (id 600)] forged-head)))
  ::  Stronger forgery: a real direct save provides the exact current Markdown,
  ::  native receipt and v3 event, but there is no adjacent typed acceptance.
  =/  direct  (apply-legacy:stead-product-work db.next.approved product.next.approved alice (command 733 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]]) 2.002)
  ?>  ?=(^ events.product.direct)
  =/  fake-acceptance=acceptance:stead-doc-change-state
    [alice (id 731) 2.002 1 response.direct digest.i.events.product.direct]
  =.  forged-head  forged-head(acceptance (some fake-acceptance))
  =/  forged-direct  next.approved(db db.direct, product product.direct, changes changes.next.approved(heads (~(put by heads.changes.next.approved) [(id 100) (id 600)] forged-head)))
  =/  changed  (apply-legacy:stead-product-work db.next.accepted product.next.accepted alice (command 732 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' second-markdown]]) 2.003)
  =/  changed-doc  next.accepted(db db.changed, product product.changed)
  =/  other-target  (put doc-target 'document_id' [%s (id 299)])
  =/  wrong-target  request(outcomes (malt ~[[(id 500) other-target]]))
  =/  without-receipts  next.accepted(db db.next.accepted(data data.db.next.accepted(receipts ~)))
  %-  expect
  !>  ?&  ?=(~ (resolve:stead-doc-change-proof next.approved alice request))
          ?=(~ (resolve:stead-doc-change-proof forged alice request))
          ?=(~ (resolve:stead-doc-change-proof forged-direct alice request))
          ?=(~ (resolve:stead-doc-change-proof changed-doc alice request))
          ?=(~ (resolve:stead-doc-change-proof next.accepted alice wrong-target))
          ?=(~ (resolve:stead-doc-change-proof next.accepted alice request(execution 2)))
          ?=(~ (resolve:stead-doc-change-proof without-receipts alice request))
      ==
++  test-doc-change-accepted-proof-survives-review-expiry-with-current-completer
  =/  short  bob(method 'native-approved-browser/1', strength 'native-approved-browser', audit (hex 64 2), expires 2.005)
  =/  approved  (dispatch next.submitted catalog short (action next.submitted 740 'change.approve') 2.001)
  =/  accepted  (dispatch next.approved catalog alice (action next.approved 741 'change.accept') 2.002)
  =/  before  (head next.accepted)
  =/  old-completer  alice(method 'native-approved-browser/1', strength 'native-approved-browser', audit (hex 64 3), expires 2.005)
  %-  expect
  !>  ?&  ?=(^ (resolve:stead-doc-change-proof next.accepted alice (wanted next.accepted alice 2.010)))
          ?=(~ (resolve:stead-doc-change-proof next.accepted short (wanted next.accepted short 2.010)))
          ?=(~ (resolve:stead-doc-change-proof next.accepted carol (wanted next.accepted carol 2.010)))
          ?=(~ (resolve:stead-doc-change-proof next.accepted old-completer (wanted next.accepted old-completer 2.010)))
          =(before (head next.accepted))
          =(%accepted status.before)  =(markdown (doc-body next.accepted))
      ==
--

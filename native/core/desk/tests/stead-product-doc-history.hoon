::  Source-only combined owner/Work/Doc Change timeline tests. No local native execution or Home
::  activation is claimed. Every fixture identity is public and disposable.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-restore, stead-principals, stead-product-state, stead-product-codec, stead-product-migrate, stead-product-work, stead-product-owner-codec, stead-product-owner, stead-product-adapters, stead-product-restore, stead-product-history, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-doc-change-proof
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
++  value
  |=  raw=@t
  ^-  object-map
  =/  parsed  (need (parse-result raw))
  ?>  ?=([%o *] parsed)
  p.parsed
++  result-field
  |=  [raw=@t name=@t]
  ^-  @t
  (field (value raw) name)
++  child
  |=  [data=object-map key=@t]
  ^-  object-map
  =/  item  (~(got by data) key)
  ?>  ?=([%o *] item)
  p.item
++  member-config
  |=  [raw=@t expected=@ud revision=@ud active=@t]
  ^-  @t
  =/  config  (value raw)
  =/  members  (child config 'bindings')
  =/  person  (child members '~nec')
  =.  person  (~(put by person) 'binding_revision' [%s (decimal revision)])
  =.  person  (~(put by person) 'active' [%s active])
  =.  members  (~(put by members) '~nec' [%o person])
  =.  config  (~(put by config) 'bindings' [%o members])
  (canonical [%o (~(put by config) 'expected_revision' [%s (decimal expected)])])
++  owner-command
  |=  [req=@ud operation=@t expected=@ud payload=(list [@t @t])]
  ^-  command:stead-product-owner-codec
  =/  base  (object ~[['protocol' 'stead.owner-command/1'] ['request_id' (id req)] ['operation' operation] ['expected_revision' (decimal expected)]])
  ?>  ?=([%o *] base)
  (decode:stead-product-owner-codec (canonical [%o (~(put by p.base) 'payload' (object payload))]))
++  command-four
  |=  [req=@ud work=@ud operation=@t expected=(list [@t @t]) payload=json]
  ^-  command:stead-product-codec
  =/  base  (object ~[['protocol' 'stead.command/4'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id work)] ['authority_epoch' '1'] ['operation' operation]])
  ?>  ?=([%o *] base)
  =/  fields  (~(put by p.base) 'expected' (object expected))
  (decode:stead-product-codec (canonical [%o (~(put by fields) 'payload' payload)]))
++  props
  ^-  json
  (object ~[['type' 'task'] ['status' 'todo'] ['priority' 'none'] ['owner_principal_id' (id 102)] ['worker_principal_id' (id 103)] ['blocked_reason' '']])
++  goal
  |=  outcomes=json
  ^-  json
  =/  base  (object ~[['title' 'Ship the guide'] ['description' 'Exact source notes'] ['acceptance_criteria' 'Reviewed shared documentation']])
  ?>  ?=([%o *] base)
  [%o (~(put by p.base) 'required_outcomes' outcomes)]
++  make-work
  ^-  command:stead-product-codec
  =/  properties  props
  =/  contract  (goal [%o ~])
  ?>  &(?=([%o *] properties) ?=([%o *] contract))
  (command-four 401 111 'work.create' ~[['work_revision' '0'] ['execution_contract_revision' '0']] [%o (~(uni by p.properties) p.contract)])
++  comment-command
  |=  [req=@ud sequence=@ud]
  ^-  command:stead-product-codec
  (command-four req 111 'work.comment' ~[['discussion_sequence' (decimal sequence)]] (object ~[['body' 'A retained question']]))
++  migrate
  |=  db=state:stead-team
  ^-  migrated:stead-product-migrate
  =/  job  (begin:stead-product-migrate db ~zod)
  =/  budget=@ud  1.024
  |-
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  (need (result:stead-product-migrate job))
  ?>  (gth budget 0)
  $(job (step:stead-product-migrate job), budget (dec budget))
++  finish
  |=  job=job:stead-product-history
  ^-  job:stead-product-history
  =/  budget=@ud  1.024
  |-
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  job
  ?>  (gth budget 0)
  $(job (step:stead-product-history job), budget (dec budget))
++  restored
  |=  target=state:stead-product-history
  ^-  job:stead-product-history
  (finish (begin:stead-product-history target ~zod))
++  rejected
  |=  target=state:stead-product-history
  ^-  ?
  =/  attempted  (mule |.((restored target)))
  ?:  ?=(%| -.attempted)  &
  ?&  =(%invalid phase.p.attempted)
      ?=(~ (restored:stead-product-history p.attempted))
  ==
++  admission-refused
  |=  target=state:stead-product-history
  ^-  ?
  ?=([%| *] (mule |.((begin:stead-product-history target ~zod))))
++  events-phase
  |=  target=state:stead-product-history
  ^-  job:stead-product-history
  =/  job  (begin:stead-product-history target ~zod)
  =/  budget=@ud  1.024
  |-
  ?:  =(%events phase.job)  job
  ?>  &((gth budget 0) !=(%invalid phase.job) !=(%valid phase.job))
  $(job (step:stead-product-history job), budget (dec budget))
++  newest-body
  |=  product=state:stead-product-state
  ^-  @t
  ?>  ?=(^ events.product)
  (field (value bytes.i.events.product) 'body')
++  record-replaced
  |=  [product=state:stead-product-state key=@t replacement=@t]
  ^-  state:stead-product-state
  ?>  ?=(^ events.product)
  =/  event  i.events.product
  =/  body  (canonical [%o (~(put by (value (newest-body product))) key [%s replacement])])
  =/  encoded  (canonical [%o (~(put by (value bytes.event)) 'body' [%s body])])
  product(events [event(bytes encoded, digest (hash 'stead.product-event/1' encoded)) t.events.product])
++  rechain
  |=  [product=state:stead-product-state events=(list event:stead-product-state)]
  ^-  state:stead-product-state
  ?>  (lte (lent events) 64)
  =/  next=state:stead-product-state  product(events ~)
  =/  remaining  (flop events)
  |-
  ?~  remaining  next
  =/  body  (field (value bytes.i.remaining) 'body')
  $(remaining t.remaining, next (append-event:stead-product-state next family.i.remaining body))
++  put
  |=  [value=json key=@t next=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key next)]
++  head
  |=  state=state:stead-product-history
  ^-  head:stead-doc-change-state
  (~(got by heads.changes.state) [(id 100) (id 601)])
++  doc-wire
  |=  [req=@ud expected=@ud operation=@t payload=json]
  ^-  command:stead-doc-change-codec
  =/  base
    (object ~[['protocol' 'stead.doc-change/1'] ['request_id' (id req)] ['project_id' (id 100)] ['work_id' (id 111)] ['change_id' (id 601)] ['authority_epoch' '1'] ['expected_revision' (decimal expected)] ['operation' operation]])
  (decode:stead-doc-change-codec (canonical (put base 'payload' payload)))
++  submission
  |=  [state=state:stead-product-history req=@ud expected=@ud target=json markdown=@t]
  ^-  command:stead-doc-change-codec
  =/  metadata  (~(got by works.product.state) [(id 100) (id 111)])
  =/  payload
    (object ~[['outcome_id' (id 500)] ['markdown' markdown] ['summary' 'Revise the canonical guide'] ['execution_contract_revision' (decimal execution-revision.metadata)] ['execution_contract_digest' execution-digest.metadata] ['run_id' ''] ['attempt' '0']])
  (doc-wire req expected 'change.submit' (put payload 'target' target))
++  action
  |=  [state=state:stead-product-history req=@ud operation=@t]
  ^-  command:stead-doc-change-codec
  =/  head  (head state)
  (doc-wire req revision.head operation (object ~[['result_revision' (decimal output-revision.head)] ['result_digest' output-digest.head] ['note' 'Exact version checked.']]))
++  doc-body
  |=  state=state:stead-product-history
  ^-  @t
  =/  doc  (~(got by documents.data.db.state) [(id 100) (scope-key:stead-core (id 200) (id 201))])
  data.body:(~(got by objects.data.db.state) blob.doc)
++  budget-filled
  |=  state=state:stead-product-history
  ^-  state:stead-product-history
  ::  Explicit synthetic count fixture, not valid replay history.
  =/  count
    (add (event-count:stead-team db.state '' |) (add (lent ~(tap by attempts.product.state)) (add (owner-count:stead-product-owner ledger.state |) (lent ~(tap by attempts.changes.state)))))
  =/  sample  (~(got by attempts.product.state) [(id 100) (id 103) (id 402)])
  =/  left  (sub 4.095 count)
  =/  index=@ud  0
  =/  attempts  attempts.product.state
  |-
  ?:  =(left 0)  state(product product.state(attempts attempts))
  =/  key  [(id (add 200 (div index 64))) (id 102) (id (add 300 (mod index 64)))]
  ?>  !(~(has by attempts) key)
  $(left (dec left), index +(index), attempts (~(put by attempts) key sample))
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
=/  work-fields  ~[['title' 'Legacy draft'] ['description' 'Old notes'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
=/  create  (apply-command:stead-team next.reader alice (command 304 101 0 'work.create' work-fields) 1.005)
=/  shared-box  (apply-command:stead-team next.create alice (command 351 200 0 'container.create' ~[['title' 'Shared'] ['visibility' 'shared']]) 1.006)
=/  private-box  (apply-command:stead-team next.shared-box alice (command 352 202 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.007)
=/  migrated  (migrate next.private-box)
=/  baseline  (initialize:stead-product-history migrated ~zod)
=/  human-command  (owner-command 901 'principal.declare' 1 ~[['principal_id' (id 102)] ['kind' 'person'] ['display_name' 'Alice'] ['active' 'yes']])
=/  agent-command  (owner-command 902 'principal.declare' 1 ~[['principal_id' (id 103)] ['kind' 'person'] ['display_name' 'Bob'] ['active' 'yes']])
=/  human  (apply-owner:stead-product-history baseline human-command ~zod ~zod 2.000)
=/  agent  (apply-owner:stead-product-history next.human agent-command ~zod ~zod 2.001)
=/  created  (apply-work:stead-product-history next.agent alice make-work 2.002)
=/  question  (apply-work:stead-product-history next.created bob (comment-command 402 0) 2.003)
=/  markdown  (cat 3 (header:stead-team (id 201) 'published') 'Saved shared Markdown')
=/  doc-command  (command 450 201 0 'document.save' ~[['container_id' (id 200)] ['markdown' markdown]])
=/  saved  (apply-legacy:stead-product-history next.question alice doc-command 2.004)
=/  doc-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '1'] ['base_markdown_sha256' (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])]])
=/  outcomes  [%o (malt ~[[(id 500) doc-target]])]
=/  contracted  (apply-work:stead-product-history next.saved alice (command-four 403 111 'work.update-contract' ~[['execution_contract_revision' '1']] (goal outcomes)) 2.005)
=/  prepared=state:stead-product-history
  =/  state  next.contracted
  =/  index=@ud  0
  |-
  ?:  =(index 5)  state
  =/  reply  (apply-work:stead-product-history state bob (comment-command (add 800 index) (add 1 index)) (add 2.100 index))
  ?>  =('accepted' (result-field response.reply 'status'))
  $(state next.reply, index +(index))
=/  draft  (cat 3 markdown (cat 3 10 'Proposed exact revision.'))
=/  revised-markdown  (cat 3 draft (cat 3 10 'Clarified final instruction λ.  '))
=/  submit-command  (submission prepared 750 0 doc-target draft)
=/  submitted  (apply-doc:stead-product-history prepared alice submit-command 2.200)
=/  requested  (apply-doc:stead-product-history next.submitted bob (action next.submitted 751 'change.request-changes') 2.201)
=/  revised  (apply-doc:stead-product-history next.requested alice (submission next.requested 752 2 doc-target revised-markdown) 2.202)
=/  approved  (apply-doc:stead-product-history next.revised bob (action next.revised 753 'change.approve') 2.203)
=/  accept-command  (action next.approved 754 'change.accept')
=/  accepted  (apply-doc:stead-product-history next.approved alice accept-command 2.204)
=/  complete-command  (command-four 755 111 'work.complete' ~[['work_revision' '1'] ['execution_contract_revision' '2']] (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
=/  completed  (apply-work:stead-product-history next.accepted alice complete-command 2.205)
|%
++  test-product-doc-history-real-owner-review-accept-complete-replays-exactly
  =/  job  (restored next.completed)
  =/  metadata  (~(got by works.product.next.completed) [(id 100) (id 111)])
  =/  work  (~(got by works.data.db.next.completed) [(id 100) (id 111)])
  =/  retry  (apply-doc:stead-product-history next.completed alice accept-command 2.206)
  %-  expect
  !>  ?&  =('accepted' (result-field response.accepted 'status'))
          =('accepted' (result-field response.completed 'status'))
          =('done' (field data.work 'status'))  =(%outcomes completion-basis.metadata)
          =(%accepted status:(head next.completed))
          =(revised-markdown (doc-body next.completed))
          =(%valid phase.job)  =((some next.completed) (restored:stead-product-history job))
          =(response.accepted response.retry)  =(next.completed next.retry)
          =(2 (lent ~(tap by results.changes.next.completed)))
      ==
++  test-product-doc-history-orphaned-dropped-and-reordered-accept-pairs-rejected
  =/  product  product.next.accepted
  =/  events  events.product
  ?>  ?=(^ events)
  ?>  ?=(^ t.events)
  ?>  &(=(%doc-change family.i.events) =(%v3 family.i.t.events))
  =/  without-change  (rechain product t.events)
  =/  without-save  (rechain product [i.events t.t.events])
  =/  reversed  (rechain product [i.t.events i.events t.t.events])
  =/  body  (value (newest-body product))
  =/  forged  (record-replaced product 'save_event_digest' (hex 64 0))
  =/  orphan  (record-replaced product 'save_event' '')
  %-  expect
  !>  ?&  (rejected next.accepted(product without-change))
          (rejected next.accepted(product without-save))
          (rejected next.accepted(product reversed))
          (rejected next.accepted(product forged))
          (rejected next.accepted(product orphan))
          !=('' (field body 'save_event'))
      ==
++  test-product-doc-history-command-receipt-output-and-admission-tamper-rejected
  =/  product  product.next.accepted
  =/  record  (value (newest-body product))
  =/  receipt  (value (field record 'receipt'))
  =/  altered-receipt  (canonical [%o (~(put by receipt) 'result_digest' [%s (hex 64 0)])])
  =/  command  (value (field record 'canonical_command'))
  =/  payload  (child command 'payload')
  =.  payload  (~(put by payload) 'result_revision' [%s '1'])
  =/  altered-command  (canonical [%o (~(put by command) 'payload' [%o payload])])
  =/  tampered-receipt  (record-replaced product 'receipt' altered-receipt)
  =/  tampered-command  (record-replaced product 'canonical_command' altered-command)
  =/  tampered-output  (record-replaced product 'result' '{}')
  =/  sha  markdown-sha256:(~(got by results.changes.next.accepted) [(id 100) (id 601) 2])
  =/  oversized  (rap 3 (reap 32.769 'x'))
  =/  damaged  next.accepted(changes changes.next.accepted(bodies (~(put by bodies.changes.next.accepted) sha oversized)))
  %-  expect
  !>  ?&  (rejected next.accepted(product tampered-receipt))
          (rejected next.accepted(product tampered-command))
          (rejected next.accepted(product tampered-output))
          (rejected next.accepted(product (record-replaced product 'save_receipt' '{}')))
          (rejected next.accepted(product (record-replaced product 'canonical_command' (cat 3 (field record 'canonical_command') ' '))))
          (admission-refused damaged)
      ==
++  test-product-doc-history-historical-declarations-and-later-current-fences
  =/  disable  (owner-command 760 'principal.declare' 2 ~[['principal_id' (id 103)] ['kind' 'person'] ['display_name' 'Bob'] ['active' 'no']])
  =/  disabled  (apply-owner:stead-product-history next.completed disable ~zod ~zod 2.206)
  =/  old-review  (apply-doc:stead-product-history next.disabled bob (action next.disabled 761 'change.approve') 2.207)
  =/  old-comment  (apply-work:stead-product-history next.disabled bob (comment-command 762 6) 2.207)
  =/  historical  (restored next.disabled)
  =/  removed
    %+  skip  events.product.next.completed
    |=  event=event:stead-product-state
    ?.  =(%owner family.event)  |
    =/  record  (value (field (value bytes.event) 'body'))
    =/  cmd  (decode:stead-product-owner-codec (field record 'canonical_command'))
    =((id 902) request.cmd)
  =/  missing-declaration  (rechain product.next.completed removed)
  =/  person  (~(got by principals.catalog.next.disabled) (id 103))
  =/  changed-catalog  catalog.next.disabled(principals (~(put by principals.catalog.next.disabled) (id 103) person(active &)))
  %-  expect
  !>  ?&  =(%valid phase.historical)
          =((some next.disabled) (restored:stead-product-history historical))
          =('denied_or_not_found' (result-field response.old-review 'error'))
          =('denied_or_not_found' (result-field response.old-comment 'error'))
          =(next.disabled next.old-review)  =(next.disabled next.old-comment)
          (rejected next.completed(product missing-declaration))
          (rejected next.disabled(catalog changed-catalog))
      ==
++  test-product-doc-history-checkpoints-never-publish-half-an-accept-pair
  =/  started  (events-phase next.completed)
  =/  first  (step:stead-product-history started)
  ?>  =(%events phase.first)
  ?>  =(15 (lent events.product.rebuilt.first))
  ?>  ?=(^ remaining.first)
  ?>  ?=(^ t.remaining.first)
  ?>  =(%v3 family.i.remaining.first)
  ?>  =(%doc-change family.i.t.remaining.first)
  ?>  =('16' (field (value bytes.i.remaining.first) 'sequence'))
  ?>  =('17' (field (value bytes.i.t.remaining.first) 'sequence'))
  ?>  =(%approved status:(head rebuilt.first))
  ?>  =(markdown (doc-body rebuilt.first))
  =/  job  !<(job:stead-product-history (cue (jam !>(first))))
  =/  seen=@ud  1
  =/  partial=?  ?=(~ (restored:stead-product-history first))
  =/  safe=?  &
  |-
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))
    %-  expect
    !>  ?&  =(%valid phase.job)  (gte seen 2)  partial  safe
            =((some next.completed) (restored:stead-product-history job))
        ==
  ?>  (lth seen 16)
  =/  advanced  (step:stead-product-history job)
  =/  rebuilt  rebuilt.advanced
  =/  doc  (~(get by documents.data.db.rebuilt) [(id 100) (scope-key:stead-core (id 200) (id 201))])
  =/  change  (~(get by heads.changes.rebuilt) [(id 100) (id 601)])
  =/  doc-accepted  ?~(doc | =(2 revision.u.doc))
  =/  change-accepted  ?~(change | =(%accepted status.u.change))
  =/  next-safe  &(safe =(doc-accepted change-accepted))
  =/  next-partial  ?|(partial &(=(%events phase.advanced) ?=(~ (restored:stead-product-history advanced))))
  $(job !<(job:stead-product-history (cue (jam !>(advanced)))), seen +(seen), partial next-partial, safe next-safe)
++  test-product-doc-history-shared-budget-request-collisions-and-save-rollback
  =/  work-collision  (apply-work:stead-product-history next.submitted alice (comment-command 750 6) 2.201)
  =/  legacy-collision  (apply-legacy:stead-product-history next.submitted alice (command 750 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' draft]]) 2.201)
  =/  owner-collision  (apply-owner:stead-product-history next.submitted (owner-command 750 'principal.declare' 2 ~[['principal_id' (id 103)] ['kind' 'person'] ['display_name' 'Bob'] ['active' 'yes']]) ~zod ~zod 2.201)
  =/  doc-collision  (apply-doc:stead-product-history prepared alice (submission prepared 901 0 doc-target draft) 2.200)
  =/  filled  (budget-filled next.approved)
  =/  full  (apply-doc:stead-product-history filled alice (action filled 770 'change.accept') 2.204)
  =/  tight  next.approved(changes changes.next.approved(body-bytes (sub 8.388.608 object-bytes.data.db.next.approved)))
  =/  direct  (apply-legacy:stead-product-history tight alice (command 771 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' revised-markdown]]) 2.204)
  %-  expect
  !>  ?&  =('request_id_reuse' (result-field response.work-collision 'error'))
          =('request_id_reuse' (result-field response.legacy-collision 'error'))
          =('request_id_reuse' (result-field response.owner-collision 'error'))
          =('request_id_reuse' (result-field response.doc-collision 'error'))
          =(next.submitted next.work-collision)  =(next.submitted next.legacy-collision)
          =(next.submitted next.owner-collision)  =(prepared next.doc-collision)
          =('capacity_exceeded' (result-field response.full 'error'))
          =(db.filled db.next.full)  =(heads.changes.filled heads.changes.next.full)
          =('capacity_exceeded' (result-field response.direct 'error'))
          =(tight next.direct)
      ==
--

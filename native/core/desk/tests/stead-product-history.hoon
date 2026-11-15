::  Source-only owner/Work timeline tests. No local native execution or Home
::  activation is claimed. Every fixture identity is public and disposable.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-restore, stead-principals, stead-product-state, stead-product-codec, stead-product-migrate, stead-product-work, stead-product-owner-codec, stead-product-owner, stead-product-adapters, stead-product-restore, stead-product-history
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
  =/  next  product(events ~)
  =/  remaining  (flop events)
  |-
  ?~  remaining  next
  =/  body  (field (value bytes.i.remaining) 'body')
  $(remaining t.remaining, next (append-event:stead-product-state next family.i.remaining body))
++  ordinary-count
  |=  state=state:stead-product-history
  ^-  @ud
  (add (event-count:stead-team db.state '' |) (add (lent ~(tap by attempts.product.state)) (owner-count:stead-product-owner ledger.state |)))
++  full-budget
  |=  state=state:stead-product-history
  ^-  state:stead-product-history
  ::  Synthetic count fixture only, not a replay-valid or storage-capacity
  ::  qualification history. Unique scoped keys remain valid UUIDs and bounded.
  =/  count  (ordinary-count state)
  ?>  (lth count 4.096)
  =/  example  (~(got by attempts.product.state) [(id 100) (id 103) (id 402)])
  =/  left  (sub 4.096 count)
  =/  index=@ud  0
  =/  attempts  attempts.product.state
  |-
  ?:  =(left 0)  state(product product.state(attempts attempts))
  =/  key  [(id (add 100 (div index 64))) (id 102) (id (add 300 (mod index 64)))]
  ?>  !(~(has by attempts) key)
  $(left (dec left), index +(index), attempts (~(put by attempts) key example))
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
=/  baseline  (initialize:stead-product-owner migrated ~zod)
=/  human-command  (owner-command 901 'principal.declare' 1 ~[['principal_id' (id 102)] ['kind' 'person'] ['display_name' 'Alice'] ['active' 'yes']])
=/  agent-command  (owner-command 902 'principal.declare' 1 ~[['principal_id' (id 103)] ['kind' 'agent'] ['display_name' 'Bob worker'] ['active' 'yes']])
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
=/  grant-carol  (command 451 100 3 'policy.grant' ~[['grant_id' (id 503)] ['principal_id' (id 104)] ['role' 'contributor'] ['expires_at_ms' '8000000']])
=/  granted  (apply-legacy:stead-product-history next.contracted alice grant-carol 2.006)
=/  config-two  (member-config configuration 1 2 'yes')
=/  rotate-command  (owner-command 903 'home.configure' 1 ~[['configuration' config-two]])
=/  rotated  (apply-owner:stead-product-history next.granted rotate-command ~zod ~zod 2.007)
=/  bob-two  (need (native-context:stead-team db.next.rotated ~nec 2.008))
=/  old-binding  (apply-work:stead-product-history next.rotated bob (comment-command 404 1) 2.008)
=/  second-question  (apply-work:stead-product-history next.old-binding bob-two (comment-command 405 1) 2.009)
=/  disable-command  (owner-command 904 'principal.declare' 2 ~[['principal_id' (id 103)] ['kind' 'agent'] ['display_name' 'Bob worker'] ['active' 'no']])
=/  disabled  (apply-owner:stead-product-history next.second-question disable-command ~zod ~zod 2.010)
=/  snapshot=state:stead-product-history
  =/  state  next.disabled
  =/  index=@ud  0
  |-
  ?:  =(index 12)  state
  =/  reply  (apply-work:stead-product-history state alice (comment-command (add 600 index) (add 2 index)) (add 3.000 index))
  ?>  =('accepted' (result-field response.reply 'status'))
  $(state next.reply, index +(index))
|%
++  test-product-history-owner-work-doc-and-policy-replay-is-exact
  =/  result  (restored snapshot)
  =/  meta  (~(got by works.product.rebuilt.result) [(id 100) (id 111)])
  =/  author  (~(got by comments.product.rebuilt.result) [(id 100) (id 111) 1])
  =/  person  (~(got by principals.catalog.rebuilt.result) (id 103))
  =/  doc  (~(got by documents.data.db.rebuilt.result) [(id 100) (scope-key:stead-core (id 200) (id 201))])
  =/  blob  (~(got by objects.data.db.rebuilt.result) blob.doc)
  %-  expect
  !>  ?&  =('accepted' (result-field response.created 'status'))
          =('accepted' (result-field response.saved 'status'))
          =('accepted' (result-field response.contracted 'status'))
          =('accepted' (result-field response.granted 'status'))
          =(%valid phase.result)  =(snapshot rebuilt.result)
          =((some snapshot) (restored:stead-product-history result))
          =(22 (lent events.product.rebuilt.result))  =(4 (lent ~(tap by ledger.rebuilt.result)))
          =(1 work-revision.meta)  =(2 execution-revision.meta)  =(14 discussion-sequence.meta)
          =((id 103) principal.author)  =('~nec' identity-ship.author)  =(2.003 accepted-at.author)
          =((some %agent) kind.person)  !active.person
          =(1 revision.doc)  =(markdown data.body.blob)  =((met 3 markdown) length.body.blob)
          =(2 (role:stead-team db.rebuilt.result carol (id 100) 3.012))
      ==
++  test-product-history-rotation-and-disable-fence-all-current-writes
  =/  revoke-config  (member-config config-two 2 3 'no')
  =/  revoked  (apply-owner:stead-product-history next.second-question (owner-command 906 'home.configure' 2 ~[['configuration' revoke-config]]) ~zod ~zod 2.010)
  =/  denied-binding  (apply-work:stead-product-history next.revoked bob-two (comment-command 407 2) 2.011)
  =/  replayed-revocation  (restored next.revoked)
  =/  still-declared  (~(got by principals.catalog.next.revoked) (id 103))
  =/  denied-work  (apply-work:stead-product-history next.disabled bob-two (comment-command 406 2) 2.011)
  =/  denied-retry  (apply-work:stead-product-history next.disabled bob-two (comment-command 405 1) 2.011)
  =/  denied-doc  (apply-legacy:stead-product-history next.disabled bob-two (command 452 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' (cat 3 markdown ' changed')]]) 2.011)
  =/  denied-policy  (apply-legacy:stead-product-history next.disabled bob-two grant-carol 2.011)
  =/  retry  (apply-owner:stead-product-history snapshot human-command ~zod ~zod 3.012)
  =/  forged-owner  (apply-owner:stead-product-history snapshot human-command ~zod ~bus 3.012)
  %-  expect
  !>  ?&  =('accepted' (result-field response.rotated 'status'))
          =('denied_or_not_found' (result-field response.old-binding 'error'))  =(next.rotated next.old-binding)
          =('accepted' (result-field response.second-question 'status'))
          (active-member:stead-product-history next.second-question bob-two 2.010)
          =('accepted' (result-field response.revoked 'status'))  active.still-declared
          ?=(~ (native-context:stead-team db.next.revoked ~nec 2.011))
          =('denied_or_not_found' (result-field response.denied-binding 'error'))  =(next.revoked next.denied-binding)
          =((some next.revoked) (restored:stead-product-history replayed-revocation))
          (current:stead-team db.next.disabled bob-two 2.011)
          !(active-member:stead-product-history next.disabled bob-two 2.011)
          =('denied_or_not_found' (result-field response.denied-work 'error'))  =(next.disabled next.denied-work)
          =('denied_or_not_found' (result-field response.denied-retry 'error'))  =(next.disabled next.denied-retry)
          =('denied_or_not_found' (result-field response.denied-doc 'error'))  =(next.disabled next.denied-doc)
          =('denied_or_not_found' (result-field response.denied-policy 'error'))  =(next.disabled next.denied-policy)
          =(response.human response.retry)  =(snapshot next.retry)
          =('owner_required' (result-field response.forged-owner 'error'))  =(snapshot next.forged-owner)
      ==
++  test-product-history-rejects-rehashed-owner-command-receipt-digest-and-sender
  =/  state  next.human
  =/  command  (owner-command 901 'principal.declare' 1 ~[['principal_id' (id 102)] ['kind' 'person'] ['display_name' 'Changed Alice'] ['active' 'yes']])
  =/  wrong-command  (record-replaced product.state 'canonical_command' canonical-bytes.command)
  =/  receipt  (canonical [%o (~(put by (value response.human)) 'status' [%s 'rejected'])])
  =/  wrong-receipt  (record-replaced product.state 'receipt' receipt)
  =/  wrong-digest  (record-replaced product.state 'after_catalog_digest' (hex 64 0))
  =/  wrong-sender  (record-replaced product.state 'native_sender' '~bus')
  %-  expect
  !>  ?&  (rejected state(product wrong-command))
          (rejected state(product wrong-receipt))
          (rejected state(product wrong-digest))
          (rejected state(product wrong-sender))
      ==
++  test-product-history-reordered-and-dropped-owner-events-fail-after-rechaining
  =/  state  next.agent
  =/  events  events.product.state
  ?>  =(2 (lent events))
  ?>  ?=(^ events)
  =/  reordered  (rechain product.state (flop events))
  =/  dropped  (rechain product.state t.events)
  %-  expect
  !>  ?&  (rejected state(product reordered))
          (rejected state(product dropped))
          (rejected snapshot(product product.snapshot(events ~)))
      ==
++  test-product-history-rejects-todays-catalog-false-kind-and-missing-ledger
  =/  early  next.second-question
  =/  substituted  early(catalog catalog.snapshot)
  =/  false-kind  (record-replaced product.early 'principal_kind' 'person')
  =/  missing  snapshot(ledger (~(del by ledger.snapshot) (id 903)))
  =/  attempt  (~(got by ledger.snapshot) (id 904))
  =/  wrong-ledger  snapshot(ledger (~(put by ledger.snapshot) (id 904) attempt(digest (hex 64 0))))
  %-  expect
  !>  ?&  !=(catalog.early catalog.snapshot)
          (rejected substituted)  (rejected early(product false-kind))
          (rejected missing)  (rejected wrong-ledger)
      ==
++  test-product-history-incremental-checkpoint-never-publishes-partial-replay
  =/  first  (begin:stead-product-history snapshot ~zod)
  =/  ready  (events-phase snapshot)
  =/  partial  (step:stead-product-history ready)
  =/  checkpoint  !<(job:stead-product-history (cue (jam !>(partial))))
  =/  result  (finish checkpoint)
  %-  expect
  !>  ?&  ?=(~ (restored:stead-product-history first))
          =(%events phase.ready)  ?=(~ (restored:stead-product-history ready))
          =(%events phase.partial)  =(16 (lent events.product.rebuilt.partial))
          ?=(~ (restored:stead-product-history partial))  =(partial checkpoint)
          =((some snapshot) (restored:stead-product-history result))
          =(result (step:stead-product-history result))
      ==
++  test-product-history-exhausted-budgets-roll-back-catalog-doc-and-work
  =/  full  (full-budget next.second-question)
  =/  work  (apply-work:stead-product-history full alice (comment-command 650 2) 4.000)
  =/  doc  (apply-legacy:stead-product-history full alice (command 651 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' (cat 3 markdown ' changed')]]) 4.000)
  =/  owner  (apply-owner:stead-product-history full (owner-command 905 'principal.declare' 2 ~[['principal_id' (id 102)] ['kind' 'person'] ['display_name' 'New display'] ['active' 'yes']]) ~zod ~zod 4.000)
  =/  security-write  (apply-legacy:stead-product-history full alice (command 653 100 4 'policy.revoke' ~[['grant_id' (id 501)]]) 4.000)
  =/  reducing  (apply-owner:stead-product-history full disable-command ~zod ~zod 4.000)
  =/  entry  (~(got by ledger.next.reducing) (id 904))
  =/  security  (~(uni by ledger.full) (malt (turn (gulf 0 127) |=(n=@ud [(id (add 700 n)) entry]))))
  =/  exhausted  full(ledger security)
  =/  denied  (apply-owner:stead-product-history exhausted disable-command ~zod ~zod 4.001)
  ::  This separate non-replay-valid count fixture fills global security on
  ::  OTHER project keys. Project 100's local reserve is still empty, so the
  ::  wrapper must roll back the otherwise permitted local revoke.
  =/  proof  (~(got by receipts.data.db.next.security-write) [(id 100) (id 102) (id 653)])
  =/  security-receipts
    %-  malt
    %+  turn  (gulf 0 2.047)
    |=  n=@ud
    [[(id (add 200 (div n 64))) (id 102) (id (add 300 (mod n 64)))] proof]
  =/  before  next.second-question
  =/  security-full  before(db db.before(data data.db.before(receipts (~(uni by receipts.data.db.before) security-receipts))))
  =/  blocked-policy  (apply-legacy:stead-product-history security-full alice (command 654 100 4 'policy.revoke' ~[['grant_id' (id 501)]]) 4.001)
  ::  Separate typed-event capacity rollback: no attempted owner catalog or
  ::  Doc mutation may escape when its adjacent timeline append is full.
  ?>  ?=(^ events.product.before)
  =/  events-full  before(product product.before(events (reap 6.144 i.events.product.before)))
  =/  blocked-owner  (apply-owner:stead-product-history events-full disable-command ~zod ~zod 4.000)
  =/  blocked-doc  (apply-legacy:stead-product-history events-full alice (command 652 201 1 'document.save' ~[['container_id' (id 200)] ['markdown' (cat 3 markdown ' changed')]]) 4.000)
  %-  expect
  !>  ?&  =(4.096 (ordinary-count full))
          =('capacity_exceeded' (result-field response.work 'error'))  =(full next.work)
          =('capacity_exceeded' (result-field response.doc 'error'))  =(full next.doc)
          =('capacity_exceeded' (result-field response.owner 'error'))  =(full next.owner)
          =('accepted' (result-field response.security-write 'status'))
          =(4.096 (ordinary-count next.security-write))
          =('accepted' (result-field response.reducing 'status'))
          =('security' (result-field response.reducing 'capacity_class'))
          =('capacity_exceeded' (result-field response.denied 'error'))  =(exhausted next.denied)
          =(0 (event-count:stead-team db.security-full (id 100) &))
          =(2.048 (security-count:stead-product-owner db.security-full))
          =('capacity_exceeded' (result-field response.blocked-policy 'error'))  =(security-full next.blocked-policy)
          =('capacity_exceeded' (result-field response.blocked-owner 'error'))  =(events-full next.blocked-owner)
          =('capacity_exceeded' (result-field response.blocked-doc 'error'))  =(events-full next.blocked-doc)
      ==
++  test-product-history-admission-and-compatibility-do-not-erase-owner-obligations
  =/  pair=migrated:stead-product-migrate  [db.next.human product.next.human]
  =/  unsupported  (mule |.((begin:stead-product-restore pair ~zod)))
  =/  entry  (~(got by ledger.snapshot) (id 904))
  =/  large  entry(command (rap 3 (reap 65.537 'x')))
  =/  oversized  snapshot(ledger (~(put by ledger.snapshot) (id 904) large))
  =/  person  (~(got by principals.catalog.snapshot) (id 103))
  =/  bad-catalog  catalog.snapshot(principals (~(put by principals.catalog.snapshot) (id 103) person(revision 0)))
  %-  expect
  !>  ?&  ?=(%| -.unsupported)
          (admission-refused oversized)
          (admission-refused snapshot(catalog bad-catalog))
          (rejected snapshot(ledger ~))
      ==
--

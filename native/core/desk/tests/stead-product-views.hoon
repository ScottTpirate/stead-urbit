::  Reserved query/4 source tests. Not registered or qualified by this file.
::  Fixtures use accepted predecessor writes and the real migration/reducer;
::  the narrow target/kind adapters below are synthetic authority dependencies.
/+  *test, stead-codec, stead-core, stead-projection, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-product-codec, stead-product-work, stead-product-query, stead-product-views
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  put
  |=  [value=json name=@t replacement=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) name replacement)]
++  command
  |=  [req=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  value
    (object ~[['protocol' 'stead.command/3'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
  ?>  ?=([%o *] value)
  (decode:stead-team-codec (canonical [%o (~(put by p.value) 'payload' (object payload))]))
++  command-four
  |=  [req=@ud work=@ud operation=@t expected=(list [@t @t]) payload=json]
  ^-  command:stead-product-codec
  =/  value  (object ~[['protocol' 'stead.command/4'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id work)] ['authority_epoch' '1'] ['operation' operation]])
  (decode:stead-product-codec (canonical (put (put value 'expected' (object expected)) 'payload' payload)))
++  result-object
  |=  raw=@t
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  p.value
++  result-field
  |=  [raw=@t name=@t]
  ^-  @t
  (field (result-object raw) name)
++  result-rows
  |=  raw=@t
  ^-  object-map
  =/  value  (~(got by (result-object raw)) 'rows')
  ?>  ?=([%o *] value)
  p.value
++  result-row
  |=  [raw=@t index=@ud]
  ^-  object-map
  =/  value  (~(got by (result-rows raw)) (decimal index))
  ?>  ?=([%o *] value)
  p.value
++  result-count
  |=  raw=@t
  ^-  @ud
  (lent ~(tap by (result-rows raw)))
++  indexed
  |=  db=state:stead-team
  ^-  state:stead-projection
  =/  view  (begin:stead-projection db *state:stead-projection)
  =/  budget=@ud  256
  |-
  ?:  (ready:stead-projection db view)  view
  ?>  &((gth budget 0) !poisoned.view rebuilding.view)
  $(view (batch:stead-projection db view), budget (dec budget))
++  migrate
  |=  db=state:stead-team
  ^-  migrated:stead-product-migrate
  =/  job  (begin:stead-product-migrate db ~zod)
  =/  budget=@ud  1.024
  |-
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))
    (need (result:stead-product-migrate job))
  ?>  (gth budget 0)
  $(job (step:stead-product-migrate job), budget (dec budget))
++  fixture-kind
  |=  [project=@t principal=@t now=@ud]
  ^-  (unit principal-kind:stead-product-work)
  ?:  (~(has in (silt ~[(id 102) (id 103) (id 104)])) principal)  (some %person)
  ~
++  fixture-target
  |=  [project=@t work=@t principal=@t target=json now=@ud]
  ^-  ?
  ::  This adapter is deliberately explicit; current shared-collection checks
  ::  still belong to the real Work reducer before it invokes this callback.
  ?.  ?=([%o *] target)  |
  ?&  =((id 100) project)  =('document' (field p.target 'kind'))
      =((id 200) (field p.target 'collection_id'))
      =('0' (field p.target 'expected_revision'))
      =('' (field p.target 'base_markdown_sha256'))
  ==
++  no-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  ~
++  profile
  ^-  resolvers:stead-product-work
  [fixture-kind fixture-target no-proof]
++  run
  |=  [state=migrated:stead-product-migrate actor=authentication:stead-team cmd=command:stead-product-codec now=@ud]
  ^-  transition:stead-product-work
  (apply-command:stead-product-work db.state product.state actor cmd now profile)
++  create-four
  |=  [req=@ud work=@ud outcomes=json]
  ^-  command:stead-product-codec
  =/  payload
    (object ~[['title' 'New Work without legacy index'] ['description' 'Exact new description'] ['acceptance_criteria' 'Review exact output'] ['type' 'task'] ['status' 'todo'] ['priority' 'none'] ['owner_principal_id' ''] ['worker_principal_id' ''] ['blocked_reason' '']])
  (command-four req work 'work.create' ~[['work_revision' '0'] ['execution_contract_revision' '0']] (put payload 'required_outcomes' outcomes))
++  read
  |=  [state=migrated:stead-product-migrate prior=state:stead-views actor=authentication:stead-team query=query:stead-team-codec now=@ud entropy=@]
  ^-  result:stead-product-views
  (execute:stead-product-views db.state product.state prior actor query now entropy)
++  refused
  |=  raw=@t
  ^-  ?
  ?=([%| *] (mule |.((decode:stead-product-query raw))))
++  rehash-outcomes
  |=  [state=migrated:stead-product-migrate work=@ud outcomes=json]
  ^-  migrated:stead-product-migrate
  ::  Deliberately damaged restored input, not an accepted command. Rehashing
  ::  makes the negative exercise shape/audience validation, not a stale hash.
  =/  key=work-key:stead-product-state  [(id 100) (id work)]
  =/  row  (~(got by works.data.db.state) key)
  =/  metadata  (~(got by works.product.state) key)
  =/  data  (~(put by data.row) 'required_outcomes' outcomes)
  =/  digest  (contract-digest:stead-product-state key execution-revision.metadata data)
  :-  db.state(data data.db.state(works (~(put by works.data.db.state) key row(data data))))
  product.state(works (~(put by works.product.state) key metadata(execution-digest digest)))
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
=/  exact-description  (cat 3 'Exact λ <description>  ' 10)
=/  work-fields  ~[['title' 'Migrated Work'] ['description' exact-description] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
=/  created  (apply-command:stead-team next.reader alice (command 304 101 0 'work.create' work-fields) 1.005)
=/  assigned  (apply-command:stead-team next.created alice (command 305 101 1 'work.assign' ~[['assignee_principal_id' principal.identity.bob]]) 1.006)
=/  exact-comment  (cat 3 'Exact λ <comment>  ' 10)
=/  commented  (apply-command:stead-team next.assigned bob (command 306 101 2 'work.comment' ~[['body' exact-comment]]) 1.007)
=/  shared-box  (apply-command:stead-team next.commented alice (command 307 200 0 'container.create' ~[['title' 'Shared'] ['visibility' 'shared']]) 1.008)
=/  private-box  (apply-command:stead-team next.shared-box alice (command 308 202 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.009)
=/  initial-product  (migrate next.private-box)
=/  work-query=query:stead-team-codec  [(id 600) 'work' (id 100) '' '' '' '']
=/  exact-query  work-query(resource (id 101))
=/  comments-query  exact-query(kind 'comments')
=/  doc-target  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '0'] ['base_markdown_sha256' '']])
=/  outcomes  [%o (malt ~[[(id 500) doc-target]])]
=/  many-comments
  =/  state  initial-product
  =/  sequence=@ud  1
  |-
  ?:  =(22 sequence)  state
  =/  payload  (object ~[['body' (cat 3 'Comment ' (decimal +(sequence)))]])
  =/  cmd  (command-four (add 700 sequence) 101 'work.comment' ~[['discussion_sequence' (decimal sequence)]] payload)
  =/  accepted  (run state bob cmd (add 2.000 sequence))
  ?>  =('accepted' (result-field response.accepted 'status'))
  $(state [db.accepted product.accepted], sequence +(sequence))
|%
++  test-product-views-query-four-closed-grammar-and-version
  ^-  tang
  =/  wire  (bytes:stead-product-query work-query)
  =/  value  (need (parse wire))
  ?>  =(work-query (decode:stead-product-query wire))
  ?>  =(exact-query (decode:stead-product-query (bytes:stead-product-query exact-query)))
  ?>  =(comments-query (decode:stead-product-query (bytes:stead-product-query comments-query)))
  ?>  (refused (canonical (put value 'protocol' [%s 'stead.query/3'])))
  ?>  (refused (canonical (put value 'principal_id' [%s (id 102)])))
  ?>  (refused (bytes:stead-product-query work-query(request 'invalid')))
  ?>  (refused (bytes:stead-product-query work-query(project '')))
  ?>  (refused (bytes:stead-product-query work-query(project 'invalid')))
  ?>  (refused (bytes:stead-product-query work-query(container (id 200))))
  ?>  (refused (bytes:stead-product-query work-query(search 'text')))
  ?>  (refused (bytes:stead-product-query work-query(kind 'documents')))
  ?>  (refused (bytes:stead-product-query comments-query(resource '')))
  ?>  (refused (bytes:stead-product-query work-query(resource 'invalid')))
  ?>  (refused (bytes:stead-product-query work-query(cursor 'invalid')))
  ?>  (refused '{"protocol":"stead.query/4","protocol":"stead.query/4"}')
  ~
++  test-product-views-migrated-exact-and-preview-flat-contract
  ^-  tang
  =/  full  (read initial-product *state:stead-views carol exact-query 2.000 1)
  =/  preview  (read initial-product *state:stead-views bob work-query 2.000 2)
  =/  row  (result-row response.full 0)
  =/  small  (result-row response.preview 0)
  ?>  =('stead.query-result/4' (result-field response.full 'protocol'))
  ?>  =(1 (result-count response.full))
  ?>  =((id 100) (field row 'project_id'))
  ?>  =((id 101) (field row 'resource_id'))
  ?>  =(exact-description (field row 'description'))
  ?>  =('3' (field row 'resource_revision'))
  ?>  =('2' (field row 'work_revision'))
  ?>  =('1' (field row 'execution_contract_revision'))
  ?>  =('1' (field row 'discussion_sequence'))
  ?>  =('yes' (field row 'legacy_assignment_pending'))
  ?>  =('Bob' (field row 'legacy_assignee_display_name'))
  ?>  =('' (field row 'owner_principal_id'))
  ?>  =('' (field row 'worker_principal_id'))
  ?>  =([%s '{}'] (~(got by row) 'required_outcomes'))
  ?>  (lte (lent ~(tap by row)) 32)
  ?>  (levy ~(tap by row) |=([key=@t value=json] ?=([%s *] value)))
  ?>  !(~(has by row) 'discussion')
  ?>  !(~(has by row) 'snippet')
  ?>  !(~(has by small) 'description')
  ?>  !(~(has by small) 'required_outcomes')
  ?>  =((prefix:stead-views exact-description 160) (field small 'snippet'))
  ?>  !(contains:stead-views 'authentication_context' response.full)
  ?>  !(contains:stead-views 'grant_target' response.full)
  ~
++  test-product-views-v4-work-does-not-require-legacy-journal-index
  ^-  tang
  =/  accepted  (run initial-product alice (create-four 800 102 (object ~)) 2.000)
  ?>  =('accepted' (result-field response.accepted 'status'))
  =/  state=migrated:stead-product-migrate  [db.accepted product.accepted]
  =/  index  (indexed db.state)
  =/  selected  exact-query(resource (id 102))
  ?>  =(journal.data.db.initial-product journal.data.db.state)
  ?>  !(~(has in resources.visible.index) [(id 100) 'work' '' (id 102)])
  ?>  ?=(~ (rows:stead-views db.state visible.index bob selected 2.001))
  =/  full  (read state *state:stead-views bob selected 2.001 3)
  =/  list  (read state *state:stead-views bob work-query 2.001 4)
  ?>  =('read' (result-field response.full 'status'))
  ?>  =((id 102) (field (result-row response.full 0) 'resource_id'))
  ?>  =('New Work without legacy index' (field (result-row response.full 0) 'title'))
  ?>  =(2 (result-count response.list))
  ?>  =(1 (lent events.product.state))
  ~
++  test-product-views-separate-comments-ordered-pages-and-no-raw-provenance
  ^-  tang
  =/  first  (read many-comments *state:stead-views bob comments-query 2.100 5)
  =/  follow  comments-query(cursor (result-field response.first 'cursor'))
  =/  second  (read many-comments next.first bob follow 2.101 6)
  ?>  =(20 (result-count response.first))
  ?>  =(2 (result-count response.second))
  ?>  =('' (result-field response.second 'cursor'))
  ?>  (levy (gulf 0 19) |=(n=@ud =((decimal +(n)) (field (result-row response.first n) 'sequence'))))
  ?>  =('21' (field (result-row response.second 0) 'sequence'))
  ?>  =('22' (field (result-row response.second 1) 'sequence'))
  =/  legacy  (result-row response.first 0)
  ?>  =(exact-comment (field legacy 'body'))
  ?>  =((id 306) (field legacy 'request_id'))
  ?>  =('1007' (field legacy 'accepted_at_ms'))
  ?>  =('3' (field legacy 'legacy_comment_revision'))
  ?>  =('Bob' (field legacy 'display_name'))
  =/  saved  (~(got by comments.product.many-comments) [(id 100) (id 101) 1])
  ?>  &(!=('' authentication.saved) !=('' receipt.saved))
  =/  hidden  saved(authentication 'AUTH-SECRET-CANARY', receipt 'RECEIPT-SECRET-CANARY')
  =/  damaged  many-comments(product product.many-comments(comments (~(put by comments.product.many-comments) [(id 100) (id 101) 1] hidden)))
  =/  safe  (read damaged *state:stead-views carol comments-query 2.102 7)
  ?>  !(contains:stead-views 'SECRET-CANARY' response.safe)
  ?>  !(contains:stead-views 'authentication' response.safe)
  ?>  !(contains:stead-views 'receipt' response.safe)
  =/  full  (read many-comments *state:stead-views bob exact-query 2.103 8)
  ?>  =('22' (field (result-row response.full 0) 'discussion_sequence'))
  ?>  =('2' (field (result-row response.full 0) 'work_revision'))
  ?>  !(contains:stead-views 'Comment 22' response.full)
  ~
++  test-product-views-cursor-binds-actor-scope-epoch-generation-and-purpose
  ^-  tang
  =/  first  (read many-comments *state:stead-views bob comments-query 2.100 9)
  =/  cursor  (result-field response.first 'cursor')
  =/  follow  comments-query(cursor cursor)
  =/  second  (read many-comments next.first bob follow 2.101 10)
  =/  reused  (read many-comments next.second bob follow 2.102 11)
  =/  actor  (read many-comments next.first carol follow 2.102 12)
  =/  scope  (read many-comments next.first bob work-query(cursor cursor) 2.102 13)
  =/  expired  (read many-comments next.first bob follow 302.101 14)
  =/  policy  (~(got by projects.data.db.many-comments) (id 100))
  =/  changed  many-comments(db db.many-comments(data data.db.many-comments(projects (~(put by projects.data.db.many-comments) (id 100) policy(epoch +(epoch.policy))))))
  =/  epoch  (read changed next.first bob follow 2.102 15)
  =/  added  (run many-comments bob (command-four 850 101 'work.comment' ~[['discussion_sequence' '22']] (object ~[['body' 'New visible comment']])) 2.102)
  ?>  =('accepted' (result-field response.added 'status'))
  =/  generation  (read [db.added product.added] next.first bob follow 2.103 16)
  =/  record  (~(got by cursors.next.first) cursor)
  ?>  =('product-query' purpose.record)
  ::  Change only the purpose: every actor/filter/generation binding still
  ::  matches, so a legacy cursor cannot be rejected merely by a side effect.
  =/  old-purpose  next.first(cursors (~(put by cursors.next.first) cursor record(purpose 'query')))
  =/  purpose  (read many-comments old-purpose bob follow 2.102 17)
  ?>  %+  levy  ~[response.reused response.actor response.scope response.expired response.epoch response.generation response.purpose]
      |=(raw=@t =('stale_cursor' (result-field raw 'error')))
  ?>  =(next.second next.reused)
  ?>  =(next.first next.actor)
  ?>  =(next.first next.generation)
  ?>  =(old-purpose next.purpose)
  ~
++  test-product-views-private-document-change-does-not-signal-work
  ^-  tang
  =/  before  (read many-comments *state:stead-views bob work-query 2.100 18)
  =/  comments  (read many-comments *state:stead-views bob comments-query 2.100 19)
  =/  markdown  (cat 3 (header:stead-team (id 203) 'draft') 'PRIVATE-DOC-SECRET-CANARY')
  =/  cmd  (command 860 203 0 'document.save' ~[['container_id' (id 202)] ['markdown' markdown]])
  =/  saved  (apply-legacy:stead-product-work db.many-comments product.many-comments alice cmd 2.101)
  ?>  =('accepted' (result-field response.saved 'status'))
  ?>  !(box-access:stead-team db.saved bob (id 100) (id 202) 2.102)
  =/  state=migrated:stead-product-migrate  [db.saved product.saved]
  =/  after  (read state *state:stead-views bob work-query 2.102 20)
  =/  follow  comments-query(cursor (result-field response.comments 'cursor'))
  =/  next  (read state next.comments bob follow 2.102 21)
  ?>  =((result-field response.before 'generation') (result-field response.after 'generation'))
  ?>  =(response.before response.after)
  ?>  =(2 (result-count response.next))
  ?>  !(contains:stead-views 'PRIVATE-DOC' response.after)
  ?>  !(contains:stead-views 'PRIVATE-DOC' response.next)
  ~
++  test-product-views-current-access-revocation-expiry-and-deletion
  ^-  tang
  =/  contributor  (read initial-product *state:stead-views bob exact-query 2.000 22)
  =/  reader  (read initial-product *state:stead-views carol exact-query 2.000 23)
  ?>  =('read' (result-field response.contributor 'status'))
  ?>  =('read' (result-field response.reader 'status'))
  =/  missing  (read initial-product *state:stead-views bob exact-query(project (id 999)) 2.001 24)
  =/  stale-identity  (read initial-product *state:stead-views bob(identity identity.bob(binding 'invalid')) exact-query 2.001 25)
  =/  expired-grant  (read initial-product *state:stead-views carol exact-query 5.000 26)
  =/  expired-identity  (read initial-product *state:stead-views alice exact-query 10.000.000 27)
  =/  revoke  (command 870 100 3 'policy.revoke' ~[['grant_id' (id 501)]])
  =/  revoked  (apply-legacy:stead-product-work db.initial-product product.initial-product alice revoke 2.001)
  ?>  =('accepted' (result-field response.revoked 'status'))
  =/  outsider  (read [db.revoked product.revoked] *state:stead-views bob exact-query 2.002 28)
  =/  remove  (command-four 871 101 'work.delete' ~[['work_revision' '2'] ['execution_contract_revision' '1'] ['discussion_sequence' '1']] (object ~))
  =/  deleted  (run initial-product alice remove 2.001)
  ?>  =('accepted' (result-field response.deleted 'status'))
  =/  tomb  (read [db.deleted product.deleted] *state:stead-views alice exact-query 2.002 29)
  ?>  %+  levy  ~[response.missing response.stale-identity response.expired-grant response.expired-identity response.outsider response.tomb]
      |=(raw=@t =('denied_or_not_found' (result-field raw 'error')))
  =/  absent  (execute:stead-product-views db.initial-product *state:stead-product-state *state:stead-views bob exact-query 2.000 30)
  ?>  =('migration_required' (result-field response.absent 'error'))
  ?>  =(*state:stead-views next.absent)
  ~
++  test-product-views-required-outcomes-exact-string-or-whole-detail-rejection
  ^-  tang
  =/  accepted  (run initial-product alice (create-four 880 102 outcomes) 2.000)
  ?>  =('accepted' (result-field response.accepted 'status'))
  =/  state=migrated:stead-product-migrate  [db.accepted product.accepted]
  =/  query  exact-query(resource (id 102))
  =/  valid  (read state *state:stead-views bob query 2.001 31)
  =/  row  (result-row response.valid 0)
  ?>  =([%s (canonical outcomes)] (~(got by row) 'required_outcomes'))
  ?>  =(32 (lent ~(tap by row)))
  =/  bad-target  (put doc-target 'expected_revision' [%s '01'])
  =/  malformed  (rehash-outcomes state 102 [%o (malt ~[[(id 500) bad-target]])])
  =/  shape  (read malformed *state:stead-views bob query 2.002 32)
  =/  private  (put doc-target 'collection_id' [%s (id 202)])
  =/  mixed  (rehash-outcomes state 102 [%o (malt ~[[(id 500) doc-target] [(id 501) private]])])
  =/  audience  (read mixed *state:stead-views bob query 2.002 33)
  ?>  =('invalid_product_state' (result-field response.shape 'error'))
  ?>  =('invalid_product_state' (result-field response.audience 'error'))
  ?>  !(~(has by (result-object response.shape)) 'rows')
  ?>  !(~(has by (result-object response.audience)) 'rows')
  ?>  !(contains:stead-views 'required_outcomes' response.audience)
  =/  metadata  (~(got by works.product.state) [(id 100) (id 102)])
  =/  proof=completion:stead-product-state  [(id 102) (id 881) execution-revision.metadata execution-digest.metadata 'PROOF-SECRET-CANARY']
  =/  protected  state(product product.state(works (~(put by works.product.state) [(id 100) (id 102)] metadata(completion-basis %outcomes, completion (some proof)))))
  =/  safe  (read protected *state:stead-views bob query 2.003 34)
  ?>  =('accepted-outcomes' (field (result-row response.safe 0) 'completion_basis'))
  ?>  =('' (field (result-row response.safe 0) 'completion_note'))
  ?>  !(contains:stead-views 'PROOF-SECRET-CANARY' response.safe)
  ?>  !(contains:stead-views 'authentication' response.safe)
  ?>  !(contains:stead-views 'receipt' response.safe)
  ~
--

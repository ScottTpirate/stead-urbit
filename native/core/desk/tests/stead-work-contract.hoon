/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-work-contract
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
=/  detail=query:stead-team-codec  [(id 601) 'work' (id 100) '' (id 101) '' '']
|%
++  test-work-contract-creation-domain-vector
  =/  contract  (need (replay:stead-work-contract journal.data.db (id 100) (id 101)))
  %-  expect
  !>  ?&  =(contract [1 'Draft' 'Notes'])
          =('921aaf0599b23bed49a622a56555072751ede18c5998f81546b743ae31450e06' (fingerprint:stead-work-contract (id 100) (id 101) contract))
          !=((fingerprint:stead-work-contract (id 100) (id 101) contract) (fingerprint:stead-work-contract (id 100) (id 102) contract))
      ==
++  test-work-contract-comments-and-metadata-preserve-pin
  =/  comment  (apply-command:stead-team db bob (command 305 101 1 'work.comment' ~[['body' 'A clarification']]) 1.006)
  =/  assign  (apply-command:stead-team next.comment alice (command 306 101 2 'work.assign' ~[['assignee_principal_id' principal.identity.bob]]) 1.007)
  =/  metadata  ~[['title' 'Draft'] ['description' 'Notes'] ['type' 'problem'] ['status' 'done'] ['priority' 'high']]
  =/  update  (apply-command:stead-team next.assign alice (command 307 101 3 'work.update' metadata) 1.008)
  =/  before  (replay:stead-work-contract journal.data.db (id 100) (id 101))
  =/  after  (replay:stead-work-contract journal.data.next.update (id 100) (id 101))
  %-  expect
  !>  ?&  =('4' (result-field response.update 'resource_revision'))
          =(before after)
          =(before (replay:stead-work-contract journal.data.next.comment (id 100) (id 101)))
          =(before (replay:stead-work-contract journal.data.next.assign (id 100) (id 101)))
      ==
++  test-work-contract-exact-goal-edits-and-revert-advance
  =/  title-fields  ~[['title' 'Draft '] ['description' 'Notes'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
  =/  title  (apply-command:stead-team db alice (command 305 101 1 'work.update' title-fields) 1.006)
  =/  body-fields  ~[['title' 'Draft '] ['description' 'Notes.'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
  =/  body  (apply-command:stead-team next.title alice (command 306 101 2 'work.update' body-fields) 1.007)
  =/  noop  (apply-command:stead-team next.body alice (command 307 101 3 'work.update' body-fields) 1.008)
  =/  revert  (apply-command:stead-team next.noop alice (command 308 101 4 'work.update' work-fields) 1.009)
  =/  before  (need (replay:stead-work-contract journal.data.db (id 100) (id 101)))
  =/  after  (need (replay:stead-work-contract journal.data.next.revert (id 100) (id 101)))
  %-  expect
  !>  ?&  =((some [2 'Draft ' 'Notes']) (replay:stead-work-contract journal.data.next.title (id 100) (id 101)))
          =((some [3 'Draft ' 'Notes.']) (replay:stead-work-contract journal.data.next.body (id 100) (id 101)))
          =((some [3 'Draft ' 'Notes.']) (replay:stead-work-contract journal.data.next.noop (id 100) (id 101)))
          =(after [4 'Draft' 'Notes'])
          !=((fingerprint:stead-work-contract (id 100) (id 101) before) (fingerprint:stead-work-contract (id 100) (id 101) after))
      ==
++  test-work-contract-scope-and-deletion
  =/  gone  (apply-command:stead-team db alice (command 305 101 1 'work.delete' ~) 1.006)
  =/  other  (apply-command:stead-team db alice (command 306 108 0 'work.create' work-fields) 1.006)
  =/  oversized  (mule |.((replay:stead-work-contract (reap 6.145 [(id 999) '' '']) (id 100) (id 101))))
  %-  expect
  !>  ?&  ?=(~ (replay:stead-work-contract journal.data.db (id 999) (id 101)))
          ?=(~ (replay:stead-work-contract journal.data.db (id 100) (id 999)))
          ?=(~ (replay:stead-work-contract journal.data.next.gone (id 100) (id 101)))
          =((replay:stead-work-contract journal.data.db (id 100) (id 101)) (replay:stead-work-contract journal.data.next.other (id 100) (id 101)))
          !(authorized:stead-views next.gone alice detail 1.010)
          ?=([%| *] oversized)
      ==
++  test-work-contract-authorized-detail-and-capability
  =/  view  (indexed db)
  =/  found  (snag 0 (rows:stead-views db visible.view carol detail 1.010))
  =/  listing  (snag 0 (rows:stead-views db visible.view carol detail(resource '') 1.010))
  =/  capability  (snag 0 (rows:stead-views db visible.view carol detail(kind 'capabilities', project '', resource '') 1.010))
  =/  denied  (execute:stead-views db view *state:stead-views carol detail 5.000 0xabc)
  =/  inconsistent  (~(put by data:(~(got by works.data.db) [(id 100) (id 101)])) 'title' [%s 'Unrecorded'])
  =/  refused  (mule |.((fields:stead-work-contract journal.data.db (id 100) (id 101) inconsistent)))
  %-  expect
  !>  ?&  (authorized:stead-views db carol detail 1.010)
          =('stead.work-contract/1' (field fields.found 'execution_contract_protocol'))
          =('1' (field fields.found 'execution_contract_revision'))
          =('921aaf0599b23bed49a622a56555072751ede18c5998f81546b743ae31450e06' (field fields.found 'execution_contract_digest'))
          =('stead.work-contract/1' (field fields.capability 'work_contract'))
          !(~(has by fields.listing) 'execution_contract_revision')
          =('denied_or_not_found' (result-field response.denied 'error'))
          ?=([%| *] refused)
      ==
++  test-work-contract-replay-preserves-authoritative-snapshot
  =/  request  (command 305 101 1 'work.comment' ~[['body' 'Context only']])
  =/  accepted  (apply-command:stead-team db bob request 1.006)
  =/  repeated  (apply-command:stead-team next.accepted bob request 1.007)
  =/  restored  (need (result:stead-restore (step:stead-restore (begin:stead-restore next.accepted ~zod))))
  =/  before  (jam next.accepted)
  =/  contract  (replay:stead-work-contract journal.data.restored (id 100) (id 101))
  %-  expect
  !>  ?&  =(accepted repeated)
          =(next.accepted restored)
          =(before (jam restored))
          =((some [1 'Draft' 'Notes']) contract)
          =('2' (result-field response.accepted 'resource_revision'))
      ==
--

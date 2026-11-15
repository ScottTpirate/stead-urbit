/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract
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
=/  comment-one  (apply-command:stead-team db bob (command 305 101 1 'work.comment' ~[['body' 'Exact <first>']]) 1.006)
=/  assigned  (apply-command:stead-team next.comment-one alice (command 306 101 2 'work.assign' ~[['assignee_principal_id' principal.identity.bob]]) 1.007)
=/  progress-fields  ~[['title' 'Draft'] ['description' 'Notes'] ['type' 'task'] ['status' 'in_progress'] ['priority' 'high']]
=/  progress  (apply-command:stead-team next.assigned alice (command 307 101 3 'work.update' progress-fields) 1.008)
=/  goal-fields  ~[['title' 'Draft revised'] ['description' 'Notes'] ['type' 'task'] ['status' 'in_progress'] ['priority' 'high']]
=/  goal  (apply-command:stead-team next.progress alice (command 308 101 4 'work.update' goal-fields) 1.009)
=/  blocked-fields  ~[['title' 'Draft revised'] ['description' 'Notes'] ['type' 'task'] ['status' 'blocked'] ['priority' 'high']]
=/  blocked  (apply-command:stead-team next.goal alice (command 309 101 5 'work.update' blocked-fields) 1.010)
=/  comment-two  (apply-command:stead-team next.blocked bob (command 310 101 6 'work.comment' ~[['body' 'Exact second  ']]) 1.011)
=/  unknown-blocked  (apply-command:stead-team next.comment-two alice (command 311 108 0 'work.create' blocked-fields) 1.012)
=/  done-fields  ~[['title' 'Historic Done'] ['description' 'No modern acceptance receipt'] ['type' 'task'] ['status' 'done'] ['priority' 'none']]
=/  done  (apply-command:stead-team next.unknown-blocked alice (command 312 109 0 'work.create' done-fields) 1.013)
=/  doomed  (apply-command:stead-team next.done alice (command 313 110 0 'work.create' work-fields) 1.014)
=/  removed  (apply-command:stead-team next.doomed alice (command 314 110 1 'work.delete' ~) 1.015)
=/  legacy  next.removed
|%
++  test-product-migrate-deterministic-after-real-predecessor-replay
  =/  restored  (need (result:stead-restore (step:stead-restore (begin:stead-restore legacy ~zod))))
  =/  first  (finished legacy)
  =/  second  (finished restored)
  =/  repeated  (step:stead-product-migrate first)
  %-  expect
  !>  ?&  =(legacy restored)
          =(%valid phase.first)  =(%valid phase.second)
          =(first repeated)
          =((result:stead-product-migrate first) (result:stead-product-migrate second))
      ==
++  test-product-migrate-independent-counters-and-original-comment-provenance
  =/  converted  (migrate legacy)
  =/  work  (~(got by works.product.converted) [(id 100) (id 101)])
  =/  first  (~(got by comments.product.converted) [(id 100) (id 101) 1])
  =/  second  (~(got by comments.product.converted) [(id 100) (id 101) 2])
  =/  receipt  (~(got by receipts.data.legacy) [(id 100) principal.identity.bob (id 305)])
  =/  current  (~(got by works.data.db.converted) [(id 100) (id 101)])
  =/  old-pin  (need (replay:stead-work-contract journal.data.legacy (id 100) (id 101)))
  %-  expect
  !>  ?&  =(4 work-revision.work)  =(2 execution-revision.work)
          =(2 discussion-sequence.work)  =(7 revision.current)
          =('Exact <first>' body.first)  =('Exact second  ' body.second)
          =((id 305) request.first)  =((id 310) request.second)
          =((some 2) legacy-revision.first)  =((some 7) legacy-revision.second)
          =(principal.identity.bob principal.first)  =('~nec' identity-ship.first)
          =(1.006 accepted-at.first)  =(bytes.receipt receipt.first)
          !=('' authentication.first)
          !(~(has by data.current) 'discussion')
          =('' (field data.current 'acceptance_criteria'))
          !=(execution-digest.work (fingerprint:stead-work-contract (id 100) (id 101) old-pin))
          =(execution-digest.work (contract-digest:stead-product-state [(id 100) (id 101)] 2 data.current))
      ==
++  test-product-migrate-prefix-bytes-and-nonwork-state-remain-exact
  ?>  ?=(^ journal.data.legacy)
  =/  converted  (migrate legacy)
  =/  db  db.converted
  =/  original-work  db(data data.db(works works.data.legacy))
  =/  boundary  (need migration.product.converted)
  =/  expected  (boundary-of:stead-product-state journal-count.boundary heads.boundary predecessor-registry.boundary timeline-digest.boundary)
  =/  changed  (boundary-of:stead-product-state journal-count.boundary heads.boundary predecessor-registry.boundary (hex 64 0))
  =/  other-wire  (object ~[['protocol' 'stead.command/3'] ['request_id' (id 900)] ['project_id' (id 200)] ['resource_id' (id 200)] ['expected_revision' '0'] ['authority_epoch' '1'] ['operation' 'project.create']])
  ?>  ?=([%o *] other-wire)
  =/  other-pay  (object ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' 'Other'] ['project_key' 'OTHER'] ['preset' 'general']])
  =/  other-command  (decode:stead-team-codec (canonical [%o (~(put by p.other-wire) 'payload' other-pay)]))
  =/  a  (apply-command:stead-team initial alice make-project 2.000)
  =/  ab  (apply-command:stead-team next.a alice other-command 2.000)
  =/  b  (apply-command:stead-team initial alice other-command 2.000)
  =/  ba  (apply-command:stead-team next.b alice make-project 2.000)
  =/  left  (migrate next.ab)
  =/  right  (migrate next.ba)
  =/  left-boundary  (need migration.product.left)
  =/  right-boundary  (need migration.product.right)
  %-  expect
  !>  ?&  =(legacy original-work)
          =(journal.data.legacy journal.data.db)
          =(receipts.data.legacy receipts.data.db)
          =(registry.legacy predecessor-registry.boundary)
          =(boundary expected)
          =((lent journal.data.legacy) journal-count.boundary)
          =((~(got by heads.boundary) (id 100)) digest.i.journal.data.legacy)
          !=(fingerprint.boundary fingerprint.changed)
          =(2 journal-count.left-boundary)
          =(journal-count.left-boundary journal-count.right-boundary)
          =(heads.left-boundary heads.right-boundary)
          =(configuration-digest.left-boundary configuration-digest.right-boundary)
          !=(timeline-digest.left-boundary timeline-digest.right-boundary)
          !=(fingerprint.left-boundary fingerprint.right-boundary)
      ==
++  test-product-migrate-legacy-blocked-done-and-assignee-stay-explicit
  =/  converted  (migrate legacy)
  =/  metadata  (~(got by works.product.converted) [(id 100) (id 101)])
  =/  known  (need legacy-blocked.metadata)
  =/  assigned  (need legacy-assignee.metadata)
  =/  current  (~(got by works.data.db.converted) [(id 100) (id 101)])
  =/  unknown  (~(got by works.product.converted) [(id 100) (id 108)])
  =/  unknown-row  (~(got by works.data.db.converted) [(id 100) (id 108)])
  =/  completed  (~(got by works.product.converted) [(id 100) (id 109)])
  =/  reuse  (apply-command:stead-team legacy alice (command 315 110 0 'work.create' work-fields) 1.016)
  =/  config  (need (parse-result configuration))
  ?>  ?=([%o *] config)
  =/  people  (~(got by p.config) 'bindings')
  ?>  ?=([%o *] people)
  =/  changed  (~(put by p.config) 'expected_revision' [%s '1'])
  =.  changed  (~(put by changed) 'bindings' [%o (~(del by p.people) '~nec')])
  =/  departed  (configure:stead-team legacy (canonical [%o changed]) ~zod 2.000)
  =/  after-departure  (migrate departed)
  =/  later  (~(got by works.product.after-departure) [(id 100) (id 101)])
  =/  unavailable  (need legacy-assignee.later)
  %-  expect
  !>  ?&  =('blocked' raw-status.known)  =((some 'in_progress') prior-status.known)
          !resolved.known  =('' raw-reason.known)
          =('in_progress' (field data.current 'status'))
          ?=(~ prior-status:(need legacy-blocked.unknown))
          =('legacy-blocked' (field data.unknown-row 'status'))
          =(%legacy completion-basis.completed)
          =(principal.identity.bob principal.assigned)  =('Bob' display.assigned)
          =(%registry display-source.assigned)  !resolved.assigned
          =(%unavailable display-source.unavailable)  =('' display.unavailable)
          =(principal.assigned principal.unavailable)
          =((id 306) request.assigned)  !=('' target.assigned)
          =('' (field data.current 'owner_principal_id'))
          =('' (field data.current 'worker_principal_id'))
          !(~(has by data.current) 'assignee_principal_id')
          (~(has in tombs.db.converted) [(id 100) 'work' '' (id 110)])
          =(legacy next.reuse)
          =('revision_conflict' (result-field response.reuse 'error'))
      ==
++  test-product-migrate-rejects-unmatched-comments-and-damaged-prefix
  =/  current  (~(got by works.data.legacy) [(id 100) (id 101)])
  =/  notes  (discussion:stead-team data.current)
  ?>  ?=(^ notes)
  ?>  ?=([%o *] i.notes)
  =/  forged  [%o (~(put by p.i.notes) 'body' [%s 'Unmatched replacement'])]
  =/  bad-data  (~(put by data.current) 'discussion' [%a [forged t.notes]])
  =/  changed  legacy(data data.legacy(works (~(put by works.data.legacy) [(id 100) (id 101)] current(data bad-data))))
  =/  missing  legacy(data data.legacy(journal ~))
  =/  bad-comment  (finished changed)
  =/  bad-prefix  (finished missing)
  %-  expect
  !>  ?&  =(%invalid phase.bad-comment)  =(%invalid phase.bad-prefix)
          ?=(~ (result:stead-product-migrate bad-comment))
          ?=(~ (result:stead-product-migrate bad-prefix))
          =(changed converted.bad-comment)  =(missing converted.bad-prefix)
      ==
++  test-product-migrate-batches-before-exposing-converted-work
  =/  many
    =/  state  db
    =/  count=@ud  0
    |-
    ?:  =(33 count)  state
    =/  accepted  (apply-command:stead-team state alice (command (add 400 count) (add 500 count) 0 'work.create' work-fields) (add 2.000 count))
    ?>  =('accepted' (result-field response.accepted 'status'))
    $(state next.accepted, count +(count))
  =/  start  (begin:stead-product-migrate many ~zod)
  =/  first  (step:stead-product-migrate start)
  =/  completed  (finished many)
  =/  converted  (need (result:stead-product-migrate completed))
  %-  expect
  !>  ?&  =(%validate phase.first)
          ?=(~ (result:stead-product-migrate start))
          ?=(~ (result:stead-product-migrate first))
          =(many converted.first)
          =(34 (lent ~(tap by works.product.converted)))
          =(%valid phase.completed)
      ==
--

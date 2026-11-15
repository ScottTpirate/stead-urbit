/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views
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
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (field p.value name)
++  indexed
  |=  db=state:stead-team
  ^-  state:stead-projection
  (batch:stead-projection db (begin:stead-projection db *state:stead-projection))
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
=/  project  (apply-command:stead-team initial alice make-project 1.001)
=/  grant-editor  (command 302 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' principal.identity.bob] ['role' 'contributor'] ['expires_at_ms' '5000']])
=/  editor  (apply-command:stead-team next.project alice grant-editor 1.002)
=/  grant-reader  (command 303 100 2 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' principal.identity.carol] ['role' 'reader'] ['expires_at_ms' '8000000']])
=/  reader  (apply-command:stead-team next.editor alice grant-reader 1.003)
=/  work-fields  ~[['title' 'Draft'] ['description' 'Notes'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
=/  created  (apply-command:stead-team next.reader alice (command 304 101 0 'work.create' work-fields) 1.004)
=/  assign  (command 305 101 1 'work.assign' ~[['assignee_principal_id' principal.identity.bob]])
=/  assigned  (apply-command:stead-team next.created alice assign 1.005)
=/  db  next.assigned
=/  revoke  (command 306 100 3 'policy.revoke' ~[['grant_id' (id 501)]])
=/  revoked  (apply-command:stead-team db alice revoke 1.006)
=/  roster=query:stead-team-codec  [(id 601) 'assignees' (id 100) '' '' '' '']
=/  listing=query:stead-team-codec  [(id 602) 'work' (id 100) '' '' '' '']
|%
++  test-work-assignment-persists-through-edits-and-replay
  =/  update  (apply-command:stead-team db bob (command 307 101 2 'work.update' work-fields) 1.007)
  =/  item  (~(got by works.data.next.update) [(id 100) (id 101)])
  =/  view  (indexed next.update)
  %-  expect
  !>  ?&  =('2' (result-field response.assigned 'resource_revision'))
          =(assigned (apply-command:stead-team db alice assign 1.006))
          =('3' (result-field response.update 'resource_revision'))
          =(principal.identity.bob (field data.item 'assignee_principal_id'))
          =(revision.item 3)
          (ready:stead-projection next.update view)
          =((some next.update) (result:stead-restore (step:stead-restore (begin:stead-restore next.update ~zod))))
      ==
++  test-work-assignment-roster-and-search-are-project-scoped
  =/  view  (indexed db)
  =/  choices  (rows:stead-views db visible.view alice roster 1.010)
  =/  search  listing(kind 'search', search 'Bob')
  =/  match  (rows:stead-views db visible.view carol search 1.010)
  =/  found  (snag 0 match)
  %-  expect
  !>  ?&  =(2 (lent choices))
          (lien choices |=([id=@t fields=object-map] =('~nec' (field fields 'identity_ship'))))
          (authorized:stead-views db bob roster 1.010)
          !(authorized:stead-views db carol roster 1.010)
          !(authorized:stead-views db alice roster(project (id 999)) 1.010)
          =(principal.identity.bob (field fields.found 'assignee_principal_id'))
          =('Bob' (field fields.found 'assignee_display_name'))
          ?=(~ (rows:stead-views db visible.view carol search 5.000))
          !=((generation:stead-views db carol search 1.010) (generation:stead-views db carol search 5.000))
      ==
++  test-work-assignment-revocation-hides-name-and-allows-clearing
  =/  after  next.revoked
  =/  view  (indexed after)
  =/  found  (snag 0 (rows:stead-views after visible.view carol listing 1.010))
  =/  rejected  (apply-command:stead-team after alice (command 307 101 2 'work.assign' ~[['assignee_principal_id' principal.identity.bob]]) 1.010)
  =/  cleared  (apply-command:stead-team after alice (command 308 101 2 'work.assign' ~[['assignee_principal_id' '']]) 1.011)
  =/  item  (~(got by works.data.next.cleared) [(id 100) (id 101)])
  %-  expect
  !>  ?&  =('accepted' (result-field response.revoked 'status'))
          =(principal.identity.bob (field fields.found 'assignee_principal_id'))
          !(~(has by fields.found) 'assignee_display_name')
          =('denied_or_not_found' (result-field response.rejected 'error'))
          =(after next.rejected)
          =('3' (result-field response.cleared 'resource_revision'))
          !(~(has by data.item) 'assignee_principal_id')
          =((some next.cleared) (result:stead-restore (step:stead-restore (begin:stead-restore next.cleared ~zod))))
      ==
++  test-work-assignment-rejects-stale-and-ineligible-actors
  =/  stale  (apply-command:stead-team db alice (command 307 101 1 'work.assign' ~[['assignee_principal_id' '']]) 1.010)
  =/  target-reader  (apply-command:stead-team db alice (command 308 101 2 'work.assign' ~[['assignee_principal_id' principal.identity.carol]]) 1.011)
  =/  actor-reader  (apply-command:stead-team db carol (command 309 101 2 'work.assign' ~[['assignee_principal_id' '']]) 1.012)
  %-  expect
  !>  ?&  =('revision_conflict' (result-field response.stale 'error'))
          =('denied_or_not_found' (result-field response.target-reader 'error'))
          =('denied_or_not_found' (result-field response.actor-reader 'error'))
          =(db next.stale)  =(db next.target-reader)  =(db next.actor-reader)
      ==
++  test-work-assignment-at-creation-is-one-accepted-edit
  =/  payload  (weld work-fields ~[['assignee_principal_id' principal.identity.bob]])
  =/  create  (command 307 108 0 'work.create' payload)
  =/  done  (apply-command:stead-team db alice create 1.010)
  =/  item  (~(got by works.data.next.done) [(id 100) (id 108)])
  =/  view  (indexed next.done)
  %-  expect
  !>  ?&  =('accepted' (result-field response.done 'status'))
          =('1' (result-field response.done 'resource_revision'))
          =(done (apply-command:stead-team next.done alice create 1.011))
          =(principal.identity.bob (field data.item 'assignee_principal_id'))
          =(revision.item 1)
          (ready:stead-projection next.done view)
          =((some next.done) (result:stead-restore (step:stead-restore (begin:stead-restore next.done ~zod))))
      ==
++  test-work-assignment-at-creation-denies-ineligible-targets-and-readers
  =/  to-reader  (command 307 108 0 'work.create' (weld work-fields ~[['assignee_principal_id' principal.identity.carol]]))
  =/  to-editor  (command 308 108 0 'work.create' (weld work-fields ~[['assignee_principal_id' principal.identity.bob]]))
  =/  target-reader  (apply-command:stead-team db alice to-reader 1.010)
  =/  actor-reader  (apply-command:stead-team db carol to-editor 1.010)
  =/  target-expired  (apply-command:stead-team db alice to-editor 5.000)
  =/  target-revoked  (apply-command:stead-team next.revoked alice to-editor 1.010)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.target-reader 'error'))
          =('denied_or_not_found' (result-field response.actor-reader 'error'))
          =('denied_or_not_found' (result-field response.target-expired 'error'))
          =('denied_or_not_found' (result-field response.target-revoked 'error'))
          =(db next.target-reader)  =(db next.actor-reader)  =(db next.target-expired)
          =(next.revoked next.target-revoked)
      ==
++  test-work-assignment-at-creation-wire-shape
  =/  empty-assignee  (weld work-fields ~[['assignee_principal_id' '']])
  =/  malformed-assignee  (weld work-fields ~[['assignee_principal_id' '~nec']])
  =/  update-assignee  (weld work-fields ~[['assignee_principal_id' principal.identity.bob]])
  =/  empty  (mule |.((command 307 108 0 'work.create' empty-assignee)))
  =/  malformed  (mule |.((command 307 108 0 'work.create' malformed-assignee)))
  =/  update  (mule |.((command 307 101 2 'work.update' update-assignee)))
  %-  expect
  !>  &(?=([%| *] empty) ?=([%| *] malformed) ?=([%| *] update))
--

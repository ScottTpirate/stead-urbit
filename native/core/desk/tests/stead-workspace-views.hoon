/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-work-contract, stead-updates, stead-update-codec, stead-update-security, stead-session
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  command
  |=  [req=@ud project=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  value
    (object ~[['protocol' 'stead.command/3'] ['request_id' (id req)] ['project_id' (id project)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
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
  =/  view  (begin:stead-projection db *state:stead-projection)
  |-
  ?:  (ready:stead-projection db view)  view
  ?>  &(!poisoned.view rebuilding.view)
  $(view (batch:stead-projection db view))
++  apply
  |=  [db=state:stead-team actor=authentication:stead-team cmd=command:stead-codec now=@ud]
  ^-  state:stead-team
  =/  out  (apply-command:stead-team db actor cmd now)
  ?>  =('accepted' (result-field response.out 'status'))
  next.out
++  new-project
  |=  [db=state:stead-team actor=authentication:stead-team req=@ud project=@ud title=@t key=@t]
  ^-  state:stead-team
  (apply db actor (command req project project 0 'project.create' ~[['organization_id' (id 5)] ['owning_team_id' (id 6)] ['title' title] ['project_key' key] ['preset' 'general']]) 1.002)
++  query-wire
  |=  query=query:stead-team-codec
  ^-  @t
  (canonical (object ~[['protocol' 'stead.query/3'] ['request_id' request.query] ['kind' kind.query] ['project_id' project.query] ['container_id' container.query] ['resource_id' resource.query] ['search' search.query] ['cursor' cursor.query]]))
++  rejected-query
  |=  query=query:stead-team-codec
  ^-  ?
  =/  out  (mule |.((decode-query:stead-team-codec (query-wire query))))
  ?=([%| *] out)
++  markdown
  |=  [document=@ud state=@t content=@t]
  ^-  @t
  (cat 3 (header:stead-team (id document) state) content)
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
=/  garden  (new-project initial alice 301 100 'Garden' 'GARDEN')
=/  workshop  (new-project garden alice 302 200 'Workshop' 'SHOP')
=/  private-project  (new-project workshop alice 303 300 'Hidden project' 'HIDDEN')
=/  granted  (apply private-project alice (command 304 100 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' principal.identity.bob] ['role' 'contributor'] ['expires_at_ms' '8000000']]) 1.003)
=/  reader  (apply granted alice (command 305 200 200 1 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' principal.identity.bob] ['role' 'reader'] ['expires_at_ms' '5000']]) 1.004)
=/  work-fields  ~[['title' 'Visible work'] ['description' 'Shared context'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]
=/  first-work  (apply reader alice (command 306 100 101 0 'work.create' [['assignee_principal_id' principal.identity.bob] work-fields]) 1.005)
=/  second-work  (apply first-work alice (command 307 200 101 0 'work.create' work-fields) 1.006)
=/  secret-work  (apply second-work alice (command 308 300 301 0 'work.create' ~[['title' 'SECRET-PROJECT-CANARY'] ['description' 'Hidden'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]) 1.007)
=/  alice-box  (apply secret-work alice (command 309 100 400 0 'container.create' ~[['title' 'Alice private'] ['visibility' 'private']]) 1.008)
=/  alice-doc  (apply alice-box alice (command 310 100 401 0 'document.save' ~[['container_id' (id 400)] ['markdown' (markdown 401 'draft' 'SECRET-DOC-CANARY')]]) 1.009)
=/  bob-box  (apply alice-doc bob (command 311 100 410 0 'container.create' ~[['title' 'Bob private'] ['visibility' 'private']]) 1.010)
=/  bob-doc  (apply bob-box bob (command 312 100 411 0 'document.save' ~[['container_id' (id 410)] ['markdown' (markdown 411 'draft' 'BOB-OWN-DOCUMENT')]]) 1.011)
=/  shared-box  (apply bob-doc alice (command 313 100 420 0 'container.create' ~[['title' 'Shared docs'] ['visibility' 'shared']]) 1.012)
=/  db  (apply shared-box alice (command 314 100 421 0 'document.save' ~[['container_id' (id 420)] ['markdown' (markdown 421 'published' 'Visible shared document')]]) 1.013)
=/  search=query:stead-team-codec  [(id 600) 'workspace-search' '' '' '' '' '']
=/  mine  search(kind 'my-work')
=/  view  (indexed db)
=/  grown
  =/  state  db
  =/  count=@ud  0
  |-
  ?:  =(count 22)  state
  =/  cmd  (command (add 700 count) 100 (add 800 count) 0 'work.create' work-fields)
  $(state (apply state alice cmd (add 2.000 count)), count +(count))
|%
++  test-workspace-closed-empty-scope-grammar
  ^-  tang
  ?>  =(search (decode-query:stead-team-codec (query-wire search)))
  ?>  =(mine (decode-query:stead-team-codec (query-wire mine)))
  ?>  =(search(search 'Visible') (decode-query:stead-team-codec (query-wire search(search 'Visible'))))
  ?>  (rejected-query search(project (id 100)))
  ?>  (rejected-query search(container (id 400)))
  ?>  (rejected-query search(resource (id 401)))
  ?>  (rejected-query mine(search 'Visible'))
  ?>  (rejected-query search(search (rap 3 (reap 129 'x'))))
  ?>  (rejected-query search(kind 'workspace-inbox'))
  ~
++  test-workspace-per-resource-access-and-independent-project-identity
  ^-  tang
  =/  rows  (rows:stead-views db visible.view bob search 3.000)
  ?>  =(4 (lent rows))
  ?>  =(4 (lent ~(tap in (silt (turn rows |=([key=@t value=object-map] key))))))
  ?>  (levy rows |=([key=@t value=object-map] (~(has in (silt ~[(id 100) (id 200)])) (field value 'project_id'))))
  =/  output  (execute:stead-views db view *state:stead-views bob search 3.000 1)
  ?>  !(contains:stead-views 'SECRET-' response.output)
  ?>  !(contains:stead-views 'Hidden project' response.output)
  ?>  (contains:stead-views 'BOB-OWN-DOCUMENT' response.output)
  ?>  (contains:stead-views 'Workshop' response.output)
  =/  owner  (execute:stead-views db view *state:stead-views alice search 3.000 2)
  ?>  !(contains:stead-views 'BOB-OWN-DOCUMENT' response.owner)
  ?>  (contains:stead-views 'SECRET-DOC-CANARY' response.owner)
  =/  outsider  (execute:stead-views db view *state:stead-views carol search 3.000 3)
  ?>  =(0 (result-count response.outsider))
  =/  invalid  (execute:stead-views db view *state:stead-views bob(identity identity.bob(binding 'not-a-binding')) search 3.000 4)
  ?>  =('denied_or_not_found' (result-field response.invalid 'error'))
  ~
++  test-workspace-assigned-to-me-and-current-completion-filter
  ^-  tang
  =/  found  (rows:stead-views db visible.view bob mine 3.000)
  ?>  =(1 (lent found))
  ?>  =((id 100) (field fields.i.found 'project_id'))
  ?>  =((id 101) (field fields.i.found 'resource_id'))
  =/  done  (apply db alice (command 315 100 101 1 'work.update' ~[['title' 'Visible work'] ['description' 'Shared context'] ['type' 'task'] ['status' 'done'] ['priority' 'none']]) 3.001)
  ?>  ?=(~ (rows:stead-views done visible:(indexed done) bob mine 3.002))
  =/  canceled  (apply db alice (command 316 100 101 1 'work.update' ~[['title' 'Visible work'] ['description' 'Shared context'] ['type' 'task'] ['status' 'canceled'] ['priority' 'none']]) 3.001)
  ?>  ?=(~ (rows:stead-views canceled visible:(indexed canceled) bob mine 3.002))
  ?>  ?=(~ (rows:stead-views db visible.view alice mine 3.000))
  ~
++  test-workspace-private-writes-do-not-signal-other-members
  ^-  tang
  =/  hidden  (apply db alice (command 315 100 401 1 'document.save' ~[['container_id' (id 400)] ['markdown' (markdown 401 'draft' 'SECRET-DOC-UPDATED')]]) 3.001)
  ?>  =((generation:stead-views db bob search 3.000) (generation:stead-views hidden bob search 3.002))
  ?>  !=((generation:stead-views db alice search 3.000) (generation:stead-views hidden alice search 3.002))
  =/  foreign  (apply db alice (command 316 300 302 0 'work.create' work-fields) 3.001)
  ?>  =((generation:stead-views db bob search 3.000) (generation:stead-views foreign bob search 3.002))
  ~
++  test-workspace-pagination-binds-search-principal-and-visible-generation
  ^-  tang
  =/  first  (execute:stead-views grown (indexed grown) *state:stead-views bob search 3.000 10)
  ?>  =(20 (result-count response.first))
  =/  cursor  (result-field response.first 'cursor')
  ?>  !=('' cursor)
  =/  follow  search(cursor cursor)
  =/  foreign  (execute:stead-views grown (indexed grown) next.first alice follow 3.001 11)
  ?>  =('stale_cursor' (result-field response.foreign 'error'))
  =/  different  (execute:stead-views grown (indexed grown) next.first bob follow(search 'Visible') 3.001 12)
  ?>  =('stale_cursor' (result-field response.different 'error'))
  =/  hidden  (apply grown alice (command 315 100 401 1 'document.save' ~[['container_id' (id 400)] ['markdown' (markdown 401 'draft' 'SECRET-DOC-UPDATED')]]) 3.001)
  =/  second  (execute:stead-views hidden (indexed hidden) next.first bob follow 3.002 13)
  ?>  =(6 (result-count response.second))
  ?>  =('' (result-field response.second 'cursor'))
  =/  expired  (execute:stead-views grown (indexed grown) next.first bob follow 5.000 14)
  ?>  =('stale_cursor' (result-field response.expired 'error'))
  =/  revoked  (apply grown alice (command 316 100 100 2 'policy.revoke' ~[['grant_id' (id 501)]]) 3.001)
  =/  refused  (execute:stead-views revoked (indexed revoked) next.first bob follow 3.002 15)
  ?>  =('stale_cursor' (result-field response.refused 'error'))
  ~
++  test-workspace-queued-updates-private-isolation-and-revocation
  ^-  tang
  =/  input=envelope:stead-update-codec  [(id 900) 'open' '' '' search(request (id 900))]
  =/  first  (execute:stead-updates db view *state:stead-session *state:stead-updates *state:stead-views bob input 3.000 20)
  ?>  =('watching' (result-field response.first 'status'))
  =/  hidden  (apply db alice (command 315 100 401 1 'document.save' ~[['container_id' (id 400)] ['markdown' (markdown 401 'draft' 'SECRET-DOC-UPDATED')]]) 3.001)
  =/  quiet  (advance:stead-updates hidden *state:stead-session next.first pages.first 3.002)
  ?>  =(next.first next.quiet)
  ?>  =(pages.first pages.quiet)
  =/  visible  (apply hidden bob (command 316 100 101 1 'work.comment' ~[['body' 'Visible change']]) 3.003)
  =/  queued  (advance:stead-updates visible *state:stead-session next.quiet pages.quiet 3.004)
  ?>  !=(next.quiet next.queued)
  =/  revoked  (apply visible alice (command 317 100 100 2 'policy.revoke' ~[['grant_id' (id 501)]]) 3.005)
  =/  poll=envelope:stead-update-codec  [(id 901) 'poll' (result-field response.first 'watch_id') (result-field response.first 'cursor') [(id 901) '' '' '' '' '' '']]
  =/  expired  (execute:stead-updates visible (indexed visible) *state:stead-session next.queued pages.queued bob poll 5.000 22)
  ?>  =('refresh_required' (result-field response.expired 'status'))
  ?>  ?=(~ watches.next.expired)
  ?>  ?=(~ streams.next.expired)
  ?>  ?=(~ cursors.pages.expired)
  ?>  !(contains:stead-views 'Visible change' response.expired)
  =/  refused  (execute:stead-updates revoked (indexed revoked) *state:stead-session next.queued pages.queued bob poll 3.006 21)
  ?>  =('refresh_required' (result-field response.refused 'status'))
  ?>  ?=(~ watches.next.refused)
  ?>  ?=(~ streams.next.refused)
  ?>  ?=(~ cursors.pages.refused)
  ?>  !(contains:stead-views 'Visible change' response.refused)
  ~
--

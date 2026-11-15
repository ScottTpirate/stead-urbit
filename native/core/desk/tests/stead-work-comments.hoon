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
=/  first  (command 305 101 1 'work.comment' ~[['body' 'Exact <text>']])
=/  posted  (apply-command:stead-team db bob first 1.006)
=/  read=query:stead-team-codec  [(id 601) 'comments' (id 100) '' (id 101) '' '']
|%
++  test-work-comments-attributed-ordered-and-preserved
  =/  edit  (apply-command:stead-team next.posted alice (command 306 101 2 'work.update' work-fields) 1.007)
  =/  again  (apply-command:stead-team next.edit alice (command 307 101 3 'work.comment' ~[['body' 'Second']]) 1.008)
  =/  view  (indexed next.again)
  =/  comments  (rows:stead-views next.again visible.view carol read 1.010)
  =/  one  (snag 0 comments)
  =/  two  (snag 1 comments)
  =/  detail  (snag 0 (rows:stead-views next.again visible.view carol read(kind 'work') 1.010))
  =/  listing  (snag 0 (rows:stead-views next.again visible.view carol read(kind 'work', resource '') 1.010))
  %-  expect
  !>  ?&  =('1' (result-field response.create 'resource_revision'))
          =('2' (result-field response.posted 'resource_revision'))
          =(posted (apply-command:stead-team next.posted bob first 1.007))
          =('4' (result-field response.again 'resource_revision'))
          =('Exact <text>' (field fields.one 'body'))
          =('~nec' (field fields.one 'identity_ship'))
          =(principal.identity.bob (field fields.one 'principal_id'))
          =('1006' (field fields.one 'accepted_at_ms'))
          =('2' id.one)  =('4' id.two)
          =('2' (field fields.detail 'comment_count'))
          !(~(has by fields.detail) 'discussion')
          !(~(has by fields.listing) 'comment_count')
          !(~(has by fields.listing) 'discussion')
          =((some next.again) (result:stead-restore (step:stead-restore (begin:stead-restore next.again ~zod))))
      ==
++  test-work-comments-authorize-current-ticket-access
  =/  denied  (apply-command:stead-team db carol first 1.010)
  =/  stale  (apply-command:stead-team next.posted alice first 1.011)
  =/  gone  (apply-command:stead-team next.posted alice (command 306 101 2 'work.delete' ~) 1.012)
  =/  retracted  (apply-command:stead-team next.gone bob (command 307 101 3 'work.comment' ~[['body' 'Hidden']]) 1.013)
  %-  expect
  !>  ?&  (authorized:stead-views next.posted carol read 1.010)
          !(authorized:stead-views next.posted carol read 5.000)
          !(authorized:stead-views next.posted alice read(project (id 998)) 1.010)
          !(authorized:stead-views next.posted alice read(resource (id 998)) 1.010)
          !(authorized:stead-views next.gone alice read 1.013)
          =('denied_or_not_found' (result-field response.denied 'error'))
          =('revision_conflict' (result-field response.stale 'error'))
          =('denied_or_not_found' (result-field response.retracted 'error'))
          =(db next.denied)  =(next.posted next.stale)  =(next.gone next.retracted)
      ==
++  test-work-comments-paginate-and-reject-stale-cursors
  =/  later
    =/  state  db
    =/  revision=@ud  1
    |-
    ?:  =(revision 33)  state
    =/  req  (command (add 310 revision) 101 revision 'work.comment' ~[['body' 'Comment']])
    =/  accepted  (apply-command:stead-team state alice req (add 2.000 revision))
    ?>  =('accepted' (result-field response.accepted 'status'))
    $(state next.accepted, revision +(revision))
  =/  view  (indexed later)
  =/  full  (command 343 101 33 'work.comment' ~[['body' 'Too many']])
  =/  rejected  (apply-command:stead-team later alice full 2.040)
  =/  first-page  (execute:stead-views later view *state:stead-views carol read 2.041 0xabc)
  =/  next-query  read(cursor (result-field response.first-page 'cursor'))
  =/  second  (execute:stead-views later view next.first-page carol next-query 2.042 0xabd)
  =/  edited  (apply-command:stead-team later alice (command 344 101 33 'work.update' work-fields) 2.043)
  =/  stale  (execute:stead-views next.edited (indexed next.edited) next.first-page carol next-query 2.044 0xabe)
  %-  expect
  !>  ?&  =('capacity_exceeded' (result-field response.rejected 'error'))
          =(later next.rejected)
          =(20 (result-count response.first-page))
          =(12 (result-count response.second))
          =('' (result-field response.second 'cursor'))
          =('stale_cursor' (result-field response.stale 'error'))
      ==
++  test-work-comments-require-exact-bounded-body
  =/  blank-body  (cat 3 9 10)
  =/  too-long  (rap 3 (reap 2.049 'a'))
  =/  forged  (mule |.((command 305 101 1 'work.comment' ~[['body' 'Wrong'] ['identity_ship' '~bus']])))
  =/  empty  (mule |.((command 305 101 1 'work.comment' ~[['body' '']])))
  %-  expect
  !>  ?&  (comment-body:stead-team-codec (cat 3 'Line' 10))
          !(comment-body:stead-team-codec blank-body)
          !(comment-body:stead-team-codec too-long)
          !(comment-body:stead-team-codec (cat 3 'Line' 13))
          ?=([%| *] forged)  ?=([%| *] empty)
      ==
--

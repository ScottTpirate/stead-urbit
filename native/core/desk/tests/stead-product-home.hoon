::  Pure lifecycle/carrier seam cases. The separate Gall rehearsal must prove
::  actual marks, sender/watch binding, full saved10 fields and bootstrap.
/+  *test, stead-codec, stead-team, stead-team-codec, stead-views, stead-product-home, stead-product-home-views, stead-product-query, stead-product-history, stead-product-state, stead-product-owner-codec
/=  fixture  /tests/stead-product-doc-history
=,  stead-codec
|%
++  finish
  |=  input=pair:stead-product-home
  ^-  pair:stead-product-home
  =/  source  (snapshot:stead-product-home input)
  =/  budget=@ud  1.024
  |-
  ?:  (ready:stead-product-home phase.input)  input
  ?>  &((gth budget 0) !(invalid:stead-product-home phase.input))
  ?>  =(source (snapshot:stead-product-home input))
  =/  saved=vase  !>(source)
  =/  copied  !<(target:stead-product-home (cue (jam saved)))
  ?>  =(source copied)
  $(input (step:stead-product-home input ~zod), budget (dec budget))
++  query
  |=  [kind=@t resource=@t cursor=@t]
  ^-  query:stead-team-codec
  [(id:fixture 940) kind (id:fixture 100) '' resource '' cursor]
++  read
  |=  [state=state:stead-product-history actor=authentication:stead-team kind=@t resource=@t]
  ^-  result:stead-views
  (execute:stead-product-home-views state *state:stead-views actor (query kind resource '') 2.300 19)
++  value
  |=  raw=@t
  ^-  object-map
  =/  parsed  (need (parse-result raw))
  ?>  ?=([%o *] parsed)
  p.parsed
++  child
  |=  [obj=object-map key=@t]
  ^-  object-map
  =/  found  (~(got by obj) key)
  ?>  ?=([%o *] found)
  p.found
++  first-row
  |=  raw=@t
  ^-  object-map
  (child (child (value raw) 'rows') '0')
++  test-product-home-migration-keeps-pristine-target-until-publish
  =/  source=target:stead-product-home  [%predecessor next.private-box:fixture]
  =/  started  (begin:stead-product-home source ~zod)
  =/  once  (step:stead-product-home started ~zod)
  =/  result  (finish once)
  =/  restarted  (finish (begin:stead-product-home (snapshot:stead-product-home once) ~zod))
  %-  expect
  !>  ?&  =(empty:stead-team db.started)
          =(source (snapshot:stead-product-home started))
          =(source (snapshot:stead-product-home once))
          =(result restarted)
          =(baseline:fixture (current:stead-product-home result))
      ==
++  test-product-home-restore-keeps-exact-target-and-completion
  =/  source=target:stead-product-home  [%product next.completed:fixture]
  =/  started  (begin:stead-product-home source ~zod)
  =/  result  (finish started)
  =/  saved  (snapshot:stead-product-home result)
  %-  expect
  !>  ?&  =(empty:stead-team db.started)
          =(source (snapshot:stead-product-home started))
          =(source saved)
          =(next.completed:fixture (current:stead-product-home result))
          =(result (finish (begin:stead-product-home saved ~zod)))
      ==
++  test-product-home-dispatches-exact-doc-review-accept-complete
  =/  start  (publish:stead-product-home prepared:fixture)
  =/  submitted  (command:stead-product-home start alice:fixture canonical-bytes.submit-command:fixture 2.200)
  =/  request  (action:fixture (current:stead-product-home next.submitted) 751 'change.request-changes')
  =/  requested  (command:stead-product-home next.submitted bob:fixture canonical-bytes.request 2.201)
  =/  revision  (submission:fixture (current:stead-product-home next.requested) 752 2 doc-target:fixture revised-markdown:fixture)
  =/  revised  (command:stead-product-home next.requested alice:fixture canonical-bytes.revision 2.202)
  =/  approval  (action:fixture (current:stead-product-home next.revised) 753 'change.approve')
  =/  approved  (command:stead-product-home next.revised bob:fixture canonical-bytes.approval 2.203)
  =/  accepted  (command:stead-product-home next.approved alice:fixture canonical-bytes.accept-command:fixture 2.204)
  =/  completed  (command:stead-product-home next.accepted alice:fixture canonical-bytes.complete-command:fixture 2.205)
  =/  again  (command:stead-product-home next.completed alice:fixture canonical-bytes.accept-command:fixture 2.206)
  %-  expect
  !>  ?&  =(next.completed:fixture (current:stead-product-home next.completed))
          =(response.accepted:fixture response.accepted)
          =(response.completed:fixture response.completed)
          =(response.accepted response.again)  =(next.completed next.again)
      ==
++  test-product-home-legacy-work-and-inactive-cached-retry-denied
  =/  start  (publish:stead-product-home next.completed:fixture)
  =/  legacy  (command:fixture 941 101 1 'work.update' work-fields:fixture)
  =/  denied  (command:stead-product-home start alice:fixture canonical-bytes.legacy 2.300)
  =/  disable  (owner-command:fixture 942 'principal.declare' 2 ~[['principal_id' (id:fixture 102)] ['kind' 'person'] ['display_name' 'Alice'] ['active' 'no']])
  =/  disabled  (owner-command:stead-product-home start canonical-bytes.disable ~zod ~zod 2.301)
  =/  retry  (command:stead-product-home next.disabled alice:fixture canonical-bytes.complete-command:fixture 2.302)
  =/  outsider  (mule |.((owner-command:stead-product-home start canonical-bytes.disable ~zod ~bus 2.303)))
  %-  expect
  !>  ?&  =('rejected' (field (value response.denied) 'status'))
          =(start next.denied)
          =('denied_or_not_found' (field (value response.retry) 'error'))
          =(next.disabled next.retry)  ?=(%| -.outsider)
      ==
++  test-product-home-principal-roster-real-kinds-and-reader-fence
  =/  source  next.accepted:fixture
  =/  selected  (read source alice:fixture 'principals' '')
  =/  entries  ~(tap by (child (value response.selected) 'rows'))
  =/  alice  (first-row response.selected)
  =/  carol
    =/  matches
      %+  skim  entries
      |=  [key=@t item=json]
      ?>  ?=([%o *] item)
      =((id:fixture 104) (field p.item 'principal_id'))
    ?>  ?=(^ matches)
    ?>  ?=([%o *] q.i.matches)
    p.q.i.matches
  =/  denied  (read source carol:fixture 'principals' '')
  %-  expect
  !>  ?&  =(3 (lent entries))
          =(6 (lent ~(tap by alice)))
          =('person' (field alice 'principal_kind'))
          =('maintainer' (field alice 'project_role'))
          =('unresolved' (field carol 'principal_kind'))
          =('reader' (field carol 'project_role'))
          =('denied_or_not_found' (field (value response.denied) 'error'))
      ==
++  test-product-home-completion-advice-requires-current-exact-proof
  =/  approved  (read next.approved:fixture alice:fixture 'completion' (id:fixture 111))
  =/  accepted  (read next.accepted:fixture alice:fixture 'completion' (id:fixture 111))
  =/  changed-command  (command:fixture 943 201 2 'document.save' ~[['container_id' (id:fixture 200)] ['markdown' markdown:fixture]])
  =/  changed  (apply-legacy:stead-product-history next.accepted:fixture alice:fixture changed-command 2.210)
  =/  stale  (read next.changed alice:fixture 'completion' (id:fixture 111))
  =/  empty  (read next.created:fixture alice:fixture 'completion' (id:fixture 111))
  %-  expect
  !>  ?&  =('no' (field (first-row response.approved) 'ready'))
          =('yes' (field (first-row response.accepted) 'ready'))
          =(7 (lent ~(tap by (first-row response.accepted))))
          =('2' (field (first-row response.accepted) 'execution_contract_revision'))
          =('no' (field (first-row response.stale) 'ready'))
          =('required-outcomes-unconfirmed' (field (first-row response.stale) 'reason'))
          =('human-note-required' (field (first-row response.empty) 'reason'))
      ==
++  test-product-home-new-query-scopes-and-cursor-shapes-are-closed
  =/  principals  (query 'principals' '' '')
  =/  complete  (query 'completion' (id:fixture 111) '')
  =/  wrong  (mule |.((decode:stead-product-query (bytes:stead-product-query principals(resource (id:fixture 111))))))
  =/  cursor  (mule |.((decode:stead-product-query (bytes:stead-product-query complete(cursor (hex 64 0))))))
  =/  search  (mule |.((decode:stead-product-query (bytes:stead-product-query principals(kind 'search')))))
  %-  expect
  !>  ?&  =(principals (decode:stead-product-query (bytes:stead-product-query principals)))
          =(complete (decode:stead-product-query (bytes:stead-product-query complete)))
          ?=(%| -.wrong)  ?=(%| -.cursor)  ?=(%| -.search)
      ==
++  test-product-home-owner-configuration-enters-same-restorable-history
  =/  source  (publish:stead-product-home next.completed:fixture)
  =/  config  (member-config:fixture configuration:fixture 1 2 'yes')
  =/  command  (owner-command:fixture 944 'home.configure' 1 ~[['configuration' config]])
  =/  changed  (owner-command:stead-product-home source canonical-bytes.command ~zod ~zod 2.300)
  =/  target  (snapshot:stead-product-home next.changed)
  =/  restored  (finish (begin:stead-product-home target ~zod))
  =/  old-actor  (read (current:stead-product-home restored) bob:fixture 'principals' '')
  %-  expect
  !>  ?&  =('accepted' (field (value response.changed) 'status'))
          =(next.changed restored)
          =('denied_or_not_found' (field (value response.old-actor) 'error'))
      ==
--

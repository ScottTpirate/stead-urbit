/+  *test, stead-codec, stead-git, stead-session, stead-code-credentials, stead-code-store, stead-code-review-home, stead-code-delivery, stead-code-review, stead-code-build-home, stead-code-delivery-export
=/  scope=scope:stead-code-credentials  [~zod '019939ba-4000-7000-8000-000000000100' '019939ba-4000-7000-8000-000000000200' 1]
=/  actor=actor:stead-session  [~bus '019939ba-4000-7000-8000-000000001001' '019939ba-4000-7000-8000-000000002001' 1 & 1.000.000]
=/  worker=actor:stead-session  [~nec '019939ba-4000-7000-8000-000000001002' '019939ba-4000-7000-8000-000000002002' 1 & 1.000.000]
=/  request=@t  '019939ba-4000-7000-8000-000000000300'
=/  work=@t  '019939ba-4000-7000-8000-000000000400'
=/  proposal=@t  '019939ba-4000-7000-8000-000000000500'
=/  job-id=@t  '019939ba-4000-7000-8000-000000000600'
=/  main=@t  'refs/heads/main'
=/  tag=@t  'refs/tags/one'
=/  upcoming=@t  'refs/heads/upcoming'
=/  token=@t  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
=/  protected=(set @t)  (silt ~[main upcoming])
|%
++  repo
  ^-  state:stead-code-store
  =/  empty  (empty:stead-code-store scope)
  =/  receipt=receipt:stead-code-store  [1 scope request token actor 1 ~[[main 0x0 0x1] [tag 0x0 0x2]]]
  empty(revision 1, refs (malt ~[[main 0x1] [tag 0x2]]), journal ~[request], receipts (malt ~[[request receipt]]))
++  board
  (empty:stead-code-review-home scope)
++  report
  |=  [offset=@ud snapshot=@t]
  (page:stead-code-delivery-export repo board *state:stead-code-build-home protected offset snapshot)
++  example-job
  |=  data=octets:stead-git
  ^-  build:stead-code-delivery
  =/  item=proposal:stead-code-review
    [proposal principal.actor [project.scope repository.scope main] work [1 1 0x0 0x1]]
  =/  recipe  recipe:stead-code-build-home
  =/  digest  (digest:stead-code-build-home data)
  [job-id actor item token recipe %finished [worker 1 1.000] [token recipe digest %passed]]
++  test-audit-empty-terminal
  =/  got  (page:stead-code-delivery-export (empty:stead-code-store scope) board *state:stead-code-build-home ~ 0 '')
  ?>  ?=(%& -.got)
  =/  correct=?
    ?&  ?=(~ next.p.got)
        =(0 total.p.got)
        =('' records.p.got)
        =('6d016f542cbbf05531525555e8e2572455d1161a0462cc0ce93528870ae56459' snapshot.p.got)
    ==
  (expect !>(correct))
++  test-audit-four-record-pagination
  =/  first  (report 0 '')
  ?>  ?=(%& -.first)
  =/  second  (report 4 snapshot.p.first)
  ?>  ?=(%& -.second)
  =/  correct=?
    ?&  =([~ 4] next.p.first)
        ?=(~ next.p.second)
        =(7 total.p.first)
        =(7 total.p.second)
        =(snapshot.p.first snapshot.p.second)
        =(header.p.first header.p.second)
        !=(records.p.first records.p.second)
    ==
  (expect !>(correct))
++  test-audit-rejects-unbound-offset
  (expect !>(=([%| %invalid-cursor] (report 4 ''))))
++  test-audit-page-rejects-protection-change
  =/  first  (report 0 '')
  ?>  ?=(%& -.first)
  =/  changed  (page:stead-code-delivery-export repo board *state:stead-code-build-home (silt ~[main]) 4 snapshot.p.first)
  (expect !>(=([%| %snapshot-changed] changed)))
++  test-audit-artifact-base64-exact
  =/  data=octets:stead-git  [3 0x42.4100]
  =/  job  (example-job data)
  =/  extras=state:stead-code-build-home  [(malt ~[[job-id worker]]) (malt ~[[job-id data]])]
  =/  row  (build-row:stead-code-delivery-export extras job)
  =/  parsed  (parse:stead-codec row)
  ?>  ?=([~ %o *] parsed)
  =/  bytes  (field:stead-codec p.u.parsed 'artifact_base64')
  =/  found  (field:stead-codec p.u.parsed 'output_sha256')
  (expect !>(&(=('AEFC' bytes) =((digest:stead-code-build-home data) found))))
++  test-audit-rejects-artifact-hash-mismatch
  =/  job  (example-job [3 0x42.4100])
  =/  saved=state:stead-code-review-home  board
  =.  builds.board.saved  (malt ~[[job-id job]])
  =/  extras=state:stead-code-build-home  [(malt ~[[job-id worker]]) (malt ~[[job-id [3 0x43.4100]]])]
  (expect !>(=([%| %audit-bounds] (page:stead-code-delivery-export repo saved extras protected 0 ''))))
++  failure-control
  (expect !>(%.n))
--

/+  *test, stead-project-retirement, stead-codec, stead-team, stead-team-codec
=,  stead-project-retirement
=/  project=@t  '019939ba-4000-7000-8000-000000000100'
=/  other=@t  '019939ba-4000-7000-8000-000000000101'
=/  initial
  %-  configure:stead-team
  :*  empty:stead-team
      '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000102","binding_id":"019939ba-4000-7000-8000-000000000202","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Alice"}},"project_creators":{"019939ba-4000-7000-8000-000000000102":"yes"}}'
      ~zod  1.000
  ==
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  create
  %-  decode:stead-team-codec
  '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000301","project_id":"019939ba-4000-7000-8000-000000000100","resource_id":"019939ba-4000-7000-8000-000000000100","expected_revision":"0","authority_epoch":"1","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","title":"Moving","project_key":"MOVE","preset":"general"}}'
=/  other-create
  %-  decode:stead-team-codec
  '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000302","project_id":"019939ba-4000-7000-8000-000000000101","resource_id":"019939ba-4000-7000-8000-000000000101","expected_revision":"0","authority_epoch":"1","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","title":"Other","project_key":"OTHER","preset":"general"}}'
=/  created  (apply-command:stead-team initial alice create 1.001)
=/  source  next.created
=/  tip  (need (head data.source project))
=/  command=intent  [project '019939ba-4000-7000-8000-000000000400' 1 ~nec tip]
=/  retired  (need (retire ~zod data.source ~ command 1.002))
|%
++  test-project-retire-current-source
  (expect !>(&((validate ~zod data.source retired) =(tip (need (head data.source project))))))
++  test-project-retire-compare-and-set
  %-  expect
  !>  ?&  ?=(~ (retire ~zod data.source ~ command(epoch 2) 1.002))
          ?=(~ (retire ~zod data.source ~ command(journal-head (hex:stead-codec 64 0)) 1.002))
          ?=(~ (retire ~zod data.source ~ command(destination ~zod) 1.002))
      ==
++  test-project-retire-replay-and-conflict
  %-  expect
  !>  ?&  =([~ retired] (retire ~zod data.source retired command 1.003))
          ?=(~ (retire ~zod data.source retired command(destination ~bud) 1.003))
      ==
++  test-project-retire-freezes-replay-and-keeps-other-project-writable
  =/  rejected  (apply retired source alice create 1.003)
  =/  value  (need (parse-result:stead-codec response.rejected))
  ?>  ?=([%o *] value)
  =/  accepted  (apply retired source alice other-create 1.003)
  %-  expect
  !>  ?&  =(source next.rejected)
          =('authority_retired' (field:stead-codec p.value 'error'))
          (~(has by projects.data.next.accepted) other)
          (validate ~zod data.next.accepted retired)
      ==
++  test-project-retire-rejects-changed-journal-on-load
  =/  altered  data.source(journal [[project '' (hex:stead-codec 64 0)] journal.data.source])
  (expect !>(!(validate ~zod altered retired)))
++  test-project-retire-rejects-unexportable-journal-before-fencing
  ::  Share one synthetic atom across 256 rows to reach 64 MiB with LFs.
  =/  entry  [project `@t`(bex 2.097.136) tip]
  =/  exact  (reap 256 entry)
  =/  wide  [other `@t`(bex 2.097.152) tip]
  =/  compact  [project 'a' tip]
  =/  fitting  data.source(journal [wide exact])
  =/  overflowing  data.source(journal [compact exact])
  =/  max-row  data.source(journal ~[[project `@t`(bex 2.097.144) tip]])
  =/  max-count  (reap journal-max-rows compact)
  =/  observation  (need (parse-result:stead-codec (need (status ~zod overflowing ~ project))))
  ?>  ?=([%o *] observation)
  %-  expect
  !>  ?&  (journal-admissible fitting project)
          (journal-admissible max-row project)
          (journal-admissible data.source(journal max-count) project)
          !(journal-admissible fitting other)
          !(journal-admissible data.source(journal [compact max-count]) project)
          ?=(^ (retire ~zod fitting ~ command 1.002))
          ?=(~ (retire ~zod overflowing ~ command 1.002))
          =('active' (field:stead-codec p.observation 'writer_state'))
          =([~ retired] (retire ~zod overflowing retired command 1.003))
      ==
--

/+  *test, stead-codec, stead-project-retirement, stead-restore, stead-team, stead-team-codec
=,  stead-codec
=/  project=@t  '019939ba-4000-7000-8000-000000000100'
=/  creator-grant=@t  '019939ba-4000-7000-8000-000000000301'
=/  renewal-request=@t  '019939ba-4000-7000-8000-000000000302'
=/  second-request=@t  '019939ba-4000-7000-8000-000000000303'
=/  binding=@t  '019939ba-4000-7000-8000-000000000202'
=/  another-binding=@t  '019939ba-4000-7000-8000-000000000203'
=/  config
  |=  [expected=@t binding=@t revision=@t expiry=@t]
  %-  rap
  :-  3
  :~  '{"protocol":"stead.team-config/1","expected_revision":"'  expected
      '","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000102","binding_id":"'  binding
      '","binding_revision":"'  revision  '","active":"yes","expires_at_ms":"'  expiry
      '","display_name":"Alice"}},"project_creators":{"019939ba-4000-7000-8000-000000000102":"yes"}}'
  ==
=/  initial  (configure:stead-team empty:stead-team (config '0' binding '1' '2000') ~zod 1.000)
=/  original  (need (native-context:stead-team initial ~bus 1.001))
=/  create
  %-  decode:stead-team-codec
  '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000301","project_id":"019939ba-4000-7000-8000-000000000100","resource_id":"019939ba-4000-7000-8000-000000000100","expected_revision":"0","authority_epoch":"1","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","title":"Renewal","project_key":"RENEW","preset":"general"}}'
=/  created  (apply-command:stead-team initial original create 1.001)
=/  rebound  (configure:stead-team next.created (config '1' binding '2' '9000') ~zod 3.000)
=/  fresh  (need (native-context:stead-team rebound ~bus 3.001))
=/  policy-command
  |=  [op=@t request=@t grant=@t revision=@t epoch=@t]
  %-  decode:stead-team-codec
  %-  rap
  :-  3
  :~  '{"protocol":"stead.command/3","request_id":"'  request
      '","project_id":"'  project  '","resource_id":"'  project
      '","expected_revision":"'  revision  '","authority_epoch":"'  epoch
      '","operation":"'  op  '","payload":{"grant_id":"'  grant  '"}}'
  ==
=/  renew
  |=  [request=@t grant=@t revision=@t epoch=@t]
  (policy-command 'policy.renew-creator-grant' request grant revision epoch)
=/  renew-original  (renew renewal-request creator-grant '1' '1')
=/  renewed  (apply-command:stead-team rebound fresh renew-original 3.001)
=/  result-field
  |=  [raw=@t key=@t]
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (field p.value key)
|%
++  test-creator-renewal-requires-explicit-acceptance-and-replays
  =/  retry  (apply-command:stead-team next.renewed fresh renew-original 3.002)
  =/  restored  (result:stead-restore (step:stead-restore (begin:stead-restore next.renewed ~zod)))
  %-  expect
  !>  ?&  =((role:stead-team rebound fresh project 3.001) 0)
          =((role:stead-team next.renewed fresh project 3.001) 3)
          =((result-field response.renewed 'resource_revision') '2')
          =(renewed retry)
          =(restored (some next.renewed))
      ==
++  test-creator-renewal-rejects-stale-requests-and-no-extension
  =/  wrong-epoch  (apply-command:stead-team rebound fresh (renew renewal-request creator-grant '1' '2') 3.001)
  =/  wrong-revision  (apply-command:stead-team rebound fresh (renew renewal-request creator-grant '2' '1') 3.001)
  =/  reused  (apply-command:stead-team next.renewed fresh (renew renewal-request creator-grant '2' '1') 3.002)
  =/  unchanged  (apply-command:stead-team next.renewed fresh (renew second-request creator-grant '2' '1') 3.002)
  %-  expect
  !>  ?&  =('authority_epoch_conflict' (result-field response.wrong-epoch 'error'))
          =('revision_conflict' (result-field response.wrong-revision 'error'))
          =('request_id_reuse' (result-field response.reused 'error'))
          =('invalid_command' (result-field response.unchanged 'error'))
          =(rebound next.wrong-epoch)  =(rebound next.wrong-revision)
          =(next.renewed next.reused)  =(next.renewed next.unchanged)
      ==
++  test-creator-renewal-needs-current-original-binding-and-grant
  =/  stale  (apply-command:stead-team rebound original renew-original 3.001)
  =/  delegate
    %-  decode:stead-team-codec
    '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000304","project_id":"019939ba-4000-7000-8000-000000000100","resource_id":"019939ba-4000-7000-8000-000000000100","expected_revision":"1","authority_epoch":"1","operation":"policy.grant","payload":{"grant_id":"019939ba-4000-7000-8000-000000000303","principal_id":"019939ba-4000-7000-8000-000000000102","role":"maintainer","expires_at_ms":"2000"}}'
  =/  delegated  (apply-command:stead-team next.created original delegate 1.002)
  =/  delegated-db  (configure:stead-team next.delegated (config '1' binding '2' '9000') ~zod 3.000)
  =/  wrong-state  (configure:stead-team next.created (config '1' another-binding '2' '9000') ~zod 3.000)
  =/  wrong-actor  (need (native-context:stead-team wrong-state ~bus 3.001))
  =/  wrong  (apply-command:stead-team wrong-state wrong-actor renew-original 3.001)
  =/  non-creator  (apply-command:stead-team delegated-db fresh (renew renewal-request second-request '2' '1') 3.001)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.stale 'error'))
          =('denied_or_not_found' (result-field response.wrong 'error'))
          =('accepted' (result-field response.delegated 'status'))
          =('denied_or_not_found' (result-field response.non-creator 'error'))
          =(rebound next.stale)  =(wrong-state next.wrong)  =(delegated-db next.non-creator)
      ==
++  test-creator-renewal-cannot-reopen-retired-closed-or-revoked-project-access
  =/  revoke  (policy-command 'policy.revoke' second-request creator-grant '1' '1')
  =/  revoked  (apply-command:stead-team next.created original revoke 1.002)
  =/  revoked-db  (configure:stead-team next.revoked (config '1' binding '2' '9000') ~zod 3.000)
  =/  rejected  (apply-command:stead-team revoked-db fresh (renew renewal-request creator-grant '2' '1') 3.001)
  =/  tip  (need (head:stead-project-retirement data.rebound project))
  =/  retired  (need (retire:stead-project-retirement ~zod data.rebound ~ [project second-request 1 ~nec tip] 3.000))
  =/  fenced  (apply:stead-project-retirement retired rebound fresh renew-original 3.001)
  =/  row  (~(got by projects.data.rebound) project)
  =/  closed  rebound(data data.rebound(projects (~(put by projects.data.rebound) project row(policy 18.446.744.073.709.551.615))))
  =/  refused  (apply-command:stead-team closed fresh renew-original 3.001)
  %-  expect
  !>  ?&  =('denied_or_not_found' (result-field response.rejected 'error'))
          =('authority_retired' (result-field response.fenced 'error'))
          =('denied_or_not_found' (result-field response.refused 'error'))
          =(revoked-db next.rejected)  =(rebound next.fenced)  =(closed next.refused)
      ==
--

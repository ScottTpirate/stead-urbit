::  Source-only actor compatibility fixtures. No service carrier is active.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-principals, stead-actor
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  command
  |=  [req=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  base  (object ~[['protocol' 'stead.command/3'] ['request_id' (id req)] ['project_id' (id 100)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
  ?>  ?=([%o *] base)
  (decode:stead-team-codec (canonical [%o (~(put by p.base) 'payload' (object payload))]))
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
=/  shared-box  (apply-command:stead-team db alice (command 351 200 0 'container.create' ~[['title' 'Shared'] ['visibility' 'shared']]) 1.006)
=/  private-box  (apply-command:stead-team next.shared-box alice (command 352 202 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.007)
=/  db  next.private-box
=/  imported  (import:stead-principals registry.db ~zod)
=/  human  (declare:stead-principals imported ~zod ~zod (id 102) 1 %person 'Alice' & 1.010)
=/  second-human  (declare:stead-principals next.human ~zod ~zod (id 103) 1 %person 'Bob' & 1.011)
=/  catalog  next.second-human
=/  scope=scope:stead-actor  [~zod (id 100) 1 (id 101) '' '' (silt ~[%work-read %work-comment])]
|%
++  test-actor-native-verification-keeps-exact-historical-authentication
  =/  actor  (need (verify-native:stead-actor db catalog alice 2.000))
  %-  expect
  !>  ?&  =([%native alice] actor)
          =((authentication-json:stead-team alice) (audit-bytes:stead-actor actor))
          =((some alice) (native-context:stead-actor actor))
          =((id 102) (principal:stead-actor actor))
          (native-human:stead-actor db catalog actor 2.000)
      ==
++  test-actor-unresolved-kind-is-not-human-and-inactive-or-forged-denied
  =/  unresolved  (need (verify-native:stead-actor db imported alice 2.000))
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 102) 2 %person 'Alice' | 2.000)
  =/  forged  alice(identity identity.alice(revision 999))
  %-  expect
  !>  ?&  !(native-human:stead-actor db imported unresolved 2.001)
          ?=(~ (verify-native:stead-actor db next.disabled alice 2.001))
          ?=(~ (verify-native:stead-actor db catalog forged 2.001))
          ?=(~ (verify-native:stead-actor db catalog alice 10.000.000))
      ==
++  test-actor-service-tag-has-no-native-identity-or-human-review-authority
  ::  A typed serialization fixture is not a verified credential or live actor.
  =/  service=service:stead-actor  [(id 106) (id 806) 1 (hex 64 1) 1 (hex 64 2) (hex 64 3) 3.000 scope]
  =/  actor=verified:stead-actor  [%service service]
  =/  parsed  (need (parse-result (audit-bytes:stead-actor actor)))
  ?>  ?=([%o *] parsed)
  %-  expect
  !>  ?&  =((id 106) (principal:stead-actor actor))
          ?=(~ (native-context:stead-actor actor))
          !(native-human:stead-actor db catalog actor 2.000)
          =('stead.service-auth/1' (field p.parsed 'protocol'))
          !(~(has by p.parsed) 'identity_ship')
          !(~(has by p.parsed) 'identity')
          !(~(has by p.parsed) 'bearer')
      ==
++  test-actor-service-scopes-are-exact-bounded-resource-intents
  =/  doc  scope(collection (id 200), document (id 201), actions (silt ~[%doc-propose]))
  %-  expect
  !>  ?&  (scope-valid:stead-actor scope)  (scope-valid:stead-actor doc)
          !(scope-valid:stead-actor scope(actions ~))
          !(scope-valid:stead-actor scope(project '', epoch 0))
          !(scope-valid:stead-actor scope(work ''))
          !(scope-valid:stead-actor scope(actions (silt ~[%doc-propose])))
          !(scope-valid:stead-actor doc(document ''))
          !=((scope-bytes:stead-actor scope) (scope-bytes:stead-actor doc))
      ==
--

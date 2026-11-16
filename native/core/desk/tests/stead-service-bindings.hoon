::  Source-only service binding fixtures. No service carrier is active.
/+  *test, stead-codec, stead-session, stead-core, stead-team, stead-team-codec, stead-principals, stead-actor, stead-service-bindings
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
=/  permitted-actions=(list action:stead-actor)  ~[%work-read %work-comment]
=/  scope=scope:stead-actor  [~zod (id 100) 1 (id 101) '' '' (silt permitted-actions)]
=/  first-agent  (declare:stead-principals catalog ~zod ~zod (id 106) 0 %agent 'Documentation agent' & 1.020)
=/  second-agent  (declare:stead-principals next.first-agent ~zod ~zod (id 107) 0 %agent 'Release agent' & 1.021)
=/  first-runtime  (runtime-put:stead-principals next.second-agent ~zod ~zod (id 810) 0 (id 106) 'isolated-doc-worker' (hex 64 1) 1.022)
=/  second-runtime  (runtime-put:stead-principals next.first-runtime ~zod ~zod (id 811) 0 (id 107) 'isolated-doc-worker' (hex 64 2) 1.023)
=/  catalog  next.second-runtime
::  Explicit trusted shared-core grant fixtures. Native policy.grant remains
::  ship-only; this does not claim a new Home grant adapter exists. No new
::  permissions map or credential-derived grant is introduced by these tests.
=/  first-grant=grant-state:stead-core  [(id 100) (id 106) 'contributor' 8.000.000 |]
=/  second-grant=grant-state:stead-core  [(id 100) (id 107) 'contributor' 8.000.000 |]
=/  with-first  db(data data.db(grants (~(put by grants.data.db) (scope-key:stead-core (id 100) (id 850)) first-grant)))
=/  granted  with-first(data data.with-first(grants (~(put by grants.data.with-first) (scope-key:stead-core (id 100) (id 851)) second-grant)))
=/  empty-bindings  (initialize:stead-service-bindings granted ~zod)
=/  first-binding  (owner-bind:stead-service-bindings empty-bindings granted catalog ~zod (id 806) 0 (id 106) 'supervisor-a' (id 810) 1 9.999.999 2.000 0)
=/  second-binding  (owner-bind:stead-service-bindings next.first-binding granted catalog ~zod (id 807) 0 (id 107) 'supervisor-b' (id 811) 1 9.999.999 2.001 1)
=/  book  (new-live:stead-service-bindings ~zod 999)
=/  proposal-actions=(list action:stead-actor)  ~[%work-read %work-comment %doc-propose]
=/  scope  scope(collection (id 200), document (id 201), actions (silt proposal-actions))
=/  issued-a  (issue:stead-service-bindings next.second-binding book granted catalog [%native alice] (id 806) scope 2.002 111 2)
=/  issued-b  (issue:stead-service-bindings next.issued-a live.issued-a granted catalog [%native alice] (id 807) scope 2.003 222 3)
=/  state  next.issued-b
=/  book  live.issued-b
|%
++  test-service-bindings-two-agents-have-distinct-current-scoped-identity
  =/  a  (need (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope %work-comment 2.004))
  =/  b  (need (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-b scope %doc-propose 2.004))
  =/  descriptor  (~(got by descriptors.state) handle.issued-a)
  =/  record  (need (parse-result (need record.issued-a)))
  ?>  ?=([%o *] record)
  %-  expect
  !>  ?&  =(%accepted status.first-binding)  =(%accepted status.second-binding)
          =(%accepted status.issued-a)  =(%accepted status.issued-b)
          =((id 106) (principal:stead-actor a))  =((id 107) (principal:stead-actor b))
          !=(bearer.issued-a bearer.issued-b)  !=(handle.issued-a handle.issued-b)
          ?=(~ (native-context:stead-actor a))
          !(native-human:stead-actor granted catalog a 2.004)
          =(902.002 expires.descriptor)
          =(alice issuer.descriptor)
          =((digest:stead-session 'stead.service-credential/1' bearer.issued-a) bearer-hash.descriptor)
          !=(bearer.issued-a bearer-hash.descriptor)
          !(~(has by p.record) 'bearer')
          !(~(has by p.record) 'entropy')
      ==
++  test-service-bindings-wrong-resource-operation-epoch-and-forged-proof-denied
  =/  actor  (need (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope %work-comment 2.004))
  ?>  ?=(%service -.actor)
  =/  forged  actor(context context.actor(principal (id 107)))
  =/  project  (~(got by projects.data.granted) (id 100))
  =/  advanced  granted(data data.granted(projects (~(put by projects.data.granted) (id 100) project(epoch 2))))
  %-  expect
  !>  ?&  ?=(~ (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope(project (id 999)) %work-comment 2.004))
          ?=(~ (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope(work (id 999)) %work-comment 2.004))
          ?=(~ (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope %doc-read 2.004))
          ?=(~ (verify-bearer:stead-service-bindings state book advanced catalog bearer.issued-a scope %work-comment 2.004))
          ?=(~ (verify-bearer:stead-service-bindings state book granted catalog (hex 64 0) scope %work-comment 2.004))
          !(recheck-effect:stead-service-bindings state book granted catalog forged scope %work-comment 2.004)
      ==
++  test-service-bindings-owner-custody-and-one-active-mechanism
  =/  denied  (owner-bind:stead-service-bindings empty-bindings granted catalog ~bus (id 808) 0 (id 106) 'supervisor-a' (id 810) 1 9.999.999 2.004 4)
  =/  duplicate  (owner-bind:stead-service-bindings state granted catalog ~zod (id 808) 0 (id 106) 'supervisor-a' (id 810) 1 9.999.999 2.004 4)
  =/  changed-custody  (owner-bind:stead-service-bindings state granted catalog ~zod (id 806) 1 (id 106) 'other-supervisor' (id 810) 1 9.999.999 2.004 4)
  =/  reused-native  (owner-bind:stead-service-bindings state granted catalog ~zod (id 202) 0 (id 106) 'supervisor-a' (id 810) 1 9.999.999 2.004 4)
  =/  native-agent  (declare:stead-principals next.human ~zod ~zod (id 103) 1 %agent 'Native worker' & 1.020)
  =/  runtime  (runtime-put:stead-principals next.native-agent ~zod ~zod (id 812) 0 (id 103) 'isolated-doc-worker' (hex 64 3) 1.021)
  =/  competing  (owner-bind:stead-service-bindings state granted next.runtime ~zod (id 809) 0 (id 103) 'native-worker-supervisor' (id 812) 1 9.999.999 2.004 4)
  =/  revoked  (owner-revoke:stead-service-bindings state granted ~zod (id 806) 1 2.005 [4 0 0])
  =/  transfer  (owner-bind:stead-service-bindings next.revoked granted catalog ~zod (id 806) 2 (id 107) 'supervisor-a' (id 811) 1 9.999.999 2.005 5)
  %-  expect
  !>  ?&  =(%denied status.denied)  =(empty-bindings next.denied)
          =(%mechanism-conflict status.duplicate)
          =(%ownership-conflict status.changed-custody)
          =(%ownership-conflict status.reused-native)
          =(%mechanism-conflict status.competing)
          =(%ownership-conflict status.transfer)
          =((some (id 106)) (~(get by owners.next.revoked) (id 806)))
          =((some 2) (~(get by highwaters.next.revoked) (id 806)))
      ==
++  test-service-bindings-rotation-and-revocation-fence-in-flight-effects
  =/  actor  (need (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope %work-comment 2.004))
  =/  rotated  (owner-bind:stead-service-bindings state granted catalog ~zod (id 806) 1 (id 106) 'supervisor-a' (id 810) 1 9.999.999 2.005 4)
  =/  next-credential  (issue:stead-service-bindings next.rotated book granted catalog [%native alice] (id 806) scope 2.006 333 5)
  =/  revoked  (revoke-credential:stead-service-bindings state book granted catalog [%native alice] handle.issued-a 2.005 [4 0 0])
  =/  binding-revoked  (owner-revoke:stead-service-bindings state granted ~zod (id 806) 1 2.005 [4 0 0])
  %-  expect
  !>  ?&  =(%accepted status.rotated)  =(%accepted status.next-credential)
          !(recheck-effect:stead-service-bindings next.rotated book granted catalog actor scope %work-comment 2.006)
          ?=(~ (verify-bearer:stead-service-bindings next.next-credential live.next-credential granted catalog bearer.issued-a scope %work-comment 2.007))
          ?=(^ (verify-bearer:stead-service-bindings next.next-credential live.next-credential granted catalog bearer.next-credential scope %work-comment 2.007))
          ?=(~ (verify-bearer:stead-service-bindings next.revoked book granted catalog bearer.issued-a scope %work-comment 2.006))
          ?=(^ (verify-bearer:stead-service-bindings next.revoked book granted catalog bearer.issued-b scope %work-comment 2.006))
          ?=(~ (verify-bearer:stead-service-bindings next.binding-revoked book granted catalog bearer.issued-a scope %work-comment 2.006))
          =((~(got by descriptors.state) handle.issued-a) (~(got by descriptors.next.next-credential) handle.issued-a))
      ==
++  test-service-bindings-restore-descriptors-never-revive-a-live-bearer
  =/  restored  !<(state:stead-service-bindings ;;(vase (cue (jam !>(state)))))
  =/  new-book  (new-live:stead-service-bindings ~zod 1.000)
  =/  actor  (need (verify-bearer:stead-service-bindings state book granted catalog bearer.issued-a scope %work-comment 2.004))
  =/  empty-old  book(credentials ~)
  =/  wrong-highwater  state(highwaters (~(put by highwaters.state) (id 806) 0))
  =/  malformed-book  book(credentials (malt ~[[(hex 64 0) handle.issued-a]]))
  %-  expect
  !>  ?&  =(state restored)
          !=(incarnation.book incarnation.new-book)
          ?=(~ (verify-bearer:stead-service-bindings restored new-book granted catalog bearer.issued-a scope %work-comment 2.005))
          ?=(~ (verify-bearer:stead-service-bindings restored empty-old granted catalog bearer.issued-a scope %work-comment 2.005))
          !(recheck-effect:stead-service-bindings restored new-book granted catalog actor scope %work-comment 2.005)
          (bounded-state:stead-service-bindings state)
          (bounded-state:stead-service-bindings restored)
          (bounded-live:stead-service-bindings state book)
          (bounded-live:stead-service-bindings restored new-book)
          !(bounded-state:stead-service-bindings wrong-highwater)
          !(bounded-live:stead-service-bindings state malformed-book)
      ==
++  test-service-bindings-shared-grants-and-issuer-authority-cannot-be-renewed-implicitly
  =/  no-grant  (issue:stead-service-bindings next.second-binding book db catalog [%native alice] (id 806) scope 2.004 444 4)
  =/  contributor  (issue:stead-service-bindings state book granted catalog [%native bob] (id 806) scope 2.004 444 4)
  =/  private  (issue:stead-service-bindings state book granted catalog [%native alice] (id 806) scope(collection (id 202)) 2.004 444 4)
  =/  revoked-grant  granted(data data.granted(grants (~(put by grants.data.granted) (scope-key:stead-core (id 100) (id 850)) first-grant(revoked &))))
  =/  renewed  revoked-grant(data data.revoked-grant(grants (~(put by grants.data.revoked-grant) (scope-key:stead-core (id 100) (id 852)) first-grant)))
  =/  issuer-grant  (~(got by grants.data.granted) (scope-key:stead-core (id 100) (id 301)))
  =/  lost-issuer  granted(data data.granted(grants (~(put by grants.data.granted) (scope-key:stead-core (id 100) (id 301)) issuer-grant(revoked &))))
  %-  expect
  !>  ?&  =(%denied status.no-grant)  =(%denied status.contributor)  =(%denied status.private)
          ?=(~ (verify-bearer:stead-service-bindings state book renewed catalog bearer.issued-a scope %work-comment 2.005))
          ?=(^ (verify-bearer:stead-service-bindings state book renewed catalog bearer.issued-b scope %work-comment 2.005))
          ?=(~ (verify-bearer:stead-service-bindings state book lost-issuer catalog bearer.issued-a scope %work-comment 2.005))
      ==
++  test-service-bindings-expiry-current-catalog-and-immutable-runtime-versions
  =/  short  alice(method 'native-approved-browser/1', strength 'native-approved-browser', audit (hex 64 9), expires 2.100)
  =/  short-credential  (issue:stead-service-bindings state book granted catalog [%native short] (id 806) scope 2.004 444 4)
  =/  row  (~(got by descriptors.next.short-credential) handle.short-credential)
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 106) 1 %agent 'Documentation agent' | 2.005)
  =/  new-runtime  (runtime-put:stead-principals catalog ~zod ~zod (id 810) 1 (id 106) 'new-worker-profile' (hex 64 4) 2.005)
  =/  old-binding  (~(got by bindings.state) (id 806))
  %-  expect
  !>  ?&  =(2.100 expires.row)
          ?=(~ (verify-bearer:stead-service-bindings next.short-credential live.short-credential granted catalog bearer.short-credential scope %work-comment 2.100))
          ?=(~ (verify-bearer:stead-service-bindings state book granted next.disabled bearer.issued-a scope %work-comment 2.006))
          ?=(^ (verify-bearer:stead-service-bindings state book granted next.new-runtime bearer.issued-a scope %work-comment 2.006))
          =(1 runtime-revision.old-binding)
          =((~(got by runtimes.catalog) [(id 810) 1]) (~(got by runtimes.next.new-runtime) [(id 810) 1]))
      ==
++  test-service-bindings-global-budget-and-entropy-fail-closed
  =/  capacity  (issue:stead-service-bindings state book granted catalog [%native alice] (id 806) scope 2.004 444 4.096)
  =/  no-entropy  (issue:stead-service-bindings state book granted catalog [%native alice] (id 806) scope 2.004 0 4)
  =/  binding-reserve  (owner-revoke:stead-service-bindings state granted ~zod (id 806) 1 2.005 [4.096 2.047 127])
  =/  credential-reserve  (revoke-credential:stead-service-bindings state book granted catalog [%native alice] handle.issued-a 2.004 [4.096 2.047 127])
  =/  binding-repeat  (owner-revoke:stead-service-bindings next.binding-reserve granted ~zod (id 806) 2 2.006 [4.096 2.048 128])
  =/  credential-repeat  (revoke-credential:stead-service-bindings next.credential-reserve book granted catalog [%native alice] handle.issued-a 2.006 [4.096 2.048 128])
  =/  global-full  (owner-revoke:stead-service-bindings state granted ~zod (id 806) 1 2.005 [4.096 2.048 127])
  =/  owner-full  (revoke-credential:stead-service-bindings state book granted catalog [%native alice] handle.issued-a 2.004 [4.096 0 128])
  =/  expired  (revoke-credential:stead-service-bindings state book granted catalog [%native alice] handle.issued-a 902.002 [4.096 0 0])
  =/  absent  (revoke-credential:stead-service-bindings state book(credentials ~) granted catalog [%native alice] handle.issued-a 2.004 [4.096 0 0])
  =/  disabled  (declare:stead-principals catalog ~zod ~zod (id 106) 1 %agent 'Documentation agent' | 2.004)
  =/  disabled-revoke  (revoke-credential:stead-service-bindings state book granted next.disabled [%native alice] handle.issued-a 2.005 [4.096 0 0])
  =/  reserve-record  (need (parse-result (need record.credential-reserve)))
  ?>  ?=([%o *] reserve-record)
  %-  expect
  !>  ?&  =(%capacity status.capacity)  =(state next.capacity)  =(book live.capacity)
          =('' bearer.capacity)  ?=(~ record.capacity)
          =(%invalid status.no-entropy)  =(state next.no-entropy)
          =(%accepted status.binding-reserve)  =(%accepted status.credential-reserve)
          =('security' (field p.reserve-record 'capacity_class'))
          =(%unchanged status.binding-repeat)  =(next.binding-reserve next.binding-repeat)
          ?=(~ record.binding-repeat)
          =(%unchanged status.credential-repeat)  =(next.credential-reserve next.credential-repeat)
          ?=(~ record.credential-repeat)
          =(%capacity status.global-full)  =(state next.global-full)
          =(%capacity status.owner-full)  =(state next.owner-full)
          =(%capacity status.expired)  =(state next.expired)
          =(%capacity status.absent)  =(state next.absent)
          =(%accepted status.disabled-revoke)
      ==
--

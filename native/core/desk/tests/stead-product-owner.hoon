/+  *test, stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-views, stead-product-migrate, stead-product-state, stead-work-contract, stead-product-work, stead-product-codec, stead-principals, stead-product-owner-codec, stead-product-owner-policy, stead-product-owner
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
++  owner-command
  |=  [req=@ud operation=@t expected=@ud payload=(list [@t @t])]
  ^-  command:stead-product-owner-codec
  =/  base  (object ~[['protocol' 'stead.owner-command/1'] ['request_id' (id req)] ['operation' operation] ['expected_revision' (decimal expected)]])
  ?>  ?=([%o *] base)
  (decode:stead-product-owner-codec (canonical [%o (~(put by p.base) 'payload' (object payload))]))
++  json-object
  |=  raw=@t
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  p.value
++  child
  |=  [data=object-map key=@t]
  ^-  object-map
  =/  value  (~(got by data) key)
  ?>  ?=([%o *] value)
  p.value
++  member-config
  |=  [raw=@t expected=@ud ship=@t revision=@ud active=@t expires=@ud]
  ^-  @t
  =/  value  (json-object raw)
  =/  members  (child value 'bindings')
  =/  person  (child members ship)
  =.  person  (~(put by person) 'binding_revision' [%s (decimal revision)])
  =.  person  (~(put by person) 'active' [%s active])
  =.  person  (~(put by person) 'expires_at_ms' [%s (decimal expires)])
  =.  members  (~(put by members) ship [%o person])
  =.  value  (~(put by value) 'bindings' [%o members])
  (canonical [%o (~(put by value) 'expected_revision' [%s (decimal expected)])])
++  rejected-wire
  |=  raw=@t
  ^-  ?
  ?=([%| *] (mule |.((decode:stead-product-owner-codec raw))))
++  full-budget
  |=  state=state:stead-product-owner
  ^-  budget:stead-product-owner
  ::  Models counts supplied by another typed authority ledger at the exact
  ::  capacity boundary. This is not a large-storage qualification fixture.
  =/  existing  (add (event-count:stead-team db.state '' |) (add (lent ~(tap by attempts.product.state)) (owner-count:stead-product-owner ledger.state |)))
  [(sub 4.096 existing) 0]
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
=/  initial-product  (migrate next.private-box)
=/  owner-initial  (initialize:stead-product-owner initial-product ~zod)
=/  human-command  (owner-command 901 'principal.declare' 1 ~[['principal_id' (id 102)] ['kind' 'person'] ['display_name' 'Alice'] ['active' 'yes']])
=/  agent-command  (owner-command 902 'principal.declare' 1 ~[['principal_id' (id 103)] ['kind' 'agent'] ['display_name' 'Bob worker'] ['active' 'yes']])
=/  human  (apply:stead-product-owner owner-initial human-command ~zod ~zod 2.000 [0 0])
=/  agent  (apply:stead-product-owner next.human agent-command ~zod ~zod 2.001 [0 0])
=/  owner  next.agent
|%
++  test-product-owner-codec-is-closed-and-never-accepts-a-wire-actor
  =/  value  (json-object canonical-bytes.human-command)
  =/  unexpected  (canonical [%o (~(put by value) 'native_sender' [%s '~zod'])])
  =/  unknown  (canonical [%o (~(put by value) 'operation' [%s 'policy.override'])])
  =/  number  (canonical [%o (~(put by value) 'expected_revision' [%s '01'])])
  =/  config  (member-config configuration 1 '~nec' 2 'no' 9.999.999)
  =/  valid  (owner-command 903 'home.configure' 1 ~[['configuration' config]])
  =/  mismatched  (json-object canonical-bytes.valid)
  =/  mismatch  (canonical [%o (~(put by mismatched) 'expected_revision' [%s '2'])])
  %-  expect
  !>  ?&  =(human-command (decode:stead-product-owner-codec canonical-bytes.human-command))
          (rejected-wire unexpected)  (rejected-wire unknown)  (rejected-wire number)
          (rejected-wire mismatch)
          (rejected-wire '{"protocol":"stead.owner-command/1","protocol":"stead.owner-command/1"}')
          =(digest.valid (hash 'stead.owner-command/1' canonical-bytes.valid))
      ==
++  test-product-owner-declaration-retry-and-current-owner-boundary
  =/  denied  (apply:stead-product-owner owner-initial human-command ~zod ~bus 2.000 [0 0])
  =/  retry  (apply:stead-product-owner owner human-command ~zod ~zod 2.002 [0 0])
  =/  denied-retry  (apply:stead-product-owner owner human-command ~zod ~bus 2.002 [0 0])
  =/  changed  (owner-command 901 'principal.declare' 2 ~[['principal_id' (id 102)] ['kind' 'person'] ['display_name' 'Renamed'] ['active' 'yes']])
  =/  reused  (apply:stead-product-owner owner changed ~zod ~zod 2.002 [0 0])
  =/  forged-kind  (owner-command 903 'principal.declare' 2 ~[['principal_id' (id 103)] ['kind' 'person'] ['display_name' 'Bob'] ['active' 'yes']])
  =/  refused  (apply:stead-product-owner owner forged-kind ~zod ~zod 2.002 [0 0])
  %-  expect
  !>  ?&  =('owner_required' (result-field response.denied 'error'))
          =(owner-initial next.denied)  ?=(~ record.denied)
          =('accepted' (result-field response.human 'status'))
          =((some %person) (native-kind:stead-principals catalog.owner registry.db.owner (id 102) 2.002))
          =(response.human response.retry)  =(owner next.retry)  ?=(~ record.retry)
          =('owner_required' (result-field response.denied-retry 'error'))
          =('request_id_reuse' (result-field response.reused 'error'))
          =('kind_conflict' (result-field response.refused 'error'))
          =(catalog.owner catalog.next.refused)
          =('~zod' (result-field (need record.human) 'native_sender'))
          =(events.product.owner-initial events.product.owner)
      ==
++  test-product-owner-runtime-definitions-retain-pinned-versions
  =/  runtime-command  (owner-command 903 'runtime.put' 0 ~[['runtime_id' (id 401)] ['principal_id' (id 103)] ['profile' 'docs-worker/1'] ['policy_digest' (hex 64 1)]])
  =/  runtime  (apply:stead-product-owner owner runtime-command ~zod ~zod 2.002 [0 0])
  =/  definition-command  (owner-command 904 'definition.put' 0 ~[['definition_id' (id 501)] ['principal_id' (id 103)] ['instructions_digest' (hex 64 2)] ['runtime_id' (id 401)] ['runtime_revision' '1']])
  =/  definition  (apply:stead-product-owner next.runtime definition-command ~zod ~zod 2.003 [0 0])
  =/  original  (~(got by definitions.catalog.next.definition) [(id 501) 1])
  =/  update-command  (owner-command 905 'runtime.put' 1 ~[['runtime_id' (id 401)] ['principal_id' (id 103)] ['profile' 'docs-worker/2'] ['policy_digest' (hex 64 3)]])
  =/  update  (apply:stead-product-owner next.definition update-command ~zod ~zod 2.004 [0 0])
  =/  unauthorized  (apply:stead-product-owner next.definition update-command ~zod ~nec 2.004 [0 0])
  %-  expect
  !>  ?&  =('accepted' (result-field response.runtime 'status'))
          =('accepted' (result-field response.definition 'status'))
          =('accepted' (result-field response.update 'status'))
          =(original (~(got by definitions.catalog.next.update) [(id 501) 1]))
          =(1 runtime-revision.original)
          =((hex 64 1) policy-digest:(~(got by runtimes.catalog.next.update) [(id 401) 1]))
          =('owner_required' (result-field response.unauthorized 'error'))
          =(next.definition next.unauthorized)
      ==
++  test-product-owner-configuration-revocation-reconciles-highwaters
  =/  raw  (member-config configuration 1 '~nec' 2 'no' 9.999.999)
  =/  cmd  (owner-command 903 'home.configure' 1 ~[['configuration' raw]])
  =/  revoked  (apply:stead-product-owner owner cmd ~zod ~zod 2.002 [0 0])
  =/  stale  (apply:stead-product-owner next.revoked (owner-command 904 'home.configure' 1 ~[['configuration' raw]]) ~zod ~zod 2.003 [0 0])
  =/  old-person  (~(got by principals.catalog.owner) (id 103))
  %-  expect
  !>  ?&  =('accepted' (result-field response.revoked 'status'))
          ?=(~ (native-context:stead-team db.next.revoked ~nec 2.003))
          ?=(~ (native-kind:stead-principals catalog.next.revoked registry.db.next.revoked (id 103) 2.003))
          =(old-person (~(got by principals.catalog.next.revoked) (id 103)))
          =(2 (~(got by principal-highwaters.catalog.next.revoked) (id 103)))
          =((id 103) (~(got by binding-owners.catalog.next.revoked) (id 203)))
          =('revision_conflict' (result-field response.stale 'error'))
          =(db.next.revoked db.next.stale)
          !=((result-field (need record.revoked) 'before_registry_digest') (result-field (need record.revoked) 'after_registry_digest'))
      ==
++  test-product-owner-security-fallback-requires-strict-authority-reduction
  =/  budget  (full-budget owner)
  =/  disable  (owner-command 903 'principal.declare' 2 ~[['principal_id' (id 103)] ['kind' 'agent'] ['display_name' 'Bob worker'] ['active' 'no']])
  =/  reduced  (apply:stead-product-owner owner disable ~zod ~zod 2.002 budget)
  =/  expand  (owner-command 904 'principal.declare' 3 ~[['principal_id' (id 103)] ['kind' 'agent'] ['display_name' 'Bob worker'] ['active' 'yes']])
  =/  denied  (apply:stead-product-owner next.reduced expand ~zod ~zod 2.003 budget)
  =/  raw  (member-config configuration 1 '~nec' 2 'no' 9.999.999)
  =/  config  (apply:stead-product-owner owner (owner-command 905 'home.configure' 1 ~[['configuration' raw]]) ~zod ~zod 2.002 budget)
  =/  renewal  (member-config configuration 1 '~nec' 2 'yes' 19.999.999)
  =/  renew  (apply:stead-product-owner owner (owner-command 906 'home.configure' 1 ~[['configuration' renewal]]) ~zod ~zod 2.002 budget)
  =/  exhausted  (apply:stead-product-owner owner disable ~zod ~zod 2.002 budget(security 2.048))
  =/  origin  (canonical [%o (~(put by (json-object raw)) 'origin' [%s 'https://changed.test'])])
  =/  moved  (apply:stead-product-owner owner (owner-command 908 'home.configure' 1 ~[['configuration' origin]]) ~zod ~zod 2.002 budget)
  ::  Inject the bounded ledger count to exercise the dedicated owner limit;
  ::  these duplicate fixture receipts are not a replay-valid history.
  =/  receipt  (~(got by ledger.next.reduced) (id 903))
  =/  filled  owner(ledger (malt (turn (gulf 0 127) |=(n=@ud [(id (add 700 n)) receipt]))))
  =/  owner-full  (apply:stead-product-owner filled disable ~zod ~zod 2.002 (full-budget filled))
  %-  expect
  !>  ?&  =('accepted' (result-field response.reduced 'status'))
          =('security' (result-field response.reduced 'capacity_class'))
          =('capacity_exceeded' (result-field response.denied 'error'))
          =(next.reduced next.denied)  ?=(~ record.denied)
          =('accepted' (result-field response.config 'status'))
          =('security' (result-field response.config 'capacity_class'))
          =('capacity_exceeded' (result-field response.renew 'error'))
          =(owner next.renew)  ?=(~ record.renew)
          =('capacity_exceeded' (result-field response.exhausted 'error'))
          =(owner next.exhausted)
          =('capacity_exceeded' (result-field response.moved 'error'))
          =(owner next.moved)
          =('capacity_exceeded' (result-field response.owner-full 'error'))
          =(filled next.owner-full)
      ==
++  test-product-owner-configuration-expansion-imports-new-unresolved-principal
  =/  raw  (json-object configuration)
  =/  members  (child raw 'bindings')
  =/  newcomer  (object ~[['principal_id' (id 105)] ['binding_id' (id 205)] ['binding_revision' '1'] ['active' 'yes'] ['expires_at_ms' '9999999'] ['display_name' 'New native member']])
  =.  members  (~(put by members) '~wes' newcomer)
  =.  raw  (~(put by raw) 'bindings' [%o members])
  =.  raw  (~(put by raw) 'expected_revision' [%s '1'])
  =/  config  (canonical [%o raw])
  =/  cmd  (owner-command 907 'home.configure' 1 ~[['configuration' config]])
  =/  admitted  (apply:stead-product-owner owner cmd ~zod ~zod 2.002 [0 0])
  =/  denied  (apply:stead-product-owner owner cmd ~zod ~zod 2.002 (full-budget owner))
  =/  imported  (~(got by principals.catalog.next.admitted) (id 105))
  %-  expect
  !>  ?&  =('accepted' (result-field response.admitted 'status'))
          ?=(~ kind.imported)  imported.imported
          =('New native member' display.imported)
          =((id 105) (~(got by binding-owners.catalog.next.admitted) (id 205)))
          =(source.catalog.owner source.catalog.next.admitted)
          =('capacity_exceeded' (result-field response.denied 'error'))
          =(owner next.denied)
      ==
--

/+  *test, stead-codec, stead-core, stead-session, stead-team-config, stead-principals
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  person
  |=  [principal=@ud binding=@ud revision=@ud active=@t expires=@ud display=@t]
  ^-  json
  %-  object
  :~  ['principal_id' (id principal)]  ['binding_id' (id binding)]
      ['binding_revision' (decimal revision)]  ['active' active]
      ['expires_at_ms' (decimal expires)]  ['display_name' display]
  ==
++  configure
  |=  [prior=registry:stead-team-config people=(map @t json) now=@ud]
  ^-  registry:stead-team-config
  =/  raw
    %-  object
    :~  ['protocol' 'stead.team-config/1']
        ['expected_revision' (decimal ?~(current.prior 0 revision.u.current.prior))]
        ['home' '~zod']  ['origin' 'https://home.test']
        ['organization_id' (id 105)]  ['team_id' (id 106)]
        ['custody' 'local-disposable']  ['runtime' 'isolated-fake']
    ==
  ?>  ?=([%o *] raw)
  =/  wire
    [%o (~(put by (~(put by p.raw) 'bindings' [%o people])) 'project_creators' (object ~[[(id 102) 'yes']]))]
  (decode:stead-team-config (canonical wire) prior ~zod now)
--
=/  bindings
  (malt ~[['~bus' (person 102 202 1 'yes' 9.999.999 'Human or agent is unresolved')] ['~nec' (person 103 203 1 'yes' 9.999.999 'Worker')]])
=/  registry  (configure *registry:stead-team-config bindings 1.000)
=/  imported  (import:stead-principals registry ~zod)
=/  human  (declare:stead-principals imported ~zod ~zod (id 102) 1 %person 'Alice' & 1.001)
=/  agent  (declare:stead-principals next.human ~zod ~zod (id 103) 1 %agent 'Docs worker' & 1.002)
=/  db  next.agent
|%
++  test-principals-import-preserves-identity-with-unresolved-kind
  ^-  tang
  ?>  =(imported (import:stead-principals registry ~zod))
  ?>  =(owners.registry binding-owners.imported)
  ?>  =(revisions.registry principal-highwaters.imported)
  ?>  =(2 (lent ~(tap by principals.imported)))
  ?>  ?=(~ (native-kind:stead-principals imported registry (id 102) 1.001))
  ?>  ?=(~ (native-kind:stead-principals imported registry (id 103) 1.001))
  =/  removed  (configure registry (~(del by bindings) '~nec') 1.010)
  =/  retained  (import:stead-principals removed ~zod)
  ?>  (~(has by principals.retained) (id 103))
  ?>  =('' display:(~(got by principals.retained) (id 103)))
  ?>  =((id 103) (~(got by binding-owners.retained) (id 203)))
  ?>  !=(source.imported source.retained)
  ~
++  test-principals-declarations-require-owner-current-cas-and-fixed-kind
  ^-  tang
  =/  denied  (declare:stead-principals imported ~bus ~zod (id 102) 1 %person 'Alice' & 1.001)
  ?>  =([%denied imported] denied)
  ?>  =(%accepted status.human)
  ?>  =(%accepted status.agent)
  =/  stale  (declare:stead-principals db ~zod ~zod (id 102) 1 %person 'Renamed' & 1.003)
  ?>  =([%conflict db] stale)
  =/  changed  (declare:stead-principals db ~zod ~zod (id 103) 2 %person 'Worker becomes owner' & 1.003)
  ?>  =([%kind-conflict db] changed)
  =/  disabled  (declare:stead-principals db ~zod ~zod (id 103) 2 %agent 'Docs worker' | 1.003)
  ?>  =(%accepted status.disabled)
  ?>  ?=(~ (native-kind:stead-principals next.disabled registry (id 103) 1.004))
  =/  replace  (declare:stead-principals next.disabled ~zod ~zod (id 103) 3 %person 'Wrong kind' & 1.005)
  ?>  =([%kind-conflict next.disabled] replace)
  ~
++  test-principals-native-kind-follows-current-binding-and-expiry
  ^-  tang
  ?>  =((some %person) (native-kind:stead-principals db registry (id 102) 1.010))
  ?>  =((some %agent) (native-kind:stead-principals db registry (id 103) 1.010))
  ?>  ?=(~ (native-kind:stead-principals db registry (id 103) 9.999.999))
  =/  inactive  (configure registry (~(put by bindings) '~nec' (person 103 203 2 'no' 9.999.999 'Worker')) 1.011)
  ?>  ?=(~ (native-kind:stead-principals db inactive (id 103) 1.012))
  =/  removed  (configure registry (~(del by bindings) '~nec') 1.011)
  ?>  ?=(~ (native-kind:stead-principals db removed (id 103) 1.012))
  =/  rotated  (configure registry (~(put by bindings) '~nec' (person 103 204 2 'yes' 9.999.999 'Renamed worker')) 1.011)
  ?>  =((some %agent) (native-kind:stead-principals db rotated (id 103) 1.012))
  ?>  =((id 103) (~(got by owners.rotated) (id 203)))
  ?>  =((id 103) (~(got by owners.rotated) (id 204)))
  ?>  =('Docs worker' display:(~(got by principals.db) (id 103)))
  =/  newer  (import:stead-principals rotated ~zod)
  =/  declared  (declare:stead-principals newer ~zod ~zod (id 103) 1 %agent 'Docs worker' & 1.012)
  ?>  =((some %agent) (native-kind:stead-principals next.declared rotated (id 103) 1.013))
  ?>  ?=(~ (native-kind:stead-principals next.declared registry (id 103) 1.013))
  =/  wrong-owner  db(binding-owners (~(put by binding-owners.db) (id 203) (id 102)))
  ?>  ?=(~ (native-kind:stead-principals wrong-owner registry (id 103) 1.013))
  ~
++  test-principals-runtime-and-definition-versions-preserve-exact-history
  ^-  tang
  =/  runtime  (runtime-put:stead-principals db ~zod ~zod (id 401) 0 (id 103) 'docs-worker/1' (hex 64 1) 1.010)
  ?>  =(%accepted status.runtime)
  =/  definition  (definition-put:stead-principals next.runtime ~zod ~zod (id 501) 0 (id 103) (hex 64 2) (id 401) 1 1.011)
  ?>  =(%accepted status.definition)
  =/  original  (~(got by definitions.next.definition) [(id 501) 1])
  =/  update  (runtime-put:stead-principals next.definition ~zod ~zod (id 401) 1 (id 103) 'docs-worker/2' (hex 64 3) 1.012)
  ?>  =(%accepted status.update)
  ?>  =(original (~(got by definitions.next.update) [(id 501) 1]))
  ?>  =(1 runtime-revision.original)
  ?>  =((hex 64 1) policy-digest:(~(got by runtimes.next.update) [(id 401) 1]))
  ?>  =((hex 64 3) policy-digest:(~(got by runtimes.next.update) [(id 401) 2]))
  =/  revised  (definition-put:stead-principals next.update ~zod ~zod (id 501) 1 (id 103) (hex 64 4) (id 401) 2 1.013)
  ?>  =(%accepted status.revised)
  ?>  =(original (~(got by definitions.next.revised) [(id 501) 1]))
  ?>  =(2 runtime-revision:(~(got by definitions.next.revised) [(id 501) 2]))
  ~
++  test-principals-workers-cannot-update-runtime-or-transfer-definition-owner
  ^-  tang
  =/  second  (declare:stead-principals db ~zod ~zod (id 104) 0 %agent 'Second worker' & 1.010)
  =/  denied  (runtime-put:stead-principals next.second ~nec ~zod (id 401) 0 (id 103) 'self-expanded-policy' (hex 64 1) 1.011)
  ?>  =([%denied next.second] denied)
  =/  runtime  (runtime-put:stead-principals next.second ~zod ~zod (id 401) 0 (id 103) 'docs-worker/1' (hex 64 1) 1.011)
  =/  transferred  (runtime-put:stead-principals next.runtime ~zod ~zod (id 401) 1 (id 104) 'docs-worker/2' (hex 64 2) 1.012)
  ?>  =([%ownership-conflict next.runtime] transferred)
  =/  foreign  (definition-put:stead-principals next.runtime ~zod ~zod (id 501) 0 (id 104) (hex 64 3) (id 401) 1 1.012)
  ?>  =([%invalid next.runtime] foreign)
  =/  definition  (definition-put:stead-principals next.runtime ~zod ~zod (id 501) 0 (id 103) (hex 64 3) (id 401) 1 1.012)
  =/  other-runtime  (runtime-put:stead-principals next.definition ~zod ~zod (id 402) 0 (id 104) 'docs-worker/1' (hex 64 1) 1.013)
  =/  transfer  (definition-put:stead-principals next.other-runtime ~zod ~zod (id 501) 1 (id 104) (hex 64 3) (id 402) 1 1.014)
  ?>  =([%ownership-conflict next.other-runtime] transfer)
  ~
++  test-principals-definition-rejects-missing-version-and-disabled-agent
  ^-  tang
  =/  runtime  (runtime-put:stead-principals db ~zod ~zod (id 401) 0 (id 103) 'docs-worker/1' (hex 64 1) 1.010)
  =/  missing  (definition-put:stead-principals next.runtime ~zod ~zod (id 501) 0 (id 103) (hex 64 2) (id 401) 2 1.011)
  ?>  =([%invalid next.runtime] missing)
  =/  disabled  (declare:stead-principals next.runtime ~zod ~zod (id 103) 2 %agent 'Docs worker' | 1.012)
  =/  denied  (definition-put:stead-principals next.disabled ~zod ~zod (id 501) 0 (id 103) (hex 64 2) (id 401) 1 1.013)
  ?>  =([%invalid next.disabled] denied)
  =/  unknown  (runtime-put:stead-principals imported ~zod ~zod (id 401) 0 (id 103) 'docs-worker/1' (hex 64 1) 1.010)
  ?>  =([%invalid imported] unknown)
  ~
--

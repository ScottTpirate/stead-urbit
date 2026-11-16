::  PRIVATE authored reducer fixtures. No compiler/registration claim.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-team-config, stead-principals, stead-actor, stead-session, stead-project-retirement, stead-repository-catalog, stead-repository-authority, stead-code-credentials
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  put
  |=  [value=json key=@t item=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key item)]
++  person
  |=  [principal=@ud binding=@ud revision=@ud active=@t expires=@ud display=@t]
  ^-  json
  (object ~[['principal_id' (id principal)] ['binding_id' (id binding)] ['binding_revision' (decimal revision)] ['active' active] ['expires_at_ms' (decimal expires)] ['display_name' display]])
++  config-wire
  |=  [prior=registry:stead-team-config people=(map @t json)]
  ^-  @t
  =/  raw
    %-  object
    :~  ['protocol' 'stead.team-config/1']
        ['expected_revision' (decimal ?~(current.prior 0 revision.u.current.prior))]
        ['home' '~zod']  ['origin' 'https://home.test']
        ['organization_id' '019939ba-4000-7000-8000-000000000005']
        ['team_id' '019939ba-4000-7000-8000-000000000006']
        ['custody' 'local-disposable']  ['runtime' 'isolated-fake']
    ==
  =/  wire  (put (put raw 'bindings' [%o people]) 'project_creators' (object ~[[(id 102) 'yes']]))
  (canonical wire)
++  config
  |=  [prior=registry:stead-team-config people=(map @t json) now=@ud]
  ^-  registry:stead-team-config
  (decode:stead-team-config (config-wire prior people) prior ~zod now)
++  command
  |=  [request=@ud project=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  raw  (object ~[['protocol' 'stead.command/3'] ['request_id' (id request)] ['project_id' (id project)] ['resource_id' (id resource)] ['expected_revision' (decimal revision)] ['authority_epoch' '1'] ['operation' operation]])
  (decode:stead-team-codec (canonical (put raw 'payload' (object payload))))
++  project-command
  |=  [request=@ud project=@ud name=@t]
  ^-  command:stead-codec
  (command request project project 0 'project.create' ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' name] ['project_key' name] ['preset' 'general']])
++  accepted
  |=  out=transition:stead-team
  ^-  state:stead-team
  =/  value  (need (parse-result response.out))
  ?>  ?=([%o *] value)
  ?>  =('accepted' (field p.value 'status'))
  next.out
++  wire
  |=  [request=@ud project=@ud repository=@ud revision=@ud name=@t]
  ^-  @t
  (canonical (object ~[['request_id' (id request)] ['project_id' (id project)] ['repository_id' (id repository)] ['expected_catalog_revision' (decimal revision)] ['authority_epoch' '1'] ['display_name' name]]))
++  login
  |=  [state=snapshot:stead-repository-authority sender=@p now=@ud]
  ^-  result:stead-session
  =/  context  (need (native-context:stead-team db.state sender now))
  =/  begun  (begin:stead-session sessions.state identity.context home.state 'https://home.test' now 0x111)
  ?>  =(%pending status.begun)
  =/  challenge  (~(got by challenges.next.begun) id.begun)
  =/  approved  (approve:stead-session next.begun id.begun sender identity.context home.state 'https://home.test' 'stead.auth/1' 'member-session' expires.challenge +(now))
  ?>  =(%approved status.approved)
  =/  consumed  (consume:stead-session next.approved id.begun cookie.begun identity.context home.state 'https://home.test' (add now 2) 0x222)
  ?>  =(%accepted status.consumed)
  consumed
--
=/  bindings
  %-  malt
  :~  ['~bus' (person 102 202 1 'yes' 9.999.999 'Alice')]
      ['~nec' (person 103 203 1 'yes' 9.999.999 'Bob')]
      ['~bud' (person 104 204 1 'yes' 9.999.999 'Carol')]
      ['~wes' (person 105 205 1 'yes' 9.999.999 'Outside')]
  ==
=/  initial=state:stead-team
  (configure:stead-team empty:stead-team (config-wire *registry:stead-team-config bindings) ~zod 1.000)
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  bob  (need (native-context:stead-team initial ~nec 1.001))
=/  carol  (need (native-context:stead-team initial ~bud 1.001))
=/  one  (accepted (apply-command:stead-team initial alice (project-command 301 100 'ONE') 1.002))
=/  two  (accepted (apply-command:stead-team one alice (project-command 302 101 'TWO') 1.003))
=/  editor  (accepted (apply-command:stead-team two alice (command 303 100 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' (id 103)] ['role' 'contributor'] ['expires_at_ms' '8000000']]) 1.004))
=/  db  (accepted (apply-command:stead-team editor alice (command 304 100 100 2 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' (id 104)] ['role' 'reader'] ['expires_at_ms' '5000']]) 1.005))
=/  imported  (import:stead-principals registry.db ~zod)
=/  a  (declare:stead-principals imported ~zod ~zod (id 102) 1 %person 'Alice' & 1.010)
=/  b  (declare:stead-principals next.a ~zod ~zod (id 103) 1 %person 'Bob' & 1.011)
=/  c  (declare:stead-principals next.b ~zod ~zod (id 104) 1 %person 'Carol' & 1.012)
=/  d  (declare:stead-principals next.c ~zod ~zod (id 105) 1 %person 'Outside' & 1.013)
?>  ?&  =(%accepted status.a)  =(%accepted status.b)
        =(%accepted status.c)  =(%accepted status.d)
    ==
=/  base=snapshot:stead-repository-authority  [~zod db next.d *catalog:stead-repository-catalog ~ *state:stead-session]
=/  raw  (wire 701 100 210 0 'Source')
=/  first  (create:stead-repository-authority base [%native ~bus] raw 1.500)
?>  ?=(%accepted -.first)
=/  first-state  base(repositories next.first)
=/  second  (create:stead-repository-authority first-state [%native ~bus] (wire 702 100 211 1 'Docs') 1.501)
?>  ?=(%accepted -.second)
=/  second-state  base(repositories next.second)
=/  third  (create:stead-repository-authority second-state [%native ~bus] (wire 703 101 212 2 'Other project') 1.502)
?>  ?=(%accepted -.third)
=/  state  base(repositories next.third)
=/  target=ref:stead-repository-catalog  [(id 100) (id 210)]
=/  destination=scope:stead-code-credentials  [~zod (id 100) (id 210) 1]
|%
++  test-repository-authority-current-human-roles-and-two-repos
  ^-  tang
  =/  primary  (need (resolve:stead-repository-authority state [%native ~bus] target %manage 2.000))
  =/  other  (need (resolve:stead-repository-authority state [%native ~nec] [(id 100) (id 211)] %write 2.000))
  ?>  ?&  =(destination destination.primary)
          =([~zod (id 100) (id 211) 1] destination.other)
          =(%inline-sha1-v1 profile.primary)
          ?=(^ (resolve:stead-repository-authority state [%native ~bud] target %read 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~bud] target %write 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~nec] target %manage 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~wes] target %read 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~zod] target %manage 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~bus] [(id 101) (id 210)] %read 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~nec] [(id 101) (id 212)] %read 2.000))
          ?=(~ (resolve:stead-repository-authority state [%native ~bus] [(id 100) (id 299)] %read 2.000))
          =([%denied %denied-or-not-found] (create:stead-repository-authority state [%native ~nec] (wire 704 100 213 3 'Not manager') 2.000))
      ==
  ~
++  test-repository-authority-nonhuman-and-unresolved-denied
  ^-  tang
  ::  Each kind is declared on its own imported branch, never rewritten.
  =/  agent  (declare:stead-principals imported ~zod ~zod (id 102) 1 %agent 'Alice' & 2.000)
  =/  service  (declare:stead-principals imported ~zod ~zod (id 102) 1 %service 'Alice' & 2.000)
  =/  disabled  (declare:stead-principals principals.state ~zod ~zod (id 102) 2 %person 'Alice' | 2.000)
  =/  scope=scope:stead-actor  [~zod (id 100) 1 (id 110) '' '' (silt ~[%work-read])]
  ::  Explicit typed-tag negative, not a verified service credential.
  =/  tagged=verified:stead-actor  [%service [(id 102) (id 202) 1 (hex 64 1) 1 (hex 64 2) (hex 64 3) 3.000 scope]]
  ?>  ?=(~ (human:stead-repository-authority state tagged 2.001))
  =/  candidates=(list state:stead-principals)  ~[imported next.agent next.service next.disabled]
  =/  logged  (login state ~bus 2.000)
  |-
  ?~  candidates  ~
  =/  current  state(principals i.candidates, sessions next.logged)
  ?>  ?&  ?=(~ (native:stead-repository-authority current ~bus 2.003))
          ?=(~ (browser:stead-repository-authority current cookie.logged csrf.logged 2.003))
          ?=(~ ((current:stead-repository-authority current [%native ~bus]) identity.alice (id 100) 2.003))
          ?=(~ ((member:stead-repository-authority current 2.003) ~bus))
          =([%| %denied] (issue:stead-repository-authority current *ledger:stead-code-credentials [%native ~bus] target & 2.003 0x333))
      ==
  $(candidates t.candidates)
++  test-repository-authority-browser-possession-and-current-session
  ^-  tang
  =/  logged  (login state ~bus 2.000)
  =/  current  state(sessions next.logged)
  =/  source=source:stead-repository-authority  [%browser cookie.logged csrf.logged]
  =/  actor  (need (authenticate:stead-repository-authority current source 2.003))
  =/  saved  (~(got by sessions.next.logged) (digest:stead-session 'stead.session/1' cookie.logged))
  =/  resumed  (resume:stead-session next.logged cookie.logged identity.alice ~zod 'https://home.test' 2.004 0x444)
  ?>  =(%authenticated status.resumed)
  =/  fresh  current(sessions next.resumed)
  =/  out  (logout:stead-session next.resumed cookie.logged csrf.resumed identity.alice ~zod 'https://home.test' 2.005)
  ?>  =(%logged-out status.out)
  =/  gone  current(sessions next.out)
  ::  A synthetic changed-origin row is explicitly invalid session evidence.
  =/  wrong  current(sessions next.logged(sessions (~(put by sessions.next.logged) (digest:stead-session 'stead.session/1' cookie.logged) saved(origin 'https://other.test'))))
  ?>  ?&  =('native-approved-browser/1' method.actor)
          =(audit.saved audit.actor)  =(expires.saved expires.actor)
          ?=(^ (resolve:stead-repository-authority current source target %read 2.003))
          ?=(~ (browser:stead-repository-authority current (hex 64 0) csrf.logged 2.003))
          ?=(~ (browser:stead-repository-authority current cookie.logged (hex 64 0) 2.003))
          ?=(~ (browser:stead-repository-authority current(home ~nec) cookie.logged csrf.logged 2.003))
          ?=(~ (browser:stead-repository-authority wrong cookie.logged csrf.logged 2.003))
          ?=(~ (browser:stead-repository-authority current cookie.logged csrf.logged expires.saved))
          ?=(~ (authenticate:stead-repository-authority fresh source 2.005))
          ?=(^ (browser:stead-repository-authority fresh cookie.logged csrf.resumed 2.005))
          ?=(~ (authenticate:stead-repository-authority gone source 2.006))
          ?=(~ ((current:stead-repository-authority gone source) identity.actor (id 100) 2.006))
          =([%denied %denied-or-not-found] (create:stead-repository-authority gone source raw 2.006))
          =(repositories.state repositories.gone)
      ==
  ~
++  test-repository-authority-binding-and-grant-changes-refuse-old-actors
  ^-  tang
  =/  issued  (issue:stead-repository-authority state *ledger:stead-code-credentials [%native ~nec] target & 2.000 0x555)
  ?>  ?=(%& -.issued)
  =/  rotated  (config registry.db (~(put by bindings) '~nec' (person 103 213 2 'yes' 9.999.999 'Bob')) 2.001)
  =/  disabled  (config registry.db (~(put by bindings) '~nec' (person 103 203 2 'no' 9.999.999 'Bob')) 2.001)
  =/  removed  (config registry.db (~(del by bindings) '~nec') 2.001)
  =/  current  state(db db(registry rotated))
  =/  fresh  (need (native:stead-repository-authority current ~nec 2.002))
  =/  revoked  (accepted (apply-command:stead-team db alice (command 305 100 100 3 'policy.revoke' ~[['grant_id' (id 501)]]) 2.001))
  ?>  ?&  ?=(~ ((current:stead-repository-authority current [%native ~nec]) identity.bob (id 100) 2.002))
          ?=(^ (resolve:stead-repository-authority current [%native ~nec] target %write 2.002))
          ?=(~ (check:stead-repository-authority current next.p.issued bearer.p.issued destination %read 2.002))
          ?=(~ (native:stead-repository-authority state(db db(registry disabled)) ~nec 2.002))
          ?=(~ (native:stead-repository-authority state(db db(registry removed)) ~nec 2.002))
          ?=(~ (resolve:stead-repository-authority state(db revoked) [%native ~nec] target %read 2.002))
          ?=(~ (check:stead-repository-authority state(db revoked) next.p.issued bearer.p.issued destination %read 2.002))
          ?=(~ (resolve:stead-repository-authority state [%native ~bud] target %read 5.000))
          ?=(~ ((current:stead-repository-authority current [%native ~nec]) identity.fresh(expires +(expires.identity.fresh)) (id 100) 2.002))
          ?=(~ ((current:stead-repository-authority current [%native ~nec]) identity.fresh(active |) (id 100) 2.002))
          ?=(~ ((current:stead-repository-authority current [%native ~nec]) identity.fresh(ship ~bud) (id 100) 2.002))
      ==
  ~
++  test-repository-authority-credentials-exact-scope-and-expiry
  ^-  tang
  =/  issued  (issue:stead-repository-authority state *ledger:stead-code-credentials [%native ~bus] target & 2.000 0x666)
  =/  read-only  (issue:stead-repository-authority state *ledger:stead-code-credentials [%native ~bud] target | 2.000 0x777)
  ?>  &(?=(%& -.issued) ?=(%& -.read-only))
  =/  revoked  (revoke:stead-code-credentials next.p.issued handle.p.issued identity.alice ~zod 2.001)
  ?>  ?=(%& -.revoked)
  =/  logged  (login state ~bus 2.000)
  =/  current  state(sessions next.logged)
  ::  Near actual session end makes its bound shorter than the15min cap.
  =/  saved  (~(got by sessions.next.logged) (digest:stead-session 'stead.session/1' cookie.logged))
  =/  late  (sub expires.saved 100)
  =/  browser-issued  (issue:stead-repository-authority current *ledger:stead-code-credentials [%browser cookie.logged csrf.logged] target & late 0x888)
  ?>  ?=(%& -.browser-issued)
  =/  logout  (logout:stead-session next.logged cookie.logged csrf.logged identity.alice ~zod 'https://home.test' +(late))
  ?>  =(%logged-out status.logout)
  ?>  ?&  =(902.000 expires.p.issued)
          =(expires.saved expires.p.browser-issued)
          ?=(^ (check:stead-repository-authority state next.p.issued bearer.p.issued destination %write 2.001))
          ?=(~ (check:stead-repository-authority state next.p.issued bearer.p.issued destination(repository (id 211)) %read 2.001))
          ?=(~ (check:stead-repository-authority state next.p.issued bearer.p.issued destination(project (id 101)) %read 2.001))
          ?=(~ (check:stead-repository-authority state next.p.issued bearer.p.issued destination(home ~nec) %read 2.001))
          ?=(~ (check:stead-repository-authority state next.p.issued bearer.p.issued destination(epoch 2) %read 2.001))
          ?=(^ (check:stead-repository-authority state next.p.read-only bearer.p.read-only destination %read 2.001))
          ?=(~ (check:stead-repository-authority state next.p.read-only bearer.p.read-only destination %write 2.001))
          ?=(~ (check:stead-repository-authority state next.p.issued bearer.p.issued destination %read expires.p.issued))
          ?=(~ (check:stead-repository-authority state p.revoked bearer.p.issued destination %read 2.002))
          ?=(^ (check:stead-repository-authority current(sessions next.logout) next.p.browser-issued bearer.p.browser-issued destination %read (add late 2)))
      ==
  ~
++  test-repository-authority-retirement-and-lifecycle
  ^-  tang
  =/  tip  (need (head:stead-project-retirement data.db (id 100)))
  =/  request=intent:stead-project-retirement  [(id 100) (id 900) 1 ~nec tip]
  =/  retired  (need (retire:stead-project-retirement ~zod data.db ~ request 2.000))
  =/  current  state(retired retired)
  ?>  (validate:stead-project-retirement ~zod data.db retired)
  ::  Structural lifecycle negatives; no new close/tombstone command claimed.
  =/  row  (~(got by entries.repositories.state) (id 210))
  =/  tomb  state(repositories repositories.state(entries (~(put by entries.repositories.state) (id 210) row(lifecycle %tombstone))))
  =/  project  (~(got by projects.data.db) (id 100))
  =/  closed  state(db db(data data.db(projects (~(put by projects.data.db) (id 100) project(policy 18.446.744.073.709.551.615)))))
  =/  bad  current(retired (~(put by retired) (id 100) [request(journal-head (hex 64 0)) 2.000]))
  ?>  ?&  ?=(^ (resolve:stead-repository-authority current [%native ~bud] target %read 2.001))
          ?=(~ (resolve:stead-repository-authority current [%native ~bus] target %write 2.001))
          ?=(~ (resolve:stead-repository-authority current [%native ~bus] target %manage 2.001))
          ?=(^ (resolve:stead-repository-authority current [%native ~bus] [(id 101) (id 212)] %write 2.001))
          =([%denied %denied-or-not-found] (create:stead-repository-authority current [%native ~bus] raw 2.001))
          =([%denied %denied-or-not-found] (create:stead-repository-authority current [%native ~bus] (wire 704 100 213 3 'Retired') 2.001))
          ?=(~ (resolve:stead-repository-authority tomb [%native ~bus] target %read 2.001))
          ?=(~ (resolve:stead-repository-authority closed [%native ~bus] target %read 2.001))
          ?=(~ (resolve:stead-repository-authority bad [%native ~bus] target %read 2.001))
      ==
  ~
++  test-repository-authority-current-before-original-create-replay
  ^-  tang
  =/  replay  (create:stead-repository-authority state [%native ~bus] raw 2.000)
  ?>  ?=(%replayed -.replay)
  ?>  ?&  =(repositories.state next.replay)  =(receipt.first receipt.replay)
          =(row.first row.replay)  =(1 revision.receipt.replay)
      ==
  =/  changed  (wire 701 100 210 0 'Different bytes')
  =/  disabled  (declare:stead-principals principals.state ~zod ~zod (id 102) 2 %person 'Alice' | 2.000)
  ::  Give Bob an actual maintainer grant before testing cross-principal retry.
  =/  managed  (accepted (apply-command:stead-team db alice (command 306 100 100 3 'policy.grant' ~[['grant_id' (id 503)] ['principal_id' (id 103)] ['role' 'maintainer'] ['expires_at_ms' '8000000']]) 2.000))
  =/  lost  (accepted (apply-command:stead-team managed bob (command 307 100 100 4 'policy.revoke' ~[['grant_id' (id 301)]]) 2.001))
  ?>  ?&  =([%denied %request-id-reuse] (create:stead-repository-authority state [%native ~bus] changed 2.001))
          =([%denied %denied-or-not-found] (create:stead-repository-authority state [%native ~nec] raw 2.001))
          =([%denied %request-id-reuse] (create:stead-repository-authority state(db managed) [%native ~nec] raw 2.001))
          =([%denied %denied-or-not-found] (create:stead-repository-authority state(principals next.disabled) [%native ~bus] raw 2.001))
          =([%denied %denied-or-not-found] (create:stead-repository-authority state(db lost) [%native ~bus] raw 2.002))
          =(identity.alice actor.receipt.replay)
      ==
  ~
++  test-repository-authority-missing-and-forged-snapshot-boundaries
  ^-  tang
  =/  no-project  state(db db(data data.db(projects (~(del by projects.data.db) (id 100)))))
  =/  broken  state(repositories repositories.state(revision 4))
  =/  typed  (create:stead-repository-authority state [%native ~bus] (wire 705 100 100 3 'Typed ID equality') 2.000)
  ?>  ?=(%accepted -.typed)
  =/  equal  state(repositories next.typed)
  ?>  ?&  ?=(~ (native:stead-repository-authority state(db empty:stead-team) ~bus 2.001))
          ?=(~ (native:stead-repository-authority state(principals *state:stead-principals) ~bus 2.001))
          ?=(~ (native:stead-repository-authority state(home ~nec) ~bus 2.001))
          ?=(~ (resolve:stead-repository-authority no-project [%native ~bus] target %read 2.001))
          ?=(~ (resolve:stead-repository-authority state(repositories *catalog:stead-repository-catalog) [%native ~bus] target %read 2.001))
          ?=(~ (resolve:stead-repository-authority broken [%native ~bus] target %read 2.001))
          ?=(~ ((current:stead-repository-authority state [%native ~bus]) identity.bob (id 100) 2.001))
          ?=(~ ((current:stead-repository-authority state [%native ~bus]) identity.alice(revision 99) (id 100) 2.001))
          ?=(^ (resolve:stead-repository-authority equal [%native ~bus] [(id 100) (id 100)] %read 2.001))
          ?=(~ (legacy-resolve:stead-repository-authority equal [%native ~bus] (id 100) %read 2.001))
          !legacy-alias.row.typed
          =(3 revision.repositories.state)
      ==
  ~
--

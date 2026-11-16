::  PRIVATE authored pure tests, not registered or compiled.
/+  *test, stead-codec, stead-core, stead-session, stead-code-credentials, stead-code-store, stead-repository-catalog
=,  stead-repository-catalog
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal:stead-codec n)))
++  wire
  |=  [request=@ud project=@ud repository=@ud revision=@ud epoch=@ud name=@t]
  ^-  @t
  (canonical:stead-codec (object:stead-codec ~[['request_id' (id request)] ['project_id' (id project)] ['repository_id' (id repository)] ['expected_catalog_revision' (decimal:stead-codec revision)] ['authority_epoch' (decimal:stead-codec epoch)] ['display_name' name]]))
++  changed
  |=  [raw=@t key=@t replacement=@t]
  ^-  @t
  =/  value  (need (parse:stead-codec raw))
  ?>  ?=([%o *] value)
  (canonical:stead-codec [%o (~(put by p.value) key [%s replacement])])
--
=/  alice=actor:stead-session  [~bus (id 102) (id 202) 1 & 1.000.000]
=/  bob=actor:stead-session  [~nec (id 103) (id 203) 1 & 1.000.000]
=>
|%
++  facts-for
  ::  Abstract trusted callback only; no claim of concrete Home authorization.
  |=  [rank=@ud epoch=@ud retired=?]
  ^-  current
  |=  [who=actor:stead-session project=@t now=@ud]
  ^-  (unit facts)
  ?.  |((same-actor:stead-session who alice) (same-actor:stead-session who bob))  ~
  ?.  |(=(project (id 100)) =(project (id 101)))  ~
  [~ ~zod epoch rank retired]
++  no-facts
  ^-  current
  |=  [who=actor:stead-session project=@t now=@ud]
  *(unit facts)
++  one
  ^-  decision
  (create *catalog (wire 301 100 210 0 1 'Source') alice 1.000 (facts-for 3 1 |))
++  base
  ^-  catalog
  =/  first  one
  ?>  ?=(%accepted -.first)
  next.first
++  two
  ^-  decision
  (create base (wire 302 100 211 1 1 'Docs') alice 1.001 (facts-for 3 1 |))
--
|%
++  test-repository-catalog-two-repos-exact-inline-profile
  ^-  tang
  =/  first  one
  =/  second  two
  ?>  &(?=(%accepted -.first) ?=(%accepted -.second))
  ?>  (valid next.second)
  ?>  &(=(2 revision.next.second) =(2 ~(wyt by entries.next.second)))
  ?>  &(=(%inline-sha1-v1 profile.row.first) =(%inline-sha1-v1 profile.row.second))
  ?>  =((empty:stead-code-store [~zod (id 100) (id 210) 1]) initial.first)
  ?>  =((empty:stead-code-store [~zod (id 100) (id 211) 1]) initial.second)
  ?>  ?=(^ (resolve next.second [(id 100) (id 210)] alice %manage 1.002 (facts-for 3 1 |)))
  ?>  ?=(^ (resolve next.second [(id 100) (id 211)] alice %write 1.002 (facts-for 2 1 |)))
  ?>  ?=(~ (resolve next.second [(id 101) (id 210)] alice %read 1.002 (facts-for 3 1 |)))
  ?>  ?=(~ (~(get by entries.next.second) (id 101)))
  ~
++  test-repository-catalog-typed-ids-never-infer-alias
  ^-  tang
  =/  first  (create *catalog (wire 303 100 101 0 1 'Typed equality') alice 1.000 (facts-for 3 1 |))
  ?>  ?=(%accepted -.first)
  ?>  !legacy-alias.row.first
  ?>  ?=(~ (legacy-resolve next.first (id 101) alice %read 1.001 (facts-for 3 1 |)))
  ?>  ?=(^ (resolve next.first [(id 100) (id 101)] alice %read 1.001 (facts-for 3 1 |)))
  ?>  =([%denied %repository-id-reuse] (create next.first (wire 304 101 101 1 1 'Already retained') alice 1.001 (facts-for 3 1 |)))
  ?>  =([%denied %request-id-reuse] (create next.first (wire 303 101 212 1 1 'Other project') alice 1.001 (facts-for 3 1 |)))
  ~
++  test-repository-catalog-retry-is-original-and-current-authorized
  ^-  tang
  =/  first  one
  =/  second  two
  ?>  &(?=(%accepted -.first) ?=(%accepted -.second))
  =/  raw  (wire 301 100 210 0 1 'Source')
  =/  replay  (create next.second raw alice 2.000 (facts-for 3 2 |))
  ?>  ?=(%replayed -.replay)
  ?>  &(=(next.second next.replay) =(receipt.first receipt.replay) =(row.first row.replay))
  ?>  =([%denied %request-id-reuse] (create next.second (changed raw 'display_name' 'Changed') alice 2.000 (facts-for 3 2 |)))
  ?>  =([%denied %request-id-reuse] (create next.second raw bob 2.000 (facts-for 3 2 |)))
  ?>  =([%denied %denied-or-not-found] (create next.second raw alice 2.000 no-facts))
  ?>  =([%denied %denied-or-not-found] (create next.second raw alice 2.000 (facts-for 0 2 |)))
  ?>  =([%denied %denied-or-not-found] (create next.second raw alice 1.000.000 (facts-for 3 2 |)))
  ~
++  test-repository-catalog-resolver-authority-cas-retirement
  ^-  tang
  =/  raw  (wire 302 100 211 1 1 'Docs')
  ?>  =([%denied %denied-or-not-found] (create base raw alice 1.001 no-facts))
  ?>  =([%denied %denied-or-not-found] (create base raw alice(active |) 1.001 (facts-for 3 1 |)))
  ?>  =([%denied %denied-or-not-found] (create base raw alice 1.001 (facts-for 1 1 |)))
  ?>  =([%denied %denied-or-not-found] (create base raw alice 1.001 (facts-for 2 1 |)))
  ?>  =([%denied %denied-or-not-found] (create base raw alice 1.001 (facts-for 3 1 &)))
  ?>  =([%denied %authority-epoch-conflict] (create base raw alice 1.001 (facts-for 3 2 |)))
  ?>  =([%denied %revision-conflict] (create base (changed raw 'expected_catalog_revision' '0') alice 1.001 (facts-for 3 1 |)))
  ?>  =([%denied %invalid-time] (create base raw alice 0 (facts-for 3 1 |)))
  ?>  ?=(~ (resolve base [(id 100) (id 212)] alice %read 1.001 (facts-for 3 1 |)))
  ?>  ?=(~ (resolve base [(id 100) (id 210)] alice %write 1.001 (facts-for 1 1 |)))
  ?>  ?=(~ (resolve base [(id 100) (id 210)] alice %manage 1.001 (facts-for 2 1 |)))
  ?>  ?=(~ (resolve base [(id 100) (id 210)] alice %write 1.001 (facts-for 3 1 &)))
  ?>  ?=(^ (resolve base [(id 100) (id 210)] alice %read 1.001 (facts-for 1 1 &)))
  ~
++  test-repository-catalog-global-retained-capacity-no-eviction
  ^-  tang
  =/  imported=catalog
    :*  2
        (malt ~[[(id 200) [(id 200) '' 1 %inline-sha1-v1 %tombstone & [%legacy]]] [(id 201) [(id 201) '' 1 %external-sha1-pack-v1 %active & [%legacy]]]])
        ~
    ==
  ?>  (valid imported)
  =/  third  (create imported (wire 305 100 212 2 1 'Third') alice 1.000 (facts-for 3 1 |))
  ?>  ?=(%accepted -.third)
  =/  fourth  (create next.third (wire 306 101 213 3 1 'Fourth') alice 1.001 (facts-for 3 1 |))
  ?>  ?=(%accepted -.fourth)
  ?>  (valid next.fourth)
  ?>  =([%denied %capacity-exceeded] (create next.fourth (wire 307 101 214 4 1 'Fifth') alice 1.002 (facts-for 3 1 |)))
  ?>  =((~(got by entries.imported) (id 200)) (~(got by entries.next.fourth) (id 200)))
  ?>  =((~(got by entries.imported) (id 201)) (~(got by entries.next.fourth) (id 201)))
  ?>  ?=(~ (resolve next.fourth [(id 200) (id 200)] alice %read 1.003 (facts-for 3 1 |)))
  ~
++  test-repository-catalog-closed-codec-and-receipt-closure
  ^-  tang
  =/  raw  (wire 301 100 210 0 1 'Source')
  =/  cmd  (decode raw)
  ?>  =(raw canonical-bytes.cmd)
  ?>  =(digest.cmd '94c8b51c60e99a2bb461343de4379cd99ae8d8047a480104a9c75c93046cef4a')
  ?>  =([%denied %invalid-command] (create *catalog (changed raw 'profile' 'external-sha1-pack-v1') alice 1.000 (facts-for 3 1 |)))
  ?>  =([%denied %invalid-command] (create *catalog (changed raw 'authority_epoch' '0') alice 1.000 (facts-for 3 1 |)))
  ?>  =([%denied %invalid-command] (create *catalog (changed raw 'expected_catalog_revision' '00') alice 1.000 (facts-for 3 1 |)))
  ?>  =([%denied %invalid-command] (create *catalog (changed raw 'repository_id' 'not-a-uuid') alice 1.000 (facts-for 3 1 |)))
  ?>  =([%denied %invalid-command] (create *catalog (changed raw 'display_name' '') alice 1.000 (facts-for 3 1 |)))
  =/  duplicate  (cat 3 '{"request_id":"x",' (cut 3 [1 (dec (met 3 raw))] raw))
  ?>  =([%denied %invalid-command] (create *catalog duplicate alice 1.000 (facts-for 3 1 |)))
  =/  large  (rap 3 (reap 2.049 'x'))
  ?>  =([%denied %invalid-command] (create *catalog large alice 1.000 (facts-for 3 1 |)))
  =/  first  one
  ?>  ?=(%accepted -.first)
  =/  corrupt  next.first(creates (~(put by creates.next.first) (id 301) receipt.first(version 2)))
  ?>  !(valid corrupt)
  ?>  =([%denied %invalid-catalog] (create corrupt raw alice 1.001 (facts-for 3 1 |)))
  ?>  !(valid next.first(creates ~))
  ?>  !(valid next.first(revision 2))
  ~
--

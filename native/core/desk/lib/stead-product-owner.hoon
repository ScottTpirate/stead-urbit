::  Reserved owner preparation, not a live commit path. A caller must append
::  the returned typed record to the ONE product timeline atomically with next,
::  or discard the entire result. No independent owner event journal exists.
::  The sender is actual verified Gall context, never decoded command data.
/+  stead-codec, stead-core, stead-team, stead-principals, stead-product-state, stead-product-migrate, stead-product-owner-codec, stead-product-owner-policy
=,  stead-codec
|%
+$  attempt  [digest=@t operation=@t command=@t receipt=@t security=?]
+$  ledger  (map @t attempt)
+$  state
  [db=state:stead-team product=state:stead-product-state catalog=state:stead-principals ledger=ledger]
+$  budget
  ::  Counts from other authoritative typed ledgers, supplied by Home only.
  [ordinary=@ud security=@ud]
+$  result  [response=@t next=state record=(unit @t)]
+$  decision  [next=state error=@t reducing=?]
++  initialize
  |=  [pair=migrated:stead-product-migrate home=@p]
  ^-  state
  =/  boundary  (need migration.product.pair)
  ?>  &(=(registry.db.pair predecessor-registry.boundary) ?=(~ events.product.pair))
  [db.pair product.pair (import:stead-principals registry.db.pair home) ~]
++  revision
  |=  [state=state cmd=command:stead-product-owner-codec]
  ^-  @ud
  ?:  =('home.configure' operation.cmd)
    ?~(current.registry.db.state 0 revision.u.current.registry.db.state)
  ?:  =('principal.declare' operation.cmd)
    =/  found  (~(get by principals.catalog.state) (field payload.cmd 'principal_id'))
    ?~(found 0 revision.u.found)
  =/  head
    ?:  =('runtime.put' operation.cmd)
      (~(get by runtime-heads.catalog.state) (field payload.cmd 'runtime_id'))
    (~(get by definition-heads.catalog.state) (field payload.cmd 'definition_id'))
  ?~(head 0 u.head)
++  deny
  |=  [state=state cmd=command:stead-product-owner-codec error=@t]
  ^-  result
  :*  (canonical (object ~[['protocol' 'stead.owner-receipt/1'] ['status' 'rejected'] ['request_id' request.cmd] ['canonical_sha256' digest.cmd] ['error' error]]))
      state  ~
  ==
++  native-error
  |=  status=@tas
  ^-  @t
  ?:  =(%accepted status)  ''
  ?:  =(%conflict status)  'revision_conflict'
  ?:  =(%capacity status)  'capacity_exceeded'
  ?:  =(%kind-conflict status)  'kind_conflict'
  ?:  =(%ownership-conflict status)  'ownership_conflict'
  'invalid_command'
++  decide
  |=  [state=state cmd=command:stead-product-owner-codec home=@p now=@ud]
  ^-  decision
  ?.  =(expected.cmd (revision state cmd))  [state 'revision_conflict' |]
  ?:  =('home.configure' operation.cmd)
    =/  attempted
      %-  mule
      |.
      =/  db  (configure:stead-team db.state (field payload.cmd 'configuration') home now)
      =/  catalog  (reconcile:stead-product-owner-policy catalog.state registry.db home)
      [db catalog]
    ?:  ?=(%| -.attempted)  [state 'invalid_configuration' |]
    =/  next  state(db -.p.attempted, catalog +.p.attempted)
    [next '' (config-reduces:stead-product-owner-policy registry.db.state registry.db.next now)]
  =/  declared=result:stead-principals
    ?:  =('principal.declare' operation.cmd)
      =/  kind=kind:stead-principals
        ?+  (field payload.cmd 'kind')  !!
          %'person'  %person
          %'agent'  %agent
          %'service'  %service
        ==
      (declare:stead-principals catalog.state home home (field payload.cmd 'principal_id') expected.cmd kind (field payload.cmd 'display_name') =('yes' (field payload.cmd 'active')) now)
    ?:  =('runtime.put' operation.cmd)
      (runtime-put:stead-principals catalog.state home home (field payload.cmd 'runtime_id') expected.cmd (field payload.cmd 'principal_id') (field payload.cmd 'profile') (field payload.cmd 'policy_digest') now)
    (definition-put:stead-principals catalog.state home home (field payload.cmd 'definition_id') expected.cmd (field payload.cmd 'principal_id') (field payload.cmd 'instructions_digest') (field payload.cmd 'runtime_id') (uint (field payload.cmd 'runtime_revision')) now)
  =/  error  (native-error status.declared)
  =/  next  state(catalog next.declared)
  =/  reducing
    ?.  &(=('' error) =('principal.declare' operation.cmd))  |
    (principal-reduces:stead-product-owner-policy catalog.state catalog.next (field payload.cmd 'principal_id'))
  [next error reducing]
++  owner-count
  |=  [ledger=ledger security=?]
  ^-  @ud
  (lent (skim ~(tap by ledger) |=([key=@t val=attempt] =(security security.val))))
++  security-count
  |=  db=state:stead-team
  ^-  @ud
  (lent (skim ~(tap by receipts.data.db) |=([key=[@t @t @t] val=receipt-state:stead-core] =('policy.revoke' operation.val))))
++  prepare
  |=  [prior=state chosen=decision cmd=command:stead-product-owner-codec home=@p sender=@p now=@ud security=?]
  ^-  result
  =/  next  next.chosen
  =/  response
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.owner-receipt/1']  ['status' ?:(=('' error.chosen) 'accepted' 'rejected')]
        ['request_id' request.cmd]  ['canonical_sha256' digest.cmd]  ['operation' operation.cmd]
        ['expected_revision' (decimal expected.cmd)]  ['resulting_revision' (decimal (revision next cmd))]
        ['recorded_at_ms' (decimal now)]  ['error' error.chosen]
        ['capacity_class' ?:(security 'security' 'ordinary')]
    ==
  ?>  (lte (met 3 response) 8.192)
  =/  record
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.owner-journal/1']  ['canonical_command' canonical-bytes.cmd]
        ['receipt' response]  ['home' (scot %p home)]  ['native_sender' (scot %p sender)]
        ['before_registry_digest' (hash 'stead.owner-registry/1' (bytes-hex (jam registry.db.prior)))]
        ['after_registry_digest' (hash 'stead.owner-registry/1' (bytes-hex (jam registry.db.next)))]
        ['before_catalog_digest' (hash 'stead.owner-catalog/1' (bytes-hex (jam catalog.prior)))]
        ['after_catalog_digest' (hash 'stead.owner-catalog/1' (bytes-hex (jam catalog.next)))]
    ==
  ?>  (lte (met 3 record) 262.144)
  =/  stored=attempt  [digest.cmd operation.cmd canonical-bytes.cmd response security]
  [response next(ledger (~(put by ledger.next) request.cmd stored)) (some record)]
++  apply
  |=  [state=state cmd=command:stead-product-owner-codec home=@p sender=@p now=@ud other=budget]
  ^-  result
  ?.  &(=(sender home) ?=(^ current.registry.db.state) =(home home.u.current.registry.db.state))
    (deny state cmd 'owner_required')
  ?~  migration.product.state  (deny state cmd 'migration_required')
  ?.  &((gth now 0) (lte now 18.446.744.073.709.551.615))  (deny state cmd 'invalid_time')
  =/  previous  (~(get by ledger.state) request.cmd)
  ?^  previous
    ?.  =(digest.cmd digest.u.previous)  (deny state cmd 'request_id_reuse')
    [receipt.u.previous state ~]
  ?.  &((lte ordinary.other 4.096) (lte security.other 2.048))
    (deny state cmd 'capacity_exceeded')
  =/  chosen  (decide state cmd home now)
  =/  ordinary
    (add (add (event-count:stead-team db.state '' |) (lent ~(tap by attempts.product.state))) (add (owner-count ledger.state |) ordinary.other))
  =/  security  (gte ordinary 4.096)
  ?:  ?&  security
          ?|  !=('' error.chosen)  !reducing.chosen
              (gte (owner-count ledger.state &) 128)
              (gte (add (security-count db.state) (add (owner-count ledger.state &) security.other)) 2.048)
          ==
      ==
    (deny state cmd 'capacity_exceeded')
  =/  attempted  (mule |.((prepare state chosen cmd home sender now security)))
  ?:  ?=(%| -.attempted)  (deny state cmd 'capacity_exceeded')
  p.attempted
--

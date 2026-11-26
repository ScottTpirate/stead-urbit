::  Native-human-doc/1 lifecycle and sole product mutation dispatcher.
::  This library does not activate a Home. The Gall adapter admits only the
::  explicit disposable, no-Code profile and supplies verified actors/time.
/+  stead-codec, stead-team, stead-team-codec, stead-product-codec, stead-product-state, stead-product-migrate, stead-product-history, stead-product-owner-codec, stead-doc-change-codec, stead-principals, stead-doc-change-state, stead-product-owner, stead-projection, stead-views, stead-product-query, stead-product-home-views, stead-doc-change-query, stead-doc-change-views, stead-doc-change
=,  stead-codec
|%
+$  extras
  $:  product=state:stead-product-state  catalog=state:stead-principals
      ledger=ledger:stead-product-owner  changes=state:stead-doc-change-state
  ==
+$  stage
  $%  [%migrating conversion=job:stead-product-migrate]
      [%restoring validation=job:stead-product-history]
      [%ready retained=extras]
  ==
+$  target
  $%  [%predecessor db=state:stead-team]
      [%product value=state:stead-product-history]
  ==
+$  pair  [db=state:stead-team phase=stage]
+$  transition  [response=@t next=pair]
++  profile  'native-human-doc/1'
++  ready
  |=  phase=stage
  ^-  ?
  ?=(%ready -.phase)
++  current
  |=  data=pair
  ^-  state:stead-product-history
  ?>  ?=(%ready -.phase.data)
  [db.data product.retained.phase.data catalog.retained.phase.data ledger.retained.phase.data changes.retained.phase.data]
++  publish
  |=  value=state:stead-product-history
  ^-  pair
  [db.value [%ready product.value catalog.value ledger.value changes.value]]
++  snapshot
  |=  data=pair
  ^-  target
  ?:  ?=(%migrating -.phase.data)
    [%predecessor legacy.conversion.phase.data]
  ?:  ?=(%restoring -.phase.data)
    [%product target.validation.phase.data]
  [%product (current data)]
++  begin
  |=  [saved=target home=@p]
  ^-  pair
  ?:  ?=(%predecessor -.saved)
    [empty:stead-team [%migrating (begin:stead-product-migrate db.saved home)]]
  [empty:stead-team [%restoring (begin:stead-product-history value.saved home)]]
++  invalid
  |=  phase=stage
  ^-  ?
  ?:  ?=(%migrating -.phase)  =(%invalid phase.conversion.phase)
  ?:  ?=(%restoring -.phase)  =(%invalid phase.validation.phase)
  |
++  step
  |=  [data=pair home=@p]
  ^-  pair
  ?:  ?=(%migrating -.phase.data)
    =/  converted  (step:stead-product-migrate conversion.phase.data)
    ?.  =(%valid phase.converted)  [db.data [%migrating converted]]
    (publish (initialize:stead-product-history (need (result:stead-product-migrate converted)) home))
  ?:  ?=(%restoring -.phase.data)
    =/  restored  (step:stead-product-history validation.phase.data)
    ?.  =(%valid phase.restored)  [db.data [%restoring restored]]
    (publish (need (restored:stead-product-history restored)))
  data
++  rejection
  |=  [domain=@t value=json reason=@t]
  ^-  @t
  ?>  ?=([%o *] value)
  =/  request  (field p.value 'request_id')
  ?>  (uuid request)
  =/  protocol
    ?:  =('stead.command/4' domain)  'stead.receipt/4'
    ?:  =('stead.doc-change/1' domain)  'stead.doc-change-receipt/1'
    'stead.result/3'
  (canonical (object ~[['protocol' protocol] ['status' 'rejected'] ['request_id' request] ['canonical_sha256' (hash domain (canonical value))] ['error' reason]]))
++  command
  ::  The active profile never calls the old raw reducer, even for legacy
  ::  browser/native requests. History rejects all old Work operations.
  |=  [data=pair actor=authentication:stead-team raw=@t now=@ud]
  ^-  transition
  =/  value  (need (parse-product:stead-product-codec raw))
  ?>  ?=([%o *] value)
  =/  domain  (field p.value 'protocol')
  ?>  (~(has in (silt ~['stead.command/3' 'stead.command/4' 'stead.doc-change/1'])) domain)
  ?.  (ready phase.data)  [(rejection domain value 'migration_required') data]
  =/  retained  (current data)
  ?.  (active-member:stead-product-history retained actor now)
    [(rejection domain value 'denied_or_not_found') data]
  =/  applied
    %-  mule
    |.
    ?:  =('stead.command/4' domain)
      (apply-work:stead-product-history retained actor (decode:stead-product-codec raw) now)
    ?:  =('stead.doc-change/1' domain)
      (apply-doc:stead-product-history retained actor (decode:stead-doc-change-codec raw) now)
    (apply-legacy:stead-product-history retained actor (decode:stead-team-codec raw) now)
  ?:  ?=(%| -.applied)  [(rejection domain value 'invalid_command') data]
  [response.p.applied (publish next.p.applied)]
++  owner-command
  ::  Home ownership never becomes a project content grant. The owner reducer
  ::  verifies actual transport sender before durable request lookup.
  |=  [data=pair raw=@t home=@p sender=@p now=@ud]
  ^-  transition
  ?>  &(=(home sender) (ready phase.data))
  =/  applied  (apply-owner:stead-product-history (current data) (decode:stead-product-owner-codec raw) home sender now)
  =/  config  (need current.registry.db.next.applied)
  ?>  &(=('isolated-fake' runtime.config) =('local-disposable' custody.config))
  [response.applied (publish next.applied)]
++  capabilities
  |=  db=state:stead-team
  ^-  @t
  =/  config  (need current.registry.db)
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.capabilities/3']  ['profile' 'configured-team']
      ['product_profile' profile]  ['commands' 'stead.command/3']  ['queries' 'stead.query/3']
      ['work_commands' 'stead.command/4']  ['work_queries' 'stead.query/4']
      ['doc_change_commands' 'stead.doc-change/1']  ['doc_change_queries' 'stead.doc-change-query/1']
      ['devices' 'stead.devices/1']  ['identity_discovery' 'stead.identity-address/1'] ['refresh' 'explicit/1']  ['authentication' 'native-approved-browser/1']
      ['max_request_bytes' '65536']  ['max_response_bytes' '262144']  ['page_size' '20']
      ['runtime' runtime.config]
  ==
++  query
  |=  [data=pair view=state:stead-projection pages=state:stead-views actor=authentication:stead-team raw=@t now=@ud entropy=@]
  ^-  result:stead-views
  ?>  (ready phase.data)
  =/  retained  (current data)
  ?.  (active-member:stead-product-history retained actor now)
    [(error:stead-team 'denied_or_not_found') pages]
  =/  value  (need (parse-product:stead-product-codec raw))
  ?>  ?=([%o *] value)
  =/  domain  (field p.value 'protocol')
  ?:  =('stead.query/4' domain)
    (execute:stead-product-home-views retained pages actor (decode:stead-product-query raw) now entropy)
  ?:  =('stead.doc-change-query/1' domain)
    (execute:stead-doc-change-views [db.retained product.retained changes.retained] catalog.retained pages actor (decode:stead-doc-change-query raw) now entropy deny-run:stead-doc-change)
  ?.  =('stead.query/3' domain)  [(error:stead-team 'unsupported_version') pages]
  =/  decoded  (decode-query:stead-team-codec raw)
  ::  The legacy index covers only these retained v3 resources. It cannot
  ::  make claims about v4 Work, discussion or aggregate activity/search.
  ?.  (~(has in (silt ~['identity' 'projects' 'project' 'containers' 'documents' 'document' 'relations' 'receipt' 'assignees'])) kind.decoded)
    [(error:stead-team 'unsupported_query') pages]
  (execute:stead-views db.retained view pages actor decoded now entropy)
++  projected
  ::  Product Work has no legacy index row. A Doc acceptance contributes its
  ::  real generated v3 save; append every new v3 row in original order.
  |=  [before=state:stead-team after=state:stead-team prior=state:stead-projection]
  ^-  state:stead-projection
  =/  count  (lent journal.data.before)
  ?>  (gte (lent journal.data.after) count)
  =/  added  (sub (lent journal.data.after) count)
  ?>  (lte added 1)
  ?>  =(journal.data.before (slag added journal.data.after))
  ?:  =(added 0)  prior
  ?>  ?=(^ journal.data.after)
  (append:stead-projection prior i.journal.data.after)
--

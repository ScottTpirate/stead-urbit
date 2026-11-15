::  Reserved Work sidecar. No app save envelope currently contains this mold.
::  Authored Work fields remain in the core Work map; this stores revisions,
::  separate immutable discussion and explicit migration provenance only.
/+  stead-codec, stead-team-config
=,  stead-codec
|%
+$  work-key  [project=@t work=@t]
+$  assignment
  $:  principal=@t  display=@t  display-source=?(%registry %unavailable)
      request=@t  authentication=@t  target=@t  resolved=?
  ==
+$  blocked
  [raw-status=@t prior-status=(unit @t) raw-reason=@t resolved=?]
+$  completion
  [principal=@t request=@t execution-revision=@ud execution-digest=@t evidence=@t]
+$  metadata
  $:  work-revision=@ud  execution-revision=@ud  discussion-sequence=@ud
      execution-digest=@t  legacy-assignee=(unit assignment)
      legacy-blocked=(unit blocked)  completion-basis=?(%none %legacy %human %outcomes)
      completion=(unit completion)
  ==
+$  comment
  $:  body=@t  request=@t  principal=@t  identity-ship=@t  accepted-at=@ud
      authentication=@t  receipt=@t  legacy-revision=(unit @ud)
  ==
+$  boundary
  ::  This bounded registry is immutable replay input, never live authority.
  $:  journal-count=@ud  heads=(map @t @t)
      predecessor-registry=registry:stead-team-config
      configuration-digest=@t  timeline-digest=@t  fingerprint=@t
  ==
+$  state
  $:  migration=(unit boundary)  works=(map work-key metadata)
      comments=(map [project=@t work=@t sequence=@ud] comment)
      attempts=(map [project=@t principal=@t request=@t] attempt)
      events=(list event)
  ==
+$  attempt
  [digest=@t resource=@t operation=@t command=@t receipt=@t]
+$  event  [family=?(%v3 %v4) bytes=@t digest=@t]
++  append-event
  |=  [state=state family=?(%v3 %v4) body=@t]
  ^-  state
  =/  boundary  (need migration.state)
  ?>  (lth (lent events.state) 6.144)
  =/  previous  ?~(events.state fingerprint.boundary digest.i.events.state)
  =/  record
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.product-event/1']
        ['sequence' (decimal +((lent events.state)))]
        ['previous_digest' previous]  ['family' ?:(=(family %v3) 'stead.command/3' 'stead.command/4')]
        ['body' body]
    ==
  ?>  (lte (met 3 record) 262.144)
  state(events [[family record (hash 'stead.product-event/1' record)] events.state])
++  boundary-of
  |=  [count=@ud heads=(map @t @t) registry=registry:stead-team-config timeline=@t]
  ^-  boundary
  =/  configuration  (hash 'stead.work-migration-config/1' (bytes-hex (jam registry)))
  =/  strings
    (object ~[['journal_count' (decimal count)] ['configuration_digest' configuration] ['timeline_digest' timeline]])
  ?>  ?=([%o *] strings)
  =/  value  [%o (~(put by p.strings) 'heads' (object ~(tap by heads)))]
  [count heads registry configuration timeline (hash 'stead.work-migration/1' (canonical value))]
++  contract-digest
  |=  [key=work-key revision=@ud data=object-map]
  ^-  @t
  =/  strings
    %-  object
    :~  ['project_id' project.key]  ['work_id' work.key]
        ['execution_contract_revision' (decimal revision)]
        ['title' (field data 'title')]  ['description' (field data 'description')]
        ['acceptance_criteria' (field data 'acceptance_criteria')]
    ==
  ?>  ?=([%o *] strings)
  =/  value  [%o (~(put by p.strings) 'required_outcomes' (~(got by data) 'required_outcomes'))]
  (hash 'stead.work-contract/2' (canonical value))
--

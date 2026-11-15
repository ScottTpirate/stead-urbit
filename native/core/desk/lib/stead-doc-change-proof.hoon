::  Exact accepted shared-Doc outcomes for Work completion. This is a Home
::  internal resolver over reconstructed authoritative state, never wire data.
/+  stead-codec, stead-core, stead-team, stead-product-codec, stead-product-state, stead-product-work, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change
=,  stead-codec
|%
++  flat
  |=  [raw=@t names=(list @t)]
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  ?>  &(=(raw (canonical value)) (keys p.value names))
  ?>  (levy ~(tap by p.value) |=([key=@t value=json] ?=([%s *] value)))
  p.value
++  pair
  |=  [state=state:stead-doc-change output=output:stead-doc-change-state head=head:stead-doc-change-state changed=event:stead-product-state saved=event:stead-product-state]
  ^-  ?
  ?>  ?=(^ acceptance.head)
  =/  accepted  u.acceptance.head
  ?.  &(=(%doc-change family.changed) =(%v3 family.saved))  |
  ?.  ?&  =(event-digest.accepted digest.saved)
          =(digest.saved (hash 'stead.product-event/1' bytes.saved))
          =(digest.changed (hash 'stead.product-event/1' bytes.changed))
      ==
    |
  =/  envelope  (flat bytes.changed ~['protocol' 'sequence' 'previous_digest' 'family' 'body'])
  =/  write  (flat bytes.saved ~['protocol' 'sequence' 'previous_digest' 'family' 'body'])
  ?.  ?&  =('stead.product-event/1' (field envelope 'protocol'))
          =('stead.product-event/1' (field write 'protocol'))
          =('stead.doc-change/1' (field envelope 'family'))
          =('stead.command/3' (field write 'family'))
          =(digest.saved (field envelope 'previous_digest'))
          =(+((uint (field write 'sequence'))) (uint (field envelope 'sequence')))
      ==
    |
  =/  record  (flat (field envelope 'body') ~['protocol' 'canonical_command' 'receipt' 'authentication_context' 'result' 'approval' 'adoption' 'save_command' 'save_receipt' 'save_event' 'save_event_digest'])
  =/  cmd  (decode:stead-doc-change-codec (field record 'canonical_command'))
  =/  native  (~(get by receipts.data.db.state) [project.output principal.identity.actor.accepted (field-result:stead-doc-change receipt.accepted 'request_id')])
  ?~  native  |
  =/  attempt  (~(get by attempts.changes.state) [project.output principal.identity.actor.accepted request.accepted])
  ?~  attempt  |
  ?&  =('stead.doc-change-journal/1' (field record 'protocol'))
      =('change.accept' operation.cmd)  =(request.accepted request.cmd)
      =(project.output project.cmd)  =(work.output work.cmd)  =(change.output change.cmd)
      =(revision.output (uint (field payload.cmd 'result_revision')))
      =(digest.output (field payload.cmd 'result_digest'))
      =(canonical-bytes.cmd (field record 'canonical_command'))
      =(digest.cmd digest.u.attempt)  =(canonical-bytes.cmd command.u.attempt)
      =((field record 'receipt') receipt.u.attempt)
      =('accepted' (field-result:stead-doc-change receipt.u.attempt 'status'))
      =(recorded-at.accepted (uint (field-result:stead-doc-change receipt.u.attempt 'recorded_at_ms')))
      =((authentication-json:stead-team actor.accepted) (field record 'authentication_context'))
      =((output-bytes:stead-doc-change-state output) (field record 'result'))
      =((evidence-bytes:stead-doc-change-state approval.head) (field record 'approval'))
      =((evidence-bytes:stead-doc-change-state adoption.head) (field record 'adoption'))
      =(command.u.native (field record 'save_command'))
      =(receipt.accepted (field record 'save_receipt'))
      =(bytes.saved (field record 'save_event'))
      =(digest.saved (field record 'save_event_digest'))
  ==
++  committed
  |=  [state=state:stead-doc-change output=output:stead-doc-change-state head=head:stead-doc-change-state]
  ^-  ?
  =/  events  events.product.state
  |-
  ?~  events  |
  ?~  t.events  |
  ?:  &(=(%doc-change family.i.events) =(%v3 family.i.t.events))
    =/  checked  (mule |.((pair state output head i.events i.t.events)))
    ?:  ?=([%& %.y] checked)  &
    $(events t.events)
  $(events t.events)
++  accepted
  |=  [state=state:stead-doc-change actor=authentication:stead-team wanted=proof-request:stead-product-work id=@t target=json key=key:stead-doc-change-state head=head:stead-doc-change-state]
  ^-  (unit @t)
  ?.  ?&  =(project.wanted project.key)  =(work.wanted work.head)
          =(%accepted status.head)  ?=(^ acceptance.head)
          ?=(^ approval.head)  ?=([%o *] target)
      ==
    ~
  =/  output  (~(get by results.changes.state) [project.key change.key output-revision.head])
  ?~  output  ~
  =/  saved  u.acceptance.head
  =/  value  u.output
  =/  box  (~(get by boxes.db.state) (field p.target 'collection_id'))
  ?~  box  ~
  ?.  ?&  =(id outcome.value)  =(target target.value)
          =('document' (field p.target 'kind'))
          =(project.wanted (field p.target 'project_id'))
          =(project.wanted project.u.box)  =('shared' visibility.u.box)
          =(project.wanted project.value)  =(work.wanted work.value)
          =(change.key change.value)  =(output-revision.head revision.value)
          =(epoch.wanted epoch.value)  =(execution.wanted execution.value)
          =(digest.wanted execution-digest.value)
          =(output-digest.head digest.value)
          =(digest.value (output-digest:stead-doc-change-state value))
          =(digest.value digest.u.approval.head)
          !=(principal.identity.producer.value principal.identity.actor.u.approval.head)
          =(revision.saved +((uint (field p.target 'expected_revision'))))
          (box-access:stead-team db.state actor project.wanted (field p.target 'collection_id') now.wanted)
          (subject:stead-team db.state actor project.wanted 'document' (field p.target 'collection_id') (field p.target 'document_id') now.wanted)
      ==
    ~
  =/  document  (~(get by documents.data.db.state) [project.wanted (scope-key:stead-core (field p.target 'collection_id') (field p.target 'document_id'))])
  ?~  document  ~
  ?.  =(revision.saved revision.u.document)  ~
  =/  body  (~(get by objects.data.db.state) blob.u.document)
  ?~  body  ~
  ?.  &(=(%blob kind.u.body) =(markdown-sha256.value (markdown-sha256:stead-product-adapters body.u.body)))  ~
  ::  The concrete accepted native write remains in the original receipt map
  ::  and in the single timeline. Neither an authored digest nor a head flag
  ::  alone proves that the Doc was committed.
  =/  receipt  (need (parse-result receipt.saved))
  ?>  ?=([%o *] receipt)
  ?.  =('accepted' (field p.receipt 'status'))  ~
  =/  native  (~(get by receipts.data.db.state) [project.wanted principal.identity.actor.saved (field p.receipt 'request_id')])
  ?~  native  ~
  ?.  ?&  =(receipt.saved bytes.u.native)  =('document.save' operation.u.native)
          =((field p.target 'document_id') resource.u.native)
      ==
    ~
  ?.  (committed state value head)  ~
  =/  evidence
    %-  canonical
    (object ~[['project_id' project.wanted] ['work_id' work.wanted] ['change_id' change.key] ['result_revision' (decimal revision.value)] ['result_digest' digest.value] ['outcome_id' id] ['accepted_request_id' request.saved] ['document_revision' (decimal revision.saved)] ['markdown_sha256' markdown-sha256.value] ['save_event_digest' event-digest.saved]])
  (some (hash 'stead.accepted-doc-outcome/1' evidence))
++  find
  |=  [state=state:stead-doc-change actor=authentication:stead-team wanted=proof-request:stead-product-work id=@t target=json]
  ^-  (unit @t)
  =/  heads  ~(tap by heads.changes.state)
  =/  found=(unit @t)  ~
  |-
  ?~  heads  found
  =/  matched  (accepted state actor wanted id target p.i.heads q.i.heads)
  ?~  matched  $(heads t.heads)
  ::  Ambiguous accepted evidence fails rather than choosing an arbitrary row.
  ?^  found  ~
  $(heads t.heads, found matched)
++  resolve
  |=  [state=state:stead-doc-change actor=authentication:stead-team wanted=proof-request:stead-product-work]
  ^-  (unit proof:stead-product-work)
  ?.  ?&  =(principal.wanted principal.identity.actor)
          (current:stead-team db.state actor now.wanted)
          (gte (role:stead-team db.state actor project.wanted now.wanted) 2)
          (subject:stead-team db.state actor project.wanted 'work' '' work.wanted now.wanted)
          (gth (lent ~(tap by outcomes.wanted)) 0)
          (lte (lent ~(tap by outcomes.wanted)) 16)
      ==
    ~
  =/  current  (~(get by projects.data.db.state) project.wanted)
  ?~  current  ~
  ?.  =(epoch.wanted epoch.u.current)  ~
  =/  outcomes  ~(tap by outcomes.wanted)
  =/  evidence=(list [@t @t])  ~
  |-
  ?~  outcomes
    =/  receipt  (canonical (object evidence))
    ?>  (lte (met 3 receipt) 8.192)
    (some [project.wanted work.wanted epoch.wanted execution.wanted digest.wanted (outcome-digest:stead-product-work outcomes.wanted) receipt])
  =/  checked
    %-  mule
    |.
    (find state actor wanted p.i.outcomes q.i.outcomes)
  ?:  ?=(%| -.checked)  ~
  ?~  p.checked  ~
  $(outcomes t.outcomes, evidence [[p.i.outcomes u.p.checked] evidence])
++  resolver
  |=  [state=state:stead-doc-change actor=authentication:stead-team]
  ^-  proof-resolver:stead-product-work
  |=  wanted=proof-request:stead-product-work
  (resolve state actor wanted)
--

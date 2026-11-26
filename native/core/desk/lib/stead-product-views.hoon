::  Reserved bounded Work/comment reads. Home must finish mixed replay before
::  calling this library. It does not activate a route, mark or saved envelope.
/+  stead-codec, stead-core, stead-team, stead-team-codec, stead-team-config, stead-session, stead-views, stead-product-codec, stead-product-state
=,  stead-codec
|%
+$  row  row:stead-views
+$  result  [response=@t next=state:stead-views]
++  error
  |=  [query=query:stead-team-codec why=@t]
  ^-  @t
  (canonical (object ~[['protocol' 'stead.query-result/4'] ['status' 'rejected'] ['request_id' request.query] ['error' why]]))
++  audience-valid
  |=  [db=state:stead-team project=@t outcomes=object-map]
  ^-  ?
  %+  levy  ~(tap by outcomes)
  |=  [id=@t value=json]
  ?.  ?=([%o *] value)  |
  ?.  &(=('document' (field p.value 'kind')) =(project (field p.value 'project_id')))  |
  =/  box  (~(get by boxes.db) (field p.value 'collection_id'))
  ?~  box  |
  &(=(project project.u.box) =('shared' visibility.u.box))
++  display
  |=  [people=(map @t member:stead-team-config) id=@t]
  ^-  @t
  =/  found  (~(get by people) id)
  ?~(found '' display.u.found)
++  basis
  |=  value=?(%none %legacy %human %outcomes)
  ^-  @t
  ?-  value
    %none  ''
    %legacy  'legacy'
    %human  'human-note'
    %outcomes  'accepted-outcomes'
  ==
++  work-row
  |=  [db=state:stead-team product=state:stead-product-state project=@t id=@t full=? people=(map @t member:stead-team-config)]
  ^-  object-map
  =/  item  (~(got by works.data.db) [project id])
  =/  meta  (~(got by works.product) [project id])
  =/  data  data.item
  =/  out
    %-  fields:stead-views
    :~  ['kind' 'work']  ['project_id' project]  ['resource_id' id]  ['container_id' '']
        ['resource_revision' (decimal revision.item)]
        ['work_revision' (decimal work-revision.meta)]
        ['execution_contract_protocol' 'stead.work-contract/2']
        ['execution_contract_revision' (decimal execution-revision.meta)]
        ['execution_contract_digest' execution-digest.meta]
        ['discussion_sequence' (decimal discussion-sequence.meta)]
        ['title' (field data 'title')]  ['type' (field data 'type')]
        ['status' (field data 'status')]  ['priority' (field data 'priority')]
        ['owner_principal_id' (field data 'owner_principal_id')]
        ['worker_principal_id' (field data 'worker_principal_id')]
        ['owner_display_name' (display people (field data 'owner_principal_id'))]
        ['worker_display_name' (display people (field data 'worker_principal_id'))]
    ==
  ?.  full  (~(put by out) 'snippet' [%s (prefix:stead-views (field data 'description') 160)])
  ?>  (contract:stead-product-codec project id data)
  =/  outcomes  (object-field:stead-product-codec data 'required_outcomes')
  ?>  (audience-valid db project outcomes)
  ?>  =(execution-digest.meta (contract-digest:stead-product-state [project id] execution-revision.meta data))
  =/  legacy-assignee  legacy-assignee.meta
  =/  legacy-blocked  legacy-blocked.meta
  ::  Structured contract data is one canonical JSON string within the bounded
  ::  flat row. Never return raw saved provenance, credentials or proof receipts.
  %-  ~(uni by out)
  %-  fields:stead-views
  :~  ['description' (field data 'description')]
      ['acceptance_criteria' (field data 'acceptance_criteria')]
      ['required_outcomes' (canonical [%o outcomes])]
      ['blocked_reason' (field data 'blocked_reason')]
      ['completion_basis' (basis completion-basis.meta)]
      ['completion_principal_id' ?~(completion.meta '' principal.u.completion.meta)]
      ['completion_request_id' ?~(completion.meta '' request.u.completion.meta)]
      ['completion_note' ?:(=(%human completion-basis.meta) ?~(completion.meta '' evidence.u.completion.meta) '')]
      ['legacy_assignment_pending' ?~(legacy-assignee 'no' ?:(resolved.u.legacy-assignee 'no' 'yes'))]
      ['legacy_assignee_principal_id' ?~(legacy-assignee '' principal.u.legacy-assignee)]
      ['legacy_assignee_display_name' ?~(legacy-assignee '' (display people principal.u.legacy-assignee))]
      ['legacy_blocked_pending' ?~(legacy-blocked 'no' ?:(resolved.u.legacy-blocked 'no' 'yes'))]
      ['legacy_blocked_status' ?~(legacy-blocked '' raw-status.u.legacy-blocked)]
      ['legacy_prior_status' ?~(legacy-blocked '' ?~(prior-status.u.legacy-blocked '' u.prior-status.u.legacy-blocked))]
  ==
++  rows
  |=  [db=state:stead-team product=state:stead-product-state actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  (list row)
  ?>  &((lte (lent ~(tap by works.data.db)) 2.048) (lte (lent ~(tap by works.product)) 2.048) (lte (lent ~(tap by comments.product)) 4.096))
  =/  people  (assignees:stead-team db project.query now)
  ?:  =('comments' kind.query)
    =/  meta  (~(got by works.product) [project.query resource.query])
    ?>  (lte discussion-sequence.meta 32)
    =/  sequence=@ud  1
    =/  out=(list row)  ~
    |-
    ?:  (gth sequence discussion-sequence.meta)  (flop out)
    =/  comment  (~(got by comments.product) [project.query resource.query sequence])
    =/  fields
      %-  fields:stead-views
      :~  ['kind' 'comment']  ['project_id' project.query]  ['work_id' resource.query]
          ['sequence' (decimal sequence)]  ['body' body.comment]
          ['principal_id' principal.comment]  ['display_name' (display people principal.comment)]
          ['identity_ship' identity-ship.comment]  ['request_id' request.comment]
          ['accepted_at_ms' (decimal accepted-at.comment)]
          ['legacy_comment_revision' ?~(legacy-revision.comment '' (decimal u.legacy-revision.comment))]
      ==
    $(sequence +(sequence), out [[(decimal sequence) fields] out])
  =/  items  ~(tap by works.data.db)
  =/  out=(list row)  ~
  |-
  ?~  items  (sort out |=([a=row b=row] (aor id.a id.b)))
  =/  key=work-key:stead-product-state  p.i.items
  ?.  &(=(project.query project.key) ?|(=('' resource.query) =(resource.query work.key)))
    $(items t.items)
  ?.  (subject:stead-team db actor project.key 'work' '' work.key now)  $(items t.items)
  =/  item  (work-row db product project.key work.key !=('' resource.query) people)
  $(items t.items, out [[work.key item] out])
++  execute
  |=  [db=state:stead-team product=state:stead-product-state prior=state:stead-views actor=authentication:stead-team query=query:stead-team-codec now=@ud entropy=@]
  ^-  result
  ?.  &((current:stead-team db actor now) (gth (role:stead-team db actor project.query now) 0))
    [(error query 'denied_or_not_found') prior]
  ?~  migration.product  [(error query 'migration_required') prior]
  ?.  &((uuid request.query) =('' container.query) =('' search.query) ?|(=('' cursor.query) (opaque:stead-team-codec cursor.query)))
    [(error query 'invalid_request') prior]
  ?.  ?|  &(=('work' kind.query) ?|(=('' resource.query) (uuid resource.query)))
          &(=('comments' kind.query) (uuid resource.query))
      ==
    [(error query 'unsupported_query') prior]
  ?:  &(!=('' resource.query) !(subject:stead-team db actor project.query 'work' '' resource.query now))
    [(error query 'denied_or_not_found') prior]
  =/  attempted  (mule |.((rows db product actor query now)))
  ?:  ?=(%| -.attempted)  [(error query 'invalid_product_state') prior]
  =/  all  p.attempted
  =/  rank  (role:stead-team db actor project.query now)
  =/  epoch  epoch:(~(got by projects.data.db) project.query)
  =/  filter  query(request '', cursor '')
  =/  gen  (hash 'stead.product-view-generation/1' (bytes-hex (jam [identity.actor filter rank epoch all])))
  =/  next=state:stead-views
    prior(cursors (malt (skim ~(tap by cursors.prior) |=([key=@t val=cursor-record:stead-views] (gth expires.val now)))))
  =/  continuation=(unit cursor-record:stead-views)  (~(get by cursors.next) cursor.query)
  ?:  &(!=('' cursor.query) ?=(~ continuation))  [(error query 'stale_cursor') prior]
  ?.  ?~  continuation  &
      ?&  =('product-query' purpose.u.continuation)  =(actor actor.u.continuation)
          =(filter query.u.continuation)  =(gen generation.u.continuation)
          =(rank rank.u.continuation)  =(epoch epoch.u.continuation)
      ==
    [(error query 'stale_cursor') prior]
  =/  offset  ?~(continuation 0 offset.u.continuation)
  ?:  (gth offset (lent all))  [(error query 'stale_cursor') prior]
  =.  cursors.next  (~(del by cursors.next) cursor.query)
  =/  remaining  (slag offset all)
  =/  page  (scag 20 remaining)
  =/  more  (gth (lent remaining) 20)
  =/  token=@t  ''
  =?  cursors.next  &(more =('' cursor.query))
    (malt (skip ~(tap by cursors.next) |=([key=@t val=cursor-record:stead-views] &(?|(=('query' purpose.val) =('product-query' purpose.val)) =(actor actor.val)))))
  ?:  &(more ?|((gte counter.next 18.446.744.073.709.551.615) (gte (lent ~(tap by cursors.next)) 64) (gte (lent (skim ~(tap by cursors.next) |=([key=@t val=cursor-record:stead-views] =(principal.identity.actor principal.identity.actor.val)))) 4)))
    [(error query 'capacity_exceeded') prior]
  =?  next  more  next(counter +(counter.next))
  =?  token  more  (token:stead-session entropy counter.next 'stead.product-cursor/1')
  ?:  &(more (~(has by cursors.prior) token))  [(error query 'capacity_exceeded') prior]
  =?  cursors.next  more
    (~(put by cursors.next) token [actor filter gen rank epoch (add offset (lent page)) (min expires.actor (add now 300.000)) 'product-query' '' ''])
  =/  fields
    %-  fields:stead-views
    :~  ['protocol' 'stead.query-result/4']  ['status' 'read']
        ['request_id' request.query]  ['kind' kind.query]  ['project_id' project.query]
        ['container_id' '']  ['resource_id' resource.query]  ['authority_epoch' (decimal epoch)]
        ['generation' gen]  ['cursor' token]
    ==
  =/  index=@ud  0
  =/  output=object-map  ~
  |-
  ?~  page
    =/  encoded  (canonical [%o (~(put by fields) 'rows' [%o output])])
    ?:  (gth (met 3 encoded) 262.144)  [(error query 'capacity_exceeded') prior]
    [encoded next]
  $(page t.page, index +(index), output (~(put by output) (decimal index) [%o fields.i.page]))
--

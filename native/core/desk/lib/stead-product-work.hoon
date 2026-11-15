::  Reserved paired Work reducer. No Home route invokes this library yet.
::  All resolver gates are supplied by Home, never decoded from a command.
::  Home retirement/handoff fencing and real resolver adapters remain required
::  before activation. Native replay never runs an external effect here.
/+  stead-codec, stead-core, stead-team, stead-team-codec, stead-team-config, stead-product-codec, stead-product-state
=,  stead-codec
|%
+$  principal-kind  ?(%person %agent %service)
+$  kind-resolver  $-([project=@t principal=@t now=@ud] (unit principal-kind))
+$  target-resolver  $-([project=@t work=@t principal=@t target=json now=@ud] ?)
+$  proof-request
  $:  project=@t  work=@t  epoch=@ud  execution=@ud  digest=@t
      outcomes=object-map  principal=@t  now=@ud
  ==
+$  proof
  $:  project=@t  work=@t  epoch=@ud  execution=@ud  digest=@t
      outcomes-digest=@t  receipt=@t
  ==
+$  proof-resolver  $-(proof-request (unit proof))
+$  resolvers  [kind=kind-resolver target=target-resolver accepted=proof-resolver]
+$  transition  [response=@t db=state:stead-team product=state:stead-product-state]
++  outcome-digest
  |=  outcomes=object-map
  ^-  @t
  (hash 'stead.required-outcomes/1' (canonical [%o outcomes]))
++  kind-name
  |=  kind=(unit principal-kind)
  ^-  @t
  ?~  kind  ''
  ?-  u.kind
    %person  'person'
    %agent  'agent'
    %service  'service'
  ==
++  current-access
  |=  [db=state:stead-team actor=authentication:stead-team cmd=command:stead-product-codec now=@ud]
  ^-  ?
  ?&  (current:stead-team db actor now)
      (gte (role:stead-team db actor project.cmd now) 2)
      ?:  =('work.create' operation.cmd)  &
      ?:  =('work.delete' operation.cmd)  (~(has by works.data.db) [project.cmd resource.cmd])
      (subject:stead-team db actor project.cmd 'work' '' resource.cmd now)
  ==
++  eligible
  |=  [db=state:stead-team project=@t data=object-map now=@ud kind=kind-resolver]
  ^-  ?
  ::  Current adapter is intentionally native-binding-only. Catalog-only or
  ::  service actors need a reviewed current-membership adapter before use.
  =/  available  (assignees:stead-team db project now)
  =/  owner  (field data 'owner_principal_id')
  =/  worker  (field data 'worker_principal_id')
  ?&  ?|  =('' owner)
          &((~(has by available) owner) =((some %person) (kind project owner now)))
      ==
      ?|  =('' worker)
          ?&  (~(has by available) worker)
              =/  who  (kind project worker now)
              ?|  =((some %person) who)  =((some %agent) who)
              ==
          ==
      ==
  ==
++  targets-allowed
  |=  [db=state:stead-team cmd=command:stead-product-codec actor=authentication:stead-team now=@ud resolver=target-resolver]
  ^-  ?
  =/  targets  (object-field:stead-product-codec payload.cmd 'required_outcomes')
  %+  levy  ~(tap by targets)
  |=  [id=@t target=json]
  ?.  ?=([%o *] target)  |
  ::  First profile exposes exact contracts to project readers. Required
  ::  outputs are shared Docs only; private context remains a separate scope.
  ?.  =('document' (field p.target 'kind'))  |
  =/  collection  (field p.target 'collection_id')
  =/  document  (field p.target 'document_id')
  =/  box  (~(get by boxes.db) collection)
  ?~  box  |
  ?.  &(=(project.cmd project.u.box) =('shared' visibility.u.box))  |
  ?.  &((gte (role:stead-team db actor project.cmd now) 2) (box-access:stead-team db actor project.cmd collection now))  |
  ?:  (~(has in tombs.db) [project.cmd 'document' collection document])  |
  =/  current  (~(get by documents.data.db) [project.cmd (scope-key:stead-core collection document)])
  =/  expected  (uint (field p.target 'expected_revision'))
  ?.  ?:(=(expected 0) ?=(~ current) &(?=(^ current) =(expected revision.u.current)))  |
  (resolver project.cmd resource.cmd principal.identity.actor target now)
++  revisions
  |=  [product=state:stead-product-state key=work-key:stead-product-state]
  ^-  json
  =/  metadata  (~(get by works.product) key)
  %-  object
  :~  ['work_revision' (decimal ?~(metadata 0 work-revision.u.metadata))]
      ['execution_contract_revision' (decimal ?~(metadata 0 execution-revision.u.metadata))]
      ['discussion_sequence' (decimal ?~(metadata 0 discussion-sequence.u.metadata))]
      ['execution_contract_digest' ?~(metadata '' execution-digest.u.metadata)]
  ==
++  unrecorded
  |=  [db=state:stead-team product=state:stead-product-state cmd=command:stead-product-codec error=@t]
  ^-  transition
  :+  (canonical (object ~[['protocol' 'stead.receipt/4'] ['status' 'rejected'] ['request_id' request.cmd] ['canonical_sha256' digest.cmd] ['error' error]]))
    db
  product
++  receipt
  |=  [product=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud error=@t]
  ^-  @t
  =/  fields
    %-  object
    :~  ['protocol' 'stead.receipt/4']  ['status' ?:(=('' error) 'accepted' 'rejected')]
        ['request_id' request.cmd]  ['canonical_sha256' digest.cmd]
        ['project_id' project.cmd]  ['resource_id' resource.cmd]
        ['authority_epoch' (decimal epoch.cmd)]  ['operation' operation.cmd]
        ['principal_id' principal.identity.actor]  ['recorded_at_ms' (decimal now)]
        ['error' error]
    ==
  ?>  ?=([%o *] fields)
  =/  data  (~(put by p.fields) 'expected' [%o expected.cmd])
  =.  data  (~(put by data) 'resulting' (revisions product [project.cmd resource.cmd]))
  =/  bytes  (canonical [%o data])
  ?>  (lte (met 3 bytes) 8.192)
  bytes
++  record
  |=  [db=state:stead-team product=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud error=@t kind=kind-resolver]
  ^-  transition
  =/  response  (receipt product actor cmd now error)
  =/  metadata  (~(get by works.product) [project.cmd resource.cmd])
  =/  completion=@t
    ?.  &(=('' error) =('work.complete' operation.cmd) ?=(^ metadata) ?=(^ completion.u.metadata))  ''
    =/  saved  u.completion.u.metadata
    (canonical (object ~[['principal_id' principal.saved] ['request_id' request.saved] ['execution_contract_revision' (decimal execution-revision.saved)] ['execution_contract_digest' execution-digest.saved] ['evidence' evidence.saved]]))
  =/  body
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.work-journal/4']
        ['canonical_command' canonical-bytes.cmd]  ['receipt' response]
        ['authentication_context' (authentication-json:stead-team actor)]
        ['principal_kind' (kind-name (kind project.cmd principal.identity.actor now))]
        ['completion' completion]
    ==
  =/  next  (append-event:stead-product-state product %v4 body)
  =/  saved=attempt:stead-product-state  [digest.cmd resource.cmd operation.cmd canonical-bytes.cmd response]
  [response db next(attempts (~(put by attempts.next) [project.cmd principal.identity.actor request.cmd] saved))]
++  reject
  |=  [db=state:stead-team product=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud error=@t kind=kind-resolver]
  ^-  transition
  =/  attempted  (mule |.((record db product actor cmd now error kind)))
  ?:  ?=(%| -.attempted)  (unrecorded db product cmd 'capacity_exceeded')
  p.attempted
++  save-work
  |=  [db=state:stead-team before=state:stead-product-state after=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud kind=kind-resolver data=object-map metadata=metadata:stead-product-state deleted=?]
  ^-  transition
  =/  key=work-key:stead-product-state  [project.cmd resource.cmd]
  =/  prior  (~(get by works.data.db) key)
  =/  aggregate  ?~(prior 1 +(revision.u.prior))
  ?>  (lte aggregate 18.446.744.073.709.551.615)
  =/  next  db(data data.db(works (~(put by works.data.db) key [aggregate data])))
  =?  next  deleted  next(tombs (~(put in tombs.next) [project.cmd 'work' '' resource.cmd]))
  =/  product  after(works (~(put by works.after) key metadata))
  (commit db before next product actor cmd now kind)
++  replacement
  |=  [data=object-map payload=object-map names=(list @t)]
  ^-  object-map
  |-
  ?~  names  data
  $(names t.names, data (~(put by data) i.names (~(got by payload) i.names)))
++  proof-bytes
  |=  proof=proof
  ^-  @t
  %-  canonical
  %-  object
  :~  ['project_id' project.proof]  ['work_id' work.proof]
      ['authority_epoch' (decimal epoch.proof)]
      ['execution_contract_revision' (decimal execution.proof)]
      ['execution_contract_digest' digest.proof]
      ['required_outcomes_digest' outcomes-digest.proof]  ['receipt' receipt.proof]
  ==
++  apply-command
  |=  [db=state:stead-team product=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud resolvers=resolvers]
  ^-  transition
  ?.  (current-access db actor cmd now)  (unrecorded db product cmd 'denied_or_not_found')
  ?~  migration.product  (unrecorded db product cmd 'migration_required')
  =/  key=work-key:stead-product-state  [project.cmd resource.cmd]
  =/  request-key  [project.cmd principal.identity.actor request.cmd]
  =/  epoch  epoch:(~(got by projects.data.db) project.cmd)
  =/  previous  (~(get by attempts.product) request-key)
  ?^  previous
    ?.  =(epoch epoch.cmd)  (unrecorded db product cmd 'authority_epoch_conflict')
    ?.  =(digest.cmd digest.u.previous)  (unrecorded db product cmd 'request_id_reuse')
    [receipt.u.previous db product]
  ?:  (~(has by receipts.data.db) request-key)  (unrecorded db product cmd 'request_id_reuse')
  ?:  (gte (add (event-count:stead-team db project.cmd |) (lent ~(tap by attempts.product))) 4.096)
    (unrecorded db product cmd 'capacity_exceeded')
  ?.  =(epoch epoch.cmd)  (reject db product actor cmd now 'authority_epoch_conflict' kind.resolvers)
  =/  current  (~(get by works.data.db) key)
  =/  metadata  (~(get by works.product) key)
  ?.  =(?=(^ current) ?=(^ metadata))  (unrecorded db product cmd 'invalid_product_state')
  ?^  current
    ?>  ?=(^ metadata)
    ?.  =(execution-digest.u.metadata (contract-digest:stead-product-state key execution-revision.u.metadata data.u.current))
      (unrecorded db product cmd 'invalid_product_state')
    (apply-existing db product actor cmd now resolvers u.current u.metadata)
  ?.  =('work.create' operation.cmd)  (unrecorded db product cmd 'denied_or_not_found')
  ?.  (matches product cmd)  (reject db product actor cmd now 'revision_conflict' kind.resolvers)
  ?:  (gte (lent (skim ~(tap by works.data.db) |=([key=work-key:stead-product-state value=work-state:stead-core] =(project.cmd project.key)))) 128)
    (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
  ?.  (eligible db project.cmd payload.cmd now kind.resolvers)
    (reject db product actor cmd now 'ineligible_assignment' kind.resolvers)
  ?.  (targets-allowed db cmd actor now target.resolvers)
    (reject db product actor cmd now 'target_unavailable' kind.resolvers)
  =/  metadata=metadata:stead-product-state
    [1 1 0 (contract-digest:stead-product-state key 1 payload.cmd) ~ ~ %none ~]
  (save-work db product product actor cmd now kind.resolvers payload.cmd metadata |)
++  apply-existing
  |=  [db=state:stead-team product=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud resolvers=resolvers current=work-state:stead-core metadata=metadata:stead-product-state]
  ^-  transition
  =/  key=work-key:stead-product-state  [project.cmd resource.cmd]
  ?.  (matches product cmd)  (reject db product actor cmd now 'revision_conflict' kind.resolvers)
  ?:  (~(has in tombs.db) [project.cmd 'work' '' resource.cmd])
    (unrecorded db product cmd 'denied_or_not_found')
  ?:  =('work.create' operation.cmd)  (reject db product actor cmd now 'invalid_command' kind.resolvers)
  ?:  =(revision.current 18.446.744.073.709.551.615)
    (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
  =/  data  data.current
  =/  legacy-blocked  ?~(legacy-blocked.metadata | !resolved.u.legacy-blocked.metadata)
  =/  legacy-assigned  ?~(legacy-assignee.metadata | !resolved.u.legacy-assignee.metadata)
  ?:  =('work.comment' operation.cmd)
    ?:  (gte discussion-sequence.metadata 32)
      (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
    =/  sequence  +(discussion-sequence.metadata)
    =/  item=comment:stead-product-state
      [(field payload.cmd 'body') request.cmd principal.identity.actor (scot %p ship.identity.actor) now (authentication-json:stead-team actor) '' ~]
    =/  meta  metadata(discussion-sequence sequence)
    =/  staged  product(works (~(put by works.product) key meta))
    =/  accepted  (receipt staged actor cmd now '')
    =.  item  item(receipt accepted)
    =.  staged  staged(comments (~(put by comments.staged) [project.cmd resource.cmd sequence] item))
    (save-work db product staged actor cmd now kind.resolvers data meta |)
  ?:  =('work.update-contract' operation.cmd)
    =/  changed  (replacement data payload.cmd ~['title' 'description' 'acceptance_criteria' 'required_outcomes'])
    =/  same  =(execution-digest.metadata (contract-digest:stead-product-state key execution-revision.metadata changed))
    ?:  &(=('done' (field data 'status')) !same)
      (reject db product actor cmd now 'reopen_required' kind.resolvers)
    ?.  ?|(same (targets-allowed db cmd actor now target.resolvers))
      (reject db product actor cmd now 'target_unavailable' kind.resolvers)
    ?:  &(!same =(execution-revision.metadata 18.446.744.073.709.551.615))
      (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
    =/  revision  ?:(same execution-revision.metadata +(execution-revision.metadata))
    =/  meta  metadata(execution-revision revision, execution-digest (contract-digest:stead-product-state key revision changed))
    (save-work db product product actor cmd now kind.resolvers changed meta |)
  ?:  =('work.resolve-legacy-blocked' operation.cmd)
    ?.  legacy-blocked  (reject db product actor cmd now 'legacy_resolution_unavailable' kind.resolvers)
    ?:  =(work-revision.metadata 18.446.744.073.709.551.615)
      (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
    =/  changed  (replacement data payload.cmd ~['status' 'blocked_reason'])
    ?>  ?=(^ legacy-blocked.metadata)
    =/  meta  metadata(work-revision +(work-revision.metadata), legacy-blocked (some u.legacy-blocked.metadata(resolved &)))
    (save-work db product product actor cmd now kind.resolvers changed meta |)
  ?:  =('work.resolve-legacy-assignee' operation.cmd)
    ?.  legacy-assigned  (reject db product actor cmd now 'legacy_resolution_unavailable' kind.resolvers)
    ?:  =(work-revision.metadata 18.446.744.073.709.551.615)
      (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
    =/  changed  (replacement data payload.cmd ~['owner_principal_id' 'worker_principal_id'])
    ?.  (eligible db project.cmd changed now kind.resolvers)
      (reject db product actor cmd now 'ineligible_assignment' kind.resolvers)
    ?>  ?=(^ legacy-assignee.metadata)
    =/  meta  metadata(work-revision +(work-revision.metadata), legacy-assignee (some u.legacy-assignee.metadata(resolved &)))
    (save-work db product product actor cmd now kind.resolvers changed meta |)
  ?:  =('work.update-properties' operation.cmd)
    ?:  =(work-revision.metadata 18.446.744.073.709.551.615)
      (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
    =/  changed  (replacement data payload.cmd ~['type' 'status' 'priority' 'owner_principal_id' 'worker_principal_id' 'blocked_reason'])
    =/  assignment-changed
      ?|  !=((field data 'owner_principal_id') (field changed 'owner_principal_id'))
          !=((field data 'worker_principal_id') (field changed 'worker_principal_id'))
      ==
    ?:  &(legacy-assigned assignment-changed)
      (reject db product actor cmd now 'legacy_resolution_required' kind.resolvers)
    ?:  &(legacy-blocked ?|(!=((field data 'status') (field changed 'status')) !=((field data 'blocked_reason') (field changed 'blocked_reason'))))
      (reject db product actor cmd now 'legacy_resolution_required' kind.resolvers)
    ?:  &(=('done' (field changed 'status')) ?|(!=('done' (field data 'status')) !(valid-completion metadata)))
      (reject db product actor cmd now 'completion_required' kind.resolvers)
    ?.  (eligible db project.cmd changed now kind.resolvers)
      (reject db product actor cmd now 'ineligible_assignment' kind.resolvers)
    =/  meta  metadata(work-revision +(work-revision.metadata))
    =?  meta  !=('done' (field changed 'status'))  meta(completion-basis %none, completion ~)
    (save-work db product product actor cmd now kind.resolvers changed meta |)
  ?:  =('work.delete' operation.cmd)
    ?:  =(work-revision.metadata 18.446.744.073.709.551.615)
      (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
    (save-work db product product actor cmd now kind.resolvers data metadata(work-revision +(work-revision.metadata)) &)
  ?>  =('work.complete' operation.cmd)
  ?:  =('done' (field data 'status'))
    (reject db product actor cmd now 'already_complete' kind.resolvers)
  ?:  ?|(legacy-blocked !=('' (field data 'blocked_reason')) =('canceled' (field data 'status')))
    (reject db product actor cmd now 'completion_blocked' kind.resolvers)
  ?:  =(work-revision.metadata 18.446.744.073.709.551.615)
    (reject db product actor cmd now 'capacity_exceeded' kind.resolvers)
  =/  outcomes  (object-field:stead-product-codec data 'required_outcomes')
  =/  human  =('human-note' (field payload.cmd 'basis'))
  =/  selected
    ?:  human
      ?:  ?=(^ outcomes)  [| 'required_outcomes_pending']
      ?.  =((some %person) (kind.resolvers project.cmd principal.identity.actor now))
        [| 'human_completion_required']
      =/  owner  (field data 'owner_principal_id')
      ?.  ?|(=('' owner) =(owner principal.identity.actor) =(3 (role:stead-team db actor project.cmd now)))
        [| 'owner_completion_required']
      [& (field payload.cmd 'note')]
    ?~  outcomes  [| 'human_completion_required']
    =/  wanted=proof-request
      [project.cmd resource.cmd epoch.cmd execution-revision.metadata execution-digest.metadata outcomes principal.identity.actor now]
    =/  proof  (accepted.resolvers wanted)
    ?~  proof  [| 'required_outcomes_pending']
    ?.  ?&  =(project.cmd project.u.proof)  =(resource.cmd work.u.proof)
            =(epoch.cmd epoch.u.proof)  =(execution-revision.metadata execution.u.proof)
            =(execution-digest.metadata digest.u.proof)
            =((outcome-digest outcomes) outcomes-digest.u.proof)
            (gth (met 3 receipt.u.proof) 0)  (lte (met 3 receipt.u.proof) 8.192)
        ==
      [| 'required_outcomes_pending']
    [& (proof-bytes u.proof)]
  ?.  -.selected  (reject db product actor cmd now +.selected kind.resolvers)
  =/  completion=completion:stead-product-state
    [principal.identity.actor request.cmd execution-revision.metadata execution-digest.metadata +.selected]
  =/  meta  metadata(work-revision +(work-revision.metadata), completion-basis ?:(human %human %outcomes), completion (some completion))
  =/  changed  (~(put by data) 'status' [%s 'done'])
  (save-work db product product actor cmd now kind.resolvers changed meta |)
++  legacy-rejected
  |=  [db=state:stead-team product=state:stead-product-state cmd=command error=@t]
  ^-  transition
  :+  (canonical (object ~[['protocol' 'stead.result/3'] ['status' 'rejected'] ['request_id' request.cmd] ['canonical_sha256' digest.cmd] ['error' error]]))
    db
  product
++  apply-legacy
  |=  [db=state:stead-team product=state:stead-product-state actor=authentication:stead-team cmd=command now=@ud]
  ^-  transition
  ::  This wrapper is mandatory for every remaining command/3 write after
  ::  migration. Owner configuration must be fenced until separately recorded.
  ?.  (allowed:stead-team db actor cmd now)
    (legacy-rejected db product cmd 'denied_or_not_found')
  ?~  migration.product  (legacy-rejected db product cmd 'migration_required')
  =/  key  [project.cmd principal.identity.actor request.cmd]
  ?:  (~(has by attempts.product) key)  (legacy-rejected db product cmd 'request_id_reuse')
  ?:  (~(has by receipts.data.db) key)
    =/  retry  (apply-command:stead-team db actor cmd now)
    ?>  =(db next.retry)
    [response.retry db product]
  ?:  =('work' (kind:stead-team-codec operation.cmd))
    (legacy-rejected db product cmd 'unsupported_version')
  ?:  &(!=('policy.revoke' operation.cmd) (gte (add (event-count:stead-team db project.cmd |) (lent ~(tap by attempts.product))) 4.096))
    (legacy-rejected db product cmd 'capacity_exceeded')
  =/  legacy  (apply-command:stead-team db actor cmd now)
  ?:  =(db next.legacy)  [response.legacy db product]
  =/  attempted
    %-  mule
    |.
    ?>  ?=(^ journal.data.next.legacy)
    ?>  =(journal.data.db t.journal.data.next.legacy)
    =/  product  (append-event:stead-product-state product %v3 bytes.i.journal.data.next.legacy)
    [response.legacy next.legacy product]
  ?:  ?=(%| -.attempted)  (legacy-rejected db product cmd 'capacity_exceeded')
  p.attempted
++  matches
  |=  [product=state:stead-product-state cmd=command:stead-product-codec]
  ^-  ?
  =/  actual  (revisions product [project.cmd resource.cmd])
  ?>  ?=([%o *] actual)
  %+  levy  ~(tap by expected.cmd)
  |=  [key=@t value=json]
  =(value (~(got by p.actual) key))
++  valid-completion
  |=  metadata=metadata:stead-product-state
  ^-  ?
  ?:  =(%legacy completion-basis.metadata)  ?=(~ completion.metadata)
  ?.  ?|  =(%human completion-basis.metadata)  =(%outcomes completion-basis.metadata)
      ==
    |
  ?~  completion.metadata  |
  ?&  =(execution-revision.metadata execution-revision.u.completion.metadata)
      =(execution-digest.metadata execution-digest.u.completion.metadata)
      (uuid principal.u.completion.metadata)  (uuid request.u.completion.metadata)
      !=('' evidence.u.completion.metadata)
  ==
++  invalidate
  |=  [db=state:stead-team project=@t work=@t]
  ^-  state:stead-team
  =/  scopes=(set @t)  (silt ~[''])
  =/  links  ~(tap by links.db)
  =/  relevant
    |-
    ?~  links  scopes
    =/  link  q.i.links
    =/  id  +.p.i.links
    ?.  &(=(project -.p.i.links) !(~(has in tombs.db) [project 'relation' '' id]))  $(links t.links)
    =/  source  &(=('work' (field data.link 'source_kind')) =(work (field data.link 'source_id')))
    =/  target  &(=('work' (field data.link 'target_kind')) =(work (field data.link 'target_id')))
    ?.  ?|(source target)  $(links t.links)
    $(links t.links, scopes (~(uni in scopes) (link-scopes:stead-team db data.link)))
  =/  remaining  ~(tap in relevant)
  |-
  ?~  remaining  db
  =/  prior  (~(get by generations.db) [project i.remaining])
  =/  generation  ?~(prior 1 +(u.prior))
  ?>  (lte generation 18.446.744.073.709.551.615)
  $(remaining t.remaining, db db(generations (~(put by generations.db) [project i.remaining] generation)))
++  commit
  |=  [prior-db=state:stead-team prior-product=state:stead-product-state db=state:stead-team product=state:stead-product-state actor=authentication:stead-team cmd=command:stead-product-codec now=@ud kind=kind-resolver]
  ^-  transition
  =/  attempted
    %-  mule
    |.
    (record (invalidate db project.cmd resource.cmd) product actor cmd now '' kind)
  ?:  ?=(%| -.attempted)  (unrecorded prior-db prior-product cmd 'capacity_exceeded')
  p.attempted
--

::  Deterministic, incremental conversion of validated configured-team Work.
::  This is not an app on-load path and does not activate command/4.
/+  stead-codec, stead-core, stead-team, stead-team-codec, stead-team-config, stead-restore, stead-product-state
=,  stead-codec
=>
|%
+$  event  [project=@t bytes=@t digest=@t]
+$  assignment-source  [principal=@t request=@t authentication=@t target=@t]
+$  observed-work
  $:  aggregate=@ud  properties=@ud  execution=@ud  sequence=@ud
      data=object-map  discussion=(list json)  prior-status=(unit @t)
      assignment=(unit assignment-source)  deleted=?
  ==
+$  conversion
  $:  legacy=state:stead-team  converted=state:stead-team
      validation=job:stead-restore  product=state:stead-product-state
      observed=(map work-key:stead-product-state observed-work)
      events=(list event)  resources=(list [p=work-key:stead-product-state q=work-state:stead-core])
      heads=(map @t @t)  timeline=@t  phase=?(%validate %events %resources %valid %invalid)
  ==
++  optional-field
  |=  [data=object-map key=@t]
  ^-  @t
  =/  value  (~(get by data) key)
  ?~  value  ''
  ?>  ?=([%s *] u.value)
  p.u.value
++  unfinished
  |=  status=@t
  ^-  ?
  (~(has in (silt ~['backlog' 'todo' 'in_progress'])) status)
++  assignment-at
  |=  [principal=@t request=@t record=object-map]
  ^-  (unit assignment-source)
  ?:  =('' principal)  ~
  (some [principal request (field record 'authentication_context') (field record 'grant_target')])
++  one-event
  |=  job=conversion
  ^-  conversion
  =/  remaining=(list event)  events.job
  ?>  &(=(phase.job %events) ?=(^ remaining))
  =/  event  i.remaining
  ::  Per-project heads alone do not bind interleaving across projects.
  =/  timeline
    %-  hash
    :-  'stead.work-migration-timeline/1'
    (canonical (object ~[['previous' timeline.job] ['project_id' project.event] ['journal_digest' digest.event]]))
  =.  job  job(events t.remaining, heads (~(put by heads.job) project.event digest.event), timeline timeline)
  =/  value  (need (parse-result bytes.event))
  ?>  ?=([%o *] value)
  =/  record  p.value
  =/  cmd  (decode:stead-team-codec (field record 'canonical_command'))
  ?.  =('work' (kind:stead-team-codec operation.cmd))  job
  =/  key=work-key:stead-product-state  [project.cmd resource.cmd]
  =/  aggregate  (uint (field record 'new_revision'))
  ?:  =('work.create' operation.cmd)
    ?>  !(~(has by observed.job) key)
    =/  assigned  (assignment-at (optional-field payload.cmd 'assignee_principal_id') request.cmd record)
    =/  work=observed-work  [aggregate 1 1 0 payload.cmd ~ ~ assigned |]
    job(observed (~(put by observed.job) key work))
  =/  work  (~(got by observed.job) key)
  ?>  &(!deleted.work =(aggregate.work (uint (field record 'old_revision'))))
  =.  work  work(aggregate aggregate)
  ?:  =('work.delete' operation.cmd)
    job(observed (~(put by observed.job) key work(deleted &)))
  ?:  =('work.comment' operation.cmd)
    =/  receipt  (need (parse-result (field record 'receipt')))
    ?>  ?=([%o *] receipt)
    =/  body  (field payload.cmd 'body')
    =/  principal  (field p.receipt 'principal_id')
    =/  ship  (field p.receipt 'identity_ship')
    =/  accepted  (uint (field p.receipt 'accepted_at_ms'))
    =/  posted
      %-  object
      :~  ['comment_revision' (decimal aggregate)]  ['body' body]
          ['principal_id' principal]  ['identity_ship' ship]
          ['accepted_at_ms' (decimal accepted)]
      ==
    =/  sequence  +(sequence.work)
    =/  comment=comment:stead-product-state
      [body request.cmd principal ship accepted (field record 'authentication_context') (field record 'receipt') (some aggregate)]
    =/  product  product.job(comments (~(put by comments.product.job) [project.cmd resource.cmd sequence] comment))
    job(product product, observed (~(put by observed.job) key work(sequence sequence, discussion [posted discussion.work])))
  ?:  =('work.assign' operation.cmd)
    =/  principal  (field payload.cmd 'assignee_principal_id')
    =/  changed  !=(principal (optional-field data.work 'assignee_principal_id'))
    =/  data
      ?:  =('' principal)  (~(del by data.work) 'assignee_principal_id')
      (~(put by data.work) 'assignee_principal_id' [%s principal])
    =/  assigned  (assignment-at principal request.cmd record)
    job(observed (~(put by observed.job) key work(data data, properties ?:(changed +(properties.work) properties.work), assignment assigned)))
  ?>  =('work.update' operation.cmd)
  =/  data  payload.cmd
  =/  assigned  (optional-field data.work 'assignee_principal_id')
  =?  data  !=('' assigned)  (~(put by data) 'assignee_principal_id' [%s assigned])
  =/  goal-changed  ?|(!=((field data 'title') (field data.work 'title')) !=((field data 'description') (field data.work 'description')))
  =/  properties-changed
    %+  lien  ~['type' 'status' 'priority']
    |=  name=@t
    !=((field data name) (field data.work name))
  =/  before  (field data.work 'status')
  =/  after  (field data 'status')
  =/  prior
    ?:  !=('blocked' after)  *(unit @t)
    ?:  =('blocked' before)  prior-status.work
    ?:((unfinished before) (some before) ~)
  job(observed (~(put by observed.job) key work(data data, properties ?:(properties-changed +(properties.work) properties.work), execution ?:(goal-changed +(execution.work) execution.work), prior-status prior)))
++  assignment-display
  |=  [db=state:stead-team source=assignment-source]
  ^-  assignment:stead-product-state
  =/  config  (need current.registry.db)
  =/  found
    %+  skim  ~(tap by members.config)
    |=  [ship=@p person=member:stead-team-config]
    =(principal.source principal.identity.person)
  ?>  (lte (lent found) 1)
  =/  name  ?~(found '' display.q.i.found)
  [principal.source name ?~(found %unavailable %registry) request.source authentication.source target.source |]
++  one-resource
  |=  job=conversion
  ^-  conversion
  ?>  &(=(phase.job %resources) ?=(^ resources.job))
  =/  key  p.i.resources.job
  =/  old  q.i.resources.job
  =/  work  (~(got by observed.job) key)
  ?>  &(=(aggregate.work revision.old) =(data.work (~(del by data.old) 'discussion')))
  ?>  =(discussion.work (discussion:stead-team data.old))
  ?>  =(deleted.work (~(has in tombs.legacy.job) [project.key 'work' '' work.key]))
  =/  data  (~(del by data.work) 'assignee_principal_id')
  =/  raw-status  (field data 'status')
  =/  blocked=(unit blocked:stead-product-state)
    ?:  !=('blocked' raw-status)  ~
    (some ['blocked' prior-status.work '' |])
  =?  data  ?=(^ blocked)
    (~(put by data) 'status' [%s ?~(prior-status.work 'legacy-blocked' u.prior-status.work)])
  =.  data  (~(put by data) 'owner_principal_id' [%s ''])
  =.  data  (~(put by data) 'worker_principal_id' [%s ''])
  =.  data  (~(put by data) 'blocked_reason' [%s ''])
  =.  data  (~(put by data) 'acceptance_criteria' [%s ''])
  =.  data  (~(put by data) 'required_outcomes' [%o ~])
  =/  assigned=(unit assignment:stead-product-state)
    ?~(assignment.work ~ (some (assignment-display legacy.job u.assignment.work)))
  =/  metadata=metadata:stead-product-state
    [properties.work execution.work sequence.work (contract-digest:stead-product-state key execution.work data) assigned blocked ?:(=('done' raw-status) %legacy %none) ~]
  =/  next  converted.job
  =.  next  next(data data.next(works (~(put by works.data.next) key old(data data))))
  job(converted next, resources t.resources.job, product product.job(works (~(put by works.product.job) key metadata)))
--
|%
+$  job  conversion
+$  migrated  [db=state:stead-team product=state:stead-product-state]
++  begin
  |=  [old=state:stead-team home=@p]
  ^-  job
  ?>  ?=(^ current.registry.old)
  =/  validation  (begin:stead-restore old home)
  [old old validation *state:stead-product-state ~ ~ ~ ~ (hex 64 0) %validate]
++  step
  |=  job=conversion
  ^-  conversion
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  job
  ?:  =(phase.job %validate)
    =/  validation  (step:stead-restore validation.job)
    ?:  =(%invalid status.validation)  job(validation validation, phase %invalid)
    ?:  =(%pending status.validation)  job(validation validation)
    ?>  =((some legacy.job) (result:stead-restore validation))
    job(validation validation, events (flop journal.data.legacy.job), phase %events)
  =/  left=@ud  16
  |-
  ?:  =(0 left)  job
  ?:  &(=(phase.job %events) ?=(~ events.job))
    =/  boundary=boundary:stead-product-state
      (boundary-of:stead-product-state (lent journal.data.legacy.job) heads.job registry.legacy.job timeline.job)
    $(job job(resources ~(tap by works.data.legacy.job), product product.job(migration (some boundary)), phase %resources))
  ?:  &(=(phase.job %resources) ?=(~ resources.job))
    ?>  =((lent ~(tap by observed.job)) (lent ~(tap by works.data.legacy.job)))
    job(phase %valid)
  =/  attempted
    (mule |.(?:(=(phase.job %events) (one-event job) (one-resource job))))
  ?:  ?=(%| -.attempted)  job(phase %invalid)
  $(job p.attempted, left (dec left))
++  result
  |=  job=job
  ^-  (unit migrated)
  ?:(=(phase.job %valid) (some [converted.job product.job]) ~)
--

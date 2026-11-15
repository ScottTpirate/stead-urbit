::  Reserved mixed-history validation. No Home save/load path invokes it.
::  Historical adapters validate independent retained authority evidence; a
::  recorded principal_kind or today's catalog is not such evidence.
/+  stead-codec, stead-core, stead-projection, stead-restore, stead-team, stead-team-codec, stead-product-codec, stead-product-state, stead-product-migrate, stead-product-work
=,  stead-codec
=>
|%
+$  paired  migrated:stead-product-migrate
+$  adapter-input
  $:  rebuilt=paired  record=object-map  command=command:stead-product-codec
      actor=authentication:stead-team  now=@ud
  ==
+$  historical-adapter
  $-(adapter-input (unit resolvers:stead-product-work))
+$  validation
  $:  target=paired  rebuilt=paired  home=@p
      history=history-job:stead-restore
      migration=(unit job:stead-product-migrate)
      remaining=(list event:stead-product-state)
      latest=@ud  phase=?(%history %migration %events %valid %invalid)
  ==
++  bounded
  ::  Keep the existing restore's combined noun ceiling; no per-side increase.
  |=  value=*
  ^-  ?
  =/  todo=(list *)  [value ~]
  =/  nodes=@ud  16.777.216
  =/  bytes=@ud  2.147.483.648
  |-
  ?~  todo  &
  ?:  =(nodes 0)  |
  ?^  i.todo
    $(todo [-.i.todo [+.i.todo t.todo]], nodes (dec nodes))
  =/  size  (met 3 i.todo)
  ?:  (gth size bytes)  |
  $(todo t.todo, nodes (dec nodes), bytes (sub bytes size))
++  metadata-bounded
  |=  meta=metadata:stead-product-state
  ^-  ?
  ?&  (gth work-revision.meta 0)  (lte work-revision.meta 18.446.744.073.709.551.615)
      (gth execution-revision.meta 0)  (lte execution-revision.meta 18.446.744.073.709.551.615)
      (lte discussion-sequence.meta 32)  (opaque:stead-team-codec execution-digest.meta)
      ?~  legacy-assignee.meta  &
      =/  old  u.legacy-assignee.meta
      ?&  (uuid principal.old)  (uuid request.old)
          ?|(=('' display.old) (title display.old))
          (lte (met 3 authentication.old) 4.096)  (lte (met 3 target.old) 1.024)
      ==
      ?~  legacy-blocked.meta  &
      =/  old  u.legacy-blocked.meta
      ?&  =('blocked' raw-status.old)  =('' raw-reason.old)
          ?~  prior-status.old  &
          (~(has in (silt ~['backlog' 'todo' 'in_progress'])) u.prior-status.old)
      ==
      ?~  completion.meta  ?|(=(%none completion-basis.meta) =(%legacy completion-basis.meta))
      =/  saved  u.completion.meta
      ?&  (uuid principal.saved)  (uuid request.saved)
          (gth execution-revision.saved 0)  (lte execution-revision.saved 18.446.744.073.709.551.615)
          (opaque:stead-team-codec execution-digest.saved)
          =(execution-revision.meta execution-revision.saved)
          =(execution-digest.meta execution-digest.saved)
          ?:  =(%human completion-basis.meta)  (comment-body:stead-team-codec evidence.saved)
          ?.  =(%outcomes completion-basis.meta)  |
          =/  proof  (flat evidence.saved ~['project_id' 'work_id' 'authority_epoch' 'execution_contract_revision' 'execution_contract_digest' 'required_outcomes_digest' 'receipt'])
          ?&  (uuid (field proof 'project_id'))  (uuid (field proof 'work_id'))
              (gth (uint (field proof 'authority_epoch')) 0)
              (gth (uint (field proof 'execution_contract_revision')) 0)
              (opaque:stead-team-codec (field proof 'execution_contract_digest'))
              (opaque:stead-team-codec (field proof 'required_outcomes_digest'))
              (gth (met 3 (field proof 'receipt')) 0)  (lte (met 3 (field proof 'receipt')) 8.192)
          ==
      ==
  ==
++  sidecar-bounded
  |=  product=state:stead-product-state
  ^-  ?
  ?&  (lte (lent events.product) 6.144)
      (lte (lent ~(tap by works.product)) 2.048)
      (lte (lent ~(tap by comments.product)) 4.096)
      (lte (lent ~(tap by attempts.product)) 4.096)
      %+  levy  events.product
      |=  [family=family:stead-product-state bytes=@t digest=@t]
      &((lte (met 3 bytes) 262.144) (opaque:stead-team-codec digest))
      %+  levy  ~(tap by works.product)
      |=  [key=work-key:stead-product-state meta=metadata:stead-product-state]
      &((uuid project.key) (uuid work.key) (metadata-bounded meta))
      %+  levy  ~(tap by attempts.product)
      |=  [key=[project=@t principal=@t request=@t] item=attempt:stead-product-state]
      ?&  (uuid project.key)  (uuid principal.key)  (uuid request.key)
          (uuid resource.item)  (opaque:stead-team-codec digest.item)
          (lte (met 3 operation.item) 64)
          (lte (met 3 command.item) 65.536)  (lte (met 3 receipt.item) 8.192)
      ==
      %+  levy  ~(tap by comments.product)
      |=  [key=[project=@t work=@t sequence=@ud] item=comment:stead-product-state]
      ?&  (uuid project.key)  (uuid work.key)  (gth sequence.key 0)  (lte sequence.key 32)
          (comment-body:stead-team-codec body.item)
          (uuid principal.item)  (uuid request.item)  (lte (met 3 identity-ship.item) 128)
          (gth accepted-at.item 0)  (lte accepted-at.item 18.446.744.073.709.551.615)
          (lte (met 3 authentication.item) 4.096)  (lte (met 3 receipt.item) 8.192)
          ?~  legacy-revision.item  &
          &((gth u.legacy-revision.item 0) (lte u.legacy-revision.item 18.446.744.073.709.551.615))
      ==
  ==
++  flat
  |=  [raw=@t names=(list @t)]
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  ?>  &(=(raw (canonical value)) (keys p.value names))
  ?>  (levy ~(tap by p.value) |=([key=@t value=json] ?=([%s *] value)))
  p.value
++  one
  |=  [job=validation adapter=historical-adapter]
  ^-  validation
  ?>  &(=(phase.job %events) ?=(^ remaining.job))
  =/  event  i.remaining.job
  =/  envelope  (flat bytes.event ~['protocol' 'sequence' 'previous_digest' 'family' 'body'])
  ?>  =('stead.product-event/1' (field envelope 'protocol'))
  ?>  =(digest.event (hash 'stead.product-event/1' bytes.event))
  =/  before  rebuilt.job
  =/  prior  events.product.before
  =/  boundary  (need migration.product.before)
  ?>  =(+((lent prior)) (uint (field envelope 'sequence')))
  ?>  =(?~(prior fingerprint.boundary digest.i.prior) (field envelope 'previous_digest'))
  ?>  =(?:(=(family.event %v3) 'stead.command/3' 'stead.command/4') (field envelope 'family'))
  =/  body  (field envelope 'body')
  =/  replayed=[now=@ud transition=transition:stead-product-work]
    ?:  =(family.event %v3)
      =/  record  (flat body ~['protocol' 'sequence' 'previous_digest' 'canonical_command' 'old_revision' 'new_revision' 'authentication_context' 'grant_target' 'receipt'])
      =/  cmd  (decode:stead-team-codec (field record 'canonical_command'))
      =/  row=event:stead-projection  [project.cmd body (hash 'stead.journal/3' body)]
      =/  decoded  (decoded:stead-projection row)
      =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
      =/  now  (uint (field receipt.decoded 'accepted_at_ms'))
      ?>  (gte now latest.job)
      =/  applied  (apply-legacy:stead-product-work db.before product.before actor cmd now)
      ?>  =(response.applied (field record 'receipt'))
      [now applied]
    =/  record  (flat body ~['protocol' 'canonical_command' 'receipt' 'authentication_context' 'principal_kind' 'completion'])
    ?>  =('stead.work-journal/4' (field record 'protocol'))
    =/  cmd  (decode:stead-product-codec (field record 'canonical_command'))
    ?>  =(canonical-bytes.cmd (field record 'canonical_command'))
    =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
    =/  receipt  (need (parse-result (field record 'receipt')))
    ?>  ?=([%o *] receipt)
    =/  now  (uint (field p.receipt 'recorded_at_ms'))
    ?>  &((gth now 0) (gte now latest.job))
    ::  The adapter must bind historical kinds, targets and accepted proof to
    ::  this rebuilt state/event. It is never supplied by saved or wire bytes.
    =/  policies  (need (adapter [before record cmd actor now]))
    =/  applied  (apply-command:stead-product-work db.before product.before actor cmd now policies)
    ?>  =(response.applied (field record 'receipt'))
    [now applied]
  =/  applied  transition.replayed
  ?>  ?=(^ events.product.applied)
  ?>  &(=(event i.events.product.applied) =(prior t.events.product.applied))
  job(rebuilt [db.applied product.applied], remaining t.remaining.job, latest now.replayed)
--
|%
+$  job  validation
+$  adapter  historical-adapter
+$  evidence-request  adapter-input
++  record-bounds
  |=  product=state:stead-product-state
  ^-  ?
  (sidecar-bounded product)
++  noun-bounds
  |=  value=*
  ^-  ?
  (bounded value)
++  begin
  |=  [target=migrated:stead-product-migrate home=@p]
  ^-  job
  ?>  (bounded target)
  ::  Admission retains every existing per-map/object bound and registry
  ::  check. Do not step this old validator on converted Work state.
  =/  checked  (begin:stead-restore db.target home)
  =/  product  product.target
  =/  boundary  (need migration.product)
  ::  No unjournaled owner configuration or catalog update may bypass the
  ::  mixed timeline. This first profile deliberately fences configuration.
  ?>  =(registry.target.checked predecessor-registry.boundary)
  ?>  (sidecar-bounded product)
  ::  This compatibility validator has no owner-history authority adapter.
  ?>  (levy events.product |=(event=event:stead-product-state ?|(=(%v3 family.event) =(%v4 family.event))))
  ?>  (lte journal-count.boundary (lent journal.data.db.target))
  =/  prefix  (flop (scag journal-count.boundary (flop journal.data.db.target)))
  =/  history  (begin-history:stead-restore predecessor-registry.boundary prefix home)
  [target [empty:stead-team *state:stead-product-state] home history ~ (flop events.product) 0 %history]
++  step
  |=  [job=validation adapter=historical-adapter]
  ^-  job
  ?:  ?|(=(phase.job %valid) =(phase.job %invalid))  job
  ?:  =(phase.job %history)
    =/  history  (step-history:stead-restore history.job)
    ?:  =(%invalid status.cursor.history)  job(history history, phase %invalid)
    ?:  =(%pending status.cursor.history)  job(history history)
    =/  migration  (begin:stead-product-migrate (need (result-history:stead-restore history)) home.job)
    job(history history, migration (some migration), latest latest.cursor.history, phase %migration)
  ?:  =(phase.job %migration)
    =/  migration  (step:stead-product-migrate (need migration.job))
    ?:  =(%invalid phase.migration)  job(migration (some migration), phase %invalid)
    ?.  =(%valid phase.migration)  job(migration (some migration))
    =/  rebuilt  (need (result:stead-product-migrate migration))
    ?.  =(migration.product.rebuilt migration.product.target.job)
      job(migration (some migration), phase %invalid)
    job(migration (some migration), rebuilt rebuilt, phase %events)
  =/  left=@ud  16
  |-
  ?~  remaining.job
    job(phase ?:(=(target.job rebuilt.job) %valid %invalid))
  ?:  =(left 0)  job
  =/  attempted  (mule |.((one job adapter)))
  ?:  ?=(%| -.attempted)  job(phase %invalid)
  $(job p.attempted, left (dec left))
++  result
  |=  job=validation
  ^-  (unit migrated:stead-product-migrate)
  ?:(=(phase.job %valid) (some rebuilt.job) ~)
--

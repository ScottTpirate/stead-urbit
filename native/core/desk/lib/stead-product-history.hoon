::  Reserved single-timeline owner/Work integration. No Home carrier or saved
::  envelope invokes it yet. All operations below are pure and commit as one
::  returned state; an exception cannot publish a partial catalog or Doc write.
/+  stead-codec, stead-core, stead-team, stead-team-codec, stead-projection, stead-restore, stead-principals, stead-product-codec, stead-product-state, stead-product-migrate, stead-product-work, stead-product-adapters, stead-product-owner-codec, stead-product-owner, stead-product-restore, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-doc-change-proof
=,  stead-codec
=>
|%
+$  current
  $:  db=state:stead-team  product=state:stead-product-state
      catalog=state:stead-principals  ledger=ledger:stead-product-owner
      changes=state:stead-doc-change-state
  ==
+$  transition  [response=@t next=current]
+$  validation
  $:  target=current  rebuilt=current  home=@p
      history=history-job:stead-restore
      migration=(unit job:stead-product-migrate)
      remaining=(list event:stead-product-state)
      latest=@ud  phase=?(%history %migration %events %valid %invalid)
  ==
++  initialized
  |=  [pair=migrated:stead-product-migrate home=@p]
  ^-  current
  =/  old  (initialize:stead-product-owner pair home)
  [db.old product.old catalog.old ledger.old empty:stead-doc-change-state]
++  owner-state
  |=  state=current
  ^-  state:stead-product-owner
  [db.state product.state catalog.state ledger.state]
++  doc-state
  |=  state=current
  ^-  state:stead-doc-change
  [db.state product.state changes.state]
++  member
  ::  An unresolved imported kind does not invent an Owner, but a disabled
  ::  principal cannot keep making ordinary writes through its native binding.
  |=  [state=current actor=authentication:stead-team now=@ud]
  ^-  ?
  ?.  (current:stead-team db.state actor now)  |
  =/  found  (~(get by principals.catalog.state) principal.identity.actor)
  ?~(found | active.u.found)
++  ordinary
  |=  state=current
  ^-  @ud
  (add (event-count:stead-team db.state '' |) (add (lent ~(tap by attempts.product.state)) (add (owner-count:stead-product-owner ledger.state |) (lent ~(tap by attempts.changes.state)))))
++  security
  |=  state=current
  ^-  @ud
  (add (security-count:stead-product-owner db.state) (owner-count:stead-product-owner ledger.state &))
++  catalog-bounds
  |=  value=state:stead-principals
  ^-  ?
  ?&  (opaque:stead-team-codec source.value)
      (lte (lent ~(tap by principals.value)) 128)
      (lte (lent ~(tap by binding-owners.value)) 256)
      (lte (lent ~(tap by principal-highwaters.value)) 128)
      (lte (lent ~(tap by runtimes.value)) 128)  (lte (lent ~(tap by runtime-heads.value)) 32)
      (lte (lent ~(tap by definitions.value)) 128)  (lte (lent ~(tap by definition-heads.value)) 32)
      %+  levy  ~(tap by principals.value)
      |=  [id=@t row=principal:stead-principals]
      ?&  (uuid id)  (gth revision.row 0)  (lte revision.row 18.446.744.073.709.551.615)
          ?|(=('' display.row) (title display.row))
          (lte declared-at.row 18.446.744.073.709.551.615)
      ==
      %+  levy  ~(tap by binding-owners.value)
      |=  [binding=@t principal=@t]
      &((uuid binding) (uuid principal))
      %+  levy  ~(tap by principal-highwaters.value)
      |=  [principal=@t revision=@ud]
      &((uuid principal) (gth revision 0) (lte revision 18.446.744.073.709.551.615))
      %+  levy  (weld ~(tap by runtime-heads.value) ~(tap by definition-heads.value))
      |=  [id=@t revision=@ud]
      &((uuid id) (gth revision 0) (lte revision 18.446.744.073.709.551.615))
      %+  levy  ~(tap by runtimes.value)
      |=  [key=[id=@t revision=@ud] row=runtime:stead-principals]
      ?&  (uuid id.key)  =(revision.key revision.row)
          (gth revision.row 0)  (lte revision.row 18.446.744.073.709.551.615)
          (uuid principal.row)  (title profile.row)  (opaque:stead-team-codec policy-digest.row)
          (gth declared-at.row 0)  (lte declared-at.row 18.446.744.073.709.551.615)
      ==
      %+  levy  ~(tap by definitions.value)
      |=  [key=[id=@t revision=@ud] row=definition:stead-principals]
      ?&  (uuid id.key)  =(revision.key revision.row)
          (gth revision.row 0)  (lte revision.row 18.446.744.073.709.551.615)
          (uuid principal.row)  (opaque:stead-team-codec instructions-digest.row)
          (uuid runtime-id.row)  (gth runtime-revision.row 0)  (lte runtime-revision.row 18.446.744.073.709.551.615)
          (gth declared-at.row 0)  (lte declared-at.row 18.446.744.073.709.551.615)
      ==
  ==
++  work
  |=  [state=current actor=authentication:stead-team cmd=command:stead-product-codec now=@ud]
  ^-  transition
  ?.  (member state actor now)
    [response:(unrecorded:stead-product-work db.state product.state cmd 'denied_or_not_found') state]
  ?:  ?|  (~(has by attempts.changes.state) [project.cmd principal.identity.actor request.cmd])
          (~(has by ledger.state) request.cmd)
      ==
    [response:(unrecorded:stead-product-work db.state product.state cmd 'request_id_reuse') state]
  =/  resolvers  (current:stead-product-adapters db.state catalog.state actor)
  =.  accepted.resolvers  (resolver:stead-doc-change-proof (doc-state state) actor)
  =/  out  (apply-command:stead-product-work db.state product.state actor cmd now resolvers)
  =/  next  state(db db.out, product product.out)
  ?:  (gth (ordinary next) 4.096)
    [response:(unrecorded:stead-product-work db.state product.state cmd 'capacity_exceeded') state]
  [response.out next]
++  legacy
  |=  [state=current actor=authentication:stead-team cmd=command now=@ud]
  ^-  transition
  ?.  (member state actor now)
    [response:(legacy-rejected:stead-product-work db.state product.state cmd 'denied_or_not_found') state]
  ?:  ?|  (~(has by attempts.changes.state) [project.cmd principal.identity.actor request.cmd])
          (~(has by ledger.state) request.cmd)
      ==
    [response:(legacy-rejected:stead-product-work db.state product.state cmd 'request_id_reuse') state]
  =/  out  (apply-legacy:stead-product-work db.state product.state actor cmd now)
  =/  next  state(db db.out, product product.out)
  ?:  ?|  (gth (ordinary next) 4.096)  (gth (security next) 2.048)
          !(body-budget:stead-doc-change (doc-state next))
      ==
    [response:(legacy-rejected:stead-product-work db.state product.state cmd 'capacity_exceeded') state]
  [response.out next]
++  owner
  |=  [state=current cmd=command:stead-product-owner-codec home=@p sender=@p now=@ud]
  ^-  transition
  =/  base  (owner-state state)
  ?.  &(=(sender home) ?=(^ current.registry.db.state) =(home home.u.current.registry.db.state))
    [response:(deny:stead-product-owner base cmd 'owner_required') state]
  =/  native-used
    %+  lien  ~(tap by receipts.data.db.state)
    |=  [key=[project=@t principal=@t request=@t] value=receipt-state:stead-core]
    =(request.cmd request.key)
  =/  work-used
    %+  lien  ~(tap by attempts.product.state)
    |=  [key=[project=@t principal=@t request=@t] value=attempt:stead-product-state]
    =(request.cmd request.key)
  =/  doc-used
    %+  lien  ~(tap by attempts.changes.state)
    |=  [key=request-key:stead-doc-change value=attempt:stead-doc-change-state]
    =(request.cmd request.key)
  ?:  ?|(native-used work-used doc-used)
    [response:(deny:stead-product-owner base cmd 'request_id_reuse') state]
  =/  out  (apply:stead-product-owner base cmd home sender now [(lent ~(tap by attempts.changes.state)) 0])
  =/  next  state(db db.next.out, product product.next.out, catalog catalog.next.out, ledger ledger.next.out)
  ?~  record.out  [response.out next]
  =/  attempted
    %-  mule
    |.
    next(product (append-event:stead-product-state product.next %owner u.record.out))
  ?:  ?=(%| -.attempted)
    [response:(deny:stead-product-owner (owner-state state) cmd 'capacity_exceeded') state]
  [response.out p.attempted]
++  doc
  |=  [state=current actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud]
  ^-  transition
  ?.  (member state actor now)
    [response:(deny:stead-doc-change (doc-state state) cmd 'denied_or_not_found') state]
  =/  used
    |=  key=request-key:stead-doc-change
    ^-  ?
    (~(has by ledger.state) request.key)
  =/  other=budget:stead-doc-change  [(owner-count:stead-product-owner ledger.state |) used]
  =/  out  (apply:stead-doc-change (doc-state state) catalog.state actor cmd now deny-run:stead-doc-change other)
  =/  next  state(db db.next.out, product product.next.out, changes changes.next.out)
  ?~  record.out  [response.out next]
  =/  attempted
    %-  mule
    |.
    ?>  (lte (ordinary next) 4.096)
    next(product (append-event:stead-product-state product.next %doc-change u.record.out))
  ?:  ?=(%| -.attempted)
    [response:(deny:stead-doc-change (doc-state state) cmd 'capacity_exceeded') state]
  [response.out p.attempted]
++  flat
  |=  [raw=@t names=(list @t)]
  ^-  object-map
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  ?>  &(=(raw (canonical value)) (keys p.value names))
  ?>  (levy ~(tap by p.value) |=([key=@t value=json] ?=([%s *] value)))
  p.value
++  receipt-time
  |=  raw=@t
  ^-  @ud
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (uint (field p.value 'recorded_at_ms'))
++  doc-record
  |=  raw=@t
  ^-  object-map
  (flat raw ~['protocol' 'canonical_command' 'receipt' 'authentication_context' 'result' 'approval' 'adoption' 'save_command' 'save_receipt' 'save_event' 'save_event_digest'])
++  paired-next
  |=  remaining=(list event:stead-product-state)
  ^-  ?
  ?~  remaining  |
  ?~  t.remaining  |
  ?.  &(=(%v3 family.i.remaining) =(%doc-change family.i.t.remaining))  |
  =/  following  (flat bytes.i.t.remaining ~['protocol' 'sequence' 'previous_digest' 'family' 'body'])
  !=('' (field (doc-record (field following 'body')) 'save_event'))
++  doc-event
  |=  [job=validation paired=?]
  ^-  validation
  ?>  ?=(^ remaining.job)
  =/  before  rebuilt.job
  =/  prior  events.product.before
  =/  selected=event:stead-product-state
    ?.  paired  i.remaining.job
    ?>  ?=(^ t.remaining.job)
    i.t.remaining.job
  ?>  =(%doc-change family.selected)
  =/  envelope  (flat bytes.selected ~['protocol' 'sequence' 'previous_digest' 'family' 'body'])
  ?>  ?&  =('stead.product-event/1' (field envelope 'protocol'))
          =('stead.doc-change/1' (field envelope 'family'))
          =(digest.selected (hash 'stead.product-event/1' bytes.selected))
          =((add (lent prior) ?:(paired 2 1)) (uint (field envelope 'sequence')))
      ==
  =/  record  (doc-record (field envelope 'body'))
  ?>  =('stead.doc-change-journal/1' (field record 'protocol'))
  =/  boundary  (need migration.product.before)
  =/  previous  ?:(paired digest.i.remaining.job ?~(prior fingerprint.boundary digest.i.prior))
  ?>  =(previous (field envelope 'previous_digest'))
  ?>  ?:  paired
        ?&  =(%v3 family.i.remaining.job)
            =(bytes.i.remaining.job (field record 'save_event'))
            =(digest.i.remaining.job (field record 'save_event_digest'))
            !=('' (field record 'save_command'))  !=('' (field record 'save_receipt'))
        ==
      ?&  =('' (field record 'save_event'))  =('' (field record 'save_event_digest'))
          =('' (field record 'save_command'))  =('' (field record 'save_receipt'))
      ==
  =/  cmd  (decode:stead-doc-change-codec (field record 'canonical_command'))
  ?>  =(canonical-bytes.cmd (field record 'canonical_command'))
  =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
  =/  now  (receipt-time (field record 'receipt'))
  ?>  &((gth now 0) (gte now latest.job))
  ::  A successful accept reruns ONCE from the state preceding both records.
  ::  It creates the exact native write and adjacent typed acceptance together.
  =/  out  (doc before actor cmd now)
  ?>  =(response.out (field record 'receipt'))
  =/  generated  events.product.next.out
  ?>  ?=(^ generated)
  ?>  =(selected i.generated)
  =/  rest
    ?.  paired
      ?>  =(prior t.generated)
      t.remaining.job
    ?>  &(?=(^ t.generated) ?=(^ t.remaining.job))
    ?>  &(=(i.remaining.job i.t.generated) =(prior t.t.generated))
    t.t.remaining.job
  job(rebuilt next.out, remaining rest, latest now)
++  one
  |=  job=validation
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
  ?>  =((event-protocol:stead-product-state family.event) (field envelope 'family'))
  =/  body  (field envelope 'body')
  ?:  =(%doc-change family.event)  (doc-event job |)
  ?:  (paired-next remaining.job)  (doc-event job &)
  =/  replayed=[now=@ud transition=transition]
    ?:  =(family.event %owner)
      =/  record  (flat body ~['protocol' 'canonical_command' 'receipt' 'home' 'native_sender' 'before_registry_digest' 'after_registry_digest' 'before_catalog_digest' 'after_catalog_digest'])
      ?>  =('stead.owner-journal/1' (field record 'protocol'))
      ?>  =((scot %p home.job) (field record 'home'))
      ?>  =((scot %p home.job) (field record 'native_sender'))
      =/  cmd  (decode:stead-product-owner-codec (field record 'canonical_command'))
      ?>  =(canonical-bytes.cmd (field record 'canonical_command'))
      =/  now  (receipt-time (field record 'receipt'))
      ?>  &((gth now 0) (gte now latest.job))
      =/  out  (owner before cmd home.job home.job now)
      ?>  =(response.out (field record 'receipt'))
      [now out]
    ?:  =(family.event %v3)
      =/  record  (flat body ~['protocol' 'sequence' 'previous_digest' 'canonical_command' 'old_revision' 'new_revision' 'authentication_context' 'grant_target' 'receipt'])
      =/  cmd  (decode:stead-team-codec (field record 'canonical_command'))
      =/  row=event:stead-projection  [project.cmd body (hash 'stead.journal/3' body)]
      =/  decoded  (decoded:stead-projection row)
      =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
      =/  now  (uint (field receipt.decoded 'accepted_at_ms'))
      ?>  (gte now latest.job)
      =/  out  (legacy before actor cmd now)
      ?>  =(response.out (field record 'receipt'))
      [now out]
    ?>  =(family.event %v4)
    =/  record  (flat body ~['protocol' 'canonical_command' 'receipt' 'authentication_context' 'principal_kind' 'completion'])
    ?>  =('stead.work-journal/4' (field record 'protocol'))
    =/  cmd  (decode:stead-product-codec (field record 'canonical_command'))
    ?>  =(canonical-bytes.cmd (field record 'canonical_command'))
    =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
    =/  now  (receipt-time (field record 'receipt'))
    ?>  &((gth now 0) (gte now latest.job))
    =/  out  (work before actor cmd now)
    ?>  =(response.out (field record 'receipt'))
    [now out]
  =/  out  transition.replayed
  ?>  ?=(^ events.product.next.out)
  ?>  &(=(event i.events.product.next.out) =(prior t.events.product.next.out))
  job(rebuilt next.out, remaining t.remaining.job, latest now.replayed)
--
|%
+$  state  current
+$  result  transition
+$  job  validation
++  active-member  member
++  initialize  initialized
++  apply-work  work
++  apply-legacy  legacy
++  apply-owner  owner
++  apply-doc  doc
++  begin
  |=  [target=state home=@p]
  ^-  job
  ?>  (noun-bounds:stead-product-restore target)
  =/  checked  (begin:stead-restore db.target home)
  ?>  =(registry.target.checked registry.db.target)
  ?>  (record-bounds:stead-product-restore product.target)
  ?>  (changes-bounded:stead-doc-change (doc-state target))
  ?>  (catalog-bounds catalog.target)
  ?>  &((lte (lent ~(tap by ledger.target)) 4.224) (lte (ordinary target) 4.096) (lte (security target) 2.048))
  ?>  %+  levy  ~(tap by ledger.target)
      |=  [id=@t item=attempt:stead-product-owner]
      ?&  (uuid id)  (opaque:stead-team-codec digest.item)
          (lte (met 3 operation.item) 64)
          (lte (met 3 command.item) 65.536)  (lte (met 3 receipt.item) 8.192)
      ==
  =/  boundary  (need migration.product.target)
  ?>  (lte journal-count.boundary (lent journal.data.db.target))
  =/  prefix  (flop (scag journal-count.boundary (flop journal.data.db.target)))
  =/  history  (begin-history:stead-restore predecessor-registry.boundary prefix home)
  [target *state home history ~ (flop events.product.target) 0 %history]
++  step
  |=  job=validation
  ^-  validation
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
    =/  pair  (need (result:stead-product-migrate migration))
    ?.  =(migration.product.pair migration.product.target.job)
      job(migration (some migration), phase %invalid)
    =/  rebuilt  (initialized pair home.job)
    job(migration (some migration), rebuilt rebuilt, phase %events)
  =/  left=@ud  16
  |-
  ?~  remaining.job
    job(phase ?:(=(target.job rebuilt.job) %valid %invalid))
  ?:  =(left 0)  job
  =/  sized  (mule |.(?:((paired-next remaining.job) 2 1)))
  ?:  ?=(%| -.sized)  job(phase %invalid)
  ::  Reserve both event slots before invoking the pure acceptance reducer.
  ::  A checkpoint therefore never exposes half a committed Doc acceptance.
  ?:  (gth p.sized left)  job
  =/  attempted  (mule |.((one job)))
  ?:  ?=(%| -.attempted)  job(phase %invalid)
  =/  used  (sub (lent remaining.job) (lent remaining.p.attempted))
  ?>  =(used p.sized)
  $(job p.attempted, left (sub left used))
++  restored
  |=  job=validation
  ^-  (unit state)
  ?:(=(phase.job %valid) (some rebuilt.job) ~)
--

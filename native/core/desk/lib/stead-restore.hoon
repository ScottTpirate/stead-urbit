::  Saved-state consistency only; journal admission assertions are not fresh
::  authentication. Private reconstruction can never become a serving registry.
/+  stead-codec, stead-team, stead-team-config, stead-team-codec, stead-session, stead-core, stead-projection, stead-git
=,  stead-codec
=>
|%
+$  validation
  $:  target=state:stead-team  rebuilt=state:stead-team
      remaining=(list event:stead-projection)
      observed=(map @t actor:stead-session)  latest=@ud
      status=?(%pending %valid %invalid)
  ==
++  bounded
  |=  value=*
  ^-  ?
  ::  Bound traversal before any map/list traversal or semantic reconstruction.
  ::  This is an aggregate noun-input ceiling, not a claimed resident RAM size.
  ::  Reachability alone permits >3M expanded nodes; the loose independent
  ::  maxima (4096 sets of384 OIDs plus outer maps) fit below7M. Other
  ::  bounded maps/records fit within the remaining >9M nodes.
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
++  current-consistent
  |=  job=validation
  ^-  ?
  ?~  current.registry.target.job  ?=(~ observed.job)
  %+  levy  ~(tap by members.u.current.registry.target.job)
  |=  [ship=@p member=member:stead-team-config]
  =/  actor  identity.member
  =/  historical  (~(get by observed.job) principal.actor)
  ?~  historical  &
  ?|  (gth revision.actor revision.u.historical)
      =(actor u.historical)
  ==
++  remember
  |=  [registry=registry:stead-team-config observed=(map @t actor:stead-session) actor=actor:stead-session home=@p now=@ud]
  ^-  (map @t actor:stead-session)
  ?>  &(!=(home ship.actor) (live:stead-session actor now))
  ?>  =(principal.actor (~(got by owners.registry) binding.actor))
  ?>  (lte revision.actor (~(got by revisions.registry) principal.actor))
  =/  prior  (~(get by observed) principal.actor)
  ?>  ?~  prior  &
      ?|  (gth revision.actor revision.u.prior)
          =(actor u.prior)
      ==
  (~(put by observed) principal.actor actor)
++  one
  |=  job=validation
  ^-  validation
  ?>  &(?=(^ remaining.job) =(%pending status.job))
  =/  row  i.remaining.job
  =/  decoded  (decoded:stead-projection row)
  =/  cmd  cmd.decoded
  =/  receipt  receipt.decoded
  =/  value  (need (parse-result bytes.row))
  ?>  ?=([%o *] value)
  =/  record  p.value
  =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
  =/  now  (uint (field receipt 'accepted_at_ms'))
  ?>  (gte now latest.job)
  =/  config  (need current.registry.target.job)
  ?>  &(=(home.actor home.config) =(organization.actor organization.config) =(team.actor team.config) =(runtime.actor runtime.config))
  =/  observed  (remember registry.target.job observed.job identity.actor home.config now)
  =/  people=(map @p member:stead-team-config)
    (~(put by *(map @p member:stead-team-config)) ship.identity.actor [identity.actor 'Recorded binding'])
  =/  target  (field record 'grant_target')
  =/  prepared
    ?.  =('policy.grant' operation.cmd)
      ?>  =('' target)
      [people observed]
    =/  who  (decode-actor:stead-team target)
    ?>  =(principal.who (field payload.cmd 'principal_id'))
    =/  next  (remember registry.target.job observed who home.config now)
    ?:  ?|(=(ship.who ship.identity.actor) =(principal.who principal.identity.actor) =(binding.who binding.identity.actor))
      ?>  =(who identity.actor)
      [people next]
    [(~(put by people) ship.who [who 'Recorded binding']) next]
  =/  creators=(set @t)
    ?:(=('project.create' operation.cmd) (silt ~[principal.identity.actor]) ~)
  =/  registry  registry.target.job(current [~ config(members -.prepared, creators creators)])
  =/  input  rebuilt.job(registry registry)
  =/  key  [project.cmd principal.identity.actor request.cmd]
  ?>  !(~(has by receipts.data.input) key)
  =/  result  (apply-command:stead-team input actor cmd now)
  ?>  =(response.result (field record 'receipt'))
  ?>  ?=(^ journal.data.next.result)
  ?>  &(=(row i.journal.data.next.result) =(journal.data.input t.journal.data.next.result))
  ?>  =(+((lent ~(tap by receipts.data.input))) (lent ~(tap by receipts.data.next.result)))
  job(rebuilt next.result(registry registry.target.job), remaining t.remaining.job, observed +.prepared, latest now)
--
|%
+$  job  validation
++  begin
  |=  [target=state:stead-team home=@p]
  ^-  job
  ?>  (bounded target)
  ?>  (validate:stead-team-config registry.target home)
  ?~  current.registry.target
    ?>  =(target empty:stead-team)
    [target target ~ ~ 0 %valid]
  ?>  initialized.data.target
  ?>  ?=(~ bindings.data.target)
  ?>  &((lte (lent journal.data.target) 6.144) (lte (lent ~(tap by receipts.data.target)) 6.144))
  ?>  &((lte (lent ~(tap by projects.data.target)) 16) (lte (lent ~(tap by works.data.target)) 2.048))
  ?>  &((lte (lent ~(tap by boxes.target)) 512) (lte (lent ~(tap by containers.data.target)) 512))
  ?>  &((lte (lent ~(tap by links.target)) 4.096) (lte (lent ~(tap by grants.data.target)) 2.048))
  ?>  &((lte object-bytes.data.target 8.388.608) (lte (lent ~(tap by objects.data.target)) 12.288))
  ?>  &((lte (lent ~(tap by documents.data.target)) 4.096) (lte (lent ~(tap by reachable.data.target)) 4.096))
  ?>  &((lte (lent ~(tap in tombs.target)) 4.096) (lte (lent ~(tap by generations.target)) 2.576))
  ?>  (levy ~(tap by containers.data.target) |=([id=@t val=container-state:stead-core] &((lte (lent history.val) 128) (lte (lent ~(tap by entries.val)) 32))))
  ?>  (levy ~(tap by reachable.data.target) |=([oid=@ux ids=(set @ux)] (lte (lent ~(tap in ids)) 384)))
  ?>  (lte (roll ~(tap by objects.data.target) |=([row=[@ux object:stead-git] size=@ud] (add size length.body.+.row))) 8.388.608)
  ?>  (levy ~(tap by objects.data.target) |=([oid=@ux val=object:stead-git] (lte (met 3 data.body.val) length.body.val)))
  ?>  (levy ~(tap by receipts.data.target) |=([key=[@t @t @t] val=receipt-state:stead-core] &((lte (met 3 command.val) 65.536) (lte (met 3 bytes.val) 8.192))))
  ?>  (levy journal.data.target |=([project=@t bytes=@t digest=@t] (lte (met 3 bytes) 262.144)))
  =/  rebuilt  empty:stead-team
  =.  rebuilt  rebuilt(registry registry.target, data data.rebuilt(initialized &))
  [target rebuilt (flop journal.data.target) ~ 0 %pending]
++  step
  |=  job=validation
  ^-  validation
  ?.  =(%pending status.job)  job
  =/  left=@ud  16
  |-
  ?~  remaining.job
    job(status ?:(&(=(target.job rebuilt.job) (current-consistent job)) %valid %invalid))
  ?:  =(left 0)  job
  =/  attempted  (mule |.((one job)))
  ?:  ?=(%| -.attempted)  job(status %invalid)
  $(job p.attempted, left (dec left))
++  result
  |=  job=validation
  ^-  (unit state:stead-team)
  ?:(=(%valid status.job) (some target.job) ~)
--

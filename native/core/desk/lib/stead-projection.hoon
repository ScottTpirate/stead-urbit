::  Rebuildable accepted-event index. This is never an authorization source.
/+  stead-codec, stead-team-codec, stead-team, stead-core
=,  stead-codec
|%
+$  event  [project=@t bytes=@t digest=@t]
+$  entry
  [project=@t principal=@t request=@t kind=@t container=@t resource=@t operation=@t receipt=@t]
+$  index
  $:  heads=(map @t [sequence=@ud digest=@t])
      seen=(map [@t @t @t] @t)  resources=(set [@t @t @t @t])
      entries=(list entry)
  ==
+$  state
  [visible=index shadow=index remaining=(list event) rebuilding=? poisoned=?]
++  decoded
  |=  row=event
  ^-  [cmd=command receipt=object-map sequence=@ud previous=@t]
  ?>  &((lte (met 3 bytes.row) 262.144) =(digest.row (hash 'stead.journal/3' bytes.row)))
  =/  value  (need (parse-result bytes.row))
  ?>  ?=([%o *] value)
  =/  record  p.value
  ?>  (keys record ~['protocol' 'sequence' 'previous_digest' 'canonical_command' 'receipt' 'old_revision' 'new_revision' 'authentication_context' 'grant_target'])
  ?>  &(=(bytes.row (canonical value)) =('stead.journal/3' (field record 'protocol')))
  =/  cmd  (decode:stead-team-codec (field record 'canonical_command'))
  ?>  &(=(project.row project.cmd) =(canonical-bytes.cmd (field record 'canonical_command')))
  =/  receipt-json  (need (parse-result (field record 'receipt')))
  ?>  ?=([%o *] receipt-json)
  =/  receipt  p.receipt-json
  ?>  =((field record 'receipt') (canonical receipt-json))
  ?>  (keys receipt ~['protocol' 'status' 'request_id' 'canonical_sha256' 'project_id' 'resource_id' 'resource_kind' 'container_id' 'resource_revision' 'authority_epoch' 'operation' 'principal_id' 'binding_id' 'binding_revision' 'identity_ship' 'authentication' 'authentication_strength' 'session_audit_id' 'runtime' 'accepted_at_ms' 'git_commit_oid'])
  ?>  &(=('stead.receipt/3' (field receipt 'protocol')) =('accepted' (field receipt 'status')))
  ?>  &(=(request.cmd (field receipt 'request_id')) =(digest.cmd (field receipt 'canonical_sha256')))
  ?>  &(=(project.cmd (field receipt 'project_id')) =(resource.cmd (field receipt 'resource_id')))
  ?>  &(=(operation.cmd (field receipt 'operation')) =((kind:stead-team-codec operation.cmd) (field receipt 'resource_kind')))
  ?>  =((container:stead-team-codec cmd) (field receipt 'container_id'))
  ?>  &(=(epoch.cmd (uint (field receipt 'authority_epoch'))) =(expected.cmd (uint (field record 'old_revision'))))
  ?>  &(=(+(expected.cmd) (uint (field record 'new_revision'))) =((field record 'new_revision') (field receipt 'resource_revision')))
  ?>  &((uuid (field receipt 'principal_id')) (uuid (field receipt 'binding_id')) (gth (uint (field receipt 'binding_revision')) 0))
  =/  ship  (need (slaw %p (field receipt 'identity_ship')))
  ?>  =((scot %p ship) (field receipt 'identity_ship'))
  ?>  ?|  &(=('native-sender/1' (field receipt 'authentication')) =('native-sender' (field receipt 'authentication_strength')) =('' (field receipt 'session_audit_id')))
          &(=('native-approved-browser/1' (field receipt 'authentication')) =('native-approved-browser' (field receipt 'authentication_strength')) (opaque:stead-team-codec (field receipt 'session_audit_id')))
      ==
  ?>  &(=('isolated-fake' (field receipt 'runtime')) (gth (uint (field receipt 'accepted_at_ms')) 0))
  =/  actor  (decode-authentication:stead-team (field record 'authentication_context'))
  ?>  &((gth expires.actor (uint (field receipt 'accepted_at_ms'))) =(principal.identity.actor (field receipt 'principal_id')) =(binding.identity.actor (field receipt 'binding_id')))
  ?>  &(=((decimal revision.identity.actor) (field receipt 'binding_revision')) =((scot %p ship.identity.actor) (field receipt 'identity_ship')))
  ?>  &(=(method.actor (field receipt 'authentication')) =(strength.actor (field receipt 'authentication_strength')) =(audit.actor (field receipt 'session_audit_id')) =(runtime.actor (field receipt 'runtime')))
  =/  target  (field record 'grant_target')
  ?>  ?:  =('policy.grant' operation.cmd)
        =/  who  (decode-actor:stead-team target)
        &((gth expires.who (uint (field receipt 'accepted_at_ms'))) =(principal.who (field payload.cmd 'principal_id')))
      =('' target)
  =/  oid  (field receipt 'git_commit_oid')
  ?>  ?:(=('document' (kind:stead-team-codec operation.cmd)) (oid:stead-team-codec oid) =('' oid))
  [cmd receipt (uint (field record 'sequence')) (field record 'previous_digest')]
++  advance
  |=  [view=index row=event]
  ^-  index
  =/  decoded  (decoded row)
  =/  cmd  cmd.decoded
  =/  receipt  receipt.decoded
  =/  key  [project.cmd (field receipt 'principal_id') request.cmd]
  =/  duplicate  (~(get by seen.view) key)
  ?^  duplicate
    ?>  =(u.duplicate digest.row)
    view
  ?>  (lth (lent entries.view) 6.144)
  =/  head  (~(get by heads.view) project.cmd)
  ?>  =(sequence.decoded ?~(head 1 +(sequence.u.head)))
  ?>  =(previous.decoded ?~(head (hex 64 0) digest.u.head))
  =/  kind  (kind:stead-team-codec operation.cmd)
  =/  container  (container:stead-team-codec cmd)
  =.  heads.view  (~(put by heads.view) project.cmd [sequence.decoded digest.row])
  =.  seen.view  (~(put by seen.view) key digest.row)
  =?  resources.view  !=('policy' kind)
    (~(put in resources.view) [project.cmd kind container resource.cmd])
  view(entries [[project.cmd (field receipt 'principal_id') request.cmd kind container resource.cmd operation.cmd (canonical [%o receipt])] entries.view])
++  begin
  |=  [db=state:stead-team prior=state]
  ^-  state
  ?>  (lte (lent journal.data.db) 6.144)
  prior(shadow *index, remaining (flop journal.data.db), rebuilding &, poisoned |)
++  batch
  |=  [db=state:stead-team prior=state]
  ^-  state
  ?:  ?|(!rebuilding.prior poisoned.prior)  prior
  =/  left=@ud  16
  |-
  ?~  remaining.prior
    ?.  &(=(heads.shadow.prior (heads db)) =((lent entries.shadow.prior) (lent journal.data.db)))
      prior(poisoned &)
    prior(visible shadow.prior, shadow *index, remaining ~, rebuilding |)
  ?:  =(left 0)  prior
  =/  attempted  (mule |.((advance shadow.prior i.remaining.prior)))
  ?:  ?=(%| -.attempted)  prior(poisoned &)
  $(left (dec left), prior prior(shadow p.attempted, remaining t.remaining.prior))
++  append
  |=  [prior=state row=event]
  ^-  state
  ?:  poisoned.prior  prior
  ?:  rebuilding.prior
    ?>  (lth (lent remaining.prior) 6.144)
    prior(remaining (weld remaining.prior [row ~]))
  =/  attempted  (mule |.((advance visible.prior row)))
  ?:  ?=(%| -.attempted)  prior(poisoned &)
  prior(visible p.attempted)
++  heads
  |=  db=state:stead-team
  ^-  (map @t [sequence=@ud digest=@t])
  =/  rows  journal.data.db
  =/  out=(map @t [sequence=@ud digest=@t])  ~
  |-
  ?~  rows  out
  ?:  (~(has by out) project.i.rows)  $(rows t.rows)
  =/  value  (decoded i.rows)
  $(rows t.rows, out (~(put by out) project.i.rows [sequence.value digest.i.rows]))
++  ready
  |=  [db=state:stead-team view=state]
  ^-  ?
  &(!rebuilding.view !poisoned.view =((lent journal.data.db) (lent entries.visible.view)) =(heads.visible.view (heads db)))
--

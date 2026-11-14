::  Canonical private worker wires. Authenticated provenance comes from the
::  caller. A decoded proof is evidence for the ledger, not authorization.
/+  stead-codec, stead-code-credentials, stead-code-pack-anchor, stead-code-pack-push, stead-code-pack-ledger, stead-code-receive, stead-code-git-objects, stead-code-git-graph, stead-session, stead-git
=,  stead-codec
|%
+$  scope  scope:stead-code-credentials
+$  manifest  manifest:stead-code-pack-anchor
+$  intent  intent:stead-code-pack-ledger
+$  update  update:stead-code-receive
+$  kind  object-kind:stead-code-git-graph
+$  pin  [ship=@p principal=@t binding=@t revision=@ud]
+$  admission-view  [claim=intent who=pin since=@ud until=@ud]
+$  row  [change=update type=(unit kind)]
+$  fields  object-map:stead-codec
++  number-text
  |=  [text=@t positive=?]
  ^-  @ud
  =/  value  (uint text)
  ?>  &(=((decimal value) text) |(!positive !=(0 value)))
  value
++  hash-wire
  |=  raw=@t
  ^-  @t
  =/  size  (met 3 raw)
  (hex 64 (sha-256l:sha [size (rev 3 size raw)]))
++  read-wire
  |=  raw=@t
  ^-  fields
  ?>  (lte (met 3 raw) 65.536)
  =/  parsed  (need (parse-result raw))
  ?>  ?=([%o *] parsed)
  ?>  =(raw (cat 3 (canonical parsed) 10))
  p.parsed
++  nested
  |=  [root=fields name=@t]
  ^-  fields
  =/  value  (~(got by root) name)
  ?>  ?=([%o *] value)
  p.value
++  shared
  ^-  (list @t)
  :~  'scope'  'base_snapshot'  'generation'  'attempt'  'incarnation'  'request_id'
      'actor'  'wire_sha256'  'update_count'  'admitted_at_ms'  'expires_at_ms'
  ==
++  read-scope
  |=  obj=fields
  ^-  scope
  ?>  (keys obj ~['home' 'project_id' 'repository_id' 'authority_epoch'])
  =/  home  (field obj 'home')
  =/  ship  (need (slaw %p home))
  ?>  =((scot %p ship) home)
  =/  out=scope
    [ship (field obj 'project_id') (field obj 'repository_id') (number-text (field obj 'authority_epoch') &)]
  ?>  (scope-valid:stead-code-credentials out)
  ?>  =(project.out repository.out)
  out
++  read-actor
  |=  [obj=fields home=@p]
  ^-  pin
  ?>  (keys obj ~['identity_ship' 'principal_id' 'binding_id' 'binding_revision'])
  =/  text  (field obj 'identity_ship')
  =/  ship  (need (slaw %p text))
  ?>  &(!=(ship home) (lte (met 0 ship) 128) =((scot %p ship) text))
  =/  principal  (field obj 'principal_id')
  =/  binding  (field obj 'binding_id')
  ?>  &((uuid principal) (uuid binding))
  [ship principal binding (number-text (field obj 'binding_revision') &)]
++  read-row
  |=  [obj=fields proof=?]
  ^-  row
  ?>  (keys obj ?:(proof ~['ref' 'prior' 'target' 'kind' 'lineage'] ~['ref' 'prior' 'target']))
  =/  key  (field obj 'ref')
  ?>  (ref:stead-code-pack-anchor key |)
  =/  size  (div (met 3 key) 2)
  =/  name=@t  (rev 3 size (raw-ref:stead-code-pack-push key))
  ?>  (valid-ref:stead-code-git-objects [size name])
  =/  old  (need (parse-oid:stead-code-git-objects [40 (field obj 'prior')]))
  =/  new  (need (parse-oid:stead-code-git-objects [40 (field obj 'target')]))
  =/  branch  =('refs/heads/' (cut 3 [0 11] name))
  ?>  &(!=(new 0) !=(new old) |(branch =(old 0)))
  =/  change=update  [name old new]
  ?.  proof  [change ~]
  =/  type=@tas  (field obj 'kind')
  ?>  ?=(kind type)
  ?>  |(!branch =(%commit type))
  ?>  =((field obj 'lineage') ?:(=(old 0) 'none' 'fast-forward'))
  [change [~ type]]
++  read-rows
  |=  [root=fields name=@t proof=?]
  ^-  (list row)
  =/  count  (number-text (field root 'update_count') &)
  ?>  (lte count 32)
  =/  obj  (nested root name)
  ?>  =(count ~(wyt by obj))
  =/  cursor=@ud  0
  =/  seen=(set @t)  ~
  =/  result=(list row)  ~
  |-
  ^-  (list row)
  ?:  =(count cursor)  (flop result)
  =/  label  ?:((lth cursor 10) (cat 3 '0' (decimal cursor)) (decimal cursor))
  =/  item  (read-row (nested obj label) proof)
  ?>  !(~(has in seen) name.change.item)
  $(cursor +(cursor), seen (~(put in seen) name.change.item), result [item result])
++  read-admission
  |=  [obj=fields rows=(list row) base=manifest]
  ^-  admission-view
  =/  destination  (read-scope (nested obj 'scope'))
  ?>  =(destination destination.base)
  =/  who  (read-actor (nested obj 'actor') home.destination)
  =/  generation  (number-text (field obj 'generation') |)
  ?>  (lth generation 7)
  =/  changes  (turn rows |=(item=row change.item))
  =/  since  (number-text (field obj 'admitted_at_ms') &)
  =/  until  (number-text (field obj 'expires_at_ms') &)
  ?>  &((lth since until) (lte until (add since 300.000)))
  =/  claim=intent
    :*  destination  (field obj 'base_snapshot')  generation
        (field obj 'wire_sha256')  (field obj 'request_id')
        (number-text (field obj 'attempt') &)  (field obj 'incarnation')  changes
    ==
  ?>  =(base.claim snapshot.base)
  ?>  (valid-intent:stead-code-pack-ledger claim)
  [claim who since until]
++  decode-admission
  |=  [raw=@t expected-sha=@t base=manifest]
  ^-  (unit admission-view)
  =/  out
    %-  mule
    |.
    ?>  &((lte (met 3 raw) 65.536) =(expected-sha (hash-wire raw)))
    ?>  (valid-manifest:stead-code-pack-anchor base)
    =/  obj  (read-wire raw)
    ?>  (keys obj ['protocol' 'changes' shared])
    ?>  =('stead.git-pack-admission/1' (field obj 'protocol'))
    (read-admission obj (read-rows obj 'changes' |) base)
  ?:  ?=(%| -.out)  ~
  [~ p.out]
++  derive
  |=  [base=manifest rows=(list row)]
  ^-  [refs=(map @t @t) kinds=(map @ux kind) lineage=(set [@ux @ux])]
  =/  refs  refs.base
  =/  kinds=(map @ux kind)  ~
  =/  lineage=(set [@ux @ux])  ~
  |-
  ^-  [refs=(map @t @t) kinds=(map @ux kind) lineage=(set [@ux @ux])]
  ?~  rows  [refs kinds lineage]
  =/  item  i.rows
  =/  change  change.item
  =/  kind  (need type.item)
  =/  found  (~(get by kinds) target.change)
  ?>  ?~(found & =(u.found kind))
  =?  lineage  !=(prior.change 0)
    (~(put in lineage) [prior.change target.change])
  %=  $
    rows      t.rows
    refs      (~(put by refs) (bytes-hex name.change) (oid-text:stead-git target.change))
    kinds     (~(put by kinds) target.change kind)
    lineage   lineage
  ==
++  decode-proof
  |=  [raw=@t admitted=@t expected-sha=@t base=manifest]
  ^-  (unit evidence:stead-code-pack-push)
  =/  out
    %-  mule
    |.
    =/  original  (need (decode-admission admitted expected-sha base))
    =/  obj  (read-wire raw)
    ?>  (keys obj ['protocol' 'admission_sha256' 'candidate_snapshot' 'head' 'updates' 'pack' shared])
    ?>  =('stead.git-pack-worker-proof/1' (field obj 'protocol'))
    ?>  =(expected-sha (field obj 'admission_sha256'))
    ?>  =(head.base (field obj 'head'))
    =/  rows  (read-rows obj 'updates' &)
    ?>  =(original (read-admission obj rows base))
    =/  claim  claim.original
    =/  derived  (derive base rows)
    =/  pack  (nested obj 'pack')
    ?>  (keys pack ~['pack_sha256' 'pack_bytes' 'object_count' 'object_bytes' 'object_ids_sha256'])
    =/  next=manifest
      :*  destination.claim  (field obj 'candidate_snapshot')  head.base  refs.derived
          (field pack 'pack_sha256')  (number-text (field pack 'pack_bytes') &)
          (number-text (field pack 'object_count') &)  (number-text (field pack 'object_bytes') &)
          (field pack 'object_ids_sha256')
      ==
    =/  evidence=evidence:stead-code-pack-push
      :*  destination.claim  base.claim  generation.claim  wire.claim  request.claim
          changes.claim  next  kinds.derived  lineage.derived
      ==
    =/  checked
      (decide:stead-code-pack-push destination.claim generation.claim base evidence ~ |=([action:stead-code-receive update] &))
    ?>  ?=(%candidate -.checked)
    evidence
  ?:  ?=(%| -.out)  ~
  [~ p.out]
--

::  Build the exact private worker admission from Home-selected inputs.
::  The Home authenticates the member and owns the transition and clock.
/+  stead-codec, stead-code-credentials, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-proof, stead-code-receive, stead-git, stead-session
=,  stead-codec
|%
+$  scope  scope:stead-code-credentials
+$  intent  intent:stead-code-pack-ledger
+$  actor  actor:stead-session
+$  manifest  manifest:stead-code-pack-anchor
+$  update  update:stead-code-receive
+$  result  [wire=@t digest=@t]
++  rows
  |=  changes=(list update)
  ^-  json
  =/  index=@ud  0
  =/  result=object-map  ~
  |-
  ^-  json
  ?~  changes  [%o result]
  =/  label  ?:((lth index 10) (cat 3 '0' (decimal index)) (decimal index))
  =/  item
    %-  object
    :~  ['ref' (bytes-hex name.i.changes)]
        ['prior' (oid-text:stead-git prior.i.changes)]
        ['target' (oid-text:stead-git target.i.changes)]
    ==
  $(changes t.changes, index +(index), result (~(put by result) label item))
++  build
  |=  [selected=scope claim=intent who=actor now=@ud base=manifest]
  ^-  (unit result)
  ?.  ?&  =(selected destination.claim)
          =(selected destination.base)
          =(base.claim snapshot.base)
          (scope-valid:stead-code-credentials selected)
          =(project.selected repository.selected)
          (valid-intent:stead-code-pack-ledger claim)
          (lth generation.claim 7)
          (gth now 0)
          (live:stead-session who now)
          !=(ship.who home.selected)
          (lte (met 0 ship.who) 128)
      ==
    ~
  =/  until  (min expires.who (add now 300.000))
  =/  actor-json
    %-  object
    :~  ['identity_ship' (scot %p ship.who)]
        ['principal_id' principal.who]
        ['binding_id' binding.who]
        ['binding_revision' (decimal revision.who)]
    ==
  =/  scope-json
    %-  object
    :~  ['home' (scot %p home.selected)]
        ['project_id' project.selected]
        ['repository_id' repository.selected]
        ['authority_epoch' (decimal epoch.selected)]
    ==
  =/  plain
    %-  object
    :~  ['protocol' 'stead.git-pack-admission/1']
        ['base_snapshot' base.claim]
        ['generation' (decimal generation.claim)]
        ['attempt' (decimal attempt.claim)]
        ['incarnation' incarnation.claim]
        ['request_id' request.claim]
        ['wire_sha256' wire.claim]
        ['update_count' (decimal (lent changes.claim))]
        ['admitted_at_ms' (decimal now)]
        ['expires_at_ms' (decimal until)]
    ==
  ?>  ?=([%o *] plain)
  =/  fields  (~(put by p.plain) 'actor' actor-json)
  =.  fields  (~(put by fields) 'scope' scope-json)
  =.  fields  (~(put by fields) 'changes' (rows changes.claim))
  =/  raw  (cat 3 (canonical [%o fields]) 10)
  ?.  (lte (met 3 raw) 65.536)  ~
  =/  digest  (hash-wire:stead-code-pack-proof raw)
  =/  checked  (decode-admission:stead-code-pack-proof raw digest base)
  ?~  checked  ~
  ?.  =(u.checked [claim [ship.who principal.who binding.who revision.who] now until])  ~
  [~ raw digest]
--

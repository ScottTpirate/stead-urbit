::  Pure protected-HEAD promotion preflight for one selected external pack.
::  The Home supplies the current selection, authenticated caller, current
::  member/policy gates, latest stored proposal and stored approval. A caller
::  must never substitute request fields for either stored review record.
::  No board, pack ledger, acceptance receipt or ref is mutated here.
::
::  This first profile promotes an already accepted branch tip, retaining
::  the exact pack/object inventory. Worker kinds/ancestry are authenticated
::  facts bound by the Home to this selection and candidate, not user claims.
::  Home must recheck selection/policy and atomically persist any subsequent
::  acceptance with capacity, request replay and latest-revision checks.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-review, stead-code-pack-anchor, stead-code-pack-push, stead-code-receive, stead-code-git-objects, stead-git
|%
+$  scope  scope:stead-code-credentials
+$  actor  actor:stead-session
+$  manifest  manifest:stead-code-pack-anchor
+$  role  ?(%propose %review %merge)
+$  permit  $-([actor scope @t @t role] ?)
+$  authority
  [destination=scope now=@ud resolve=membership:stead-code-credentials allows=permit]
+$  proposal
  $:  destination=scope  snapshot=@t  generation=@ud  owner=actor
      source=@t  item=proposal:stead-code-review
  ==
+$  approval  [reviewed=proposal reviewer=actor approved-at=@ud]
+$  candidate
  [decision=candidate:stead-code-pack-push review=approval merger=actor]
::
++  active
  |=  [env=authority who=actor]
  ^-  (unit actor)
  ?:  =(ship.who home.destination.env)  ~
  ?.  (lte (met 0 ship.who) 128)  ~
  =/  current  (resolve.env ship.who)
  ?~  current  ~
  ?.  &((live:stead-session u.current now.env) (same-actor:stead-session who u.current))  ~
  current
++  allowed
  |=  [env=authority who=actor item=proposal:stead-code-review capability=role]
  ^-  ?
  =/  current  (active env who)
  ?~  current  |
  (allows.env u.current destination.env work.item target.location.item capability)
++  branch
  |=  name=@t
  ^-  ?
  ?&  (lte (met 3 name) 1.024)
      =('refs/heads/' (cut 3 [0 11] name))
      (valid-ref:stead-code-git-objects [(met 3 name) name])
  ==
::  Source-tip membership and target CAS are separate exact comparisons.
::  Ancestry is deliberately not inferred from either ref or its spelling.
++  check-proposal
  |=  [env=authority generation=@ud current=manifest row=proposal]
  ^-  (unit @tas)
  ?.  ?&  (scope-valid:stead-code-credentials destination.env)
          =(destination.env destination.current)
          (gth now.env 0)  (lte now.env 18.446.744.073.709.551.615)
          (lth generation 18.446.744.073.709.551.615)
          (valid-manifest:stead-code-pack-anchor current)
      ==
    [~ %invalid-selection]
  ?.  ?&  =(destination.row destination.env)
          =(snapshot.row snapshot.current)
          =(generation.row generation)
      ==
    [~ %stale-selection]
  =/  item  item.row
  ?.  ?&  (branch source.row)
          (branch target.location.item)
          (valid-proposal:stead-code-review item)
          (uuid:stead-codec id.item)  (uuid:stead-codec work.item)
          (lte number.change.item 64)
          =(author.item principal.owner.row)
          =(project.location.item project.destination.env)
          =(repo.location.item repository.destination.env)
          =(epoch.change.item epoch.destination.env)
          =((bytes-hex:stead-codec target.location.item) head.current)
          !=(0 base.change.item)
      ==
    [~ %invalid-proposal]
  ?.  =((~(get by refs.current) head.current) [~ (oid-text:stead-git base.change.item)])
    [~ %stale-target]
  ?.  =((~(get by refs.current) (bytes-hex:stead-codec source.row)) [~ (oid-text:stead-git head.change.item)])
    [~ %source-conflict]
  ?.  (allowed env owner.row item %propose)  [~ %denied]
  ~
++  propose
  |=  $:  env=authority  generation=@ud  current=manifest  caller=actor
          source=@t  item=proposal:stead-code-review
      ==
  ^-  (each proposal @tas)
  =/  owner  (active env caller)
  ?~  owner  [%| %denied]
  =/  row=proposal
    [destination.env snapshot.current generation u.owner source item]
  =/  fault  (check-proposal env generation current row)
  ?^  fault  [%| u.fault]
  [%& row]
++  approve
  |=  [env=authority generation=@ud current=manifest caller=actor row=proposal]
  ^-  (each approval @tas)
  =/  fault  (check-proposal env generation current row)
  ?^  fault  [%| u.fault]
  =/  reviewer  (active env caller)
  ?~  reviewer  [%| %denied]
  ?.  (allowed env u.reviewer item.row %review)  [%| %denied]
  =/  review-permit=permission:stead-code-review
    |=  [principal=@t at=scope:stead-code-review]
    &(=(principal principal.u.reviewer) =(at location.item.row))
  =/  checked
    (approve:stead-code-review item.row epoch.destination.env principal.u.reviewer review-permit)
  ?:  ?=(%| -.checked)  [%| p.checked]
  [%& row u.reviewer now.env]
++  preflight
  |=  $:  env=authority  generation=@ud  current=manifest  caller=actor
          row=proposal  accepted=approval  checked=evidence:stead-code-pack-push
      ==
  ^-  (each candidate @tas)
  =/  fault  (check-proposal env generation current row)
  ?^  fault  [%| u.fault]
  ?.  =(row reviewed.accepted)  [%| %stale-review]
  ?.  ?&  (gth approved-at.accepted 0)
          (lte approved-at.accepted now.env)
          (live:stead-session reviewer.accepted approved-at.accepted)
      ==
    [%| %invalid-approval]
  =/  merger  (active env caller)
  ?~  merger  [%| %denied]
  ?.  &((allowed env reviewer.accepted item.row %review) (allowed env u.merger item.row %merge))
    [%| %denied]
  =/  review-permit=permission:stead-code-review
    |=  [principal=@t at=scope:stead-code-review]
    &(=(principal principal.reviewer.accepted) =(at location.item.row))
  =/  merge-permit=permission:stead-code-review
    |=  [principal=@t at=scope:stead-code-review]
    &(=(principal principal.u.merger) =(at location.item.row))
  =/  reviewed=approval:stead-code-review
    [principal.reviewer.accepted item.reviewed.accepted]
  =/  ready
    (check-merge:stead-code-review item.row reviewed epoch.destination.env base.change.item.row principal.u.merger review-permit merge-permit)
  ?:  ?=(%| -.ready)  [%| p.ready]
  ::  Exactly this reviewed update, with no hidden companion update. The
  ::  existing pack gate checks every final ref, object kind and ancestry.
  ?.  =(changes.checked [p.ready ~])  [%| %review-change-conflict]
  ?.  ?&  =(pack-sha.current pack-sha.pack.checked)
          =(pack-bytes.current pack-bytes.pack.checked)
          =(objects.current objects.pack.checked)
          =(object-bytes.current object-bytes.pack.checked)
          =(ids-sha.current ids-sha.pack.checked)
      ==
    [%| %pack-conflict]
  =/  authorize=$-([action:stead-code-receive update:stead-code-receive] ?)
    |=  [intent=action:stead-code-receive change=update:stead-code-receive]
    &(=(%advance intent) =(change p.ready))
  ::  This private call admits only the exact reviewed HEAD advance. The raw
  ::  push route/ledger retains its own protected-ref refusal unchanged.
  =/  result
    (decide:stead-code-pack-push destination.env generation current checked ~ authorize)
  ?:  ?=(%rejected -.result)  [%| reason.result]
  [%& next.result accepted u.merger]
--

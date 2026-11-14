::  Saved reviewed-promotion structure, independent of any ledger or board.
::  Historical validation does not authenticate a worker or reconstruct old
::  grants. Creation requires current Home authorization and atomic append.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-review, stead-code-pack-review, stead-code-pack-push, stead-code-pack-anchor, stead-code-git-graph, stead-code-receive
|%
+$  actor  actor:stead-session
+$  manifest  manifest:stead-code-pack-anchor
+$  proposal  proposal:stead-code-pack-review
+$  approval  approval:stead-code-pack-review
+$  candidate  candidate:stead-code-pack-review
+$  record
  $:  version=@ud  request=@t  merger=actor  accepted-at=@ud
      base=manifest  candidate=candidate
      kinds=(map @ux object-kind:stead-code-git-graph)
      lineage=(set [@ux @ux])
  ==
++  proposal-valid
  |=  row=proposal
  ^-  ?
  =/  item  item.row
  ?&  (scope-valid:stead-code-credentials destination.row)
      =(project.destination.row repository.destination.row)
      (token-valid:stead-session snapshot.row)
      (lth generation.row 18.446.744.073.709.551.615)
      (live:stead-session owner.row 1)
      (lte (met 0 ship.owner.row) 128)
      !=(ship.owner.row home.destination.row)
      (branch:stead-code-pack-review source.row)
      (branch:stead-code-pack-review target.location.item)
      (valid-proposal:stead-code-review item)
      (uuid:stead-codec id.item)  (uuid:stead-codec work.item)
      (lte number.change.item 64)
      =(author.item principal.owner.row)
      =(project.location.item project.destination.row)
      =(repo.location.item repository.destination.row)
      =(epoch.change.item epoch.destination.row)
      !=(0 base.change.item)
  ==
++  approval-valid
  |=  row=approval
  ^-  ?
  ?&  (proposal-valid reviewed.row)
      (gth approved-at.row 0)
      (lte approved-at.row 18.446.744.073.709.551.615)
      (live:stead-session reviewer.row approved-at.row)
      (lte (met 0 ship.reviewer.row) 128)
      !=(ship.reviewer.row home.destination.reviewed.row)
      !=(ship.reviewer.row ship.owner.reviewed.row)
      !=(principal.reviewer.row author.item.reviewed.row)
  ==
++  evidence
  |=  saved=record
  ^-  evidence:stead-code-pack-push
  =/  decision  decision.candidate.saved
  :*  destination.decision  base.decision
      generation.reviewed.review.candidate.saved
      wire.decision  request.decision  changes.decision  pack.decision
      kinds.saved  lineage.saved
  ==
++  valid
  |=  saved=record
  ^-  ?
  =/  next  candidate.saved
  =/  review  review.next
  =/  row  reviewed.review
  =/  item  item.row
  ?.  ?&  =(1 version.saved)
          (uuid:stead-codec request.saved)
          =(request.saved request.decision.next)
          =(merger.saved merger.next)
          (gth accepted-at.saved 0)
          (lte accepted-at.saved 18.446.744.073.709.551.615)
          (live:stead-session merger.saved accepted-at.saved)
          (lte (met 0 ship.merger.saved) 128)
          !=(ship.merger.saved home.destination.row)
          !=(ship.merger.saved ship.owner.row)
          (approval-valid review)
          (lte approved-at.review accepted-at.saved)
          ?:  =(ship.reviewer.review ship.merger.saved)
            (same-actor:stead-session reviewer.review merger.saved)
          &
      ==
    |
  ::  Only a structural historical member view. Expiry at creation remains
  ::  well formed; later renewal/revocation must not invalidate saved history.
  =/  historical=authority:stead-code-pack-review
    =/  resolve=membership:stead-code-credentials
      |=  ship=@p
      ?:(=(ship ship.owner.row) [~ owner.row] ~)
    =/  allows=permit:stead-code-pack-review
      |=  [actor scope:stead-code-credentials @t @t role:stead-code-pack-review]
      &
    [destination.row 1 resolve allows]
  ?^  (check-proposal:stead-code-pack-review historical generation.row base.saved row)
    |
  =/  allowed=permission:stead-code-review
    |=  [@t scope:stead-code-review]
    &
  =/  checked-review=approval:stead-code-review
    [principal.reviewer.review item]
  =/  ready
    (check-merge:stead-code-review item checked-review epoch.destination.row base.change.item principal.merger.saved allowed allowed)
  ?:  ?=(%| -.ready)  |
  ?.  =(changes.decision.next [p.ready ~])  |
  ?.  ?&  =(pack-sha.base.saved pack-sha.pack.decision.next)
          =(pack-bytes.base.saved pack-bytes.pack.decision.next)
          =(objects.base.saved objects.pack.decision.next)
          =(object-bytes.base.saved object-bytes.pack.decision.next)
          =(ids-sha.base.saved ids-sha.pack.decision.next)
      ==
    |
  =/  authorize=$-([action:stead-code-receive update:stead-code-receive] ?)
    |=  [action=action:stead-code-receive change=update:stead-code-receive]
    &(=(action %advance) =(change p.ready))
  =/  result
    (decide:stead-code-pack-push destination.row generation.row base.saved (evidence saved) ~ authorize)
  ?:  ?=(%rejected -.result)  |
  =(next.result decision.next)
--

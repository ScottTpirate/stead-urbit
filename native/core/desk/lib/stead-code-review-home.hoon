::  Home-only protected review transitions. Caller supplies the authenticated
::  actor and current Work/project policy. Ref and object facts come from repo.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-review, stead-code-delivery, stead-code-store, stead-code-git-graph
|%
+$  actor  actor:stead-session
+$  scope  scope:stead-code-credentials
+$  proposal  proposal:stead-code-review
+$  repo-state  state:stead-code-store
+$  receipt  receipt:stead-code-store
+$  authority  authority:stead-code-delivery
+$  merge-record  [id=@t number=@ud]
+$  state
  [version=@ud board=state:stead-code-delivery merges=(map @t merge-record)]
+$  command
  $%  [%submit item=proposal via=(unit @t)]
      [%delegate id=@t worker=@p work=@t target=@t expires=@ud]
      [%revoke id=@t]
      [%approve id=@t number=@ud]
      [%merge id=@t number=@ud request=@t]
  ==
+$  result
  $%  [%applied next=state repo=repo-state receipt=(unit receipt)]
      [%replayed next=state repo=repo-state receipt=(unit receipt)]
      [%rejected reason=@tas]
  ==
+$  view  [item=proposal reviewer=(unit @t) merged=(unit @ud)]
+$  view-policy  $-([actor scope @t @t] ?)
::
++  empty
  |=  destination=scope
  ^-  state
  [1 (empty:stead-code-delivery destination) ~]
++  source
  |=  repo=repo-state
  ^-  inspect:stead-code-delivery
  |=  [who=actor item=proposal]
  ^-  (unit @t)
  =/  load=reader:stead-code-git-graph
    |=  id=@ux
    (~(get by objects.repo) id)
  =/  graph  (closure:stead-code-store refs.repo load)
  ?:  ?=(%| -.graph)  ~
  =/  head  head.change.item
  =/  base  base.change.item
  ?.  =([~ %commit] (~(get by p.graph) head))  ~
  ?.  |(=(0 base) =([~ %commit] (~(get by p.graph) base)))  ~
  =/  found  (load head)
  ?~  found  ~
  [~ (hash:stead-codec 'stead.code-reviewed-source/1' (bytes-hex:stead-codec (jam [destination.repo head u.found])))]
++  digest
  |=  [request=@t item=proposal who=actor]
  ^-  @t
  =/  material  [request item ship.who principal.who binding.who revision.who]
  (hash:stead-codec 'stead.code-reviewed-merge/1' (bytes-hex:stead-codec (jam material)))
++  change
  |=  item=proposal
  ^-  update:stead-code-store
  [target.location.item base.change.item head.change.item]
++  linked-receipt
  |=  [db=state repo=repo-state request=@t key=merge-record]
  ^-  (unit receipt)
  =/  row  (~(get by revisions.board.db) key)
  ?~  row  ~
  ?.  (~(has by reviews.board.db) key)  ~
  =/  found  (~(get by receipts.repo) request)
  ?~  found  ~
  =/  accepted  u.found
  =/  item  item.u.row
  ?.  ?&  (uuid:stead-codec request)
          =(1 version.accepted)
          =(destination.repo destination.accepted)
          =(request id.accepted)
          (gth revision.accepted 0)
          (lte revision.accepted revision.repo)
          (valid-actor owner.accepted)
          !=(author.item principal.owner.accepted)
          =(~[(change item)] changes.accepted)
          =((digest request item owner.accepted) digest.accepted)
      ==
    ~
  found
++  live-review
  |=  [db=state env=authority key=merge-record item=proposal]
  ^-  ?
  =/  found  (~(get by reviews.board.db) key)
  ?~  found  |
  ?&  =(reviewed.proof.u.found item)
      =(reviewer.proof.u.found principal.reviewer.u.found)
      !=(author.item principal.reviewer.u.found)
      (allowed:stead-code-delivery env reviewer.u.found work.item target.location.item %review)
  ==
++  merge
  |=  $:  db=state  repo=repo-state  protected=(set @t)  env=authority
          caller=actor  key=merge-record  request=@t
      ==
  ^-  result
  ?.  (uuid:stead-codec request)  [%rejected %invalid-request]
  =/  row  (~(get by revisions.board.db) key)
  ?~  row  [%rejected %denied]
  =/  item  item.u.row
  ?.  ?&  (eligible:stead-code-delivery board.db env u.row)
          !=(author.item principal.caller)
          (allowed:stead-code-delivery env caller work.item target.location.item %merge)
      ==
    [%rejected %denied]
  ?.  (live-review db env key item)  [%rejected %review-required-or-denied]
  =/  previous  (~(get by merges.db) request)
  ?^  previous
    ?.  =(key u.previous)  [%rejected %request-id-reused]
    =/  found  (linked-receipt db repo request key)
    ?~  found  [%rejected %invalid-receipt]
    ?.  (same-actor:stead-session owner.u.found caller)  [%rejected %denied]
    [%replayed db repo found]
  ?:  |((~(has by receipts.repo) request) (~(has by pending.repo) request))  [%rejected %request-id-reused]
  ?:  (lien ~(tap by merges.db) |=([id=@t prior=merge-record] =(prior key)))  [%rejected %already-merged]
  ?:  (gte ~(wyt by merges.db) 32)  [%rejected %capacity]
  ?.  (~(has in protected) target.location.item)  [%rejected %protected-target-required]
  =/  candidate  (merge-candidate:stead-code-delivery board.db env caller id.key number.key)
  ?:  ?=(%| -.candidate)  [%rejected p.candidate]
  =/  committed  (commit-reviewed:stead-code-store repo caller request (digest request item caller) p.candidate)
  ?:  ?=(%rejected -.committed)  [%rejected reason.committed]
  ?.  ?=(%applied -.committed)  [%rejected %invalid-receipt]
  [%applied db(merges (~(put by merges.db) request key)) next.committed [~ accepted.committed]]
++  perform
  |=  [db=state repo=repo-state protected=(set @t) env=authority caller=actor action=command]
  ^-  result
  ?.  &((scoped:stead-code-delivery board.db env) =(1 version.db) =(destination.repo destination.env))  [%rejected %denied]
  =/  current  (active:stead-code-delivery env caller)
  ?~  current  [%rejected %denied]
  =/  tip=refs:stead-code-delivery
    |=  target=@t
    (fall (~(get by refs.repo) target) 0x0)
  =.  env  env(tip tip, source (source repo))
  ?:  ?=(%merge -.action)
    (merge db repo protected env u.current [id.action number.action] request.action)
  =/  applied=result:stead-code-delivery
    ?-  -.action
      %submit  (submit:stead-code-delivery board.db env u.current item.action via.action)
      %approve  (approve:stead-code-delivery board.db env u.current id.action number.action)
      %revoke  (revoke:stead-code-delivery board.db env u.current id.action)
      %delegate
        =/  worker  (resolve.env worker.action)
        ?~  worker  [%rejected %denied]
        ?.  =(ship.u.worker worker.action)  [%rejected %denied]
        (delegate:stead-code-delivery board.db env u.current [id.action u.current u.worker work.action target.action expires.action])
    ==
  ?-  -.applied
    %rejected  [%rejected reason.applied]
    %applied  [%applied db(board next.applied) repo ~]
    %replayed  [%replayed db repo ~]
  ==
++  lookup
  |=  [db=state repo=repo-state env=authority caller=actor viewer=view-policy id=@t number=@ud]
  ^-  (unit view)
  ?.  &((scoped:stead-code-delivery board.db env) =(1 version.db) =(destination.repo destination.env))  ~
  =/  who  (active:stead-code-delivery env caller)
  ?~  who  ~
  ?.  &((uuid:stead-codec id) (gth number 0) (lte number 64))  ~
  =/  key=merge-record  [id number]
  =/  found  (~(get by revisions.board.db) key)
  ?~  found  ~
  =/  item  item.u.found
  ?.  (viewer u.who destination.repo work.item target.location.item)  ~
  =/  review  (~(get by reviews.board.db) key)
  =/  merged=(unit @ud)
    =/  matches  (skim ~(tap by merges.db) |=([request=@t row=merge-record] =(row key)))
    ?.  ?=([* ~] matches)  ~
    =/  accepted  (linked-receipt db repo p.i.matches key)
    ?~  accepted  ~
    [~ revision.u.accepted]
  [~ item ?~(review ~ [~ principal.reviewer.u.review]) merged]
::
::  The saved envelope's caller also validates the whole repository journal
::  and the configured project scope. Historical actors may have since left.
++  valid-actor
  |=  who=actor
  &((lte (met 0 ship.who) 128) (live:stead-session who 0))
++  valid-grant
  |=  [key=@t row=grant:stead-code-delivery]
  ^-  ?
  =/  entry  entry.row
  ?&  =(key id.entry)
      (uuid:stead-codec key)
      (uuid:stead-codec work.entry)
      (branch:stead-code-delivery target.entry)
      (valid-actor sponsor.entry)
      (valid-actor worker.entry)
      !=(principal.sponsor.entry principal.worker.entry)
      (gth expires.entry 0)
      (lte expires.entry expires.sponsor.entry)
      (lte expires.entry expires.worker.entry)
  ==
++  valid-submission
  |=  [db=state key=merge-record row=submission:stead-code-delivery]
  ^-  ?
  =/  item  item.row
  =/  scope  destination.board.db
  ?&  =(id.key id.item)
      =(number.key number.change.item)
      (uuid:stead-codec id.key)
      (uuid:stead-codec work.item)
      (branch:stead-code-delivery target.location.item)
      (valid-proposal:stead-code-review item)
      (valid-actor owner.row)
      =(author.item principal.owner.row)
      =(project.location.item project.scope)
      =(repo.location.item repository.scope)
      =(epoch.change.item epoch.scope)
      (lte number.key (fall (~(get by latest.board.db) id.key) 0))
      (lte number.key 64)
      ?:  =(1 number.key)  &
      =/  prior  (~(get by revisions.board.db) [id.key (dec number.key)])
      ?~  prior  |
      &((same-actor:stead-session owner.row owner.u.prior) =(location.item location.item.u.prior) =(work.item work.item.u.prior))
      ?~  via.row  &
      =/  proof  (~(get by delegates.board.db) u.via.row)
      ?~  proof  |
      &((same-actor:stead-session owner.row worker.entry.u.proof) =(work.item work.entry.u.proof) =(target.location.item target.entry.u.proof))
  ==
++  validate-saved
  |=  [db=state repo=repo-state]
  ^-  ?
  =/  board  board.db
  ?&  =(1 version.db)
      =(1 version.board)
      =(destination.board destination.repo)
      (scope-valid:stead-code-credentials destination.board)
      (lte ~(wyt by delegates.board) 32)
      (lte ~(wyt by revisions.board) 64)
      (lte ~(wyt by latest.board) 64)
      (lte ~(wyt by reviews.board) 64)
      (lte ~(wyt by merges.db) 32)
      =(~(wyt by merges.db) ~(wyt in (silt (turn ~(tap by merges.db) |=([request=@t key=merge-record] key)))))
      (lte ~(wyt by builds.board) 32)
      (lte ~(wyt by releases.board) 32)
      (levy ~(tap by delegates.board) valid-grant)
      (levy ~(tap by revisions.board) |=([key=merge-record row=submission:stead-code-delivery] (valid-submission db key row)))
      (levy ~(tap by latest.board) |=([id=@t number=@ud] (~(has by revisions.board) [id number])))
      %+  levy  ~(tap by reviews.board)
      |=  [key=merge-record review=review:stead-code-delivery]
      =/  row  (~(get by revisions.board) key)
      ?~  row  |
      &((valid-actor reviewer.review) =(principal.reviewer.review reviewer.proof.review) =(item.u.row reviewed.proof.review) !=(author.item.u.row principal.reviewer.review))
      %+  levy  ~(tap by merges.db)
      |=  [request=@t key=merge-record]
      ?=(^ (linked-receipt db repo request key))
  ==
--

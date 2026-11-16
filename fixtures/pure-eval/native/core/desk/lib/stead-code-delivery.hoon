::  Versioned, pure review and build transitions. The Home owns this state.
::  Policy, membership, ref and source gates come from the current authority.
::  The authenticated external runner attests results; no code executes here.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-review, stead-code-git-objects
|%
+$  scope  scope:stead-code-credentials
+$  actor  actor:stead-session
+$  proposal  proposal:stead-code-review
+$  role  ?(%delegate %propose %agent-propose %review %merge %queue-build %run-build %release)
+$  permit  $-([actor scope @t @t role] ?)
+$  inspect  $-([actor proposal] (unit @t))
+$  refs  $-(@t @ux)
+$  attestation  [source=@t recipe=@t output=@t outcome=?(%passed %failed)]
+$  verify-output  $-([scope @t proposal @ud actor attestation] ?)
+$  authority
  $:  destination=scope  now=@ud
      resolve=membership:stead-code-credentials
      allows=permit  source=inspect  tip=refs  recipe=$-([scope @t] ?)
      accepted=$-([scope proposal] ?)  verify=verify-output
  ==
+$  delegation
  [id=@t sponsor=actor worker=actor work=@t target=@t expires=@ud]
+$  grant
  $%  [%granted entry=delegation]
      [%revoked entry=delegation]
  ==
+$  submission  [item=proposal owner=actor via=(unit @t)]
+$  review  [reviewer=actor proof=approval:stead-code-review]
+$  lease  [worker=actor attempt=@ud until=@ud]
+$  build-stage
  $%  [%queued ~]
      [%leased grant=lease]
      [%finished grant=lease evidence=attestation]
      [%cancelled ~]
  ==
+$  build
  [id=@t requester=actor item=proposal source=@t recipe=@t stage=build-stage]
+$  release
  [id=@t owner=actor job=@t item=proposal evidence=attestation]
+$  state
  $:  version=@ud  destination=scope
      delegates=(map @t grant)
      revisions=(map [@t @ud] submission)
      latest=(map @t @ud)
      reviews=(map [@t @ud] review)
      builds=(map @t build)
      releases=(map @t release)
  ==
+$  result
  $%  [%applied next=state]
      [%replayed next=state]
      [%rejected reason=@tas]
  ==
::
++  empty
  |=  destination=scope
  ^-  state
  [1 destination ~ ~ ~ ~ ~ ~]
++  scoped
  |=  [db=state env=authority]
  ^-  ?
  ?&  (scope-valid:stead-code-credentials destination.env)
      =(1 version.db)
      =(destination.db destination.env)
  ==
++  active
  |=  [env=authority who=actor]
  ^-  (unit actor)
  =/  current  (resolve.env ship.who)
  ?~  current  ~
  ?.  &((live:stead-session u.current now.env) (same-actor:stead-session who u.current))  ~
  current
++  allowed
  |=  [env=authority who=actor work=@t target=@t capability=role]
  ^-  ?
  =/  current  (active env who)
  ?~  current  |
  (allows.env u.current destination.env work target capability)
++  branch
  |=  value=@t
  ^-  ?
  ?&  (lte (met 3 value) 128)
      =('refs/heads/' (cut 3 [0 11] value))
      (valid-ref:stead-code-git-objects [(met 3 value) value])
  ==
++  grant-valid
  |=  [env=authority entry=delegation]
  ^-  ?
  ?&  (uuid:stead-codec id.entry)
      (uuid:stead-codec work.entry)
      (branch target.entry)
      !=(principal.sponsor.entry principal.worker.entry)
      (gth expires.entry now.env)
      (lte expires.entry (add now.env 86.400.000))
      (lte expires.entry expires.sponsor.entry)
      (lte expires.entry expires.worker.entry)
      (allowed env sponsor.entry work.entry target.entry %delegate)
      (allowed env worker.entry work.entry target.entry %agent-propose)
  ==
++  delegate
  |=  [db=state env=authority caller=actor entry=delegation]
  ^-  result
  ?.  ?&  (scoped db env)
          (same-actor:stead-session caller sponsor.entry)
          (grant-valid env entry)
      ==
    [%rejected %denied]
  =/  prior  (~(get by delegates.db) id.entry)
  ?^  prior
    ?:  =([%granted entry] u.prior)  [%replayed db]
    [%rejected %id-conflict]
  ?:  (gte ~(wyt by delegates.db) 32)  [%rejected %capacity]
  [%applied db(delegates (~(put by delegates.db) id.entry [%granted entry]))]
++  revoke
  |=  [db=state env=authority caller=actor id=@t]
  ^-  result
  ?.  &((scoped db env) (uuid:stead-codec id))  [%rejected %denied]
  =/  prior  (~(get by delegates.db) id)
  ?~  prior  [%rejected %denied]
  =/  row  entry.u.prior
  ?.  &((same-actor:stead-session sponsor.row caller) (allowed env caller work.row target.row %delegate))
    [%rejected %denied]
  ?:  ?=(%revoked -.u.prior)  [%replayed db]
  [%applied db(delegates (~(put by delegates.db) id [%revoked row]))]
++  eligible
  |=  [db=state env=authority row=submission]
  ^-  ?
  =/  item  item.row
  ?&  (scoped db env)
      (valid-proposal:stead-code-review item)
      (uuid:stead-codec id.item)
      (uuid:stead-codec work.item)
      (branch target.location.item)
      =(author.item principal.owner.row)
      =(project.location.item project.destination.env)
      =(repo.location.item repository.destination.env)
      =(epoch.change.item epoch.destination.env)
      (lte number.change.item 64)
      ?:  ?=(~ via.row)
        (allowed env owner.row work.item target.location.item %propose)
      ?.  (uuid:stead-codec u.via.row)  |
      =/  linked  (~(get by delegates.db) u.via.row)
      ?~  linked  |
      ?.  ?=(%granted -.u.linked)  |
      =/  proof  entry.u.linked
      ?&  (same-actor:stead-session worker.proof owner.row)
          =(work.proof work.item)
          =(target.proof target.location.item)
          (grant-valid env proof)
      ==
  ==
++  submit
  |=  [db=state env=authority caller=actor item=proposal via=(unit @t)]
  ^-  result
  =/  row=submission  [item caller via]
  ?.  (eligible db env row)  [%rejected %denied]
  =/  pin  (source.env caller item)
  ?~  pin  [%rejected %unavailable]
  ?.  (token-valid:stead-session u.pin)  [%rejected %unavailable]
  =/  key  [id.item number.change.item]
  =/  previous  (~(get by revisions.db) key)
  ?^  previous
    ?:  ?&  (same-actor:stead-session owner.u.previous caller)
            =(item.u.previous item)
            =(via.u.previous via)
        ==
      [%replayed db]
    [%rejected %id-conflict]
  =/  newest  (~(get by latest.db) id.item)
  =/  number  (fall newest 0)
  ?.  =(number.change.item +(number))  [%rejected %stale-revision]
  ?.  =(base.change.item (tip.env target.location.item))  [%rejected %stale-target]
  =/  owns=?
    ?~  newest  &
    =/  prior  (~(get by revisions.db) [id.item u.newest])
    ?~  prior  |
    ?&  (same-actor:stead-session owner.u.prior caller)
        =(location.item location.item.u.prior)
        =(work.item work.item.u.prior)
    ==
  ?.  owns  [%rejected %denied]
  ?:  (gte ~(wyt by revisions.db) 64)  [%rejected %capacity]
  [%applied db(revisions (~(put by revisions.db) key row), latest (~(put by latest.db) id.item number.change.item))]
++  current
  |=  [db=state env=authority id=@t number=@ud]
  ^-  (unit submission)
  ?.  &((scoped db env) (uuid:stead-codec id) =((~(get by latest.db) id) [~ number]))  ~
  =/  found  (~(get by revisions.db) [id number])
  ?~  found  ~
  ?.  (eligible db env u.found)  ~
  found
++  approve
  |=  [db=state env=authority caller=actor id=@t number=@ud]
  ^-  result
  =/  found  (current db env id number)
  ?~  found  [%rejected %denied]
  =/  item  item.u.found
  ?.  (allowed env caller work.item target.location.item %review)  [%rejected %denied]
  =/  review-permit=permission:stead-code-review
    |=  [principal=@t at=scope:stead-code-review]
    &(=(principal principal.caller) =(at location.item))
  =/  checked  (approve:stead-code-review item epoch.destination.env principal.caller review-permit)
  ?:  ?=(%| -.checked)  [%rejected p.checked]
  =/  prior  (~(get by reviews.db) [id number])
  ?^  prior
    ?:  &((same-actor:stead-session reviewer.u.prior caller) =(proof.u.prior p.checked))  [%replayed db]
    [%rejected %already-reviewed]
  ?:  (gte ~(wyt by reviews.db) 64)  [%rejected %capacity]
  [%applied db(reviews (~(put by reviews.db) [id number] [caller p.checked]))]
++  merge-candidate
  |=  [db=state env=authority caller=actor id=@t number=@ud]
  ^-  merge-result:stead-code-review
  =/  found  (current db env id number)
  ?~  found  [%| %denied]
  =/  item  item.u.found
  ?.  (allowed env caller work.item target.location.item %merge)  [%| %denied]
  =/  stored  (~(get by reviews.db) [id number])
  ?~  stored  [%| %review-required]
  =/  reviewer  reviewer.u.stored
  ?.  (allowed env reviewer work.item target.location.item %review)  [%| %review-denied]
  =/  review-permit=permission:stead-code-review
    |=  [person=@t at=scope:stead-code-review]
    &(=(person principal.reviewer) =(at location.item))
  =/  merge-permit=permission:stead-code-review
    |=  [person=@t at=scope:stead-code-review]
    &(=(person principal.caller) =(at location.item))
  (check-merge:stead-code-review item proof.u.stored epoch.destination.env (tip.env target.location.item) principal.caller review-permit merge-permit)
::
::  The exact immutable source is resolved through the authority's object view.
++  queue
  |=  [db=state env=authority caller=actor id=@t proposal-id=@t number=@ud recipe=@t]
  ^-  result
  ?.  &((uuid:stead-codec id) (token-valid:stead-session recipe))  [%rejected %invalid-input]
  =/  found  (current db env proposal-id number)
  ?~  found  [%rejected %denied]
  =/  item  item.u.found
  ?.  (allowed env caller work.item target.location.item %queue-build)  [%rejected %denied]
  ?.  (recipe.env destination.env recipe)  [%rejected %recipe-denied]
  =/  pinned  (source.env caller item)
  ?~  pinned  [%rejected %unavailable]
  ?.  (token-valid:stead-session u.pinned)  [%rejected %unavailable]
  =/  prior  (~(get by builds.db) id)
  ?^  prior
    ?:  ?&  (same-actor:stead-session requester.u.prior caller)
            =(item item.u.prior)
            =(recipe recipe.u.prior)
            =(u.pinned source.u.prior)
        ==
      [%replayed db]
    [%rejected %id-conflict]
  ?:  (gte ~(wyt by builds.db) 32)  [%rejected %capacity]
  =/  row=build  [id caller item u.pinned recipe %queued ~]
  [%applied db(builds (~(put by builds.db) id row))]
++  job-authorized
  |=  [db=state env=authority row=build]
  ^-  ?
  =/  item  item.row
  =/  prior  (~(get by revisions.db) [id.item number.change.item])
  ?~  prior  |
  ?&  (eligible db env u.prior)
      =(item item.u.prior)
      (allowed env requester.row work.item target.location.item %queue-build)
      (recipe.env destination.env recipe.row)
  ==
::  Check these mutable inputs only when advancing a job or creating a release.
++  job-fresh
  |=  [db=state env=authority row=build]
  ^-  ?
  =/  item  item.row
  ?&  =((~(get by latest.db) id.item) [~ number.change.item])
      =([~ source.row] (source.env requester.row item))
  ==
++  worker-allowed
  |=  [env=authority caller=actor row=build]
  ^-  ?
  ?&  !=(principal.caller principal.requester.row)
      !=(principal.caller author.item.row)
      (allowed env caller work.item.row target.location.item.row %run-build)
  ==
++  claim
  |=  [db=state env=authority caller=actor id=@t expected=@ud]
  ^-  result
  ?.  &((scoped db env) (uuid:stead-codec id))  [%rejected %denied]
  =/  prior  (~(get by builds.db) id)
  ?~  prior  [%rejected %denied]
  =/  row  u.prior
  ?.  &((worker-allowed env caller row) (job-authorized db env row) (job-fresh db env row))
    [%rejected %denied]
  =/  stage  stage.row
  ?:  ?=(?(%finished %cancelled) -.stage)  [%rejected %terminal]
  =/  count  ?:  ?=(%leased -.stage)  attempt.grant.stage  0
  ?:  &(?=(%leased -.stage) (gth until.grant.stage now.env))
    ?:  &((same-actor:stead-session worker.grant.stage caller) =(expected (dec count)))
      [%replayed db]
    [%rejected %leased]
  ?.  =(expected count)  [%rejected %stale-attempt]
  ?:  (gte count 3)  [%rejected %attempt-limit]
  =/  current-worker  (need (active env caller))
  =/  next=build-stage
    [%leased current-worker +(count) (min expires.current-worker (add now.env 120.000))]
  [%applied db(builds (~(put by builds.db) id row(stage next)))]
++  finish
  |=  [db=state env=authority caller=actor id=@t attempt=@ud evidence=attestation]
  ^-  result
  ?.  &((scoped db env) (uuid:stead-codec id) (token-valid:stead-session output.evidence))  [%rejected %denied]
  =/  prior  (~(get by builds.db) id)
  ?~  prior  [%rejected %denied]
  =/  row  u.prior
  ?.  &((worker-allowed env caller row) (job-authorized db env row))  [%rejected %denied]
  ?.  &(=(source.evidence source.row) =(recipe.evidence recipe.row))  [%rejected %wrong-input]
  =/  stage  stage.row
  ?:  ?=(%finished -.stage)
    ?:  ?&  (same-actor:stead-session worker.grant.stage caller)
            =(attempt attempt.grant.stage)
            =(evidence evidence.stage)
            (verify.env destination.env id item.row attempt worker.grant.stage evidence)
        ==
      [%replayed db]
    [%rejected %id-conflict]
  ?.  (job-fresh db env row)  [%rejected %denied]
  ?.  ?=(%leased -.stage)  [%rejected %not-leased]
  ?.  ?&  (same-actor:stead-session worker.grant.stage caller)
          =(attempt attempt.grant.stage)
          (gth until.grant.stage now.env)
      ==
    [%rejected %stale-lease]
  ?.  (verify.env destination.env id item.row attempt worker.grant.stage evidence)
    [%rejected %artifact-unverified]
  =/  next=build-stage  [%finished grant.stage evidence]
  [%applied db(builds (~(put by builds.db) id row(stage next)))]
++  cancel
  |=  [db=state env=authority caller=actor id=@t]
  ^-  result
  ?.  &((scoped db env) (uuid:stead-codec id))  [%rejected %denied]
  =/  prior  (~(get by builds.db) id)
  ?~  prior  [%rejected %denied]
  =/  row  u.prior
  ?.  &((same-actor:stead-session requester.row caller) (allowed env caller work.item.row target.location.item.row %queue-build))
    [%rejected %denied]
  ?:  ?=(%finished -.stage.row)  [%rejected %terminal]
  ?:  ?=(%cancelled -.stage.row)  [%replayed db]
  [%applied db(builds (~(put by builds.db) id row(stage [%cancelled ~])))]
::
::  Record authorization for one reviewed, already accepted ref and build.
::  This transition never dispatches a deployment or any external effect.
++  release-intent
  |=  [db=state env=authority caller=actor id=@t job=@t]
  ^-  result
  ?.  &((scoped db env) (uuid:stead-codec id) (uuid:stead-codec job))  [%rejected %denied]
  =/  found  (~(get by builds.db) job)
  ?~  found  [%rejected %denied]
  =/  row  u.found
  =/  item  item.row
  ?.  &((job-authorized db env row) (allowed env caller work.item target.location.item %release))
    [%rejected %denied]
  ?.  ?=(%finished -.stage.row)  [%rejected %build-required]
  ?.  =(%passed outcome.evidence.stage.row)  [%rejected %build-required]
  =/  builder  worker.grant.stage.row
  ?.  ?&  (worker-allowed env builder row)
          !=(principal.caller principal.builder)
          !=(principal.caller author.item)
          !=(principal.caller principal.requester.row)
      ==
    [%rejected %denied]
  ?.  (verify.env destination.env job item attempt.grant.stage.row builder evidence.stage.row)
    [%rejected %artifact-unverified]
  =/  prior  (~(get by reviews.db) [id.item number.change.item])
  ?~  prior  [%rejected %review-required]
  ?.  ?&  (allowed env reviewer.u.prior work.item target.location.item %review)
          =(reviewed.proof.u.prior item)
          =(reviewer.proof.u.prior principal.reviewer.u.prior)
          !=(principal.reviewer.u.prior author.item)
      ==
    [%rejected %review-denied]
  =/  record=release  [id caller job item evidence.stage.row]
  =/  prior  (~(get by releases.db) id)
  ?^  prior
    ?:  ?&  (same-actor:stead-session owner.u.prior caller)
            =(job.u.prior job)
            =(item.u.prior item)
            =(evidence.u.prior evidence.record)
        ==
      [%replayed db]
    [%rejected %id-conflict]
  ?.  (job-fresh db env row)  [%rejected %denied]
  ?.  =(head.change.item (tip.env target.location.item))  [%rejected %unaccepted-head]
  ?.  (accepted.env destination.env item)  [%rejected %acceptance-required]
  ?:  (gte ~(wyt by releases.db) 32)  [%rejected %capacity]
  ?:  (lien ~(tap by releases.db) |=([key=@t entry=release] =(job.entry job)))
    [%rejected %already-released]
  [%applied db(releases (~(put by releases.db) id record))]
--

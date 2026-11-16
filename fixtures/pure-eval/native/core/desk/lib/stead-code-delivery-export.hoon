::  Bounded read-only audit projection. The Home authorizes every page.
::  Credential, upload and binding state is outside this view.
/+  stead-codec, stead-git, stead-session, stead-code-credentials, stead-code-store, stead-code-review-home, stead-code-delivery, stead-code-review, stead-code-build-home
=,  stead-codec
|%
+$  result-page
  [snapshot=@t total=@ud next=(unit @ud) header=@t records=@t]
+$  fields  (list [@t @t])
+$  audit-input
  $:  repo=state:stead-code-store  board=state:stead-code-review-home
      extras=state:stead-code-build-home  protected=(set @t)
  ==
++  protocol
  'stead.code-delivery-audit/1'
++  encode
  |=  pairs=fields
  ^-  @t
  (canonical (object pairs))
++  json-lines
  |=  rows=(list @t)
  ^-  @t
  (rap 3 (zing (turn rows |=(row=@t ~[row 10]))))
++  proposal-key
  |=  item=proposal:stead-code-review
  ^-  fields
  ~[['proposal_id' id.item] ['revision' (decimal number.change.item)]]
++  proposal-row
  |=  row=submission:stead-code-delivery
  ^-  @t
  =/  item  item.row
  %-  encode
  :*  ['kind' 'proposal']
      ['author' author.item]  ['work_id' work.item]
      ['ref_hex' (bytes-hex target.location.item)]
      ['base_oid' (oid-text:stead-git base.change.item)]
      ['head_oid' (oid-text:stead-git head.change.item)]
      ['delegation_id' (fall via.row '')]
      (proposal-key item)
  ==
++  approval-row
  |=  row=review:stead-code-delivery
  ^-  @t
  (encode [['kind' 'approval'] ['reviewer' principal.reviewer.row] (proposal-key reviewed.proof.row)])
++  receipt-rows
  |=  [repo=state:stead-code-store board=state:stead-code-review-home request=@t]
  ^-  (list @t)
  =/  row  (~(got by receipts.repo) request)
  =/  merged  (~(get by merges.board) request)
  =/  header=@t
    %-  encode
    :~  ['kind' 'ref_receipt']  ['request_id' request]
        ['repository_revision' (decimal revision.row)]
        ['actor' principal.owner.row]  ['digest' digest.row]
        ['changes' (decimal (lent changes.row))]
        ['proposal_id' ?~(merged '' id.u.merged)]
        ['proposal_revision' ?~(merged '' (decimal number.u.merged))]
    ==
  =/  pending  changes.row
  =/  index=@ud  0
  =/  out=(list @t)  ~[header]
  |-  ^-  (list @t)
  ?~  pending  (flop out)
  =/  item  i.pending
  =/  record=@t
    %-  encode
    :~  ['kind' 'ref_change']  ['request_id' request]  ['index' (decimal index)]
        ['ref_hex' (bytes-hex name.item)]
        ['prior_oid' (oid-text:stead-git prior.item)]
        ['target_oid' (oid-text:stead-git target.item)]
    ==
  $(pending t.pending, index +(index), out [record out])
++  build-row
  |=  [extras=state:stead-code-build-home job=build:stead-code-delivery]
  ^-  @t
  =/  phase  stage.job
  =/  lease  (lease-of:stead-code-build-home phase)
  =/  assigned  (~(get by workers.extras) id.job)
  =/  artifact  (~(get by artifacts.extras) id.job)
  %-  encode
  :*  ['kind' 'build']  ['job_id' id.job]
      ['requester' principal.requester.job]
      ['source' source.job]  ['recipe' recipe.job]  ['stage' -.phase]
      ['assigned_worker' ?~(assigned '' principal.u.assigned)]
      ['lease_worker' ?~(lease '' principal.worker.u.lease)]
      ['attempt' ?~(lease '' (decimal attempt.u.lease))]
      ['lease_expires_ms' ?~(lease '' (decimal until.u.lease))]
      ['output_sha256' ?:(?=(%finished -.phase) output.evidence.phase '')]
      ['outcome' ?:(?=(%finished -.phase) outcome.evidence.phase '')]
      ['artifact_base64' ?~(artifact '' (en:base64:mimes:html u.artifact))]
      (proposal-key item.job)
  ==
++  release-row
  |=  row=release:stead-code-delivery
  ^-  @t
  %-  encode
  :*  ['kind' 'release']  ['release_id' id.row]  ['job_id' job.row]
      ['actor' principal.owner.row]  ['source' source.evidence.row]
      ['recipe' recipe.evidence.row]  ['output_sha256' output.evidence.row]
      ['outcome' outcome.evidence.row]
      (proposal-key item.row)
  ==
++  delegation-row
  |=  row=grant:stead-code-delivery
  ^-  @t
  =/  item  entry.row
  %-  encode
  :~  ['kind' 'delegation']  ['delegation_id' id.item]  ['stage' -.row]
      ['work_id' work.item]  ['ref_hex' (bytes-hex target.item)]
      ['sponsor' principal.sponsor.item]  ['worker' principal.worker.item]
      ['expires_at_ms' (decimal expires.item)]
  ==
++  bounded
  |=  input=audit-input
  ^-  ?
  =/  repo  repo.input
  =/  board  board.board.input
  ?&  =(1 version.repo)
      =(1 version.board.input)
      =(1 version.board)
      =(destination.repo destination.board)
      (scope-valid:stead-code-credentials destination.repo)
      (lte ~(wyt by refs.repo) 16)
      (lte ~(wyt in protected.input) 16)
      (lte ~(wyt by revisions.board) 64)
      (lte ~(wyt by reviews.board) 64)
      (lte ~(wyt by builds.board) 32)
      (lte ~(wyt by releases.board) 32)
      (lte ~(wyt by delegates.board) 32)
      (lte ~(wyt by merges.board.input) 32)
      (lte ~(wyt by workers.extras.input) 32)
      (lte ~(wyt by artifacts.extras.input) 32)
      %+  levy  ~(tap by artifacts.extras.input)
      |=  [id=@t bytes=octets:stead-git]
      =/  job  (~(get by builds.board) id)
      ?~  job  |
      ?.  ?=(%finished -.stage.u.job)  |
      &((valid-artifact:stead-code-build-home bytes) =(output.evidence.stage.u.job (digest:stead-code-build-home bytes)))
      (lte (lent (scag 33 journal.repo)) 32)
      =(revision.repo ~(wyt by receipts.repo))
      =(revision.repo (lent journal.repo))
      =(revision.repo ~(wyt in (silt journal.repo)))
      (levy journal.repo |=(id=@t (~(has by receipts.repo) id)))
      (levy ~(tap by receipts.repo) |=([id=@t row=receipt:stead-code-store] (lte (lent (scag 9 changes.row)) 8)))
  ==
++  records
  |=  input=audit-input
  ^-  (list @t)
  =/  repo  repo.input
  =/  review  board.input
  =/  board  board.review
  =/  refs=(list @t)
    (turn ~(tap by refs.repo) |=([ref=@t oid=@ux] (encode ~[['kind' 'ref'] ['ref_hex' (bytes-hex ref)] ['oid' (oid-text:stead-git oid)]])))
  =/  protections=(list @t)
    (turn ~(tap in protected.input) |=(ref=@t (encode ~[['kind' 'protection'] ['ref_hex' (bytes-hex ref)]])))
  =/  proposals=(list @t)
    (turn ~(tap by revisions.board) |=([key=merge-record:stead-code-review-home row=submission:stead-code-delivery] (proposal-row row)))
  =/  approvals=(list @t)
    (turn ~(tap by reviews.board) |=([key=merge-record:stead-code-review-home row=review:stead-code-delivery] (approval-row row)))
  =/  transactions=(list @t)
    (zing (turn (flop journal.repo) |=(id=@t (receipt-rows repo review id))))
  =/  jobs=(list @t)
    (turn ~(tap by builds.board) |=([id=@t row=build:stead-code-delivery] (build-row extras.input row)))
  =/  releases=(list @t)
    (turn ~(tap by releases.board) |=([id=@t row=release:stead-code-delivery] (release-row row)))
  =/  delegations=(list @t)
    (turn ~(tap by delegates.board) |=([id=@t row=grant:stead-code-delivery] (delegation-row row)))
  (zing ~[refs protections proposals approvals transactions jobs releases delegations])
++  page
  |=  [repo=state:stead-code-store board=state:stead-code-review-home extras=state:stead-code-build-home protected=(set @t) offset=@ud expected=@t]
  ^-  (each result-page @tas)
  ?.  &((lte offset 544) =(0 (mod offset 4)) ?:(=('' expected) =(0 offset) (token-valid:stead-session expected)))
    [%| %invalid-cursor]
  =/  input=audit-input  [repo board extras protected]
  ?.  (bounded input)  [%| %audit-bounds]
  =/  rows  (records input)
  =/  total  (lent rows)
  ?.  &((lte total 544) (levy rows |=(row=@t (lte (met 3 row) 12.288))))  [%| %audit-bounds]
  =/  body  (json-lines rows)
  ?.  (lte (met 3 body) 786.432)  [%| %audit-bounds]
  =/  scope  destination.repo
  =/  header=@t
    %-  encode
    :~  ['protocol' protocol]  ['home' (scot %p home.scope)]
        ['project_id' project.scope]  ['repository_id' repository.scope]
        ['epoch' (decimal epoch.scope)]  ['repository_revision' (decimal revision.repo)]
        ['records' (decimal total)]
    ==
  =/  snapshot  (hash protocol (rap 3 ~[header 10 body]))
  ?.  |(=('' expected) =(snapshot expected))  [%| %snapshot-changed]
  ?.  |((lth offset total) &(=(0 total) =(0 offset)))  [%| %invalid-cursor]
  =/  after  (add offset 4)
  [%& snapshot total ?:((lth after total) [~ after] ~) header (json-lines (scag 4 (slag offset rows)))]
--

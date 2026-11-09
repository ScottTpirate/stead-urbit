::  Exact build leases for individually assigned workers. The Home verifies
::  artifact bytes and records evidence. Repository code runs only off Home.
/+  stead-codec, stead-team, stead-session, stead-git, stead-code-credentials, stead-code-review, stead-code-delivery, stead-code-review-home, stead-code-review-api, stead-code-store, stead-code-git-graph
=,  stead-codec
|%
+$  state
  [workers=(map @t actor:stead-session) artifacts=(map @t octets:stead-git)]
+$  manifest-entry  [path=@t mode=tree-mode:stead-code-git-graph oid=@ux]
+$  answer
  $%  [%read rows=(list [@t @t])]
      [%accepted next=state board=state:stead-code-review-home rows=(list [@t @t])]
      [%failed status=@ud reason=@t]
  ==
++  recipe
  '9dfe50f0b7df0c270bff4c06a67251eac3e94476c034e4e3d0209fa8aa96fc6e'
++  operation
  |=  op=@t
  =('build-' (cut 3 [0 6] op))
++  digest
  |=  bytes=octets:stead-git
  ^-  @t
  (hex 64 (sha-256l:sha [length.bytes (rev 3 length.bytes data.bytes)]))
++  valid-artifact
  |=  bytes=octets:stead-git
  &((gth length.bytes 0) (lte length.bytes 8.192) (valid-octets:stead-git bytes))
++  files
  |=  [repo=state:stead-code-store root=@ux]
  ^-  (unit @t)
  =/  pending=(list manifest-entry)  ~[['' %directory root]]
  =/  fuel=@ud  128
  =/  budget=@ud  262.144
  =/  output=@t  ''
  =/  hashes=(map @ux @t)  ~
  |-
  ?~  pending  [~ output]
  ?:  =(0 fuel)  ~
  =/  entry  i.pending
  =/  found  (~(get by objects.repo) oid.entry)
  ?~  found  ~
  ?:  ?=(%directory mode.entry)
    =/  facts  (inspect:stead-code-git-graph u.found)
    ?.  ?=([%& %tree *] facts)  ~
    =/  children=(list manifest-entry)
      %+  turn  entries.p.facts
      |=  child=tree-entry:stead-code-git-graph
      =/  path  ?:(=('' path.entry) name.child (rap 3 ~[path.entry '/' name.child]))
      [path mode.child oid.child.child]
    ?.  (lte (lent (scag 129 (weld children t.pending))) 128)  ~
    $(pending (weld children t.pending), fuel (dec fuel))
  ?.  ?&  =(%blob kind.u.found)
          (lte (met 3 path.entry) 512)
          (sune:de:json:html path.entry)
      ==
    ~
  =/  prior  (~(get by hashes) oid.entry)
  ?.  |(?=(^ prior) (lte length.body.u.found budget))  ~
  =/  hash  ?~(prior (digest body.u.found) u.prior)
  =?  budget  ?=(~ prior)  (sub budget length.body.u.found)
  =?  hashes  ?=(~ prior)  (~(put by hashes) oid.entry hash)
  =/  row=@t
    %-  rap
    :*  3
        :~  '{"bytes":'  (decimal length.body.u.found)
            ',"mode":"'  ?:(=(%file mode.entry) '100644' '100755')
            '","oid":"'  (oid-text:stead-git oid.entry)
            '","path":'  (quote path.entry)
            ',"sha256":"'  hash  '"}'
        ==
    ==
  =/  next  ?:(=('' output) row (rap 3 ~[output ',' row]))
  ?:  (gth (met 3 next) 8.192)  ~
  $(pending t.pending, fuel (dec fuel), output next)
++  matches-manifest
  |=  [repo=state:stead-code-store commit=@ux bytes=octets:stead-git]
  ^-  ?
  =/  found  (~(get by objects.repo) commit)
  ?~  found  |
  =/  facts  (inspect:stead-code-git-graph u.found)
  ?.  ?=([%& %commit *] facts)  |
  =/  tree  oid.root.p.facts
  =/  rows  (files repo tree)
  ?~  rows  |
  =/  expected
    %-  rap
    :*  3
        :~  '{"commit":"'  (oid-text:stead-git commit)
            '","files":['  u.rows
            '],"object_format":"sha1","protocol":"stead.build.git-tree-manifest/1","tree":"'
            (oid-text:stead-git tree)  '"}'  10
        ==
    ==
  =([(met 3 expected) expected] bytes)
++  merged
  |=  [board=state:stead-code-review-home repo=state:stead-code-store item=proposal:stead-code-review]
  ^-  ?
  %+  lien  ~(tap by merges.board)
  |=  [id=@t row=merge-record:stead-code-review-home]
  ?.  =(row [id.item number.change.item])  |
  ?=(^ (linked-receipt:stead-code-review-home board repo id row))
++  lease-of
  |=  stage=build-stage:stead-code-delivery
  ^-  (unit lease:stead-code-delivery)
  ?:  ?=(%leased -.stage)  [~ grant.stage]
  ?:  ?=(%finished -.stage)  [~ grant.stage]
  ~
++  rows
  |=  job=build:stead-code-delivery
  ^-  (list [@t @t])
  =/  stage  stage.job
  =/  lease  (lease-of stage)
  :~  ['status' -.stage]
      ['job_id' id.job]  ['proposal_id' id.item.job]
      ['proposal_revision' (decimal number.change.item.job)]
      ['commit' (oid-text:stead-git head.change.item.job)]
      ['source' source.job]  ['recipe' recipe.job]
      ['attempt' ?~(lease '0' (decimal attempt.u.lease))]
      ['lease_expires_ms' ?~(lease '0' (decimal until.u.lease))]
      ['output' ?:(?=(%finished -.stage) output.evidence.stage '')]
      ['outcome' ?:(?=(%finished -.stage) outcome.evidence.stage '')]
  ==
++  run
  |=  $:  team=state:stead-team  board=state:stead-code-review-home
          extras=state  repo=state:stead-code-store  who=actor:stead-session
          now=@ud  resolve=membership:stead-code-credentials  fields=object-map
          base=(list @t)  op=@t
      ==
  ^-  answer
  =/  scope  destination.repo
  =/  id  (field fields 'job_id')
  ?.  (uuid id)  [%failed 400 'invalid_request']
  =/  prior  (~(get by builds.board.board) id)
  =/  assigned=(unit actor:stead-session)  (~(get by workers.extras) id)
  =/  worker=(unit actor:stead-session)
    ?.  =('build-queue' op)  assigned
    =/  ship  (slaw %p (field fields 'worker_ship'))
    ?~  ship  ~
    ?.  =((scot %p u.ship) (field fields 'worker_ship'))  ~
    (resolve u.ship)
  ?~  worker  [%failed 404 'denied_or_not_found']
  ?.  ?~(assigned ?=(~ prior) (same-actor:stead-session u.worker u.assigned))
    [%failed 409 'job_identity_conflict']
  ?.  ?~  prior  =('build-queue' op)
      =/  rank  (current-work:stead-code-review-api team who scope work.item.u.prior now)
      |(=(3 rank) &((gte rank 1) (same-actor:stead-session who u.worker)))
    [%failed 404 'denied_or_not_found']
  =/  raw=(unit octets:stead-git)
    ?.  =('build-finish' op)  (~(get by artifacts.extras) id)
    =/  encoded  (field fields 'artifact_base64')
    =/  bytes  (de:base64:mimes:html encoded)
    ?~  bytes  ~
    ?.  &((valid-artifact u.bytes) =(encoded (en:base64:mimes:html u.bytes)))  ~
    bytes
  =/  permits=permit:stead-code-delivery
    |=  [actor=actor:stead-session target=scope:stead-code-credentials work=@t ref=@t action=role:stead-code-delivery]
    ?.  =(scope target)  |
    =/  rank  (current-work:stead-code-review-api team actor target work now)
    ?+  action  |
      %agent-propose  (gte rank 1)
      %propose  (gte rank 2)
      %delegate  =(3 rank)
      %review  =(3 rank)
      %queue-build  =(3 rank)
      %release  =(3 rank)
      %run-build  &((gte rank 1) (same-actor:stead-session actor u.worker))
    ==
  =/  view=refs:stead-code-delivery
    |=(target=@t (fall (~(get by refs.repo) target) 0x0))
  =/  env=authority:stead-code-delivery
    :*  scope  now  resolve  permits  (source:stead-code-review-home repo)  view
        |=([target=scope:stead-code-credentials chosen=@t] &(=(target scope) =(chosen recipe)))
        |=([target=scope:stead-code-credentials item=proposal:stead-code-review] &(=(target scope) (merged board repo item)))
        |=  [target=scope:stead-code-credentials job=@t item=proposal:stead-code-review attempt=@ud runner=actor:stead-session evidence=attestation:stead-code-delivery]
        ?~  raw  |
        ?&  =(target scope)  =(job id)
            (same-actor:stead-session runner u.worker)
            =(output.evidence (digest u.raw))
            ?:  =(%passed outcome.evidence)  (matches-manifest repo head.change.item u.raw)
            &
        ==
    ==
  ?:  =('build-job' op)
    ?.  (keys fields ['job_id' base])  [%failed 400 'invalid_request']
    ?~  prior  [%failed 404 'denied_or_not_found']
    =/  rank  (current-work:stead-code-review-api team who scope work.item.u.prior now)
    ?.  |(=(3 rank) &((gte rank 1) (same-actor:stead-session who u.worker)))
      [%failed 404 'denied_or_not_found']
    [%read (rows u.prior)]
  =/  change=result:stead-code-delivery
    ?:  =('build-queue' op)
      ?.  (keys fields ['job_id' 'proposal_id' 'revision' 'recipe' 'worker_ship' base])  [%rejected %invalid-input]
      =/  item-id  (field fields 'proposal_id')
      =/  number  (uint (field fields 'revision'))
      =/  candidate  (~(get by revisions.board.board) [item-id number])
      ?~  candidate  [%rejected %denied]
      ?.  (permits u.worker scope work.item.u.candidate target.location.item.u.candidate %run-build)
        [%rejected %denied]
      ?:  |(=(principal.u.worker principal.who) =(principal.u.worker author.item.u.candidate))
        [%rejected %denied]
      (queue:stead-code-delivery board.board env who id item-id number (field fields 'recipe'))
    ?:  =('build-claim' op)
      ?.  (keys fields ['job_id' 'expected_attempt' base])  [%rejected %invalid-input]
      (claim:stead-code-delivery board.board env who id (uint (field fields 'expected_attempt')))
    ?:  =('build-finish' op)
      ?.  (keys fields ['job_id' 'attempt' 'source' 'recipe' 'output' 'outcome' 'artifact_base64' base])  [%rejected %invalid-input]
      ?~  raw  [%rejected %artifact-unverified]
      =/  outcome  (field fields 'outcome')
      ?.  |(=('passed' outcome) =('failed' outcome))  [%rejected %invalid-input]
      =/  proof=attestation:stead-code-delivery
        [(field fields 'source') (field fields 'recipe') (field fields 'output') ?:(=('passed' outcome) %passed %failed)]
      (finish:stead-code-delivery board.board env who id (uint (field fields 'attempt')) proof)
    ?:  =('build-cancel' op)
      ?.  (keys fields ['job_id' base])  [%rejected %invalid-input]
      (cancel:stead-code-delivery board.board env who id)
    ?:  =('build-release' op)
      ?.  (keys fields ['job_id' 'request_id' base])  [%rejected %invalid-input]
      (release-intent:stead-code-delivery board.board env who (field fields 'request_id') id)
    [%rejected %invalid-input]
  ?:  ?=(%rejected -.change)  [%failed 409 reason.change]
  =/  job  (~(get by builds.next.change) id)
  ?~  job  [%failed 409 'job_unavailable']
  =?  extras  &(?=(%applied -.change) =('build-queue' op))
    extras(workers (~(put by workers.extras) id u.worker))
  =?  extras  &(?=(%applied -.change) =('build-finish' op) ?=(^ raw))
    extras(artifacts (~(put by artifacts.extras) id u.raw))
  =/  reply=(list [@t @t])
    [['transition' ?:(?=(%replayed -.change) 'replayed' 'accepted')] (rows u.job)]
  [%accepted extras board(board next.change) reply]
++  validate-saved
  |=  [board=state:stead-code-review-home extras=state repo=state:stead-code-store]
  ^-  ?
  =/  delivery  board.board
  ?.  ?&  (lte ~(wyt by builds.delivery) 32)
          (lte ~(wyt by releases.delivery) 32)
          =(~(wyt by workers.extras) ~(wyt by builds.delivery))
          (lte ~(wyt by artifacts.extras) 32)
      ==
    |
  ?.  %+  levy  ~(tap by builds.delivery)
      |=  [id=@t job=build:stead-code-delivery]
      =/  worker  (~(get by workers.extras) id)
      ?~  worker  |
      =/  item  item.job
      =/  record  (~(get by revisions.delivery) [id.item number.change.item])
      ?~  record  |
      ?.  ?&  (uuid id)  =(id id.job)  =(item item.u.record)  =(recipe recipe.job)
              (valid-actor:stead-code-review-home requester.job)
              (valid-actor:stead-code-review-home u.worker)
              !=(principal.u.worker principal.requester.job)
              !=(principal.u.worker author.item)
              (token-valid:stead-session source.job)
          ==
        |
      =/  stage  stage.job
      =/  bytes  (~(get by artifacts.extras) id)
      =/  lease  (lease-of stage)
      ?~  lease  ?=(~ bytes)
      ?.  ?&  (same-actor:stead-session worker.u.lease u.worker)
              (gth attempt.u.lease 0)  (lte attempt.u.lease 3)
              (gth until.u.lease 0)
          ==
        |
      ?.  ?=(%finished -.stage)  ?=(~ bytes)
      ?~  bytes  |
      ?&  (valid-artifact u.bytes)
          =(source.evidence.stage source.job)
          =(recipe.evidence.stage recipe.job)
          =(output.evidence.stage (digest u.bytes))
          ?:  =(%passed outcome.evidence.stage)  (matches-manifest repo head.change.item u.bytes)
          &
      ==
    |
  ?.  (levy ~(tap by artifacts.extras) |=([id=@t bytes=octets:stead-git] (~(has by builds.delivery) id)))  |
  %+  levy  ~(tap by releases.delivery)
  |=  [id=@t entry=release:stead-code-delivery]
  =/  job  (~(get by builds.delivery) job.entry)
  ?~  job  |
  ?.  ?=(%finished -.stage.u.job)  |
  ?&  (uuid id)  =(id id.entry)  (valid-actor:stead-code-review-home owner.entry)
      !=(principal.owner.entry author.item.u.job)
      !=(principal.owner.entry principal.requester.u.job)
      !=(principal.owner.entry principal.worker.grant.stage.u.job)
      =(item.entry item.u.job)  =(evidence.entry evidence.stage.u.job)
      =(%passed outcome.evidence.entry)  (merged board repo item.entry)
  ==
--

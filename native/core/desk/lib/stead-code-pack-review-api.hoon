::  Browser review actions. The Home mints actor and selects the pack.
/+  stead-codec, stead-team, stead-session, stead-code-credentials, stead-code-review, stead-code-review-api, stead-code-pack-anchor, stead-code-pack-review, stead-code-pack-review-board, stead-code-pack-promotion, stead-code-git-objects, stead-git
=,  stead-codec
|%
+$  board  state:stead-code-pack-review-board
+$  proposal  proposal:stead-code-pack-review
+$  result  [status=@ud body=@t next=(unit board)]
++  failed
  |=  [status=@ud reason=@t]
  ^-  result
  [status (canonical (object ~[['error' reason]])) ~]
++  env
  |=  [team=state:stead-team destination=scope:stead-code-credentials now=@ud resolve=membership:stead-code-credentials]
  ^-  authority:stead-code-pack-review
  =/  allows=permit:stead-code-pack-review
    |=  [actor=actor:stead-session scope=scope:stead-code-credentials work=@t ref=@t role=role:stead-code-pack-review]
    ?:  (~(has in tombs.team) [project.scope 'work' '' work])  |
    =/  rank  (current-work:stead-code-review-api team actor scope work now)
    (gte rank ?:(=(%propose role) 2 3))
  [destination now resolve allows]
++  view-fields
  |=  row=proposal
  ^-  (list [@t @t])
  :~  ['proposal_id' id.item.row]
      ['revision' (decimal number.change.item.row)]
      ['author' author.item.row]
      ['work_id' work.item.row]
      ['source_ref' source.row]
      ['ref' target.location.item.row]
      ['base_oid' (oid-text:stead-git base.change.item.row)]
      ['head_oid' (oid-text:stead-git head.change.item.row)]
      ['base_snapshot' snapshot.row]
      ['generation' (decimal generation.row)]
  ==
++  run
  |=  $:  team=state:stead-team  book=board  auth=authentication:stead-team
          destination=scope:stead-code-credentials  current=manifest:stead-code-pack-anchor
          generation=@ud  now=@ud  fields=object-map  resolve=membership:stead-code-credentials
      ==
  ^-  result
  =/  operation  (field fields 'action')
  =/  id  (field fields 'proposal_id')
  ?.  (uuid id)  (failed 400 'invalid_request')
  =/  base-keys  ~['protocol' 'action' 'project_id' 'proposal_id']
  =/  environment  (env team destination now resolve)
  =/  caller  identity.auth
  =/  row  (~(get by proposals.book) id)
  ?:  =('external-proposal' operation)
    ?.  (keys fields base-keys)  (failed 400 'invalid_request')
    ?~  row  (failed 404 'denied_or_not_found')
    ?.  (subject:stead-team team auth project.destination 'work' '' work.item.u.row now)
      (failed 404 'denied_or_not_found')
    =/  review  (~(get by approvals.book) id)
    =/  committed=(unit @t)
      =/  records  ~(tap by promotions.book)
      |-
      ?~  records  ~
      =/  candidate  candidate.q.i.records
      ?:  =(u.row reviewed.review.candidate)  [~ snapshot.pack.decision.candidate]
      $(records t.records)
    =/  response
      %-  canonical  %-  object
      :*  ['protocol' 'stead.code/1']  ['status' 'proposal']
          ['reviewer' ?~(review '' principal.reviewer.u.review)]
          ['merged_revision' ?~(committed '' (decimal number.change.item.u.row))]
          ['merged_snapshot' (fall committed '')]  (view-fields u.row)
      ==
    [200 response ~]
  =/  request  (field fields 'request_id')
  =/  revision  (uint (field fields 'revision'))
  =/  changed
    ^-  result:stead-code-pack-review-board
    ?:  =('external-approve' operation)
      ?.  (keys fields ['request_id' 'revision' 'base_snapshot' 'base_oid' 'head_oid' base-keys])
        [%rejected %invalid-request]
      ?~  row  [%rejected %proposal-unavailable]
      ?.  ?&  =(revision number.change.item.u.row)
              =((field fields 'base_snapshot') snapshot.u.row)
              =((field fields 'base_oid') (oid-text:stead-git base.change.item.u.row))
              =((field fields 'head_oid') (oid-text:stead-git head.change.item.u.row))
          ==
        [%rejected %stale-review]
      (approve:stead-code-pack-review-board book environment generation current caller request u.row)
    ?.  =('external-submit' operation)  [%rejected %invalid-request]
    ?.  (keys fields ['request_id' 'revision' 'work_id' 'source_ref' 'ref' 'base_oid' 'head_oid' base-keys])
      [%rejected %invalid-request]
    =/  before  (parse-oid:stead-code-git-objects [40 (field fields 'base_oid')])
    =/  after  (parse-oid:stead-code-git-objects [40 (field fields 'head_oid')])
    ?.  &(?=(^ before) ?=(^ after))  [%rejected %invalid-request]
    =/  item=proposal:stead-code-review
      :*  id  principal.caller  [project.destination repository.destination (field fields 'ref')]
          (field fields 'work_id')  [epoch.destination revision u.before u.after]
      ==
    (submit:stead-code-pack-review-board book environment generation current caller request (field fields 'source_ref') item)
  ?:  ?=(%rejected -.changed)  (failed 409 reason.changed)
  =/  body
    %-  canonical  %-  object
    ~[['protocol' 'stead.code/1'] ['status' 'accepted'] ['request_id' request] ['proposal_id' id] ['revision' (decimal revision)]]
  [200 body ?:(?=(%applied -.changed) [~ next.changed] ~)]
--

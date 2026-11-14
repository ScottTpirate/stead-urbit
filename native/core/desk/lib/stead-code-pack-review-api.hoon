::  Browser review actions. The Home mints actor and selects the pack.
/+  stead-codec, stead-team, stead-session, stead-code-credentials, stead-code-review, stead-code-review-api, stead-code-pack-anchor, stead-code-pack-review, stead-code-pack-review-board, stead-code-pack-ledger, stead-code-git-objects, stead-git
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
++  visible
  |=  [team=state:stead-team book=board auth=authentication:stead-team project=@t now=@ud row=proposal]
  ^-  (unit @t)
  =/  work  work.item.row
  ?.  (subject:stead-team team auth project 'work' '' work now)  ~
  =/  linked  (~(got by works.data.team) [project work])
  =/  review  (~(get by approvals.book) id.item.row)
  =/  committed=(unit [request=@t snapshot=@t])
    =/  records  ~(tap by promotions.book)
    |-
    ?~  records  ~
    =/  candidate  candidate.q.i.records
    ?:  =(row reviewed.review.candidate)  [~ p.i.records snapshot.pack.decision.candidate]
    $(records t.records)
  =/  response
    %-  canonical  %-  object
    :*  ['protocol' 'stead.code/1']  ['status' 'proposal']
        ['work_title' (field data.linked 'title')]
        ['reviewer' ?~(review '' principal.reviewer.u.review)]
        ['merged_revision' ?~(committed '' (decimal number.change.item.row))]
        ['merged_snapshot' ?~(committed '' snapshot.u.committed)]
        ['merged_request_id' ?~(committed '' request.u.committed)]  (view-fields row)
    ==
  [~ response]
++  list-visible
  |=  [team=state:stead-team book=board auth=authentication:stead-team project=@t now=@ud filter=@t]
  ^-  result
  =/  remaining  ~(tap by proposals.book)
  =/  parts=(list @t)  ~
  |-
  ?~  remaining
    =/  ordered  (flop parts)
    =/  array
      ?~  ordered  '[]'
      %-  rap  :-  3
      ['[' i.ordered (weld (turn t.ordered |=(part=@t (cat 3 ',' part))) [']' ~])]
    =/  body  (canonical (object ~[['protocol' 'stead.code/1'] ['status' 'proposals'] ['rows' array]]))
    ?.  (lte (met 3 body) 245.760)  (failed 409 'review_list_capacity')
    [200 body ~]
  =/  row  q.i.remaining
  ?:  &(!=('' filter) !=(filter work.item.row))
    $(remaining t.remaining)
  =/  entry  (visible team book auth project now row)
  ?~  entry  $(remaining t.remaining)
  $(remaining t.remaining, parts [u.entry parts])
++  run
  |=  $:  team=state:stead-team  book=board  auth=authentication:stead-team
          destination=scope:stead-code-credentials  current=manifest:stead-code-pack-anchor
          generation=@ud  now=@ud  fields=object-map  resolve=membership:stead-code-credentials
      ==
  ^-  result
  =/  operation  (field fields 'action')
  ?:  =('external-list' operation)
    =/  base  ~['protocol' 'action' 'project_id']
    ?:  (keys fields base)  (list-visible team book auth project.destination now '')
    ?.  (keys fields ['work_id' base])  (failed 400 'invalid_request')
    =/  work  (field fields 'work_id')
    ?.  (uuid work)  (failed 400 'invalid_request')
    (list-visible team book auth project.destination now work)
  =/  id  (field fields 'proposal_id')
  ?.  (uuid id)  (failed 400 'invalid_request')
  =/  base-keys  ~['protocol' 'action' 'project_id' 'proposal_id']
  =/  environment  (env team destination now resolve)
  =/  caller  identity.auth
  =/  row  (~(get by proposals.book) id)
  ?:  =('external-proposal' operation)
    ?.  (keys fields base-keys)  (failed 400 'invalid_request')
    ?~  row  (failed 404 'denied_or_not_found')
    =/  found  (visible team book auth project.destination now u.row)
    ?~  found  (failed 404 'denied_or_not_found')
    [200 u.found ~]
  =/  request  (field fields 'request_id')
  =/  revision  (uint (field fields 'revision'))
  ?:  (gte generation max-advances:stead-code-pack-ledger)
    (failed 409 'history-capacity')
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
    ?.  (keys fields ['request_id' 'revision' 'work_id' 'source_ref' 'ref' 'base_oid' 'head_oid' 'base_snapshot' 'generation' base-keys])
      [%rejected %invalid-request]
    ?.  &(=(snapshot.current (field fields 'base_snapshot')) =((decimal generation) (field fields 'generation')))
      [%rejected %stale-selection]
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

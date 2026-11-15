::  Browser protocol for the configured Home review board. Identity and
::  policy come only from the authenticated Home caller.
/+  stead-codec, stead-team, stead-session, stead-code-credentials, stead-code-git-objects, stead-git, stead-code-store, stead-code-review-home, stead-code-delivery, stead-code-review
=,  stead-codec
|%
+$  answer  $%([%read rows=(list [@t @t])] [%accepted next=state:stead-code-review-home repo=state:stead-code-store rows=(list [@t @t])] [%failed status=@ud reason=@t])
++  current-work
  |=  [team=state:stead-team who=actor:stead-session scope=scope:stead-code-credentials work=@t now=@ud]
  ^-  @ud
  =/  actor  (native-context:stead-team team ship.who now)
  ?~  actor  0
  ?.  &((same-actor:stead-session who identity.u.actor) (subject:stead-team team u.actor project.scope 'work' '' work now))  0
  (role:stead-team team u.actor project.scope now)
++  decode
  |=  [fields=object-map base=(list @t) op=@t who=actor:stead-session scope=scope:stead-code-credentials]
  ^-  (unit command:stead-code-review-home)
  ?:  =('delegate' op)
    ?.  (keys fields ['delegation_id' 'worker_ship' 'work_id' 'ref' 'expires_at_ms' base])  ~
    =/  value  (field fields 'worker_ship')
    =/  worker  (slaw %p value)
    ?~  worker  ~
    ?.  =((scot %p u.worker) value)  ~
    [~ %delegate (field fields 'delegation_id') u.worker (field fields 'work_id') (field fields 'ref') (uint (field fields 'expires_at_ms'))]
  ?:  =('revoke-delegation' op)
    ?.  (keys fields ['delegation_id' base])  ~
    [~ %revoke (field fields 'delegation_id')]
  =/  required
    ?:  =('approve' op)  ['proposal_id' 'revision' base]
    ?:  =('merge' op)  ['proposal_id' 'revision' 'request_id' base]
    ?:  =('submit' op)  ['proposal_id' 'revision' 'work_id' 'ref' 'base_oid' 'head_oid' 'delegation_id' base]
    ~
  ?.  &(?=(^ required) (keys fields required))  ~
  =/  id  (field fields 'proposal_id')
  =/  number  (uint (field fields 'revision'))
  ?:  =('approve' op)  [~ %approve id number]
  ?:  =('merge' op)  [~ %merge id number (field fields 'request_id')]
  =/  old  (parse-oid:stead-code-git-objects [40 (field fields 'base_oid')])
  =/  new  (parse-oid:stead-code-git-objects [40 (field fields 'head_oid')])
  ?~  old  ~
  ?~  new  ~
  =/  delegation  (field fields 'delegation_id')
  =/  item=proposal:stead-code-review
    [id principal.who [project.scope repository.scope (field fields 'ref')] (field fields 'work_id') [epoch.scope number u.old u.new]]
  [~ %submit item ?:(=('' delegation) ~ [~ delegation])]
++  run
  |=  $:  team=state:stead-team  board=state:stead-code-review-home
          repo=state:stead-code-store  protected=(set @t)  who=actor:stead-session
          now=@ud  resolve=membership:stead-code-credentials  fields=object-map
          base=(list @t)  op=@t
      ==
  ^-  answer
  =/  scope  destination.repo
  ?.  =(scope destination.board.board)  [%failed 404 'denied_or_not_found']
  =/  rank
    |=  [actor=actor:stead-session target=scope:stead-code-credentials work=@t]
    ^-  @ud
    ?.  =(scope target)  0
    (current-work team actor scope work now)
  =/  permits=permit:stead-code-delivery
    |=  [actor=actor:stead-session target=scope:stead-code-credentials work=@t ref=@t action=role:stead-code-delivery]
    =/  level  (rank actor target work)
    ?+  action  |
      %agent-propose  (gte level 1)
      %propose  (gte level 2)
      %delegate  =(3 level)
      %review  =(3 level)
      %merge  =(3 level)
    ==
  =/  env=authority:stead-code-delivery
    :*  scope  now  resolve  permits
        |=([actor=actor:stead-session proposal=proposal:stead-code-review] *(unit @t))
        |=(ref=@t `@ux`0)
        |=([target=scope:stead-code-credentials recipe=@t] |)
        |=([target=scope:stead-code-credentials proposal=proposal:stead-code-review] |)
        |=([target=scope:stead-code-credentials job=@t proposal=proposal:stead-code-review attempt=@ud worker=actor:stead-session proof=attestation:stead-code-delivery] |)
    ==
  ?:  =('work-delegations' op)
    ?.  (keys fields ['work_id' base])  [%failed 400 'invalid_request']
    =/  work  (field fields 'work_id')
    ?.  (uuid work)  [%failed 400 'invalid_request']
    =/  level  (rank who scope work)
    ?:  =(0 level)  [%failed 404 'denied_or_not_found']
    =/  visible
      %+  skim  ~(tap by delegates.board.board)
      |=  [id=@t row=grant:stead-code-delivery]
      ?&  =(work work.entry.row)
          |(=(3 level) (same-actor:stead-session who worker.entry.row))
      ==
    =/  listed=(list [@t json])
      %+  turn  visible
      |=  [id=@t row=grant:stead-code-delivery]
      =/  entry  entry.row
      =/  status
        ?:  ?=(%revoked -.row)  'revoked'
        ?:  (lte expires.entry now)  'expired'
        ?:  (grant-valid:stead-code-delivery env entry)  'active'
        'unavailable'
      =/  links
        %+  skim  ~(tap by latest.board.board)
        |=  [proposal=@t revision=@ud]
        =/  stored  (~(get by revisions.board.board) [proposal revision])
        ?~  stored  |
        =([~ id] via.u.stored)
      =/  proposals=(list [@t json])
        %+  turn  links
        |=  [proposal=@t revision=@ud]
        [proposal [%s (decimal revision)]]
      :-  id
      %-  object
      :~  ['delegation_id' id]  ['worker_ship' (scot %p ship.worker.entry)]
          ['ref' target.entry]  ['expires_at_ms' (decimal expires.entry)]
          ['status' status]  ['proposals' (canonical [%o (malt proposals)])]
          ['can_revoke' ?:(&(?=(%granted -.row) (same-actor:stead-session who sponsor.entry)) 'yes' 'no')]
      ==
    [%read ~[['status' 'work-delegations'] ['work_id' work] ['rows' (canonical [%o (malt listed)])]]]
  ?:  =('proposal' op)
    ?.  (keys fields ['proposal_id' 'revision' base])  [%failed 400 'invalid_request']
    =/  viewer=view-policy:stead-code-review-home
      |=  [actor=actor:stead-session target=scope:stead-code-credentials work=@t ref=@t]
      (gte (rank actor target work) 1)
    =/  view
      (lookup:stead-code-review-home board repo env who viewer (field fields 'proposal_id') (uint (field fields 'revision')))
    ?~  view  [%failed 404 'denied_or_not_found']
    =/  item  item.u.view
    :+  %read  ['status' 'proposal']
    :~  ['proposal_id' id.item]  ['revision' (decimal number.change.item)]
        ['work_id' work.item]  ['ref' target.location.item]
        ['base_oid' (oid-text:stead-git base.change.item)]  ['head_oid' (oid-text:stead-git head.change.item)]
        ['author' author.item]  ['reviewer' (fall reviewer.u.view '')]
        ['merged_revision' ?~(merged.u.view '' (decimal u.merged.u.view))]
    ==
  =/  cmd  (decode fields base op who scope)
  ?~  cmd  [%failed 400 'invalid_request']
  =/  result  (perform:stead-code-review-home board repo protected env who u.cmd)
  ?:  ?=(%rejected -.result)  [%failed 409 reason.result]
  =/  rows=(list [@t @t])  ~[['status' ?:(?=(%replayed -.result) 'replayed' 'accepted')]]
  =/  delegation
    ?+  -.u.cmd  ''
      %delegate  id.u.cmd
      %revoke    id.u.cmd
    ==
  =?  rows  !=('' delegation)  [['delegation_id' delegation] rows]
  =?  rows  &(?=(^ receipt.result) ?=(%merge -.u.cmd))
    :*  ['request_id' request.u.cmd]
        ['proposal_id' id.u.cmd]
        ['revision' (decimal number.u.cmd)]
        ['repository_revision' (decimal revision.u.receipt.result)]
        rows
    ==
  [%accepted next.result repo.result rows]
--

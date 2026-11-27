/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-team-config, stead-session, stead-invitations, stead-http, stead-restore, stead-code-credentials, stead-projection
=,  stead-codec
=/  project=@t  '019939ba-4000-7000-8000-000000000001'
=/  company-init  (configure:stead-team empty:stead-team '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000002","binding_id":"019939ba-4000-7000-8000-000000000003","binding_revision":"1","active":"yes","expires_at_ms":"1600000000","display_name":"Synthetic member"}},"project_creators":{"019939ba-4000-7000-8000-000000000002":"yes"}}' ~zod 1)
=/  create  (decode:stead-team-codec '{"protocol":"stead.command/3","request_id":"019939ba-4000-7000-8000-000000000007","project_id":"019939ba-4000-7000-8000-000000000001","resource_id":"019939ba-4000-7000-8000-000000000001","expected_revision":"0","authority_epoch":"1","operation":"project.create","payload":{"organization_id":"019939ba-4000-7000-8000-000000000005","owning_team_id":"019939ba-4000-7000-8000-000000000006","title":"Synthetic ledger reload","project_key":"LEDGER","preset":"general"}}')
=/  actor  (need (native-context:stead-team company-init ~bus 1))
=/  created  (apply-command:stead-team company-init actor create 1)
=/  origin=@t  'https://home.test'
=/  pending  (begin:stead-session *state:stead-session identity.actor ~zod origin 1 222)
=/  proof  (approve:stead-session next.pending id.pending ~bus identity.actor ~zod origin 'stead.auth/1' 'member-session' 120.001 2)
=/  login  (consume:stead-session next.proof id.pending cookie.pending identity.actor ~zod origin 3 333)
=/  start=changes:stead-invitations  [~ ~ next.created next.login]
=/  json-fields
  |=  raw=@t
  ^-  object-map
  =/  o  (need (parse raw))
  ?>  ?=([%o *] o)
  p.o
=/  manage
  |=  [s=changes:stead-invitations action=@t fields=(list [@t @t]) now=@ud]
  =/  raw  (canonical (object [['protocol' 'stead.invitation/1'] ['action' action] ['project_id' project] fields]))
  (call:stead-invitations s ['/stead/api/invitations' raw cookie.login '' csrf.login] ~ now now)
=/  issue
  |=  [mode=@t role=@t who=@t]
  (manage start 'issue' ~[['mode' mode] ['role' role] ['identity_ship' who] ['expires_at_ms' ''] ['use_limit' '1']] 4)
=/  personal  (issue 'personal' 'contributor' '~nec')
=/  request-link  (issue 'request' 'reader' '')
=/  visit
  |=  [state=changes:stead-invitations token=@t ship=@p now=@ud]
  =/  body  (canonical (object ~[['protocol' 'stead.invitation/1'] ['token' token] ['identity_ship' (scot %p ship)]]))
  (call:stead-invitations state ['/stead/auth/invite/start' body '' '' ''] ~ now now)
=/  finish
  |=  [opened=result:stead-invitations sender=@p now=@ud]
  =/  msg  (need outgoing.opened)
  =/  id  (field (json-fields bytes.opened) 'challenge_id')
  =/  returned  (token:stead-session now 1 'synthetic-device')
  =/  approved-msg  (canonical [%o (~(put by (json-fields bytes.msg)) 'return_digest' [%s (digest:stead-session 'stead.identity-return/1' returned)])])
  =/  approvals  (approve-proof:stead-invitations pending.next.opened sender approved-msg now)
  ?>  ?=(^ cookies.opened)
  =/  cookie  (cut 3 [(met 3 '__Host-stead-pending=') 64] i.cookies.opened)
  =/  body  (canonical (object ~[['protocol' 'stead.invitation/1'] ['challenge_id' id] ['return_proof' returned]]))
  (call:stead-invitations next.opened(pending approvals) ['/stead/auth/invite/consume' body '' cookie ''] ~ now now)
=/  token  (field (json-fields bytes.personal) 'token')
=/  link-id  (field (json-fields bytes.personal) 'invitation_id')
=/  opened  (visit next.personal token ~nec 5)
=/  joined  (finish opened ~nec 6)
|%
++  test-invitation-personal-binding-and-expiry
  ?>  &(!(eligible:stead-invitations ~zod 'live-synthetic') !(eligible:stead-invitations 65.535 'live-synthetic'))
  ?>  &((eligible:stead-invitations 65.536 'live-synthetic') !(eligible:stead-invitations 4.294.967.296 'live-synthetic'))
  =/  wrong  (mule |.((visit next.personal token ~bud 5)))
  =/  expired  (mule |.((finish opened ~nec 120.005)))
  =/  later  (visit next.opened token ~nec 120.006)
  =/  forwarded  (mule |.((finish later ~bud 120.007)))
  ::  Three days later the issuing browser session has expired, as has the old proof.
  =/  monday=@ud  259.200.007
  =/  dormant  (prune:stead-session auth.next.opened monday)
  ?>  ?=(~ sessions.dormant)
  =/  anew  (visit next.opened(auth dormant) token ~nec monday)
  =/  accepted  (finish anew ~nec +(monday))
  ?>  =('authenticated' (field (json-fields bytes.accepted) 'status'))
  (expect !>(&(?=(%| -.wrong) ?=(%| -.expired) ?=(%| -.forwarded) =('pending' (field (json-fields bytes.later) 'status')))))
++  test-invitation-preserves-other-sessions-and-history
  =/  row  (~(got by offers.next.joined) link-id)
  =/  member  (need (native-context:stead-team db.next.joined ~nec 7))
  =/  scope=scope:stead-code-credentials  [~zod project project 1]
  =/  rights
    |=  db=state:stead-team
    ^-  allowance:stead-code-credentials
    |=  [who=actor:stead-session target=scope:stead-code-credentials access=access:stead-code-credentials]
    =/  identity  (native-context:stead-team db ship.who 7)
    ?~(identity | (gte (role:stead-team db u.identity project.target 7) ?:(=(%write access) 2 1)))
  =/  credential  (issue:stead-code-credentials *ledger:stead-code-credentials identity.actor scope & 900.000 3 7 (rights db.start))
  ?>  ?=(%& -.credential)
  =/  resolve=membership:stead-code-credentials
    |=  ship=@p
    =/  who  (native-context:stead-team db.next.joined ship 7)
    ?~(who ~ (some identity.u.who))
  ?>  =([~ identity.actor] (check:stead-code-credentials next.p.credential bearer.p.credential scope %write 7 resolve (rights db.next.joined)))
  =/  key  (digest:stead-session 'stead.session/1' cookie.login)
  =/  old  (~(got by sessions.auth.start) key)
  =/  events  journal.data.db.next.joined
  ?>  ?=(^ events)
  =/  grant  (need (parse-result bytes.i.events))
  ?>  ?=([%o *] grant)
  =/  before  db.next.personal
  =/  prior  (batch:stead-projection before (begin:stead-projection before *state:stead-projection))
  =/  view  (append:stead-projection prior i.events)
  ?>  (ready:stead-projection db.next.joined view)
  =/  recorded  (decode-authentication:stead-team (field p.grant 'authentication_context'))
  =/  restored  (step:stead-restore (begin:stead-restore db.next.joined ~zod))
  =/  ok=?
    ?&  =(1 (uses:stead-invitations row))
        =(2 (role:stead-team db.next.joined member project 7))
        =([~ old] (~(get by sessions.auth.next.joined) key))
        =('project-invitation/1' method.recorded)  =(link-id audit.recorded)
        =([~ db.next.joined] (result:stead-restore restored))
    ==
  (expect !>(ok))
++  test-invitation-retry-and-revocation
  =/  again  (finish (visit next.joined token ~nec 7) ~nec 8)
  ?>  =(db.next.joined db.next.again)
  =/  revoked  (manage next.joined 'revoke' ~[['invitation_id' link-id]] 8)
  =/  closed  (mule |.((visit next.revoked token ~nec 9)))
  =/  member  (need (native-context:stead-team db.next.joined ~nec 9))
  =/  out  (manage next.joined 'remove' ~[['identity_ship' '~nec'] ['invitation_id' link-id]] 9)
  =/  removed  db.next.out
  =/  previous  (~(got by offers.next.joined) link-id)
  =/  elapsed  next.joined(offers (~(put by offers.next.joined) link-id previous(expires 8)))
  =/  later  (manage elapsed 'issue' ~[['mode' 'request'] ['role' 'reader'] ['identity_ship' ''] ['expires_at_ms' ''] ['use_limit' '1']] 10)
  ?>  (~(has by offers.next.later) link-id)
  =/  late-remove  (manage next.later 'remove' ~[['identity_ship' '~nec'] ['invitation_id' link-id]] 11)
  ?>  !(~(has by (prune-book:stead-invitations offers.next.late-remove db.next.late-remove 12)) link-id)
  =/  retried  (mule |.((finish (visit next.out token ~nec 10) ~nec 11)))
  (expect !>(&(?=(%| -.closed) ?=(%| -.retried) =(0 (role:stead-team removed member project 12)))))
++  test-invitation-requires-current-maintainer
  =/  team  db.next.opened
  =/  all  grants.data.team
  =/  rows  ~(tap by all)
  ?>  ?=(^ rows)
  =/  key  p.i.rows
  =/  row  (~(got by all) key)
  =/  next  next.opened(db team(data data.team(grants (~(put by all) key row(revoked &)))))
  =/  result  (mule |.((finish opened(next next) ~nec 6)))
  =/  old  registry.db.next.joined
  =/  cfg  (need current.old)
  =/  changed  old(current (some cfg(members (~(del by members.cfg) ~nec))))
  =/  links  (after-config:stead-invitations offers.next.request-link old changed)
  =/  group  (~(got by links) (field (json-fields bytes.request-link) 'invitation_id'))
  ?>  &(!(available:stead-invitations group ~nec 7) (available:stead-invitations group ~bud 7))
  (expect !>(?=(%| -.result)))
++  test-invitation-group-request-needs-maintainer
  =/  id  (field (json-fields bytes.request-link) 'invitation_id')
  =/  group  (field (json-fields bytes.request-link) 'token')
  =/  requested  (finish (visit next.request-link group ~nec 5) ~nec 6)
  ?>  =(db.next.request-link db.next.requested)
  ?>  =('requested' (field (json-fields bytes.requested) 'status'))
  =/  accepted  (manage next.requested 'approve' ~[['identity_ship' '~nec'] ['invitation_id' id] ['role' 'reader']] 7)
  =/  final  (finish (visit next.accepted group ~nec 8) ~nec 9)
  =/  denied  (mule |.((visit next.final group ~bud 10)))
  ::  Two independently proven guests race for the final Reader slot.
  =/  open-link  (issue 'reader' 'reader' '')
  =/  shared  (field (json-fields bytes.open-link) 'token')
  =/  first  (visit next.open-link shared ~nec 10)
  =/  second  (visit next.first shared ~bud 11)
  =/  winner  (finish first(next next.second) ~nec 12)
  =/  loser  (mule |.((finish second(next next.winner) ~bud 13)))
  ?>  ?=(%| -.loser)
  ?>  ?=(~ (native-context:stead-team db.next.winner ~bud 14))
  =/  member  (need (native-context:stead-team db.next.final ~nec 10))
  (expect !>(&(?=(%| -.denied) =(1 (role:stead-team db.next.final member project 10)) =(db.next.final db.next.accepted))))
++  test-invitation-direct-return-binding
  =/  opened  (begin-as:stead-session *state:stead-session identity.actor ~zod origin 1 98 &)
  =/  returned  (token:stead-session 22 33 'identity-device')
  =/  return-hash  (digest:stead-session 'stead.identity-return/1' returned)
  =/  legacy  (approve:stead-session next.opened id.opened ~bus identity.actor ~zod origin 'stead.auth/1' 'member-session' 120.001 2)
  =/  approved  (approve-bound:stead-session next.opened id.opened ~bus identity.actor ~zod origin 'stead.auth/2' 'member-session' 120.001 2 return-hash)
  =/  missing  (consume:stead-session next.approved id.opened cookie.opened identity.actor ~zod origin 3 99)
  =/  mismatch  (consume-bound:stead-session next.approved id.opened cookie.opened identity.actor ~zod origin 3 99 return-hash)
  =/  consumed  (consume-bound:stead-session next.approved id.opened cookie.opened identity.actor ~zod origin 3 99 returned)
  (expect !>(&(=(%denied status.legacy) =(%approved status.approved) =(%denied status.missing) =(%denied status.mismatch) =(%accepted status.consumed))))
--

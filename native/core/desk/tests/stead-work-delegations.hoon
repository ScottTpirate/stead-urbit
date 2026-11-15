/+  *test, stead-codec, stead-code-home, stead-code-credentials, stead-code-store, stead-code-git-objects, stead-git, stead-session, stead-team, stead-team-config, stead-core
=,  stead-codec
=>
|%
++  id
  |=  value=@ud
  (fixture-id:stead-core (cat 3 '000000000' (decimal value)))
++  make
  |=  [kind=@tas text=@t]
  (need (hash-object:stead-code-git-objects kind [(met 3 text) text]))
++  tree
  (make %tree '')
++  commit
  |=  [parent=@ux message=@t]
  =/  parents  ?:  =(0 parent)  ''
    (rap 3 ~['parent ' (oid-text:stead-git parent) 10])
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 parents 'author Test <test@example.invalid> 1 +0000' 10 'committer Test <test@example.invalid> 1 +0000' 10 10 message 10]))
++  base
  (commit 0x0 'base')
++  head
  (commit oid:base 'candidate')
++  response
  |=  out=result:stead-code-home
  ^-  object-map
  =/  value  (need (parse-result data.body.out))
  ?>  ?=([%o *] value)
  p.value
++  nested
  |=  value=@t
  ^-  object-map
  =/  parsed  (need (parse-result value))
  ?>  ?=([%o *] parsed)
  p.parsed
++  rows
  |=  out=result:stead-code-home
  (nested (field (response out) 'rows'))
++  found
  |=  [result=object-map key=@t]
  ^-  object-map
  =/  row  (~(got by result) key)
  ?>  ?=([%o *] row)
  p.row
--
=/  project  (id 100)
=/  other  (id 101)
=/  work  (id 200)
=/  second-work  (id 201)
=/  main=@t  'refs/heads/main'
=/  topic=@t  'refs/heads/agent-topic'
=/  origin=@t  'https://home.test'
=/  sponsor=actor:stead-session  [~bus (id 300) (id 400) 1 & 1.000.000]
=/  worker=actor:stead-session  [~nec (id 301) (id 401) 1 & 1.000.000]
=/  other-worker=actor:stead-session  [~bud (id 302) (id 402) 1 & 1.000.000]
=/  reader=actor:stead-session  [~wes (id 303) (id 403) 1 & 1.000.000]
=/  outsider=actor:stead-session  [~sev (id 304) (id 404) 1 & 1.000.000]
=/  config=config:stead-team-config
  :*  1  ~zod  origin  (id 501)  (id 502)  'local-disposable'  'isolated-fake'
      (malt ~[[~bus [sponsor 'Sponsor']] [~nec [worker 'Agent']] [~bud [other-worker 'Second agent']] [~wes [reader 'Reader']] [~sev [outsider 'Outsider']]])
      ~
  ==
=/  project-row=project-state:stead-core  [1 1 1 ~]
=/  grants=(map @t grant-state:stead-core)
  %-  malt
  :~  [(id 500) [project principal.sponsor 'maintainer' 1.000.000 |]]
      [(id 501) [project principal.worker 'reader' 1.000.000 |]]
      [(id 502) [project principal.other-worker 'contributor' 1.000.000 |]]
      [(id 503) [project principal.reader 'reader' 1.000.000 |]]
      [(id 504) [other principal.sponsor 'maintainer' 1.000.000 |]]
  ==
=/  core=state:stead-core  *state:stead-core
=.  core  core(initialized &, projects (malt ~[[project project-row] [other project-row]]), works (malt ~[[[project work] [1 ~]] [[project second-work] [1 ~]] [[other work] [1 ~]]]), grants grants)
=/  team=state:stead-team  [[[~ config] ~ ~] core ~ ~ ~ ~]
=/  destination=scope:stead-code-credentials  [~zod project project 1]
=/  distinct=scope:stead-code-credentials  [~zod other other 1]
=/  protect=(set @t)  (silt ~[main])
=/  seeded=state:stead-code-store
  =/  allowed=allowance:stead-code-credentials
    |=  [who=actor:stead-session target=scope:stead-code-credentials kind=access:stead-code-credentials]
    &(=(who sponsor) =(target destination))
  =/  issued  (issue:stead-code-credentials *ledger:stead-code-credentials sponsor destination & 10.000 10 99 allowed)
  ?>  ?=(%& -.issued)
  =/  req  (id 600)
  =/  payload=payload:stead-code-store
    [destination req sponsor ~[[main 0x0 oid:base] [topic 0x0 oid:head]] ~[tree base head]]
  =/  digest  (fingerprint:stead-code-store payload)
  =/  repo  (empty:stead-code-store destination)
  =.  pending.repo  (~(put by pending.repo) req [digest payload])
  =/  applied
    (accept:stead-code-store repo destination next.p.issued bearer.p.issued req digest 12 (member:stead-code-home team 12) allowed |=([who=actor:stead-session loc=scope:stead-code-credentials action=action:stead-code-store delta=update:stead-code-store] &) ~)
  ?>  ?=(%applied -.applied)
  next.applied
=/  code=state:stead-code-home  *state:stead-code-home
=.  code  code(repos (malt ~[[project [seeded protect]] [other [(empty:stead-code-store distinct) protect]]]))
=/  request
  |=  [db=state:stead-team app=state:stead-code-home who=actor:stead-session target=@t now=@ud op=@t args=(list [@t @t])]
  ^-  result:stead-code-home
  =/  cookie  (token:stead-session ship.who 1 'fixture')
  =/  csrf  (token:stead-session ship.who 2 'fixture')
  =/  session=session:stead-session
    [who ~zod origin cookie (digest:stead-session 'stead.csrf/1' csrf) cookie 10.000]
  =/  auth=state:stead-session  [0 ~ (malt ~[[(digest:stead-session 'stead.session/1' cookie) session]])]
  =/  body  (canonical (object (weld ~[['protocol' 'stead.code/1'] ['action' op] ['project_id' target]] args)))
  (manage:stead-code-home db app auth ['/stead/api/code' body cookie '' csrf] now 55 |=(unused=@t |))
=/  first-id  (id 700)
=/  second-id  (id 701)
=/  elsewhere-id  (id 702)
=/  proposal  (id 800)
=/  grant
  |=  [app=state:stead-code-home delegation=@t ship=@t ticket=@t]
  (request team app sponsor project 20 'delegate' ~[['delegation_id' delegation] ['worker_ship' ship] ['work_id' ticket] ['ref' main] ['expires_at_ms' '500']])
=/  first  (grant code first-id '~nec' work)
=/  second  (grant next.first second-id '~bud' work)
=/  elsewhere  (grant next.second elsewhere-id '~bud' second-work)
=/  live  next.elsewhere
=/  read
  |=  [db=state:stead-team app=state:stead-code-home who=actor:stead-session target=@t ticket=@t now=@ud]
  (request db app who target now 'work-delegations' ~[['work_id' ticket]])
|%
++  test-work-delegations-native-http-scopes-and-reader-isolation
  =/  owned  (read team live sponsor project work 30)
  =/  assigned  (read team live worker project work 30)
  =/  read-only  (read team live reader project work 30)
  =/  absent  (read team live outsider project work 30)
  =/  wrong-work  (read team live sponsor project (id 299) 30)
  =/  other-project  (read team live sponsor other work 30)
  =/  mixed  live(reviews (~(put by reviews.live) other (~(got by reviews.live) project)))
  =/  deleted  team(tombs (silt ~[[project 'work' '' work]]))
  =/  owned-rows  (rows owned)
  =/  assigned-rows  (rows assigned)
  %-  expect
  !>  ?&  =(200 status.first)  =(200 status.second)  =(200 status.elsewhere)
          =(first-id (field (response first) 'delegation_id'))
          =(200 status.owned)  =(work (field (response owned) 'work_id'))
          =(2 ~(wyt by owned-rows))
          (~(has by owned-rows) first-id)  (~(has by owned-rows) second-id)
          !(~(has by owned-rows) elsewhere-id)
          =('yes' (field (found owned-rows first-id) 'can_revoke'))
          =(200 status.assigned)  =(1 ~(wyt by assigned-rows))
          =('no' (field (found assigned-rows first-id) 'can_revoke'))
          =(200 status.read-only)  =(~ (rows read-only))
          =(404 status.absent)  =(404 status.wrong-work)
          =(200 status.other-project)  =(~ (rows other-project))
          =(404 status:(read team mixed sponsor other work 30))
          =(404 status:(read deleted live sponsor project work 30))
          =(live next.owned)  =(live next.assigned)
      ==
++  test-work-delegations-native-http-worker-proposes-staged-commit
  =/  payload
    :~  ['proposal_id' proposal]  ['revision' '1']  ['work_id' work]  ['ref' main]
        ['base_oid' (oid-text:stead-git oid:base)]  ['head_oid' (oid-text:stead-git oid:head)]
        ['delegation_id' first-id]
    ==
  =/  posted  (request team live worker project 32 'submit' payload)
  =/  unrelated  (request team live reader project 32 'submit' payload)
  =/  listed  (read team next.posted worker project work 33)
  =/  entry  (found (rows listed) first-id)
  =/  revoked  (request team next.posted sponsor project 34 'revoke-delegation' ~[['delegation_id' first-id]])
  =/  settled  (read team next.revoked worker project work 35)
  =/  retry  (request team next.revoked worker project 36 'submit' payload)
  %-  expect
  !>  ?&  =(200 status.posted)  =('accepted' (field (response posted) 'status'))
          =(409 status.unrelated)
          =('active' (field entry 'status'))
          =('1' (field (nested (field entry 'proposals')) proposal))
          =(200 status.revoked)  =(first-id (field (response revoked) 'delegation_id'))
          =('revoked' (field (found (rows settled) first-id) 'status'))
          =(409 status.retry)  =(next.revoked next.retry)
          =(repos.live repos.next.revoked)
      ==
++  test-work-delegations-native-http-correlates-replay-and-expiry
  =/  again  (grant live first-id '~nec' work)
  =/  expired  (read team live worker project work 500)
  =/  denied  (request team live worker project 35 'revoke-delegation' ~[['delegation_id' first-id]])
  =/  malformed  (request team live sponsor project 35 'delegate' ~[['delegation_id' first-id]])
  %-  expect
  !>  ?&  =(200 status.again)  =('replayed' (field (response again) 'status'))
          =(first-id (field (response again) 'delegation_id'))  =(live next.again)
          =('expired' (field (found (rows expired) first-id) 'status'))
          =(409 status.denied)  =(live next.denied)
          =(400 status.malformed)  =(live next.malformed)
      ==
--

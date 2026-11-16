::  Source-only pure run fixtures. Positive gates below are explicit trusted
::  authority/result/provider evidence fixtures, NOT a live Home run adapter.
::  In particular their result gate is not proof that a real Change exists.
/+  *test, stead-codec, stead-core, stead-actor, stead-run-state, stead-run
=,  stead-codec
=,  stead-run-state
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  field-of
  |=  [raw=@t key=@t]
  ^-  @t
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (field p.value key)
++  command
  |=  [request=@ud expected=@ud attempt=@ud operation=operation]
  ^-  command:stead-run-state
  [(id request) (id 100) (id 401) expected attempt operation]
--
=/  person=verified:stead-actor
  [%native [[~bus (id 102) (id 202) 1 & 9.000.000] 'native' 'ship' (hex 64 1) 9.000.000 ~zod (id 105) (id 106) 'isolated-fake']]
=/  worker-actions=(list action:stead-actor)  ~[%work-read %work-comment %doc-propose]
=/  worker=verified:stead-actor
  [%service [(id 107) (id 807) 1 (hex 64 2) 1 (hex 64 3) (hex 64 4) 160.000 [~zod (id 100) 1 (id 101) (id 200) (id 201) (silt worker-actions)]]]
=/  task=contract
  :*  ~zod  (id 100)  (id 101)  1  2  (hex 64 5)
      (id 102)  (id 102)  %explicit  (id 107)  (id 807)  1
      (id 810)  1  (id 811)  1
      (scope-key:stead-core (id 100) (id 850))
      [(id 100) (id 107) 'contributor' 400.000 |]
      (hex 64 6)  ~[[(id 300) (id 200) (id 201) 0 '']]
      [300.000 [32 8 10.000 100.000 65.536 32.768]]  301.000
  ==
=/  output=result-reference  [(id 700) 1 (hex 64 7) (id 300)]
=/  book  (empty-live:stead-run (hex 64 8))
=/  gate=gates
  :*  |=  [actor=verified:stead-actor item=contract now=@ud]
      ^-  (unit membership)
      ?:  =(actor person)  (some [9.000.000 &])
      ?:  =(actor worker)  (some [160.000 |])
      ~
      |=  [actor=verified:stead-actor item=contract operation=@tas now=@ud]
      ^-  ?
      ?:  =(%read operation)  ?|(=(actor person) =(actor worker))
      ?:  ?=(?(%issue %answer %cancel %reconcile) operation)  =(actor person)
      =(actor worker)
      |=  [item=contract mode=?(%execute %read) now=@ud]
      ^-  ?
      =(item task)
      |=([item=contract now=@ud] &(=(item task) (lth now expires.grant.item)))
      |=  [actor=verified:stead-actor item=contract attempt=@ud proposal=intent now=@ud]
      ?&  =(%provider-call kind.proposal)  =((id 901) provider.proposal)
          =((hex 64 10) request-digest.proposal)
          =(charge.proposal [0 1 100 10 50 100])
      ==
      |=([item=contract attempt=@ud reference=result-reference now=@ud] &(=(item task) =(reference output)))
      |=([item=contract attempt=@ud effect=effect resolution=settlement now=@ud] =(evidence.resolution (hex 64 20)))
      |=([item=contract attempt=@ud effects-digest=@t evidence=@t now=@ud] =(evidence (hex 64 30)))
      |=(key=request-key |)
  ==
=/  issue  (command 301 0 0 [%issue task])
=/  issued  (apply:stead-run *state book person issue 1.000 gate [0 0 0])
=/  claim  (command 302 1 0 [%claim ~])
=/  claimed  (apply:stead-run next.issued live.issued worker claim 2.000 gate [1 0 0])
=>
|%
++  run
  |=  [prior=transition actor=verified:stead-actor cmd=command:stead-run-state now=@ud]
  ^-  transition
  (apply:stead-run next.prior live.prior actor cmd now gate [(lent ~(tap by requests.next.prior)) 0 0])
++  row
  |=  prior=transition
  ^-  head
  (~(got by heads.next.prior) [(id 100) (id 401)])
++  accepted
  |=  prior=transition
  ^-  ?
  =('accepted' (field-of response.prior 'status'))
++  rejected
  |=  [prior=transition reason=@t]
  ^-  ?
  &(=('rejected' (field-of response.prior 'status')) =(reason (field-of response.prior 'error')))
--
|%
++  test-run-claim-competes-and-retries-with-one-bounded-lease
  ::  Independently calculated SHA-256(domain + NUL + canonical JSON) vector.
  =/  portable  (contract-bytes task)
  =/  grant  (need (parse-result (field-of portable 'grant')))
  =/  targets  (need (parse-result (field-of portable 'targets')))
  ?>  &(?=([%o *] grant) ?=([%o *] targets))
  =/  target  (~(got by p.targets) (id 300))
  ?>  ?=([%o *] target)
  =/  two  task(targets [[(id 301) (id 200) (id 202) 0 ''] targets.task])
  =/  ordered  (normalize-contract two)
  ?>  ?=(^ targets.ordered)
  =/  replay  (run claimed worker claim 2.001)
  =/  competitor  (run claimed worker (command 303 1 0 [%claim ~]) 2.002)
  =/  renewal  (run claimed worker (command 304 2 1 [%heartbeat ~]) 121.000)
  ?>  ?=(%service -.worker)
  =/  renewed  worker(context context.worker(credential (hex 64 14), audit (hex 64 15), expires 250.000))
  =/  fresh-credential
    gate(member |=([actor=verified:stead-actor item=contract now=@ud] (some [250.000 |])), policy |=([actor=verified:stead-actor item=contract operation=@tas now=@ud] &))
  =/  forbidden  (apply:stead-run next.claimed live.claimed renewed (command 305 2 1 [%heartbeat ~]) 121.000 fresh-credential [2 0 0])
  =/  first  (~(got by attempts.next.claimed) [[(id 100) (id 401)] 1])
  =/  later  (~(got by attempts.next.renewal) [[(id 100) (id 401)] 1])
  ?>  ?=(^ intents.claimed)
  ?>  ?=(%execution -.i.intents.claimed)
  %-  expect
  !>  ?&  (accepted issued)  (accepted claimed)  (accepted renewal)
          =(1.569 (met 3 portable))
          =('8363546216f67077fb15b3c42123d55c95cfbb06692ddfa1f432b593385ec1af' (hash 'stead.run-contract/1' portable))
          (keys p.grant ~['project_id' 'principal_id' 'role' 'expires_at_ms' 'revoked'])
          =('no' (field p.grant 'revoked'))
          (keys p.target ~['kind' 'project_id' 'collection_id' 'document_id' 'expected_revision' 'base_markdown_sha256'])
          =('document' (field p.target 'kind'))
          =('1' (field-of (result-bytes output) 'result_revision'))
          =((hex 64 7) (field-of (result-bytes output) 'result_digest'))
          =((id 300) outcome.i.targets.ordered)
          =((contract-bytes two) (contract-bytes ordered))
          =(ordered (normalize-contract ordered))
          =(%queued phase:(row issued))  =(%running phase:(row claimed))
          =(1 (lent ~(tap by attempts.next.claimed)))  =(1 (lent intents.claimed))
          ?=(%execution -.i.intents.claimed)
          =(0 continuation.i.intents.claimed)
          =(122.000 until.first)  =(160.000 until.later)
          (rejected forbidden 'stale_lease')  =(attempts.next.claimed attempts.next.forbidden)
          =(response.claimed response.replay)  =(next.claimed next.replay)
          ?=(~ intents.replay)  ?=(~ record.replay)
          (rejected competitor 'revision_conflict')
          =(attempts.next.claimed attempts.next.competitor)
      ==
++  test-run-original-pins-fence-effects-but-comments-do-not
  ::  No comment/property revision is an execution input. Identical trusted
  ::  execution evidence still permits the heartbeat after ordinary discussion.
  =/  continued  (run claimed worker (command 303 2 1 [%heartbeat ~]) 3.000)
  =/  changed
    gate(pins |=([item=contract mode=?(%execute %read) now=@ud] =(%read mode)))
  =/  stale  (apply:stead-run next.claimed live.claimed worker (command 304 2 1 [%heartbeat ~]) 3.001 changed [2 0 0])
  =/  rotated  gate(original |=([item=contract now=@ud] |))
  =/  no-renewal  (apply:stead-run next.claimed live.claimed worker (command 305 2 1 [%heartbeat ~]) 3.002 rotated [2 0 0])
  %-  expect
  !>  ?&  (accepted continued)
          (rejected stale 'stale_contract_or_authority')
          (rejected no-renewal 'stale_contract_or_authority')
          =(attempts.next.claimed attempts.next.stale)
          =(heads.next.claimed heads.next.no-renewal)
          ?=(~ intents.stale)  ?=(~ intents.no-renewal)
      ==
++  test-run-clarification-is-attributable-and-only-explicit-continuation
  =/  waiting  (run claimed worker (command 303 2 1 [%wait 'Which introduction should I preserve?']) 3.000)
  =/  premature  (run waiting worker (command 304 3 1 [%resume 1]) 3.001)
  =/  answered  (run waiting person (command 305 3 1 [%answer 1 'Keep the existing introduction.']) 3.002)
  =/  resumed  (run answered worker (command 306 4 1 [%resume 1]) 3.003)
  =/  retry  (run resumed worker (command 306 4 1 [%resume 1]) 3.004)
  =/  expired  (run answered worker (command 307 4 1 [%resume 1]) 160.001)
  =/  question  (~(got by questions.next.resumed) [[(id 100) (id 401)] 1])
  =/  answer  (need answer.question)
  ?>  ?=(^ intents.waiting)
  ?>  ?=(^ intents.answered)
  ?>  ?=(^ intents.resumed)
  ?>  ?=(%execution -.i.intents.resumed)
  %-  expect
  !>  ?&  (accepted waiting)  (accepted answered)  (accepted resumed)
          (rejected premature 'answer_required')
          (rejected expired 'denied_or_not_found')
          =(%waiting phase:(row answered))  =(%running phase:(row resumed))
          =(1 attempt:(row resumed))  =(task contract:(row resumed))
          =((id 107) principal.question)  =((id 102) principal.answer)
          ?=(%question -.i.intents.waiting)  ?=(%answer -.i.intents.answered)
          ?=(%execution -.i.intents.resumed)  ?=(~ intents.expired)
          =(1 continuation.i.intents.resumed)
          =(response.resumed response.retry)  ?=(~ intents.retry)
      ==
++  test-run-unknown-provider-outcome-requires-reconciliation-before-replace
  =/  intent=intent  [(id 900) %provider-call (id 901) (hex 64 10) ~ [0 1 100 10 50 100]]
  =/  pending  (run claimed worker (command 303 2 1 [%intent intent]) 3.000)
  =/  duplicate  (run pending worker (command 304 3 1 [%intent intent]) 3.001)
  =/  unknown  (run pending worker (command 305 3 1 [%settle [(id 900) %unknown (hex 64 20) '']]) 3.002)
  =/  blocked  (run unknown worker (command 306 4 1 [%replace (hex 64 30)]) 125.000)
  =/  resolved  (run unknown person (command 307 4 1 [%reconcile [(id 900) %settled (hex 64 20) (hex 64 21)]]) 125.001)
  =/  replaced  (run resolved worker (command 308 5 1 [%replace (hex 64 30)]) 125.002)
  =/  late  (run replaced worker (command 309 6 1 [%finish output]) 125.003)
  =/  old  (~(got by attempts.next.replaced) [[(id 100) (id 401)] 1])
  %-  expect
  !>  ?&  (accepted pending)  (accepted duplicate)  ?=(~ intents.duplicate)
          =(used:(row pending) used:(row duplicate))
          (accepted unknown)  (rejected blocked 'effects_unresolved')
          (accepted resolved)  (accepted replaced)  =(2 attempt:(row replaced))
          =(%replaced disposition.old)  (rejected late 'revision_conflict')
          ?=(~ intents.late)  =(effects.next.resolved effects.next.replaced)
      ==
++  test-run-cancellation-fences-and-shares-existing-revocation-remainder
  =/  disabled  gate(original |=([item=contract now=@ud] |))
  =/  cancel  (command 303 1 0 [%cancel 'Stop this run.'])
  =/  canceled  (apply:stead-run next.issued live.issued person cancel 2.000 disabled [4.096 0 0])
  =/  capacity  (apply:stead-run next.issued live.issued person cancel 2.000 disabled [4.096 0 128])
  =/  exhausted  (apply:stead-run next.issued live.issued person cancel 2.000 disabled [4.096 2.048 0])
  =/  repeat  (apply:stead-run next.canceled live.canceled person (command 304 2 0 [%cancel 'Stop again.']) 2.001 disabled [4.096 1 1])
  =/  expired  (apply:stead-run next.issued live.issued person cancel 400.001 disabled [4.096 0 0])
  =/  cleanup  (apply:stead-run next.issued live.issued person cancel 400.001 disabled [1 0 0])
  =/  late  (run canceled worker (command 305 2 0 [%claim ~]) 2.002)
  %-  expect
  !>  ?&  (accepted canceled)  =(%canceled phase:(row canceled))
          =('security' (field-of (need record.canceled) 'capacity_class'))
          (rejected capacity 'capacity_exceeded')  (rejected exhausted 'capacity_exceeded')
          (rejected repeat 'capacity_exceeded')  (rejected expired 'capacity_exceeded')
          (accepted cleanup)  =('ordinary' (field-of (need record.cleanup) 'capacity_class'))
          (rejected late 'terminal_run')  ?=(~ intents.late)
          =(next.issued next.capacity)  =(next.issued next.expired)
      ==
++  test-run-finish-is-exact-reviewed-result-reference-not-work-completion
  =/  denied  gate(result |=([item=contract attempt=@ud reference=result-reference now=@ud] |))
  =/  finish  (command 303 2 1 [%finish output])
  =/  absent  (apply:stead-run next.claimed live.claimed worker finish 3.000 denied [2 0 0])
  =/  submitted  (run claimed worker finish 3.000)
  =/  forged-result  gate(result |=([item=contract attempt=@ud reference=result-reference now=@ud] &))
  =/  foreign  (apply:stead-run next.claimed live.claimed worker (command 305 2 1 [%finish output(outcome (id 301))]) 3.001 forged-result [2 0 0])
  =/  replay  (run submitted worker finish 130.000)
  =/  changed  (run submitted worker (command 303 2 1 [%finish output(digest (hex 64 11))]) 130.001)
  =/  fresh  (run submitted worker (command 304 3 1 [%finish output]) 130.002)
  ?>  ?=(^ intents.submitted)
  %-  expect
  !>  ?&  (rejected absent 'unverified_result')  (accepted submitted)
          (rejected foreign 'result_scope_conflict')  ?=(~ intents.foreign)
          =(%submitted phase:(row submitted))  =((some output) result:(row submitted))
          ?=(%submitted -.i.intents.submitted)
          ?=(~ leases.live.submitted)
          =(response.submitted response.replay)  =(next.submitted next.replay)
          ?=(~ intents.replay)  ?=(~ record.replay)
          (rejected changed 'request_id_reuse')  (rejected fresh 'terminal_run')
          (bounded:stead-run next.submitted)
      ==
++  test-run-restart-clears-lease-without-dispatch-or-fourth-attempt
  =/  restart  (restart:stead-run next.claimed (hex 64 9))
  =/  before=transition  [response.claimed db.restart book.restart ~ ~]
  =/  heartbeat  (run before worker (command 303 2 1 [%heartbeat ~]) 3.000)
  =/  no-evidence  (run before worker (command 304 2 1 [%replace (hex 64 31)]) 3.001)
  =/  second  (run before worker (command 305 2 1 [%replace (hex 64 30)]) 3.002)
  =/  again  (restart:stead-run next.second (hex 64 12))
  =/  second-base=transition  [response.second db.again book.again ~ ~]
  =/  third  (run second-base worker (command 306 3 2 [%replace (hex 64 30)]) 3.003)
  =/  last  (restart:stead-run next.third (hex 64 13))
  =/  third-base=transition  [response.third db.last book.last ~ ~]
  =/  fourth  (run third-base worker (command 307 4 3 [%replace (hex 64 30)]) 3.004)
  %-  expect
  !>  ?&  =(next.claimed db.restart)  ?=(~ leases.book.restart)  ?=(~ intents.restart)
          (rejected heartbeat 'stale_lease')  (rejected no-evidence 'reconciliation_required')
          (accepted second)  (accepted third)  =(3 attempt:(row third))
          (rejected fourth 'attempt_limit')  =(3 (lent ~(tap by attempts.next.fourth)))
          ?=(~ intents.fourth)  (bounded:stead-run next.third)
      ==
++  test-run-finite-budgets-and-project-run-cap-are-enforced
  =/  intent=intent  [(id 900) %provider-call (id 901) (hex 64 10) ~ [0 1 100 10 50 100]]
  =/  oversized  intent(charge [0 1 10.001 10 50 100])
  =/  larger-exact-request
    gate(effect |=([actor=verified:stead-actor item=contract attempt=@ud proposal=intent now=@ud] =(proposal oversized)))
  =/  blocked  (apply:stead-run next.claimed live.claimed worker (command 303 2 1 [%intent oversized]) 3.000 larger-exact-request [2 0 0])
  =/  zero  (run claimed worker (command 304 2 1 [%intent intent(charge [0 1 0 0 50 100])]) 3.001)
  =/  provider  (run claimed worker (command 305 2 1 [%intent intent(provider (id 902))]) 3.002)
  =/  understated  (run claimed worker (command 306 2 1 [%intent intent(charge [0 1 99 10 50 100])]) 3.003)
  =/  many
    =/  prior=transition  ['' *state book ~ ~]
    =/  count=@ud  0
    |-
    ?:  =(32 count)  prior
    =/  cmd=command:stead-run-state  [(id (add 400 count)) (id 100) (id (add 600 count)) 0 0 [%issue task]]
    =/  out  (apply:stead-run next.prior live.prior person cmd (add 1.000 count) gate [count 0 0])
    ?>  (accepted out)
    $(prior out, count +(count))
  =/  extra=command:stead-run-state  [(id 500) (id 100) (id 699) 0 0 [%issue task]]
  =/  overflow  (apply:stead-run next.many live.many person extra 2.000 gate [32 0 0])
  %-  expect
  !>  ?&  (rejected blocked 'budget_exhausted')  (rejected zero 'invalid_effect')
          (rejected provider 'effect_authority_denied')  (rejected understated 'effect_authority_denied')
          ?=(~ intents.provider)  ?=(~ intents.understated)
          =(heads.next.claimed heads.next.blocked)  ?=(~ effects.next.blocked)
          (rejected overflow 'capacity_exceeded')
          =(32 (lent ~(tap by heads.next.overflow)))  (bounded:stead-run next.many)
      ==
++  test-run-current-access-precedes-cache-and-shared-request-scope
  =/  hidden  (apply:stead-run next.claimed live.claimed worker claim 3.000 deny-gates:stead-run [2 0 0])
  =/  occupied  gate(used |=(key=request-key =(request.key request.claim)))
  =/  collision  (apply:stead-run next.issued live.issued worker claim 3.000 occupied [1 0 0])
  =/  missing-command  (command 304 0 0 [%claim ~])
  =/  missing  (run claimed worker missing-command(run (id 402)) 3.000)
  %-  expect
  !>  ?&  (rejected hidden 'denied_or_not_found')  =(next.claimed next.hidden)
          (rejected collision 'request_id_reuse')  =(next.issued next.collision)
          (rejected missing 'denied_or_not_found')  ?=(~ record.missing)
          ?=(~ intents.hidden)  ?=(~ record.hidden)
      ==
++  test-run-capacity-rolls-back-candidate-lease-and-effects
  =/  full  (apply:stead-run next.issued live.issued worker claim 2.000 gate [4.096 0 0])
  =/  intent=intent  [(id 900) %provider-call (id 901) (hex 64 10) ~ [0 1 100 10 50 100]]
  =/  effect  (apply:stead-run next.claimed live.claimed worker (command 303 2 1 [%intent intent]) 3.000 gate [4.096 0 0])
  =/  bad-ordinary  (apply:stead-run next.issued live.issued person (command 304 1 0 [%cancel 'Stop.']) 3.001 gate [4.097 0 0])
  =/  bad-security  (apply:stead-run next.issued live.issued person (command 304 1 0 [%cancel 'Stop.']) 3.001 gate [4.096 2.049 0])
  =/  bad-project  (apply:stead-run next.issued live.issued person (command 304 1 0 [%cancel 'Stop.']) 3.001 gate [4.096 0 129])
  =/  corrupt  next.claimed
  =/  row  (~(got by heads.corrupt) [(id 100) (id 401)])
  =.  corrupt  corrupt(heads (~(put by heads.corrupt) [(id 100) (id 401)] row(digest (hex 64 99))))
  =/  overdrawn  next.claimed(heads (~(put by heads.next.claimed) [(id 100) (id 401)] row(used [0 0 10.001 0 0 0])))
  %-  expect
  !>  ?&  (rejected full 'capacity_exceeded')  =(next.issued next.full)
          =(live.issued live.full)  ?=(~ intents.full)  ?=(~ record.full)
          (rejected effect 'capacity_exceeded')  =(next.claimed next.effect)
          =(live.claimed live.effect)  ?=(~ intents.effect)  ?=(~ record.effect)
          !(bounded:stead-run corrupt)
          !(bounded:stead-run overdrawn)
          (rejected bad-ordinary 'invalid_capacity')  (rejected bad-security 'invalid_capacity')
          (rejected bad-project 'invalid_capacity')  =(next.issued next.bad-ordinary)
          =(next.issued next.bad-security)  =(next.issued next.bad-project)
      ==
--

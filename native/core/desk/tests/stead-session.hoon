/+  stead-session, stead-codec
=,  stead-session
=/  alice=actor
  [~bus '019939ba-4000-7000-8000-000000000102' '019939ba-4000-7000-8000-000000000202' 1 & 9.999.999]
=/  bob=actor
  [~nec '019939ba-4000-7000-8000-000000000103' '019939ba-4000-7000-8000-000000000203' 1 & 9.999.999]
=/  origin  'https://home.test'
=/  empty=state  *state
=/  first=result  (begin empty alice ~zod origin 1.000 1)
=/  approved=result
  (approve next.first id.first ~bus alice ~zod origin 'stead.auth/1' 'member-session' 121.000 1.001)
=/  logged=result  (consume next.approved id.first cookie.first alice ~zod origin 1.002 2)
=/  live-pending=state  next.logged(challenges challenges.next.approved)
|%
++  actor-for
  |=  n=@ud
  ^-  actor
  [(add 100 n) (cat 3 '019939ba-4000-7000-8000-' (hex:stead-codec 12 (add 1.000 n))) (cat 3 '019939ba-4000-7000-8000-' (hex:stead-codec 12 (add 2.000 n))) 1 & 9.999.999]
++  enroll
  |=  [db=state identity=actor entropy=@]
  ^-  result
  =/  pending  (begin db identity ~zod origin 1.000 entropy)
  ?.  =(%pending status.pending)  pending
  =/  accepted  (approve next.pending id.pending ship.identity identity ~zod origin 'stead.auth/1' 'member-session' 121.000 1.001)
  ?>  =(%approved status.accepted)
  (consume next.accepted id.pending cookie.pending identity ~zod origin 1.002 +(entropy))
++  filled
  |=  [sessions=? count=@ud]
  ^-  state
  ?>  (lte count 64)
  =/  db  empty
  =/  index=@ud  0
  |-
  ?:  =(index count)  db
  =/  actor  (actor-for (div index 4))
  =/  row
    ?:  sessions  (enroll db actor index)
    (begin db actor ~zod origin 1.000 index)
  ?>  =(?:(sessions %accepted %pending) status.row)
  $(db next.row, index +(index))
++  test-session-token-separation
  ^-  tang
  ?>  =(%pending status.first)
  ?>  =(%accepted status.logged)
  ?>  (levy `(list @t)`~[id.first cookie.first id.logged cookie.logged csrf.logged] token-valid)
  ?>  =(5 (lent ~(tap in (silt ~[id.first cookie.first id.logged cookie.logged csrf.logged]))))
  ?>  !=(id.first id:(begin empty alice ~zod origin 1.000 2))
  ~
++  test-session-origin-actor-admission
  ^-  tang
  ?>  (levy `(list @t)`~['https://home.test' 'https://home.localhost:8443'] origin-valid)
  ?>  (levy `(list @t)`~['http://home.test' 'https://Home.test' 'https://home.test/' 'https://home.test:443' 'https://home.test:0' 'https://home.test:65536' 'https://home.test:0443' 'https://-home.test' 'https://home..test' 'https://home.test:443:80'] |=(x=@t !(origin-valid x)))
  ?>  =(%denied status:(begin empty alice ~bus origin 1.000 1))
  ?>  =(%denied status:(begin empty alice(active |) ~zod origin 1.000 1))
  ?>  =(%denied status:(begin empty alice(revision 0) ~zod origin 1.000 1))
  ?>  =(%denied status:(begin empty alice(binding 'bad') ~zod origin 1.000 1))
  ~
++  test-session-approval-binding
  ^-  tang
  ?>  =(%approved status.approved)
  ?>  =(%denied status:(approve next.first id.first ~nec alice ~zod origin 'stead.auth/1' 'member-session' 121.000 1.001))
  ?>  =(%denied status:(approve next.first id.first ~bus alice ~bus origin 'stead.auth/1' 'member-session' 121.000 1.001))
  ?>  =(%denied status:(approve next.first id.first ~bus alice ~zod 'https://other.test' 'stead.auth/1' 'member-session' 121.000 1.001))
  ?>  =(%denied status:(approve next.first id.first ~bus alice ~zod origin 'stead.auth/2' 'member-session' 121.000 1.001))
  ?>  =(%denied status:(approve next.first id.first ~bus alice ~zod origin 'stead.auth/1' 'owner-session' 121.000 1.001))
  ?>  =(%denied status:(approve next.first id.first ~bus alice ~zod origin 'stead.auth/1' 'member-session' 121.001 1.001))
  ?>  (levy `(list actor)`~[alice(ship ~nec) alice(principal principal.bob) alice(binding binding.bob) alice(revision 2) alice(active |) alice(expires 1.001)] |=(x=actor =(%denied status:(approve next.first id.first ~bus x ~zod origin 'stead.auth/1' 'member-session' 121.000 1.001))))
  ?>  =(%denied status:(approve next.approved id.first ~bus alice ~zod origin 'stead.auth/1' 'member-session' 121.000 1.002))
  ~
++  test-session-challenge-expiry
  ^-  tang
  ?>  =(%approved status:(approve next.first id.first ~bus alice ~zod origin 'stead.auth/1' 'member-session' 121.000 120.999))
  ?>  =(%denied status:(approve next.first id.first ~bus alice ~zod origin 'stead.auth/1' 'member-session' 121.000 121.000))
  ?>  =(%accepted status:(consume next.approved id.first cookie.first alice ~zod origin 120.999 2))
  ?>  =(%denied status:(consume next.approved id.first cookie.first alice ~zod origin 121.000 2))
  ~
++  test-session-consumption-possession
  ^-  tang
  ?>  =(%denied status:(consume next.first id.first cookie.first alice ~zod origin 1.002 2))
  ?>  =(%denied status:(consume next.approved id.first (token 9 1 'stolen') alice ~zod origin 1.002 2))
  ?>  =(%denied status:(consume next.approved id.first cookie.first bob ~zod origin 1.002 2))
  ?>  =(%accepted status.logged)
  ~
++  test-session-consumption-replay
  ^-  tang
  ?>  =(%denied status:(consume next.logged id.first cookie.first alice ~zod origin 1.003 2))
  ?>  !(~(has by challenges.next.logged) id.first)
  ~
++  test-session-current-authorization
  ^-  tang
  ?>  ?=(^ (authorize next.logged cookie.logged csrf.logged alice ~zod origin 1.003))
  ?>  ?=(~ (authorize next.logged cookie.logged cookie.logged alice ~zod origin 1.003))
  ?>  ?=(~ (authorize next.logged cookie.logged csrf.logged alice ~bus origin 1.003))
  ?>  ?=(~ (authorize next.logged cookie.logged csrf.logged alice ~zod 'https://other.test' 1.003))
  ?>  (levy `(list actor)`~[bob alice(binding binding.bob) alice(revision 2) alice(active |) alice(expires 1.003)] |=(x=actor ?=(~ (authorize next.logged cookie.logged csrf.logged x ~zod origin 1.003))))
  ~
++  test-session-session-expiry
  ^-  tang
  ?>  ?=(^ (authorize next.logged cookie.logged csrf.logged alice ~zod origin 1.801.001))
  ?>  ?=(~ (authorize next.logged cookie.logged csrf.logged alice ~zod origin 1.801.002))
  ~
++  test-session-challenge-limits
  ^-  tang
  =/  global  (filled | 32)
  =/  personal  (filled | 4)
  ?>  =(32 (lent ~(tap by challenges.global)))
  ?>  =(%capacity status:(begin global (actor-for 8) ~zod origin 1.001 99))
  ?>  =(%capacity status:(begin personal (actor-for 0) ~zod origin 1.001 99))
  ?>  =(%pending status:(begin personal (actor-for 1) ~zod origin 1.001 99))
  ~
++  test-session-session-limits
  ^-  tang
  =/  global  (filled & 64)
  =/  personal  (filled & 4)
  ?>  =(64 (lent ~(tap by sessions.global)))
  ?>  =(%capacity status:(enroll global (actor-for 16) 99))
  ?>  =(%capacity status:(enroll personal (actor-for 0) 99))
  ?>  =(%accepted status:(enroll personal (actor-for 1) 99))
  ~
++  test-session-consume-rollback
  ^-  tang
  =/  full  live-pending(counter 18.446.744.073.709.551.615)
  =/  outcome  (consume full id.first cookie.first alice ~zod origin 1.002 2)
  ?>  =(%capacity status.outcome)
  ?>  =(full next.outcome)
  ?>  ?=(^ (authorize next.outcome cookie.logged csrf.logged alice ~zod origin 1.003))
  ::  A collision is forced with an independently created other-browser row.
  =/  other  (enroll next.logged bob 99)
  =/  old-key  (digest 'stead.session/1' cookie.other)
  =/  target-key  (digest 'stead.session/1' (token 9 +(counter.next.other) 'stead.session/1'))
  =/  collision  next.other(challenges challenges.next.approved, sessions (~(put by sessions.next.other) target-key (~(got by sessions.next.other) old-key)))
  =/  failed  (consume collision id.first cookie.first alice ~zod origin 1.003 9)
  ?>  =(%capacity status.failed)
  ?>  =(collision next.failed)
  ~
++  test-session-replace-rollback
  ^-  tang
  =/  full  live-pending(counter 18.446.744.073.709.551.615)
  =/  outcome  (replace full cookie.logged csrf.logged alice bob ~zod origin 1.003 3)
  ?>  =(%capacity status.outcome)
  ?>  =(full next.outcome)
  ?>  ?=(^ (authorize next.outcome cookie.logged csrf.logged alice ~zod origin 1.004))
  =/  denied  (replace live-pending cookie.logged 'wrong' alice bob ~zod origin 1.003 3)
  ?>  =(%denied status.denied)
  ?>  =(live-pending next.denied)
  ~
++  test-session-replace-isolation
  ^-  tang
  =/  other  (enroll live-pending bob 99)
  =/  replaced  (replace next.other cookie.logged csrf.logged alice alice ~zod origin 2.000 3)
  ?>  =(%pending status.replaced)
  ?>  !(~(has by challenges.next.replaced) id.first)
  ?>  ?=(~ (authorize next.replaced cookie.logged csrf.logged alice ~zod origin 2.001))
  ?>  ?=(^ (authorize next.replaced cookie.other csrf.other bob ~zod origin 2.001))
  =/  approval  (approve next.replaced id.replaced ~bus alice ~zod origin 'stead.auth/1' 'member-session' 122.000 2.001)
  =/  replacement  (consume next.approval id.replaced cookie.replaced alice ~zod origin 2.002 4)
  ?>  =(%accepted status.replacement)
  ?>  ?=(^ (authorize next.replacement cookie.replacement csrf.replacement alice ~zod origin 2.003))
  ?>  ?=(^ (authorize next.replacement cookie.other csrf.other bob ~zod origin 2.003))
  ~
++  test-session-logout-cleanup
  ^-  tang
  =/  other  (enroll live-pending bob 99)
  =/  outcome  (logout next.other cookie.logged csrf.logged alice ~zod origin 1.004)
  ?>  =(%logged-out status.outcome)
  ?>  !(~(has by challenges.next.outcome) id.first)
  ?>  ?=(~ (authorize next.outcome cookie.logged csrf.logged alice ~zod origin 1.005))
  ?>  ?=(^ (authorize next.outcome cookie.other csrf.other bob ~zod origin 1.005))
  ~
++  test-session-binding-cleanup
  ^-  tang
  =/  other  (enroll live-pending bob 99)
  =/  revoked  (invalidate-actor next.other principal.alice)
  ?>  =(~ challenges.revoked)
  ?>  ?=(~ (authorize revoked cookie.logged csrf.logged alice ~zod origin 1.003))
  ?>  ?=(^ (authorize revoked cookie.other csrf.other bob ~zod origin 1.003))
  ~
++  test-session-empty-state-denial
  ^-  tang
  ?>  ?=(~ (authorize empty cookie.logged csrf.logged alice ~zod origin 1.003))
  ?>  =(%denied status:(consume empty id.first cookie.first alice ~zod origin 1.003 3))
  ~
++  test-session-resume-rotation
  =/  row  (~(got by sessions.next.logged) (digest 'stead.session/1' cookie.logged))
  =/  renewed  (resume next.logged cookie.logged alice ~zod origin 1.005 998)
  ?>  =(%authenticated status.renewed)
  ?>  &(!=('' csrf.renewed) !=(csrf.logged csrf.renewed))
  ?>  =(~ (authorize next.renewed cookie.logged csrf.logged alice ~zod origin 1.006))
  ?>  ?=(^ (authorize next.renewed cookie.logged csrf.renewed alice ~zod origin 1.006))
  =/  after  (~(got by sessions.next.renewed) (digest 'stead.session/1' cookie.logged))
  ?>  =(row after(csrf csrf.row))
  ?>  =(challenges.next.logged challenges.next.renewed)
  ?>  =('' cookie.renewed)
  ~
++  test-session-resume-denial
  =/  wrong  (resume next.logged cookie.logged bob ~zod origin 1.005 998)
  ?>  =(%denied status.wrong)
  ?>  =(next.logged next.wrong)
  =/  expired  (resume next.logged cookie.logged alice ~zod origin 1.801.002 998)
  ?>  =(%denied status.expired)
  ?>  =(next.logged next.expired)
  =/  rebound  (resume next.logged cookie.logged alice(revision 2) ~zod origin 1.005 998)
  ?>  =(%denied status.rebound)
  ?>  =(next.logged next.rebound)
  =/  misplaced  (resume next.logged cookie.logged alice ~bus origin 1.005 998)
  ?>  =(%denied status.misplaced)
  ?>  =(next.logged next.misplaced)
  =/  foreign  (resume next.logged cookie.logged alice ~zod 'https://other.test' 1.005 998)
  ?>  =(%denied status.foreign)
  ?>  =(next.logged next.foreign)
  ~
++  test-session-resume-boundary
  =/  full  next.logged(counter 18.446.744.073.709.551.615)
  =/  capped  (resume full cookie.logged alice ~zod origin 1.005 998)
  ?>  =(%capacity status.capped)
  ?>  =(full next.capped)
  =/  renewed  (resume next.logged cookie.logged alice ~zod origin 1.801.001 998)
  ?>  =(%authenticated status.renewed)
  ?>  ?=(~ (authorize next.renewed cookie.logged csrf.renewed alice ~zod origin 1.801.002))
  ~
--

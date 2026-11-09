/+  *test, stead-code-credentials, stead-session
=,  stead-code-credentials
=/  alice=actor
  [~bus '019939ba-4000-7000-8000-000000000102' '019939ba-4000-7000-8000-000000000202' 1 & 2.000.000]
=/  bob=actor
  [~nec '019939ba-4000-7000-8000-000000000103' '019939ba-4000-7000-8000-000000000203' 1 & 2.000.000]
=/  target=scope
  [~zod '019939ba-4000-7000-8000-000000000301' '019939ba-4000-7000-8000-000000000302' 2]
=/  allowed=allowance
  |=  [who=actor destination=scope operation=access]
  &
=/  read-only=allowance
  |=  [who=actor destination=scope operation=access]
  =(%read operation)
=/  denied=allowance
  |=  [who=actor destination=scope operation=access]
  |
=/  resolve=membership
  |=  ship=@p
  ^-  (unit actor)
  ?:  =(ship ~bus)  [~ alice]
  ~
=/  rotated=membership
  |=  ship=@p
  ^-  (unit actor)
  ?:  =(ship ~bus)  [~ alice(revision 2)]
  ~
=/  unbound=membership
  |=  ship=@p
  ^-  (unit actor)
  ~
=/  write-issue  (issue *ledger alice target & 1.000.000 1.000 42 allowed)
?>  ?=(%& -.write-issue)
=/  read-issue  (issue *ledger alice target | 10.000 1.000 17 read-only)
?>  ?=(%& -.read-issue)
=/  book  next.p.write-issue
=/  secret  bearer.p.write-issue
=/  id  handle.p.write-issue
|%
++  test-credential-issue-bounds-expiry
  (expect !>(&(=(901.000 expires.p.write-issue) =(10.000 expires.p.read-issue))))
++  test-credential-digest-storage
  =/  key  (digest:stead-session 'stead.git-credential/1' secret)
  (expect !>(&(!=(secret id) !(~(has by credentials.book) secret) (~(has by credentials.book) key))))
++  test-credential-active-write
  (expect !>(=([~ alice] (check book secret target %write 1.001 resolve allowed))))
++  test-credential-active-read
  (expect !>(=([~ alice] (check book secret target %read 1.001 resolve read-only))))
++  test-credential-read-cannot-write
  (expect !>(=(~ (check next.p.read-issue bearer.p.read-issue target %write 1.001 resolve allowed))))
++  test-credential-read-only-role-cannot-issue-write
  (expect !>(=([%| %denied] (issue *ledger alice target & 10.000 1.000 42 read-only))))
++  test-credential-unauthorized-issue
  (expect !>(=([%| %denied] (issue *ledger alice target | 10.000 1.000 42 denied))))
++  test-credential-current-policy-denial
  (expect !>(=(~ (check book secret target %write 1.001 resolve read-only))))
++  test-credential-other-repository
  (expect !>(=(~ (check book secret target(repository '019939ba-4000-7000-8000-000000000303') %read 1.001 resolve allowed))))
++  test-credential-other-home
  (expect !>(=(~ (check book secret target(home ~bud) %read 1.001 resolve allowed))))
++  test-credential-stale-epoch
  (expect !>(=(~ (check book secret target(epoch 3) %read 1.001 resolve allowed))))
++  test-credential-binding-revision
  (expect !>(=(~ (check book secret target %read 1.001 rotated allowed))))
++  test-credential-unbound-member
  (expect !>(=(~ (check book secret target %read 1.001 unbound allowed))))
++  test-credential-expiry
  (expect !>(=(~ (check book secret target %read 901.000 resolve allowed))))
++  test-credential-invalid-token
  (expect !>(=(~ (check book 'invalid' target %read 1.001 resolve allowed))))
++  test-credential-handle-is-not-bearer
  (expect !>(=(~ (check book id target %read 1.001 resolve allowed))))
++  test-credential-revoke-wrong-member
  (expect !>(=([%| %denied] (revoke book id bob ~zod 1.001))))
++  test-credential-revoke-wrong-home
  (expect !>(=([%| %denied] (revoke book id alice ~bud 1.001))))
++  test-credential-revoke
  =/  outcome  (revoke book id alice ~zod 1.001)
  ?>  ?=(%& -.outcome)
  (expect !>(=(~ (check p.outcome secret target %read 1.001 resolve allowed))))
++  test-credential-counter-limit
  (expect !>(=([%| %capacity] (issue [18.446.744.073.709.551.615 ~] alice target | 10.000 1.000 42 allowed))))
++  failure-control
  (expect !>(%.n))
--

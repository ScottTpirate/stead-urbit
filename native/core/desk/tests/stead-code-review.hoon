/+  *test, stead-code-review
|%
++  item
  ^-  proposal:stead-code-review
  ['proposal' 'author' ['project' 'repository' 'refs/heads/main'] 'work' [7 1 0x1 0x2]]
++  evidence
  ^-  approval:stead-code-review
  ['reviewer' item]
++  allowed-review
  |=  [actor=@t where=scope:stead-code-review]
  ^-  ?
  =([actor where] ['reviewer' ['project' 'repository' 'refs/heads/main']])
++  allowed-merge
  |=  [actor=@t where=scope:stead-code-review]
  ^-  ?
  =([actor where] ['maintainer' ['project' 'repository' 'refs/heads/main']])
++  denied
  |=  [actor=@t where=scope:stead-code-review]
  ^-  ?
  |
++  review-check
  |=  [proposal=proposal:stead-code-review approval=approval:stead-code-review reason=@tas]
  ^-  tang
  (expect !>(=([%| reason] (check-merge:stead-code-review proposal approval 7 0x1 'maintainer' allowed-review allowed-merge))))
++  test-review-records-exact-change
  (expect !>(=([%& evidence] (approve:stead-code-review item 7 'reviewer' allowed-review))))
++  test-review-self-denied
  (expect !>(=([%| %self-review] (approve:stead-code-review item 7 'author' allowed-review))))
++  test-review-outsider-denied
  (expect !>(=([%| %review-denied] (approve:stead-code-review item 7 'outsider' allowed-review))))
++  test-review-approval-epoch
  (expect !>(=([%| %stale-epoch] (approve:stead-code-review item 8 'reviewer' allowed-review))))
++  test-review-candidate-ref
  (expect !>(=([%& 'refs/heads/main' 0x1 0x2] (check-merge:stead-code-review item evidence 7 0x1 'maintainer' allowed-review allowed-merge))))
++  test-review-revoked-reviewer
  (expect !>(=([%| %review-denied] (check-merge:stead-code-review item evidence 7 0x1 'maintainer' denied allowed-merge))))
++  test-review-merge-permission
  (expect !>(=([%| %merge-denied] (check-merge:stead-code-review item evidence 7 0x1 'reviewer' allowed-review allowed-merge))))
++  test-review-epoch-changed
  (expect !>(=([%| %stale-epoch] (check-merge:stead-code-review item evidence 8 0x1 'maintainer' allowed-review allowed-merge))))
++  test-review-ref-changed
  (expect !>(=([%| %stale-target] (check-merge:stead-code-review item evidence 7 0x3 'maintainer' allowed-review allowed-merge))))
++  test-review-proposal-revised
  =/  current  item
  (review-check current(change change.current(number 2)) evidence %stale-review)
++  test-review-head-changed
  =/  current  item
  (review-check current(change change.current(head 0x4)) evidence %stale-review)
++  test-review-scope-changed
  =/  proof  evidence
  =/  wrong  reviewed.proof
  (review-check item proof(reviewed wrong(location location.wrong(repo 'other-repository'))) %stale-review)
++  test-review-self-merge
  (expect !>(=([%| %self-merge] (check-merge:stead-code-review item evidence 7 0x1 'author' allowed-review allowed-merge))))
++  test-review-forged-self-review
  =/  proof  evidence
  (review-check item proof(reviewer 'author') %self-review)
++  test-review-requires-work-item
  =/  current  item
  (review-check current(work '') evidence %invalid-proposal)
--

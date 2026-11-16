::  Pure exact-revision review checks. Only the home reads/stores approvals.
::  Gates receive authenticated principals and use current scoped policy.
/+  stead-code-git-objects, stead-code-receive
|%
+$  scope  [project=@t repo=@t target=@t]
+$  revision  [epoch=@ud number=@ud base=@ux head=@ux]
+$  proposal  [id=@t author=@t location=scope work=@t change=revision]
+$  approval  [reviewer=@t reviewed=proposal]
+$  permission  $-([@t scope] ?)
+$  merge-result  (each update:stead-code-receive @tas)
::
++  id-width
  |=  value=@t
  ^-  ?
  ?&  !=('' value)
      (lte (met 3 value) 64)
  ==
::
++  valid-proposal
  |=  item=proposal
  ^-  ?
  ?&  (id-width id.item)
      (id-width author.item)
      (id-width project.location.item)
      (id-width repo.location.item)
      (id-width work.item)
      =('refs/heads/' (cut 3 [0 11] target.location.item))
      (valid-ref:stead-code-git-objects [(met 3 target.location.item) target.location.item])
      !=(0 epoch.change.item)
      !=(0 number.change.item)
      !=(0 head.change.item)
      !=(base.change.item head.change.item)
      (lte (met 3 base.change.item) 20)
      (lte (met 3 head.change.item) 20)
  ==
::
++  approve
  |=  [item=proposal epoch=@ud reviewer=@t review=permission]
  ^-  (each approval @tas)
  ?.  (valid-proposal item)  [%| %invalid-proposal]
  ?.  (id-width reviewer)  [%| %invalid-principal]
  ?:  =(reviewer author.item)  [%| %self-review]
  ?.  (review reviewer location.item)  [%| %review-denied]
  ?.  =(epoch epoch.change.item)  [%| %stale-epoch]
  [%& reviewer item]
::
::  The authority must retrieve evidence from its accepted review store.
::  This proves review scope/current eligibility, not ancestry or ref write.
::  The resulting command still goes through the final receive transaction.
++  check-merge
  |=  $:  item=proposal  evidence=approval  epoch=@ud  prior=@ux
          merger=@t  review=permission  merge=permission
      ==
  ^-  merge-result
  ?.  (valid-proposal item)  [%| %invalid-proposal]
  ?.  &((id-width merger) (id-width reviewer.evidence))  [%| %invalid-principal]
  ?:  =(author.item merger)  [%| %self-merge]
  ?.  (merge merger location.item)  [%| %merge-denied]
  ?.  =(epoch epoch.change.item)  [%| %stale-epoch]
  ?.  =(prior base.change.item)  [%| %stale-target]
  ?.  =(reviewed.evidence item)  [%| %stale-review]
  ?:  =(author.item reviewer.evidence)  [%| %self-review]
  ?.  (review reviewer.evidence location.item)  [%| %review-denied]
  [%& target.location.item prior head.change.item]
--

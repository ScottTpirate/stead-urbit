::  Bounded exact commit ancestry over a repository-scoped reader.
::  Each turn verifies one commit or consumes one duplicate edge.
::  The authority owns the saved job and binds the reader to the same view.
/+  stead-code-git-graph
|%
+$  reader  reader:stead-code-git-graph
+$  search
  $%  [%walking base=@ux todo=(list @ux) seen=(set @ux) queued=@ud steps=@ud bytes=@ud]
      [%ancestor ~]
      [%diverged ~]
      [%invalid reason=@tas]
  ==
::
++  oid-valid
  |=  oid=@ux
  &(!=(0 oid) (lte (met 3 oid) 20))
::
++  begin
  |=  [base=@ux tip=@ux]
  ^-  search
  ?.  &((oid-valid base) (oid-valid tip))  [%invalid %object-oid]
  [%walking base ~[tip] ~ 1 32.768 67.108.864]
::
++  step
  |=  [work=search load=reader]
  ^-  search
  ?.  ?=(%walking -.work)  work
  ?~  todo.work  ?:(=(0 queued.work) [%diverged ~] [%invalid %queue-state])
  ?:  |(=(0 queued.work) (gth queued.work 32.768))  [%invalid %queue-state]
  ?:  |(=(0 steps.work) (gth steps.work 32.768))  [%invalid %ancestry-work-bound]
  ?:  (gth bytes.work 67.108.864)  [%invalid %ancestry-byte-bound]
  =/  oid  i.todo.work
  ?.  (oid-valid oid)  [%invalid %object-oid]
  =/  next  work(todo t.todo.work, queued (dec queued.work), steps (dec steps.work))
  ?:  (~(has in seen.work) oid)  next
  =/  value  (load oid)
  ?~  value  [%invalid %missing-commit]
  ?.  &(=(oid oid.u.value) =(%commit kind.u.value))  [%invalid %commit-kind]
  ?:  (gth length.body.u.value bytes.work)  [%invalid %ancestry-byte-bound]
  =/  parsed  (inspect:stead-code-git-graph u.value)
  ?:  ?=(%| -.parsed)  [%invalid p.parsed]
  ?.  ?=(%commit -.p.parsed)  [%invalid %commit-kind]
  ?:  =(oid base.work)  [%ancestor ~]
  =/  parents  (turn parents.p.parsed |=(child=edge:stead-code-git-graph oid.child))
  =/  queued=@ud  (add queued.next (lent parents))
  ?:  (gth queued 32.768)  [%invalid %ancestry-queue-bound]
  %=  next
    todo    (weld parents todo.next)
    seen    (~(put in seen.work) oid)
    queued  queued
    bytes   (sub bytes.work length.body.u.value)
  ==
--

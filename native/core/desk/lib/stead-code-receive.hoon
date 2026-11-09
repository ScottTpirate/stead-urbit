::  Pure candidate ref transaction for a validated Git receive.
::  The authoritative home supplies current policy and verified object facts.
/+  stead-code-git-objects
|%
+$  refs  (map @t @ux)
+$  update  [name=@t prior=@ux target=@ux]
+$  action  ?(%create %advance %delete)
+$  decision  (each refs @tas)
::
++  ancestor-ref
  |=  [name=@t namespace=refs]
  ^-  ?
  =/  width  (met 3 name)
  ?:  (gth width 1.024)  &
  =/  offset=@ud  1
  |-  ^-  ?
  ?:  (gte offset width)  |
  ?:  &(=(47 (cut 3 [offset 1] name)) (~(has by namespace) (cut 3 [0 offset] name)))
    &
  $(offset +(offset))
::
::  All decisions use the same current refs and authority epoch. An error
::  returns no candidate state. The caller commits refs, objects and receipt
::  in one home transition; neither this gate nor quarantine grants access.
++  decide
  |=  $:  current=refs  epoch=@ud  expected=@ud  changes=(list update)
          protected=(set @t)  authorize=$-([action update] ?)
          kind=$-(@ux (unit @tas))  descends=$-([@ux @ux] ?)
      ==
  ^-  decision
  ?:  |(=(0 epoch) !=(expected epoch))  [%| %stale-epoch]
  ?:  (gth ~(wyt by current) 256)  [%| %ref-bound]
  =/  candidate  current
  =/  seen=(set @t)  ~
  =/  count=@ud  0
  |-  ^-  decision
  ?~  changes
    ?:  =(0 count)  [%| %empty-update]
    ?:  (gth ~(wyt by candidate) 256)  [%| %ref-bound]
    ?.  (levy ~(tap by candidate) |=([name=@t oid=@ux] !(ancestor-ref name candidate)))
      [%| %ref-conflict]
    [%& candidate]
  ?:  =(32 count)  [%| %update-bound]
  =/  change  i.changes
  ?.  (valid-ref:stead-code-git-objects [(met 3 name.change) name.change])
    [%| %invalid-ref]
  =/  branch  =('refs/heads/' (cut 3 [0 11] name.change))
  =/  tag  =('refs/tags/' (cut 3 [0 10] name.change))
  ?.  |(branch tag)  [%| %unsupported-ref]
  ?:  |((gth (met 3 prior.change) 20) (gth (met 3 target.change) 20))
    [%| %invalid-oid]
  ?:  (~(has in seen) name.change)  [%| %duplicate-ref]
  ?:  =(prior.change target.change)  [%| %unchanged-ref]
  =/  intent=action
    ?:  =(0 prior.change)  %create
    ?:  =(0 target.change)  %delete
    %advance
  ?.  (authorize intent change)  [%| %denied]
  =/  observed  (fall (~(get by current) name.change) 0)
  ?.  =(prior.change observed)  [%| %stale-ref]
  ?:  =(%delete intent)
    ?:  (~(has in protected) name.change)  [%| %protected-ref]
    $(changes t.changes, candidate (~(del by candidate) name.change), seen (~(put in seen) name.change), count +(count))
  =/  object  (kind target.change)
  ?~  object  [%| %missing-object]
  ?:  &(branch !=(%commit u.object))  [%| %wrong-object-kind]
  ?.  ?=(?(%blob %tree %commit %tag) u.object)  [%| %wrong-object-kind]
  ?:  &(=(%advance intent) tag)  [%| %tag-replacement]
  ?:  &(=(%advance intent) !(descends prior.change target.change))  [%| %non-fast-forward]
  $(changes t.changes, candidate (~(put by candidate) name.change target.change), seen (~(put in seen) name.change), count +(count))
--

::  Pure quarantine reconstruction. A completed pack contains candidate
::  objects. The home still validates graph, custody, current policy and refs.
/+  stead-code-git-pack, stead-code-git-entry, stead-code-git-delta, stead-code-git-objects
|%
+$  octets  octets:stead-code-git-pack
+$  object  object:stead-code-git-objects
+$  objects  (map @ux object)
+$  inflater  $-([octets @ud @ud] (each [body=octets next=@ud] @tas))
+$  base-reader  $-(@ux (unit object))
+$  built  [item=object depth=@ud]
+$  delta  [at=@ud source=base:stead-code-git-entry patch=octets]
+$  staging
  $:  by-oid=(map @ux built)  by-offset=(map @ud (unit built))
      budget=@ud  checksum=@ux
  ==
+$  scan-state  [pack=octets cursor=@ud left=@ud store=staging pending=(list delta)]
+$  resolve-state  [store=staging ready=(list delta) retry=(list delta) progress=? round=@ud]
+$  job
  $%  [%scan data=scan-state]
      [%resolve data=resolve-state]
      [%complete items=objects checksum=@ux]
      [%rejected reason=@tas]
  ==
::
++  begin
  |=  pack=octets
  ^-  job
  =/  checked  (inspect:stead-code-git-pack pack)
  ?:  ?=(%invalid -.checked)  [%rejected reason.checked]
  [%scan pack 12 declared.checked [~ ~ 33.554.432 checksum.checked] ~]
::
++  insert
  |=  [store=staging at=@ud value=built]
  ^-  (each staging @tas)
  =/  prior  (~(get by by-oid.store) oid.item.value)
  ?:  &(?=(^ prior) !=(item.value item.u.prior))
    [%| %oid-collision]
  =/  selected=built
    ?~  prior  value
    ?:((lte depth.u.prior depth.value) u.prior value)
  [%& store(by-oid (~(put by by-oid.store) oid.item.value selected), by-offset (~(put by by-offset.store) at [~ value]))]
::
++  scan-one
  |=  [scan=scan-state inflate=inflater]
  ^-  job
  =/  end=@ud  (sub length.pack.scan 20)
  ?:  =(0 left.scan)
    ?.  =(cursor.scan end)  [%rejected %extra-entry-bytes]
    [%resolve store.scan (flop pending.scan) ~ | 1]
  =/  header  (decode:stead-code-git-entry pack.scan cursor.scan)
  ?:  ?=(%| -.header)  [%rejected p.header]
  =/  size=@ud  inflated.p.header
  ?:  (gth size budget.store.scan)  [%rejected %expansion-bound]
  =/  source  source.p.header
  ?:  &(?=([%offset *] source) !(~(has by by-offset.store.scan) at.source))
    [%rejected %base-boundary]
  =/  prefix=octets  [end (cut 3 [0 end] data.pack.scan)]
  =/  start=@ud  zlib-offset.p.header
  =/  expanded  (inflate prefix start size)
  ?:  ?=(%| -.expanded)  [%rejected p.expanded]
  =/  [body=octets next=@ud]  p.expanded
  ?.  &((gth next start) (lte next end) =(length.body size) (lte (met 3 data.body) size))
    [%rejected %inflated-boundary]
  =/  store=staging  store.scan(budget (sub budget.store.scan size))
  ?:  ?=(%none source)
    =/  kind=@tas
      ?+  kind.p.header  %invalid
        %1  %commit
        %2  %tree
        %3  %blob
        %4  %tag
      ==
    =/  direct  (hash-object:stead-code-git-objects kind body)
    ?~  direct  [%rejected %invalid-object]
    =/  added  (insert store cursor.scan [u.direct 0])
    ?:  ?=(%| -.added)  [%rejected p.added]
    [%scan scan(cursor next, left (dec left.scan), store p.added)]
  =.  by-offset.store  (~(put by by-offset.store) cursor.scan ~)
  [%scan scan(cursor next, left (dec left.scan), store store, pending [[cursor.scan source body] pending.scan])]
::
++  find-base
  |=  [store=staging source=base:stead-code-git-entry external=base-reader]
  ^-  (each (unit built) @tas)
  ?@  source  [%| %missing-delta-base]
  ?:  ?=(%offset -.source)
    =/  found  (~(get by by-offset.store) at.source)
    ?~  found  [%| %base-boundary]
    [%& u.found]
  =/  found  (~(get by by-oid.store) value.source)
  ?^  found  [%& found]
  =/  prior  (external value.source)
  ?~  prior  [%& ~]
  =/  checked  (hash-object:stead-code-git-objects kind.u.prior body.u.prior)
  ?~  checked  [%| %invalid-base]
  ?.  &(=(u.prior u.checked) =(oid.u.checked value.source))  [%| %invalid-base]
  [%& ~ u.checked 0]
::
++  resolve-one
  |=  [resolve=resolve-state external=base-reader]
  ^-  job
  ?~  ready.resolve
    ?~  retry.resolve
      =/  all  ~(tap by by-oid.store.resolve)
      =/  out=objects
        %-  malt
        (turn all |=([oid=@ux value=built] [oid item.value]))
      [%complete out checksum.store.resolve]
    ?.  progress.resolve  [%rejected %unresolved-base]
    ?:  =(32 round.resolve)  [%rejected %delta-depth]
    [%resolve resolve(ready (flop retry.resolve), retry ~, progress |, round +(round.resolve))]
  =/  entry  i.ready.resolve
  =/  base  (find-base store.resolve source.entry external)
  ?:  ?=(%| -.base)  [%rejected p.base]
  ?~  p.base
    [%resolve resolve(ready t.ready.resolve, retry [entry retry.resolve])]
  ?:  (gte depth.u.p.base 32)  [%rejected %delta-depth]
  =/  expanded
    (apply:stead-code-git-delta body.item.u.p.base patch.entry budget.store.resolve)
  ?:  ?=(%| -.expanded)  [%rejected p.expanded]
  =/  value  (hash-object:stead-code-git-objects kind.item.u.p.base p.expanded)
  ?~  value  [%rejected %invalid-object]
  =/  store  store.resolve(budget (sub budget.store.resolve length.p.expanded))
  =/  added  (insert store at.entry [u.value +(depth.u.p.base)])
  ?:  ?=(%| -.added)  [%rejected p.added]
  [%resolve resolve(store p.added, ready t.ready.resolve, progress &)]
::
::  Do one admitted scan or delta attempt. The caller owns durable scheduling
::  and can persist the tagged job value without storing executable gates.
++  step
  |=  [work=job inflate=inflater external=base-reader]
  ^-  job
  ?-  -.work
    %scan  (scan-one data.work inflate)
    %resolve  (resolve-one data.work external)
    %complete  work
    %rejected  work
  ==
--

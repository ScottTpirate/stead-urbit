::  Bounded stateless v0 fetch selection. No listener, policy or stored state.
::  Official Git pack-protocol and v2.55.0 upload-pack.c, get_common_commits.
::  Caller supplies CURRENT authorized advertised OIDs and a scoped loader.
/+  stead-git, stead-code-fetch-wire, stead-code-git-response, stead-code-git-graph, stead-code-git-emit
|%
+$  octets  octets:stead-git
+$  object  object:stead-git
+$  object-kind  object-kind:stead-code-git-graph
+$  edge  edge:stead-code-git-graph
+$  reader  reader:stead-code-git-graph
+$  request  request:stead-code-fetch-wire
+$  reachable  (map @ux object-kind)
+$  reply  [terminal=?(%round %done) body=octets object-count=@ud]
+$  result  (each reply @tas)
::  The duplicate HEAD/ref/peeled OID case is ordinary, but kinds must agree.
++  advertisement
  |=  tips=(list edge)
  ^-  (each reachable @tas)
  =/  known=reachable  ~
  =/  count=@ud  0
  |-  ^-  (each reachable @tas)
  ?~  tips  [%& known]
  ?:  =(512 count)  [%| %advertisement-bound]
  =/  tip  i.tips
  ?.  (oid-valid:stead-code-git-response oid.tip)  [%| %advertisement-oid]
  =/  previous  (~(get by known) oid.tip)
  ?:  &(?=(^ previous) !=(u.previous type.tip))  [%| %advertisement-kind]
  $(tips t.tips, count +(count), known (~(put by known) oid.tip type.tip))
::  Validate the complete decoded request before calling any object loader.
++  roots
  |=  [input=request advertised=reachable]
  ^-  (each (list edge) @tas)
  ?:  (gth (lent (scag 257 wants.input)) 256)  [%| %want-bound]
  ?:  (gth (lent (scag 1.025 haves.input)) 1.024)  [%| %have-bound]
  ?.  (levy haves.input oid-valid:stead-code-git-response)  [%| %have-oid]
  =/  pending=(list @ux)  wants.input
  =/  out=(list edge)  ~
  =/  seen=(set @ux)  ~
  |-  ^-  (each (list edge) @tas)
  ?~  pending
    ?~  out  [%| %missing-want]
    [%& (flop out)]
  ?.  (oid-valid:stead-code-git-response i.pending)  [%| %want-oid]
  =/  kind  (~(get by advertised) i.pending)
  ?~  kind  [%| %unadvertised-want]
  ?:  (~(has in seen) i.pending)  $(pending t.pending)
  $(pending t.pending, out [[i.pending u.kind] out], seen (~(put in seen) i.pending))
::  Internal closure state originates here, never from a client.
++  closure
  |=  [tips=(list edge) load=reader]
  ^-  (each reachable @tas)
  =/  work=closure:stead-code-git-graph  (start:stead-code-git-graph tips)
  =/  turns=@ud  65.537
  |-  ^-  (each reachable @tas)
  ?:  ?=(%invalid -.work)  [%| %unavailable]
  ?:  ?=(%verified -.work)  [%& reachable.work]
  ?:  =(0 turns)  [%| %graph-work-bound]
  $(work (walk:stead-code-git-graph work load), turns (dec turns))
::  Unknown or unrelated haves never trigger lookups or widen the wanted graph.
++  common
  |=  [claims=(list @ux) visible=reachable]
  ^-  (unit @ux)
  ?~  claims  ~
  ?:  (~(has by visible) i.claims)  [~ i.claims]
  $(claims t.claims)
::  Reload only verified wanted OIDs; require exact OID/type again. Emitter
::  rehashes bytes. Its 4,096-object / 8-MiB pack limits are the final budget.
++  inventory
  |=  [visible=reachable load=reader]
  ^-  (each (list object) @tas)
  ?:  (gth ~(wyt by visible) 4.096)  [%| %pack-object-bound]
  =/  pending=(list edge)  ~(tap by visible)
  =/  out=(list object)  ~
  |-  ^-  (each (list object) @tas)
  ?~  pending  [%& (flop out)]
  =/  tip  i.pending
  =/  item  (load oid.tip)
  ?~  item  [%| %unavailable]
  ?.  &(=(oid.tip oid.u.item) =(type.tip kind.u.item))  [%| %unavailable]
  $(pending t.pending, out [u.item out])
::  Full closure pack is intentional: haves select the basic ACK only, never
::  remove objects or authorize a thin-pack base. Each stateless POST is fresh.
++  respond
  |=  [input=request advertised=(list edge) load=reader]
  ^-  result
  =/  known  (advertisement advertised)
  ?:  ?=(%| -.known)  [%| p.known]
  =/  wanted  (roots input p.known)
  ?:  ?=(%| -.wanted)  [%| p.wanted]
  =/  graph  (closure p.wanted load)
  ?:  ?=(%| -.graph)  [%| p.graph]
  =/  mutual  (common haves.input p.graph)
  =/  answer=octets
    ?~  mutual  (packet:stead-code-git-response (cat 3 'NAK' 10))
    (packet:stead-code-git-response (rap 3 ~['ACK ' (oid-text:stead-git u.mutual) 10]))
  ?:  =(%round terminal.input)  [%& %round answer 0]
  =/  objects  (inventory p.graph load)
  ?:  ?=(%| -.objects)  [%| p.objects]
  =/  packed  (encode:stead-code-git-emit p.objects)
  ?:  ?=(%| -.packed)  [%| p.packed]
  [%& %done (append:stead-git answer p.packed) (lent p.objects)]
::  The raw-byte entry also checks the offered ofs-delta capability. This
::  encoder uses full stored entries regardless of that optional client flag.
++  from-wire
  |=  $:  body=octets  offered-offset-deltas=?
          advertised=(list edge)  load=reader
      ==
  ^-  result
  =/  decoded  (decode:stead-code-fetch-wire body offered-offset-deltas)
  ?:  ?=(%| -.decoded)  [%| p.decoded]
  (respond p.decoded advertised load)
--

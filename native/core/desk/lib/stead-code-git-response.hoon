::  Pure Smart HTTP v0 response bodies; no listener, policy or receipt owner.
::  Sources: git-scm.com/docs/http-protocol and /docs/pack-protocol.
::  Caller supplies only currently authorized refs and proven final outcomes.
::  Bounds: 256 refs, 32 outcomes, 1,024-byte refs, 128-byte error text.
::  HTTP Content-Type/cache headers and negotiated version remain caller duties.
/+  stead-git, stead-code-git-objects, stead-code-git-pkt
|%
+$  octets  octets:stead-git
+$  service  ?(%git-upload-pack %git-receive-pack)
+$  advertised-ref  [name=@t oid=@ux peeled=(unit @ux)]
+$  unpack-result  $%([%unpacked ~] [%failed reason=@t])
+$  outcome  $%([%committed ~] [%rejected reason=@t])
+$  ref-result  [name=@t result=outcome]
::  Internal formatting helpers are called only after admission below.
++  packet
  |=  text=@t
  ^-  octets
  (need (encode:stead-code-git-pkt %data [(met 3 text) text]))
++  oid-valid
  |=  oid=@ux
  ^-  ?
  &(!=(0 oid) (lte (met 3 oid) 20))
++  reason-valid
  |=  text=@t
  ^-  ?
  ?.  &((gte (met 3 text) 1) (lte (met 3 text) 128) !=('ok' text))  |
  (levy (trip text) |=([byte=@] &((gte byte 32) (lte byte 126))))
++  capability
  |=  [kind=service value=@t]
  ^-  ?
  ?:  =('ofs-delta' value)  &
  ?.  =(%git-receive-pack kind)  |
  |(=('report-status' value) =('delete-refs' value) =('atomic' value))
++  caps
  |=  [kind=service values=(list @t)]
  ^-  (each @t @tas)
  =/  out=@t  ''
  =/  seen=(set @t)  ~
  =/  count=@ud  0
  |-  ^-  (each @t @tas)
  ?~  values  ?:(=(0 count) [%| %capabilities-empty] [%& out])
  ?:  =(8 count)  [%| %capabilities-bound]
  ?.  (capability kind i.values)  [%| %unsupported-capability]
  ?:  (~(has in seen) i.values)  [%| %duplicate-capability]
  =/  text=@t  ?:(=(0 count) i.values (cat 3 (cat 3 out ' ') i.values))
  $(values t.values, out text, count +(count), seen (~(put in seen) i.values))
++  ref-line
  |=  [name=@t oid=@ux suffix=@t]
  ^-  octets
  (packet (rap 3 ~[(oid-text:stead-git oid) ' ' name suffix 10]))
::  Input order is explicit: HEAD, if present, first; then C byte ordering.
::  Caller MUST supply a verified peeled OID for each annotated tag.
::  Capabilities are caller-selected service commitments, never enabled here.
++  discovery
  |=  [kind=service refs=(list advertised-ref) capabilities=(list @t)]
  ^-  (each octets @tas)
  =/  accepted  (caps kind capabilities)
  ?:  ?=(%| -.accepted)  [%| p.accepted]
  =/  first-suffix=@t  (lsh [3 1] p.accepted)
  =/  banner  (packet (rap 3 ~['# service=' kind 10]))
  =/  out=octets  (append:stead-git banner [4 '0000'])
  =/  count=@ud  0
  =/  prior=@t  ''
  |-  ^-  (each octets @tas)
  ?~  refs
    ?:  =(0 count)
      =/  blank  (ref-line 'capabilities^{}' 0x0 first-suffix)
      [%& (append:stead-git (append:stead-git out blank) [4 '0000'])]
    [%& (append:stead-git out [4 '0000'])]
  ?:  =(256 count)  [%| %ref-bound]
  =/  ref  i.refs
  ?.  (oid-valid oid.ref)  [%| %oid-bound]
  ?:  =('HEAD' name.ref)
    ?.  &(=(0 count) ?=(~ peeled.ref))  [%| %head-position]
    =/  line  (ref-line name.ref oid.ref first-suffix)
    $(refs t.refs, count +(count), prior name.ref, out (append:stead-git out line))
  ?.  (valid-ref:stead-code-git-objects [(met 3 name.ref) name.ref])  [%| %invalid-ref]
  ?.  &(!=(prior name.ref) (aor prior name.ref))  [%| %ref-order]
  =/  line  (ref-line name.ref oid.ref ?:(=(0 count) first-suffix ''))
  =/  next=octets  (append:stead-git out line)
  ?~  peeled.ref
    $(refs t.refs, count +(count), prior name.ref, out next)
  ?.  =('refs/tags/' (cut 3 [0 10] name.ref))  [%| %peeled-ref]
  ?.  (oid-valid u.peeled.ref)  [%| %peeled-oid]
  =/  peeled  (ref-line (cat 3 name.ref '^{}') u.peeled.ref '')
  $(refs t.refs, count +(count), prior name.ref, out (append:stead-git next peeled))
::  Only call when negotiated report-status is in effect. A committed result
::  MUST come from the durable final home transition, never quarantine/proposal.
::  No pending outcome exists in this type. Failed unpack cannot report success.
++  report
  |=  [unpack=unpack-result outcomes=(list ref-result)]
  ^-  (each octets @tas)
  =/  unpack-text=@t
    ?:  ?=(%unpacked -.unpack)  'ok'
    reason.unpack
  ?:  &(?=(%failed -.unpack) !(reason-valid unpack-text))  [%| %invalid-reason]
  =/  out=octets  (packet (rap 3 ~['unpack ' unpack-text 10]))
  =/  count=@ud  0
  =/  seen=(set @t)  ~
  |-  ^-  (each octets @tas)
  ?~  outcomes
    ?:  =(0 count)  [%| %empty-outcomes]
    [%& (append:stead-git out [4 '0000'])]
  ?:  =(32 count)  [%| %outcome-bound]
  =/  item  i.outcomes
  ?.  (valid-ref:stead-code-git-objects [(met 3 name.item) name.item])  [%| %invalid-ref]
  ?:  (~(has in seen) name.item)  [%| %duplicate-ref]
  ?:  &(?=(%committed -.result.item) ?=(%failed -.unpack))  [%| %unpack-failed-success]
  ?:  &(?=(%rejected -.result.item) !(reason-valid reason.result.item))  [%| %invalid-reason]
  =/  line=@t
    ?:  ?=(%committed -.result.item)  (cat 3 'ok ' name.item)
    (rap 3 ~['ng ' name.item ' ' reason.result.item])
  $(outcomes t.outcomes, count +(count), seen (~(put in seen) name.item), out (append:stead-git out (packet (cat 3 line 10))))
--

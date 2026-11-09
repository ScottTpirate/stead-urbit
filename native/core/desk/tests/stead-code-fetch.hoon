/+  *test, stead-git, stead-code-git-objects, stead-code-git-pkt, stead-code-git-response, stead-code-fetch-wire, stead-code-git-graph, stead-code-git-emit, stead-code-fetch
=,  stead-code-fetch
|%
++  make
  |=  [kind=@tas data=@t]
  ^-  object
  (need (hash-object:stead-code-git-objects kind [(met 3 data) data]))
++  blob
  (make %blob 'abc')
++  secret
  (make %blob 'private sibling content')
++  tree
  =/  prefix=@t  '100644 file.txt'
  =/  width=@ud  +((met 3 prefix))
  =/  body=octets  [(add width 20) (can 3 ~[[width prefix] [20 (rev 3 20 oid:blob)]])]
  (need (hash-object:stead-code-git-objects %tree body))
++  first
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 'author Test <test@example.invalid> 1 +0000' 10 'committer Test <test@example.invalid> 1 +0000' 10 10 'first' 10]))
++  tip
  (make %commit (rap 3 ~['tree ' (oid-text:stead-git oid:tree) 10 'parent ' (oid-text:stead-git oid:first) 10 'author Test <test@example.invalid> 2 +0000' 10 'committer Test <test@example.invalid> 2 +0000' 10 10 'second' 10]))
++  tag
  (make %tag (rap 3 ~['object ' (oid-text:stead-git oid:tip) 10 'type commit' 10 'tag v1' 10 'tagger Test <test@example.invalid> 2 +0000' 10 10 'tag message' 10]))
++  view
  |=  oid=@ux
  ^-  (unit object)
  ?:  =(oid oid:blob)  [~ blob]
  ?:  =(oid oid:tree)  [~ tree]
  ?:  =(oid oid:first)  [~ first]
  ?:  =(oid oid:tip)  [~ tip]
  ?:  =(oid oid:tag)  [~ tag]
  ::  Any lookup outside the exact fixture closure is a test failure.
  !!
++  absent
  |=  oid=@ux
  ^-  (unit object)
  ~
++  corrupt
  |=  oid=@ux
  ^-  (unit object)
  ?:  =(oid oid:blob)  [~ %blob [4 'evil'] oid]
  (view oid)
++  mismatched
  |=  oid=@ux
  ^-  (unit object)
  [~ blob]
++  offer
  ^-  (list edge)
  ~[[oid:tip %commit] [oid:tag %tag]]
++  done
  ^-  request
  [~[oid:tip] ~ %done |]
++  round
  ^-  request
  [~[oid:tip] ~ %round |]
++  nak
  ^-  octets
  [8 0xa4b.414e.3830.3030]
++  ack
  |=  oid=@ux
  ^-  octets
  (packet:stead-code-git-response (rap 3 ~['ACK ' (oid-text:stead-git oid) 10]))
++  emitted
  |=  input=request
  ^-  reply
  =/  value  (respond input offer view)
  ?>  ?=(%& -.value)
  p.value
++  wire
  |=  terminal=@t
  ^-  octets
  =/  want  (packet:stead-code-git-response (rap 3 ~['want ' (oid-text:stead-git oid:tip) 10]))
  =/  end=octets
    ?:  =('done' terminal)  (packet:stead-code-git-response (cat 3 'done' 10))
    [4 '0000']
  (append:stead-git (append:stead-git want [4 '0000']) end)
++  visible-count
  |=  count=@ud
  ^-  reachable
  =/  out=reachable  ~
  |-  ^-  reachable
  ?:  =(0 count)  out
  =/  oid=@ux  (add count 0)
  $(count (dec count), out (~(put by out) oid %blob))
::  Raw native response bodies for an independent stock-Git index-pack oracle.
++  interoperability
  =/  value  (emitted [~[oid:tag] ~ %done |])
  body.value
++  interoperability-ack
  =/  value  (emitted [~[oid:tag] ~[oid:first] %done |])
  body.value
++  test-fetch-round-nak
  (expect !>(=([%& %round nak 0] (respond round offer view))))
++  test-fetch-round-ack
  (expect !>(=([%& %round (ack oid:first) 0] (respond [~[oid:tip] ~[oid:first] %round |] offer view))))
++  test-fetch-round-first-common
  (expect !>(=([%& %round (ack oid:first) 0] (respond [~[oid:tip] ~[0xdead oid:first oid:tip] %round |] offer view))))
++  test-fetch-round-unknown-have
  (expect !>(=([%& %round nak 0] (respond [~[oid:tip] ~[0xdead] %round |] offer view))))
++  test-fetch-round-private-have
  (expect !>(=([%& %round nak 0] (respond [~[oid:tip] ~[oid:secret] %round |] offer view))))
++  test-fetch-round-unwanted-advertised-have
  (expect !>(=([%& %round nak 0] (respond [~[oid:tip] ~[oid:secret] %round |] [[oid:secret %blob] offer] view))))
++  test-fetch-done-closure
  =/  value  (emitted done)
  (expect !>(&(=(%done terminal.value) =(4 object-count.value) =(data:nak (cut 3 [0 8] data.body.value)) =('PACK' (cut 3 [8 4] data.body.value)))))
++  test-fetch-done-tag-closure
  =/  value  (emitted [~[oid:tag] ~ %done |])
  (expect !>(=(5 object-count.value)))
++  test-fetch-done-ack
  =/  value  (emitted [~[oid:tip] ~[oid:first] %done |])
  =/  expected  (ack oid:first)
  (expect !>(&(=(4 object-count.value) =(data.expected (cut 3 [0 length.expected] data.body.value)) =('PACK' (cut 3 [length.expected 4] data.body.value)))))
++  test-fetch-duplicate-wants
  (expect !>(=((respond done offer view) (respond [~[oid:tip oid:tip] ~ %done |] offer view))))
++  test-fetch-offset-flag-preserves-pack
  (expect !>(=((respond done offer view) (respond [~[oid:tip] ~ %done &] offer view))))
++  test-fetch-private-have-preserves-pack
  (expect !>(=((respond done offer view) (respond [~[oid:tip] ~[oid:secret] %done |] offer view))))
++  test-fetch-unwanted-advertised-object-omitted
  (expect !>(=((respond done offer view) (respond done [[oid:secret %blob] offer] view))))
++  test-fetch-have-current-tip-full-pack
  =/  value  (emitted [~[oid:tip] ~[oid:tip] %done |])
  (expect !>(=(4 object-count.value)))
++  test-fetch-unadvertised-ancestor
  (expect !>(=([%| %unadvertised-want] (respond [~[oid:first] ~ %done |] offer view))))
++  test-fetch-unadvertised-reachable-blob
  (expect !>(=([%| %unadvertised-want] (respond [~[oid:blob] ~ %done |] offer view))))
++  test-fetch-unadvertised-private
  (expect !>(=([%| %unadvertised-want] (respond [~[oid:secret] ~ %done |] offer view))))
++  test-fetch-revoked-current-advertisement
  (expect !>(=([%| %unadvertised-want] (respond done ~ view))))
++  test-fetch-mixed-wants-denied
  (expect !>(=([%| %unadvertised-want] (respond [~[oid:tip oid:secret] ~ %done |] offer view))))
++  test-fetch-missing-want
  (expect !>(=([%| %missing-want] (respond [~ ~ %round |] offer view))))
++  test-fetch-zero-want
  (expect !>(=([%| %want-oid] (respond [~[0x0] ~ %done |] offer view))))
++  test-fetch-wide-want
  (expect !>(=([%| %want-oid] (respond [~[(bex 160)] ~ %done |] offer view))))
++  test-fetch-zero-have
  (expect !>(=([%| %have-oid] (respond [~[oid:tip] ~[0x0] %round |] offer view))))
++  test-fetch-wide-have
  (expect !>(=([%| %have-oid] (respond [~[oid:tip] ~[(bex 160)] %round |] offer view))))
++  test-fetch-want-count-over
  (expect !>(=([%| %want-bound] (respond [(reap 257 oid:tip) ~ %done |] offer view))))
++  test-fetch-have-count-over
  (expect !>(=([%| %have-bound] (respond [~[oid:tip] (reap 1.025 0x1) %round |] offer view))))
++  test-fetch-advertisement-count-over
  (expect !>(=([%| %advertisement-bound] (respond done (reap 513 [oid:tip %commit]) view))))
++  test-fetch-advertisement-zero
  (expect !>(=([%| %advertisement-oid] (respond done ~[[0x0 %commit]] view))))
++  test-fetch-advertisement-wide
  (expect !>(=([%| %advertisement-oid] (respond done ~[[(bex 160) %commit]] view))))
++  test-fetch-advertisement-conflicting-kind
  (expect !>(=([%| %advertisement-kind] (respond done ~[[oid:tip %commit] [oid:tip %blob]] view))))
++  test-fetch-advertisement-wrong-kind
  (expect !>(=([%| %unavailable] (respond done ~[[oid:tip %blob]] view))))
++  test-fetch-missing-object
  (expect !>(=([%| %unavailable] (respond done offer absent))))
++  test-fetch-corrupt-object
  (expect !>(=([%| %unavailable] (respond done offer corrupt))))
++  test-fetch-mismatched-loader
  (expect !>(=([%| %unavailable] (respond done offer mismatched))))
++  test-fetch-want-count-at
  (expect !>(=([%& %round nak 0] (respond [(reap 256 oid:tip) ~ %round |] offer view))))
++  test-fetch-have-count-at
  (expect !>(=([%& %round nak 0] (respond [~[oid:tip] (reap 1.024 0x1) %round |] offer view))))
++  test-fetch-advertisement-count-at
  (expect !>(=([%& %round nak 0] (respond round (reap 512 [oid:tip %commit]) view))))
++  test-fetch-inventory-object-bound
  (expect !>(=([%| %pack-object-bound] (inventory (visible-count 4.097) view))))
++  test-fetch-wire-round
  (expect !>(=([%& %round nak 0] (from-wire (wire 'round') | offer view))))
++  test-fetch-wire-done
  (expect !>(=((respond done offer view) (from-wire (wire 'done') | offer view))))
++  test-fetch-wire-malformed
  (expect !>(=([%| %truncated-request] (from-wire [0 0] | offer view))))
++  test-fetch-wire-unadvertised-capability
  =/  first  (packet:stead-code-git-response (rap 3 ~['want ' (oid-text:stead-git oid:tip) ' ofs-delta' 10]))
  =/  input  (append:stead-git (append:stead-git first [4 '0000']) (packet:stead-code-git-response (cat 3 'done' 10)))
  (expect !>(=([%| %unadvertised-capability] (from-wire input | offer view))))
++  test-fetch-done-blob-golden
  (expect !>(=([%& %done [55 0x53.aa97.6a94.c0cd.ed4d.68c0.7006.1356.07b2.105d.1527.014d.0263.6261.fffc.0003.0101.7833.0100.0000.0200.0000.4b43.4150.0a4b.414e.3830.3030] 1] (respond [~[oid:blob] ~ %done |] ~[[oid:blob %blob]] view))))
++  failure-control
  (expect !>(%.n))
--

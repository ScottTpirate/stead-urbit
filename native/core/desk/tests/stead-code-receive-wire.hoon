/+  *test, stead-code-git-pkt, stead-code-receive-wire
::  Pure command framing only. Pack validity and authority remain separate.
|%
++  offered
  ^-  (set @t)
  (silt ~['report-status' 'delete-refs' 'atomic' 'ofs-delta' 'object-format=sha1' 'agent'])
++  bytes
  |=  text=@t
  ^-  octets:stead-code-receive-wire
  [(met 3 text) text]
++  join
  |=  [left=octets:stead-code-receive-wire right=octets:stead-code-receive-wire]
  ^-  octets:stead-code-receive-wire
  [(add length.left length.right) (mix data.left (lsh [3 length.left] data.right))]
++  packet
  |=  body=octets:stead-code-receive-wire
  ^-  octets:stead-code-receive-wire
  (need (encode:stead-code-git-pkt %data body))
++  line
  |=  name=@t
  ^-  octets:stead-code-receive-wire
  (bytes (cat 3 '0000000000000000000000000000000000000000 1111111111111111111111111111111111111111 ' name))
++  first
  |=  [name=@t caps=@t]
  ^-  octets:stead-code-receive-wire
  (packet (join (join (line name) [1 0]) (bytes caps)))
++  finish
  |=  input=octets:stead-code-receive-wire
  ^-  octets:stead-code-receive-wire
  (join input [4 '0000'])
++  repeated
  |=  [count=@ud byte=@ud]
  ^-  octets:stead-code-receive-wire
  =/  out=octets:stead-code-receive-wire  [0 0]
  |-  ^-  octets:stead-code-receive-wire
  ?:  =(0 count)  out
  $(count (dec count), out (join out [1 byte]))
++  valid
  ^-  octets:stead-code-receive-wire
  (finish (first 'refs/heads/main' 'report-status atomic object-format=sha1 agent=git/2.55.0'))
++  denied
  |=  [wire=octets:stead-code-receive-wire reason=@tas]
  ^-  tang
  (expect !>(=([%| reason] (decode:stead-code-receive-wire wire offered))))
++  many
  |=  total=@ud
  ^-  octets:stead-code-receive-wire
  =/  count=@ud  0
  =/  out=octets:stead-code-receive-wire  [0 0]
  |-  ^-  octets:stead-code-receive-wire
  ?:  =(count total)  (finish out)
  =/  name=@t  (cat 3 'refs/heads/r' (scot %ud count))
  =/  next  ?:(=(0 count) (first name '') (packet (line name)))
  $(count +(count), out (join out next))
++  test-receive-wire-create
  =/  wire  valid
  =/  parsed  (decode:stead-code-receive-wire wire offered)
  ?>  ?=([%& *] parsed)
  =/  expected  0x1111.1111.1111.1111.1111.1111.1111.1111.1111.1111
  =/  correct=?
    ?&  =(~[['refs/heads/main' 0x0 expected]] changes.p.parsed)
        =(length.wire pack-offset.p.parsed)
        =((silt ~['report-status' 'atomic' 'object-format=sha1' 'agent=git/2.55.0']) capabilities.p.parsed)
    ==
  (expect !>(correct))
++  test-receive-wire-stock-leading-space
  =/  wire  (finish (first 'refs/heads/main' ' report-status atomic'))
  =/  parsed  (decode:stead-code-receive-wire wire offered)
  ?>  ?=([%& *] parsed)
  (expect !>(&((=(length.wire pack-offset.p.parsed)) =((silt ~['report-status' 'atomic']) capabilities.p.parsed))))
++  test-receive-wire-double-leading-space
  (denied (finish (first 'refs/heads/main' '  report-status atomic')) %capability-bound)
++  test-receive-wire-empty-capabilities
  =/  parsed  (decode:stead-code-receive-wire (finish (first 'refs/heads/main' '')) ~)
  (expect !>(?=([%& *] parsed)))
++  test-receive-wire-command-order
  =/  wire  (finish (join (first 'refs/heads/one' '') (packet (line 'refs/tags/two'))))
  =/  parsed  (decode:stead-code-receive-wire wire offered)
  ?>  ?=([%& *] parsed)
  (expect !>(=(~['refs/heads/one' 'refs/tags/two'] (turn changes.p.parsed |=(change=update:stead-code-receive-wire name.change)))))
++  test-receive-wire-final-lf
  =/  first-body  (join (join (line 'refs/heads/main') [1 0]) (bytes 'report-status'))
  =/  wire  (finish (join (packet (join first-body [1 10])) (packet (join (line 'refs/tags/v1') [1 10]))))
  =/  parsed  (decode:stead-code-receive-wire wire offered)
  (expect !>(?=([%& *] parsed)))
++  test-receive-wire-pack-is-opaque
  =/  wire  (join valid [8 'PACK'])
  =/  parsed  (decode:stead-code-receive-wire wire offered)
  ?>  ?=([%& *] parsed)
  =/  offset  pack-offset.p.parsed
  (expect !>(=([8 'PACK'] [(sub length.wire offset) (rsh [3 offset] data.wire)])))
++  test-receive-wire-large-tail-bypasses-pkt-buffer-limit
  =/  command-block  valid
  =/  wire  (join command-block [8.388.608 'PACK'])
  =/  parsed  (decode:stead-code-receive-wire wire offered)
  ?>  ?=([%& *] parsed)
  (expect !>(=(length.command-block pack-offset.p.parsed)))
++  test-receive-wire-pack-bound
  (denied (join valid [8.388.609 0]) %pack-bound)
++  test-receive-wire-buffer-bound
  (denied [8.454.145 0] %buffer-bound)
++  test-receive-wire-buffer-width
  (denied [0 1] %buffer-bound)
++  test-receive-wire-empty
  (denied [4 '0000'] %empty-command-block)
++  test-receive-wire-truncated-header
  (denied [3 '000'] %truncated-command-block)
++  test-receive-wire-truncated-payload
  (denied [8 '0070abcd'] %truncated-command-block)
++  test-receive-wire-missing-flush
  (denied (first 'refs/heads/main' '') %truncated-command-block)
++  test-receive-wire-invalid-header
  (denied [4 '000g'] %header-hex)
++  test-receive-wire-delimiter
  (denied [4 '0001'] %unexpected-control)
++  test-receive-wire-response-end
  (denied [4 '0002'] %unexpected-control)
++  test-receive-wire-first-nul-required
  (denied (finish (packet (line 'refs/heads/main'))) %missing-capabilities)
++  test-receive-wire-later-nul-forbidden
  (denied (finish (join (first 'refs/heads/main' '') (first 'refs/heads/other' 'atomic'))) %unexpected-capabilities)
++  test-receive-wire-duplicate-ref
  (denied (finish (join (first 'refs/heads/main' '') (packet (line 'refs/heads/main')))) %duplicate-ref)
++  test-receive-wire-invalid-ref
  (denied (finish (first 'refs/heads/a..b' '')) %invalid-ref)
++  test-receive-wire-unsupported-ref
  (denied (finish (first 'refs/notes/main' '')) %unsupported-ref)
++  test-receive-wire-uppercase-oid
  =/  bad  (bytes 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA 1111111111111111111111111111111111111111 refs/heads/main')
  (denied (finish (packet (join bad [1 0]))) %invalid-oid)
++  test-receive-wire-command-spacing
  =/  bad  (bytes '0000000000000000000000000000000000000000X1111111111111111111111111111111111111111 refs/heads/main')
  (denied (finish (packet (join bad [1 0]))) %command-spacing)
++  test-receive-wire-unknown-capability
  (denied (finish (first 'refs/heads/main' 'mystery')) %unsupported-capability)
++  test-receive-wire-unsupported-sha256
  (denied (finish (first 'refs/heads/main' 'object-format=sha256')) %unsupported-capability)
++  test-receive-wire-push-options-unsupported
  (denied (finish (first 'refs/heads/main' 'push-options')) %unsupported-capability)
++  test-receive-wire-unadvertised-capability
  (expect !>(=([%| %unadvertised-capability] (decode:stead-code-receive-wire (finish (first 'refs/heads/main' 'atomic')) ~))))
++  test-receive-wire-duplicate-capability
  (denied (finish (first 'refs/heads/main' 'atomic atomic')) %duplicate-capability)
++  test-receive-wire-duplicate-agent-key
  (denied (finish (first 'refs/heads/main' 'agent=one agent=two')) %duplicate-capability)
++  test-receive-wire-capability-whitespace
  (denied (finish (first 'refs/heads/main' 'atomic  report-status')) %capability-bound)
++  test-receive-wire-capability-nul
  =/  body  (join (join (line 'refs/heads/main') [1 0]) (join (bytes 'atomic') [1 0]))
  (denied (finish (packet body)) %capability-byte)
++  test-receive-wire-command-count-at-bound
  =/  parsed  (decode:stead-code-receive-wire (many 32) offered)
  ?>  ?=([%& *] parsed)
  (expect !>(=(32 (lent changes.p.parsed))))
++  test-receive-wire-command-count-over-bound
  (denied (many 33) %update-bound)
++  test-receive-wire-delete-advertisement
  =/  body  (bytes '1111111111111111111111111111111111111111 0000000000000000000000000000000000000000 refs/heads/main')
  =/  wire  (finish (packet (join body [1 0])))
  =/  allowed  (decode:stead-code-receive-wire wire offered)
  (expect !>(&(?=([%& *] allowed) =([%| %delete-not-advertised] (decode:stead-code-receive-wire wire ~)))))
++  test-receive-wire-advertisement-profile
  (expect !>(=([%| %unsupported-advertisement] (decode:stead-code-receive-wire valid (silt ~['push-options'])))))
++  test-receive-wire-advertisement-bound
  (expect !>(=([%| %advertisement-bound] (decode:stead-code-receive-wire valid (~(put in offered) 'extra')))))
++  test-receive-wire-header-bound
  (denied (join (first 'refs/heads/main' '') [4 'fff0']) %header-bound)
++  test-receive-wire-capability-block-bound
  (expect !>(=([%| %capability-bound] (parse-capabilities:stead-code-receive-wire [1.025 0] offered))))
++  test-receive-wire-agent-at-token-bound
  =/  tail  (repeated 122 97)
  =/  caps=@t  (cat 3 'agent=' data.tail)
  =/  parsed  (decode:stead-code-receive-wire (finish (first 'refs/heads/main' caps)) offered)
  (expect !>(?=([%& *] parsed)))
++  test-receive-wire-agent-over-token-bound
  =/  tail  (repeated 123 97)
  (denied (finish (first 'refs/heads/main' (cat 3 'agent=' data.tail))) %capability-bound)
++  test-receive-wire-ref-at-bound
  =/  tail  (repeated 1.013 114)
  =/  name=@t  (cat 3 'refs/heads/' data.tail)
  =/  parsed  (decode:stead-code-receive-wire (finish (first name '')) offered)
  (expect !>(?=([%& *] parsed)))
++  test-receive-wire-ref-over-bound
  =/  tail  (repeated 1.014 114)
  (denied (finish (first (cat 3 'refs/heads/' data.tail) '')) %invalid-ref)
++  test-receive-wire-command-payload-bound
  (denied (packet [2.133 0]) %command-bound)
++  test-receive-wire-shallow-unsupported
  (denied (finish (packet (bytes 'shallow 1111111111111111111111111111111111111111'))) %command-bound)
++  test-receive-wire-signed-push-unsupported
  (denied (finish (packet (join (bytes 'push-cert') [1 0]))) %command-bound)
++  failure-control
  (expect !>(%.n))
--

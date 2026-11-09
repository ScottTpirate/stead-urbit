::  Original bounded SHA-1 receive-pack command-block parser.
::  No transport, identity, pack validation, ref acceptance or response claim.
/+  stead-code-git-pkt, stead-code-git-objects, stead-code-receive
|%
+$  octets  octets:stead-code-git-pkt
+$  update  update:stead-code-receive
+$  header
  $:  changes=(list update:stead-code-receive)
      pack-offset=@ud
      capabilities=(set @t)
  ==
+$  result  (each header @tas)
+$  line-result
  (each [change=update:stead-code-receive capabilities=(set @t)] @tas)
::  The advertised profile uses exact names, except the informational agent
::  key. Client agent text is returned intact, never used as an identity.
++  offered-name
  |=  name=@t
  ^-  ?
  ?|  =('report-status' name)  =('delete-refs' name)  =('atomic' name)
      =('ofs-delta' name)  =('object-format=sha1' name)  =('agent' name)
  ==
++  capability-key
  |=  token=@t
  ^-  (unit @t)
  ?:  &((offered-name token) !=('agent' token))  [~ token]
  ?:  &((gth (met 3 token) 6) =('agent=' (cut 3 [0 6] token)))
    [~ 'agent']
  ~
::  At most 1,024 bytes, eight tokens, 128 bytes per printable-ASCII token.
::  Duplicate capability keys, whitespace variants and unknown keys fail.
++  parse-capabilities
  |=  [value=octets offered=(set @t)]
  ^-  (each (set @t) @tas)
  ?.  (valid-octets:stead-code-git-pkt value 1.024)
    [%| %capability-bound]
  ?:  =(0 length.value)  [%& ~]
  =/  index=@ud  0
  =/  start=@ud  0
  =/  count=@ud  0
  =/  seen=(set @t)  ~
  =/  accepted=(set @t)  ~
  |-  ^-  (each (set @t) @tas)
  =/  terminal=?  =(index length.value)
  =/  byte=@ud  ?:(terminal 32 (cut 3 [index 1] data.value))
  ?:  =(32 byte)
    =/  width=@ud  (sub index start)
    ?:  |(=(0 width) (gth width 128) =(8 count))
      [%| %capability-bound]
    =/  token=@t  (cut 3 [start width] data.value)
    =/  key  (capability-key token)
    ?~  key  [%| %unsupported-capability]
    ?.  (~(has in offered) u.key)  [%| %unadvertised-capability]
    ?:  (~(has in seen) u.key)  [%| %duplicate-capability]
    =/  next  (~(put in accepted) token)
    ?:  terminal  [%& next]
    $(index +(index), start +(index), count +(count), seen (~(put in seen) u.key), accepted next)
  ?.  &((gte byte 33) (lte byte 126))  [%| %capability-byte]
  ?:  (gte (sub index start) 128)  [%| %capability-bound]
  $(index +(index))
::  Exactly two lowercase 40-digit OIDs separated by single spaces.
::  Only the first command has NUL + capabilities. One final LF is accepted;
::  no ref, capability or OID bytes are otherwise normalized.
++  parse-line
  |=  [body=octets first=? offered=(set @t)]
  ^-  line-result
  ?.  (valid-octets:stead-code-git-pkt body 2.132)
    [%| %command-bound]
  ?:  (lth length.body 88)  [%| %command-bound]
  =/  width=@ud
    (sub length.body ?:(=(10 (cut 3 [(dec length.body) 1] data.body)) 1 0))
  ?.  &(=(32 (cut 3 [40 1] data.body)) =(32 (cut 3 [81 1] data.body)))
    [%| %command-spacing]
  =/  prior  (parse-oid:stead-code-git-objects [40 (cut 3 [0 40] data.body)])
  =/  target  (parse-oid:stead-code-git-objects [40 (cut 3 [41 40] data.body)])
  ?~  prior  [%| %invalid-oid]
  ?~  target  [%| %invalid-oid]
  =/  index=@ud  82
  |-  ^-  line-result
  =/  terminal=?  =(index width)
  =/  nul=?  &(!terminal =(0 (cut 3 [index 1] data.body)))
  ?:  |(terminal nul)
    ?:  &(first terminal)  [%| %missing-capabilities]
    ?:  &(!first nul)  [%| %unexpected-capabilities]
    =/  ref=octets  [(sub index 82) (cut 3 [82 (sub index 82)] data.body)]
    ?.  (valid-ref:stead-code-git-objects ref)  [%| %invalid-ref]
    =/  name=@t  data.ref
    ?.  |(=('refs/heads/' (cut 3 [0 11] name)) =('refs/tags/' (cut 3 [0 10] name)))
      [%| %unsupported-ref]
    ?:  &(=(0 u.target) !(~(has in offered) 'delete-refs'))
      [%| %delete-not-advertised]
    =/  requested=(each (set @t) @tas)
      ?:  !first  [%& ~]
      =/  begin=@ud  +(index)
      (parse-capabilities [(sub width begin) (cut 3 [begin (sub width begin)] data.body)] offered)
    ?-  -.requested
      %|  [%| p.requested]
      %&  [%& [name u.prior u.target] p.requested]
    ==
  ?:  (gte (sub index 82) 1.024)  [%| %invalid-ref]
  $(index +(index))
::  The caller retains the original buffer. Only its first 64 KiB are framed;
::  pack-offset addresses untouched bytes in that original, including zeroes.
::  At most 32 commands and 8 MiB of opaque pack bytes follow the header.
++  decode
  |=  [buffer=octets offered=(set @t)]
  ^-  result
  ?.  (valid-octets:stead-code-git-pkt buffer 8.454.144)
    [%| %buffer-bound]
  ?:  (gth ~(wyt in offered) 6)  [%| %advertisement-bound]
  ?.  (levy ~(tap in offered) offered-name)  [%| %unsupported-advertisement]
  =/  width=@ud  (min length.buffer 65.536)
  =/  prefix=octets  [width (cut 3 [0 width] data.buffer)]
  =/  offset=@ud  0
  =/  count=@ud  0
  =/  changes=(list update:stead-code-receive)  ~
  =/  capabilities=(set @t)  ~
  =/  seen=(set @t)  ~
  |-  ^-  result
  =/  packet  (decode:stead-code-git-pkt prefix offset)
  ?-  -.packet
    %invalid  [%| reason.packet]
    %need
      ?:  (gth (add offset required.packet) 65.536)  [%| %header-bound]
      [%| %truncated-command-block]
    %ready
      ?:  =(%flush kind.packet)
        ?:  =(0 count)  [%| %empty-command-block]
        ?:  (gth (sub length.buffer next.packet) 8.388.608)  [%| %pack-bound]
        [%& (flop changes) next.packet capabilities]
      ?.  =(%data kind.packet)  [%| %unexpected-control]
      ?:  =(32 count)  [%| %update-bound]
      =/  line  (parse-line body.packet =(0 count) offered)
      ?-  -.line
        %|  [%| p.line]
        %&
          ?:  (~(has in seen) name.change.p.line)  [%| %duplicate-ref]
          $(offset next.packet, count +(count), changes [change.p.line changes], seen (~(put in seen) name.change.p.line), capabilities ?:(=(0 count) capabilities.p.line capabilities))
      ==
  ==
--

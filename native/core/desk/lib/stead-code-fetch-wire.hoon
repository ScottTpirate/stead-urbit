::  A complete stateless v0 upload-pack request in the bounded SHA-1 profile.
::  Want/have OIDs are untrusted claims; the home authorizes them separately.
/+  stead-code-git-pkt, stead-code-git-objects
|%
+$  octets  octets:stead-code-git-pkt
+$  request
  $:  wants=(list @ux)
      haves=(list @ux)
      terminal=?(%round %done)
      offset-deltas=?
  ==
+$  result  (each request @tas)
::
++  line-oid
  |=  data=@
  ^-  (unit @ux)
  =/  hex=@t  (crip (cass (trip (cut 3 [5 40] data))))
  =/  oid  (parse-oid:stead-code-git-objects [40 hex])
  ?~  oid  ~
  ?:(=(0 u.oid) ~ oid)
::
++  decode
  |=  [buffer=octets offered-offset-deltas=?]
  ^-  result
  ?.  (valid-octets:stead-code-git-pkt buffer 65.536)
    [%| %buffer-bound]
  =/  phase=?(%wants %haves)  %wants
  =/  offset=@ud  0
  =/  wants=(list @ux)  ~
  =/  haves=(list @ux)  ~
  =/  want-count=@ud  0
  =/  have-count=@ud  0
  =/  offset-deltas=?  |
  |-  ^-  result
  =/  frame  (decode:stead-code-git-pkt buffer offset)
  ?:  ?=(%invalid -.frame)  [%| reason.frame]
  ?:  ?=(%need -.frame)  [%| %truncated-request]
  ?:  =(%flush kind.frame)
    ?:  =(%wants phase)
      ?:  =(0 want-count)  [%| %missing-want]
      $(phase %haves, offset next.frame)
    ?.  =(next.frame length.buffer)  [%| %trailing-request]
    [%& (flop wants) (flop haves) %round offset-deltas]
  ?.  =(%data kind.frame)  [%| %unexpected-control]
  =/  body  body.frame
  ?:  =(0 length.body)  [%| %command-width]
  =/  width=@ud
    (sub length.body ?:(=(10 (cut 3 [(dec length.body) 1] data.body)) 1 0))
  =/  data=@  (cut 3 [0 width] data.body)
  ?:  &(=(4 width) =('done' data))
    ?.  =(%haves phase)  [%| %unexpected-done]
    ?.  =(next.frame length.buffer)  [%| %trailing-request]
    [%& (flop wants) (flop haves) %done offset-deltas]
  =/  command=@t  (cut 3 [0 5] data)
  ?.  |(=('want ' command) =('have ' command))  [%| %unsupported-command]
  ?:  (lth width 45)  [%| %command-width]
  =/  oid  (line-oid data)
  ?~  oid  [%| %invalid-oid]
  ?:  =(%haves phase)
    ?.  =('have ' command)  [%| %unexpected-want]
    ?.  =(45 width)  [%| %command-width]
    ?:  =(1.024 have-count)  [%| %have-bound]
    $(offset next.frame, haves [u.oid haves], have-count +(have-count))
  ?.  =('want ' command)  [%| %unexpected-have]
  ?:  =(256 want-count)  [%| %want-bound]
  ?:  =(45 width)
    $(offset next.frame, wants [u.oid wants], want-count +(want-count))
  ?.  &(=(55 width) =(' ofs-delta' (cut 3 [45 10] data)) =(0 want-count))
    [%| %unsupported-capability]
  ?.  offered-offset-deltas  [%| %unadvertised-capability]
  $(offset next.frame, wants [u.oid wants], want-count +(want-count), offset-deltas &)
--

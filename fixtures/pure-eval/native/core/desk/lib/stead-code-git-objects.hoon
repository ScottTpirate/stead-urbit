::  Original pure code-Git byte helpers. No graph validation or acceptance.
::  Reuses the already implemented exact-byte SHA-1 document constructors.
/+  stead-git
|%
+$  octets  octets:stead-git
+$  object  object:stead-git
::  Compute the canonical OID without changing body bytes or author text.
::  A successful hash is not proof that a tree/commit/tag body is well formed.
++  hash-object
  |=  [kind=@tas body=octets]
  ^-  (unit object)
  ?.  (valid-octets:stead-git body)  ~
  ?.  ?|  =(%blob kind)  =(%tree kind)  =(%commit kind)  =(%tag kind)
      ==
    ~
  ?.  =(%tag kind)  [~ (make-object:stead-git kind body)]
  =/  header=@t  (cat 3 'tag ' (decimal:stead-git length.body))
  =/  raw=octets  (append:stead-git [(add 1 (met 3 header)) header] body)
  [~ kind body (sha-1l:sha [length.raw (rev 3 length.raw data.raw)])]
::  Protocol SHA-1 spelling. Zero is parsed, but remains a create/delete
::  sentinel at the later ref-command layer; it is not an existing object.
++  parse-oid
  |=  text=octets
  ^-  (unit @ux)
  ?.  &(=(40 length.text) (lte (met 3 data.text) 40))  ~
  =/  index=@ud  0
  =/  result=@ux  0x0
  |-  ^-  (unit @ux)
  ?:  =(40 index)  [~ result]
  =/  byte=@ud  (cut 3 [index 1] data.text)
  =/  digit=(unit @ud)
    ?:  &((gte byte 48) (lte byte 57))  [~ (sub byte 48)]
    ?:  &((gte byte 97) (lte byte 102))  [~ (add 10 (sub byte 97))]
    ~
  ?~  digit  ~
  $(index +(index), result (add (mul result 16) u.digit))
::  Full refs/ names only, at most 1,024 bytes. No case folding, Unicode,
::  path or slash normalization. HEAD belongs to a future symbolic-ref layer.
++  valid-ref
  |=  name=octets
  ^-  ?
  ?.  ?&  (gte length.name 6)
          (lte length.name 1.024)
          (lte (met 3 data.name) length.name)
          =('refs/' (cut 3 [0 5] data.name))
      ==
    %.n
  ?:  =(46 (cut 3 [(dec length.name) 1] data.name))  %.n
  =/  index=@ud  0
  =/  start=@ud  0
  =/  previous=@ud  0
  |-  ^-  ?
  ?:  =(index length.name)
    ?.  (gth index start)  %.n
    ?.  (gte (sub index start) 5)  %.y
    !=('.lock' (cut 3 [(sub index 5) 5] data.name))
  =/  byte=@ud  (cut 3 [index 1] data.name)
  ?:  ?|  (lte byte 32)  =(byte 127)  =(byte 126)  =(byte 94)
          =(byte 58)  =(byte 63)  =(byte 42)  =(byte 91)  =(byte 92)
          &(=(byte 46) =(previous 46))
          &(=(byte 123) =(previous 64))
          &(=(index start) =(byte 46))
      ==
    %.n
  ?:  =(47 byte)
    ?.  (gth index start)  %.n
    ?:  &((gte (sub index start) 5) =('.lock' (cut 3 [(sub index 5) 5] data.name)))  %.n
    $(index +(index), start +(index), previous byte)
  $(index +(index), previous byte)
--

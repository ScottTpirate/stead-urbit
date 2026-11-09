::  Original Git pkt-line framing. Pure bytes, no authority or transport.
::  See CODE_GIT_PACKET_PROFILE.md before connecting an untrusted input.
|%
+$  octets  [length=@ud data=@]
+$  packet-kind  ?(%data %flush %delim %response-end)
+$  decoded
  $%  [%ready kind=packet-kind body=octets next=@ud]
      [%need required=@ud]
      [%invalid reason=@tas]
  ==
::
++  valid-octets
  |=  [value=octets limit=@ud]
  ^-  ?
  ?&  (lte length.value limit)
      (lte (met 3 data.value) length.value)
  ==
::  Four lower-case hex digits, including leading zeroes.
++  hex-four
  |=  value=@ud
  ^-  @t
  ?>  (lte value 65.535)
  =/  count=@ud  4
  =/  digits=tape  ~
  |-  ^-  @t
  ?:  =(0 count)  (crip digits)
  $(count (dec count), value (div value 16), digits [(snag (mod value 16) "0123456789abcdef") digits])
::
++  encode
  |=  [kind=packet-kind body=octets]
  ^-  (unit octets)
  ?.  (valid-octets body 65.516)  ~
  ?:  =(%data kind)
    =/  width=@ud  (add 4 length.body)
    [~ width (mix (hex-four width) (lsh [3 4] data.body))]
  ?.  =([0 0] body)  ~
  [~ 4 ?:(=(%flush kind) '0000' ?:(=(%delim kind) '0001' '0002'))]
::  Offset addresses the next header in a bounded caller-owned input buffer.
::  Incomplete input reports required bytes from offset, not a new allocation.
++  decode
  |=  [buffer=octets offset=@ud]
  ^-  decoded
  ?.  (valid-octets buffer 1.048.576)  [%invalid %buffer-bound]
  ?:  (gth offset length.buffer)  [%invalid %offset-bound]
  =/  available=@ud  (sub length.buffer offset)
  ?:  (lth available 4)  [%need 4]
  =/  index=@ud  0
  =/  size=@ud  0
  |-  ^-  decoded
  ?:  =(4 index)
    ?:  =(0 size)  [%ready %flush [0 0] (add offset 4)]
    ?:  =(1 size)  [%ready %delim [0 0] (add offset 4)]
    ?:  =(2 size)  [%ready %response-end [0 0] (add offset 4)]
    ?:  =(3 size)  [%invalid %reserved-length]
    ?:  (gth size 65.520)  [%invalid %packet-bound]
    ?:  (lth available size)  [%need size]
    =/  payload=@ud  (sub size 4)
    [%ready %data [payload (cut 3 [(add offset 4) payload] data.buffer)] (add offset size)]
  =/  byte=@ud  (cut 3 [(add offset index) 1] data.buffer)
  =/  nibble=(unit @ud)
    ?:  &((gte byte 48) (lte byte 57))  [~ (sub byte 48)]
    ?:  &((gte byte 97) (lte byte 102))  [~ (add 10 (sub byte 97))]
    ?:  &((gte byte 65) (lte byte 70))  [~ (add 10 (sub byte 65))]
    ~
  ?~  nibble  [%invalid %header-hex]
  $(index +(index), size (add (mul size 16) u.nibble))
--

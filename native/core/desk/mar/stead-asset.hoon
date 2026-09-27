::  Exact bounded asset bytes. MIME type is supplied by the verified inventory.
|_  raw=@t
++  grab
  |%
  ++  noun  @t
  ++  mime
    |=  value=[p=mite q=octs]
    ?>  &((lte p.q.value 524.288) =(p.q.value (met 3 q.q.value)))
    q.q.value
  --
++  grow
  |%
  ++  mime  [/application/octet-stream (met 3 raw) raw]
  --
++  grad  %mime
--

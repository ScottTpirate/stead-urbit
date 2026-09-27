::  Bounded immutable assets, loaded only during a fenced native bootstrap.
/+  stead-codec
/=  assets  /web/stead/inventory
|%
+$  cache  (map @t [mime=@t bytes=@t])
++  paths
  |=  prefix=@t
  ^-  (set @t)
  (silt (skim ~(tap in paths:assets) |=(route=@t =(prefix (cut 3 [0 (met 3 prefix)] route)))))
++  load
  |=  [byk=beak prefix=@t]
  ^-  cache
  =/  rows  ~(tap by inventory:assets)
  ?>  &((gth (lent rows) 0) (lte (lent rows) 32))
  =.  rows  (skim rows |=([key=@t value=*] =(prefix (cut 3 [0 (met 3 prefix)] key))))
  ?>  (gth (lent rows) 0)
  =/  total=@ud  0
  =/  files=cache  ~
  |-  ^-  cache
  ?~  rows  files
  =/  entry  q.i.rows
  =/  path  (en-beam [byk file.entry])
  =/  bytes=@t  .^(@t %cx path)
  ?>  &((lte (met 3 bytes) 524.288) =(digest.entry (hex:stead-codec 64 (sha-256l:sha [(met 3 bytes) (rev 3 (met 3 bytes) bytes)]))))
  =.  total  (add total (met 3 bytes))
  ?>  (lte total 2.097.152)
  $(rows t.rows, files (~(put by files) p.i.rows [mime.entry bytes]))
--

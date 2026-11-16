::  Original bounded SHA-1 pack envelope inspection, without decompression.
::  %envelope proves the header/trailer only, never object validity or trust.
|%
+$  octets  [length=@ud data=@]
+$  result
  $%  [%envelope version=@ud declared=@ud entries-length=@ud checksum=@ux]
      [%invalid reason=@tas]
  ==
++  inspect
  |=  pack=octets
  ^-  result
  ?.  ?&  (lte length.pack 8.388.608)
          (lte (met 3 data.pack) length.pack)
      ==
    [%invalid %byte-bound]
  ?:  (lth length.pack 32)  [%invalid %truncated-envelope]
  ?.  =('PACK' (cut 3 [0 4] data.pack))  [%invalid %signature]
  =/  version=@ud  (rev 3 4 (cut 3 [4 4] data.pack))
  ?.  ?|(=(2 version) =(3 version))  [%invalid %version]
  =/  count=@ud  (rev 3 4 (cut 3 [8 4] data.pack))
  ?:  (gth count 4.096)  [%invalid %object-count]
  =/  entries=@ud  (sub length.pack 32)
  ?:  &(=(0 count) !=(0 entries))  [%invalid %empty-pack-payload]
  ?:  &((gth count 0) =(0 entries))  [%invalid %missing-entries]
  =/  hashed-length=@ud  (sub length.pack 20)
  =/  expected=@ux  (rev 3 20 (cut 3 [hashed-length 20] data.pack))
  =/  observed=@ux
    (sha-1l:sha [hashed-length (rev 3 hashed-length (cut 3 [0 hashed-length] data.pack))])
  ?.  =(expected observed)  [%invalid %checksum]
  [%envelope version count entries observed]
--

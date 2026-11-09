/+  *test, stead-code-git-entry
::  Synthetic envelopes are intentionally not checksummed: header scope only.
|%
++  inspect
  |=  [body=octets:stead-code-git-entry offset=@ud]
  ^-  result:stead-code-git-entry
  (decode:stead-code-git-entry [(add 32 length.body) (lsh [3 12] data.body)] offset)
++  check
  |=  [body=octets:stead-code-git-entry offset=@ud wanted=result:stead-code-git-entry]
  ^-  tang
  (expect !>(=(wanted (inspect body offset))))
++  test-entry-ordinary-commit
  (check [2 0x7810] 12 [%& 1 0 %none 13])
++  test-entry-ordinary-tree
  (check [2 0x7820] 12 [%& 2 0 %none 13])
++  test-entry-ordinary-blob
  (check [2 0x7830] 12 [%& 3 0 %none 13])
++  test-entry-ordinary-tag
  (check [2 0x7840] 12 [%& 4 0 %none 13])
++  test-entry-multi-byte-size
  (check [3 0x78.01b0] 12 [%& 3 16 %none 14])
++  test-entry-size-at-bound
  (check [5 0x78.2080.80b0] 12 [%& 3 8.388.608 %none 16])
++  test-entry-size-over-bound
  (check [5 0x78.2080.80b1] 12 [%| %size-bound])
++  test-entry-size-zero-extension
  (check [6 0x7800.8080.80b0] 12 [%& 3 0 %none 17])
++  test-entry-size-extension-bound
  (check [7 0x78.0080.8080.80b0] 12 [%| %size-encoding])
++  test-entry-truncated-size
  (check [1 0xb0] 12 [%| %truncated-size])
++  test-entry-invalid-type
  (check [2 0x7800] 12 [%| %reserved-type])
++  test-entry-reserved-type
  (check [2 0x7850] 12 [%| %reserved-type])
++  test-entry-missing-zlib
  (check [1 0x30] 12 [%| %missing-zlib])
++  test-entry-offset-before-header
  (check [2 0x7830] 11 [%| %entry-offset])
++  test-entry-offset-at-trailer
  (check [2 0x7830] 14 [%| %entry-offset])
++  test-entry-offset-beyond-buffer
  (check [2 0x7830] 999 [%| %entry-offset])
++  test-entry-ofs-base
  (check [4 0x7801.6030] 13 [%& 6 0 [%offset 12] 15])
++  test-entry-ofs-multi-byte
  (check [132 0x7800.8060.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000.0000] 140 [%& 6 0 [%offset 12] 143])
++  test-entry-ofs-zero
  (check [3 0x78.0060] 12 [%| %invalid-offset])
++  test-entry-ofs-before-pack
  (check [3 0x78.0160] 12 [%| %invalid-offset])
++  test-entry-ofs-truncated
  (check [1 0x60] 12 [%| %truncated-offset])
++  test-entry-ofs-extension-bound
  (check [7 0x78.0080.8080.8060] 12 [%| %offset-bound])
++  test-entry-ofs-value-bound
  (check [6 0x787f.ffff.ff60] 12 [%| %offset-bound])
++  test-entry-ofs-missing-zlib
  (check [3 0x1.6030] 13 [%| %missing-zlib])
++  test-entry-ref-big-endian
  (check [22 0x7814.1312.1110.0f0e.0d0c.0b0a.0908.0706.0504.0302.0170] 12 [%& 7 0 [%oid 0x102.0304.0506.0708.090a.0b0c.0d0e.0f10.1112.1314] 33])
++  test-entry-ref-zero-preserved
  (check [22 0x7800.0000.0000.0000.0000.0000.0000.0000.0000.0000.0070] 12 [%& 7 0 [%oid 0x0] 33])
++  test-entry-ref-truncated
  (check [20 0x70] 12 [%| %truncated-reference])
++  test-entry-ref-missing-zlib
  (check [21 0x70] 12 [%| %missing-zlib])
++  test-entry-pack-byte-bound
  (expect !>(=([%| %buffer-bound] (decode:stead-code-git-entry [8.388.609 0] 12))))
++  test-entry-explicit-width
  (expect !>(=([%| %buffer-bound] (decode:stead-code-git-entry [32 (bex 256)] 12))))
++  test-entry-short-envelope
  (expect !>(=([%| %buffer-bound] (decode:stead-code-git-entry [31 0] 12))))
++  test-entry-empty-envelope
  (expect !>(=([%| %entry-offset] (decode:stead-code-git-entry [32 0] 12))))
--

/+  *test, stead-code-git-pkt
::  No ship, state transition, authorization, pack or transport claim.
|%
++  test-encode-data
  (expect !>(=([~ 7 '0007abc'] (encode:stead-code-git-pkt %data [3 'abc']))))
++  test-encode-binary
  (expect !>(=([~ 6 0xff.3630.3030] (encode:stead-code-git-pkt %data [2 255]))))
++  test-encode-empty-data
  (expect !>(=([~ 4 '0004'] (encode:stead-code-git-pkt %data [0 0]))))
++  test-encode-controls
  =/  valid=?
    ?&
      =([~ 4 '0000'] (encode:stead-code-git-pkt %flush [0 0]))
      =([~ 4 '0001'] (encode:stead-code-git-pkt %delim [0 0]))
      =([~ 4 '0002'] (encode:stead-code-git-pkt %response-end [0 0]))
    ==
  (expect !>(valid))
++  test-encode-control-payload-rejected
  (expect !>(=(~ (encode:stead-code-git-pkt %flush [1 0]))))
++  test-encode-at-bound
  (expect !>(=([~ 65.520 'fff0'] (encode:stead-code-git-pkt %data [65.516 0]))))
++  test-encode-over-bound-rejected
  (expect !>(=(~ (encode:stead-code-git-pkt %data [65.517 0]))))
++  test-encode-width-rejected
  (expect !>(=(~ (encode:stead-code-git-pkt %data [0 1]))))
++  test-decode-controls-and-empty
  =/  valid=?
    ?&
      =([%ready %flush [0 0] 4] (decode:stead-code-git-pkt [4 '0000'] 0))
      =([%ready %delim [0 0] 4] (decode:stead-code-git-pkt [4 '0001'] 0))
      =([%ready %response-end [0 0] 4] (decode:stead-code-git-pkt [4 '0002'] 0))
      =([%ready %data [0 0] 4] (decode:stead-code-git-pkt [4 '0004'] 0))
    ==
  (expect !>(valid))
++  test-decode-binary-zero
  (expect !>(=([%ready %data [2 255] 6] (decode:stead-code-git-pkt [6 0xff.3630.3030] 0))))
++  test-decode-all-zero-payload
  (expect !>(=([%ready %data [2 0] 6] (decode:stead-code-git-pkt [6 '0006'] 0))))
++  test-decode-offset-and-tail
  (expect !>(=([%ready %data [1 'a'] 9] (decode:stead-code-git-pkt [13 '00000005a0000'] 4))))
++  test-decode-truncated-header
  (expect !>(=([%need 4] (decode:stead-code-git-pkt [3 '000'] 0))))
++  test-decode-truncated-payload
  (expect !>(=([%need 7] (decode:stead-code-git-pkt [6 '0007ab'] 0))))
++  test-decode-required-relative-to-offset
  (expect !>(=([%need 7] (decode:stead-code-git-pkt [10 '00000007ab'] 4))))
++  test-decode-nonhex-rejected
  (expect !>(=([%invalid %header-hex] (decode:stead-code-git-pkt [4 '00g0'] 0))))
++  test-decode-reserved-rejected
  (expect !>(=([%invalid %reserved-length] (decode:stead-code-git-pkt [4 '0003'] 0))))
++  test-decode-over-bound-rejected
  (expect !>(=([%invalid %packet-bound] (decode:stead-code-git-pkt [4 'fff1'] 0))))
++  test-decode-at-bound
  (expect !>(=([%ready %data [65.516 0] 65.520] (decode:stead-code-git-pkt [65.520 'fff0'] 0))))
++  test-decode-upper-hex
  (expect !>(=([%ready %data [6 'abcdef'] 10] (decode:stead-code-git-pkt [10 '000Aabcdef'] 0))))
++  test-decode-offset-rejected
  (expect !>(=([%invalid %offset-bound] (decode:stead-code-git-pkt [4 '0000'] 5))))
++  test-decode-buffer-bound-rejected
  (expect !>(=([%invalid %buffer-bound] (decode:stead-code-git-pkt [1.048.577 0] 0))))
++  test-decode-buffer-width-rejected
  (expect !>(=([%invalid %buffer-bound] (decode:stead-code-git-pkt [0 1] 0))))
++  failure-control
  (expect !>(%.n))
--
